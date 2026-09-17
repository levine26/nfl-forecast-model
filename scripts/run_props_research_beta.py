from __future__ import annotations

"""Produce LevLine Props Research Beta artifacts from frozen lane handoffs.

This coordinator is research-only. It does not fetch live sportsbook data, does not
mutate winner probabilities, and never feeds market information into the pure simulation.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.challenger_props_simulation import (  # noqa: E402
    build_game_input_from_upstream,
    simulate_game,
)
from nfl_forecast.props_integration import build_forecast_artifact  # noqa: E402
from nfl_forecast.props_publication import (  # noqa: E402
    append_jsonl_immutable,
    build_public_props,
    make_forecast_receipt,
)


def _load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"missing integration manifest: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("integration manifest must be a JSON object")
    return payload


def _required(payload: dict, key: str):
    if key not in payload:
        raise ValueError(f"integration manifest missing required field: {key}")
    return payload[key]


def _aware(value: object, label: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def produce(
    payload: dict,
    *,
    output: Path,
    public_output: Path | None,
    history_ledger: Path,
) -> dict:
    forecast_timestamp = _aware(
        _required(payload, "forecast_timestamp_utc"), "forecast_timestamp_utc"
    )
    kickoff = _aware(_required(payload, "kickoff_utc"), "kickoff_utc")
    if forecast_timestamp >= kickoff:
        raise ValueError("forecast_timestamp_utc must be before kickoff_utc")

    game = build_game_input_from_upstream(
        home_team=str(_required(payload, "home_team")),
        away_team=str(_required(payload, "away_team")),
        opportunity_projections=_required(payload, "opportunity_projections"),
        efficiency_player_parameters=_required(payload, "efficiency_player_parameters"),
        team_td_parameters=_required(payload, "team_td_parameters"),
        residual_efficiency_by_team=_required(payload, "residual_efficiency_by_team"),
        model_version=str(
            payload.get("model_version") or "levline-props-simulation-v0.1.0"
        ),
        shared_pace_correlation=float(payload.get("shared_pace_correlation", 0.0)),
        shared_scoring_log_sd=float(payload.get("shared_scoring_log_sd", 0.0)),
        pass_rate_game_script_sensitivity=float(
            payload.get("pass_rate_game_script_sensitivity", 0.0)
        ),
    )
    result = simulate_game(
        game,
        simulations=int(payload.get("simulations", 20_000)),
        seed=int(payload.get("seed", 0)),
    )
    artifact = build_forecast_artifact(
        result,
        _required(payload, "market_artifacts"),
        kickoff_utc=kickoff,
        forecast_timestamp_utc=forecast_timestamp,
        interval_level=float(payload.get("prediction_interval_level", 0.80)),
    )
    public = (
        build_public_props(artifact, now_utc=datetime.now(timezone.utc))
        if public_output is not None
        else None
    )

    recorded = datetime.now(timezone.utc)
    receipts = [
        make_forecast_receipt(row, recorded_utc=recorded)
        for row in artifact["forecasts"]
    ]
    append_jsonl_immutable(
        history_ledger, receipts, identity_key="forecast_id"
    )

    # Publish only after every original receipt has passed immutable-history validation.
    _write_json(output, artifact)
    if public_output is not None and public is not None:
        _write_json(public_output, public)

    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the integrated LevLine Props Research Beta from frozen lane artifacts."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "props" / "forecasts.json",
    )
    parser.add_argument(
        "--public-output",
        type=Path,
        default=ROOT / "outputs" / "props" / "public_props.json",
    )
    parser.add_argument(
        "--history-ledger",
        type=Path,
        default=ROOT / "outputs" / "props" / "history" / "forecast_originals.jsonl",
    )
    args = parser.parse_args()
    artifact = produce(
        _load(args.input),
        output=args.output,
        public_output=args.public_output,
        history_ledger=args.history_ledger,
    )
    print(
        f"wrote {len(artifact['forecasts'])} Props Research Beta forecasts -> {args.output}"
    )
    print(f"locked immutable originals -> {args.history_ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
