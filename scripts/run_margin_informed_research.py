from __future__ import annotations

"""Run pre-registered F-MI-01 expected-margin challenger on 2022-2025 OOS games."""

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
from nfl_forecast.challenger_historical import build_historical_challenger_frame
from nfl_forecast.margin_informed_research import RIDGE_ALPHA, MAPPER_C, season_forward_margin_informed
from run_challenger_v08 import TARGET_SEASONS, build_nested_research, nested_linear_hybrid

EXPERIMENT_ID = "F-MI-01"
CANDIDATE_VERSION = "orthogonal-margin-informed-v1"


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _feature_hash(features: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(features)).encode("utf-8")).hexdigest()


def _metrics(label: str, y: pd.Series, probability) -> dict:
    return {"candidate": label, **score_probabilities(y, probability)}


def run(
    config_path: str = "config/model.yaml",
    output_dir: str = "research_outputs/orthogonal/margin_informed",
) -> dict:
    research = build_historical_challenger_frame(config_path, end_season=2025)
    historical = research.games
    features = research.feature_sets["opponent_adjusted_qb"]
    seed = int(research.config["model"]["random_state"])

    margin_result = season_forward_margin_informed(
        historical,
        features,
        target_seasons=TARGET_SEASONS,
        alpha=RIDGE_ALPHA,
    )
    _, production_research = build_nested_research(
        historical,
        research.feature_sets["production_compatible"],
        seed,
    )
    _, v08_research = build_nested_research(historical, features, seed)
    v08_adaptive = nested_linear_hybrid(v08_research, objective="brier")

    margin_target = margin_result.predictions
    prod_target = production_research[production_research.season.isin(TARGET_SEASONS)]
    v08_target = v08_research[v08_research.season.isin(TARGET_SEASONS)]
    common = margin_target.index.intersection(prod_target.index).intersection(v08_target.index)
    common = common.intersection(v08_adaptive.predictions.index)
    if len(common) < 1000:
        raise RuntimeError(f"Margin-informed paired target sample unexpectedly small: {len(common)}")

    paired = historical.loc[common, ["game_id", "season", "week", "home_win", "margin"]].copy()
    paired["market"] = pd.to_numeric(historical.loc[common, "market_home_prob"], errors="coerce")
    paired["production_75_25"] = blend_probabilities(
        prod_target.loc[common, "pure_prob"],
        prod_target.loc[common, "market_prob"],
        0.75,
    )
    paired["v08_adaptive_brier"] = pd.to_numeric(
        v08_adaptive.predictions.loc[common, "probability"], errors="coerce"
    )
    paired["f_mi_01"] = pd.to_numeric(margin_target.loc[common, "probability"], errors="coerce")
    paired["f_mi_01_expected_margin"] = pd.to_numeric(
        margin_target.loc[common, "predicted_margin"], errors="coerce"
    )
    candidate_columns = ["market", "production_75_25", "v08_adaptive_brier", "f_mi_01"]
    if paired[candidate_columns].isna().any().any():
        raise RuntimeError("Margin-informed paired frame contains missing probabilities")

    overall = pd.DataFrame([_metrics(column, paired.home_win, paired[column]) for column in candidate_columns])
    season_rows: list[dict] = []
    for season in TARGET_SEASONS:
        piece = paired[paired.season.eq(season)]
        for column in candidate_columns:
            row = {"season": season, **_metrics(column, piece.home_win, piece[column])}
            if column == "f_mi_01":
                row["margin_mae"] = float(
                    np.mean(np.abs(piece["margin"].to_numpy(dtype=float) - piece["f_mi_01_expected_margin"].to_numpy(dtype=float)))
                )
            season_rows.append(row)
    by_season = pd.DataFrame(season_rows)
    metrics = overall.set_index("candidate")
    deltas = {
        "vs_market": {
            "winner_pp": float(100.0 * (metrics.loc["f_mi_01", "winner_pct"] - metrics.loc["market", "winner_pct"])),
            "brier_delta": float(metrics.loc["f_mi_01", "brier"] - metrics.loc["market", "brier"]),
            "log_loss_delta": float(metrics.loc["f_mi_01", "log_loss"] - metrics.loc["market", "log_loss"]),
        },
        "vs_v08_adaptive": {
            "winner_pp": float(100.0 * (metrics.loc["f_mi_01", "winner_pct"] - metrics.loc["v08_adaptive_brier", "winner_pct"])),
            "brier_delta": float(metrics.loc["f_mi_01", "brier"] - metrics.loc["v08_adaptive_brier", "brier"]),
            "log_loss_delta": float(metrics.loc["f_mi_01", "log_loss"] - metrics.loc["v08_adaptive_brier", "log_loss"]),
        },
    }
    margin_mae = float(
        np.mean(
            np.abs(
                paired["margin"].to_numpy(dtype=float)
                - paired["f_mi_01_expected_margin"].to_numpy(dtype=float)
            )
        )
    )

    report = {
        "status": "healthy",
        "mode": "research_only",
        "experiment_id": EXPERIMENT_ID,
        "candidate_version": CANDIDATE_VERSION,
        "ridge_alpha_precommitted": RIDGE_ALPHA,
        "probability_mapper_c_precommitted": MAPPER_C,
        "hyperparameter_search_performed": False,
        "target_seasons": list(TARGET_SEASONS),
        "paired_target_games": int(len(paired)),
        "expected_margin_mae": margin_mae,
        "2026_outcomes_used": 0,
        "market_used_as_model_feature": False,
        "promotion_authorized": False,
        "shadow_authorized": False,
        "deltas": deltas,
        "overall_metrics": json.loads(overall.to_json(orient="records")),
        "fit_diagnostics": json.loads(margin_result.diagnostics.to_json(orient="records")),
        "reproducibility": {
            "git_sha": _git_sha(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "data_seasons": sorted(int(value) for value in historical.season.unique()),
            "maximum_pbp_season": 2025,
            "feature_set_hash": _feature_hash(features),
            "feature_count": len(features),
            "random_seed": seed,
            "games": int(len(historical)),
            "package_versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scikit_learn": sklearn.__version__,
            },
            "exclusions": {
                "2026_outcomes": 0,
                "market_model_features": 0,
                "v09_player_features": 0,
                "post_kickoff_features": 0,
            },
        },
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paired.to_csv(out / "paired_predictions_2022_2025.csv", index=False)
    overall.to_csv(out / "overall_metrics.csv", index=False)
    by_season.to_csv(out / "season_metrics.csv", index=False)
    margin_result.diagnostics.to_csv(out / "fit_diagnostics.csv", index=False)
    margin_result.calibration_oof.to_csv(out / "calibration_oof_history.csv", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== F-MI-01 MARGIN-INFORMED: 2022-25 OOS ===")
    print(overall.to_string(index=False))
    print(f"expected margin MAE: {margin_mae:.4f}")
    print(json.dumps(deltas, indent=2))
    print("2026 outcomes used: 0")
    print("market used as model feature: 0")
    print("production outputs modified: 0")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="research_outputs/orthogonal/margin_informed")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()
