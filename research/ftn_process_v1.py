from __future__ import annotations

"""Leakage-safe implementation of the preregistered FTN-PROCESS-01 experiment.

This module is research-only. It builds prior-game FTN team state using explicit
point-in-time availability, evaluates a fixed market-conditioned logistic candidate
season-forward through 2025, and never loads or scores completed 2026 outcomes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss

EXPERIMENT_ID = "FTN-PROCESS-01"
MIN_IDENTITY_RATE = 0.995
DECISION_HORIZON_MINUTES = 120
MIN_ROLLING_GAMES = 2
WINDOWS = (3, 6)
TEST_SEASONS = (2023, 2024, 2025)
BOOTSTRAP_REPLICATES = 5000
BOOTSTRAP_SEED = 20260911
EPS = 1e-6

RAW_FIELDS = (
    "n_defense_box",
    "is_motion",
    "is_play_action",
    "is_screen_pass",
    "is_rpo",
    "is_qb_out_of_pocket",
    "is_interception_worthy",
    "n_blitzers",
    "n_pass_rushers",
    "is_qb_fault_sack",
)

OFFENSE_METRICS = {
    "motion_rate": "is_motion",
    "play_action_rate": "is_play_action",
    "screen_rate": "is_screen_pass",
    "rpo_rate": "is_rpo",
    "qb_out_of_pocket_rate": "is_qb_out_of_pocket",
    "interception_worthy_rate": "is_interception_worthy",
    "qb_fault_sack_rate": "is_qb_fault_sack",
}
DEFENSE_METRICS = {
    "mean_defenders_in_box": "n_defense_box",
    "mean_blitzers": "n_blitzers",
    "mean_pass_rushers": "n_pass_rushers",
}
BASE_METRICS = tuple(OFFENSE_METRICS) + tuple(DEFENSE_METRICS)


def matchup_feature_columns() -> list[str]:
    cols: list[str] = []
    for metric in BASE_METRICS:
        cols.extend(
            [
                f"ftn_{metric}_w3_diff",
                f"ftn_{metric}_w6_diff",
                f"ftn_{metric}_change_diff",
            ]
        )
    return cols


def offense_feature_columns() -> list[str]:
    return [c for c in matchup_feature_columns() if any(f"ftn_{m}_" in c for m in OFFENSE_METRICS)]


def defense_feature_columns() -> list[str]:
    return [c for c in matchup_feature_columns() if any(f"ftn_{m}_" in c for m in DEFENSE_METRICS)]


def change_feature_columns() -> list[str]:
    return [c for c in matchup_feature_columns() if c.endswith("_change_diff")]


def quality_control_feature_columns() -> list[str]:
    markers = ("interception_worthy_rate", "qb_fault_sack_rate")
    return [c for c in matchup_feature_columns() if any(marker in c for marker in markers)]


def kickoff_utc(gameday: object, gametime: object) -> datetime:
    local = datetime.strptime(
        f"{str(gameday)[:10]} {str(gametime)[:5]}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=ZoneInfo("America/New_York"))
    return local.astimezone(timezone.utc)


def decision_timestamp_utc(gameday: object, gametime: object) -> datetime:
    return kickoff_utc(gameday, gametime) - timedelta(minutes=DECISION_HORIZON_MINUTES)


def _bool_numeric(series: pd.Series) -> pd.Series:
    mapping = {
        True: 1.0,
        False: 0.0,
        1: 1.0,
        0: 0.0,
        "1": 1.0,
        "0": 0.0,
        "true": 1.0,
        "false": 0.0,
        "True": 1.0,
        "False": 0.0,
    }
    return series.map(mapping).astype(float)


def _utc_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def join_ftn_to_pbp(
    ftn: pd.DataFrame,
    pbp: pd.DataFrame,
    *,
    min_identity_rate: float = MIN_IDENTITY_RATE,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required_ftn = {
        "nflverse_game_id",
        "nflverse_play_id",
        "season",
        "week",
        "date_pulled",
        *RAW_FIELDS,
    }
    missing_ftn = required_ftn - set(ftn.columns)
    if missing_ftn:
        raise ValueError(f"FTN-PROCESS-01 missing FTN fields: {sorted(missing_ftn)}")
    required_pbp = {"game_id", "play_id", "posteam", "defteam"}
    missing_pbp = required_pbp - set(pbp.columns)
    if missing_pbp:
        raise ValueError(f"FTN-PROCESS-01 missing PBP fields: {sorted(missing_pbp)}")

    chart = ftn.copy()
    season = pd.to_numeric(chart["season"], errors="coerce")
    if season.dropna().ge(2026).any():
        raise ValueError("FTN-PROCESS-01 may not load 2026-or-later FTN rows")
    chart["nflverse_game_id"] = chart["nflverse_game_id"].astype(str)
    chart["nflverse_play_id"] = pd.to_numeric(chart["nflverse_play_id"], errors="coerce").astype("Int64")
    chart["date_pulled_utc"] = _utc_series(chart["date_pulled"])

    chart_keys = chart[["nflverse_game_id", "nflverse_play_id"]]
    if chart_keys.isna().any(axis=None):
        raise ValueError("FTN-PROCESS-01 FTN rows contain missing game/play identity")
    if chart_keys.duplicated().any():
        raise ValueError("FTN-PROCESS-01 FTN game/play identity is not unique")

    keys = pbp[["game_id", "play_id", "posteam", "defteam"]].copy()
    keys["game_id"] = keys["game_id"].astype(str)
    keys["play_id"] = pd.to_numeric(keys["play_id"], errors="coerce").astype("Int64")
    keys = keys[keys["game_id"].notna() & keys["play_id"].notna()].copy()
    if keys[["game_id", "play_id"]].duplicated().any():
        raise ValueError("FTN-PROCESS-01 PBP game/play identity is not unique")

    joined = chart.merge(
        keys,
        how="left",
        left_on=["nflverse_game_id", "nflverse_play_id"],
        right_on=["game_id", "play_id"],
        validate="one_to_one",
    )
    matched = joined["posteam"].notna() & joined["defteam"].notna()
    identity_rate = float(matched.mean()) if len(joined) else 0.0
    date_rate = float(joined["date_pulled_utc"].notna().mean()) if len(joined) else 0.0
    if identity_rate < float(min_identity_rate):
        raise RuntimeError(
            f"FTN-PROCESS-01 identity join rate {identity_rate:.6f} < {min_identity_rate:.6f}"
        )
    if date_rate < float(min_identity_rate):
        raise RuntimeError(
            f"FTN-PROCESS-01 date_pulled validity {date_rate:.6f} < {min_identity_rate:.6f}"
        )

    joined = joined[matched & joined["date_pulled_utc"].notna()].copy()
    for field in OFFENSE_METRICS.values():
        joined[field] = _bool_numeric(joined[field])
    for field in DEFENSE_METRICS.values():
        joined[field] = pd.to_numeric(joined[field], errors="coerce")

    audit = {
        "experiment_id": EXPERIMENT_ID,
        "input_ftn_rows": int(len(chart)),
        "eligible_joined_rows": int(len(joined)),
        "identity_join_rate": identity_rate,
        "date_pulled_valid_rate": date_rate,
        "minimum_required_rate": float(min_identity_rate),
        "latest_ftn_season": int(season.dropna().max()) if season.notna().any() else None,
        "completed_2026_outcomes_used": 0,
    }
    return joined, audit


def _named_mean_map(mapping: dict[str, str]) -> dict[str, pd.NamedAgg]:
    return {name: pd.NamedAgg(column=field, aggfunc="mean") for name, field in mapping.items()}


def aggregate_ftn_team_games(
    joined: pd.DataFrame,
    schedules: pd.DataFrame,
) -> pd.DataFrame:
    required_schedule = {"game_id", "season", "week", "gameday", "gametime"}
    missing = required_schedule - set(schedules.columns)
    if missing:
        raise ValueError(f"FTN-PROCESS-01 schedule missing fields: {sorted(missing)}")

    offense = joined.groupby(["nflverse_game_id", "posteam"], dropna=False).agg(
        **_named_mean_map(OFFENSE_METRICS),
        offense_available_at_utc=pd.NamedAgg(column="date_pulled_utc", aggfunc="max"),
    ).reset_index().rename(columns={"posteam": "team"})

    defense = joined.groupby(["nflverse_game_id", "defteam"], dropna=False).agg(
        **_named_mean_map(DEFENSE_METRICS),
        defense_available_at_utc=pd.NamedAgg(column="date_pulled_utc", aggfunc="max"),
    ).reset_index().rename(columns={"defteam": "team"})

    team_games = offense.merge(
        defense,
        on=["nflverse_game_id", "team"],
        how="outer",
        validate="one_to_one",
    )
    team_games["available_at_utc"] = team_games[
        ["offense_available_at_utc", "defense_available_at_utc"]
    ].max(axis=1)

    schedule = schedules[list(required_schedule)].copy()
    schedule["game_id"] = schedule["game_id"].astype(str)
    if schedule["game_id"].duplicated().any():
        raise ValueError("FTN-PROCESS-01 schedule game_id is not unique")
    schedule["source_game_kickoff_utc"] = [
        kickoff_utc(gameday, gametime)
        for gameday, gametime in zip(schedule["gameday"], schedule["gametime"])
    ]
    team_games = team_games.merge(
        schedule,
        how="left",
        left_on="nflverse_game_id",
        right_on="game_id",
        validate="many_to_one",
    )
    if team_games["game_id"].isna().any():
        raise RuntimeError("FTN-PROCESS-01 team-game aggregate missing schedule identity")
    if team_games[["nflverse_game_id", "team"]].duplicated().any():
        raise RuntimeError("FTN-PROCESS-01 duplicate team-game aggregate")
    return team_games.sort_values(["team", "source_game_kickoff_utc", "game_id"]).reset_index(drop=True)


def _rolling_side_state(
    history: pd.DataFrame,
    *,
    team: str,
    target_game_id: str,
    decision_utc: datetime,
) -> tuple[dict[str, float], int]:
    decision = pd.Timestamp(decision_utc)
    eligible = history[
        history["team"].eq(team)
        & history["game_id"].ne(target_game_id)
        & (pd.to_datetime(history["source_game_kickoff_utc"], utc=True) < decision)
        & (pd.to_datetime(history["available_at_utc"], utc=True) <= decision)
    ].sort_values("source_game_kickoff_utc")

    state: dict[str, float] = {}
    for metric in BASE_METRICS:
        for window in WINDOWS:
            recent = eligible.tail(window)
            values = pd.to_numeric(recent[metric], errors="coerce").dropna()
            state[f"{metric}_w{window}"] = (
                float(values.mean()) if len(values) >= MIN_ROLLING_GAMES else np.nan
            )
        w3 = state[f"{metric}_w3"]
        w6 = state[f"{metric}_w6"]
        state[f"{metric}_change"] = float(w3 - w6) if np.isfinite(w3) and np.isfinite(w6) else np.nan
    return state, int(len(eligible))


def build_matchup_features(
    games: pd.DataFrame,
    team_games: pd.DataFrame,
) -> pd.DataFrame:
    required = {
        "game_id", "season", "week", "gameday", "gametime", "home_team", "away_team",
        "home_score", "away_score", "market_home_prob",
    }
    missing = required - set(games.columns)
    if missing:
        raise ValueError(f"FTN-PROCESS-01 target games missing fields: {sorted(missing)}")

    frame = games.copy()
    season = pd.to_numeric(frame["season"], errors="coerce")
    if season.dropna().ge(2026).any():
        raise ValueError("FTN-PROCESS-01 historical evaluation may not contain 2026 games")
    frame["decision_timestamp_utc"] = [
        decision_timestamp_utc(gameday, gametime)
        for gameday, gametime in zip(frame["gameday"], frame["gametime"])
    ]
    frame["home_win"] = np.where(
        frame["home_score"].notna(),
        (pd.to_numeric(frame["home_score"], errors="coerce") > pd.to_numeric(frame["away_score"], errors="coerce")).astype(float),
        np.nan,
    )

    records: list[dict[str, Any]] = []
    for _, game in frame.iterrows():
        decision = game["decision_timestamp_utc"]
        home_state, home_count = _rolling_side_state(
            team_games,
            team=str(game["home_team"]),
            target_game_id=str(game["game_id"]),
            decision_utc=decision,
        )
        away_state, away_count = _rolling_side_state(
            team_games,
            team=str(game["away_team"]),
            target_game_id=str(game["game_id"]),
            decision_utc=decision,
        )
        features: dict[str, Any] = {
            "game_id": str(game["game_id"]),
            "decision_timestamp_utc": decision,
            "ftn_prior_game_count_home": home_count,
            "ftn_prior_game_count_away": away_count,
        }
        for metric in BASE_METRICS:
            for suffix in ("w3", "w6", "change"):
                home_value = home_state[f"{metric}_{suffix}"]
                away_value = away_state[f"{metric}_{suffix}"]
                name = f"ftn_{metric}_{suffix}_diff"
                features[name] = (
                    float(home_value - away_value)
                    if np.isfinite(home_value) and np.isfinite(away_value)
                    else np.nan
                )
        records.append(features)

    feature_frame = pd.DataFrame(records)
    out = frame.merge(feature_frame, on="game_id", how="left", validate="one_to_one", suffixes=("", "_feature"))
    if "decision_timestamp_utc_feature" in out.columns:
        out = out.drop(columns=["decision_timestamp_utc_feature"])
    return out


def _logit(probability: Iterable[float]) -> np.ndarray:
    p = np.clip(np.asarray(list(probability), dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


@dataclass(frozen=True)
class FoldPreprocessor:
    medians: dict[str, float]
    means: dict[str, float]
    scales: dict[str, float]


def preprocess_ftn_fold(
    train: pd.DataFrame,
    test: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[np.ndarray, np.ndarray, FoldPreprocessor, list[str]]:
    train_parts: list[np.ndarray] = []
    test_parts: list[np.ndarray] = []
    medians: dict[str, float] = {}
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    output_names: list[str] = []

    for col in feature_cols:
        tr = pd.to_numeric(train[col], errors="coerce").to_numpy(dtype=float)
        te = pd.to_numeric(test[col], errors="coerce").to_numpy(dtype=float)
        finite = tr[np.isfinite(tr)]
        if finite.size == 0:
            raise RuntimeError(f"FTN-PROCESS-01 feature has no finite training values: {col}")
        median_value = float(np.median(finite))
        tr_missing = ~np.isfinite(tr)
        te_missing = ~np.isfinite(te)
        tr_imp = np.where(tr_missing, median_value, tr)
        te_imp = np.where(te_missing, median_value, te)
        mean_value = float(np.mean(tr_imp))
        scale_value = float(np.std(tr_imp, ddof=0))
        if not math.isfinite(scale_value) or scale_value <= 1e-12:
            scale_value = 1.0
        train_parts.extend([((tr_imp - mean_value) / scale_value)[:, None], tr_missing.astype(float)[:, None]])
        test_parts.extend([((te_imp - mean_value) / scale_value)[:, None], te_missing.astype(float)[:, None]])
        medians[col] = median_value
        means[col] = mean_value
        scales[col] = scale_value
        output_names.extend([col, f"{col}__missing"])

    return (
        np.hstack(train_parts) if train_parts else np.empty((len(train), 0)),
        np.hstack(test_parts) if test_parts else np.empty((len(test), 0)),
        FoldPreprocessor(medians=medians, means=means, scales=scales),
        output_names,
    )


def score_probabilities(y_true: Iterable[float], probability: Iterable[float]) -> dict[str, float]:
    y = np.asarray(list(y_true), dtype=float)
    p = np.clip(np.asarray(list(probability), dtype=float), EPS, 1.0 - EPS)
    brier = float(np.mean((p - y) ** 2))
    loss = float(log_loss(y, p, labels=[0, 1]))
    accuracy = float(np.mean((p >= 0.5).astype(int) == y.astype(int)))
    calibration_intercept = np.nan
    calibration_slope = np.nan
    if len(y) >= 20 and np.unique(y).size == 2:
        calibrator = LogisticRegression(
            C=1e6,
            penalty="l2",
            solver="lbfgs",
            max_iter=3000,
        )
        calibrator.fit(_logit(p)[:, None], y.astype(int))
        calibration_intercept = float(calibrator.intercept_[0])
        calibration_slope = float(calibrator.coef_[0, 0])
    return {
        "brier": brier,
        "log_loss": loss,
        "accuracy": accuracy,
        "calibration_intercept": calibration_intercept,
        "calibration_slope": calibration_slope,
    }


def _eligible_evaluation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    season = pd.to_numeric(out["season"], errors="coerce")
    if season.dropna().ge(2026).any():
        raise ValueError("FTN-PROCESS-01 evaluation frame contains 2026-or-later rows")
    market = pd.to_numeric(out["market_home_prob"], errors="coerce")
    outcome = pd.to_numeric(out["home_win"], errors="coerce")
    keep = market.gt(0.0) & market.lt(1.0) & outcome.isin([0.0, 1.0]) & season.ge(2022) & season.le(2025)
    return out.loc[keep].copy()


def evaluate_feature_set(
    frame: pd.DataFrame,
    feature_cols: list[str],
    *,
    test_seasons: tuple[int, ...] = TEST_SEASONS,
) -> dict[str, Any]:
    data = _eligible_evaluation_frame(frame)
    prediction_parts: list[pd.DataFrame] = []
    fold_metrics: list[dict[str, Any]] = []
    coefficients: list[dict[str, Any]] = []

    for test_season in test_seasons:
        season = pd.to_numeric(data["season"], errors="coerce")
        train = data[season < test_season].copy()
        test = data[season.eq(test_season)].copy()
        if train.empty or test.empty:
            raise RuntimeError(f"FTN-PROCESS-01 missing train/test rows for {test_season}")
        y_train = pd.to_numeric(train["home_win"], errors="raise").astype(int).to_numpy()
        y_test = pd.to_numeric(test["home_win"], errors="raise").astype(int).to_numpy()
        if np.unique(y_train).size != 2:
            raise RuntimeError(f"FTN-PROCESS-01 training fold {test_season} lacks both outcomes")

        market_train = _logit(pd.to_numeric(train["market_home_prob"], errors="raise"))[:, None]
        market_test = _logit(pd.to_numeric(test["market_home_prob"], errors="raise"))[:, None]
        baseline = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=3000)
        baseline.fit(market_train, y_train)
        baseline_prob = baseline.predict_proba(market_test)[:, 1]

        ftn_train, ftn_test, preprocessor, ftn_names = preprocess_ftn_fold(train, test, feature_cols)
        candidate_train = np.hstack([market_train, ftn_train])
        candidate_test = np.hstack([market_test, ftn_test])
        candidate = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=3000)
        candidate.fit(candidate_train, y_train)
        candidate_prob = candidate.predict_proba(candidate_test)[:, 1]

        part = pd.DataFrame(
            {
                "game_id": test["game_id"].astype(str).to_numpy(),
                "season": int(test_season),
                "home_win": y_test,
                "baseline_probability": baseline_prob,
                "candidate_probability": candidate_prob,
                "any_ftn_missing": test[feature_cols].isna().any(axis=1).to_numpy(),
            },
            index=test.index,
        )
        prediction_parts.append(part)
        base_score = score_probabilities(y_test, baseline_prob)
        cand_score = score_probabilities(y_test, candidate_prob)
        fold_metrics.append(
            {
                "test_season": int(test_season),
                "training_seasons": sorted(pd.to_numeric(train["season"], errors="coerce").astype(int).unique().tolist()),
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "baseline": base_score,
                "candidate": cand_score,
                "candidate_minus_baseline_brier": cand_score["brier"] - base_score["brier"],
                "preprocessing": {
                    "medians": preprocessor.medians,
                    "means": preprocessor.means,
                    "scales": preprocessor.scales,
                },
            }
        )
        coef_names = ["market_logit", *ftn_names]
        coefficients.append(
            {
                "test_season": int(test_season),
                "intercept": float(candidate.intercept_[0]),
                "coefficients": {
                    name: float(value)
                    for name, value in zip(coef_names, candidate.coef_[0])
                },
            }
        )

    predictions = pd.concat(prediction_parts).sort_values(["season", "game_id"])
    overall = {
        "baseline": score_probabilities(predictions["home_win"], predictions["baseline_probability"]),
        "candidate": score_probabilities(predictions["home_win"], predictions["candidate_probability"]),
    }
    overall["candidate_minus_baseline_brier"] = overall["candidate"]["brier"] - overall["baseline"]["brier"]
    return {
        "feature_columns": list(feature_cols),
        "predictions": predictions,
        "overall": overall,
        "fold_metrics": fold_metrics,
        "coefficients": coefficients,
    }


def bootstrap_brier_difference(
    predictions: pd.DataFrame,
    *,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float | int]:
    if replicates < 1:
        raise ValueError("bootstrap replicates must be positive")
    rng = np.random.default_rng(seed)
    season_groups = [group for _, group in predictions.groupby("season", sort=True)]
    diffs = np.empty(replicates, dtype=float)
    for i in range(replicates):
        pieces = []
        for group in season_groups:
            positions = rng.integers(0, len(group), size=len(group))
            pieces.append(group.iloc[positions])
        sample = pd.concat(pieces, ignore_index=True)
        y = sample["home_win"].to_numpy(dtype=float)
        baseline = sample["baseline_probability"].to_numpy(dtype=float)
        candidate = sample["candidate_probability"].to_numpy(dtype=float)
        diffs[i] = np.mean((candidate - y) ** 2) - np.mean((baseline - y) ** 2)
    return {
        "replicates": int(replicates),
        "seed": int(seed),
        "mean": float(np.mean(diffs)),
        "lower_95": float(np.quantile(diffs, 0.025)),
        "upper_95": float(np.quantile(diffs, 0.975)),
    }


def _missingness_report(predictions: pd.DataFrame) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for label, mask in {
        "complete_ftn_rows": ~predictions["any_ftn_missing"],
        "rows_with_any_ftn_missing": predictions["any_ftn_missing"],
    }.items():
        subset = predictions[mask]
        if subset.empty:
            out[label] = {"rows": 0}
            continue
        out[label] = {
            "rows": int(len(subset)),
            "baseline": score_probabilities(subset["home_win"], subset["baseline_probability"]),
            "candidate": score_probabilities(subset["home_win"], subset["candidate_probability"]),
        }
    return out


def run_preregistered_evaluation(
    frame: pd.DataFrame,
    *,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
) -> dict[str, Any]:
    full_features = matchup_feature_columns()
    primary = evaluate_feature_set(frame, full_features)
    bootstrap = bootstrap_brier_difference(
        primary["predictions"],
        replicates=bootstrap_replicates,
        seed=BOOTSTRAP_SEED,
    )

    ablation_specs = {
        "offense_process_removed": set(offense_feature_columns()),
        "defense_structure_removed": set(defense_feature_columns()),
        "change_features_removed": set(change_feature_columns()),
        "quality_control_fields_removed": set(quality_control_feature_columns()),
    }
    ablations: dict[str, Any] = {}
    for name, removed in ablation_specs.items():
        features = [col for col in full_features if col not in removed]
        result = evaluate_feature_set(frame, features)
        ablations[name] = {
            "removed_features": sorted(removed),
            "feature_count": len(features),
            "overall": result["overall"],
            "fold_metrics": result["fold_metrics"],
        }

    overall = primary["overall"]
    fold_deltas = [float(row["candidate_minus_baseline_brier"]) for row in primary["fold_metrics"]]
    qualifies = (
        float(overall["candidate_minus_baseline_brier"]) < 0.0
        and float(bootstrap["upper_95"]) < 0.0
        and float(overall["candidate"]["log_loss"]) <= float(overall["baseline"]["log_loss"])
        and all(delta <= 0.010 for delta in fold_deltas)
    )
    conclusion = (
        "FTN-PROCESS-01 qualifies for a research-only prospective shadow candidate under the preregistered rule. No production promotion is authorized."
        if qualifies
        else "FTN-PROCESS-01 is negative or inconclusive under the preregistered rule and may not be rescue-tuned."
    )

    predictions = primary.pop("predictions")
    return {
        "experiment_id": EXPERIMENT_ID,
        "status": "EVALUATED_HISTORICAL_THROUGH_2025",
        "production_effect": "none",
        "benchmark_scope": "conservative_historical_market_conditioned_screen_not_t120_simulation",
        "completed_2026_outcomes_used": 0,
        "candidate_definition": {
            "feature_count": len(full_features),
            "features": full_features,
            "model": "fixed-L2 logistic market logit + standardized FTN matchup features + missing indicators",
        },
        "sample_size": int(len(predictions)),
        "overall_metrics": overall,
        "season_level_metrics": primary["fold_metrics"],
        "coefficient_stability": primary["coefficients"],
        "uncertainty": bootstrap,
        "missing_data_behavior": _missingness_report(predictions),
        "ablations": ablations,
        "qualification_decision": {
            "qualifies_for_shadow_candidate": bool(qualifies),
            "automatic_production_promotion": False,
            "max_season_brier_worsening": max(fold_deltas) if fold_deltas else None,
        },
        "exact_conclusion": conclusion,
        "predictions": predictions,
    }
