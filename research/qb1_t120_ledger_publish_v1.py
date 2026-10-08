"""Fail-closed archival reconciliation for Candidate 4 QB1 T-120 research rows.

Only writes the QB1 CSV in an isolated research-data Git worktree. Preserves
old file bytes and never changes existing game records, model or official picks.
This DOES NOT independently authenticate prospective capture timestamps.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil

ID = "ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1"
REQUIRED = {
    "game_id", "qb1_snapshot_sha256", "candidate_id", "captured_at_utc",
    "t120_target_utc", "kickoff_utc", "research_only",
    "production_authorized", "completed_2026_outcomes_used",
}
SHA = re.compile(r"^[0-9a-f]{64}$")


def _read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Missing nonempty QB1 ledger: {path}")
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        if not fields or not REQUIRED.issubset(fields) or len(fields) != len(set(fields)):
            raise ValueError("QB1 snapshot ledger schema mismatch")
        rows = list(reader)
    known = set()
    for row in rows:
        game_id, digest = row.get("game_id"), row.get("qb1_snapshot_sha256")
        if (not game_id or game_id in known or not digest or not SHA.fullmatch(digest)
            or None in row or any(value is None for value in row.values())):
            raise ValueError("Duplicate, malformed, or unhashed QB1 snapshot")
        known.add(game_id)
        if (row["candidate_id"] != ID or row["research_only"].lower() != "true"
            or row["production_authorized"].lower() != "false"
            or row["completed_2026_outcomes_used"] != "0"):
            raise ValueError("QB1 ledger must remain research-only and outcome-blind")
        try:
            ko = datetime.fromisoformat(row["kickoff_utc"].replace("Z", "+00:00"))
            cap = datetime.fromisoformat(row["captured_at_utc"].replace("Z", "+00:00"))
            target = datetime.fromisoformat(row["t120_target_utc"].replace("Z", "+00:00"))
            if (not all(t.tzinfo is not None and t.utcoffset() is not None for t in (ko,cap,target))
                or cap > target or target >= ko):
                raise ValueError("Invalid T-120 chronology")
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid QB1 T-120 timestamp evidence") from exc
    return list(fields), rows


def reconcile_qb1_ledger(destination: Path, incoming: Path) -> dict:
    """Append only novel game IDs. Old rows and unrelated branch files stay intact.

    Called again against the latest remote parent after a rejected push;
    no new capture clock is fabricated and no prior row is replaced.
    """
    destination = Path(destination)
    incoming = Path(incoming)
    fields, source_rows = _read(incoming)
    if not source_rows:
        raise ValueError("No QB1 rows in pending research evidence")
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(incoming, destination)
        return {"added":len(source_rows), "existing":0}
    old_fields, old_rows = _read(destination)
    if fields != old_fields:
        raise ValueError("QB1 ledger column/ordering drift; no automatic repair")
    old = {row["game_id"]: row for row in old_rows}
    additions = []
    for row in source_rows:
        prior = old.get(row["game_id"])
        if prior is not None:
            if prior != row:
                raise ValueError(f"Immutable QB1 T-120 conflict: {row['game_id']}")
        else:
            additions.append(row)
    if additions:
        if not destination.read_bytes().endswith(b"\n"):
            raise ValueError("Existing QB1 ledger has no final newline")
        with destination.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writerows(additions)
            f.flush()
            os.fsync(f.fileno())
    return {"added":len(additions), "existing":len(old_rows)}
