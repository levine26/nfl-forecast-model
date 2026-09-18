from __future__ import annotations

"""Assemble validated immutable LevLine Props integration manifests from frozen inputs."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_manifest import assemble_manifest, payload_sha256  # noqa: E402


SLATE_CONTRACT_VERSION = "levline-props-integration-slate-v0.1"


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


def _forecast_timestamp(value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("--forecast-timestamp must be timezone-aware")
        return parsed.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _manifest_from_components(
    *,
    raw_game: dict[str, Any],
    raw_opportunity: object,
    raw_efficiency: object,
    raw_team_td: object,
    raw_residual: object,
    raw_market: dict[str, Any],
    forecast_timestamp: datetime,
    source_files: dict[str, str],
    extra_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    game = {
        **raw_game,
        "forecast_timestamp_utc": forecast_timestamp.isoformat(),
    }
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
            "source_file": source_files["game_spec"],
            "sha256": payload_sha256(raw_game),
        },
        "opportunity": {
            "source_file": source_files["opportunity"],
            "sha256": payload_sha256(raw_opportunity),
        },
        "efficiency_player": {
            "source_file": source_files["efficiency_player"],
            "sha256": payload_sha256(raw_efficiency),
        },
        "team_td": {
            "source_file": source_files["team_td"],
            "sha256": payload_sha256(raw_team_td),
        },
        "residual_efficiency": {
            "source_file": source_files["residual_efficiency"],
            "sha256": payload_sha256(raw_residual),
        },
        "market_snapshot": {
            "source_file": source_files["market_snapshot"],
            "sha256": payload_sha256(raw_market),
        },
    }
    if extra_provenance:
        provenance.update(extra_provenance)

    manifest = assemble_manifest(
        game_spec=game,
        opportunity_projections=opportunity,
        efficiency_player_parameters=efficiency,
        team_td_parameters=team_td,
        residual_efficiency_by_team=residual,
        market_snapshot=raw_market,
        input_provenance=provenance,
    )
    manifest["manifest_sha256"] = payload_sha256(manifest)
    return manifest


def _resolve_index_path(root: Path, relative: object, *, label: str) -> Path:
    value = str(relative or "").strip()
    if not value:
        raise ValueError(f"upstream slate {label} path is missing")
    candidate = (root / value).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"upstream slate {label} path escapes its root") from exc
    return candidate


def _single_mode(args, raw_market: dict[str, Any], forecast: datetime) -> int:
    required = {
        "game_spec": args.game_spec,
        "opportunity": args.opportunity,
        "efficiency_player": args.efficiency_player,
        "team_td": args.team_td,
        "residual_efficiency": args.residual_efficiency,
        "output": args.output,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(
            "single-game mode missing required argument(s): " + ", ".join(missing)
        )
    raw_game = _load(args.game_spec)
    raw_opportunity = _load(args.opportunity)
    raw_efficiency = _load(args.efficiency_player)
    raw_team_td = _load(args.team_td)
    raw_residual = _load(args.residual_efficiency)
    if not isinstance(raw_game, dict):
        raise ValueError("game spec must be a JSON object")

    manifest = _manifest_from_components(
        raw_game=raw_game,
        raw_opportunity=raw_opportunity,
        raw_efficiency=raw_efficiency,
        raw_team_td=raw_team_td,
        raw_residual=raw_residual,
        raw_market=raw_market,
        forecast_timestamp=forecast,
        source_files={
            "game_spec": args.game_spec.name,
            "opportunity": args.opportunity.name,
            "efficiency_player": args.efficiency_player.name,
            "team_td": args.team_td.name,
            "residual_efficiency": args.residual_efficiency.name,
            "market_snapshot": args.market_snapshot.name,
        },
    )
    _write_frozen(args.output, manifest)
    print(
        f"frozen validated manifest for {manifest['game_id']} with "
        f"{len(manifest['market_artifacts'])} market artifacts -> {args.output}"
    )
    return 0


def _slate_mode(args, raw_market: dict[str, Any], forecast: datetime) -> int:
    if args.output_dir is None:
        raise ValueError("--output-dir is required with --upstream-slate")
    if any(
        value is not None
        for value in (
            args.game_spec,
            args.opportunity,
            args.efficiency_player,
            args.team_td,
            args.residual_efficiency,
            args.output,
        )
    ):
        raise ValueError(
            "do not combine --upstream-slate with single-game component arguments"
        )

    upstream = _load(args.upstream_slate)
    if not isinstance(upstream, dict):
        raise ValueError("upstream slate index must be a JSON object")
    if upstream.get("contract_version") != "levline-props-upstream-slate-v0.1":
        raise ValueError(
            "unsupported upstream slate contract: "
            f"{upstream.get('contract_version')!r}"
        )
    games = upstream.get("games")
    if not isinstance(games, list) or not games:
        raise ValueError("upstream slate must contain a non-empty games list")
    if int(upstream.get("game_count", -1)) != len(games):
        raise ValueError("upstream slate game_count does not match games list")

    upstream_root = args.upstream_slate.parent
    upstream_hash = payload_sha256(upstream)
    market_hash = payload_sha256(raw_market)
    manifests: list[tuple[Path, dict[str, Any]]] = []
    index_games: list[dict[str, Any]] = []
    seen_games: set[str] = set()

    for entry in games:
        if not isinstance(entry, dict):
            raise ValueError("upstream slate game entries must be objects")
        game_id = str(entry.get("game_id") or "").strip()
        if not game_id:
            raise ValueError("upstream slate game entry missing game_id")
        if game_id in seen_games:
            raise ValueError(f"duplicate game_id in upstream slate: {game_id}")
        seen_games.add(game_id)
        files = entry.get("files")
        if not isinstance(files, dict):
            raise ValueError(f"upstream slate game {game_id} missing files mapping")

        paths = {
            key: _resolve_index_path(
                upstream_root,
                files.get(key),
                label=f"{game_id}/{key}",
            )
            for key in (
                "game_spec",
                "opportunity",
                "efficiency_player",
                "team_td",
                "residual_efficiency",
            )
        }
        raw_game = _load(paths["game_spec"])
        raw_opportunity = _load(paths["opportunity"])
        raw_efficiency = _load(paths["efficiency_player"])
        raw_team_td = _load(paths["team_td"])
        raw_residual = _load(paths["residual_efficiency"])
        if not isinstance(raw_game, dict):
            raise ValueError(f"game spec for {game_id} must be a JSON object")
        if str(raw_game.get("game_id") or "") != game_id:
            raise ValueError(
                f"upstream slate game_id {game_id} disagrees with its game spec"
            )

        manifest = _manifest_from_components(
            raw_game=raw_game,
            raw_opportunity=raw_opportunity,
            raw_efficiency=raw_efficiency,
            raw_team_td=raw_team_td,
            raw_residual=raw_residual,
            raw_market=raw_market,
            forecast_timestamp=forecast,
            source_files={
                key: path.name for key, path in paths.items()
            }
            | {"market_snapshot": args.market_snapshot.name},
            extra_provenance={
                "upstream_slate": {
                    "source_file": args.upstream_slate.name,
                    "sha256": upstream_hash,
                }
            },
        )
        if manifest["game_id"] != game_id:
            raise ValueError(
                f"assembled manifest game_id {manifest['game_id']} "
                f"does not match upstream slate {game_id}"
            )

        output = args.output_dir / "games" / f"{game_id}.manifest.json"
        manifests.append((output, manifest))
        index_games.append(
            {
                "game_id": game_id,
                "home_team": manifest["home_team"],
                "away_team": manifest["away_team"],
                "kickoff_utc": manifest["kickoff_utc"],
                "manifest_file": str(output.relative_to(args.output_dir)),
                "manifest_sha256": manifest["manifest_sha256"],
                "market_artifact_count": len(manifest["market_artifacts"]),
            }
        )

    slate_index = {
        "contract_version": SLATE_CONTRACT_VERSION,
        "research_only": True,
        "production_authorized": False,
        "forecast_timestamp_utc": forecast.isoformat(),
        "game_count": len(index_games),
        "upstream_slate": {
            "source_file": args.upstream_slate.name,
            "sha256": upstream_hash,
        },
        "market_snapshot": {
            "source_file": args.market_snapshot.name,
            "sha256": market_hash,
        },
        "games": index_games,
    }
    slate_index["slate_sha256"] = payload_sha256(slate_index)
    index_path = args.output_dir / "manifest_slate.json"

    planned = [path for path, _ in manifests] + [index_path]
    existing = [str(path) for path in planned if path.exists()]
    if existing:
        raise FileExistsError(
            f"refusing partial overwrite; manifest output already exists: {existing}"
        )

    # No file is written until every game has assembled successfully and all output
    # destinations have passed create-only preflight.
    for path, manifest in manifests:
        _write_frozen(path, manifest)
    _write_frozen(index_path, slate_index)

    print(
        f"frozen {len(manifests)} validated game manifests at "
        f"{forecast.isoformat()} -> {args.output_dir}"
    )
    print(f"manifest slate index -> {index_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assemble validated LevLine Props frozen integration manifest(s)."
    )
    parser.add_argument(
        "--upstream-slate",
        type=Path,
        help="Atomic upstream slate index from build_props_upstream_snapshot.py.",
    )
    parser.add_argument("--game-spec", type=Path)
    parser.add_argument("--opportunity", type=Path)
    parser.add_argument("--efficiency-player", type=Path)
    parser.add_argument("--team-td", type=Path)
    parser.add_argument("--residual-efficiency", type=Path)
    parser.add_argument("--market-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Required for slate mode; contains games/*.manifest.json and manifest_slate.json.",
    )
    parser.add_argument(
        "--forecast-timestamp",
        help="Final manifest freeze timestamp. Defaults to current UTC.",
    )
    args = parser.parse_args()

    raw_market = _load(args.market_snapshot)
    if not isinstance(raw_market, dict):
        raise ValueError("market snapshot must be a JSON object")
    forecast = _forecast_timestamp(args.forecast_timestamp)

    if args.upstream_slate is not None:
        return _slate_mode(args, raw_market, forecast)
    return _single_mode(args, raw_market, forecast)


if __name__ == "__main__":
    raise SystemExit(main())
