from __future__ import annotations

"""Frozen Challenger A0: dynamic opponent-adjusted joint score."""

from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .phase3_scaffold import (
    A0_ALPHA_GRID,
    A0_FALLBACK,
    A0_HALF_LIFE_GRID,
    A0_ID,
    SOURCE_CONTRACT_VERSION,
    assert_prediction_receipt,
    assert_prior_only,
    guard_phase3_target_seasons,
    inner_validation_seasons,
)

A0_CAT = ["offense_team", "defense_team"]
A0_NUM = [
    "off_epa_state",
    "opp_def_epa_allowed_state",
    "pass_epa_state",
    "opp_def_pass_epa_allowed_state",
    "success_rate_state",
    "opp_def_success_allowed_state",
    "rest_diff_team",
    "home_indicator",
]


@dataclass(frozen=True)
class A0Selection:
    alpha: float
    half_life: int
    fallback_state: str
    inner_score: dict


def _pipeline(alpha: float) -> Pipeline:
    cat = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    num = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    pre = ColumnTransformer([("cat", cat, A0_CAT), ("num", num, A0_NUM)], remainder="drop")
    return Pipeline([("pre", pre), ("ridge", Ridge(alpha=float(alpha)))])


def _weights(train: pd.DataFrame, half_life: int) -> np.ndarray:
    idx = pd.to_numeric(train["team_game_index"], errors="coerce").fillna(0).to_numpy(dtype=float)
    latest = train.groupby("team")["team_game_index"].transform("max").to_numpy(dtype=float)
    games_ago = np.maximum(latest - idx, 0.0)
    return np.power(0.5, games_ago / float(half_life))


def _fit(train: pd.DataFrame, alpha: float, half_life: int) -> Pipeline:
    model = _pipeline(alpha)
    sw = _weights(train, half_life)
    model.fit(train[A0_CAT + A0_NUM], train["points_for"].astype(float), ridge__sample_weight=sw)
    return model


def _game_metrics(rows: pd.DataFrame, pred: np.ndarray) -> tuple[float, float, float]:
    work = rows[["game_id", "home_indicator", "points_for"]].copy()
    work["pred"] = np.asarray(pred, dtype=float)
    team_mae = float(np.mean(np.abs(work["points_for"].astype(float) - work["pred"])))
    home = work[work["home_indicator"].eq(1)].set_index("game_id")
    away = work[work["home_indicator"].eq(0)].set_index("game_id")
    common = home.index.intersection(away.index)
    if not len(common):
        return team_mae, float("inf"), float("inf")
    h = home.loc[common]
    a = away.loc[common]
    actual_margin = h["points_for"].to_numpy(float) - a["points_for"].to_numpy(float)
    pred_margin = h["pred"].to_numpy(float) - a["pred"].to_numpy(float)
    actual_total = h["points_for"].to_numpy(float) + a["points_for"].to_numpy(float)
    pred_total = h["pred"].to_numpy(float) + a["pred"].to_numpy(float)
    return (
        team_mae,
        float(np.mean(np.abs(actual_margin - pred_margin))),
        float(np.mean(np.abs(actual_total - pred_total))),
    )


def tune_a0(rows: pd.DataFrame, outer_target: int) -> A0Selection:
    folds = inner_validation_seasons(int(outer_target))
    if len(folds) < 2:
        return A0Selection(
            alpha=A0_FALLBACK[0],
            half_life=A0_FALLBACK[1],
            fallback_state="DEFAULT_INSUFFICIENT_INNER_HISTORY",
            inner_score={},
        )

    candidates: list[tuple] = []
    for alpha in A0_ALPHA_GRID:
        for half_life in A0_HALF_LIFE_GRID:
            scores = []
            for season in folds:
                tr = rows[(rows["season"] >= 2016) & (rows["season"] < season) & rows["points_for"].notna()].copy()
                va = rows[(rows["season"] == season) & rows["points_for"].notna()].copy()
                if tr.empty or va.empty:
                    continue
                assert_prior_only(tr, va)
                model = _fit(tr, alpha, half_life)
                scores.append(_game_metrics(va, model.predict(va[A0_CAT + A0_NUM])))
            if len(scores) < 2:
                continue
            arr = np.asarray(scores, dtype=float)
            avg = tuple(float(x) for x in arr.mean(axis=0))
            # Lexicographic frozen objective. Display-precision ties prefer stronger
            # regularization and longer half-life (less reactive weighting).
            key = (
                round(avg[0], 6),
                round(avg[1], 6),
                round(avg[2], 6),
                -float(alpha),
                -int(half_life),
            )
            candidates.append((key, float(alpha), int(half_life), avg))

    if not candidates:
        return A0Selection(
            alpha=A0_FALLBACK[0],
            half_life=A0_FALLBACK[1],
            fallback_state="DEFAULT_INSUFFICIENT_INNER_HISTORY",
            inner_score={},
        )
    candidates.sort(key=lambda x: x[0])
    _, alpha, half_life, avg = candidates[0]
    return A0Selection(
        alpha=alpha,
        half_life=half_life,
        fallback_state="NONE",
        inner_score={"team_points_mae": avg[0], "margin_mae": avg[1], "total_mae": avg[2]},
    )


def _training_covariance(train: pd.DataFrame, model: Pipeline) -> np.ndarray:
    work = train[["game_id", "home_indicator", "points_for"]].copy()
    work["pred"] = model.predict(train[A0_CAT + A0_NUM])
    work["resid"] = work["points_for"].astype(float) - work["pred"].astype(float)
    h = work[work["home_indicator"].eq(1)].set_index("game_id")[["resid"]].rename(columns={"resid": "home"})
    a = work[work["home_indicator"].eq(0)].set_index("game_id")[["resid"]].rename(columns={"resid": "away"})
    pair = h.join(a, how="inner").dropna()
    if len(pair) < 20:
        v = max(float(work["resid"].var(ddof=1)), 1.0)
        return np.array([[v, 0.0], [0.0, v]], dtype=float)
    cov = np.cov(pair[["home", "away"]].to_numpy(dtype=float), rowvar=False, ddof=1)
    cov = np.asarray(cov, dtype=float)
    cov[0, 0] = max(cov[0, 0], 1.0)
    cov[1, 1] = max(cov[1, 1], 1.0)
    # Numerical PSD repair only; no target-season information is used.
    eig = np.linalg.eigvalsh(cov)
    if eig.min() <= 1e-6:
        cov += np.eye(2) * (1e-6 - eig.min() + 1e-6)
    return cov


def _team_effects(model: Pipeline) -> tuple[dict[str, float], dict[str, float]]:
    names = model.named_steps["pre"].get_feature_names_out()
    coef = np.asarray(model.named_steps["ridge"].coef_, dtype=float)
    offense: dict[str, float] = {}
    defense: dict[str, float] = {}
    for name, value in zip(names, coef, strict=False):
        raw = str(name)
        marker_off = "cat__offense_team_"
        marker_def = "cat__defense_team_"
        if raw.startswith(marker_off):
            offense[raw[len(marker_off):]] = float(value)
        elif raw.startswith(marker_def):
            # Larger defense strength means more point suppression.
            defense[raw[len(marker_def):]] = float(-value)
    return offense, defense


def _pair_target_games(target_rows: pd.DataFrame, pred: np.ndarray) -> pd.DataFrame:
    work = target_rows.copy()
    work["expected_points"] = np.asarray(pred, dtype=float)
    home = work[work["home_indicator"].eq(1)].set_index("game_id")
    away = work[work["home_indicator"].eq(0)].set_index("game_id")
    common = sorted(set(home.index).intersection(away.index))
    rows = []
    for game_id in common:
        h = home.loc[game_id]
        a = away.loc[game_id]
        if isinstance(h, pd.DataFrame):
            h = h.iloc[0]
        if isinstance(a, pd.DataFrame):
            a = a.iloc[0]
        rows.append((str(game_id), h, a))
    return pd.DataFrame(
        [
            {
                "game_id": game_id,
                "season": int(h["season"]),
                "week": int(h["week"]),
                "gameday": h.get("gameday"),
                "home_team": str(h["team"]),
                "away_team": str(a["team"]),
                "home_score": float(h["points_for"]),
                "away_score": float(a["points_for"]),
                "expected_home_points": float(h["expected_points"]),
                "expected_away_points": float(a["expected_points"]),
                "rest_diff": float(h["rest_diff_team"]) if pd.notna(h["rest_diff_team"]) else np.nan,
            }
            for game_id, h, a in rows
        ]
    )


def fit_predict_a0_outer(
    rows: pd.DataFrame,
    target_season: int,
    *,
    code_sha: str,
    config_sha: str,
) -> tuple[pd.DataFrame, dict]:
    target_season = guard_phase3_target_seasons([target_season])[0]
    train = rows[
        (rows["season"] >= 2016)
        & (rows["season"] < target_season)
        & rows["points_for"].notna()
    ].copy()
    target = rows[(rows["season"] == target_season) & rows["points_for"].notna()].copy()
    if train.empty or target.empty:
        raise ValueError(f"A0 season {target_season}: missing training or target rows")
    assert_prior_only(train, target)
    selection = tune_a0(rows, target_season)
    model = _fit(train, selection.alpha, selection.half_life)
    cov = _training_covariance(train, model)
    effects_off, effects_def = _team_effects(model)
    games = _pair_target_games(target, model.predict(target[A0_CAT + A0_NUM]))

    var_home = float(cov[0, 0])
    var_away = float(cov[1, 1])
    cov_ha = float(cov[0, 1])
    margin_sd = float(np.sqrt(max(var_home + var_away - 2.0 * cov_ha, 1e-9)))
    total_sd = float(np.sqrt(max(var_home + var_away + 2.0 * cov_ha, 1e-9)))
    nd = NormalDist()
    z50 = nd.inv_cdf(0.75)
    z80 = nd.inv_cdf(0.90)

    games["actual_margin"] = games["home_score"] - games["away_score"]
    games["actual_total"] = games["home_score"] + games["away_score"]
    games["expected_margin"] = games["expected_home_points"] - games["expected_away_points"]
    games["expected_total"] = games["expected_home_points"] + games["expected_away_points"]
    games["home_win_probability"] = games["expected_margin"].map(
        lambda m: float(nd.cdf(float(m) / margin_sd))
    )
    games["home_score_sd"] = np.sqrt(var_home)
    games["away_score_sd"] = np.sqrt(var_away)
    games["margin_sd"] = margin_sd
    games["total_sd"] = total_sd
    games["score_uncertainty"] = float(np.sqrt(var_home + var_away))
    games["margin_p25"] = games["expected_margin"] - z50 * margin_sd
    games["margin_p75"] = games["expected_margin"] + z50 * margin_sd
    games["margin_p10"] = games["expected_margin"] - z80 * margin_sd
    games["margin_p90"] = games["expected_margin"] + z80 * margin_sd
    games["total_p25"] = games["expected_total"] - z50 * total_sd
    games["total_p75"] = games["expected_total"] + z50 * total_sd
    games["total_p10"] = games["expected_total"] - z80 * total_sd
    games["total_p90"] = games["expected_total"] + z80 * total_sd

    games["home_offense_strength"] = games["home_team"].map(effects_off).fillna(0.0)
    games["away_offense_strength"] = games["away_team"].map(effects_off).fillna(0.0)
    games["home_defense_strength"] = games["home_team"].map(effects_def).fillna(0.0)
    games["away_defense_strength"] = games["away_team"].map(effects_def).fillna(0.0)
    games["offense_strength_diff"] = games["home_offense_strength"] - games["away_offense_strength"]
    games["defense_strength_diff"] = games["home_defense_strength"] - games["away_defense_strength"]
    games["summed_offense_strength"] = games["home_offense_strength"] + games["away_offense_strength"]
    games["summed_defense_strength"] = games["home_defense_strength"] + games["away_defense_strength"]

    games["candidate_id"] = A0_ID
    games["outer_target_season"] = int(target_season)
    games["train_through_season"] = int(target_season - 1)
    games["training_through_boundary"] = f"{target_season - 1}-REG-END"
    games["selected_alpha"] = float(selection.alpha)
    games["selected_half_life"] = int(selection.half_life)
    games["source_contract_version"] = SOURCE_CONTRACT_VERSION
    games["code_sha"] = str(code_sha)
    games["config_sha"] = str(config_sha)
    games["fallback_state"] = selection.fallback_state
    games["residual_covariance_version"] = "A0_training_only_home_away_cov_v1"
    games["cov_home_var"] = var_home
    games["cov_away_var"] = var_away
    games["cov_home_away"] = cov_ha
    assert_prediction_receipt(games, A0_ID)

    meta = {
        "candidate_id": A0_ID,
        "target_season": int(target_season),
        "selected_alpha": float(selection.alpha),
        "selected_half_life": int(selection.half_life),
        "fallback_state": selection.fallback_state,
        "inner_score": selection.inner_score,
        "training_games_team_rows": int(len(train)),
        "target_games": int(len(games)),
        "covariance": cov.tolist(),
    }
    return games, meta


def generate_a0_oof(
    rows: pd.DataFrame,
    target_seasons: list[int] | tuple[int, ...],
    *,
    code_sha: str,
    config_sha: str,
) -> tuple[pd.DataFrame, list[dict]]:
    target_seasons = list(guard_phase3_target_seasons(target_seasons))
    parts: list[pd.DataFrame] = []
    meta: list[dict] = []
    for season in target_seasons:
        pred, receipt = fit_predict_a0_outer(
            rows, season, code_sha=code_sha, config_sha=config_sha
        )
        parts.append(pred)
        meta.append(receipt)
    out = pd.concat(parts, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    assert_prediction_receipt(out, A0_ID)
    return out, meta
