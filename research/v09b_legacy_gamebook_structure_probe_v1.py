from __future__ import annotations

"""Diagnostic-only probe for legacy NFLGSIS Game Book text structure.

This probe has no qualification authority. It samples exactly one canonical regular-season
Game Book per season, extracts text with the same frozen PDF extractor as the raw-archive
audit, and emits bounded candidate lines so the historical section vocabulary can be
identified empirically. It does not construct labels, use outcomes, or fit a model.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import requests

from research.v09b_legacy_gamebook_locator_audit_v1 import (
    EXPECTED_GAMES,
    _canonical_games,
    _canonical_team,
    legacy_gamebook_url,
    load_discovery_crosswalk,
)
from research.v09b_legacy_gamebook_raw_archive_v1 import _extract_pdf_text, _sha256

KEYWORD_RE = re.compile(
    r"(?i)(?:\binactive(?:s)?\b|\bdid\s+not\b|\bnot\s+play(?:ed)?\b|"
    r"\bdress(?:ed|ing)?\b|\bscratch(?:ed|es)?\b|\bdeactiv\w*\b|"
    r"\bparticipat\w*\b|\bstatus\b)"
)


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
    if not (3 <= len(cleaned) <= 100):
        return False
    letters = [ch for ch in cleaned if ch.isalpha()]
    if len(letters) < 3:
        return False
    return all(not ch.islower() for ch in letters)


def probe_season(season: int, *, timeout: float = 30.0) -> dict[str, object]:
    if season not in EXPECTED_GAMES:
        raise ValueError(f"season must be one of {sorted(EXPECTED_GAMES)}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; LevLine4Research/1.0; structure-probe)",
        "Accept": "application/pdf,*/*;q=0.8",
    })
    crosswalk = load_discovery_crosswalk(session, timeout)
    game = _canonical_games(season)[0]
    week = int(game["week"])
    away = _canonical_team(game["away_team"])
    home = _canonical_team(game["home_team"])
    match = crosswalk.get((season, week, away, home))
    if match is None or match.get("gamekey") in (None, ""):
        raise RuntimeError("sample game missing legacy discovery gamekey")
    gamekey = str(match["gamekey"])
    url = legacy_gamebook_url(season, week, gamekey)

    response = session.get(url, timeout=timeout, allow_redirects=True)
    status = int(response.status_code)
    content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    raw = bytes(response.content)
    response.close()
    if status != 200 or content_type != "application/pdf" or not raw.startswith(b"%PDF"):
        raise RuntimeError(
            f"sample source invalid: status={status} content_type={content_type!r} pdf={raw.startswith(b'%PDF')}"
        )

    text = _extract_pdf_text(raw)
    lines = text.splitlines()
    nonempty = [line for line in lines if _clean(line)]
    keyword_lines = _unique_bounded((line for line in nonempty if KEYWORD_RE.search(line)), 80)
    heading_lines = _unique_bounded((line for line in nonempty if _heading_like(line)), 120)

    return {
        "probe_version": 1,
        "season": season,
        "sample_selection": "first canonical regular-season game only",
        "game_id": str(game["game_id"]),
        "week": week,
        "away_team": away,
        "home_team": home,
        "gamekey": gamekey,
        "source_url": url,
        "source_sha256": _sha256(raw),
        "source_bytes": len(raw),
        "text_length": len(text),
        "keyword_candidate_lines": keyword_lines,
        "heading_like_lines": heading_lines,
        "first_nonempty_lines": _unique_bounded(nonempty, 80),
        "last_nonempty_lines": _unique_bounded(reversed(nonempty), 80),
        "qualification_authority": False,
        "player_labels_constructed": False,
        "game_day_roster_universe_constructed": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=sorted(EXPECTED_GAMES))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = probe_season(args.season, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "season": result["season"],
        "game_id": result["game_id"],
        "keyword_candidate_lines": result["keyword_candidate_lines"],
        "heading_like_lines": result["heading_like_lines"][:40],
        "qualification_authority": False,
        "completed_2026_outcomes_used": 0,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
