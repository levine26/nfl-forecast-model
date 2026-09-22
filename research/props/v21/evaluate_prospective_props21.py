from __future__ import annotations

"""Postgame evaluation adapter for the immutable Props 2.1 Sunday cohort.

This module is evaluation-only. It never rewrites a pregame receipt and never
changes the Props model, signal thresholds, F-ST, or production outputs.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import nflreadpy as nfl
import numpy as np
import pandas as pd

from nfl_forecast.data import load_advanced_data, load_core_data
from research.props.evaluation.props_evaluation import evaluate_history, original_sha256
from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids
from nfl_forecast.props_upstream import normalize_nflverse_scramble_semantics
from research.props.v2 import grade_prospective_football_shadow as shadow_grader


FROZEN_PUBLICATION_COMMIT = "ba723255982c79ffe6072c714dd0ee2c37e1fa34"
FROZEN_RECEIPT_BLOB = "e89cdce268fb10c5107ba6db4087107fb213555f"
FROZEN_SOURCE_RUN = "35477049179"
FROZEN_MODEL_VERSION = "levline-props-2.1-sunday-v0.1"
FROZEN_RECEIPT_VERSION = "levline-props-2.1-prospective-receipt-v0.1"
EVIDENCE_MANIFEST_VERSION = "levline-props-2.1-post-sunday-evidence-v0.1"
SUPPORTED_PROPS = {
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions",
    "passing_tds",
    "rushing_td",
    "receiving_td",
    "anytime_td",
}


class Props21EvaluationError(RuntimeError):
    pass


def _aware(value: Any, label: str) -> pd.Timestamp:
    ts = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(ts):
        raise Props21EvaluationError(f"invalid timestamp: {label}")
    return pd.Timestamp(ts)


def read_frozen_receipts(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise Props21EvaluationError(f"missing frozen receipt ledger: {path}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise Props21EvaluationError(f"invalid JSONL line {line_number}") from exc
        if not isinstance(row, dict):
            raise Props21EvaluationError(f"receipt line {line_number} is not an object")
        if row.get("receipt_version") != FROZEN_RECEIPT_VERSION:
            raise Props21EvaluationError("unexpected Props 2.1 receipt version")
        if row.get("model_version") != FROZEN_MODEL_VERSION:
            raise Props21EvaluationError("unexpected Props 2.1 model version")
        if row.get("immutable") is not True:
            raise Props21EvaluationError("Props 2.1 receipt is not immutable")
        if row.get("production_authorized") is not False:
            raise Props21EvaluationError("research receipt is production authorized")
        if row.get("outcome") is not None:
            raise Props21EvaluationError("pregame receipt was contaminated with an outcome")

        forecast = row.get("forecast")
        if not isinstance(forecast, Mapping):
            raise Props21EvaluationError("receipt missing forecast object")
        receipt_id = str(row.get("receipt_id") or "")
        forecast_id = str(forecast.get("forecast_id") or "")
        if not receipt_id or receipt_id != forecast_id or receipt_id in seen:
            raise Props21EvaluationError("invalid, mismatched, or duplicate receipt id")
        seen.add(receipt_id)

        prop = str(forecast.get("prop_type") or "")
        if prop not in SUPPORTED_PROPS:
            raise Props21EvaluationError(f"unsupported Props 2.1 prop type: {prop}")

        provenance = forecast.get("provenance")
        if not isinstance(provenance, Mapping):
            raise Props21EvaluationError("forecast missing provenance")
        if provenance.get("challenger_model_version") != FROZEN_MODEL_VERSION:
            raise Props21EvaluationError("challenger model provenance mismatch")
        if provenance.get("research_only") is not True:
            raise Props21EvaluationError("receipt provenance is not research-only")
        if provenance.get("production_authorized") is not False:
            raise Props21EvaluationError("receipt provenance authorizes production")
        if provenance.get("pure_model_market_agnostic") is not True:
            raise Props21EvaluationError("Pure LevLine provenance is not market-agnostic")

        horizon = _aware(provenance.get("source_data_horizon_utc"), "source_data_horizon_utc")
        source_forecast = _aware(
            forecast.get("source_v1_forecast_timestamp_utc"),
            "source_v1_forecast_timestamp_utc",
        )
        assembled = _aware(forecast.get("forecast_timestamp_utc"), "forecast_timestamp_utc")
        captured = _aware(row.get("captured_utc"), "captured_utc")
        kickoff = _aware(forecast.get("kickoff_utc"), "kickoff_utc")
        if not (horizon <= source_forecast <= assembled < kickoff):
            raise Props21EvaluationError("receipt violates point-in-time forecast chronology")
        if captured != assembled:
            raise Props21EvaluationError("receipt capture must equal assembled forecast timestamp")

        market_state = forecast.get("market_state")
        if isinstance(market_state, Mapping) and market_state.get("latest_capture_utc"):
            market_at = _aware(market_state.get("latest_capture_utc"), "latest market capture")
            if not (market_at <= assembled and market_at < kickoff):
                raise Props21EvaluationError("market observation is not pregame")

        rows.append(row)
    return rows


def _numeric(series: Any) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _event_map(
    pbp: pd.DataFrame,
    *,
    id_col: str,
    value: pd.Series,
    mask: pd.Series,
    prop: str,
) -> dict[tuple[str, str, str], float]:
    ids = pbp[id_col].astype("string").fillna("").str.strip()
    frame = pd.DataFrame(
        {
            "game_id": pbp["game_id"].astype(str),
            "player_id": ids,
            "value": pd.to_numeric(value, errors="coerce"),
        }
    )
    frame = frame[mask & ids.ne("") & frame["value"].notna()].copy()
    grouped = frame.groupby(["game_id", "player_id"], sort=False)["value"].sum()
    return {
        (str(game_id), str(player_id), prop): float(result)
        for (game_id, player_id), result in grouped.items()
    }


def actual_player_stats(pbp: pd.DataFrame) -> dict[tuple[str, str, str], float]:
    if "game_id" not in pbp.columns:
        raise Props21EvaluationError("PBP missing game_id")

    passer = next((c for c in ("passer_player_id", "passer_id") if c in pbp.columns), None)
    rusher = next((c for c in ("rusher_player_id", "rusher_id") if c in pbp.columns), None)
    receiver = next((c for c in ("receiver_player_id", "receiver_id") if c in pbp.columns), None)
    if not passer or not rusher or not receiver:
        raise Props21EvaluationError("PBP missing stable passer/rusher/receiver ids")

    pass_attempt = _numeric(pbp.get("pass_attempt", 0)).eq(1)
    rush_attempt = _numeric(pbp.get("rush_attempt", 0)).eq(1)
    complete_pass = _numeric(pbp.get("complete_pass", 0)).eq(1)
    pass_td = _numeric(pbp.get("pass_touchdown", 0)).eq(1)
    rush_td = _numeric(pbp.get("rush_touchdown", 0)).eq(1)

    passing_yards = (
        _numeric(pbp["passing_yards"])
        if "passing_yards" in pbp.columns
        else _numeric(pbp.get("yards_gained", 0))
    )
    rushing_yards = (
        _numeric(pbp["rushing_yards"])
        if "rushing_yards" in pbp.columns
        else _numeric(pbp.get("yards_gained", 0))
    )
    receiving_yards = (
        _numeric(pbp["receiving_yards"])
        if "receiving_yards" in pbp.columns
        else _numeric(pbp.get("yards_gained", 0))
    )

    out: dict[tuple[str, str, str], float] = {}
    specs = [
        (passer, passing_yards, pass_attempt, "passing_yards"),
        (passer, pass_td.astype(float), pass_td, "passing_tds"),
        (rusher, rushing_yards, rush_attempt, "rushing_yards"),
        (rusher, rush_td.astype(float), rush_td, "rushing_td"),
        (receiver, receiving_yards, complete_pass, "receiving_yards"),
        (receiver, complete_pass.astype(float), complete_pass, "receptions"),
        (receiver, pass_td.astype(float), pass_td & complete_pass, "receiving_td"),
    ]
    for id_col, values, mask, prop in specs:
        out.update(_event_map(pbp, id_col=id_col, value=values, mask=mask, prop=prop))

    keys = {
        (game_id, player_id)
        for game_id, player_id, prop in out
        if prop in {"rushing_td", "receiving_td"}
    }
    for game_id, player_id in keys:
        rushing = out.get((game_id, player_id, "rushing_td"), 0.0)
        receiving = out.get((game_id, player_id, "receiving_td"), 0.0)
        out[(game_id, player_id, "anytime_td")] = float(rushing + receiving)
    return out


def _receipt_to_evaluator_original(row: Mapping[str, Any]) -> dict[str, Any]:
    forecast = row["forecast"]
    provenance = forecast["provenance"]
    market_state = forecast.get("market_state") if isinstance(forecast.get("market_state"), Mapping) else {}
    qa = forecast.get("qa") if isinstance(forecast.get("qa"), Mapping) else {}

    prop = str(forecast["prop_type"])
    is_td = prop in {"rushing_td", "receiving_td", "anytime_td"}
    p_over = forecast.get("probability_over")
    p_td = forecast.get("probability_td")
    market_over = forecast.get("market_probability_over")
    market_td = forecast.get("market_probability_td")
    market_captured = market_state.get("latest_capture_utc")

    model: dict[str, Any] = {
        "version": FROZEN_MODEL_VERSION,
        "mean": forecast.get("model_mean"),
        "median": forecast.get("model_median"),
        "fair_line": forecast.get("model_median"),
        "simulation_accounting_ok": True,
    }
    if is_td:
        model["td_probability"] = p_td
    else:
        model["over_probability"] = p_over
        model["under_probability"] = (1.0 - float(p_over)) if p_over is not None else None
        model["push_probability"] = 0.0

    market: dict[str, Any] = {
        "source": ",".join(provenance.get("source_market_provider") or []),
        "captured_utc": market_captured,
        "line": forecast.get("market_line"),
    }
    if is_td:
        market["no_vig_probability"] = market_td
    else:
        market["no_vig_over_probability"] = market_over
        market["no_vig_under_probability"] = (
            1.0 - float(market_over) if market_over is not None else None
        )

    return {
        "forecast_id": forecast["forecast_id"],
        "player_identity_resolved": True,
        "player_id": forecast["player_id"],
        "player": forecast.get("player_name"),
        "position": forecast.get("position"),
        "team": forecast.get("team"),
        "opponent": forecast.get("opponent"),
        "game_id": forecast["game_id"],
        "prop_type": prop,
        "forecast_timestamp_utc": forecast["forecast_timestamp_utc"],
        "data_horizon_utc": provenance["source_data_horizon_utc"],
        "kickoff_utc": forecast["kickoff_utc"],
        "signal_state": qa.get("signal_state"),
        "market": market,
        "model": model,
        "data_quality": {
            "state": qa.get("classification") or "UNCLASSIFIED",
            "critical_ok": bool(qa.get("research_eligible", False)),
        },
    }


def build_evaluation_events(
    receipts: list[dict[str, Any]],
    *,
    completed_games: set[str],
    outcome_pbp_games: set[str],
    actuals: Mapping[tuple[str, str, str], float],
    participation: Mapping[tuple[str, str], int],
    graded_utc: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int], dict[str, dict[str, Any]]]:
    forecast_receipts: list[dict[str, Any]] = []
    grades: list[dict[str, Any]] = []
    metadata: dict[str, dict[str, Any]] = {}
    audit = {
        "receipt_count": len(receipts),
        "not_final": 0,
        "missing_final_pbp": 0,
        "missing_participation": 0,
        "zero_offense_snaps_void": 0,
        "graded": 0,
    }

    for row in receipts:
        forecast = row["forecast"]
        original = _receipt_to_evaluator_original(row)
        fid = str(forecast["forecast_id"])
        original_hash = original_sha256(original)
        forecast_receipts.append(
            {
                "history_contract_version": "levline-props-history-v0.1",
                "event_type": "FORECAST_ORIGINAL",
                "forecast_id": fid,
                "recorded_utc": row["captured_utc"],
                "original_sha256": original_hash,
                "original_forecast": original,
            }
        )
        role = forecast.get("role_state") if isinstance(forecast.get("role_state"), Mapping) else {}
        market_state = (
            forecast.get("market_state")
            if isinstance(forecast.get("market_state"), Mapping)
            else {}
        )
        metadata[fid] = {
            "role_state": role.get("state"),
            "availability_state": role.get("availability"),
            "workload_state": role.get("workload"),
            "market_distribution_status": market_state.get("status"),
            "market_book_count": market_state.get("book_count"),
            "market_line_dispersion": market_state.get("line_dispersion"),
            "qa_flag_count": len((forecast.get("qa") or {}).get("flag_codes") or []),
        }

        game_id = str(forecast["game_id"])
        if game_id not in completed_games:
            audit["not_final"] += 1
            continue
        if game_id not in outcome_pbp_games:
            audit["missing_final_pbp"] += 1
            continue
        player_id = str(forecast["player_id"])
        snaps = participation.get((game_id, player_id))
        if snaps is None:
            audit["missing_participation"] += 1
            continue
        if int(snaps) <= 0:
            audit["zero_offense_snaps_void"] += 1
            continue
        prop = str(forecast["prop_type"])
        actual = float(actuals.get((game_id, player_id, prop), 0.0))
        grades.append(
            {
                "history_contract_version": "levline-props-history-v0.1",
                "event_type": "GRADE",
                "forecast_id": fid,
                "graded_utc": graded_utc.isoformat(),
                "actual_result": actual,
                "original_sha256": original_hash,
                "result_source": "nflverse_pbp_plus_snap_participation",
            }
        )
        audit["graded"] += 1
    return forecast_receipts, grades, audit, metadata


def _bucket_diagnostics(frame: pd.DataFrame, column: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if frame.empty or column not in frame.columns:
        return out
    for value, group in frame.groupby(column, dropna=False, sort=True):
        actual = pd.to_numeric(group["actual_result"], errors="coerce")
        mean = pd.to_numeric(group["model_mean"], errors="coerce")
        valid = group[actual.notna() & mean.notna()].copy()
        item: dict[str, Any] = {
            "n": int(len(group)),
            "graded_n": int(group["actual_result"].notna().sum()),
            "unique_games": int(group["game_id"].dropna().nunique()),
        }
        if not valid.empty:
            err = valid["model_mean"].astype(float) - valid["actual_result"].astype(float)
            item.update(
                {
                    "mae_model_mean": float(np.abs(err).mean()),
                    "rmse_model_mean": float(np.sqrt(np.square(err).mean())),
                    "bias_model_mean": float(err.mean()),
                }
            )
        out[str(value)] = item
    return out


def enrich_detail(detail: pd.DataFrame, metadata: Mapping[str, Mapping[str, Any]]) -> pd.DataFrame:
    out = detail.copy()
    if out.empty:
        return out
    for field in (
        "role_state",
        "availability_state",
        "workload_state",
        "market_distribution_status",
        "market_book_count",
        "market_line_dispersion",
        "qa_flag_count",
    ):
        out[field] = out["forecast_id"].map(
            lambda fid: metadata.get(str(fid), {}).get(field)
        )
    books = pd.to_numeric(out["market_book_count"], errors="coerce")
    out["market_liquidity_bucket"] = pd.cut(
        books,
        bins=[-np.inf, 1, 3, 5, np.inf],
        labels=["0-1 books", "2-3 books", "4-5 books", "6+ books"],
    )
    mean = pd.to_numeric(out["model_mean"], errors="coerce")
    try:
        out["player_volume_bucket"] = pd.qcut(
            mean.rank(method="first"),
            q=4,
            labels=["Q1 low", "Q2", "Q3", "Q4 high"],
        )
    except ValueError:
        out["player_volume_bucket"] = "UNAVAILABLE"
    return out


def run(receipt_path: Path, output_dir: Path, bootstrap_replicates: int = 5000) -> dict[str, Any]:
    receipts = read_frozen_receipts(receipt_path)
    seasons = sorted(
        {
            int(str(row["forecast"]["game_id"]).split("_")[0])
            for row in receipts
        }
    )
    bundle = load_core_data(seasons)
    bundle = load_advanced_data(bundle, seasons)
    schedules = (
        bundle.schedules.to_pandas()
        if hasattr(bundle.schedules, "to_pandas")
        else bundle.schedules.copy()
    )
    pbp = bundle.pbp.to_pandas() if hasattr(bundle.pbp, "to_pandas") else bundle.pbp.copy()
    pbp, scramble_audit = normalize_nflverse_scramble_semantics(pbp)

    players = nfl.load_players()
    players = players.to_pandas() if hasattr(players, "to_pandas") else players.copy()
    normalized_snaps, snap_identity_audit = normalize_snap_counts_player_ids(
        bundle.snap_counts, players
    )
    if normalized_snaps is None or normalized_snaps.empty:
        raise Props21EvaluationError(
            f"snap identity normalization failed: {snap_identity_audit}"
        )

    completed_games = shadow_grader._completed_games(schedules)
    outcome_pbp_games, outcome_pbp_audit = shadow_grader.complete_outcome_pbp_games(pbp)
    participation, participation_audit = shadow_grader.offense_participation(
        normalized_snaps
    )
    actuals = actual_player_stats(pbp)

    now = datetime.now(timezone.utc)
    forecast_receipts, grade_events, eligibility_audit, metadata = build_evaluation_events(
        receipts,
        completed_games=completed_games,
        outcome_pbp_games=outcome_pbp_games,
        actuals=actuals,
        participation=participation,
        graded_utc=now,
    )

    summary, detail = evaluate_history(
        forecast_receipts,
        grade_events=grade_events,
        frozen_model_ref=(
            f"{FROZEN_MODEL_VERSION}@{FROZEN_PUBLICATION_COMMIT}"
        ),
        source_provenance={
            "source_workflow_run": FROZEN_SOURCE_RUN,
            "publication_commit": FROZEN_PUBLICATION_COMMIT,
            "receipt_git_blob_sha": FROZEN_RECEIPT_BLOB,
            "receipt_version": FROZEN_RECEIPT_VERSION,
            "evidence_manifest_version": EVIDENCE_MANIFEST_VERSION,
        },
        bootstrap_replicates=bootstrap_replicates,
    )
    detail = enrich_detail(detail, metadata)

    summary["props21_postgame_adapter"] = {
        "version": EVIDENCE_MANIFEST_VERSION,
        "eligibility_audit": eligibility_audit,
        "outcome_source_audit": {
            "pbp_normalization": scramble_audit,
            "snap_identity": snap_identity_audit,
            "participation": participation_audit,
            "outcome_pbp": outcome_pbp_audit,
        },
        "distribution_scores": {
            "crps": "UNAVAILABLE_NO_LOSSLESS_PROPS21_DISTRIBUTION_IN_FROZEN_RECEIPT",
            "pit": "UNAVAILABLE_NO_LOSSLESS_PROPS21_DISTRIBUTION_IN_FROZEN_RECEIPT",
            "interval_coverage": "UNAVAILABLE_NO_FROZEN_PROPS21_INTERVAL_IN_RECEIPT",
        },
        "subgroup_diagnostics": {
            "role_state": _bucket_diagnostics(detail, "role_state"),
            "availability_state": _bucket_diagnostics(detail, "availability_state"),
            "workload_state": _bucket_diagnostics(detail, "workload_state"),
            "market_liquidity_bucket": _bucket_diagnostics(
                detail, "market_liquidity_bucket"
            ),
            "market_distribution_status": _bucket_diagnostics(
                detail, "market_distribution_status"
            ),
            "player_volume_bucket": _bucket_diagnostics(
                detail, "player_volume_bucket"
            ),
        },
        "automatic_promotion_authorized": False,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    detail.to_csv(output_dir / "forecast_level.csv", index=False)
    pd.DataFrame(summary["probability"].get("calibration", [])).to_csv(
        output_dir / "calibration.csv", index=False
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=5000)
    args = parser.parse_args()
    run(args.receipts, args.output_dir, args.bootstrap_replicates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
