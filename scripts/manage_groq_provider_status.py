from __future__ import annotations

"""Manage game-scoped Groq provider status across a long editorial run.

The provider writer may spend many minutes researching a slate while another production
workflow advances deterministic forecast outputs on ``main``. Reconciliation resets the
worktree to latest ``origin/main``; this helper makes the current run's provider-failure
ledger an explicit ephemeral artifact that can be restored after that reset.

This is editorial status only. It never reads or changes LevLine probabilities, model
artifacts, locks, grading, market data, or provider prose.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_STATUS = Path("outputs/context_source_status.json")
SECTION = "groq_provider_fallback"
POLICY = (
    "Groq failures are game-specific; successful Groq games remain authoritative and "
    "failed games use validated ChatGPT/last-good editorial fallback."
)


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"status file must contain a JSON object: {path}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def current_run_id(value: str | None = None) -> str:
    run_id = str(value or os.environ.get("GITHUB_RUN_ID") or "local").strip()
    if not run_id:
        raise ValueError("Groq provider run id is blank")
    return run_id


def initialize(status_path: Path, *, run_id: str | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Start a fresh provider ledger so older failed-game flags cannot leak forward."""
    status = _load(status_path)
    rid = current_run_id(run_id)
    stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    section = {
        "run_id": rid,
        "status": "healthy",
        "games": {},
        "failed_games": [],
        "started_at_utc": stamp,
        "policy": POLICY,
    }
    status[SECTION] = section
    _write(status_path, status)
    return section


def snapshot(status_path: Path, output_path: Path, *, run_id: str | None = None) -> dict[str, Any]:
    """Persist only the current run's provider ledger before a worktree reset."""
    status = _load(status_path)
    section = status.get(SECTION)
    rid = current_run_id(run_id)
    if not isinstance(section, dict) or str(section.get("run_id")) != rid:
        raise ValueError(f"current Groq provider status for run {rid} is missing")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(section, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return section


def restore(status_path: Path, input_path: Path, *, run_id: str | None = None) -> dict[str, Any]:
    """Merge the saved current-run ledger into latest-main contextual status."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Groq provider status snapshot missing: {input_path}")
    section = json.loads(input_path.read_text(encoding="utf-8"))
    rid = current_run_id(run_id)
    if not isinstance(section, dict) or str(section.get("run_id")) != rid:
        raise ValueError(f"Groq provider status snapshot does not belong to run {rid}")
    status = _load(status_path)
    status[SECTION] = section
    _write(status_path, status)
    return section


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init")
    init_parser.add_argument("--status", default=str(DEFAULT_STATUS))

    snapshot_parser = sub.add_parser("snapshot")
    snapshot_parser.add_argument("--status", default=str(DEFAULT_STATUS))
    snapshot_parser.add_argument("--output", required=True)

    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("--status", default=str(DEFAULT_STATUS))
    restore_parser.add_argument("--input", required=True)

    args = parser.parse_args()
    if args.command == "init":
        section = initialize(Path(args.status))
        print(f"initialized Groq provider status for run {section['run_id']}")
    elif args.command == "snapshot":
        section = snapshot(Path(args.status), Path(args.output))
        print(f"snapshotted Groq provider status for run {section['run_id']}")
    else:
        section = restore(Path(args.status), Path(args.input))
        print(f"restored Groq provider status for run {section['run_id']}")


if __name__ == "__main__":
    main()
