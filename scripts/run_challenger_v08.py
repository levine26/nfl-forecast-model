from __future__ import annotations

"""Run the LevLine v0.8 QB-starter challenger outside production.

The experiment isolates whether pregame quarterback starter quality, experience and
continuity improve the football model beyond production-compatible and opponent-adjusted
EPA features. 2026 outcomes remain excluded from fitting/tuning; only the current
schedule's starter identity and prior completed information are used for live shadow rows.

Every replayable research candidate is precommitted for the live slate. The selected
research leader remains available at ``this_week_shadow.csv`` for compatibility, while
``candidate_shadow_slate.csv`` carries all eligible candidates for immutable T-120 scoring.
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
    nested_logit_hybrid_backtest,
)
from nfl_forecast.challenger_v07 import (
    build_opponent_adjusted_matchup_features,
    opponent_adjusted_feature_columns,
)
from nfl_forecast.challenger_v08 import build_qb_matchup_features, qb_feature_columns
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
CHALLENGER_VERSION = "0.8-qb-starter"

FEATURE_PREFIX = {
    "production_compatible": "",
    "opponent_adjusted": "Opponent-adjusted ",
    "qb_aware": "QB-aware ",
    "opponent_adjusted_qb": "Opponent-adjusted + QB-aware ",
}

SHADOW_BASE_COLUMNS = [
    "game_id",
    "season",
    "week",
    "gameday",
    "gametime",
    "away_team",
    "home_team",
    "spread_line",
    "total_line",
]


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
    opp_games = build_opponent_adjusted_matchup_features(team_games, bundle.schedules, base_games)
    games = build_qb_matchup_features(bundle.pbp, bundle.schedules, opp_games)
    games = add_vig_free_market_prob(games)

    season_num = pd.to_numeric(games.season, errors="coerce")
    historical = games[games.home_win.notna() & (season_num < LIVE_SEASON)].copy()
    current_pool = games[(season_num == LIVE_SEASON) & games.home_win.isna()].copy()
    if historical.empty or current_pool.empty:
        raise RuntimeError("Missing historical or unresolved live games for QB challenger")
    next_week = int(pd.to_numeric(current_pool.week, errors="coerce").min())
    current = current_pool[pd.to_numeric(current_pool.week, errors="coerce").eq(next_week)].copy()

    opp = opponent_adjusted_feature_columns(historical)
    qb = qb_feature_columns(historical)
    all_core = core_columns(historical)
    blocked = set(opp) | set(qb)
    base = [c for c in all_core if c not in blocked]
    feature_sets = {
        "production_compatible": sorted(base),
        "opponent_adjusted": sorted(set(base + opp)),
        "qb_aware": sorted(set(base + qb)),
        "opponent_adjusted_qb": sorted(set(base + opp + qb)),
    }
    if not base or len(opp) != 32 or not qb:
        raise RuntimeError("QB challenger feature construction failed")
    return cfg, historical, current, feature_sets, opp, qb


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
    parts, rows = [], []
    for season in TARGET_SEASONS:
        tune = frame[frame.season < season]
        test = frame[frame.season == season]
        if test.empty:
            continue
        weight, _ = select_pure_weight(tune, objective=objective, weights=HYBRID_PURE_WEIGHTS)
        probability = blend_probabilities(test.pure_prob, test.market_prob, weight)
        part = test[["season", "home_win", "pure_prob", "market_prob"]].copy()
        part["probability"] = probability
        part["pure_weight"] = weight
        part["market_weight"] = 1.0 - weight
        parts.append(part)
        rows.append(
            {
                "season": season,
                "pure_weight": weight,
                "market_weight": 1.0 - weight,
                "objective": objective,
                **score_probabilities(part.home_win, probability),
            }
        )
    predictions = pd.concat(parts).sort_index()
    return BlendBacktestResult(
        predictions=predictions,
        weights=pd.DataFrame(rows),
        metrics=score_probabilities(predictions.home_win, predictions.probability),
    )


def _suite(research: pd.DataFrame, feature_set: str) -> dict[str, dict]:
    prefix = FEATURE_PREFIX[feature_set]

    def label(text: str) -> str:
        return f"{prefix}{text}" if prefix else text

    return {
        label("Hybrid adaptive Brier"): {
            "feature_set": feature_set,
            "kind": "linear",
            "objective": "brier",
            "result": nested_linear_hybrid(research, objective="brier"),
        },
        label("Logit hybrid adaptive Brier"): {
            "feature_set": feature_set,
            "kind": "logit",
            "objective": "brier",
            "result": nested_logit_hybrid_backtest(
                research, objective="brier", calibrator="none"
            ),
        },
        label("Logit hybrid adaptive accuracy"): {
            "feature_set": feature_set,
            "kind": "logit",
            "objective": "accuracy",
            "result": nested_logit_hybrid_backtest(
                research, objective="accuracy", calibrator="none"
            ),
        },
    }


def _label(feature_set: str, text: str) -> str:
    prefix = FEATURE_PREFIX[feature_set]
    return f"{prefix}{text}" if prefix else text


def _ablation(research_by_set: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    base = research_by_set["production_compatible"]
    for season in TARGET_SEASONS:
        base_s = base[base.season.eq(season)]
        for feature_set, research in research_by_set.items():
            sample = research[research.season.eq(season)]
            common = base_s.index.intersection(sample.index)
            metrics = score_probabilities(
                sample.loc[common, "home_win"], sample.loc[common, "pure_prob"]
            )
            rows.append({"season": season, "feature_set": feature_set, **metrics})
    return pd.DataFrame(rows)


def _shadow_frame(
    current: pd.DataFrame,
    pure_probability: np.ndarray,
    market_probability: np.ndarray,
    *,
    label: str,
    feature_set: str,
    method: str,
    pure_weight: float,
    selected: bool,
) -> pd.DataFrame:
    pure = np.asarray(pure_probability, dtype=float)
    market = np.asarray(market_probability, dtype=float)
    if method == "pure":
        if not np.isclose(pure_weight, 1.0):
            raise RuntimeError("PURE shadow candidate must carry weight 1.0")
        final = np.clip(pure, 1e-6, 1.0 - 1e-6)
    elif method == "logit":
        final = logit_blend_probabilities(pure, market, pure_weight)
    elif method in {"linear", "fixed"}:
        final = blend_probabilities(pure, market, pure_weight)
    else:
        raise RuntimeError(f"Unsupported shadow method: {method}")

    frame = current[SHADOW_BASE_COLUMNS].copy()
    frame["challenger_pure_home_prob"] = pure
    frame["market_home_prob"] = market
    frame["challenger_final_home_prob"] = final
    frame["challenger_pick"] = np.where(final >= 0.5, frame.home_team, frame.away_team)
    frame["effective_pure_weight"] = float(pure_weight)
    frame["effective_market_weight"] = 1.0 - float(pure_weight)
    frame["research_candidate"] = label
    frame["research_method"] = method
    frame["research_feature_set"] = feature_set
    frame["challenger_version"] = CHALLENGER_VERSION
    frame["selected_shadow_candidate"] = bool(selected)
    return frame


def build_candidate_shadow_slate(
    current: pd.DataFrame,
    current_pure_by_set: dict[str, np.ndarray],
    research_by_set: dict[str, pd.DataFrame],
    feature_sets: dict[str, list[str]],
    adaptive_candidates: dict[str, dict],
    selected_label: str,
) -> pd.DataFrame:
    """Precommit every exact-replay candidate before the production T-120 lock."""
    market = pd.to_numeric(current.market_home_prob, errors="coerce").to_numpy(dtype=float)
    frames: list[pd.DataFrame] = []

    for feature_set in feature_sets:
        pure = current_pure_by_set[feature_set]
        pure_label = _label(feature_set, "Nested PURE")
        fixed_label = (
            PRODUCTION_LABEL
            if feature_set == "production_compatible"
            else _label(feature_set, "75% PURE / 25% MARKET")
        )
        frames.append(
            _shadow_frame(
                current,
                pure,
                market,
                label=pure_label,
                feature_set=feature_set,
                method="pure",
                pure_weight=1.0,
                selected=pure_label == selected_label,
            )
        )
        frames.append(
            _shadow_frame(
                current,
                pure,
                market,
                label=fixed_label,
                feature_set=feature_set,
                method="fixed",
                pure_weight=0.75,
                selected=fixed_label == selected_label,
            )
        )

        research = research_by_set[feature_set]
        for label, spec in adaptive_candidates.items():
            if spec["feature_set"] != feature_set:
                continue
            if spec["kind"] == "linear":
                weight, _ = select_pure_weight(
                    research,
                    objective=spec["objective"],
                    weights=HYBRID_PURE_WEIGHTS,
                )
                method = "linear"
            elif spec["kind"] == "logit":
                weight, _ = _select_logit_weight(research, objective=spec["objective"])
                method = "logit"
            else:
                raise RuntimeError(f"Unsupported adaptive transform: {spec['kind']}")
            frames.append(
                _shadow_frame(
                    current,
                    pure,
                    market,
                    label=label,
                    feature_set=feature_set,
                    method=method,
                    pure_weight=float(weight),
                    selected=label == selected_label,
                )
            )

    slate = pd.concat(frames, ignore_index=True)
    identity = ["game_id", "challenger_version", "research_candidate"]
    if slate.duplicated(identity).any():
        raise RuntimeError("Duplicate candidate identity in challenger shadow slate")
    if float(slate.effective_pure_weight.min()) < min(HYBRID_PURE_WEIGHTS) - 1e-12:
        raise RuntimeError("Research firewall violated: shadow PURE weight below 25%")
    selected_per_game = slate.groupby("game_id").selected_shadow_candidate.sum()
    if not selected_per_game.eq(1).all():
        raise RuntimeError("Each live game must have exactly one selected shadow candidate")
    return slate


def run(config_path: str = "config/model.yaml", output_dir: str = "challenger_outputs") -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cfg, historical, current, feature_sets, opp_features, qb_features = build_research_frame(
        config_path
    )
    seed = int(cfg["model"]["random_state"])

    oof_by_set: dict[str, pd.DataFrame] = {}
    research_by_set: dict[str, pd.DataFrame] = {}
    for feature_set, columns in feature_sets.items():
        oof, research = build_nested_research(historical, columns, seed)
        oof_by_set[feature_set] = oof
        research_by_set[feature_set] = research

    base_target = research_by_set["production_compatible"]
    base_target = base_target[base_target.season.isin(TARGET_SEASONS)]
    metrics_rows = [
        _metric_row(
            "Market only benchmark",
            score_probabilities(
                base_target.loc[base_target.market_prob.notna(), "home_win"],
                base_target.loc[base_target.market_prob.notna(), "market_prob"],
            ),
            feature_set="market",
            method="market",
            eligible_shadow=False,
        )
    ]
    adaptive_candidates: dict[str, dict] = {}
    for feature_set, research in research_by_set.items():
        target = research[research.season.isin(TARGET_SEASONS)]
        pure_label = _label(feature_set, "Nested PURE")
        fixed_label = _label(feature_set, "75% PURE / 25% MARKET")
        if feature_set == "production_compatible":
            fixed_label = PRODUCTION_LABEL
        metrics_rows.extend(
            [
                _metric_row(
                    pure_label,
                    score_probabilities(target.home_win, target.pure_prob),
                    feature_set=feature_set,
                    method="pure",
                    eligible_shadow=True,
                ),
                _metric_row(
                    fixed_label,
                    fixed_blend_backtest(research, 0.75, target_seasons=TARGET_SEASONS),
                    feature_set=feature_set,
                    method="fixed",
                    pure_weight=0.75,
                    market_weight=0.25,
                    eligible_shadow=True,
                ),
            ]
        )
        suite = _suite(research, feature_set)
        adaptive_candidates.update(suite)
        for label, spec in suite.items():
            result = spec["result"]
            metrics_rows.append(
                _metric_row(
                    label,
                    result.metrics,
                    feature_set=feature_set,
                    method=spec["kind"],
                    objective=spec["objective"],
                    calibration="none",
                    eligible_shadow=True,
                )
            )
            slug = label.lower().replace(" ", "_").replace("+", "plus")
            result.weights.to_csv(out / f"weights_{slug}.csv", index=False)

    metrics = pd.DataFrame(metrics_rows)
    for column in ["winner_pct", "brier", "log_loss"]:
        metrics[column] = pd.to_numeric(metrics[column], errors="coerce")
    eligible = metrics[metrics.eligible_shadow.fillna(False)].copy()
    selected = choose_shadow_candidate(eligible, PRODUCTION_LABEL)
    selected_label = str(selected.candidate)
    selected_feature_set = str(selected.feature_set)

    current_pure_by_set = {
        feature_set: fit_future_nested_stack(
            historical,
            oof_by_set[feature_set],
            current,
            feature_sets[feature_set],
            seed=seed,
        )
        for feature_set in feature_sets
    }
    candidate_slate = build_candidate_shadow_slate(
        current,
        current_pure_by_set,
        research_by_set,
        feature_sets,
        adaptive_candidates,
        selected_label,
    )
    expected_labels = set(eligible.candidate.astype(str))
    actual_labels = set(candidate_slate.research_candidate.astype(str))
    if actual_labels != expected_labels:
        missing = sorted(expected_labels - actual_labels)
        extra = sorted(actual_labels - expected_labels)
        raise RuntimeError(f"Candidate slate mismatch; missing={missing} extra={extra}")

    shadow = candidate_slate[candidate_slate.selected_shadow_candidate].copy()
    if len(shadow) != len(current):
        raise RuntimeError("Selected shadow compatibility slate does not cover the live week")
    shadow_method_values = shadow.research_method.astype(str).unique().tolist()
    if len(shadow_method_values) != 1:
        raise RuntimeError("Selected shadow candidate has inconsistent methods")
    shadow_method = shadow_method_values[0]

    candidate_slate.to_csv(out / "candidate_shadow_slate.csv", index=False)
    shadow.to_csv(out / "this_week_shadow.csv", index=False)
    for feature_set, oof in oof_by_set.items():
        oof.to_csv(out / f"base_oof_2018_2025_{feature_set}.csv", index=False)
    metrics.to_csv(out / "candidate_metrics.csv", index=False)
    ablation = _ablation(research_by_set)
    ablation.to_csv(out / "feature_set_season_ablation.csv", index=False)

    reference = metrics[metrics.candidate.eq(PRODUCTION_LABEL)].iloc[0]
    selected_metrics = metrics[metrics.candidate.eq(selected_label)].iloc[0]
    pure_lookup = {
        feature_set: metrics[
            metrics.candidate.eq(_label(feature_set, "Nested PURE"))
        ].iloc[0]
        for feature_set in feature_sets
    }
    base_pure = pure_lookup["production_compatible"]
    opp_pure = pure_lookup["opponent_adjusted"]
    qb_pure = pure_lookup["qb_aware"]
    combined_pure = pure_lookup["opponent_adjusted_qb"]

    report = {
        "status": "healthy",
        "mode": "research_only",
        "challenger_version": CHALLENGER_VERSION,
        "live_season_firewall": LIVE_SEASON,
        "target_seasons": list(TARGET_SEASONS),
        "base_oof_start": BASE_OOF_START,
        "minimum_pure_weight": min(HYBRID_PURE_WEIGHTS),
        "market_only_is_benchmark_not_candidate": True,
        "feature_sets": feature_sets,
        "opponent_adjusted_features": opp_features,
        "qb_features": qb_features,
        "qb_signal_contract": (
            "Starter identity comes from the schedule; QB EPA/success/CPOE, experience "
            "and team continuity use only completed prior starts and are shifted before "
            "the current matchup. Unplayed rows do not increment history."
        ),
        "tested_candidate_count": int(len(metrics)),
        "shadow_candidate_count": int(candidate_slate.research_candidate.nunique()),
        "current_shadow_candidate_rows": int(len(candidate_slate)),
        "selected_shadow_candidate": selected_label,
        "selected_shadow_method": shadow_method,
        "selected_shadow_feature_set": selected_feature_set,
        "selected_metrics": _jsonable_record(selected_metrics),
        "nested_production_like": _jsonable_record(reference),
        "qb_only_pure_gain_pp_vs_base": round(
            100.0 * (float(qb_pure.winner_pct) - float(base_pure.winner_pct)), 4
        ),
        "qb_only_pure_brier_delta_vs_base": round(
            float(qb_pure.brier) - float(base_pure.brier), 8
        ),
        "opponent_pure_gain_pp_vs_base": round(
            100.0 * (float(opp_pure.winner_pct) - float(base_pure.winner_pct)), 4
        ),
        "combined_pure_gain_pp_vs_opponent": round(
            100.0 * (float(combined_pure.winner_pct) - float(opp_pure.winner_pct)), 4
        ),
        "combined_pure_brier_delta_vs_opponent": round(
            float(combined_pure.brier) - float(opp_pure.brier), 8
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
        "promotion_authorized": False,
        "promotion_policy": (
            "No production change from research. QB-aware variants must survive "
            "season-forward pre-2026 evaluation and immutable 2026 T-120 shadow scoring "
            "before any promotion."
        ),
        "current_shadow_games": int(len(shadow)),
        "2026_outcomes_used_in_fitting": 0,
        "production_outputs_modified": 0,
    }
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== LEVLINE v0.8 QB-STARTER CHALLENGER: LEAKAGE-SAFE 2022-25 ===")
    print(metrics[["candidate", "games", "winner_pct", "brier", "log_loss"]].to_string(index=False))
    print("\nQB-only PURE gain vs base (pp):", report["qb_only_pure_gain_pp_vs_base"])
    print("Combined PURE gain vs opponent-adjusted (pp):", report["combined_pure_gain_pp_vs_opponent"])
    print("selected shadow candidate:", selected_label)
    print("selected feature set:", selected_feature_set)
    print("selected method:", shadow_method)
    print("precommitted shadow candidates:", report["shadow_candidate_count"])
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
