from __future__ import annotations

import argparse
import csv
from pathlib import Path


ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY = "2026-09-27"
ATS_HISTORICAL_BACKFILL_SEASON = "2026"
ATS_HISTORICAL_BACKFILL_WEEKS = frozenset({1, 2})
ATS_EDGE_EPSILON = 1e-12

_LOCK_RECEIPT_FIELDS = (
    "lock_status",
    "lock_timestamp_utc",
    "locked_model_spread",
    "locked_market_spread",
    "locked_edge",
    "closing_spread",
    "locked_ats_status",
    "locked_ats_pick_team",
    "locked_ats_pick_market_spread",
    "locked_ats_model_margin_home",
    "locked_ats_market_margin_home",
    "locked_ats_home_edge_points",
    "locked_ats_receipt_source",
)


def _value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def _number(row: dict[str, str], *keys: str) -> float | None:
    value = _value(row, *keys)
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _week(row: dict[str, str]) -> int | None:
    try:
        return int(float(_value(row, "week")))
    except (TypeError, ValueError):
        return None


def _historical_ats_backfill_eligible(row: dict[str, str]) -> bool:
    """Return whether this receipt belongs to the explicitly approved legacy cohort.

    Weeks 1-2 of the 2026 season predate the dedicated ``locked_ats_*`` schema, but
    their immutable pregame receipts already froze both ingredients used by today's
    ATS-side contract: the independent expected home margin and sportsbook home
    margin. Only that bounded cohort is reconstructed; Week 3 pre-policy receipts are
    intentionally left alone.
    """
    return (
        _value(row, "season") == ATS_HISTORICAL_BACKFILL_SEASON
        and _week(row) in ATS_HISTORICAL_BACKFILL_WEEKS
    )


def _ats_backfill_source(row: dict[str, str]) -> str:
    if _historical_ats_backfill_eligible(row):
        return "HISTORICAL_W1_W2_FROZEN_PREGAME_V1"
    gameday = _value(row, "gameday")[:10]
    if gameday and gameday >= ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY:
        return "POLICY_ERA_FROZEN_PREGAME_V1"
    return ""


def _backfill_ats_receipt(row: dict[str, str]) -> None:
    """Materialize an ATS receipt using only values frozen before kickoff.

    Dedicated ATS receipts are authoritative and are never rewritten. For 2026 Weeks
    1-2, which predate the dedicated ATS receipt schema, Sunday Signal now creates a
    provenance-marked historical receipt from the exact frozen ``expected_margin``
    and ``spread_line`` values. This is deterministic and outcome-blind: final scores,
    cover results, and later market data are never consulted.

    Sep. 27, 2026+ compatibility backfills remain supported for policy-era receipts
    created before the dedicated columns were deployed. Other pre-policy receipts,
    including Week 3 before Sep. 27, are not retroactively assigned an ATS side.
    """
    if _value(row, "locked_ats_status"):
        if not _value(row, "locked_ats_receipt_source"):
            row["locked_ats_receipt_source"] = "DEDICATED_LOCK_RECEIPT"
        return

    source = _ats_backfill_source(row)
    if not source:
        return
    row["locked_ats_receipt_source"] = source

    # Prefer explicit frozen aliases when present. Generic expected_margin/spread_line
    # are compatibility inputs from the same immutable pregame receipt.
    model_margin = _number(row, "locked_model_spread", "expected_margin")
    market_margin = _number(row, "locked_market_spread", "spread_line")
    home = _value(row, "home_team")
    away = _value(row, "away_team")

    if model_margin is not None:
        row["locked_ats_model_margin_home"] = str(model_margin)
    if market_margin is not None:
        row["locked_ats_market_margin_home"] = str(market_margin)

    if model_margin is None or market_margin is None or not home or not away:
        row["locked_ats_status"] = "UNAVAILABLE"
        return

    home_edge = model_margin - market_margin
    row["locked_ats_home_edge_points"] = str(home_edge)
    if abs(home_edge) <= ATS_EDGE_EPSILON:
        row["locked_ats_status"] = "NO_EDGE"
        return

    if home_edge > 0:
        row["locked_ats_pick_team"] = home
        row["locked_ats_pick_market_spread"] = str(-market_margin)
    else:
        row["locked_ats_pick_team"] = away
        row["locked_ats_pick_market_spread"] = str(market_margin)
    row["locked_ats_status"] = "VALUE"


def normalize_history_for_site(path: Path) -> None:
    """Add Sunday Signal receipt aliases without changing canonical history values.

    FINAL rows are immutable pregame receipts. The site gets explicit aliases for
    model/market values that existed at lock time. The bounded 2026 Week 1-2 legacy
    cohort also receives provenance-marked ATS receipts reconstructed solely from its
    frozen pregame inputs. Sep. 27, 2026+ receipts retain the policy-era compatibility
    migration. A closing spread is intentionally not inferred from the locked market
    line; it is populated only when an explicit closing-line field already exists.
    """
    if not path.exists():
        return

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames:
        return

    original_fields = set(fieldnames)
    for column in _LOCK_RECEIPT_FIELDS:
        if column not in fieldnames:
            fieldnames.append(column)

    for row in rows:
        is_final = str(row.get("snapshot_type", "")).strip().upper() == "FINAL"
        is_locked = str(row.get("lock_status", "")).strip().upper() == "LOCKED"
        if not is_final and not is_locked:
            continue

        if not _value(row, "lock_status"):
            row["lock_status"] = "LOCKED"
        if not _value(row, "lock_timestamp_utc"):
            row["lock_timestamp_utc"] = _value(row, "prediction_timestamp_utc")

        if not _value(row, "locked_model_spread"):
            row["locked_model_spread"] = _value(row, "expected_margin")
        if not _value(row, "locked_market_spread"):
            row["locked_market_spread"] = _value(row, "spread_line")
        if not _value(row, "locked_edge"):
            row["locked_edge"] = _value(row, "model_edge")

        _backfill_ats_receipt(row)

        # Closing line is a separate post-lock concept. Never manufacture it
        # from spread_line/locked_market_spread. Only carry a genuinely explicit
        # close field supplied by a newer canonical producer.
        if not _value(row, "closing_spread"):
            explicit_close_keys = tuple(
                key
                for key in ("closing_spread_line", "close_spread", "close_spread_line")
                if key in original_fields
            )
            if explicit_close_keys:
                row["closing_spread"] = _value(row, *explicit_close_keys)

    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize immutable history fields for Sunday Signal only.")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    normalize_history_for_site(args.path)


if __name__ == "__main__":
    main()
