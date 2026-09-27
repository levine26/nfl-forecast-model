from __future__ import annotations

import argparse
import csv
from pathlib import Path


ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY = "2026-09-27"
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


def _backfill_ats_receipt(row: dict[str, str]) -> None:
    """Add ATS lock aliases using only values frozen in this exact receipt.

    This is a site-compatibility migration, not a reforecast. It never consults a
    later market snapshot or game result. The policy applies only to Sep. 27,
    2026+ receipts because winner/ATS decoupling was live from that slate onward.
    """
    gameday = _value(row, "gameday")[:10]
    if not gameday or gameday < ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY:
        return
    if _value(row, "locked_ats_status"):
        return

    model_margin = _number(row, "expected_margin", "locked_model_spread")
    market_margin = _number(row, "spread_line", "locked_market_spread")
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
    model/market values that existed at lock time. For Sep. 27, 2026+ receipts it
    also materializes the model-selected ATS side and exact sportsbook spread from
    those same frozen inputs. A closing spread is intentionally not inferred from
    the locked market line; it is populated only when an explicit closing-line
    field already exists.
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

        # Canonical prediction_history uses expected_margin, spread_line and
        # model_edge for the values captured in the immutable FINAL snapshot.
        # Preserve any newer explicit aliases if they are already present.
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
