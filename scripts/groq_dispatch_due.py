from __future__ import annotations

"""Cheap, deterministic game-scoped gate for the autonomous Groq writer.

The dispatcher cannot claim Groq acceptance: only the downstream focused,
full-slate, provenance, and publication validators can do that. This gate only
decides whether a new provider run is justified. It never changes forecasts.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def _parse_utc(value: object) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if stamp.tzinfo is None:
        return None
    return stamp.astimezone(timezone.utc)


def assess_due(game_ids: list[str], provider: dict, source_status: dict, *, now_utc: datetime, maximum_age_hours: float = 36.0) -> tuple[bool, str]:
    """Return a conservative and explainable provider-refresh decision."""
    expected = set(game_ids)
    if not expected or len(expected) != len(game_ids) or any(not gid for gid in expected):
        raise ValueError("missing or duplicate canonical current-slate game IDs")
    if not isinstance(source_status, dict) or not _parse_utc(source_status.get("generated_utc")):
        raise ValueError("context source-status timestamp absent or invalid")
    if not isinstance(provider, dict):
        return True, "missing_provider_artifact"
    entries = provider.get("games")
    if not isinstance(entries, dict):
        return True, "missing_provider_game_map"
    actual = set(entries)
    if not expected.issubset(actual):
        return True, "missing_current_game_ids:" + ",".join(sorted(expected - actual))
    if any(not isinstance(entries[gid], dict) or not entries[gid].get("paragraph1") or not entries[gid].get("headline") for gid in expected):
        return True, "incomplete_current_human_layers"
    source = source_status.get("copilot_media") or {}
    if isinstance(source, dict) and (source.get("advisories") or {}):
        if expected.intersection(source["advisories"]):
            return True, "source_freshness_advisory"
    generated = _parse_utc(provider.get("generated_utc"))
    if generated is None:
        stamps = [_parse_utc(entries[gid].get("generated_utc")) for gid in expected]
        if any(stamp is None for stamp in stamps):
            return True, "missing_provider_timestamp"
        generated = min(stamps)
    elapsed = (now_utc - generated).total_seconds() / 3600
    if elapsed < -0.1:
        raise ValueError("provider artifact timestamp is in the future")
    if elapsed > maximum_age_hours:
        return True, f"editorial_refresh_due_age_hours:{elapsed:.1f}"
    return False, f"validated_current_human_layers_present:{len(expected)}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--provider", type=Path, default=Path("outputs/copilot_media_reads.json"))
    parser.add_argument("--status", type=Path, default=Path("outputs/context_source_status.json"))
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    try:
        with args.predictions.open(newline="", encoding="utf-8") as stream:
            game_ids = [str(row.get("game_id") or "").strip() for row in csv.DictReader(stream)]
        status = json.loads(args.status.read_text(encoding="utf-8"))
        provider = json.loads(args.provider.read_text(encoding="utf-8")) if args.provider.exists() else {}
        due, reason = assess_due(game_ids, provider, status, now_utc=datetime.now(timezone.utc))
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Editorial dispatcher fails closed on invalid canonical inputs: {exc}", file=sys.stderr)
        return 2
    print(f"due={str(due).lower()} reason={reason}")
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as stream:
            stream.write(f"due={str(due).lower()}\nreason={reason}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
