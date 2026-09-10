from __future__ import annotations

"""Run the single pre-registered LevLine v0.9C unit-continuity ablation."""

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
from nfl_forecast.challenger_v09c import TARGET_SEASONS, build_v09c_research_frame
from nfl_forecast.config import load_config
from run_challenger_v08 import build_nested_research, nested_linear_hybrid

CANDIDATE_VERSION = "0.9C-unit-continuity"


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _feature_hash(features: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(features)).encode("utf-8")).hexdigest()


def _metric_row(label: str, target: pd.Series, probability) -> dict:
    return {"candidate": label, **score_probabilities(target, probability)}


def run(
    config_path: str = "config/model.yaml",
    output_dir: str = "challenger_outputs/v09c",
) -> dict:
    research = build_v09c_research_frame(config_path)
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
        research.feature_sets["opponent_adjusted_qb"],
        seed,
    )
    _, v09c = build_nested_research(
        historical,
        research.feature_sets["opponent_adjusted_qb_plus_unit"],
        seed,
    )
    v08_adaptive = nested_linear_hybrid(v08, objective="brier")
    v09c_adaptive = nested_linear_hybrid(v09c, objective="brier")

    target_frames = {
        "production": production[production.season.isin(TARGET_SEASONS)],
        "v08": v08[v08.season.isin(TARGET_SEASONS)],
        "v09c": v09c[v09c.season.isin(TARGET_SEASONS)],
    }
    common = target_frames["production"].index
    common = common.intersection(target_frames["v08"].index)
    common = common.intersection(target_frames["v09c"].index)
    common = common.intersection(v08_adaptive.predictions.index)
    common = common.intersection(v09c_adaptive.predictions.index)
    if len(common) < 1000:
        raise RuntimeError(f"v0.9C paired target sample unexpectedly small: {len(common)}")

    production_target = target_frames["production"].loc[common]
    v08_target = target_frames["v08"].loc[common]
    v09c_target = target_frames["v09c"].loc[common]

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
    paired["v09c_unit_pure"] = pd.to_numeric(v09c_target.pure_prob, errors="coerce")
    paired["v09c_unit_75_25"] = blend_probabilities(
        v09c_target.pure_prob,
        v09c_target.market_prob,
        0.75,
    )
    paired["v09c_unit_adaptive_brier"] = pd.to_numeric(
        v09c_adaptive.predictions.loc[common, "probability"], errors="coerce"
    )

    candidate_columns = [
        "market",
        "production_75_25",
        "v08_pure",
        "v08_adaptive_brier",
        "v09c_unit_pure",
        "v09c_unit_75_25",
        "v09c_unit_adaptive_brier",
    ]
    if paired[candidate_columns].isna().any().any():
        bad = paired[candidate_columns].isna().sum()
        raise RuntimeError(f"v0.9C paired predictions contain missing values: {bad[bad.gt(0)].to_dict()}")

    overall = pd.DataFrame(
        [_metric_row(column, paired.home_win, paired[column]) for column in candidate_columns]
    )
    season_rows: list[dict] = []
    for season in TARGET_SEASONS:
        piece = paired[paired.season.eq(season)]
        for column in candidate_columns:
            season_rows.append({"season": season, **_metric_row(column, piece.home_win, piece[column])})
    season_metrics = pd.DataFrame(season_rows)

    feature_stability_rows: list[dict] = []
    for season, piece in historical.groupby("season", sort=True):
        for feature in research.unit_features:
            values = pd.to_numeric(piece[feature], errors="coerce")
            known = values.dropna()
            feature_stability_rows.append(
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
    feature_stability = pd.DataFrame(feature_stability_rows)

    metrics = overall.set_index("candidate")
    increments = {
        "unit_over_v08_pure": {
            "winner_pp": float(100.0 * (metrics.loc["v09c_unit_pure", "winner_pct"] - metrics.loc["v08_pure", "winner_pct"])),
            "brier_delta": float(metrics.loc["v09c_unit_pure", "brier"] - metrics.loc["v08_pure", "brier"]),
            "log_loss_delta": float(metrics.loc["v09c_unit_pure", "log_loss"] - metrics.loc["v08_pure", "log_loss"]),
        },
        "unit_over_v08_adaptive": {
            "winner_pp": float(100.0 * (metrics.loc["v09c_unit_adaptive_brier", "winner_pct"] - metrics.loc["v08_adaptive_brier", "winner_pct"])),
            "brier_delta": float(metrics.loc["v09c_unit_adaptive_brier", "brier"] - metrics.loc["v08_adaptive_brier", "brier"]),
            "log_loss_delta": float(metrics.loc["v09c_unit_adaptive_brier", "log_loss"] - metrics.loc["v08_adaptive_brier", "log_loss"]),
        },
    }

    report = {
        "status": "healthy",
        "mode": "research_only",
        "candidate_version": CANDIDATE_VERSION,
        "hypothesis": "two-prior-game snap continuity and rotation state adds incremental signal beyond v0.8",
        "candidate_search_policy": "one pre-registered 11-feature unit vector; no subset search and no new hyperparameter grid",
        "target_seasons": list(TARGET_SEASONS),
        "paired_target_games": int(len(paired)),
        "2026_outcomes_used": 0,
        "current_game_snaps_used": 0,
        "promotion_authorized": False,
        "shadow_authorized": False,
        "increments": increments,
        "overall_metrics": json.loads(overall.to_json(orient="records")),
        "unit_data_audit": research.unit_audit,
        "reproducibility": {
            "git_sha": _git_sha(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "random_seed": seed,
            "feature_set_hash": _feature_hash(research.unit_features),
            "unit_feature_columns": research.unit_features,
            "counts": research.counts,
            "package_versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scikit_learn": sklearn.__version__,
            },
            "exclusions": {
                "2026_outcomes": 0,
                "current_game_snap_counts": 0,
                "future_depth_charts": 0,
                "retrospective_inactive_status": 0,
                "fuzzy_player_identity_matches": 0,
            },
        },
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paired.to_csv(out / "paired_predictions_2022_2025.csv", index=False)
    overall.to_csv(out / "overall_metrics.csv", index=False)
    season_metrics.to_csv(out / "season_metrics.csv", index=False)
    feature_stability.to_csv(out / "unit_feature_stability.csv", index=False)
    v09c_adaptive.weights.to_csv(out / "adaptive_weights.csv", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== LEVLINE v0.9C UNIT-CONTINUITY ABLATION: 2022-25 OOS ===")
    print(overall.to_string(index=False))
    print("\nIncremental deltas (negative Brier/log-loss delta is better):")
    print(json.dumps(increments, indent=2))
    print("2026 outcomes used: 0")
    print("current-game snaps used: 0")
    print("production outputs modified: 0")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="challenger_outputs/v09c")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()
