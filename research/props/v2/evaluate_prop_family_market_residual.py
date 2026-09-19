from __future__ import annotations

"""Evaluate family-specific market-prior residual calibration for LevLine Props 2.0.

This script reuses the frozen two-parameter market-residual model but fits it separately
for each prop family. Historical 2023-2025 results remain development evidence only.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "props" / "v2"))

from props_market_residual import (  # noqa: E402
    RESEARCH_LABEL,
    apply_market_prior_residual,
    fit_market_prior_residual,
    grade_directional_rows,
)

CONTRACT_VERSION = "levline-props-v2-prop-family-market-residual-v0.1.0"
BOOTSTRAP_SEED = 20260918
BOOTSTRAP_REPLICATES = 5000
MIN_TRAINING_ROWS = 50
SUPPORTED_PROPS = (
    "passing_yards",
    "passing_tds",
    "rushing_yards",
    "receiving_yards",
    "receptions",
)


def _fingerprint(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def _read(paths: list[Path]) -> pd.DataFrame:
    data = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    required = {
        "season", "week", "game_id", "player_id", "prop_type", "market_line",
        "over_odds", "under_odds", "p_over", "model_side", "actual_result",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"forecast ledger missing fields: {sorted(missing)}")
    data["season"] = pd.to_numeric(data["season"], errors="raise").astype(int)
    data["week"] = pd.to_numeric(data["week"], errors="raise").astype(int)
    data["prop_type"] = data["prop_type"].astype(str)
    return data[data["prop_type"].isin(SUPPORTED_PROPS)].copy()


def _decided_count(frame: pd.DataFrame) -> int:
    actual = pd.to_numeric(frame["actual_result"], errors="raise").to_numpy(float)
    line = pd.to_numeric(frame["market_line"], errors="raise").to_numpy(float)
    return int((~np.isclose(actual, line, atol=1e-12)).sum())


def _fit_family_models(train: pd.DataFrame) -> tuple[dict, dict]:
    models = {}
    skipped = {}
    for prop in SUPPORTED_PROPS:
        rows = train[train["prop_type"].eq(prop)].copy()
        n = _decided_count(rows) if not rows.empty else 0
        if n < MIN_TRAINING_ROWS:
            skipped[prop] = {"decided_training_rows": n, "reason": "below_frozen_minimum"}
            continue
        models[prop] = fit_market_prior_residual(rows)
    return models, skipped


def _apply_family_models(frame: pd.DataFrame, models: dict) -> pd.DataFrame:
    parts = []
    for prop, model in models.items():
        rows = frame[frame["prop_type"].eq(prop)].copy()
        if rows.empty:
            continue
        scored = grade_directional_rows(apply_market_prior_residual(rows, model))
        scored["family_model_prop"] = prop
        parts.append(scored)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def _apply_global(frame: pd.DataFrame, model) -> pd.DataFrame:
    return grade_directional_rows(apply_market_prior_residual(frame, model))


def _merge_global(family: pd.DataFrame, global_scored: pd.DataFrame) -> pd.DataFrame:
    keys = ["season", "week", "game_id", "player_id", "prop_type", "market_line"]
    cols = keys + ["challenger_p_over", "challenger_side", "challenger_correct"]
    global_part = global_scored[cols].rename(
        columns={
            "challenger_p_over": "global_p_over",
            "challenger_side": "global_side",
            "challenger_correct": "global_correct",
        }
    )
    return family.merge(global_part, on=keys, how="left", validate="one_to_one")


def _brier(y, p) -> float:
    return float(np.mean((np.asarray(y, float) - np.asarray(p, float)) ** 2))


def _log_loss(y, p) -> float:
    p = np.clip(np.asarray(p, float), 1e-8, 1.0 - 1e-8)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


def _metrics(frame: pd.DataFrame) -> dict:
    work = frame[
        frame["market_outcome_recomputed"].ne("PUSH")
        & frame["challenger_correct"].notna()
        & frame["global_correct"].notna()
        & frame["v1_correct"].notna()
    ].copy()
    if work.empty:
        return {"n": 0}
    y = work["market_outcome_recomputed"].eq("OVER").astype(float).to_numpy()
    informative = work["market_price_correct"].notna()
    return {
        "n": int(len(work)),
        "unique_games": int(work["game_id"].astype(str).nunique()),
        "unique_players": int(work["player_id"].astype(str).nunique()),
        "family_accuracy": float(work["challenger_correct"].mean()),
        "global_accuracy": float(work["global_correct"].mean()),
        "v1_accuracy": float(work["v1_correct"].mean()),
        "family_minus_global_pp": float(
            100.0 * (work["challenger_correct"] - work["global_correct"]).mean()
        ),
        "family_minus_v1_pp": float(
            100.0 * (work["challenger_correct"] - work["v1_correct"]).mean()
        ),
        "market_price_direction_rows": int(informative.sum()),
        "market_price_tie_rows": int((~informative).sum()),
        "market_price_direction_accuracy": (
            float(work.loc[informative, "market_price_correct"].mean())
            if informative.any() else None
        ),
        "family_on_market_informative_rows_accuracy": (
            float(work.loc[informative, "challenger_correct"].mean())
            if informative.any() else None
        ),
        "family_brier": _brier(y, work["challenger_p_over"]),
        "global_brier": _brier(y, work["global_p_over"]),
        "market_brier": _brier(y, work["market_no_vig_p_over"]),
        "v1_brier": _brier(y, work["p_over"]),
        "family_log_loss": _log_loss(y, work["challenger_p_over"]),
        "global_log_loss": _log_loss(y, work["global_p_over"]),
        "market_log_loss": _log_loss(y, work["market_no_vig_p_over"]),
        "v1_log_loss": _log_loss(y, work["p_over"]),
    }


def _cluster_ci(frame: pd.DataFrame, *, replicates: int, seed: int) -> dict:
    work = frame[
        frame["market_outcome_recomputed"].ne("PUSH")
        & frame["challenger_correct"].notna()
        & frame["global_correct"].notna()
    ].copy()
    games = np.asarray(sorted(work["game_id"].astype(str).unique()))
    if len(games) < 2:
        return {"family_accuracy_ci95": [None, None], "family_minus_global_ci95_pp": [None, None]}
    grouped = {g: work[work["game_id"].astype(str).eq(g)] for g in games}
    rng = np.random.default_rng(seed)
    acc = np.empty(replicates)
    diff = np.empty(replicates)
    for i in range(replicates):
        sample = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[g] for g in sample], ignore_index=True)
        acc[i] = boot["challenger_correct"].mean()
        diff[i] = 100.0 * (boot["challenger_correct"] - boot["global_correct"]).mean()
    return {
        "family_accuracy_ci95": [float(np.quantile(acc, .025)), float(np.quantile(acc, .975))],
        "family_minus_global_ci95_pp": [
            float(np.quantile(diff, .025)), float(np.quantile(diff, .975))
        ],
    }


def _evaluate_block(
    train: pd.DataFrame,
    evaluate: pd.DataFrame,
    *,
    seed: int,
) -> tuple[pd.DataFrame, dict]:
    family_models, skipped = _fit_family_models(train)
    if not family_models:
        raise ValueError("no prop family met the frozen minimum training sample")
    eligible = evaluate[evaluate["prop_type"].isin(family_models)].copy()
    global_model = fit_market_prior_residual(
        train[train["prop_type"].isin(family_models)].copy()
    )
    family = _apply_family_models(eligible, family_models)
    global_scored = _apply_global(eligible, global_model)
    paired = _merge_global(family, global_scored)

    overall = _metrics(paired)
    overall.update(_cluster_ci(paired, replicates=BOOTSTRAP_REPLICATES, seed=seed))
    overall["by_prop_type"] = {
        str(prop): _metrics(group)
        for prop, group in paired.groupby("prop_type", sort=True)
    }
    return paired, {
        "family_models": {prop: model.to_dict() for prop, model in family_models.items()},
        "global_model": global_model.to_dict(),
        "skipped_families": skipped,
        "evaluation": overall,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    data = _read(args.input)

    fixed_train = data[data["season"].eq(2023) & data["week"].le(9)].copy()
    fixed_eval = data[
        (data["season"].eq(2023) & data["week"].ge(10))
        | data["season"].isin([2024, 2025])
    ].copy()
    fixed_rows, fixed = _evaluate_block(fixed_train, fixed_eval, seed=BOOTSTRAP_SEED)

    rolling_parts = []
    rolling_results = {}
    for season in (2024, 2025):
        train = data[data["season"].ge(2023) & data["season"].lt(season)].copy()
        evaluate = data[data["season"].eq(season)].copy()
        rows, result = _evaluate_block(train, evaluate, seed=BOOTSTRAP_SEED + season)
        rows["evaluation_season"] = season
        rolling_parts.append(rows)
        rolling_results[str(season)] = result

    rolling_rows = pd.concat(rolling_parts, ignore_index=True)
    rolling_metrics = _metrics(rolling_rows)
    rolling_metrics.update(
        _cluster_ci(rolling_rows, replicates=BOOTSTRAP_REPLICATES, seed=BOOTSTRAP_SEED + 50)
    )
    rolling_metrics["by_evaluation_season"] = {
        season: result["evaluation"] for season, result in rolling_results.items()
    }

    fixed_metric = fixed["evaluation"]
    rolling_2024 = rolling_results["2024"]["evaluation"]
    decision = bool(
        fixed_metric["family_minus_global_pp"] > 0
        and rolling_2024["family_minus_global_pp"] > 0
        and rolling_metrics["family_brier"] <= rolling_metrics["global_brier"]
    )

    summary = {
        "contract_version": CONTRACT_VERSION,
        "research_label": RESEARCH_LABEL,
        "promotion_authorized": False,
        "historical_2023_2025_is_pristine_promotion_holdout": False,
        "selective_betting_threshold_used": False,
        "completed_2026_outcomes_used_for_tuning": 0,
        "minimum_training_rows_per_family": MIN_TRAINING_ROWS,
        "input_provenance": [_fingerprint(path) for path in args.input],
        "fixed_anchor": {
            "training_rule": "2023 Weeks 1-9 only; fixed thereafter",
            **fixed,
        },
        "rolling_origin": {
            "training_rule": "target season uses prior seasons beginning 2023",
            "models_by_season": {
                season: {
                    "family_models": result["family_models"],
                    "global_model": result["global_model"],
                    "skipped_families": result["skipped_families"],
                }
                for season, result in rolling_results.items()
            },
            "evaluation": rolling_metrics,
        },
        "preregistered_development_decision": {
            "development_improving": decision,
            "rule": (
                "fixed-anchor family-minus-global > 0; 2024 rolling family-minus-global > 0; "
                "and aggregate rolling family Brier <= global Brier"
            ),
            "production_promotion_authorized_by_decision": False,
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fixed_rows.to_csv(args.output_dir / "fixed_anchor_rows.csv", index=False)
    rolling_rows.to_csv(args.output_dir / "rolling_origin_rows.csv", index=False)
    print(json.dumps({
        "decision": summary["preregistered_development_decision"],
        "fixed_anchor": fixed["evaluation"],
        "rolling_origin": rolling_metrics,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
