from __future__ import annotations

import argparse
import csv
from pathlib import Path


def normalize_history_for_site(path: Path) -> None:
    """Add Sunday Signal compatibility fields without mutating canonical history semantics."""
    if not path.exists():
        return

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not fieldnames:
        return

    for column in ("lock_status", "lock_timestamp_utc"):
        if column not in fieldnames:
            fieldnames.append(column)

    for row in rows:
        is_final = str(row.get("snapshot_type", "")).strip().upper() == "FINAL"
        if is_final and not str(row.get("lock_status", "")).strip():
            row["lock_status"] = "LOCKED"
        if is_final and not str(row.get("lock_timestamp_utc", "")).strip():
            row["lock_timestamp_utc"] = str(row.get("prediction_timestamp_utc", "")).strip()

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
