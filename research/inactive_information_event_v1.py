from __future__ import annotations

"""Build a research-only inactive-information event ledger.

This module deliberately does not estimate a football-to-probability mapping. It aligns a
point-in-time pre/post expected-lineup state with a point-in-time pre/post market state around
an authoritative inactive-information event and reports the two changes separately.

It is outcome-blind, preserves missingness, fails closed on chronology/provenance violations,
and cannot modify a production forecast.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "levline-inactive-information-event-v1"
ALLOWED_TIMESTAMP_BASES = {"published_at", "captured_at"}


def _parse_utc(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing required timestamp: {field}")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp for {field}: {text}") from exc
    if dt.tzinfo is None:
        raise ValueError(f"timestamp must be timezone-aware: {field}")
    return dt.astimezone(timezone.utc)


def _float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc
    if not math.isfinite(out):
        raise ValueError(f"non-finite numeric value: {value!r}")
    return out


def _probability(value: Any, field: str) -> float | None:
    out = _float(value)
    if out is None:
        return None
    if not 0.0 < out < 1.0:
        raise ValueError(f"{field} must be strictly between 0 and 1")
    return out


def _minutes(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds() / 60.0


def _sha256_identity(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError("inactive_raw_sha256 must be a 64-character lowercase hex digest")
    return text


def derive_inactive_event_row(row: dict[str, Any]) -> dict[str, Any]:
    """Validate one event and derive outcome-blind pre/post change measurements."""

    game_id = str(row.get("game_id") or "").strip()
    event_id = str(row.get("event_id") or "").strip()
    if not game_id or not event_id:
        raise ValueError("game_id and event_id are required")

    timestamp_basis = str(row.get("inactive_timestamp_basis") or "").strip()
    if timestamp_basis not in ALLOWED_TIMESTAMP_BASES:
        raise ValueError(
            f"inactive_timestamp_basis must be one of {sorted(ALLOWED_TIMESTAMP_BASES)}"
        )

    source = str(row.get("inactive_source") or "").strip()
    source_url_or_id = str(row.get("inactive_source_url_or_id") or "").strip()
    if not source or not source_url_or_id:
        raise ValueError("inactive source name and source URL/id are required")
    raw_sha = _sha256_identity(row.get("inactive_raw_sha256"))

    kickoff = _parse_utc(row.get("kickoff_timestamp_utc"), "kickoff_timestamp_utc")
    event_at = _parse_utc(row.get("inactive_event_at_utc"), "inactive_event_at_utc")
    pre_lineup_at = _parse_utc(row.get("pre_lineup_asof_utc"), "pre_lineup_asof_utc")
    post_lineup_at = _parse_utc(row.get("post_lineup_asof_utc"), "post_lineup_asof_utc")
    pre_market_at = _parse_utc(row.get("pre_market_asof_utc"), "pre_market_asof_utc")
    post_market_at = _parse_utc(row.get("post_market_asof_utc"), "post_market_asof_utc")

    if event_at >= kickoff:
        raise ValueError("inactive event must precede kickoff")
    if pre_lineup_at > event_at:
        raise ValueError("pre-lineup state must be known no later than inactive event")
    if post_lineup_at < event_at or post_lineup_at >= kickoff:
        raise ValueError("post-lineup state must be at/after event and before kickoff")
    if pre_market_at > event_at:
        raise ValueError("pre-market state must be known no later than inactive event")
    if post_market_at < event_at or post_market_at >= kickoff:
        raise ValueError("post-market state must be at/after event and before kickoff")
    if post_lineup_at < pre_lineup_at or post_market_at < pre_market_at:
        raise ValueError("post state cannot precede corresponding pre state")

    home_pre = _float(row.get("home_expected_lineup_value_pre"))
    home_post = _float(row.get("home_expected_lineup_value_post"))
    away_pre = _float(row.get("away_expected_lineup_value_pre"))
    away_post = _float(row.get("away_expected_lineup_value_post"))
    market_pre = _probability(row.get("market_home_prob_pre"), "market_home_prob_pre")
    market_post = _probability(row.get("market_home_prob_post"), "market_home_prob_post")

    lineup_complete = None not in {home_pre, home_post, away_pre, away_post}
    market_complete = market_pre is not None and market_post is not None
    complete = bool(lineup_complete and market_complete)

    output: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "event_id": event_id,
        "home_team": row.get("home_team"),
        "away_team": row.get("away_team"),
        "kickoff_timestamp_utc": kickoff.isoformat().replace("+00:00", "Z"),
        "inactive_event_at_utc": event_at.isoformat().replace("+00:00", "Z"),
        "inactive_timestamp_basis": timestamp_basis,
        "inactive_source": source,
        "inactive_source_url_or_id": source_url_or_id,
        "inactive_raw_sha256": raw_sha,
        "pre_lineup_asof_utc": pre_lineup_at.isoformat().replace("+00:00", "Z"),
        "post_lineup_asof_utc": post_lineup_at.isoformat().replace("+00:00", "Z"),
        "pre_market_asof_utc": pre_market_at.isoformat().replace("+00:00", "Z"),
        "post_market_asof_utc": post_market_at.isoformat().replace("+00:00", "Z"),
        "minutes_event_to_kickoff": _minutes(kickoff, event_at),
        "minutes_event_to_post_lineup_state": _minutes(post_lineup_at, event_at),
        "minutes_event_to_post_market_state": _minutes(post_market_at, event_at),
        "lineup_state_complete": bool(lineup_complete),
        "market_state_complete": bool(market_complete),
        "complete_event_measurement": complete,
        "research_only": True,
        "production_authorized": False,
        "probability_feature_authorized": False,
        "football_to_probability_mapping_authorized": False,
        "completed_2026_outcomes_used": 0,
    }

    if lineup_complete:
        assert home_pre is not None and home_post is not None
        assert away_pre is not None and away_post is not None
        home_change = home_post - home_pre
        away_change = away_post - away_pre
        output.update(
            {
                "home_expected_lineup_value_pre": home_pre,
                "home_expected_lineup_value_post": home_post,
                "away_expected_lineup_value_pre": away_pre,
                "away_expected_lineup_value_post": away_post,
                "home_lineup_value_change": home_change,
                "away_lineup_value_change": away_change,
                "net_home_lineup_shock_native_units": home_change - away_change,
            }
        )
    else:
        output.update(
            {
                "home_expected_lineup_value_pre": home_pre,
                "home_expected_lineup_value_post": home_post,
                "away_expected_lineup_value_pre": away_pre,
                "away_expected_lineup_value_post": away_post,
                "home_lineup_value_change": None,
                "away_lineup_value_change": None,
                "net_home_lineup_shock_native_units": None,
            }
        )

    if market_complete:
        assert market_pre is not None and market_post is not None
        output.update(
            {
                "market_home_prob_pre": market_pre,
                "market_home_prob_post": market_post,
                "market_home_probability_move_pp": (market_post - market_pre) * 100.0,
            }
        )
    else:
        output.update(
            {
                "market_home_prob_pre": market_pre,
                "market_home_prob_post": market_post,
                "market_home_probability_move_pp": None,
            }
        )

    # Intentionally absent: implied probability delta from player information, residual edge,
    # direction recommendation, outcome label, or any forecast mutation.
    return output


def derive_inactive_events(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for raw in rows:
        derived = derive_inactive_event_row(dict(raw))
        identity = (str(derived["game_id"]), str(derived["event_id"]))
        if identity in seen:
            raise ValueError(f"duplicate inactive event identity: {identity}")
        seen.add(identity)
        output.append(derived)

    complete = sum(int(row["complete_event_measurement"]) for row in output)
    audit = {
        "schema_version": SCHEMA_VERSION,
        "rows": len(output),
        "complete_event_measurements": complete,
        "incomplete_event_measurements": len(output) - complete,
        "measurement_contract": {
            "lineup_change_units": "native_expected_lineup_value_only",
            "market_change_units": "home_win_probability_percentage_points",
            "football_to_probability_mapping": "not_authorized",
            "missingness_policy": "preserve_missing_no_imputation",
            "chronology_policy": "strict_pre_event_and_post_event_states_before_kickoff",
        },
        "outcome_blind": True,
        "research_only": True,
        "production_authorized": False,
        "probability_feature_authorized": False,
        "completed_2026_outcomes_used": 0,
        "promotion_authorized": False,
    }
    return output, audit


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    rows, audit = derive_inactive_events(_read_csv(args.input))
    _write_csv(args.output, rows)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
