from __future__ import annotations

"""Chronological evaluation for the Props 2.0 NGS market-residual challenger.

2023-2025 results are retrospective development evidence only. The script uses
strictly lagged NGS state at every target week, train-only transforms, and fixed
regularization. It does not select a betting threshold.
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from research.props.v2.props_ngs_efficiency_state import (  # noqa: E402
    build_lagged_ngs_state,
    load_ngs_efficiency_history,
)
from research.props.v2.props_ngs_market_residual import (  # noqa: E402
    COMMON_FEATURES,
    FEATURES_BY_PROP,
    apply_ngs_market_residual,
    fit_ngs_market_residual,
    no_vig_over_probability,
)

CONTRACT_VERSION = "levline-props-v2-ngs-residual-development-v0.1.0"
BOOTSTRAP_SEED = 20260918
SUPPORTED_PROPS = tuple(FEATURES_BY_PROP)


def _read_inputs(paths: list[Path]) -> pd.DataFrame:
    frames = [pd.read_csv(path) for path in paths]
    data = pd.concat(frames, ignore_index=True)
    if "p_over" not in data.columns and "v1_p_over" in data.columns:
        data["p_over"] = data["v1_p_over"]
    if "model_side" not in data.columns and "v1_model_side" in data.columns:
        data["model_side"] = data["v1_model_side"]
    required = {
        "season", "week", "game_id", "player_id", "prop_type",
        "market_line", "over_odds", "under_odds", "p_over", "actual_result",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"forecast ledger missing fields: {sorted(missing)}")
    data["season"] = pd.to_numeric(data["season"], errors="raise").astype(int)
    data["week"] = pd.to_numeric(data["week"], errors="raise").astype(int)
    data["player_id"] = data["player_id"].astype(str)
    data["prop_type"] = data["prop_type"].astype(str)
    return data[data["prop_type"].isin(SUPPORTED_PROPS)].copy()


def _attach_ngs_state(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    min_season = int(data["season"].min())
    max_season = int(data["season"].max())
    history_seasons = list(range(max(2016, min_season - 2), max_season + 1))
    ngs = load_ngs_efficiency_history(history_seasons)

    pieces = []
    audits = {}
    for (season, week), group in data.groupby(["season", "week"], sort=True):
        ids = sorted(set(group["player_id"].astype(str)))
        state, audit = build_lagged_ngs_state(
            passing=ngs["passing"],
            receiving=ngs["receiving"],
            rushing=ngs["rushing"],
            season=int(season),
            week=int(week),
            player_ids=ids,
        )
        key = f"{int(season)}-W{int(week):02d}"
        audits[key] = audit
        merged = group.merge(
            state,
            on="player_id",
            how="left",
            validate="many_to_one",
        )
        pieces.append(merged)
    out = pd.concat(pieces, ignore_index=True)
    ngs_cols = [c for c in out.columns if c.startswith("ngs_") and not c.endswith("_version")]
    rows_any = (
        out[[c for c in ("ngs_pass_rows", "ngs_rec_rows", "ngs_rush_rows") if c in out]]
        .fillna(0)
        .sum(axis=1)
        .gt(0)
    )
    coverage = {
        "history_seasons_loaded": history_seasons,
        "forecast_rows": int(len(out)),
        "rows_with_any_ngs_state": int(rows_any.sum()),
        "row_coverage": float(rows_any.mean()) if len(out) else None,
        "ngs_feature_columns": sorted(ngs_cols),
        "period_audits": audits,
        "target_week_rows_used": 0,
    }
    return out, coverage


def _grade(scored: pd.DataFrame) -> pd.DataFrame:
    out = scored.copy()
    actual = pd.to_numeric(out["actual_result"], errors="raise").to_numpy(float)
    line = pd.to_numeric(out["market_line"], errors="raise").to_numpy(float)
    outcome = np.where(actual > line, "OVER", np.where(actual < line, "UNDER", "PUSH"))
    out["market_outcome_recomputed"] = outcome
    decided = out["market_outcome_recomputed"].ne("PUSH")
    market_p = np.asarray(
        [no_vig_over_probability(o, u) for o, u in zip(out["over_odds"], out["under_odds"])]
    )
    out["market_side"] = np.where(market_p >= 0.5, "OVER", "UNDER")
    out["market_correct"] = np.where(
        decided, out["market_side"].eq(out["market_outcome_recomputed"]).astype(float), np.nan
    )
    if "model_side" in out.columns:
        v1_side = out["model_side"].where(out["model_side"].isin(["OVER", "UNDER"]))
    else:
        v1_side = pd.Series(np.where(pd.to_numeric(out["p_over"]) >= 0.5, "OVER", "UNDER"))
    out["v1_correct"] = np.where(
        decided & v1_side.notna(),
        v1_side.eq(out["market_outcome_recomputed"]).astype(float),
        np.nan,
    )
    out["ngs_correct"] = np.where(
        decided & out["ngs_challenger_side"].notna(),
        out["ngs_challenger_side"].eq(out["market_outcome_recomputed"]).astype(float),
        np.nan,
    )
    return out


def _score_models(frame: pd.DataFrame, models: dict) -> pd.DataFrame:
    return _grade(apply_ngs_market_residual(frame, models))


def _fit_models(train: pd.DataFrame, *, include_ngs: bool) -> tuple[dict, dict]:
    models = {}
    failures = {}
    for prop in SUPPORTED_PROPS:
        try:
            features = None if include_ngs else COMMON_FEATURES
            models[prop] = fit_ngs_market_residual(
                train,
                prop_type=prop,
                feature_columns=features,
            )
        except Exception as exc:
            failures[prop] = f"{type(exc).__name__}: {exc}"
    return models, failures


def _merge_baseline_columns(ngs_scored: pd.DataFrame, base_scored: pd.DataFrame) -> pd.DataFrame:
    keys = ["season", "week", "game_id", "player_id", "prop_type", "market_line"]
    base = base_scored[keys + ["ngs_challenger_p_over", "ngs_challenger_side", "ngs_correct"]].copy()
    base = base.rename(columns={
        "ngs_challenger_p_over": "matched_baseline_p_over",
        "ngs_challenger_side": "matched_baseline_side",
        "ngs_correct": "matched_baseline_correct",
    })
    return ngs_scored.merge(base, on=keys, how="left", validate="one_to_one")


def _metrics(frame: pd.DataFrame) -> dict:
    work = frame[
        frame["market_outcome_recomputed"].ne("PUSH")
        & frame["ngs_correct"].notna()
        & frame["matched_baseline_correct"].notna()
    ].copy()
    if work.empty:
        return {"n": 0}
    return {
        "n": int(len(work)),
        "unique_games": int(work["game_id"].astype(str).nunique()),
        "unique_players": int(work["player_id"].astype(str).nunique()),
        "ngs_accuracy": float(work["ngs_correct"].mean()),
        "matched_market_v1_residual_accuracy": float(work["matched_baseline_correct"].mean()),
        "v1_accuracy": float(work["v1_correct"].mean()),
        "market_price_direction_accuracy": float(work["market_correct"].mean()),
        "ngs_minus_matched_baseline_pp": float(
            100.0 * (work["ngs_correct"] - work["matched_baseline_correct"]).mean()
        ),
        "ngs_minus_v1_pp": float(100.0 * (work["ngs_correct"] - work["v1_correct"]).mean()),
        "ngs_minus_market_pp": float(100.0 * (work["ngs_correct"] - work["market_correct"]).mean()),
    }


def _cluster_bootstrap(frame: pd.DataFrame, replicates: int, seed: int) -> dict:
    work = frame[
        frame["market_outcome_recomputed"].ne("PUSH")
        & frame["ngs_correct"].notna()
        & frame["matched_baseline_correct"].notna()
    ].copy()
    games = np.asarray(sorted(work["game_id"].astype(str).unique()))
    if len(games) < 2:
        return {"ngs_accuracy_ci95": [None, None], "ngs_minus_baseline_ci95_pp": [None, None]}
    grouped = {g: work[work["game_id"].astype(str).eq(g)] for g in games}
    rng = np.random.default_rng(seed)
    acc = np.empty(replicates)
    diff = np.empty(replicates)
    for i in range(replicates):
        sample = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[g] for g in sample], ignore_index=True)
        acc[i] = boot["ngs_correct"].mean()
        diff[i] = 100.0 * (boot["ngs_correct"] - boot["matched_baseline_correct"]).mean()
    return {
        "ngs_accuracy_ci95": [float(np.quantile(acc, .025)), float(np.quantile(acc, .975))],
        "ngs_minus_baseline_ci95_pp": [
            float(np.quantile(diff, .025)), float(np.quantile(diff, .975))
        ],
    }


def _evaluate_block(train: pd.DataFrame, evaluate: pd.DataFrame, *, replicates: int, seed: int):
    ngs_models, ngs_fail = _fit_models(train, include_ngs=True)
    base_models, base_fail = _fit_models(train, include_ngs=False)
    common = sorted(set(ngs_models) & set(base_models))
    ngs_models = {k: ngs_models[k] for k in common}
    base_models = {k: base_models[k] for k in common}
    eval_common = evaluate[evaluate["prop_type"].isin(common)].copy()
    ngs_scored = _score_models(eval_common, ngs_models)
    base_scored = _score_models(eval_common, base_models)
    paired = _merge_baseline_columns(ngs_scored, base_scored)
    overall = _metrics(paired)
    overall.update(_cluster_bootstrap(paired, replicates, seed))
    overall["by_prop_type"] = {
        str(prop): _metrics(group) for prop, group in paired.groupby("prop_type", sort=True)
    }
    return paired, {
        "models": {k: v.to_dict() for k, v in ngs_models.items()},
        "matched_baseline_models": {k: v.to_dict() for k, v in base_models.items()},
        "ngs_fit_failures": ngs_fail,
        "baseline_fit_failures": base_fail,
        "evaluation": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=3000)
    args = parser.parse_args()

    data = _read_inputs(args.input)
    data, coverage = _attach_ngs_state(data)

    fixed_train = data[(data["season"].eq(2023)) & (data["week"].le(9))].copy()
    fixed_eval = data[
        ((data["season"].eq(2023)) & data["week"].ge(10))
        | data["season"].isin([2024, 2025])
    ].copy()
    fixed_rows, fixed = _evaluate_block(
        fixed_train, fixed_eval, replicates=args.bootstrap_replicates, seed=BOOTSTRAP_SEED
    )

    rolling_rows = []
    rolling = {}
    for season in (2024, 2025):
        train = data[(data["season"].ge(2023)) & (data["season"].lt(season))].copy()
        evaluate = data[data["season"].eq(season)].copy()
        if train.empty or evaluate.empty:
            continue
        rows, result = _evaluate_block(
            train,
            evaluate,
            replicates=args.bootstrap_replicates,
            seed=BOOTSTRAP_SEED + season,
        )
        rows["evaluation_season"] = season
        rolling_rows.append(rows)
        rolling[str(season)] = result

    payload = {
        "contract_version": CONTRACT_VERSION,
        "research_label": "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE",
        "promotion_authorized": False,
        "selective_threshold_used": False,
        "completed_2026_outcomes_used_for_tuning": 0,
        "ngs_state_coverage": coverage,
        "fixed_anchor": {
            "training_rule": "2023 Weeks 1-9 only; fixed thereafter",
            **fixed,
        },
        "rolling_origin": {
            "training_rule": "target season uses only prior seasons beginning 2023",
            "by_evaluation_season": rolling,
        },
        "interpretation": (
            "The matched baseline uses the same prop-family partition, market offset, "
            "regularization and LevLine probability gap, but excludes NGS features. "
            "Therefore NGS-minus-baseline is the primary incremental-football diagnostic."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fixed_rows.to_csv(args.output_dir / "fixed_anchor_rows.csv", index=False)
    if rolling_rows:
        pd.concat(rolling_rows, ignore_index=True).to_csv(
            args.output_dir / "rolling_origin_rows.csv", index=False
        )
    print(json.dumps({
        "fixed_anchor": payload["fixed_anchor"]["evaluation"],
        "rolling_origin": {
            k: v["evaluation"] for k, v in rolling.items()
        },
        "coverage": {
            "forecast_rows": coverage["forecast_rows"],
            "rows_with_any_ngs_state": coverage["rows_with_any_ngs_state"],
            "row_coverage": coverage["row_coverage"],
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
