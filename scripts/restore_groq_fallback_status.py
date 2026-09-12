from __future__ import annotations

"""Restore current-run Groq fallback provenance after a safe main reconciliation.

A long Groq writer run may accumulate per-game fallback status in
``outputs/context_source_status.json`` before ``main`` advances with deterministic
forecast outputs. The reconciliation path deliberately resets to latest ``main`` before
re-rendering canonical LevLine facts. That reset must not erase which game-specific
provider calls failed and still require fresh ChatGPT research.

This helper copies only the ``groq_provider_fallback`` section from the pre-reset status
snapshot into the latest-main status file. All other status sections remain owned by the
newer main snapshot. It is editorial provenance only and never touches forecast/model
inputs, probabilities, locks, grading, or research outputs.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

SECTION = "groq_provider_fallback"


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def restore_fallback_status(
    saved: dict[str, Any],
    current: dict[str, Any],
    *,
    expected_run_id: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """Return current status with only current-run fallback provenance restored."""
    section = saved.get(SECTION)
    if section is None:
        return dict(current), False
    if not isinstance(section, dict):
        raise ValueError(f"saved {SECTION} must be an object")

    run_id = str(section.get("run_id") or "").strip()
    if not run_id:
        raise ValueError(f"saved {SECTION} is missing run_id")
    if expected_run_id is not None and run_id != str(expected_run_id):
        raise ValueError(
            f"saved {SECTION} run_id {run_id!r} does not match current run {str(expected_run_id)!r}"
        )

    games = section.get("games")
    if not isinstance(games, dict):
        raise ValueError(f"saved {SECTION}.games must be an object")
    for game_id, entry in games.items():
        if not str(game_id).strip() or not isinstance(entry, dict):
            raise ValueError(f"saved {SECTION}.games contains an invalid entry")
        if entry.get("provider_result") != "failed":
            raise ValueError(f"saved {SECTION}.games[{game_id!r}] is not a failed-provider receipt")
        if "requires_chatgpt_refresh" not in entry:
            raise ValueError(
                f"saved {SECTION}.games[{game_id!r}] is missing requires_chatgpt_refresh"
            )

    result = dict(current)
    # JSON round-trip produces a detached plain-data copy and avoids aliasing test data.
    result[SECTION] = json.loads(json.dumps(section))
    return result, True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--saved", required=True)
    parser.add_argument("--current", default="outputs/context_source_status.json")
    args = parser.parse_args()

    saved_path = Path(args.saved)
    current_path = Path(args.current)
    saved = _load(saved_path)
    current = _load(current_path)
    expected_run_id = str(os.environ.get("GITHUB_RUN_ID") or "").strip() or None
    restored, changed = restore_fallback_status(
        saved,
        current,
        expected_run_id=expected_run_id,
    )
    if changed:
        current_path.write_text(
            json.dumps(restored, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            "Restored current-run Groq failed-game fallback provenance after main reconciliation."
        )
    else:
        print("No Groq fallback provenance existed before reconciliation; nothing to restore.")


if __name__ == "__main__":
    main()
