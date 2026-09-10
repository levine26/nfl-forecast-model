from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import NormalDist
import numpy as np
import pandas as pd

from .config import load_config
from .data import load_core_data, load_advanced_data
from .diagnostics import add_confidence_diagnostics, build_calibration_table
from .elo import build_pregame_elo
from .features import aggregate_team_games, add_game_results, build_matchup_features, sujar_baseline_columns, core_columns
from .fst_nested_pure import build_base_oof_predictions, build_fst_training_frame, fit_future_nested_stack
from .fst_production import (
    CANDIDATE_ID,
    FINAL_PROBABILITY_STRATEGY,
    MODEL_VERSION,
    load_fst_artifact,
    score_official_fst,
    validate_training_identity,
)
from .market import add_vig_free_market_prob
from .models import fit_season_stacked_classifier, fit_weighted_regression, classification_metrics
from .publish import write_outputs


@dataclass
class PipelineArtifacts:
    games: pd.DataFrame
    predictions: pd.DataFrame
    power_ratings: pd.DataFrame
    leaderboard: pd.DataFrame
    calibration: pd.DataFrame


def projected_score(margin: pd.Series, total: pd.Series) -> tuple[pd.Series, pd.Series]:
    home = (total + margin) / 2.0
    away = (total - margin) / 2.0
    return home, away


def fair_american_odds(prob: float) -> float:
    p = float(np.clip(prob, 1e-6, 1 - 1e-6))
    if p >= 0.5:
        return -100.0 * p / (1.0 - p)
    return 100.0 * (1.0 - p) / p


def probability_above(threshold, mean, sigma) -> float:
    if pd.isna(threshold) or pd.isna(mean) or pd.isna(sigma) or float(sigma) <= 0:
        return np.nan
    return float(1.0 - NormalDist(mu=float(mean), sigma=float(sigma)).cdf(float(threshold)))


def consistency_flag(prob: float, margin: float) -> str:
    if abs(float(prob) - 0.5) < 0.02 or abs(float(margin)) < 1.0:
        return "NEUTRAL"
    return "ALIGNED" if (float(prob) - 0.5) * float(margin) > 0 else "WIN-MARGIN SPLIT"


def confidence_label(prob: float, disagreement: float = 0.0, consistency: str = "ALIGNED") -> str:
    q = max(float(prob), 1.0 - float(prob))
    level = 3 if q >= 0.70 else 2 if q >= 0.60 else 1 if q >= 0.55 else 0
    if float(disagreement) >= 0.10:
        level -= 1
    if consistency == "WIN-MARGIN SPLIT":
        level -= 1
    return ["Coin Flip", "Lean", "Solid", "High"][max(0, min(3, level))]


def _power_ratings(unresolved: pd.DataFrame, as_of: str) -> pd.DataFrame:
    """Build one current team state per club. Rank is deliberately Elo+ only."""
    df = unresolved.sort_values([c for c in ["gameday", "gametime", "week"] if c in unresolved.columns]).copy()
    rows: list[dict] = []
    seen: set[str] = set()
    mappings = [("home", "home_team"), ("away", "away_team")]
    for _, r in df.iterrows():
        for prefix, team_col in mappings:
            team = r.get(team_col)
            if pd.isna(team) or str(team) in seen:
                continue
            seen.add(str(team))
            rows.append({
                "team": str(team),
                "elo_plus": pd.to_numeric(r.get(f"{prefix}_elo"), errors="coerce"),
                "off_epa": pd.to_numeric(r.get(f"{prefix}_off_epa_ewma"), errors="coerce"),
                "def_epa_allowed": pd.to_numeric(r.get(f"{prefix}_def_epa_allowed_ewma"), errors="coerce"),
                "pass_epa": pd.to_numeric(r.get(f"{prefix}_pass_epa_ewma"), errors="coerce"),
                "recent_win_pct": pd.to_numeric(r.get(f"{prefix}_win_ewma"), errors="coerce"),
                "as_of": as_of,
            })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values(["elo_plus", "team"], ascending=[False, True], na_position="last").reset_index(drop=True)
    out.insert(0, "rank", np.arange(1, len(out) + 1))
    return out


def _metric_row(name: str, y, p, status: str, margin_mae=np.nan, total_mae=np.nan) -> dict:
    m = classification_metrics(y, p)
    return {
        "model": name,
        "games": m["games"],
        "winner_pct": m["winner_pct"],
        "brier": m["brier"],
        "log_loss": m["log_loss"],
        "margin_mae": margin_mae,
        "total_mae": total_mae,
        "status": status,
    }


def _leaderboard(historical, baseline, core, margin_model, total_model) -> pd.DataFrame:
    rows: list[dict] = []
    b = baseline.oof_predictions
    rows.append(_metric_row("Sujar Baseline", b["home_win"], b["stack"], "Walk-forward OOS 2022–25"))

    c = core.oof_predictions
    for key, label in [
        ("logistic", "Logistic"),
        ("extra_trees", "Extra Trees"),
        ("xgboost", "XGBoost"),
        ("catboost", "CatBoost"),
    ]:
        rows.append(_metric_row(label, c["home_win"], c[key], "Walk-forward OOS 2022–25"))

    rows.append(_metric_row(
        "Core Sujar+",
        c["home_win"],
        c["stack"],
        "Walk-forward OOS 2022–25",
        margin_mae=margin_model.validation_mae,
        total_mae=total_model.validation_mae,
    ))

    h = historical.loc[c.index].copy()
    elo = pd.to_numeric(h.get("elo_home_prob"), errors="coerce")
    elo_mask = elo.notna()
    if elo_mask.any():
        rows.append(_metric_row("Elo+", c.loc[elo_mask, "home_win"], elo.loc[elo_mask], "Independent benchmark"))

    market = pd.to_numeric(h.get("market_home_prob"), errors="coerce")
    market_mask = market.notna()
    if market_mask.any():
        market_margin_mae = np.nan
        market_total_mae = np.nan
        spread_mask = market_mask & h["margin"].notna() & h.get("spread_line", pd.Series(index=h.index, dtype=float)).notna()
        total_mask = market_mask & h["game_total"].notna() & h.get("total_line", pd.Series(index=h.index, dtype=float)).notna()
        if spread_mask.any():
            market_margin_mae = float(np.mean(np.abs(h.loc[spread_mask, "margin"] - h.loc[spread_mask, "spread_line"])))
        if total_mask.any():
            market_total_mae = float(np.mean(np.abs(h.loc[total_mask, "game_total"] - h.loc[total_mask, "total_line"])))
        rows.append(_metric_row(
            "Market",
            c.loc[market_mask, "home_win"],
            market.loc[market_mask],
            "Closing-line benchmark",
            margin_mae=market_margin_mae,
            total_mae=market_total_mae,
        ))

    legacy_prob = c["stack"].copy()
    legacy_prob.loc[market_mask] = 0.75 * c.loc[market_mask, "stack"] + 0.25 * market.loc[market_mask]
    rows.append(_metric_row(
        "Legacy Final Ensemble",
        c["home_win"],
        legacy_prob,
        "Legacy 75% PURE / 25% market; OOS 2022–25",
        margin_mae=margin_model.validation_mae,
        total_mae=total_model.validation_mae,
    ))

    out = pd.DataFrame(rows)
    out["brier_rank"] = out["brier"].rank(method="min", ascending=True).astype(int)
    out = out.sort_values(["brier_rank", "model"]).reset_index(drop=True)
    return out


def run(config_path="config/model.yaml", season_to_predict=2026, snapshot_type="EARLY") -> PipelineArtifacts:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, season_to_predict + 1))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])

    advanced_start = int(cfg["data"]["advanced_start_season"])
    bundle = load_advanced_data(bundle, range(advanced_start, season_to_predict + 1))

    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    tg = aggregate_team_games(bundle.pbp, cfg["data"]["neutral_wp_lower"], cfg["data"]["neutral_wp_upper"])
    tg = add_game_results(tg, bundle.schedules)
    games = build_matchup_features(tg, bundle.schedules, elo)
    games = add_vig_free_market_prob(games)

    historical = games[games["home_win"].notna()].copy()
    unresolved = games[(games["season"] == season_to_predict) & games["home_win"].isna()].copy()
    if unresolved.empty:
        raise RuntimeError(f"No upcoming games found for {season_to_predict}.")
    next_week = int(unresolved["week"].min())
    current = unresolved[unresolved["week"] == next_week].copy()

    baseline_cols = sujar_baseline_columns(historical)
    core_cols = core_columns(historical)
    if len(baseline_cols) < 4:
        raise RuntimeError(f"Baseline feature build incomplete: {baseline_cols}")

    validation_start = max(start + 1, season_to_predict - 4)
    validation_end = season_to_predict - 1
    seed = int(cfg["model"]["random_state"])
    baseline = fit_season_stacked_classifier(historical, baseline_cols, seed=seed, validation_start=validation_start, validation_end=validation_end)
    core = fit_season_stacked_classifier(historical, core_cols, seed=seed, validation_start=validation_start, validation_end=validation_end)
    margin = fit_weighted_regression(historical, core_cols, "margin", seed=seed, validation_start=validation_start, validation_end=validation_end)
    total = fit_weighted_regression(historical, core_cols, "game_total", seed=seed, validation_start=validation_start, validation_end=validation_end)

    current["sujar_home_prob"] = baseline.predict_proba(current)[:, 1]
    current["pure_home_prob"] = core.predict_proba(current)[:, 1]
    base_probs = core.base_predict(current)
    current["logistic_home_prob"] = base_probs["logistic"]
    current["extra_trees_home_prob"] = base_probs["extra_trees"]
    current["xgboost_home_prob"] = base_probs["xgboost"]
    current["catboost_home_prob"] = base_probs["catboost"]
    current["expected_margin"] = margin.predict(current)
    current["expected_total"] = total.predict(current)
    current["margin_sigma"] = float(margin.residual_std)
    current["total_sigma"] = float(total.residual_std)

    # F-ST architecture fitting is frozen at 2025. Completed 2026 games may update
    # already-supported rolling pregame features in `games`, but never enter these fits.
    fst_historical = historical[pd.to_numeric(historical["season"], errors="coerce").le(2025)].copy()
    if fst_historical.empty or pd.to_numeric(fst_historical["season"], errors="coerce").max() > 2025:
        raise RuntimeError("F-ST historical outcome cutoff enforcement failed")
    fst_features = core_columns(fst_historical)
    artifact = load_fst_artifact()
    fst_base_oof = build_base_oof_predictions(
        fst_historical,
        fst_features,
        seed=seed,
        validation_start=2018,
        validation_end=2025,
    )
    fst_training = build_fst_training_frame(fst_historical, fst_base_oof, seed=seed)
    training_digest = validate_training_identity(fst_training, artifact)
    current["fst_pure_home_prob"] = fit_future_nested_stack(
        fst_historical,
        fst_base_oof,
        current,
        fst_features,
        seed=seed,
    )

    current["legacy_pure_home_prob"] = current["pure_home_prob"]
    fst_score = score_official_fst(
        current["legacy_pure_home_prob"],
        current["fst_pure_home_prob"],
        current["market_home_prob"],
        artifact,
    )
    current["legacy_final_home_prob"] = fst_score.legacy_final_home_prob
    current["final_home_prob"] = fst_score.final_home_prob
    current["market_available"] = fst_score.market_eligible
    current["fst_fallback"] = fst_score.fst_fallback
    current["fst_fallback_reason"] = fst_score.fst_fallback_reason
    current["fst_vs_market_delta"] = fst_score.fst_vs_market_delta
    current["fst_vs_legacy_delta"] = fst_score.fst_vs_legacy_delta
    current["final_probability_strategy"] = FINAL_PROBABILITY_STRATEGY
    current["fst_artifact_id"] = CANDIDATE_ID
    current["fst_artifact_training_data_sha256"] = training_digest
    current["fst_artifact_freeze_implementation_sha"] = artifact.freeze_implementation_sha

    current["fair_home_moneyline"] = current["final_home_prob"].map(fair_american_odds)
    current["model_edge"] = np.where(
        current["spread_line"].notna(), current["expected_margin"] - current["spread_line"], np.nan
    )
    current["cover_home_prob"] = current.apply(
        lambda r: probability_above(r.get("spread_line"), r.get("expected_margin"), r.get("margin_sigma")), axis=1
    )
    current["over_prob"] = current.apply(
        lambda r: probability_above(r.get("total_line"), r.get("expected_total"), r.get("total_sigma")), axis=1
    )
    z80 = 1.2815515655446004
    current["margin_low_80"] = current["expected_margin"] - z80 * current["margin_sigma"]
    current["margin_high_80"] = current["expected_margin"] + z80 * current["margin_sigma"]
    current["total_low_80"] = current["expected_total"] - z80 * current["total_sigma"]
    current["total_high_80"] = current["expected_total"] + z80 * current["total_sigma"]

    hp, ap = projected_score(current["expected_margin"], current["expected_total"])
    current["projected_home_score"] = hp
    current["projected_away_score"] = ap
    current["projected_score"] = current.apply(
        lambda r: f"{r.home_team} {r.projected_home_score:.1f} – {r.away_team} {r.projected_away_score:.1f}", axis=1
    )
    current["pick"] = np.where(current["final_home_prob"] >= 0.5, current["home_team"], current["away_team"])

    # The pre-existing confidence machinery was validated around the legacy PURE
    # ensemble. Preserve it as an explicitly legacy diagnostic rather than silently
    # inventing an F-ST confidence model.
    current["model_disagreement"] = base_probs.std(axis=1)
    current["legacy_consistency_flag"] = current.apply(
        lambda r: consistency_flag(r["legacy_final_home_prob"], r["expected_margin"]), axis=1
    )
    current["legacy_confidence"] = current.apply(
        lambda r: confidence_label(r["legacy_final_home_prob"], r["model_disagreement"], r["legacy_consistency_flag"]), axis=1
    )
    current["consistency_flag"] = current["legacy_consistency_flag"]
    current["confidence"] = current["legacy_confidence"]
    current["confidence_diagnostic_scope"] = "legacy_75_25_pure_ensemble"
    # Feed the legacy probability through the legacy confidence-index implementation,
    # then restore the official F-ST probability immediately after diagnostics return.
    official_probability = current["final_home_prob"].copy()
    current["final_home_prob"] = current["legacy_final_home_prob"]
    current = add_confidence_diagnostics(current)
    current["final_home_prob"] = official_probability

    pbp_max = int(pd.to_numeric(bundle.pbp.get("season"), errors="coerce").max()) if len(bundle.pbp) else start
    if pbp_max >= season_to_predict:
        data_state = f"{season_to_predict} schedule/results/Elo + PBP/EPA live"
    else:
        data_state = f"{season_to_predict} schedule/results/Elo live; EPA/form through {pbp_max}"
    timestamp = datetime.now(timezone.utc).isoformat()
    current["data_state"] = data_state
    current["model_version"] = MODEL_VERSION
    current["snapshot_type"] = snapshot_type
    current["prediction_timestamp_utc"] = timestamp

    power = _power_ratings(unresolved, timestamp)
    leaderboard = _leaderboard(historical, baseline, core, margin, total)
    calibration = build_calibration_table(historical, baseline.oof_predictions, core.oof_predictions)
    return PipelineArtifacts(games=games, predictions=current, power_ratings=power, leaderboard=leaderboard, calibration=calibration)
