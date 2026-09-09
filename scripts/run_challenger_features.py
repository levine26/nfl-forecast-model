from __future__ import annotations

"""Evaluate richer football signals against the current LevLine challenger.

This is research-only. It uses no 2026 outcomes and writes only under
challenger_outputs/. Historical market inputs remain closing-line benchmarks,
so a historical win never authorizes a production change by itself.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger import (
    BASE_MODEL_NAMES,
    BlendBacktestResult,
    _meta_template,
    blend_probabilities,
    build_base_oof_predictions,
    build_nested_stack_oof,
    choose_shadow_candidate,
    fit_calibrator,
    fit_future_nested_stack,
    fixed_blend_backtest,
    score_probabilities,
    select_pure_weight,
)
from nfl_forecast.challenger_features import build_advanced_matchup_features, enriched_columns
from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features, core_columns
from nfl_forecast.market import add_vig_free_market_prob


LIVE_SEASON = 2026
TARGET_SEASONS = (2022, 2023, 2024, 2025)
BASE_OOF_START = 2018
HYBRID_WEIGHTS = tuple(float(x) for x in np.linspace(0.25, 1.0, 16))
REFERENCE = "Enriched 75% PURE / 25% MARKET"


def _nested_hybrid(
    frame: pd.DataFrame,
    *,
    objective: str = "brier",
    calibration: str = "none",
) -> BlendBacktestResult:
    parts = []
    rows = []
    for season in TARGET_SEASONS:
        tune = frame[frame.season < season].copy()
        test = frame[frame.season == season].copy()
        if test.empty:
            continue
        weight, _ = select_pure_weight(tune, objective=objective, weights=HYBRID_WEIGHTS)
        tune_raw = blend_probabilities(tune.pure_prob, tune.market_prob, weight)
        calibrator = fit_calibrator(tune.home_win, tune_raw, mode=calibration)
        raw = blend_probabilities(test.pure_prob, test.market_prob, weight)
        part = test[["season", "home_win", "pure_prob", "market_prob"]].copy()
        part["probability"] = calibrator.predict(raw)
        part["pure_weight"] = weight
        part["market_weight"] = 1.0 - weight
        parts.append(part)
        rows.append({
            "season": season,
            "pure_weight": weight,
            "market_weight": 1.0 - weight,
            "objective": objective,
            "calibration": calibration,
            **score_probabilities(part.home_win, part.probability),
        })
    if not parts:
        raise RuntimeError("No enriched target-season predictions generated")
    predictions = pd.concat(parts).sort_index()
    return BlendBacktestResult(
        predictions=predictions,
        weights=pd.DataFrame(rows),
        metrics=score_probabilities(predictions.home_win, predictions.probability),
    )


def _research_pure_frame(base_oof: pd.DataFrame, historical: pd.DataFrame, seed: int) -> pd.DataFrame:
    nested = build_nested_stack_oof(base_oof, target_seasons=TARGET_SEASONS, seed=seed)
    research = base_oof[["home_win", "season"]].copy()
    research["market_prob"] = pd.to_numeric(
        historical.loc[research.index, "market_home_prob"], errors="coerce"
    )
    research["pure_prob"] = np.nan
    research.loc[nested.target_oof.index, "pure_prob"] = nested.target_oof.pure_prob

    # Earlier nested PURE rows are tuning data for the 2022+ blend. Their meta
    # model still sees only OOF seasons strictly earlier than the target season.
    for season in sorted(int(s) for s in base_oof.season.unique() if int(s) < min(TARGET_SEASONS)):
        meta_train = base_oof[base_oof.season < season]
        test = base_oof[base_oof.season == season]
        if len(meta_train) < 300 or test.empty:
            continue
        meta = _meta_template(seed)
        meta.fit(meta_train[list(BASE_MODEL_NAMES)], meta_train.home_win.astype(int))
        research.loc[test.index, "pure_prob"] = meta.predict_proba(test[list(BASE_MODEL_NAMES)])[:, 1]
    return research[research.pure_prob.notna()].copy()


def main() -> None:
    out = Path("challenger_outputs")
    out.mkdir(parents=True, exist_ok=True)
    cfg = load_config("config/model.yaml")
    start = int(cfg["data"]["core_start_season"])
    seed = int(cfg["model"]["random_state"])
    bundle = load_core_data(range(start, LIVE_SEASON + 1), cfg["data"]["cache_dir"])
    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = add_game_results(
        aggregate_team_games(
            bundle.pbp,
            cfg["data"]["neutral_wp_lower"],
            cfg["data"]["neutral_wp_upper"],
        ),
        bundle.schedules,
    )
    base_games = add_vig_free_market_prob(build_matchup_features(team_games, bundle.schedules, elo))
    advanced = build_advanced_matchup_features(
        bundle.pbp,
        bundle.schedules,
        elo,
        windows=tuple(int(x) for x in cfg["features"]["rolling_windows"]),
        alpha=float(cfg["features"]["ewma_alpha"]),
    )
    games = base_games.merge(advanced, on="game_id", how="left", validate="one_to_one")

    pre2026 = pd.to_numeric(games.season, errors="coerce") < LIVE_SEASON
    historical = games[games.home_win.notna() & pre2026].copy()
    unresolved = games[(pd.to_numeric(games.season, errors="coerce") == LIVE_SEASON) & games.home_win.isna()].copy()
    if unresolved.empty:
        raise RuntimeError("No unresolved 2026 games for enriched shadow")
    week = int(pd.to_numeric(unresolved.week, errors="coerce").min())
    current = unresolved[pd.to_numeric(unresolved.week, errors="coerce").eq(week)].copy()

    base_historical = base_games[
        base_games.home_win.notna() & (pd.to_numeric(base_games.season, errors="coerce") < LIVE_SEASON)
    ]
    production_features = core_columns(base_historical)
    features = enriched_columns(historical, production_features)
    extra_features = [c for c in features if c not in production_features]
    if len(extra_features) < 20:
        raise RuntimeError(f"Advanced feature build unexpectedly thin: {len(extra_features)}")

    base_oof = build_base_oof_predictions(
        historical,
        features,
        seed=seed,
        validation_start=BASE_OOF_START,
        validation_end=max(TARGET_SEASONS),
    )
    research = _research_pure_frame(base_oof, historical, seed)
    target = research[research.season.isin(TARGET_SEASONS)].copy()
    if len(target) != 1087:
        # Exact historical coverage is a useful tripwire. If upstream data are
        # revised, fail rather than comparing different samples silently.
        raise RuntimeError(f"Expected 1087 target games; enriched frame has {len(target)}")

    fixed = fixed_blend_backtest(research, 0.75, target_seasons=TARGET_SEASONS)
    brier = _nested_hybrid(research, objective="brier", calibration="none")
    brier_platt = _nested_hybrid(research, objective="brier", calibration="platt")
    accuracy = _nested_hybrid(research, objective="accuracy", calibration="none")

    metrics = pd.DataFrame([
        {"candidate": "Enriched nested PURE", **score_probabilities(target.home_win, target.pure_prob)},
        {"candidate": REFERENCE, **fixed},
        {"candidate": "Enriched hybrid adaptive Brier", **brier.metrics},
        {"candidate": "Enriched hybrid Brier + Platt", **brier_platt.metrics},
        {"candidate": "Enriched hybrid adaptive accuracy", **accuracy.metrics},
    ])
    selected = choose_shadow_candidate(metrics, REFERENCE)
    selected_label = str(selected.candidate)
    if selected_label == REFERENCE:
        weight, calibration, objective = 0.75, "none", "fixed"
    elif selected_label == "Enriched nested PURE":
        weight, calibration, objective = 1.0, "none", "fixed"
    else:
        specs = {
            "Enriched hybrid adaptive Brier": ("brier", "none"),
            "Enriched hybrid Brier + Platt": ("brier", "platt"),
            "Enriched hybrid adaptive accuracy": ("accuracy", "none"),
        }
        objective, calibration = specs[selected_label]
        weight, _ = select_pure_weight(research, objective=objective, weights=HYBRID_WEIGHTS)

    current_pure = fit_future_nested_stack(historical, base_oof, current, features, seed=seed)
    current_market = pd.to_numeric(current.market_home_prob, errors="coerce").to_numpy(dtype=float)
    current_raw = blend_probabilities(current_pure, current_market, weight)
    if calibration == "none":
        current_final = current_raw
    else:
        train_raw = blend_probabilities(research.pure_prob, research.market_prob, weight)
        current_final = fit_calibrator(research.home_win, train_raw, mode=calibration).predict(current_raw)

    shadow = current[["game_id", "week", "away_team", "home_team"]].copy()
    shadow["enriched_pure_home_prob"] = current_pure
    shadow["market_home_prob"] = current_market
    shadow["enriched_final_home_prob"] = current_final
    shadow["enriched_pick"] = np.where(current_final >= 0.5, shadow.home_team, shadow.away_team)
    shadow["pure_weight"] = weight
    shadow["market_weight"] = 1.0 - weight
    shadow["candidate"] = selected_label

    baseline_report = {}
    baseline_path = out / "report.json"
    if baseline_path.exists():
        baseline_report = json.loads(baseline_path.read_text())
    baseline_selected = baseline_report.get("selected_metrics", {})
    baseline_accuracy = float(baseline_selected.get("winner_pct", np.nan))
    baseline_brier = float(baseline_selected.get("brier", np.nan))
    baseline_logloss = float(baseline_selected.get("log_loss", np.nan))

    report = {
        "status": "healthy",
        "mode": "research_only",
        "live_season_firewall": LIVE_SEASON,
        "target_seasons": list(TARGET_SEASONS),
        "advanced_feature_count": len(extra_features),
        "advanced_features": extra_features,
        "selected_candidate": selected_label,
        "selected_pure_weight": weight,
        "selected_market_weight": 1.0 - weight,
        "selected_calibration": calibration,
        "selected_metrics": {
            "winner_pct": float(selected.winner_pct),
            "brier": float(selected.brier),
            "log_loss": float(selected.log_loss),
        },
        "baseline_best_hybrid": baseline_selected,
        "accuracy_delta_pp_vs_baseline_best_hybrid": (
            round(100 * (float(selected.winner_pct) - baseline_accuracy), 4)
            if np.isfinite(baseline_accuracy) else None
        ),
        "brier_delta_vs_baseline_best_hybrid": (
            round(float(selected.brier) - baseline_brier, 8)
            if np.isfinite(baseline_brier) else None
        ),
        "log_loss_delta_vs_baseline_best_hybrid": (
            round(float(selected.log_loss) - baseline_logloss, 8)
            if np.isfinite(baseline_logloss) else None
        ),
        "beats_baseline_best_hybrid": bool(
            np.isfinite(baseline_accuracy)
            and float(selected.winner_pct) > baseline_accuracy
            and float(selected.brier) <= baseline_brier + 0.001
            and float(selected.log_loss) <= baseline_logloss + 0.003
        ),
        "promotion_authorized": False,
        "market_timing_caveat": "Historical market input is a closing-line benchmark; live T-120 shadow proof remains mandatory.",
        "current_shadow_games": int(len(shadow)),
    }

    metrics.to_csv(out / "feature_candidate_metrics.csv", index=False)
    brier.weights.to_csv(out / "feature_weights_brier.csv", index=False)
    brier_platt.weights.to_csv(out / "feature_weights_brier_platt.csv", index=False)
    accuracy.weights.to_csv(out / "feature_weights_accuracy.csv", index=False)
    shadow.to_csv(out / "feature_shadow.csv", index=False)
    (out / "feature_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== ENRICHED FOOTBALL FEATURE CHALLENGER ===")
    print("advanced features:", len(extra_features))
    print(metrics.to_string(index=False))
    print("selected:", selected_label, f"weight={weight:.2f}/{1-weight:.2f}")
    print("delta accuracy pp vs baseline best:", report["accuracy_delta_pp_vs_baseline_best_hybrid"])
    print("beats baseline best hybrid:", report["beats_baseline_best_hybrid"])
    print("2026 outcomes used: 0")


if __name__ == "__main__":
    main()
