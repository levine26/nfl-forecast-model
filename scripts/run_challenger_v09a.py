from __future__ import annotations

"""Run the precommitted LevLine v0.9A player-value ablations.

The candidate search is intentionally narrow: player-state signal is tested once over the
production-compatible football feature family and once over the existing v0.8
opponent-adjusted + QB family. Each feature family is reported as PURE, fixed 75/25 and
one chronologically tuned adaptive-Brier hybrid. 2026 is not loaded by this runner and no
candidate is promoted or written to production outputs.
"""

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
from nfl_forecast.challenger_v09a import HISTORICAL_END, TARGET_SEASONS, build_v09a_research_frame
from run_challenger_v08 import build_nested_research, nested_linear_hybrid

CANDIDATE_VERSION = "0.9A-player-value"
FEATURE_SET_ORDER = (
    "production_compatible",
    "opponent_adjusted_qb",
    "production_plus_player",
    "opponent_adjusted_qb_plus_player",
)


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _feature_hash(features: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(features)).encode("utf-8")).hexdigest()


def _metric_row(label: str, target: pd.Series, probability: pd.Series | np.ndarray) -> dict:
    return {"candidate": label, **score_probabilities(target, probability)}


def _target(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[pd.to_numeric(frame["season"], errors="coerce").isin(TARGET_SEASONS)].copy()


def _season_metrics(predictions: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for season in TARGET_SEASONS:
        piece = predictions[predictions.season.eq(season)]
        for column in columns:
            rows.append({"season": season, **_metric_row(column, piece.home_win, piece[column])})
    return pd.DataFrame(rows)


def _feature_stability(historical: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    rows: list[dict] = []
    for season, piece in historical.groupby("season", sort=True):
        for feature in features:
            values = pd.to_numeric(piece[feature], errors="coerce")
            known = values.dropna()
            rows.append(
                {
                    "season": int(season),
                    "feature": feature,
                    "rows": int(len(values)),
                    "known": int(len(known)),
                    "missing_rate": float(values.isna().mean()),
                    "mean": float(known.mean()) if len(known) else None,
                    "std": float(known.std(ddof=0)) if len(known) else None,
                    "p10": float(known.quantile(0.10)) if len(known) else None,
                    "p50": float(known.quantile(0.50)) if len(known) else None,
                    "p90": float(known.quantile(0.90)) if len(known) else None,
                }
            )
    return pd.DataFrame(rows)


def run(
    config_path: str = "config/model.yaml",
    output_dir: str = "challenger_outputs/v09a",
) -> dict:
    research = build_v09a_research_frame(config_path)
    historical = research.historical.copy()
    seed = 26

    nested: dict[str, pd.DataFrame] = {}
    adaptive: dict[str, object] = {}
    for key in FEATURE_SET_ORDER:
        _, nested[key] = build_nested_research(historical, research.feature_sets[key], seed)
        adaptive[key] = nested_linear_hybrid(nested[key], objective="brier")

    target_frames = {key: _target(frame) for key, frame in nested.items()}
    common = target_frames[FEATURE_SET_ORDER[0]].index
    for key in FEATURE_SET_ORDER[1:]:
        common = common.intersection(target_frames[key].index)
    for key in FEATURE_SET_ORDER:
        common = common.intersection(adaptive[key].predictions.index)
    if len(common) < 1000:
        raise RuntimeError(f"v0.9A paired target sample unexpectedly small: {len(common)}")

    base = target_frames["production_compatible"].loc[common]
    v08 = target_frames["opponent_adjusted_qb"].loc[common]
    player = target_frames["production_plus_player"].loc[common]
    v08_player = target_frames["opponent_adjusted_qb_plus_player"].loc[common]

    predictions = historical.loc[common, ["game_id", "season", "week", "home_win"]].copy()
    predictions["market"] = pd.to_numeric(base["market_prob"], errors="coerce")
    predictions["production_pure"] = pd.to_numeric(base["pure_prob"], errors="coerce")
    predictions["production_75_25"] = blend_probabilities(base.pure_prob, base.market_prob, 0.75)
    predictions["v08_pure"] = pd.to_numeric(v08["pure_prob"], errors="coerce")
    predictions["v08_adaptive_brier"] = adaptive["opponent_adjusted_qb"].predictions.loc[common, "probability"]
    predictions["v09a_player_pure"] = pd.to_numeric(player["pure_prob"], errors="coerce")
    predictions["v09a_player_75_25"] = blend_probabilities(player.pure_prob, player.market_prob, 0.75)
    predictions["v09a_player_adaptive_brier"] = adaptive["production_plus_player"].predictions.loc[common, "probability"]
    predictions["v09a_v08_player_pure"] = pd.to_numeric(v08_player["pure_prob"], errors="coerce")
    predictions["v09a_v08_player_75_25"] = blend_probabilities(v08_player.pure_prob, v08_player.market_prob, 0.75)
    predictions["v09a_v08_player_adaptive_brier"] = adaptive["opponent_adjusted_qb_plus_player"].predictions.loc[common, "probability"]

    candidate_columns = [
        "market",
        "production_pure",
        "production_75_25",
        "v08_pure",
        "v08_adaptive_brier",
        "v09a_player_pure",
        "v09a_player_75_25",
        "v09a_player_adaptive_brier",
        "v09a_v08_player_pure",
        "v09a_v08_player_75_25",
        "v09a_v08_player_adaptive_brier",
    ]
    if predictions[candidate_columns].isna().any().any():
        bad = predictions[candidate_columns].isna().sum()
        raise RuntimeError(f"Paired v0.9A sample has missing probabilities: {bad[bad.gt(0)].to_dict()}")

    overall = pd.DataFrame(
        [_metric_row(column, predictions.home_win, predictions[column]) for column in candidate_columns]
    )
    by_season = _season_metrics(predictions, candidate_columns)
    stability = _feature_stability(historical, research.player_feature_columns)
    weight_rows: list[pd.DataFrame] = []
    for key in FEATURE_SET_ORDER:
        weights = adaptive[key].weights.copy()
        weights.insert(0, "feature_set", key)
        weight_rows.append(weights)
    weights = pd.concat(weight_rows, ignore_index=True)

    metrics = overall.set_index("candidate")
    increments = {
        "player_over_production_pure": {
            "winner_pp": float(100.0 * (metrics.loc["v09a_player_pure", "winner_pct"] - metrics.loc["production_pure", "winner_pct"])),
            "brier_delta": float(metrics.loc["v09a_player_pure", "brier"] - metrics.loc["production_pure", "brier"]),
            "log_loss_delta": float(metrics.loc["v09a_player_pure", "log_loss"] - metrics.loc["production_pure", "log_loss"]),
        },
        "player_over_v08_pure": {
            "winner_pp": float(100.0 * (metrics.loc["v09a_v08_player_pure", "winner_pct"] - metrics.loc["v08_pure", "winner_pct"])),
            "brier_delta": float(metrics.loc["v09a_v08_player_pure", "brier"] - metrics.loc["v08_pure", "brier"]),
            "log_loss_delta": float(metrics.loc["v09a_v08_player_pure", "log_loss"] - metrics.loc["v08_pure", "log_loss"]),
        },
        "player_over_v08_adaptive": {
            "winner_pp": float(100.0 * (metrics.loc["v09a_v08_player_adaptive_brier", "winner_pct"] - metrics.loc["v08_adaptive_brier", "winner_pct"])),
            "brier_delta": float(metrics.loc["v09a_v08_player_adaptive_brier", "brier"] - metrics.loc["v08_adaptive_brier", "brier"]),
            "log_loss_delta": float(metrics.loc["v09a_v08_player_adaptive_brier", "log_loss"] - metrics.loc["v08_adaptive_brier", "log_loss"]),
        },
    }

    feature_missing = {
        feature: float(pd.to_numeric(historical[feature], errors="coerce").isna().mean())
        for feature in research.player_feature_columns
    }
    report = {
        "status": "healthy",
        "mode": "research_only",
        "candidate_version": CANDIDATE_VERSION,
        "historical_selection_seasons": list(TARGET_SEASONS),
        "data_seasons": [int(x) for x in sorted(historical.season.unique())],
        "maximum_pbp_season": HISTORICAL_END,
        "paired_target_games": int(len(predictions)),
        "2026_outcomes_used": 0,
        "candidate_search_policy": "two precommitted player-value feature-family ablations; no combinatorial feature fishing",
        "promotion_authorized": False,
        "shadow_authorized": False,
        "increments": increments,
        "overall_metrics": json.loads(overall.to_json(orient="records")),
        "player_data_audit": research.player_audit,
        "reproducibility": {
            "git_sha": _git_sha(),
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "random_seed": seed,
            "feature_set_hash": _feature_hash(research.player_feature_columns),
            "player_feature_columns": research.player_feature_columns,
            "counts": research.counts,
            "feature_missing_rates": feature_missing,
            "package_versions": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scikit_learn": sklearn.__version__,
            },
            "exclusions": {
                "2026_outcomes": 0,
                "post_kickoff_current_game_player_state": 0,
                "future_depth_chart": 0,
                "fuzzy_player_identity_matches": 0,
            },
        },
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(out / "paired_predictions_2022_2025.csv", index=False)
    overall.to_csv(out / "overall_metrics.csv", index=False)
    by_season.to_csv(out / "season_metrics.csv", index=False)
    stability.to_csv(out / "player_feature_stability.csv", index=False)
    weights.to_csv(out / "adaptive_weights.csv", index=False)
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== LEVLINE v0.9A PLAYER-VALUE ABLATION: LEAKAGE-SAFE 2022-25 ===")
    print(overall.to_string(index=False))
    print("\nIncremental deltas (negative Brier/log-loss delta is better):")
    print(json.dumps(increments, indent=2))
    print(f"paired games: {len(predictions)}")
    print("2026 outcomes used: 0")
    print("production outputs modified: 0")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="challenger_outputs/v09a")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()
