from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import json
import re
import sys

import pandas as pd
import json_repair

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
    "consensus pricing and the football-only model tell different versions",
    "keeps enough of that split visible to matter", "according to yahoo sports",
    "according to cbs sports", "live stream", "tv map",
)


def _extract_json(text: str) -> dict:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)

    candidates = [raw]
    start, end = raw.find("{"), raw.rfind("}")
    if start >= 0 and end > start and raw[start:end + 1] != raw:
        candidates.append(raw[start:end + 1])

    strict_errors: list[str] = []
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as exc:
            strict_errors.append(str(exc))
            continue
        if not isinstance(parsed, dict):
            raise ValueError("Copilot output JSON root is not an object")
        return parsed

    if start < 0 or end <= start:
        raise ValueError("Copilot output does not contain a JSON object")

    candidate = raw[start:end + 1]
    try:
        repaired = json_repair.loads(candidate, skip_json_loads=True)
    except Exception as exc:
        detail = strict_errors[-1] if strict_errors else "strict JSON parse failed"
        raise ValueError(f"Copilot JSON could not be repaired after {detail}: {exc}") from exc

    if not isinstance(repaired, dict):
        raise ValueError("Repaired Copilot output JSON root is not an object")
    print(
        "Copilot response required syntax repair before semantic validation; "
        "all publication gates remain enforced.",
        file=sys.stderr,
    )
    return repaired


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


def _team_name(code: str) -> str:
    key = "JAX" if str(code).upper() == "JAC" else str(code).upper()
    return str((TEAM_META.get(key) or {}).get("name") or key)


def _team_aliases(code: str) -> set[str]:
    key = "JAX" if str(code).upper() == "JAC" else str(code).upper()
    full = _team_name(key)
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


def _pick_side_probability(row: pd.Series, field: str) -> float | None:
    try:
        value = float(row.get(field))
    except Exception:
        return None
    if pd.isna(value):
        return None
    return value if str(row.get("pick")) == str(row.get("home_team")) else 1.0 - value


def _contains_pct(text: str, value: float | None) -> bool:
    if value is None:
        return True
    pct = value * 100.0
    candidates = {f"{pct:.1f}%", f"{pct:.0f}%"}
    return any(candidate in text for candidate in candidates)


def _contains_score(text: str, projected_score: str) -> bool:
    numbers = re.findall(r"\d+(?:\.\d+)?", str(projected_score or ""))
    return not numbers or all(number in text for number in numbers[-2:])


def _float_or_none(value) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    return None if pd.isna(number) else number


def _contains_labeled_line(
    text: str,
    value,
    home: str,
    away: str,
    labels: tuple[str, ...],
) -> bool:
    """Verify a rounded line value, its favored team, and a nearby model/market label."""
    number = _float_or_none(value)
    if number is None:
        return True

    lowered = str(text or "").lower()
    if abs(number) < 0.05:
        has_even = any(token in lowered for token in ("pick'em", "pick em", "even"))
        return has_even and any(label in lowered for label in labels)

    favored = home if number > 0 else away
    aliases = _team_aliases(favored)
    magnitude = abs(number)
    candidates = {
        f"{magnitude:.1f}",
        f"{magnitude:.2f}".rstrip("0").rstrip("."),
    }
    for candidate in candidates:
        if not candidate:
            continue
        pattern = rf"(?<![\d.]){re.escape(candidate)}(?![\d.])"
        for match in re.finditer(pattern, lowered):
            left = max(0, match.start() - 100)
            right = min(len(lowered), match.end() + 100)
            window = lowered[left:right]
            if any(label in window for label in labels) and _mentions_any(window, aliases):
                return True
    return False


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
        paragraph1 = re.sub(r"\s+", " ", str(entry.get("paragraph1") or "")).strip()
        paragraph2 = re.sub(r"\s+", " ", str(entry.get("paragraph2") or "")).strip()
        sources = entry.get("sources") or []

        p1_words = re.findall(r"\b[\w'-]+\b", paragraph1)
        p2_words = re.findall(r"\b[\w'-]+\b", paragraph2)
        if not 45 <= len(p1_words) <= 120:
            failures.append(f"{gid}: paragraph1 length {len(p1_words)} outside 45-120")
        if not 50 <= len(p2_words) <= 125:
            failures.append(f"{gid}: paragraph2 length {len(p2_words)} outside 50-125")
        if not 12 <= len(headline) <= 150:
            failures.append(f"{gid}: headline length invalid")

        combined = f"{headline} {paragraph1} {paragraph2}"
        low = combined.lower()
        for phrase in BANNED:
            if phrase in low:
                failures.append(f"{gid}: banned/template phrase '{phrase}'")

        row = rows[gid]
        away = str(row.get("away_team"))
        home = str(row.get("home_team"))
        pick = str(row.get("pick"))
        away_aliases = _team_aliases(away)
        home_aliases = _team_aliases(home)
        pick_aliases = _team_aliases(pick)

        if not _mentions_any(paragraph1, away_aliases) or not _mentions_any(paragraph1, home_aliases):
            failures.append(f"{gid}: paragraph1 must explain both teams")
        if "levline" not in paragraph2.lower():
            failures.append(f"{gid}: paragraph2 must explicitly explain LevLine")
        if not _mentions_any(paragraph2, pick_aliases):
            failures.append(f"{gid}: paragraph2 must identify the LevLine pick")

        final_prob = _pick_side_probability(row, "final_home_prob")
        pure_prob = _pick_side_probability(row, "pure_home_prob")
        market_prob = _pick_side_probability(row, "market_home_prob")
        if not _contains_pct(paragraph2, final_prob):
            failures.append(f"{gid}: paragraph2 missing LevLine pick probability")
        if pure_prob is not None and market_prob is not None:
            if "75" not in paragraph2 or "25" not in paragraph2:
                failures.append(f"{gid}: paragraph2 must explain the 75/25 blend")
            if not _contains_pct(paragraph2, pure_prob):
                failures.append(f"{gid}: paragraph2 missing PURE pick-side probability")
            if not _contains_pct(paragraph2, market_prob):
                failures.append(f"{gid}: paragraph2 missing market pick-side probability")
        if not _contains_labeled_line(
            paragraph2,
            row.get("expected_margin"),
            home,
            away,
            ("levline", "model", "project", "margin"),
        ):
            failures.append(f"{gid}: paragraph2 missing correct LevLine model line/projected margin")
        if not _contains_labeled_line(
            paragraph2,
            row.get("spread_line"),
            home,
            away,
            ("market", "spread", "consensus"),
        ):
            failures.append(f"{gid}: paragraph2 missing correct market spread")
        if not _contains_score(paragraph2, str(row.get("projected_score") or "")):
            failures.append(f"{gid}: paragraph2 missing projected score")

        expected_final = f"The pick: {_team_name(pick)} moneyline."
        if not paragraph2.endswith(expected_final):
            failures.append(f"{gid}: paragraph2 must end exactly with '{expected_final}'")

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
            "paragraph1": paragraph1,
            "paragraph2": paragraph2,
            "read": paragraph1 + "\n\n" + paragraph2,
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
    print(f"validated {len(cleaned)} two-paragraph Copilot Reads -> {args.output}")


if __name__ == "__main__":
    main()
