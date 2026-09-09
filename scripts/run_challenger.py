from __future__ import annotations

"""Run the LevLine v0.5 challenger completely outside production outputs.

The research contract is strict:
- 2026 outcomes are never used for fitting, tuning, or calibration.
- Target-season backtests are nested by season.
- The current production 75% PURE / 25% MARKET model is never modified here.
- Results are written only to challenger_outputs/.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger import (
    BASE_MODEL_NAMES,
    blend_probabilities,
    build_base_oof_predictions,
    build_nested_stack_oof,
    choose_shadow_candidate,
    fit_calibrator,
    fit_future_nested_stack,
    fixed_blend_backtest,
    nested_blend_backtest,
    score_probabilities,
    select_pure_weight,
    weight_sweep,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import (
    add_game_results,
    aggregate_team_games,
    build_matchup_features,
    core_columns,
)
from nfl_forecast.market import add_vig_free_market_prob


LIVE_SEASON = 2026
TARGET_SEASONS = (2022, 2023, 2024, 2025)
BASE_OOF_START = 2018
PRODUCTION_LABEL = "Nested 75% PURE / 25% MARKET"


def _metric_row(candidate: str, metrics: dict[str, float], **extra) -> dict:
    return {"candidate": candidate, **metrics, **extra}


def _safe_float(value):
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except Exception:
        return None


def _jsonable_record(row: pd.Series | dict) -> dict:
    items = row.to_dict() if hasattr(row, "to_dict") else dict(row)
    out = {}
    for key, value in items.items():
        if isinstance(value, (np.integer,)):
            out[key] = int(value)
        elif isinstance(value, (np.floating, float)):
            out[key] = _safe_float(value)
        else:
            out[key] = value
    return out


def build_research_frame(config_path: str):
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    bundle = load_core_data(range(start, LIVE_SEASON + 1), cfg["data"]["cache_dir"])
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

    # This is the firewall that keeps the 2026 forward test sacred even after
    # 2026 games start finishing and appear in the live schedule/PBP sources.
    historical = games[
        games["home_win"].notna() & (pd.to_numeric(games["season"], errors="coerce") < LIVE_SEASON)
    ].copy()
    current_pool = games[
        (pd.to_numeric(games["season"], errors="coerce") == LIVE_SEASON)
        & games["home_win"].isna()
    ].copy()
    if historical.empty:
        raise RuntimeError("No pre-2026 historical games available for challenger research")
    if current_pool.empty:
        raise RuntimeError("No unresolved 2026 games available for challenger shadow")
    next_week = int(pd.to_numeric(current_pool["week"], errors="coerce").min())
    current = current_pool[pd.to_numeric(current_pool["week"], errors="coerce").eq(next_week)].copy()
    features = core_columns(historical)
    if not features:
        raise RuntimeError("No production-compatible football features available")
    return cfg, games, historical, current, features


def run(config_path: str = "config/model.yaml", output_dir: str = "challenger_outputs") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg, games, historical, current, feature_cols = build_research_frame(config_path)
    seed = int(cfg["model"]["random_state"])

    base_oof = build_base_oof_predictions(
        historical,
        feature_cols,
        seed=seed,
        validation_start=BASE_OOF_START,
        validation_end=max(TARGET_SEASONS),
    )
    nested = build_nested_stack_oof(
        base_oof,
        target_seasons=TARGET_SEASONS,
        seed=seed,
    )

    # Attach market probabilities by the original game-row index.  This keeps
    # the nested PURE forecast aligned with the exact same held-out game.
    research = base_oof[["home_win", "season"]].copy()
    research["market_prob"] = pd.to_numeric(
        historical.loc[research.index, "market_home_prob"], errors="coerce"
    )
    research["pure_prob"] = np.nan
    research.loc[nested.target_oof.index, "pure_prob"] = nested.target_oof["pure_prob"]

    # Earlier OOF seasons also need a leakage-safe PURE value so they can tune
    # the 2022+ market blend. Build each such season's meta model only from OOF
    # seasons before it. The first two OOF seasons may lack enough meta history;
    # those rows are deliberately excluded from blend tuning.
    early_target = sorted(int(s) for s in base_oof["season"].unique() if int(s) < min(TARGET_SEASONS))
    for season in early_target:
        meta_train = base_oof[base_oof["season"] < season]
        test = base_oof[base_oof["season"] == season]
        if len(meta_train) < 300 or test.empty:
            continue
        from nfl_forecast.challenger import _meta_template
        meta = _meta_template(seed)
        meta.fit(meta_train[list(BASE_MODEL_NAMES)], meta_train["home_win"].astype(int))
        research.loc[test.index, "pure_prob"] = meta.predict_proba(test[list(BASE_MODEL_NAMES)])[:, 1]

    research = research[research["pure_prob"].notna()].copy()
    if not set(TARGET_SEASONS).issubset(set(research["season"].astype(int).unique())):
        raise RuntimeError("Challenger research frame is missing one or more 2022-25 target seasons")

    metrics_rows: list[dict] = []
    target = research[research["season"].isin(TARGET_SEASONS)].copy()
    metrics_rows.append(_metric_row("Nested PURE", score_probabilities(target.home_win, target.pure_prob)))

    market_usable = target[target.market_prob.notna()]
    metrics_rows.append(_metric_row(
        "Market only",
        score_probabilities(market_usable.home_win, market_usable.market_prob),
    ))
    metrics_rows.append(_metric_row(
        PRODUCTION_LABEL,
        fixed_blend_backtest(research, 0.75, target_seasons=TARGET_SEASONS),
        pure_weight=0.75,
        market_weight=0.25,
        calibration="none",
        weight_objective="fixed",
    ))

    candidate_specs = [
        ("Adaptive Brier blend", "brier", "none"),
        ("Adaptive Brier + Platt", "brier", "platt"),
        ("Adaptive Brier + Isotonic", "brier", "isotonic"),
        ("Adaptive accuracy blend", "accuracy", "none"),
    ]
    backtests = {}
    for label, objective, calibration in candidate_specs:
        result = nested_blend_backtest(
            research,
            target_seasons=TARGET_SEASONS,
            weight_objective=objective,
            calibrator=calibration,
        )
        backtests[label] = result
        metrics_rows.append(_metric_row(
            label,
            result.metrics,
            pure_weight=np.nan,
            market_weight=np.nan,
            calibration=calibration,
            weight_objective=objective,
        ))
        result.weights.to_csv(out / f"weights_{label.lower().replace(' ', '_').replace('+', 'plus')}.csv", index=False)

    metrics = pd.DataFrame(metrics_rows)
    metrics["winner_pct"] = pd.to_numeric(metrics["winner_pct"], errors="coerce")
    metrics["brier"] = pd.to_numeric(metrics["brier"], errors="coerce")
    metrics["log_loss"] = pd.to_numeric(metrics["log_loss"], errors="coerce")
    selected = choose_shadow_candidate(metrics, PRODUCTION_LABEL)

    # Descriptive weight sweep on 2022-25. It is *not* used as the OOS score;
    # nested per-season tuning above is the valid model-selection estimate.
    weight_sweep(target).to_csv(out / "weight_sweep_2022_2025_descriptive.csv", index=False)
    base_oof.to_csv(out / "base_oof_2018_2025.csv", index=False)
    target.assign(game_index=target.index).to_csv(out / "nested_research_frame.csv", index=False)
    metrics.to_csv(out / "candidate_metrics.csv", index=False)

    # Build a 2026 shadow candidate using only pre-2026 evidence. Candidate type
    # is selected on 2022-25; its final weight/calibrator is then fitted using all
    # eligible pre-2026 OOF rows. This remains research-only and never touches
    # outputs/this_week.csv or the public site.
    selected_label = str(selected["candidate"])
    spec_lookup = {label: (objective, calibration) for label, objective, calibration in candidate_specs}
    if selected_label == PRODUCTION_LABEL:
        shadow_weight = 0.75
        shadow_calibration = "none"
        shadow_objective = "fixed"
    elif selected_label == "Nested PURE":
        shadow_weight = 1.0
        shadow_calibration = "none"
        shadow_objective = "fixed"
    elif selected_label == "Market only":
        shadow_weight = 0.0
        shadow_calibration = "none"
        shadow_objective = "fixed"
    else:
        shadow_objective, shadow_calibration = spec_lookup[selected_label]
        shadow_weight, _ = select_pure_weight(research, objective=shadow_objective)

    current_pure = fit_future_nested_stack(
        historical,
        base_oof,
        current,
        feature_cols,
        seed=seed,
    )
    current_market = pd.to_numeric(current["market_home_prob"], errors="coerce").to_numpy(dtype=float)
    current_raw = blend_probabilities(current_pure, current_market, shadow_weight)
    if shadow_calibration == "none":
        current_final = current_raw
    else:
        train_raw = blend_probabilities(research.pure_prob, research.market_prob, shadow_weight)
        calibrator = fit_calibrator(research.home_win, train_raw, mode=shadow_calibration)
        current_final = calibrator.predict(current_raw)

    shadow = current[[
        "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
        "spread_line", "total_line",
    ]].copy()
    shadow["challenger_pure_home_prob"] = current_pure
    shadow["market_home_prob"] = current_market
    shadow["challenger_final_home_prob"] = current_final
    shadow["challenger_pick"] = np.where(current_final >= 0.5, shadow.home_team, shadow.away_team)
    shadow["challenger_pure_weight"] = shadow_weight
    shadow["challenger_market_weight"] = 1.0 - shadow_weight
    shadow["challenger_calibration"] = shadow_calibration
    shadow["research_candidate"] = selected_label
    shadow.to_csv(out / "this_week_shadow.csv", index=False)

    production_reference = {}
    leaderboard_path = Path("outputs/model_leaderboard.csv")
    if leaderboard_path.exists():
        try:
            leaderboard = pd.read_csv(leaderboard_path)
            final = leaderboard[leaderboard.model.eq("Final Ensemble")]
            market = leaderboard[leaderboard.model.eq("Market")]
            if len(final):
                production_reference["published_final_ensemble"] = _jsonable_record(final.iloc[0])
            if len(market):
                production_reference["published_market"] = _jsonable_record(market.iloc[0])
        except Exception as exc:
            production_reference["read_error"] = str(exc)

    reference = metrics[metrics.candidate.eq(PRODUCTION_LABEL)].iloc[0]
    selected_metrics = metrics[metrics.candidate.eq(selected_label)].iloc[0]
    report = {
        "status": "healthy",
        "mode": "research_only",
        "live_season_firewall": LIVE_SEASON,
        "target_seasons": list(TARGET_SEASONS),
        "base_oof_start": BASE_OOF_START,
        "features": feature_cols,
        "selected_shadow_candidate": selected_label,
        "selected_shadow_pure_weight": shadow_weight,
        "selected_shadow_market_weight": 1.0 - shadow_weight,
        "selected_shadow_calibration": shadow_calibration,
        "selected_shadow_weight_objective": shadow_objective,
        "nested_production_like": _jsonable_record(reference),
        "selected_metrics": _jsonable_record(selected_metrics),
        "accuracy_gain_pp_vs_nested_75_25": round(
            100.0 * (float(selected_metrics.winner_pct) - float(reference.winner_pct)), 4
        ),
        "brier_delta_vs_nested_75_25": round(
            float(selected_metrics.brier) - float(reference.brier), 8
        ),
        "log_loss_delta_vs_nested_75_25": round(
            float(selected_metrics.log_loss) - float(reference.log_loss), 8
        ),
        "published_reference": production_reference,
        "promotion_authorized": False,
        "promotion_policy": (
            "No production change from this report. A challenger must first pass leakage-safe "
            "pre-2026 OOS gates and then prove itself on immutable 2026 shadow forecasts."
        ),
        "current_shadow_games": int(len(shadow)),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== LEVLINE CHALLENGER: LEAKAGE-SAFE 2022-25 ===")
    print(metrics[["candidate", "games", "winner_pct", "brier", "log_loss"]].to_string(index=False))
    print("\nselected shadow candidate:", selected_label)
    print("selected 2026 shadow pure/market weight:", f"{shadow_weight:.2f}/{1-shadow_weight:.2f}")
    print("selected calibration:", shadow_calibration)
    print("accuracy gain vs nested 75/25 (pp):", report["accuracy_gain_pp_vs_nested_75_25"])
    print("2026 outcomes used in fitting/tuning: 0")
    print("production outputs modified: 0")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="challenger_outputs")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()
