from __future__ import annotations

import argparse
import csv
from pathlib import Path


_LOCK_RECEIPT_FIELDS = (
    "lock_status",
    "lock_timestamp_utc",
    "locked_model_spread",
    "locked_market_spread",
    "locked_edge",
    "closing_spread",
)


def _value(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def normalize_history_for_site(path: Path) -> None:
    """Add Sunday Signal receipt aliases without changing canonical history values.

    FINAL rows are immutable pregame receipts.  The site gets explicit aliases for
    the model spread, market spread, and edge that existed at lock time.  A
    closing spread is intentionally *not* inferred from the locked market line;
    it is populated only when an explicit closing-line field already exists.
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
        if not is_final:
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

        # Closing line is a separate post-lock concept.  Never manufacture it
        # from spread_line/locked_market_spread.  Only carry a genuinely explicit
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
