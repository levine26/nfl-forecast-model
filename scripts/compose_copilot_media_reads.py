from __future__ import annotations

"""Compose Copilot-written matchup prose with deterministic LevLine facts.

Copilot owns the human headline/matchup analysis and a short football rationale.
This script owns every numerical LevLine statement and normalizes source provenance
before the existing publication validator runs. It is editorial-only and cannot
change model inputs, probabilities, weights, locks, or grading.
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import json_repair
import pandas as pd

from nfl_forecast.context import TEAM_META

ALLOWED_DOMAINS = {
    "espn.com", "nfl.com", "nytimes.com", "theathletic.com", "apnews.com",
    "cbssports.com", "sports.yahoo.com", "yahoo.com", "nbcsports.com",
    "foxsports.com", "si.com", "x.com", "twitter.com",
}


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
        raise ValueError("Copilot output does not contain a JSON object")
    repaired = json_repair.loads(raw[start:end + 1], skip_json_loads=True)
    if not isinstance(repaired, dict):
        raise ValueError("Repaired Copilot output JSON root is not an object")
    return repaired


def _host(url: str) -> str:
    try:
        return (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return ""


def _domain_allowed(url: str) -> bool:
    host = _host(url)
    return any(host == domain or host.endswith("." + domain) for domain in ALLOWED_DOMAINS)


def _domain_family(url: str) -> str:
    host = _host(url)
    if host.startswith("www."):
        host = host[4:]
    if host.endswith("sports.yahoo.com"):
        return "yahoo.com"
    return host


def _canonical_url(url: str, name: str = "", publisher_url: str = "") -> str:
    """Return only a direct approved URL or a resolvable Bing target.

    Publisher homepages are intentionally not substituted for missing article URLs:
    if provenance cannot be tied to a direct approved URL, it must fail closed in
    the downstream two-independent-source gate.
    """
    del name, publisher_url  # retained in the signature for a stable call surface
    raw = str(url or "").strip()
    if _domain_allowed(raw):
        return raw

    parsed = urlparse(raw)
    if parsed.hostname and parsed.hostname.lower().endswith("bing.com"):
        target = (parse_qs(parsed.query).get("url") or [""])[0]
        target = unquote(target)
        if _domain_allowed(target):
            return target
    return ""


def _team_name(code: str) -> str:
    key = "JAX" if str(code).upper() == "JAC" else str(code).upper()
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _nick(code: str) -> str:
    return _team_name(code).split()[-1]


def _possessive(name: str) -> str:
    return f"{name}'" if str(name).lower().endswith("s") else f"{name}'s"


def _number(value) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return None if pd.isna(number) else number


def _pick_probability(row: pd.Series, field: str) -> float | None:
    value = _number(row.get(field))
    if value is None:
        return None
    return value if str(row.get("pick")) == str(row.get("home_team")) else 1.0 - value


def _line_text(value, home: str, away: str) -> str:
    margin = _number(value)
    if margin is None:
        return ""
    if abs(margin) < 0.05:
        return "pick'em"
    favored = home if margin > 0 else away
    return f"{_team_name(favored)} -{abs(margin):.1f}"


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _safe_rationale(entry: dict, preview: dict, pick: str, opponent: str) -> str:
    rationale = _clean_text(entry.get("model_rationale") or "")
    words = re.findall(r"\b[\w'-]+\b", rationale)
    banned_fact_tokens = re.compile(
        r"\d|%|\blevline\b|\bpure\b|\bmarket\b|\bspread\b|\bmodel line\b|\bmoneyline\b",
        flags=re.I,
    )
    if 16 <= len(words) <= 48 and not banned_fact_tokens.search(rationale):
        if rationale[-1:] not in ".!?":
            rationale += "."
        return rationale

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
    pick_nick = _nick(pick)
    opponent_nick = _nick(opponent)
    return (
        f"{pick_nick} context: {factor}. For {pick_nick}, this evidence supports {pick_nick} against {opponent_nick}; "
        f"{pick_nick} evidence stays editorial, not a {pick_nick} numerical input."
    )


def _model_paragraph(row: pd.Series, rationale: str) -> str:
    away = str(row.get("away_team"))
    home = str(row.get("home_team"))
    pick = str(row.get("pick"))
    pick_name = _team_name(pick)
    pick_nick = _nick(pick)

    final_prob = _pick_probability(row, "final_home_prob")
    pure_prob = _pick_probability(row, "pure_home_prob")
    market_prob = _pick_probability(row, "market_home_prob")
    model_line = _line_text(row.get("expected_margin"), home, away)
    market_line = _line_text(row.get("spread_line"), home, away)
    projected = _clean_text(row.get("projected_score"))

    sentences: list[str] = []
    if final_prob is not None:
        sentences.append(f"LevLine puts the {pick_nick} at {final_prob * 100:.1f}% to win.")
    if pure_prob is not None and market_prob is not None:
        sentences.append(
            f"{pick_nick} football-only PURE is {pure_prob * 100:.1f}%; {pick_nick} market probability is {market_prob * 100:.1f}%. "
            f"In the {pick_nick} blend, PURE carries 75%; for the {pick_nick}, MARKET carries 25%."
        )
    if model_line:
        sentences.append(f"{pick_nick} LevLine model line is {model_line}.")
    if market_line:
        sentences.append(f"{pick_nick} market spread is {market_line}.")
    if projected:
        sentences.append(f"{pick_nick} projected score: {projected}.")

    sentences.append(rationale)
    sentences.append(f"The pick: {pick_name} moneyline.")
    return " ".join(sentences)


def _source_candidates(entry: dict, preview: dict, evidence_items: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for source in entry.get("sources") or []:
        if isinstance(source, dict):
            rows.append({
                "name": source.get("name"),
                "title": source.get("title"),
                "url": source.get("url"),
            })
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
        if not url or not _domain_allowed(url):
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
        raise ValueError("Copilot media output missing games object")

    expected = set(predictions["game_id"].astype(str))
    actual = set(str(key) for key in games)
    if actual != expected:
        raise ValueError(f"Copilot media game coverage mismatch: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")

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
        sources = _canonical_sources(entry, preview, evidence.get(gid, []) if isinstance(evidence, dict) else [])
        out[gid] = {
            "headline": headline,
            "paragraph1": paragraph1,
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
    print(f"composed deterministic LevLine facts for {len(composed['games'])} Copilot Reads -> {args.output}")


if __name__ == "__main__":
    main()
