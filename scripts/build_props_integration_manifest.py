from __future__ import annotations

"""Assemble a validated immutable LevLine Props integration manifest from frozen inputs."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_manifest import assemble_manifest, payload_sha256  # noqa: E402


def _load(path: Path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_list(payload, *keys: str) -> list[dict]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = None
        for key in keys:
            if isinstance(payload.get(key), list):
                rows = payload[key]
                break
    else:
        rows = None
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError(f"expected JSON row list under one of: {', '.join(keys)}")
    return [dict(row) for row in rows]


def _extract_mapping(payload, *keys: str) -> dict:
    if isinstance(payload, dict):
        for key in keys:
            if isinstance(payload.get(key), dict):
                return dict(payload[key])
        if not keys:
            return dict(payload)
    raise ValueError(f"expected JSON object under one of: {', '.join(keys)}")


def _write_frozen(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen manifest: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble validated LevLine Props frozen integration manifest."
    )
    parser.add_argument("--game-spec", type=Path, required=True)
    parser.add_argument("--opportunity", type=Path, required=True)
    parser.add_argument("--efficiency-player", type=Path, required=True)
    parser.add_argument("--team-td", type=Path, required=True)
    parser.add_argument("--residual-efficiency", type=Path, required=True)
    parser.add_argument("--market-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--forecast-timestamp",
        help="Final manifest freeze timestamp. Defaults to current UTC when game spec omits one.",
    )
    args = parser.parse_args()

    raw_game = _load(args.game_spec)
    raw_opportunity = _load(args.opportunity)
    raw_efficiency = _load(args.efficiency_player)
    raw_team_td = _load(args.team_td)
    raw_residual = _load(args.residual_efficiency)
    raw_market = _load(args.market_snapshot)

    if not isinstance(raw_game, dict):
        raise ValueError("game spec must be a JSON object")
    if args.forecast_timestamp:
        parsed_forecast = datetime.fromisoformat(
            str(args.forecast_timestamp).replace("Z", "+00:00")
        )
        if parsed_forecast.tzinfo is None:
            raise ValueError("--forecast-timestamp must be timezone-aware")
        raw_game = {
            **raw_game,
            "forecast_timestamp_utc": parsed_forecast.astimezone(timezone.utc).isoformat(),
        }
    elif not raw_game.get("forecast_timestamp_utc"):
        raw_game = {
            **raw_game,
            "forecast_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    if not isinstance(raw_market, dict):
        raise ValueError("market snapshot must be a JSON object")

    opportunity = _extract_list(
        raw_opportunity,
        "opportunity_projections",
        "projections",
        "rows",
    )
    efficiency = _extract_list(
        raw_efficiency,
        "efficiency_player_parameters",
        "player_parameters",
        "rows",
    )
    team_td = _extract_list(
        raw_team_td,
        "team_td_parameters",
        "rows",
    )
    if isinstance(raw_residual, dict) and isinstance(
        raw_residual.get("residual_efficiency_by_team"), dict
    ):
        residual = dict(raw_residual["residual_efficiency_by_team"])
    elif isinstance(raw_residual, dict):
        residual = dict(raw_residual)
    else:
        raise ValueError("residual efficiency input must be a JSON object")

    provenance = {
        "game_spec": {
            "source_file": args.game_spec.name,
            "sha256": payload_sha256(raw_game),
        },
        "opportunity": {
            "source_file": args.opportunity.name,
            "sha256": payload_sha256(raw_opportunity),
        },
        "efficiency_player": {
            "source_file": args.efficiency_player.name,
            "sha256": payload_sha256(raw_efficiency),
        },
        "team_td": {
            "source_file": args.team_td.name,
            "sha256": payload_sha256(raw_team_td),
        },
        "residual_efficiency": {
            "source_file": args.residual_efficiency.name,
            "sha256": payload_sha256(raw_residual),
        },
        "market_snapshot": {
            "source_file": args.market_snapshot.name,
            "sha256": payload_sha256(raw_market),
        },
    }

    manifest = assemble_manifest(
        game_spec=raw_game,
        opportunity_projections=opportunity,
        efficiency_player_parameters=efficiency,
        team_td_parameters=team_td,
        residual_efficiency_by_team=residual,
        market_snapshot=raw_market,
        input_provenance=provenance,
    )
    manifest["manifest_sha256"] = payload_sha256(manifest)

    _write_frozen(args.output, manifest)
    print(
        f"frozen validated manifest for {manifest['game_id']} with "
        f"{len(manifest['market_artifacts'])} market artifacts -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
