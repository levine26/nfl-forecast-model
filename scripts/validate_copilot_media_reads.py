from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import json
import re

import pandas as pd

ALLOWED_DOMAINS = {
    "espn.com", "www.espn.com", "insider.espn.com",
    "nfl.com", "www.nfl.com",
    "nytimes.com", "www.nytimes.com", "theathletic.com", "www.nytimes.com/athletic",
    "apnews.com", "www.apnews.com",
    "cbssports.com", "www.cbssports.com",
    "sports.yahoo.com", "yahoo.com",
    "nbcsports.com", "www.nbcsports.com",
    "foxsports.com", "www.foxsports.com",
    "si.com", "www.si.com",
    "x.com", "twitter.com",
    # Google News redirects are accepted only as discovery links; the writer is
    # still instructed to identify the underlying outlet in source.name/title.
    "news.google.com",
}
BANNED = (
    "start with", "the cleanest lens", "the hinge", "the case for",
    "the matchup file", "strip away the probability", "two distinct levers",
    "real matchup counter-signal",
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


def _domain_allowed(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if host in ALLOWED_DOMAINS:
        return True
    return any(host.endswith("." + domain) for domain in ALLOWED_DOMAINS if "/" not in domain)


def _ngrams(text: str, n: int = 7) -> set[str]:
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", str(text or "").lower())
    return {" ".join(words[i:i+n]) for i in range(max(0, len(words) - n + 1))}


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
        raise SystemExit(f"Copilot media game coverage mismatch: missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")

    failures = []
    grams: dict[str, set[str]] = {}
    cleaned = {}
    generated = datetime.now(timezone.utc).isoformat()
    for gid in sorted(expected):
        entry = games.get(gid)
        if not isinstance(entry, dict):
            failures.append(f"{gid}: entry is not an object"); continue
        headline = re.sub(r"\s+", " ", str(entry.get("headline") or "")).strip()
        read = re.sub(r"\s+", " ", str(entry.get("read") or "")).strip()
        sources = entry.get("sources") or []
        words = re.findall(r"\b[\w'-]+\b", read)
        if not 70 <= len(words) <= 170:
            failures.append(f"{gid}: Read length {len(words)} words outside 70-170")
        if not 8 <= len(headline) <= 140:
            failures.append(f"{gid}: headline length invalid")
        low = f"{headline} {read}".lower()
        for phrase in BANNED:
            if phrase in low:
                failures.append(f"{gid}: banned template phrase '{phrase}'")
        if not isinstance(sources, list) or len(sources) < 1:
            failures.append(f"{gid}: no sources")
            sources = []
        valid_sources = []
        for source in sources[:6]:
            if not isinstance(source, dict):
                continue
            name = str(source.get("name") or "").strip()
            title = str(source.get("title") or "").strip()
            url = str(source.get("url") or "").strip()
            if not name or not title or not url or not _domain_allowed(url):
                failures.append(f"{gid}: invalid source {source}")
                continue
            valid_sources.append({"name":name, "title":title, "url":url})
        if not valid_sources:
            failures.append(f"{gid}: no valid approved-domain source")
        cleaned[gid] = {
            "headline": headline,
            "read": read,
            "sources": valid_sources,
            "generated_utc": generated,
        }
        for gram in _ngrams(f"{headline} {read}"):
            grams.setdefault(gram, set()).add(gid)

    repeated = {gram: sorted(gids) for gram, gids in grams.items() if len(gids) > 1}
    if repeated:
        failures.append(f"cross-game seven-word repetition: {list(repeated.items())[:5]}")
    if failures:
        raise SystemExit("Copilot media validation failed: " + "; ".join(failures))

    output = {"generated_utc": generated, "games": cleaned}
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"validated {len(cleaned)} Copilot media Reads -> {args.output}")


if __name__ == "__main__":
    main()
