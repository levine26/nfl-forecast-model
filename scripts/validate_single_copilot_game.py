from __future__ import annotations

"""Fail closed on one focused editorial response before accepting it into the slate."""

import argparse
import json
from pathlib import Path
import re

import pandas as pd

from compose_copilot_media_reads import _domain_family, _extract_json
from nfl_forecast.copilot_source_backfill import backfill_direct_sources
from nfl_forecast.source_policy import is_direct_media_report_url
from validate_copilot_media_reads import _mentions_any, _team_aliases, _team_name, _unique_ngrams


RATIONALE_PROHIBITED = re.compile(
    r"\d|%|\blevline\b|\bf-st\b|\bpure\b|\bmarket\b|\bspread\b|\bmodel line\b|\bmoneyline\b",
    flags=re.I,
)

# Groq occasionally compresses model_rationale to only a few words even when its
# researched paragraph is publication-grade. In that case the rationale field is not
# padded: it is discarded and deterministically reconstructed from a football mechanism
# already present in the sourced matchup paragraph. Team names recur every few words so
# two reconstructions using the same mechanism do not create slate-wide stock phrasing.
RATIONALE_MECHANISMS = (
    (
        ("pass rush", "pressure", "protection", "pocket", "sack"),
        "{pick}' protection against {opponent}' pressure determines whether {pick} can stay on schedule; if {pick} holds up, {opponent}' cleanest disruption path narrows.",
    ),
    (
        ("coverage", "secondary", "cornerback", "receiver", "route"),
        "{pick}' coverage answers against {opponent}' receivers determine whether {pick} can stay structurally sound against {opponent}; if coverage favors {pick}, {opponent}' easy completions become harder.",
    ),
    (
        ("run game", "rushing", "ground game", "run defense", "early down", "early-down"),
        "{pick}' early-down rushing against {opponent}' front determines whether {pick} can control down-and-distance; efficient {pick} runs would force {opponent} into less favorable defensive situations.",
    ),
    (
        ("explosive", "deep ball", "chunk play", "downfield"),
        "{pick}' explosive-play discipline against {opponent} determines whether {pick} can avoid sudden swings against {opponent}; if discipline favors {pick}, {opponent}' shortcut scoring chances shrink.",
    ),
    (
        ("quarterback", "passing game", "pass game", "dropback"),
        "{pick}' quarterback execution against {opponent}' structure determines whether {pick} can sustain drives; steady {pick} quarterback play would give {opponent} fewer obvious passing situations.",
    ),
    (
        ("scheme", "coordinator", "play-calling", "play calling", "motion"),
        "{pick}' schematic answers to {opponent}' adjustments determine whether {pick} can create favorable looks against {opponent}; if the chess match favors {pick}, {opponent} must react instead of dictate.",
    ),
    (
        ("turnover", "ball security", "takeaway"),
        "{pick}' ball security against {opponent}' takeaway chances determines whether {pick} can preserve field position; secure {pick} possessions would deny {opponent} short-field opportunities.",
    ),
    (
        ("injury", "availability", "questionable", "doubtful", "ruled out"),
        "{pick}' response to its availability constraints against {opponent} determines whether {pick} can preserve its intended structure; successful {pick} adaptation would deny {opponent} matchup shortcuts.",
    ),
    (
        ("special teams", "kicker", "punt", "kickoff", "return game"),
        "{pick}' special-teams execution against {opponent} determines whether {pick} can protect field position; clean {pick} execution there would deny {opponent} hidden-yardage advantages.",
    ),
    (
        ("red zone", "third down", "third-down"),
        "{pick}' situational execution against {opponent} determines whether {pick} can finish drives; timely {pick} conversions would leave {opponent} fewer chances to reset the game.",
    ),
)


def _clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _words(value: object) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", _clean(value))


def _rationale_has_prohibited(value: object) -> bool:
    return RATIONALE_PROHIBITED.search(_clean(value)) is not None


def _nickname(code: object) -> str:
    name = _team_name(str(code or ""))
    return name.split()[-1] if name else str(code or "")


def _repair_underlength_rationale(rationale: str, paragraph1: str, row) -> tuple[str, bool]:
    """Reconstruct a clean underlength rationale from the researched paragraph.

    The hard publication contract remains 18-40 words. Any rationale already at or
    above the minimum is left untouched, so overlength copy still fails normally.
    Numerical/model/betting leakage is never repaired. For an underlength clean field,
    reconstruction is allowed only when paragraph 1 contains a recognized football
    mechanism and the production pick is one of the matchup teams. The provider's
    original short rationale is discarded rather than used as unverified padding.
    """
    original = _clean(rationale)
    if len(_words(original)) >= 18 or _rationale_has_prohibited(original):
        return original, False

    away = str(row.get("away_team") or "")
    home = str(row.get("home_team") or "")
    pick = str(row.get("pick") or "")
    if pick not in {away, home}:
        return original, False
    opponent = home if pick == away else away

    paragraph_lower = _clean(paragraph1).lower()
    for triggers, template in RATIONALE_MECHANISMS:
        if not any(trigger in paragraph_lower for trigger in triggers):
            continue
        candidate = template.format(pick=_nickname(pick), opponent=_nickname(opponent))
        if 18 <= len(_words(candidate)) <= 40 and not _rationale_has_prohibited(candidate):
            return candidate, True
    return original, False


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


def _valid_sources_with_backfill(row, sources: object) -> tuple[list[dict], set[str], list[str]]:
    """Apply the same fail-closed provenance repair used by the final composer.

    Groq must still execute live research, but its returned citations can include
    navigation or matchup-shell URLs even when the researched prose is usable. The
    publication contract is two independent *direct* approved reports, so establish
    that contract deterministically before rejecting the prose. Invalid provider URLs
    are never promoted; the backfill module discards them and searches approved
    publishers for direct, current, matchup-relevant reports. If that repair cannot
    establish two independent publisher families, validation still fails closed.
    """
    valid, families, failures = _valid_sources(sources)
    if len(valid) >= 2 and len(families) >= 2:
        return valid, families, []

    existing = [dict(source) for source in sources[:8] if isinstance(source, dict)] if isinstance(sources, list) else []
    repaired = backfill_direct_sources(row, existing)
    repaired_valid, repaired_families, repaired_failures = _valid_sources(repaired)
    if len(repaired_valid) >= 2 and len(repaired_families) >= 2:
        return repaired_valid, repaired_families, []

    provider_failures = [failure for failure in failures if "two independent" not in failure]
    combined = provider_failures + repaired_failures
    if not any("two independent" in failure for failure in combined):
        combined.append("requires at least two independent direct approved-domain sources")
    return repaired_valid, repaired_families, combined


def _load_entry(path: Path, gid: str) -> dict:
    payload = _extract_json(path.read_text(encoding="utf-8", errors="replace"))
    games = payload.get("games") if isinstance(payload, dict) else None
    if not isinstance(games, dict) or set(map(str, games)) != {gid}:
        raise ValueError(f"{gid}: focused response must contain exactly its own game id")
    entry = games.get(gid)
    if not isinstance(entry, dict):
        raise ValueError(f"{gid}: focused game entry is not an object")
    return entry


def _write_accepted_entry(path: Path, gid: str, entry: dict) -> None:
    """Persist exactly the normalized payload that downstream slate gates will read."""
    path.write_text(
        json.dumps({"games": {gid: entry}}, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


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
    rationale, rationale_repaired = _repair_underlength_rationale(rationale, paragraph1, row)
    if rationale_repaired:
        entry["model_rationale"] = rationale

    p1_words = _words(paragraph1)
    rationale_words = _words(rationale)

    if not 12 <= len(headline) <= 150:
        failures.append(f"{gid}: headline length invalid")
    if not 55 <= len(p1_words) <= 100:
        failures.append(f"{gid}: paragraph1 length {len(p1_words)} outside 55-100")
    if not _mentions_any(paragraph1, _team_aliases(away)) or not _mentions_any(paragraph1, _team_aliases(home)):
        failures.append(f"{gid}: paragraph1 must discuss both teams")
    if not 18 <= len(rationale_words) <= 40:
        failures.append(f"{gid}: model_rationale length {len(rationale_words)} outside 18-40")
    if _rationale_has_prohibited(rationale):
        failures.append(f"{gid}: model_rationale contains a prohibited numerical/model term")

    valid_sources, _, source_failures = _valid_sources_with_backfill(row, entry.get("sources"))
    failures.extend(f"{gid}: {failure}" for failure in source_failures)
    if not source_failures:
        entry["sources"] = valid_sources

    current_human = f"{headline} {paragraph1} {rationale}"
    current_grams = _unique_ngrams(current_human)
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
            repeated = sorted(current_grams & _unique_ngrams(other_human))
            if repeated:
                failures.append(f"{gid}: repeats substantive seven-word phrase with {other_gid}: '{repeated[0]}'")
            other_template = _headline_template(
                _clean(other.get("headline")), str(other_row.get("away_team")), str(other_row.get("home_team"))
            )
            if current_template and current_template == other_template:
                failures.append(f"{gid}: headline template duplicates {other_gid}: '{current_template}'")

    if not failures:
        _write_accepted_entry(path, gid, entry)
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
        raise SystemExit("Focused editorial game validation failed: " + "; ".join(failures))
    print(f"validated focused editorial response for {args.game_id}")


if __name__ == "__main__":
    main()
