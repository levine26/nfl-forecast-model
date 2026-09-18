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
from nfl_forecast.props_manifest import (  # noqa: E402
    verify_manifest_fingerprint,
    verify_manifest_slate_index,
)
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
    verify_manifest_fingerprint(payload)
    return payload



def _resolve_slate_manifest_path(root: Path, relative: object) -> Path:
    value = str(relative or "").strip()
    if not value:
        raise ValueError("manifest slate entry missing manifest_file")
    candidate = (root / value).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("manifest slate path escapes its root") from exc
    return candidate


def _load_manifest_slate(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"missing manifest slate: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest slate must be a JSON object")
    verify_manifest_slate_index(payload)

    root = path.parent
    expected_forecast = _aware(
        payload["forecast_timestamp_utc"],
        "manifest slate forecast_timestamp_utc",
    )
    manifests: list[dict] = []
    seen_game_ids: set[str] = set()
    for entry in payload["games"]:
        game_id = str(entry["game_id"]).strip()
        manifest_path = _resolve_slate_manifest_path(
            root,
            entry["manifest_file"],
        )
        manifest = _load(manifest_path)
        if str(manifest.get("game_id") or "").strip() != game_id:
            raise ValueError(
                f"manifest slate game_id {game_id} disagrees with {manifest_path.name}"
            )
        if str(manifest.get("manifest_sha256") or "").strip() != str(
            entry["manifest_sha256"]
        ).strip():
            raise ValueError(
                f"manifest slate fingerprint disagrees for game {game_id}"
            )
        manifest_forecast = _aware(
            manifest.get("forecast_timestamp_utc"),
            f"{game_id} forecast_timestamp_utc",
        )
        if manifest_forecast != expected_forecast:
            raise ValueError(
                f"manifest slate forecast timestamp disagrees for game {game_id}"
            )
        if game_id in seen_game_ids:
            raise ValueError(f"duplicate game_id in manifest slate: {game_id}")
        seen_game_ids.add(game_id)
        manifests.append(manifest)
    return manifests

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


def _build_artifact(payload: dict) -> dict:
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
    return build_forecast_artifact(
        result,
        _required(payload, "market_artifacts"),
        kickoff_utc=kickoff,
        forecast_timestamp_utc=forecast_timestamp,
        interval_level=float(payload.get("prediction_interval_level", 0.80)),
    )


def _combine_artifacts(artifacts: list[dict], *, generated_utc: datetime) -> dict:
    if not artifacts:
        raise ValueError("at least one Props game manifest is required")
    contracts = {str(artifact.get("contract_version") or "") for artifact in artifacts}
    if len(contracts) != 1 or "" in contracts:
        raise ValueError("Props game artifacts must share one non-empty contract_version")
    research_labels = {
        str(artifact.get("research_label") or "") for artifact in artifacts
        if artifact.get("research_label") is not None
    }
    scopes = {
        str(artifact.get("scope") or "") for artifact in artifacts
        if artifact.get("scope") is not None
    }
    if len(research_labels) > 1:
        raise ValueError("Props game artifacts disagree on research_label")
    if len(scopes) > 1:
        raise ValueError("Props game artifacts disagree on scope")

    forecasts: list[dict] = []
    seen_ids: set[str] = set()
    for artifact in artifacts:
        rows = artifact.get("forecasts")
        if not isinstance(rows, list):
            raise ValueError("Props game artifact must contain a forecasts list")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Props forecast rows must be JSON objects")
            forecast_id = str(row.get("forecast_id") or "").strip()
            if not forecast_id:
                raise ValueError("Props forecast row missing forecast_id")
            if forecast_id in seen_ids:
                raise ValueError(f"duplicate forecast_id across slate: {forecast_id}")
            seen_ids.add(forecast_id)
            forecasts.append(row)

    first = artifacts[0]
    return {
        "contract_version": next(iter(contracts)),
        "generated_utc": generated_utc.astimezone(timezone.utc).isoformat(),
        "research_label": (
            next(iter(research_labels))
            if research_labels
            else first.get("research_label")
        ),
        "scope": next(iter(scopes)) if scopes else first.get("scope"),
        "game_count": len(artifacts),
        "forecasts": forecasts,
    }


def produce_many(
    payloads: list[dict],
    *,
    output: Path,
    public_output: Path | None,
    history_ledger: Path,
) -> dict:
    """Build and publish a complete Props slate as one fail-closed transaction."""

    artifacts = [_build_artifact(payload) for payload in payloads]
    recorded = datetime.now(timezone.utc)
    combined = _combine_artifacts(artifacts, generated_utc=recorded)
    public = (
        build_public_props(combined, now_utc=recorded)
        if public_output is not None
        else None
    )

    receipts = [
        make_forecast_receipt(row, recorded_utc=recorded)
        for row in combined["forecasts"]
    ]
    append_jsonl_immutable(
        history_ledger, receipts, identity_key="forecast_id"
    )

    # Publish only after every game built successfully and every original receipt has
    # passed immutable-history validation. A single failing game cannot expose a partial
    # Sunday slate.
    _write_json(output, combined)
    if public_output is not None and public is not None:
        _write_json(public_output, public)
    return combined


def produce(
    payload: dict,
    *,
    output: Path,
    public_output: Path | None,
    history_ledger: Path,
) -> dict:
    """Backward-compatible one-game producer using the slate transaction path."""

    return produce_many(
        [payload],
        output=output,
        public_output=public_output,
        history_ledger=history_ledger,
    )

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the integrated LevLine Props Research Beta from frozen lane artifacts."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--input",
        type=Path,
        nargs="+",
        help="One or more frozen game manifests. Multiple inputs publish one atomic slate.",
    )
    source.add_argument(
        "--manifest-slate",
        type=Path,
        help="Frozen manifest_slate.json; referenced game manifests are verified and loaded atomically.",
    )
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
    payloads = (
        _load_manifest_slate(args.manifest_slate)
        if args.manifest_slate is not None
        else [_load(path) for path in args.input]
    )
    artifact = produce_many(
        payloads,
        output=args.output,
        public_output=args.public_output,
        history_ledger=args.history_ledger,
    )
    print(
        f"wrote {len(artifact['forecasts'])} Props Research Beta forecasts "
        f"across {artifact['game_count']} game(s) -> {args.output}"
    )
    print(f"locked immutable originals -> {args.history_ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
