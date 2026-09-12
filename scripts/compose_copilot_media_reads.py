from __future__ import annotations

"""Compose provider-researched matchup prose with deterministic LevLine 3.0 facts.

The external provider owns the human headline/matchup analysis and a short football
rationale. This script owns every numerical LevLine statement and source normalization.
It is editorial-only and cannot change model inputs, probabilities, locks, or grading.
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import json_repair
import pandas as pd

from nfl_forecast.context import TEAM_META
from nfl_forecast.copilot_source_backfill import backfill_direct_sources
from nfl_forecast.editorial_model_read import render_model_paragraph
from nfl_forecast.source_policy import (
    is_direct_media_report_url,
    media_domain_allowed,
    media_domain_family,
)


def _extract_json(text: str) -> dict:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    candidates = [raw]
    if start >= 0 and end > start and raw[start:end + 1] != raw:
        candidates.append(raw[start:end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    if start < 0 or end <= start:
        raise ValueError("editorial output does not contain a JSON object")
    repaired = json_repair.loads(raw[start:end + 1], skip_json_loads=True)
    if not isinstance(repaired, dict):
        raise ValueError("repaired editorial output JSON root is not an object")
    return repaired


def _domain_allowed(url: str) -> bool:
    return media_domain_allowed(url)


def _domain_family(url: str) -> str:
    return media_domain_family(url)


def _canonical_url(url: str, name: str = "", publisher_url: str = "") -> str:
    """Return only a direct approved report URL or a resolvable Bing target."""
    del name, publisher_url
    raw = str(url or "").strip()
    if is_direct_media_report_url(raw):
        return raw
    try:
        parsed = urlparse(raw)
    except Exception:
        return ""
    if parsed.hostname and parsed.hostname.lower().endswith("bing.com"):
        target = unquote((parse_qs(parsed.query).get("url") or [""])[0])
        if is_direct_media_report_url(target):
            return target
    return ""


def _team_name(code: str) -> str:
    key = "JAX" if str(code).upper() == "JAC" else str(code).upper()
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _nick(code: str) -> str:
    return _team_name(code).split()[-1]


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_rationale(entry: dict, preview: dict, pick: str, opponent: str) -> str:
    rationale = _clean_text(entry.get("model_rationale") or "")
    words = re.findall(r"\b[\w'-]+\b", rationale)
    banned_fact_tokens = re.compile(
        r"\d|%|\blevline\b|\bf-st\b|\bpure\b|\bmarket\b|\bspread\b|\bmodel line\b|\bmoneyline\b",
        flags=re.I,
    )
    if 16 <= len(words) <= 48 and not banned_fact_tokens.search(rationale):
        return rationale if rationale[-1:] in ".!?" else rationale + "."

    factor = ""
    for item in preview.get("key_factors") or []:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        if title:
            factor = title
            break
    if not factor:
        factor = _clean_text(preview.get("case_for_pick")) or f"{_nick(pick)} execution against {_nick(opponent)}"
    return f"Football context: {factor}."


def _model_paragraph(row: pd.Series, rationale: str) -> str:
    """Compatibility wrapper around the canonical 3.0 model-read serializer."""
    return render_model_paragraph(row, rationale)


def _source_candidates(entry: dict, preview: dict, evidence_items: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for source in entry.get("sources") or []:
        if isinstance(source, dict):
            rows.append({"name": source.get("name"), "title": source.get("title"), "url": source.get("url")})
    for source in preview.get("reported_sources") or []:
        if isinstance(source, dict):
            rows.append({
                "name": source.get("source_name"),
                "title": source.get("title"),
                "url": source.get("source_url"),
            })
    for source in evidence_items:
        if not isinstance(source, dict):
            continue
        meta = source.get("metadata") or {}
        if str(meta.get("family") or source.get("category") or "") != "reported_angle":
            continue
        rows.append({
            "name": source.get("source_name"),
            "title": source.get("title"),
            "url": source.get("source_url"),
        })
    return rows


def _canonical_sources(entry: dict, preview: dict, evidence_items: list[dict]) -> list[dict]:
    selected: list[dict] = []
    families: set[str] = set()
    seen_titles: set[str] = set()
    for source in _source_candidates(entry, preview, evidence_items):
        name = _clean_text(source.get("name"))
        title = _clean_text(source.get("title"))
        if not name or not title:
            continue
        url = _canonical_url(source.get("url") or "", name)
        if not url or not is_direct_media_report_url(url):
            continue
        family = _domain_family(url)
        title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
        if title_key in seen_titles or family in families:
            continue
        selected.append({"name": name, "title": title, "url": url})
        seen_titles.add(title_key)
        families.add(family)
        if len(selected) >= 4:
            break
    return selected


def compose(payload: dict, predictions: pd.DataFrame, previews: dict, evidence: dict) -> dict:
    games = payload.get("games") if isinstance(payload, dict) else None
    if not isinstance(games, dict):
        raise ValueError("editorial media output missing games object")

    expected = set(predictions["game_id"].astype(str))
    actual = set(str(key) for key in games)
    if actual != expected:
        raise ValueError(f"editorial media game coverage mismatch: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")

    rows = {str(row.get("game_id")): row for _, row in predictions.iterrows()}
    out: dict[str, dict] = {}
    for gid in sorted(expected):
        entry = games.get(gid)
        if not isinstance(entry, dict):
            raise ValueError(f"{gid}: entry is not an object")
        row = rows[gid]
        preview = previews.get(gid, {}) if isinstance(previews, dict) else {}
        headline = _clean_text(entry.get("headline"))
        paragraph1 = _clean_text(entry.get("paragraph1"))
        pick = str(row.get("pick"))
        opponent = str(row.get("away_team")) if pick == str(row.get("home_team")) else str(row.get("home_team"))
        rationale = _safe_rationale(entry, preview, pick, opponent)
        paragraph2 = _model_paragraph(row, rationale)
        evidence_items = evidence.get(gid, []) if isinstance(evidence, dict) else []
        sources = _canonical_sources(entry, preview, evidence_items)
        if len({_domain_family(str(source.get("url") or "")) for source in sources}) < 2:
            sources = backfill_direct_sources(row, sources)
        out[gid] = {
            "headline": headline,
            "paragraph1": paragraph1,
            "model_rationale": rationale,
            "paragraph2": paragraph2,
            "sources": sources,
        }
    return {"games": out}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--previews", default="outputs/game_previews.json")
    parser.add_argument("--evidence", default="outputs/contextual_evidence.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = _extract_json(Path(args.input).read_text(encoding="utf-8"))
    predictions = pd.read_csv(args.predictions)
    previews = json.loads(Path(args.previews).read_text(encoding="utf-8"))
    evidence = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    composed = compose(payload, predictions, previews, evidence)
    Path(args.output).write_text(json.dumps(composed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"composed deterministic LevLine 3.0 facts for {len(composed['games'])} researched Reads -> {args.output}")


if __name__ == "__main__":
    main()
