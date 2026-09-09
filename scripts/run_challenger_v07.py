from __future__ import annotations

"""Run the LevLine v0.7 opponent-adjusted EPA challenger outside production.

Research contract:
- 2026 outcomes are never used for fitting, tuning, calibration, or selection;
- every 2022-25 score is season-forward / prior-data-only;
- opponent adjustment uses only the opponent's shifted pregame state;
- market-only remains a benchmark, never a LevLine candidate;
- shadow-eligible hybrids retain at least 25% explicit PURE football weight;
- only transforms that the T-120 shadow ledger can replay exactly are shadow-eligible;
- production outputs, picks, grading, and T-120 lock semantics are untouched.
"""

import argparse
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
    fit_future_nested_stack,
    fixed_blend_backtest,
    score_probabilities,
    select_pure_weight,
)
from nfl_forecast.challenger_v06 import (
    HYBRID_PURE_WEIGHTS,
    _select_logit_weight,
    logit_blend_probabilities,
    nested_agreement_backtest,
    nested_logit_hybrid_backtest,
    nested_market_confidence_backtest,
)
from nfl_forecast.challenger_v07 import (
    build_opponent_adjusted_matchup_features,
    opponent_adjusted_feature_columns,
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
OPPONENT_FIXED_LABEL = "Opponent-adjusted 75% PURE / 25% MARKET"


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
        if isinstance(value, np.integer):
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
    base_games = build_matchup_features(team_games, bundle.schedules, elo)
    games = build_opponent_adjusted_matchup_features(team_games, bundle.schedules, base_games)
    games = add_vig_free_market_prob(games)

    season_num = pd.to_numeric(games.season, errors="coerce")
    historical = games[games.home_win.notna() & (season_num < LIVE_SEASON)].copy()
    current_pool = games[(season_num == LIVE_SEASON) & games.home_win.isna()].copy()
    if historical.empty:
        raise RuntimeError("No pre-2026 historical games available")
    if current_pool.empty:
        raise RuntimeError("No unresolved 2026 games available")
    next_week = int(pd.to_numeric(current_pool.week, errors="coerce").min())
    current = current_pool[pd.to_numeric(current_pool.week, errors="coerce").eq(next_week)].copy()

    all_features = core_columns(historical)
    adjusted_features = opponent_adjusted_feature_columns(historical)
    base_features = [c for c in all_features if c not in set(adjusted_features)]
    augmented_features = sorted(set(base_features + adjusted_features))
    if not base_features or not adjusted_features:
        raise RuntimeError("Opponent-adjusted research feature construction failed")
    return cfg, historical, current, base_features, augmented_features, adjusted_features


def build_nested_research(historical: pd.DataFrame, feature_cols: list[str], seed: int):
    base_oof = build_base_oof_predictions(
        historical,
        feature_cols,
        seed=seed,
        validation_start=BASE_OOF_START,
        validation_end=max(TARGET_SEASONS),
    )
    nested = build_nested_stack_oof(base_oof, target_seasons=TARGET_SEASONS, seed=seed)

    research = base_oof[["home_win", "season"]].copy()
    research["market_prob"] = pd.to_numeric(
        historical.loc[research.index, "market_home_prob"], errors="coerce"
    )
    research["pure_prob"] = np.nan
    research.loc[nested.target_oof.index, "pure_prob"] = nested.target_oof.pure_prob

    for season in sorted(int(s) for s in base_oof.season.unique() if int(s) < min(TARGET_SEASONS)):
        meta_train = base_oof[base_oof.season < season]
        test = base_oof[base_oof.season == season]
        if len(meta_train) < 300 or test.empty:
            continue
        meta = _meta_template(seed)
        meta.fit(meta_train[list(BASE_MODEL_NAMES)], meta_train.home_win.astype(int))
        research.loc[test.index, "pure_prob"] = meta.predict_proba(
            test[list(BASE_MODEL_NAMES)]
        )[:, 1]

    research = research[research.pure_prob.notna()].copy()
    missing = set(TARGET_SEASONS) - set(research.season.astype(int).unique())
    if missing:
        raise RuntimeError(f"Research frame missing target seasons: {sorted(missing)}")
    return base_oof, research


def nested_linear_hybrid(frame: pd.DataFrame, *, objective: str = "brier") -> BlendBacktestResult:
    parts = []
    weights = []
    for test_season in TARGET_SEASONS:
        tune = frame[frame.season < test_season].copy()
        test = frame[frame.season == test_season].copy()
        if test.empty:
            continue
        weight, _ = select_pure_weight(
            tune,
            objective=objective,
            weights=HYBRID_PURE_WEIGHTS,
        )
        p = blend_probabilities(test.pure_prob, test.market_prob, weight)
        part = test[["season", "home_win", "pure_prob", "market_prob"]].copy()
        part["probability"] = p
        part["pure_weight"] = weight
        part["market_weight"] = 1.0 - weight
        parts.append(part)
        weights.append({
            "season": test_season,
            "pure_weight": weight,
            "market_weight": 1.0 - weight,
            "objective": objective,
            **score_probabilities(part.home_win, p),
        })
    predictions = pd.concat(parts).sort_index()
    return BlendBacktestResult(
        predictions=predictions,
        weights=pd.DataFrame(weights),
        metrics=score_probabilities(predictions.home_win, predictions.probability),
    )


def _candidate_suite(research: pd.DataFrame, *, prefix: str, feature_set: str) -> dict[str, dict]:
    def label(name: str) -> str:
        return f"{prefix}{name}" if prefix else name

    # Calibrated and regime-conditioned candidates remain research evidence only.
    # The immutable T-120 ledger cannot exactly replay their transform from a
    # persisted PURE probability + one weight, so they are deliberately excluded
    # from shadow selection rather than approximated.
    return {
        label("Hybrid adaptive Brier"): {
            "kind": "linear", "objective": "brier", "feature_set": feature_set,
            "eligible_shadow": True, "result": nested_linear_hybrid(research, objective="brier"),
        },
        label("Logit hybrid adaptive Brier"): {
            "kind": "logit", "objective": "brier", "calibrator": "none",
            "feature_set": feature_set, "eligible_shadow": True,
            "result": nested_logit_hybrid_backtest(research, objective="brier", calibrator="none"),
        },
        label("Logit hybrid + Platt"): {
            "kind": "logit", "objective": "brier", "calibrator": "platt",
            "feature_set": feature_set, "eligible_shadow": False,
            "shadow_exclusion": "calibration transform not persisted for exact T-120 replay",
            "result": nested_logit_hybrid_backtest(research, objective="brier", calibrator="platt"),
        },
        label("Logit hybrid adaptive accuracy"): {
            "kind": "logit", "objective": "accuracy", "calibrator": "none",
            "feature_set": feature_set, "eligible_shadow": True,
            "result": nested_logit_hybrid_backtest(research, objective="accuracy", calibrator="none"),
        },
        label("Market-confidence hybrid"): {
            "kind": "confidence", "objective": "brier", "feature_set": feature_set,
            "eligible_shadow": False,
            "shadow_exclusion": "T-120 market regime can differ from precommit regime",
            "result": nested_market_confidence_backtest(research, objective="brier"),
        },
        label("Agreement-aware hybrid"): {
            "kind": "agreement", "objective": "brier", "feature_set": feature_set,
            "eligible_shadow": False,
            "shadow_exclusion": "T-120 agreement regime can differ from precommit regime",
            "result": nested_agreement_backtest(research, objective="brier"),
        },
    }


def _season_ablation(
    baseline_research: pd.DataFrame,
    adjusted_research: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for season in TARGET_SEASONS:
        base = baseline_research[baseline_research.season.eq(season)]
        adj = adjusted_research[adjusted_research.season.eq(season)]
        common = base.index.intersection(adj.index)
        bm = score_probabilities(base.loc[common, "home_win"], base.loc[common, "pure_prob"])
        am = score_probabilities(adj.loc[common, "home_win"], adj.loc[common, "pure_prob"])
        rows.append({
            "season": season,
            "games": bm["games"],
            "baseline_pure_winner_pct": bm["winner_pct"],
            "opponent_adjusted_pure_winner_pct": am["winner_pct"],
            "winner_gain_pp": 100.0 * (am["winner_pct"] - bm["winner_pct"]),
            "baseline_pure_brier": bm["brier"],
            "opponent_adjusted_pure_brier": am["brier"],
            "brier_delta": am["brier"] - bm["brier"],
            "baseline_pure_log_loss": bm["log_loss"],
            "opponent_adjusted_pure_log_loss": am["log_loss"],
            "log_loss_delta": am["log_loss"] - bm["log_loss"],
        })
    return pd.DataFrame(rows)


def run(config_path: str = "config/model.yaml", output_dir: str = "challenger_outputs") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (
        cfg,
        historical,
        current,
        base_features,
        augmented_features,
        adjusted_features,
    ) = build_research_frame(config_path)
    seed = int(cfg["model"]["random_state"])

    baseline_oof, baseline_research = build_nested_research(historical, base_features, seed)
    adjusted_oof, adjusted_research = build_nested_research(historical, augmented_features, seed)
    baseline_target = baseline_research[baseline_research.season.isin(TARGET_SEASONS)].copy()
    adjusted_target = adjusted_research[adjusted_research.season.isin(TARGET_SEASONS)].copy()

    metrics_rows = [
        _metric_row(
            "Nested PURE",
            score_probabilities(baseline_target.home_win, baseline_target.pure_prob),
            feature_set="production_compatible", eligible_shadow=True, method="pure",
        ),
        _metric_row(
            "Market only benchmark",
            score_probabilities(
                baseline_target.loc[baseline_target.market_prob.notna(), "home_win"],
                baseline_target.loc[baseline_target.market_prob.notna(), "market_prob"],
            ),
            feature_set="market", eligible_shadow=False, method="market",
        ),
        _metric_row(
            PRODUCTION_LABEL,
            fixed_blend_backtest(baseline_research, 0.75, target_seasons=TARGET_SEASONS),
            feature_set="production_compatible", pure_weight=0.75, market_weight=0.25,
            method="fixed", eligible_shadow=True,
        ),
        _metric_row(
            "Opponent-adjusted Nested PURE",
            score_probabilities(adjusted_target.home_win, adjusted_target.pure_prob),
            feature_set="opponent_adjusted", eligible_shadow=True, method="pure",
        ),
        _metric_row(
            OPPONENT_FIXED_LABEL,
            fixed_blend_backtest(adjusted_research, 0.75, target_seasons=TARGET_SEASONS),
            feature_set="opponent_adjusted", pure_weight=0.75, market_weight=0.25,
            method="fixed", eligible_shadow=True,
        ),
    ]

    candidates = {}
    candidates.update(_candidate_suite(baseline_research, prefix="", feature_set="production_compatible"))
    candidates.update(
        _candidate_suite(
            adjusted_research,
            prefix="Opponent-adjusted ",
            feature_set="opponent_adjusted",
        )
    )
    for label, spec in candidates.items():
        result = spec["result"]
        metrics_rows.append(_metric_row(
            label,
            result.metrics,
            feature_set=spec["feature_set"],
            method=spec["kind"],
            objective=spec.get("objective"),
            calibration=spec.get("calibrator", "none"),
            eligible_shadow=spec["eligible_shadow"],
            shadow_exclusion=spec.get("shadow_exclusion"),
        ))
        slug = label.lower().replace(" ", "_").replace("+", "plus")
        result.weights.to_csv(out / f"weights_{slug}.csv", index=False)

    metrics = pd.DataFrame(metrics_rows)
    for col in ["winner_pct", "brier", "log_loss"]:
        metrics[col] = pd.to_numeric(metrics[col], errors="coerce")
    eligible = metrics[metrics.eligible_shadow.fillna(False)].copy()
    selected = choose_shadow_candidate(eligible, PRODUCTION_LABEL)
    selected_label = str(selected.candidate)

    baseline_current_pure = fit_future_nested_stack(
        historical, baseline_oof, current, base_features, seed=seed
    )
    adjusted_current_pure = fit_future_nested_stack(
        historical, adjusted_oof, current, augmented_features, seed=seed
    )
    current_market = pd.to_numeric(current.market_home_prob, errors="coerce").to_numpy(dtype=float)

    selected_feature_set = str(selected.get("feature_set", "production_compatible"))
    if selected_feature_set == "opponent_adjusted":
        current_pure = adjusted_current_pure
        selected_research = adjusted_research
    else:
        current_pure = baseline_current_pure
        selected_research = baseline_research

    shadow_method = "fixed"
    effective_weights = np.full(len(current), 0.75, dtype=float)
    if selected_label == PRODUCTION_LABEL or selected_label == OPPONENT_FIXED_LABEL:
        current_final = blend_probabilities(current_pure, current_market, 0.75)
    elif selected_label in {"Nested PURE", "Opponent-adjusted Nested PURE"}:
        current_final = current_pure
        effective_weights[:] = 1.0
        shadow_method = "pure"
    else:
        spec = candidates[selected_label]
        if not spec["eligible_shadow"]:
            raise RuntimeError(f"Research-only transform was incorrectly selected for shadow: {selected_label}")
        if spec["kind"] == "linear":
            weight, _ = select_pure_weight(
                selected_research,
                objective=spec["objective"],
                weights=HYBRID_PURE_WEIGHTS,
            )
            current_final = blend_probabilities(current_pure, current_market, weight)
            effective_weights[:] = weight
            shadow_method = "linear"
        elif spec["kind"] == "logit":
            weight, _ = _select_logit_weight(selected_research, objective=spec["objective"])
            current_final = logit_blend_probabilities(current_pure, current_market, weight)
            effective_weights[:] = weight
            shadow_method = "logit"
        else:
            raise RuntimeError(f"Unsupported shadow-selected transform: {spec['kind']}")

    if np.nanmin(effective_weights) < min(HYBRID_PURE_WEIGHTS) - 1e-12:
        raise RuntimeError("Research firewall violated: selected hybrid fell below 25% PURE")

    shadow = current[[
        "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
        "spread_line", "total_line",
    ]].copy()
    shadow["challenger_pure_home_prob"] = current_pure
    shadow["market_home_prob"] = current_market
    shadow["challenger_final_home_prob"] = current_final
    shadow["challenger_pick"] = np.where(current_final >= 0.5, shadow.home_team, shadow.away_team)
    shadow["effective_pure_weight"] = effective_weights
    shadow["effective_market_weight"] = 1.0 - effective_weights
    shadow["research_candidate"] = selected_label
    shadow["research_method"] = shadow_method
    shadow["research_feature_set"] = selected_feature_set
    shadow["challenger_version"] = "0.7-opponent-adjusted"
    shadow.to_csv(out / "this_week_shadow.csv", index=False)

    baseline_oof.to_csv(out / "base_oof_2018_2025.csv", index=False)
    adjusted_oof.to_csv(out / "base_oof_2018_2025_opponent_adjusted.csv", index=False)
    baseline_target.assign(game_index=baseline_target.index).to_csv(
        out / "nested_research_frame.csv", index=False
    )
    adjusted_target.assign(game_index=adjusted_target.index).to_csv(
        out / "nested_research_frame_opponent_adjusted.csv", index=False
    )
    metrics.to_csv(out / "candidate_metrics.csv", index=False)
    ablation = _season_ablation(baseline_research, adjusted_research)
    ablation.to_csv(out / "opponent_adjusted_season_ablation.csv", index=False)

    production_reference = {}
    leaderboard_path = Path("outputs/model_leaderboard.csv")
    if leaderboard_path.exists():
        try:
            leaderboard = pd.read_csv(leaderboard_path)
            for key, model_name in [
                ("published_final_ensemble", "Final Ensemble"),
                ("published_market", "Market"),
            ]:
                row = leaderboard[leaderboard.model.eq(model_name)]
                if len(row):
                    production_reference[key] = _jsonable_record(row.iloc[0])
        except Exception as exc:
            production_reference["read_error"] = str(exc)

    reference = metrics[metrics.candidate.eq(PRODUCTION_LABEL)].iloc[0]
    selected_metrics = metrics[metrics.candidate.eq(selected_label)].iloc[0]
    adjusted_pure = metrics[metrics.candidate.eq("Opponent-adjusted Nested PURE")].iloc[0]
    baseline_pure = metrics[metrics.candidate.eq("Nested PURE")].iloc[0]
    report = {
        "status": "healthy",
        "mode": "research_only",
        "challenger_version": "0.7-opponent-adjusted",
        "live_season_firewall": LIVE_SEASON,
        "target_seasons": list(TARGET_SEASONS),
        "base_oof_start": BASE_OOF_START,
        "minimum_pure_weight": min(HYBRID_PURE_WEIGHTS),
        "market_only_is_benchmark_not_candidate": True,
        "base_features": base_features,
        "opponent_adjusted_features": adjusted_features,
        "augmented_features": augmented_features,
        "opponent_adjustment_contract": (
            "Observed team EPA/success is residualized against the opponent's shifted pregame EWMA, "
            "then those residuals are shifted again before matchup use. Same-game information cannot enter."
        ),
        "tested_candidate_count": int(len(metrics)),
        "shadow_eligible_candidate_count": int(metrics.eligible_shadow.fillna(False).sum()),
        "selected_shadow_candidate": selected_label,
        "selected_shadow_method": shadow_method,
        "selected_shadow_feature_set": selected_feature_set,
        "selected_metrics": _jsonable_record(selected_metrics),
        "nested_production_like": _jsonable_record(reference),
        "opponent_adjusted_pure_gain_pp": round(
            100.0 * (float(adjusted_pure.winner_pct) - float(baseline_pure.winner_pct)), 4
        ),
        "opponent_adjusted_pure_brier_delta": round(
            float(adjusted_pure.brier) - float(baseline_pure.brier), 8
        ),
        "opponent_adjusted_pure_log_loss_delta": round(
            float(adjusted_pure.log_loss) - float(baseline_pure.log_loss), 8
        ),
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
        "market_timing_caveat": (
            "Historical nflverse market fields are closing-line benchmarks. Production locks at T-120; "
            "promotion requires immutable 2026 T-120 shadow evidence."
        ),
        "promotion_authorized": False,
        "promotion_policy": (
            "No production change from research. Opponent-adjusted features must improve leakage-safe "
            "pre-2026 evidence and then prove themselves on immutable 2026 T-120 shadow forecasts."
        ),
        "current_shadow_games": int(len(shadow)),
        "2026_outcomes_used_in_fitting": 0,
        "production_outputs_modified": 0,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== LEVLINE v0.7 OPPONENT-ADJUSTED CHALLENGER: LEAKAGE-SAFE 2022-25 ===")
    print(metrics[["candidate", "games", "winner_pct", "brier", "log_loss", "eligible_shadow"]].to_string(index=False))
    print("\nopponent-adjusted PURE gain (pp):", report["opponent_adjusted_pure_gain_pp"])
    print("selected shadow candidate:", selected_label)
    print("selected feature set:", selected_feature_set)
    print("selected method:", shadow_method)
    print("minimum effective PURE weight:", round(float(np.nanmin(effective_weights)), 4))
    print("2026 outcomes used in fitting/tuning: 0")
    print("production outputs modified: 0")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="challenger_outputs")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()
