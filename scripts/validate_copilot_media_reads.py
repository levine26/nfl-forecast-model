from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import json
import re

import pandas as pd

from nfl_forecast.context import TEAM_META

ALLOWED_DOMAINS = {
    "espn.com", "nfl.com", "nytimes.com", "theathletic.com", "apnews.com",
    "cbssports.com", "sports.yahoo.com", "yahoo.com", "nbcsports.com",
    "foxsports.com", "si.com", "x.com", "twitter.com",
}
BANNED = (
    "coverage highlights", "pressure note", "history note", "pure has",
    "start with", "the cleanest lens", "the hinge", "the case for",
    "the matchup file", "strip away the probability", "two distinct levers",
    "real matchup counter-signal", "deserves the first paragraph",
)


def _extract_json(text: str) -> dict:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Copilot output does not contain a JSON object")
        return json.loads(raw[start:end + 1])


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
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


def _ngrams(text: str, n: int = 7) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(text or "").lower())
    return {" ".join(words[i:i+n]) for i in range(max(0, len(words) - n + 1))}


def _team_aliases(code: str) -> set[str]:
    key = "JAX" if str(code).upper() == "JAC" else str(code).upper()
    full = str((TEAM_META.get(key) or {}).get("name") or key)
    parts = full.lower().split()
    aliases = {full.lower(), key.lower()}
    if parts:
        aliases.add(parts[-1])
    if len(parts) > 1:
        aliases.add(" ".join(parts[:-1]))
    return {alias for alias in aliases if len(alias) >= 2}


def _mentions_any(text: str, aliases: set[str]) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(alias)}\b", lowered) for alias in aliases)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--predictions", default="outputs/this_week.csv")
    parser.add_argument("--output", default="outputs/copilot_media_reads.json")
    args = parser.parse_args()

    payload = _extract_json(Path(args.input).read_text(encoding="utf-8"))
    games = payload.get("games") if isinstance(payload, dict) else None
    if not isinstance(games, dict):
        raise SystemExit("Copilot media output missing games object")

    predictions = pd.read_csv(args.predictions)
    expected = set(predictions["game_id"].astype(str))
    actual = set(str(x) for x in games)
    if actual != expected:
        raise SystemExit(
            f"Copilot media game coverage mismatch: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}"
        )

    rows = {str(row.get("game_id")): row for _, row in predictions.iterrows()}
    failures: list[str] = []
    grams: dict[str, set[str]] = {}
    cleaned: dict[str, dict] = {}
    generated = datetime.now(timezone.utc).isoformat()

    for gid in sorted(expected):
        entry = games.get(gid)
        if not isinstance(entry, dict):
            failures.append(f"{gid}: entry is not an object")
            continue
        headline = re.sub(r"\s+", " ", str(entry.get("headline") or "")).strip()
        read = re.sub(r"\s+", " ", str(entry.get("read") or "")).strip()
        sources = entry.get("sources") or []
        words = re.findall(r"\b[\w'-]+\b", read)
        if not 80 <= len(words) <= 165:
            failures.append(f"{gid}: Read length {len(words)} words outside 80-165")
        if not 12 <= len(headline) <= 150:
            failures.append(f"{gid}: headline length invalid")

        combined = f"{headline} {read}"
        low = combined.lower()
        for phrase in BANNED:
            if phrase in low:
                failures.append(f"{gid}: banned template phrase '{phrase}'")

        row = rows[gid]
        away_aliases = _team_aliases(str(row.get("away_team")))
        home_aliases = _team_aliases(str(row.get("home_team")))
        if not _mentions_any(combined, away_aliases) or not _mentions_any(combined, home_aliases):
            failures.append(f"{gid}: Read/headline does not clearly identify both teams")

        if not isinstance(sources, list):
            failures.append(f"{gid}: sources is not a list")
            sources = []
        valid_sources = []
        domain_families = set()
        for source in sources[:8]:
            if not isinstance(source, dict):
                continue
            name = str(source.get("name") or "").strip()
            title = str(source.get("title") or "").strip()
            url = str(source.get("url") or "").strip()
            if not name or not title or not url or not _domain_allowed(url):
                failures.append(f"{gid}: invalid source {source}")
                continue
            valid_sources.append({"name": name, "title": title, "url": url})
            domain_families.add(_domain_family(url))
        if len(valid_sources) < 2 or len(domain_families) < 2:
            failures.append(f"{gid}: requires at least two independent approved-domain sources")

        cleaned[gid] = {
            "headline": headline,
            "read": read,
            "sources": valid_sources,
            "generated_utc": generated,
        }
        for gram in _ngrams(combined):
            grams.setdefault(gram, set()).add(gid)

    repeated = {gram: sorted(gids) for gram, gids in grams.items() if len(gids) > 1}
    if repeated:
        failures.append(f"cross-game seven-word repetition: {list(repeated.items())[:8]}")
    if failures:
        raise SystemExit("Copilot media validation failed: " + "; ".join(failures))

    Path(args.output).write_text(
        json.dumps({"generated_utc": generated, "games": cleaned}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"validated {len(cleaned)} Copilot media Reads -> {args.output}")


if __name__ == "__main__":
    main()
