from __future__ import annotations

"""Run the pre-registered Phase 3 coherent joint-distribution experiment."""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_evaluation import paired_bootstrap
from nfl_forecast.challenger_joint_distribution import (
    blocked_continuous_bootstrap,
    result_dict,
    season_forward_joint_distribution,
    summarize_joint_distribution,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import (
    add_game_results,
    aggregate_team_games,
    build_matchup_features,
    core_columns,
)
from nfl_forecast.market import add_vig_free_market_prob


def _bootstrap_dict(result) -> dict:
    return {
        "metric": result.metric,
        "candidate": result.candidate,
        "reference": result.reference,
        "block": result.block,
        "observed_delta": float(result.observed_delta),
        "ci_lower": float(result.ci_lower),
        "ci_upper": float(result.ci_upper),
        "probability_better": float(result.probability_better),
        "samples": int(result.samples),
    }


def _continuous(
    predictions: pd.DataFrame,
    candidate: str,
    reference: str,
    metric: str,
    samples: int,
    seed: int,
) -> dict:
    return result_dict(
        blocked_continuous_bootstrap(
            predictions,
            candidate,
            reference,
            metric=metric,
            samples=samples,
            seed=seed,
        )
    )


def run(
    output_dir: str = "research_outputs/phase3_joint_distribution",
    *,
    config_path: str = "config/model.yaml",
    bootstrap_samples: int = 2000,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, 2026))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    advanced_start = int(cfg["data"]["advanced_start_season"])
    bundle = load_advanced_data(bundle, range(advanced_start, 2026))

    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(
        bundle.pbp,
        cfg["data"]["neutral_wp_lower"],
        cfg["data"]["neutral_wp_upper"],
    )
    team_games = add_game_results(team_games, bundle.schedules)
    games = build_matchup_features(team_games, bundle.schedules, elo)
    games = add_vig_free_market_prob(games)

    historical = games[
        pd.to_numeric(games.season, errors="coerce").le(2025)
        & games.margin.notna()
        & games.game_total.notna()
        & games.spread_line.notna()
        & games.total_line.notna()
        & games.market_home_prob.notna()
    ].copy()
    if historical.empty:
        raise RuntimeError("No historical rows available for Phase 3")
    if pd.to_numeric(historical.season, errors="coerce").max() > 2025:
        raise RuntimeError("Phase 3 historical cutoff failed")

    features = core_columns(historical)
    predictions, diagnostics = season_forward_joint_distribution(historical, features)
    summary = summarize_joint_distribution(predictions)

    probability_uncertainty = []
    for offset, metric in enumerate(("brier", "log_loss", "accuracy")):
        probability_uncertainty.append(
            _bootstrap_dict(
                paired_bootstrap(
                    predictions,
                    "candidate_home_win_prob",
                    "market_home_prob",
                    metric=metric,
                    target_col="home_win",
                    block_cols=("season", "week"),
                    samples=bootstrap_samples,
                    seed=303 + offset,
                )
            )
        )

    continuous_uncertainty = [
        _continuous(predictions, "candidate_margin_abs_error", "market_margin_abs_error", "margin_mae", bootstrap_samples, 310),
        _continuous(predictions, "candidate_total_abs_error", "market_total_abs_error", "total_mae", bootstrap_samples, 311),
        _continuous(predictions, "candidate_margin_crps", "market_margin_crps", "margin_crps", bootstrap_samples, 312),
        _continuous(predictions, "candidate_total_crps", "market_total_crps", "total_crps", bootstrap_samples, 313),
        _continuous(predictions, "candidate_joint_nll", "market_joint_nll", "joint_nll", bootstrap_samples, 314),
    ]
    if {
        "candidate_home_score_abs_error", "market_home_score_abs_error",
        "candidate_away_score_abs_error", "market_away_score_abs_error",
    }.issubset(predictions.columns):
        continuous_uncertainty.extend(
            [
                _continuous(predictions, "candidate_home_score_abs_error", "market_home_score_abs_error", "home_score_mae", bootstrap_samples, 315),
                _continuous(predictions, "candidate_away_score_abs_error", "market_away_score_abs_error", "away_score_mae", bootstrap_samples, 316),
            ]
        )

    brier = next(x for x in probability_uncertainty if x["metric"] == "brier")
    logloss = next(x for x in probability_uncertainty if x["metric"] == "log_loss")
    margin_mae = next(x for x in continuous_uncertainty if x["metric"] == "margin_mae")
    total_mae = next(x for x in continuous_uncertainty if x["metric"] == "total_mae")

    probability_not_supported_worse = not (brier["ci_lower"] > 0.0 or logloss["ci_lower"] > 0.0)
    margin_supported_better = margin_mae["ci_upper"] < 0.0
    total_supported_better = total_mae["ci_upper"] < 0.0
    coherent = int(summary["coherence_failures"]) == 0
    historically_qualified = bool(
        probability_not_supported_worse
        and margin_supported_better
        and total_supported_better
        and coherent
    )

    predictions.to_csv(out / "phase3_oof_predictions_2022_2025.csv", index=False)
    diagnostics.to_csv(out / "phase3_season_diagnostics.csv", index=False)
    pd.DataFrame(probability_uncertainty).to_csv(out / "phase3_probability_uncertainty.csv", index=False)
    pd.DataFrame(continuous_uncertainty).to_csv(out / "phase3_continuous_uncertainty.csv", index=False)

    report = {
        "status": "historically_qualified" if historically_qualified else "not_historically_qualified",
        "mode": "research_only",
        "experiment_id": "PHASE3-JOINT-DIST-001",
        "candidate_version": "market-anchored-joint-distribution-v1",
        "production_changed": False,
        "promotion_authorized": False,
        "2026_outcomes_used": 0,
        "historical_market_timing_caveat": (
            "Historical spread, total, and moneyline fields are closing-like benchmarks, not a matched T-minus-120 snapshot."
        ),
        "features": features,
        "summary": summary,
        "probability_uncertainty_vs_raw_market": probability_uncertainty,
        "continuous_uncertainty_vs_market": continuous_uncertainty,
        "qualification_gates": {
            "probability_not_statistically_supported_worse": probability_not_supported_worse,
            "margin_mae_supported_better": margin_supported_better,
            "total_mae_supported_better": total_supported_better,
            "zero_coherence_failures": coherent,
            "historically_qualified": historically_qualified,
        },
        "decision_rule": (
            "Historical qualification alone never authorizes production. A successor would also require matched-horizon prospective evidence and explicit user promotion authorization."
        ),
    }
    (out / "phase3_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/phase3_joint_distribution")
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config, bootstrap_samples=args.bootstrap_samples)


if __name__ == "__main__":
    main()
