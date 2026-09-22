from __future__ import annotations

"""Phase 1 structural error slices not used as model-selection features.

This module adds descriptive pregame-form/pace/data-quality slices and clearly
separates schedule-recorded weather observations from point-in-time forecast weather.
It does not tune or modify production models.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features, core_columns

TARGET_SEASONS = (2022, 2023, 2024, 2025)


def _metrics(part: pd.DataFrame) -> dict:
    if part.empty:
        return {"games": 0}
    margin_err = pd.to_numeric(part["actual_margin"], errors="coerce") - pd.to_numeric(part["model_margin"], errors="coerce")
    total_err = pd.to_numeric(part["actual_total"], errors="coerce") - pd.to_numeric(part["model_total"], errors="coerce")
    return {
        "games": int(len(part)),
        "margin_mae": float(margin_err.abs().mean()),
        "margin_bias_actual_minus_pred": float(margin_err.mean()),
        "total_mae": float(total_err.abs().mean()),
        "total_bias_actual_minus_pred": float(total_err.mean()),
    }


def _qcut(frame: pd.DataFrame, col: str, labels: tuple[str, ...]) -> pd.Series:
    values = pd.to_numeric(frame[col], errors="coerce")
    try:
        return pd.qcut(values, q=len(labels), labels=list(labels), duplicates="drop")
    except ValueError:
        return pd.Series(pd.NA, index=frame.index, dtype="object")


def _team_pregame_pace(team_games: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in ("game_id", "season", "week", "gameday", "team", "off_plays") if c in team_games.columns]
    if "off_plays" not in cols:
        return pd.DataFrame()
    t = team_games[cols].copy()
    t["off_plays"] = pd.to_numeric(t["off_plays"], errors="coerce")
    t = t.sort_values(["team", "season", "week", "gameday", "game_id"], na_position="last")
    t["prior5_off_plays"] = t.groupby("team")["off_plays"].transform(
        lambda s: s.shift(1).rolling(5, min_periods=1).mean()
    )
    return t[["game_id", "team", "prior5_off_plays"]].drop_duplicates(["game_id", "team"], keep="last")


def run(
    baseline_path: str = "research_outputs/spread_points_phase1/baseline_predictions_2022_2025.csv",
    output_dir: str = "research_outputs/spread_points_phase1",
    config_path: str = "config/model.yaml",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    baseline = pd.read_csv(baseline_path)
    baseline = baseline[pd.to_numeric(baseline["season"], errors="coerce").isin(TARGET_SEASONS)].copy()

    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    bundle = load_core_data(range(start, 2026), cfg["data"]["cache_dir"])
    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(bundle.pbp, cfg["data"]["neutral_wp_lower"], cfg["data"]["neutral_wp_upper"])
    team_games = add_game_results(team_games, bundle.schedules)
    games = build_matchup_features(team_games, bundle.schedules, elo)
    games = games[pd.to_numeric(games["season"], errors="coerce").isin(TARGET_SEASONS)].copy()

    feature_cols = core_columns(games)
    feature_frame = games[["game_id", *feature_cols]].copy()
    feature_frame["core_feature_missing_count"] = feature_frame[feature_cols].isna().sum(axis=1)
    merged = baseline.merge(feature_frame, on="game_id", how="left", validate="one_to_one")

    report: dict = {
        "status": "research_only_descriptive",
        "production_changed": False,
        "target_seasons": list(TARGET_SEASONS),
        "games": int(len(merged)),
        "recent_form": {},
        "pregame_pace": {},
        "data_quality": {},
        "weather": {},
    }
    rows: list[dict] = []

    form_cols = [
        "diff_off_epa_ewma",
        "diff_pass_epa_ewma",
        "diff_rush_epa_ewma",
        "diff_success_rate_ewma",
        "diff_win_ewma",
    ]
    for col in form_cols:
        if col not in merged.columns:
            report["recent_form"][col] = {"status": "unavailable"}
            continue
        valid = merged[pd.to_numeric(merged[col], errors="coerce").notna()].copy()
        valid["bucket"] = _qcut(valid, col, ("Q1_low_home_minus_away", "Q2", "Q3", "Q4_high_home_minus_away"))
        bucket_rows = []
        for bucket, part in valid.groupby("bucket", observed=True):
            item = {"bucket": str(bucket), **_metrics(part)}
            bucket_rows.append(item)
            rows.append({"dimension": f"recent_form:{col}", **item})
        x = pd.to_numeric(valid[col], errors="coerce")
        abs_margin_error = (valid["actual_margin"] - valid["model_margin"]).abs()
        abs_total_error = (valid["actual_total"] - valid["model_total"]).abs()
        report["recent_form"][col] = {
            "status": "available",
            "games": int(len(valid)),
            "corr_raw_with_abs_margin_error": float(x.corr(abs_margin_error)),
            "corr_raw_with_abs_total_error": float(x.corr(abs_total_error)),
            "corr_abs_with_abs_margin_error": float(x.abs().corr(abs_margin_error)),
            "corr_abs_with_abs_total_error": float(x.abs().corr(abs_total_error)),
            "quartiles": bucket_rows,
        }

    pace = _team_pregame_pace(team_games)
    if not pace.empty:
        home = pace.rename(columns={"team": "home_team", "prior5_off_plays": "home_prior5_off_plays"})
        away = pace.rename(columns={"team": "away_team", "prior5_off_plays": "away_prior5_off_plays"})
        pm = games[["game_id", "home_team", "away_team"]].merge(home, on=["game_id", "home_team"], how="left")
        pm = pm.merge(away, on=["game_id", "away_team"], how="left")
        pm["pregame_combined_prior5_off_plays"] = pm["home_prior5_off_plays"] + pm["away_prior5_off_plays"]
        merged = merged.merge(pm[["game_id", "pregame_combined_prior5_off_plays"]], on="game_id", how="left")
        valid = merged[pd.to_numeric(merged["pregame_combined_prior5_off_plays"], errors="coerce").notna()].copy()
        valid["bucket"] = _qcut(valid, "pregame_combined_prior5_off_plays", ("Q1_slowest", "Q2", "Q3", "Q4_fastest"))
        bucket_rows = []
        for bucket, part in valid.groupby("bucket", observed=True):
            item = {"bucket": str(bucket), **_metrics(part)}
            bucket_rows.append(item)
            rows.append({"dimension": "pregame_pace:prior5_offensive_plays", **item})
        x = pd.to_numeric(valid["pregame_combined_prior5_off_plays"], errors="coerce")
        report["pregame_pace"] = {
            "status": "available_research_diagnostic_not_current_model_feature",
            "definition": "sum of each team's mean offensive plays over its prior five completed regular-season games",
            "games": int(len(valid)),
            "corr_with_abs_margin_error": float(x.corr((valid["actual_margin"] - valid["model_margin"]).abs())),
            "corr_with_abs_total_error": float(x.corr((valid["actual_total"] - valid["model_total"]).abs())),
            "quartiles": bucket_rows,
        }
    else:
        report["pregame_pace"] = {"status": "unavailable"}

    miss = pd.to_numeric(merged["core_feature_missing_count"], errors="coerce")
    merged["missingness_bucket"] = pd.cut(
        miss,
        bins=[-1, 0, 5, np.inf],
        labels=["0_missing", "1_to_5_missing", "6plus_missing"],
    )
    dq_rows = []
    for bucket, part in merged.groupby("missingness_bucket", observed=True):
        item = {"bucket": str(bucket), **_metrics(part)}
        dq_rows.append(item)
        rows.append({"dimension": "data_quality:core_feature_missingness", **item})
    report["data_quality"] = {
        "definition": "number of current core model features missing before SimpleImputer median imputation",
        "feature_count": int(len(feature_cols)),
        "mean_missing_features": float(miss.mean()),
        "max_missing_features": int(miss.max()) if miss.notna().any() else None,
        "buckets": dq_rows,
        "feature_missing_rates": {
            col: float(pd.to_numeric(merged[col], errors="coerce").isna().mean())
            for col in feature_cols
        },
    }

    # Schedule weather fields are observational metadata, not point-in-time forecast receipts.
    # They can diagnose association with errors but are not safe historical pregame features.
    weather_cols = [c for c in ("game_id", "roof", "temp", "wind") if c in bundle.schedules.columns]
    if len(weather_cols) > 1:
        wx = bundle.schedules[weather_cols].drop_duplicates("game_id", keep="last")
        wm = merged.merge(wx, on="game_id", how="left")
        report["weather"]["point_in_time_status"] = (
            "schedule-recorded observational metadata only; not equivalent to a forecast known at the decision horizon"
        )
        if "roof" in wm.columns:
            roof_rows = []
            for bucket, part in wm[wm["roof"].notna()].groupby(wm["roof"].astype(str).str.lower()):
                item = {"bucket": str(bucket), **_metrics(part)}
                roof_rows.append(item)
                rows.append({"dimension": "weather:roof_observed", **item})
            report["weather"]["roof"] = roof_rows
        if "temp" in wm.columns:
            temp = pd.to_numeric(wm["temp"], errors="coerce")
            wm["temp_bucket"] = pd.cut(temp, bins=[-np.inf, 32, 50, 80, np.inf], labels=["<=32F", "33_50F", "51_80F", ">80F"])
            temp_rows = []
            for bucket, part in wm.groupby("temp_bucket", observed=True):
                item = {"bucket": str(bucket), **_metrics(part)}
                temp_rows.append(item)
                rows.append({"dimension": "weather:observed_temperature", **item})
            report["weather"]["temperature"] = temp_rows
        if "wind" in wm.columns:
            wind = pd.to_numeric(wm["wind"], errors="coerce")
            wm["wind_bucket"] = pd.cut(wind, bins=[-np.inf, 9.999, 19.999, np.inf], labels=["<10mph", "10_19mph", "20plus_mph"])
            wind_rows = []
            for bucket, part in wm.groupby("wind_bucket", observed=True):
                item = {"bucket": str(bucket), **_metrics(part)}
                wind_rows.append(item)
                rows.append({"dimension": "weather:observed_wind", **item})
            report["weather"]["wind"] = wind_rows
    else:
        report["weather"] = {
            "status": "unavailable_in_schedule_frame",
            "point_in_time_status": "historical point-in-time weather remains a separately governed research source",
        }

    pd.DataFrame(rows).to_csv(out / "structural_error_slices.csv", index=False)
    (out / "structural_error_slices.json").write_text(json.dumps(report, indent=2, allow_nan=True), encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="research_outputs/spread_points_phase1/baseline_predictions_2022_2025.csv")
    parser.add_argument("--output-dir", default="research_outputs/spread_points_phase1")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    print(json.dumps(run(args.baseline, args.output_dir, args.config), indent=2, allow_nan=True))
