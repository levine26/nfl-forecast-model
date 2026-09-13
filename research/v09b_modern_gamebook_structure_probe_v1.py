from __future__ import annotations

"""Diagnostic-only modern NFL Game Book text-structure probe.

One deterministic canonical game per 2017-2021 season is fetched through the already-
qualified first-party locator logic. The probe reports text candidates only; it does not
apply legacy roster semantics, construct labels, or qualify source coverage.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

import requests

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_v1
from research import v09b_modern_gamebook_locator_audit_v1 as locator_v1
from research import v09b_modern_gamebook_locator_audit_v2 as locator_v2

SEASONS = (2017, 2018, 2019, 2020, 2021)
KEYWORD_RE = re.compile(
    r"(?i)(?:\bnot\s+active\b|\bdid\s+not\s+play\b|\binactive(?:s)?\b|"
    r"\blineups?\b|\bsubstitutions?\b|\bdid\s+not\s+dress\b|\bdeactiv\w*\b)"
)
PHRASE_PATTERNS = {
    "not_active": re.compile(r"(?i)\bNot\s+Active\b"),
    "did_not_play": re.compile(r"(?i)\bDid\s+Not\s+Play\b"),
    "lineup": re.compile(r"(?i)\bLineups?\b"),
    "substitutions": re.compile(r"(?i)\bSubstitutions?\b"),
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean(line: str) -> str:
    return " ".join(line.strip().split())


def _unique_bounded(lines: Iterable[str], limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        cleaned = _clean(line)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _heading_like(line: str) -> bool:
    cleaned = _clean(line)
    if not (3 <= len(cleaned) <= 120):
        return False
    letters = [ch for ch in cleaned if ch.isalpha()]
    if len(letters) < 3:
        return False
    return all(not ch.islower() for ch in letters)


def structure_candidates(text: str) -> dict[str, object]:
    lines = text.splitlines()
    nonempty = [line for line in lines if _clean(line)]
    return {
        "literal_phrase_occurrence_counts": {
            name: len(pattern.findall(text)) for name, pattern in PHRASE_PATTERNS.items()
        },
        "keyword_candidate_lines": _unique_bounded(
            (line for line in nonempty if KEYWORD_RE.search(line)), 120
        ),
        "heading_like_lines": _unique_bounded(
            (line for line in nonempty if _heading_like(line)), 160
        ),
        "first_nonempty_lines": _unique_bounded(nonempty, 100),
        "last_nonempty_lines": _unique_bounded(reversed(nonempty), 100),
    }


def _first_party_get(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
    attempts: int,
) -> requests.Response:
    response = locator_v1._request(session, url, timeout=timeout, attempts=attempts)
    final_url = str(getattr(response, "url", url) or url)
    if not locator_v2.redirect_target_allowed(url, final_url):
        response.close()
        raise RuntimeError(
            "first-party request redirected outside authorized host class: "
            f"requested={url} final={final_url}"
        )
    return response


def fetch_sample_gamebook(
    season: int,
    *,
    timeout: float = 30.0,
    attempts: int = 3,
) -> dict[str, object]:
    if season not in SEASONS:
        raise ValueError(f"season must be one of {list(SEASONS)}")

    game = locator_v1._canonical_games(season)[0]
    week = int(game["week"])
    away = str(game["away_team"])
    home = str(game["home_team"])
    guessed_center = locator_v1.game_center_url(
        season=season,
        week=week,
        away_team=away,
        home_team=home,
    )

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; LevLine4Research/1.0; modern-structure-probe)",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })

    center_url = guessed_center
    resolution_method = "deterministic_slug"
    response = _first_party_get(session, center_url, timeout=timeout, attempts=attempts)
    center_status = int(response.status_code)
    center_html = response.text if response.ok else ""
    response.close()

    if center_status == 404:
        schedule_url = locator_v1.week_schedule_url(season=season, week=week)
        schedule_response = _first_party_get(
            session, schedule_url, timeout=timeout, attempts=attempts
        )
        schedule_status = int(schedule_response.status_code)
        schedule_html = schedule_response.text if schedule_response.ok else ""
        schedule_response.close()
        if schedule_status != 200:
            raise RuntimeError(f"week schedule HTTP {schedule_status}")
        candidates = locator_v1.extract_game_center_links(
            schedule_html,
            schedule_url=schedule_url,
            season=season,
            week=week,
            away_team=away,
            home_team=home,
        )
        if len(candidates) != 1:
            raise RuntimeError(
                f"expected exactly one first-party Game Center fallback; found {len(candidates)}"
            )
        center_url = candidates[0]
        resolution_method = "first_party_week_schedule_fallback"
        response = _first_party_get(session, center_url, timeout=timeout, attempts=attempts)
        center_status = int(response.status_code)
        center_html = response.text if response.ok else ""
        response.close()

    if center_status != 200:
        raise RuntimeError(f"Game Center HTTP {center_status}")

    links, extraction_method = locator_v2.extract_gamebook_evidence(center_html, center_url)
    if len(links) != 1:
        raise RuntimeError(f"expected exactly one Game Book document; found {len(links)}")
    document_url = links[0]
    if not locator_v1.is_allowed_document_url(document_url):
        raise RuntimeError(f"Game Book URL is not authorized first-party document: {document_url}")

    document = _first_party_get(session, document_url, timeout=timeout, attempts=attempts)
    document_status = int(document.status_code)
    content_type = (document.headers.get("content-type") or "").split(";")[0].strip().lower()
    raw = bytes(document.content)
    final_document_url = str(getattr(document, "url", document_url) or document_url)
    document.close()
    if document_status != 200:
        raise RuntimeError(f"Game Book HTTP {document_status}")
    if content_type != "application/pdf":
        raise RuntimeError(f"unexpected Game Book content type: {content_type!r}")
    if not raw.startswith(b"%PDF"):
        raise RuntimeError("Game Book missing PDF magic")

    return {
        "season": season,
        "week": week,
        "game_id": str(game["game_id"]),
        "away_team": away,
        "home_team": home,
        "guessed_game_center_url": guessed_center,
        "game_center_url": center_url,
        "game_center_resolution_method": resolution_method,
        "gamebook_extraction_method": extraction_method,
        "gamebook_url": document_url,
        "gamebook_final_url": final_document_url,
        "gamebook_content_type": content_type,
        "raw_pdf_bytes": raw,
    }


def probe_season(season: int, *, timeout: float = 30.0, attempts: int = 3) -> dict[str, Any]:
    source = fetch_sample_gamebook(season, timeout=timeout, attempts=attempts)
    raw = source.pop("raw_pdf_bytes")
    assert isinstance(raw, bytes)
    text = raw_v1._extract_pdf_text(raw)
    return {
        "probe_version": 1,
        **source,
        "source_sha256": _sha256(raw),
        "source_bytes": len(raw),
        "text_sha256": _sha256(text.encode("utf-8")),
        "text_length": len(text),
        **structure_candidates(text),
        "sample_selection": "first canonical regular-season game after canonical schedule sort",
        "semantic_parser_applied": False,
        "legacy_heading_regex_assumed_valid": False,
        "legacy_roster_partition_assumed_valid": False,
        "qualification_authority": False,
        "modern_raw_source_bytes_qualified": False,
        "modern_gamebook_structure_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=list(SEASONS))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = probe_season(args.season, timeout=args.timeout, attempts=args.attempts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "season": result["season"],
        "game_id": result["game_id"],
        "literal_phrase_occurrence_counts": result["literal_phrase_occurrence_counts"],
        "keyword_candidate_lines": result["keyword_candidate_lines"],
        "qualification_authority": False,
        "completed_2026_outcomes_used": 0,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
