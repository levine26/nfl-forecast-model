from __future__ import annotations

"""Run the single pre-registered F-LS-01 dynamic latent-state ablation."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd
import sklearn

from nfl_forecast.challenger import blend_probabilities, score_probabilities
from nfl_forecast.challenger_latent_state import TARGET_SEASONS, build_latent_research_frame
from nfl_forecast.config import load_config
from run_challenger_v08 import build_nested_research, nested_linear_hybrid

CANDIDATE_VERSION = "F-LS-01-dynamic-latent-state"
NULL_SEED = 20260910


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _feature_hash(features: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(features)).encode("utf-8")).hexdigest()


def _metric_row(label: str, target: pd.Series, probability) -> dict:
    return {"candidate": label, **score_probabilities(target, probability)}


def _permuted_latent_frame(
    historical: pd.DataFrame,
    latent_features: list[str],
    seed: int = NULL_SEED,
) -> pd.DataFrame:
    """Fixed-seed descriptive null: permute latent feature pairs within season-week."""
    rng = np.random.default_rng(seed)
    out = historical.copy()
    for _, index in out.groupby(["season", "week"], sort=True).groups.items():
        idx = np.asarray(list(index))
        if len(idx) < 2:
            continue
        order = rng.permutation(len(idx))
        values = out.loc[idx, latent_features].to_numpy(copy=True)
        out.loc[idx, latent_features] = values[order]
    return out


def run(
    config_path: str = "config/model.yaml",
    output_dir: str = "challenger_outputs/f_ls_01",
) -> dict:
    research = build_latent_research_frame(config_path)
    historical = research.historical
    cfg = load_config(config_path)
    seed = int(cfg["model"]["random_state"])

    _, production = build_nested_research(
        historical,
        research.feature_sets["production_compatible"],
        seed,
    )
    _, v08 = build_nested_research(
        historical,
        research.feature_sets["v08"],
        seed,
    )
    _, latent = build_nested_research(
        historical,
        research.feature_sets["v08_plus_latent"],
        seed,
    )
    v08_adaptive = nested_linear_hybrid(v08, objective="brier")
    latent_adaptive = nested_linear_hybrid(latent, objective="brier")

    permuted_historical = _permuted_latent_frame(historical, research.latent_features)
    _, latent_null = build_nested_research(
        permuted_historical,
        research.feature_sets["v08_plus_latent"],
        seed,
    )
    latent_null_adaptive = nested_linear_hybrid(latent_null, objective="brier")

    target_frames = {
        "production": production[production.season.isin(TARGET_SEASONS)],
        "v08": v08[v08.season.isin(TARGET_SEASONS)],
        "latent": latent[latent.season.isin(TARGET_SEASONS)],
        "latent_null": latent_null[latent_null.season.isin(TARGET_SEASONS)],
    }
    common = target_frames["production"].index
    for frame in target_frames.values():
        common = common.intersection(frame.index)
    common = common.intersection(v08_adaptive.predictions.index)
    common = common.intersection(latent_adaptive.predictions.index)
    common = common.intersection(latent_null_adaptive.predictions.index)
    if len(common) < 1000:
        raise RuntimeError(f"F-LS-01 paired target sample unexpectedly small: {len(common)}")

    production_target = target_frames["production"].loc[common]
    v08_target = target_frames["v08"].loc[common]
    latent_target = target_frames["latent"].loc[common]

    paired = historical.loc[common, ["game_id", "season", "week", "home_win"]].copy()
    paired["market"] = pd.to_numeric(historical.loc[common, "market_home_prob"], errors="coerce")
    paired["production_75_25"] = blend_probabilities(
        production_target.pure_prob,
        production_target.market_prob,
        0.75,
    )
    paired["v08_pure"] = pd.to_numeric(v08_target.pure_prob, errors="coerce")
    paired["v08_adaptive_brier"] = pd.to_numeric(
        v08_adaptive.predictions.loc[common, "probability"], errors="coerce"
    )
    paired["latent_pure"] = pd.to_numeric(latent_target.pure_prob, errors="coerce")
    paired["latent_75_25"] = blend_probabilities(
        latent_target.pure_prob,
        latent_target.market_prob,
        0.75,
    )
    paired["latent_adaptive_brier"] = pd.to_numeric(
        latent_adaptive.predictions.loc[common, "probability"], errors="coerce"
    )
    paired["permuted_latent_adaptive_brier"] = pd.to_numeric(
        latent_null_adaptive.predictions.loc[common, "probability"], errors="coerce"
    )

    candidates = [
        "market",
        "production_75_25",
        "v08_pure",
        "v08_adaptive_brier",
        "latent_pure",
        "latent_75_25",
        "latent_adaptive_brier",
        "permuted_latent_adaptive_brier",
    ]
    if paired[candidates].isna().any().any():
        bad = paired[candidates].isna().sum()
        raise RuntimeError(f"F-LS-01 paired predictions contain missing values: {bad[bad.gt(0)].to_dict()}")

    overall = pd.DataFrame([_metric_row(column, paired.home_win, paired[column]) for column in candidates])
    season_rows: list[dict] = []
    for season in TARGET_SEASONS:
        piece = paired[paired.season.eq(season)]
        for column in candidates:
            season_rows.append({"season": season, **_metric_row(column, piece.home_win, piece[column])})
    season_metrics = pd.DataFrame(season_rows)

    stability_rows: list[dict] = []
    for season, piece in historical.groupby("season", sort=True):
        for feature in research.latent_features:
            values = pd.to_numeric(piece[feature], errors="coerce")
            known = values.dropna()
            stability_rows.append(
                {
                    "season": int(season),
                    "feature": feature,
                    "rows": int(len(values)),
                    "missing_rate": float(values.isna().mean()),
                    "mean": float(known.mean()) if len(known) else None,
                    "std": float(known.std(ddof=0)) if len(known) else None,
                    "p10": float(known.quantile(0.10)) if len(known) else None,
                    "p50": float(known.quantile(0.50)) if len(known) else None,
                    "p90": float(known.quantile(0.90)) if len(known) else None,
                }
            )
    feature_stability = pd.DataFrame(stability_rows)

    metrics = overall.set_index("candidate")
    increments = {
        "latent_over_v08_pure": {
            "winner_pp": float(100.0 * (metrics.loc["latent_pure", "winner_pct"] - metrics.loc["v08_pure", "winner_pct"])),
            "brier_delta": float(metrics.loc["latent_pure", "brier"] - metrics.loc["v08_pure", "brier"]),
            "log_loss_delta": float(metrics.loc["latent_pure", "log_loss"] - metrics.loc["v08_pure", "log_loss"]),
        },
        "latent_over_v08_adaptive": {
            "winner_pp": float(100.0 * (metrics.loc["latent_adaptive_brier", "winner_pct"] - metrics.loc["v08_adaptive_brier", "winner_pct"])),
            "brier_delta": float(metrics.loc["latent_adaptive_brier", "brier"] - metrics.loc["v08_adaptive_brier", "brier"]),
            "log_loss_delta": float(metrics.loc["latent_adaptive_brier", "log_loss"] - metrics.loc["v08_adaptive_brier", "log_loss"]),
        },
        "latent_over_permutation_null": {
            "winner_pp": float(100.0 * (metrics.loc["latent_adaptive_brier", "winner_pct"] - metrics.loc["permuted_latent_adaptive_brier", "winner_pct"])),
            "brier_delta": float(metrics.loc["latent_adaptive_brier", "brier"] - metrics.loc["permuted_latent_adaptive_brier", "brier"]),
            "log_loss_delta": float(metrics.loc["latent_adaptive_brier", "log_loss"] - metrics.loc["permuted_latent_adaptive_brier", "log_loss"]),
        },
    }

    report = {
        "status": "healthy",
        "mode": "research_only",
        "experiment_id": "F-LS-01",
        "candidate_version": CANDIDATE_VERSION,
        "hypothesis": "weekly-frozen opponent-corrected latent offense/defense state adds incremental signal beyond v0.8",
        "candidate_search_policy": "one pre-registered gain/carry recursion and exactly two latent features; no grid or subset search",
        "target_seasons": list(TARGET_SEASONS),
        "paired_target_games": int(len(paired)),
        "2026_outcomes_used": 0,
        "same_week_updates_used_for_same_week_features": 0,
        "hyperparameter_search_performed": False,
        "promotion_authorized": False,
        "shadow_authorized": False,
        "increments": increments,
        "overall_metrics": json.loads(overall.to_json(orient="records")),
        "latent_state_audit": research.latent_audit,
        "null_diagnostic": {
            "seed": NULL_SEED,
            "policy": "latent feature pairs permuted within season-week; descriptive only",
        },
        "reproducibility": {
            "git_sha": _git_sha(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "random_seed": seed,
            "feature_set_hash": _feature_hash(research.latent_features),
            "latent_feature_columns": research.latent_features,
            "counts": research.counts,
            "package_versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scikit_learn": sklearn.__version__,
            },
            "exclusions": {
                "2026_outcomes": 0,
                "current_game_epa": 0,
                "future_depth_charts": 0,
                "market_probability_as_latent_feature": 0,
                "post_result_hyperparameter_search": 0,
            },
        },
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paired.to_csv(out / "paired_predictions_2022_2025.csv", index=False)
    overall.to_csv(out / "overall_metrics.csv", index=False)
    season_metrics.to_csv(out / "season_metrics.csv", index=False)
    feature_stability.to_csv(out / "latent_feature_stability.csv", index=False)
    v08_adaptive.weights.to_csv(out / "v08_adaptive_weights.csv", index=False)
    latent_adaptive.weights.to_csv(out / "latent_adaptive_weights.csv", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== F-LS-01 DYNAMIC LATENT-STATE ABLATION: 2022-25 OOS ===")
    print(overall.to_string(index=False))
    print("\nIncremental deltas (negative Brier/log-loss delta is better):")
    print(json.dumps(increments, indent=2))
    print("2026 outcomes used: 0")
    print("same-week updates used for same-week features: 0")
    print("production outputs modified: 0")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="challenger_outputs/f_ls_01")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()
