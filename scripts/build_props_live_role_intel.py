from __future__ import annotations

"""Build point-in-time live lineup intelligence for LevLine Props Research Beta."""

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_live_role_intel import (  # noqa: E402
    build_live_role_intelligence,
    validate_live_role_intelligence,
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _load_optional(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return _load_object(path)


def _write_new(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen live-role artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconcile LevLine shared news/injury intelligence with live Props market role evidence."
    )
    parser.add_argument("--player-state", type=Path, required=True)
    parser.add_argument("--market-snapshot", type=Path, required=True)
    parser.add_argument(
        "--contextual-evidence",
        type=Path,
        default=ROOT / "outputs" / "contextual_evidence.json",
    )
    parser.add_argument(
        "--media-reads",
        type=Path,
        default=ROOT / "outputs" / "copilot_media_reads.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    state_payload = _load_object(args.player_state)
    player_state = state_payload.get("player_state")
    if not isinstance(player_state, list) or not player_state:
        raise ValueError("player-state snapshot must contain a non-empty player_state list")

    market_payload = _load_object(args.market_snapshot)
    market_artifacts = market_payload.get("market_artifacts")
    captured_at = market_payload.get("captured_at_utc")
    if not isinstance(market_artifacts, list):
        raise ValueError("market snapshot must contain market_artifacts")
    if not captured_at:
        raise ValueError("market snapshot must contain captured_at_utc")

    payload = build_live_role_intelligence(
        player_state_rows=player_state,
        market_artifacts=market_artifacts,
        market_captured_at_utc=captured_at,
        contextual_evidence=_load_optional(args.contextual_evidence),
        media_reads=_load_optional(args.media_reads),
    )
    validate_live_role_intelligence(payload)
    _write_new(args.output, payload)

    resolved = int(payload.get("audit", {}).get("resolved_team_qbs", 0))
    conflicts = int(payload.get("audit", {}).get("blocking_conflict_count", 0))
    print(
        f"frozen live Props role intelligence -> {args.output} "
        f"(resolved_team_qbs={resolved}, blocking_conflicts={conflicts})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
