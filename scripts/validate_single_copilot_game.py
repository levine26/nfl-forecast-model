from __future__ import annotations

"""Fail closed on one focused Copilot response before accepting it into the slate."""

import argparse
from pathlib import Path
import re

import pandas as pd

from compose_copilot_media_reads import _domain_family, _extract_json
from nfl_forecast.source_policy import is_direct_media_report_url
from validate_copilot_media_reads import _mentions_any, _team_aliases


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _ngrams(text: str, n: int = 7) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", _clean(text).lower())
    return {" ".join(words[i:i + n]) for i in range(max(0, len(words) - n + 1))}


def _headline_template(headline: str, away: str, home: str) -> str:
    text = _clean(headline).lower()
    aliases = sorted(_team_aliases(away) | _team_aliases(home), key=len, reverse=True)
    for alias in aliases:
        text = re.sub(rf"\b{re.escape(alias)}\b", " TEAM ", text)
    tokens = re.findall(r"team|[a-z0-9]+", text)
    collapsed: list[str] = []
    for token in tokens:
        if token == "team" and collapsed and collapsed[-1] == "team":
            continue
        collapsed.append(token)
    return " ".join(collapsed)


def _valid_sources(sources: object) -> tuple[list[dict], set[str], list[str]]:
    failures: list[str] = []
    valid: list[dict] = []
    families: set[str] = set()
    if not isinstance(sources, list):
        return valid, families, ["sources must be a list"]
    for source in sources[:8]:
        if not isinstance(source, dict):
            failures.append("source entry is not an object")
            continue
        name = _clean(source.get("name"))
        title = _clean(source.get("title"))
        url = _clean(source.get("url"))
        if not name or not title or not url:
            failures.append("source is missing name, title, or URL")
            continue
        if not is_direct_media_report_url(url):
            failures.append(f"source URL is not a direct approved article/report: {url}")
            continue
        family = _domain_family(url)
        families.add(family)
        valid.append({"name": name, "title": title, "url": url})
    if len(valid) < 2 or len(families) < 2:
        failures.append("requires at least two independent direct approved-domain sources")
    return valid, families, failures


def _load_entry(path: Path, gid: str) -> dict:
    payload = _extract_json(path.read_text(encoding="utf-8", errors="replace"))
    games = payload.get("games") if isinstance(payload, dict) else None
    if not isinstance(games, dict) or set(map(str, games)) != {gid}:
        raise ValueError(f"{gid}: focused response must contain exactly its own game id")
    entry = games.get(gid)
    if not isinstance(entry, dict):
        raise ValueError(f"{gid}: focused game entry is not an object")
    return entry


def validate(path: Path, gid: str, predictions: pd.DataFrame, accepted_dir: Path | None = None) -> list[str]:
    failures: list[str] = []
    rows = predictions[predictions["game_id"].astype(str) == str(gid)]
    if len(rows) != 1:
        return [f"{gid}: expected exactly one prediction row, found {len(rows)}"]
    row = rows.iloc[0]
    away, home = str(row.get("away_team")), str(row.get("home_team"))

    try:
        entry = _load_entry(path, gid)
    except Exception as exc:
        return [str(exc)]

    headline = _clean(entry.get("headline"))
    paragraph1 = _clean(entry.get("paragraph1"))
    rationale = _clean(entry.get("model_rationale"))
    p1_words = re.findall(r"\b[\w'-]+\b", paragraph1)
    rationale_words = re.findall(r"\b[\w'-]+\b", rationale)

    if not 12 <= len(headline) <= 150:
        failures.append(f"{gid}: headline length invalid")
    if not 55 <= len(p1_words) <= 100:
        failures.append(f"{gid}: paragraph1 length {len(p1_words)} outside 55-100")
    if not _mentions_any(paragraph1, _team_aliases(away)) or not _mentions_any(paragraph1, _team_aliases(home)):
        failures.append(f"{gid}: paragraph1 must discuss both teams")
    if not 18 <= len(rationale_words) <= 40:
        failures.append(f"{gid}: model_rationale length {len(rationale_words)} outside 18-40")
    if re.search(r"\d|%|\blevline\b|\bpure\b|\bmarket\b|\bspread\b|\bmodel line\b|\bmoneyline\b", rationale, flags=re.I):
        failures.append(f"{gid}: model_rationale contains a prohibited numerical/model term")

    _, _, source_failures = _valid_sources(entry.get("sources"))
    failures.extend(f"{gid}: {failure}" for failure in source_failures)

    current_human = f"{headline} {paragraph1} {rationale}"
    current_grams = _ngrams(current_human)
    current_template = _headline_template(headline, away, home)
    if accepted_dir and accepted_dir.exists():
        rows_by_gid = {str(r.get("game_id")): r for _, r in predictions.iterrows()}
        for other_path in sorted(accepted_dir.glob("*.txt")):
            if other_path.resolve() == path.resolve():
                continue
            other_gid = other_path.stem
            other_row = rows_by_gid.get(other_gid)
            if other_row is None:
                continue
            try:
                other = _load_entry(other_path, other_gid)
            except Exception:
                continue
            other_human = f"{_clean(other.get('headline'))} {_clean(other.get('paragraph1'))} {_clean(other.get('model_rationale'))}"
            repeated = sorted(current_grams & _ngrams(other_human))
            if repeated:
                failures.append(f"{gid}: repeats seven-word phrase with {other_gid}: '{repeated[0]}'")
            other_template = _headline_template(
                _clean(other.get("headline")), str(other_row.get("away_team")), str(other_row.get("home_team"))
            )
            if current_template and current_template == other_template:
                failures.append(f"{gid}: headline template duplicates {other_gid}: '{current_template}'")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--accepted-dir", default="")
    args = parser.parse_args()

    failures = validate(
        Path(args.input),
        str(args.game_id),
        pd.read_csv(args.predictions),
        Path(args.accepted_dir) if args.accepted_dir else None,
    )
    if failures:
        raise SystemExit("Focused Copilot game validation failed: " + "; ".join(failures))
    print(f"validated focused Copilot response for {args.game_id}")


if __name__ == "__main__":
    main()
