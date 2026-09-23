from __future__ import annotations

"""Frozen Challenger C0: market-residual margin / total with M0-M3 nulls."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .phase3_scaffold import (
    C0_ALPHA_FALLBACK,
    C0_ALPHA_GRID,
    C0_ID,
    MARKET_HORIZON_LABEL,
    SOURCE_CONTRACT_VERSION,
    assert_prediction_receipt,
    assert_prior_only,
    guard_phase3_target_seasons,
    inner_validation_seasons,
)

MARGIN_M1 = ["market_margin"]
MARGIN_M2 = [
    "a0_expected_margin",
    "a0_market_margin_disagreement",
    "offense_strength_diff",
    "defense_strength_diff",
    "rest_diff",
]
MARGIN_M3 = ["market_margin"] + MARGIN_M2

TOTAL_M1 = ["market_total"]
TOTAL_M2 = [
    "a0_expected_total",
    "a0_market_total_disagreement",
    "summed_offense_strength",
    "summed_defense_strength",
    "rest_diff",
]
TOTAL_M3 = ["market_total"] + TOTAL_M2


@dataclass(frozen=True)
class C0ArmSelection:
    alpha: float
    fallback_state: str
    inner_mae: float | None


def _ridge(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def build_c0_frame(a0_oof: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    market_cols = [
        c
        for c in (
            "game_id",
            "spread_line",
            "total_line",
        )
        if c in schedules.columns
    ]
    market = schedules[market_cols].drop_duplicates("game_id").copy()
    market["game_id"] = market["game_id"].astype(str)
    frame = a0_oof.copy()
    frame["game_id"] = frame["game_id"].astype(str)
    frame = frame.merge(market, on="game_id", how="left", validate="many_to_one")
    frame["market_margin"] = pd.to_numeric(frame["spread_line"], errors="coerce")
    frame["market_total"] = pd.to_numeric(frame["total_line"], errors="coerce")
    frame["margin_residual_target"] = frame["actual_margin"] - frame["market_margin"]
    frame["total_residual_target"] = frame["actual_total"] - frame["market_total"]
    frame["a0_expected_margin"] = frame["expected_margin"]
    frame["a0_expected_total"] = frame["expected_total"]
    frame["a0_market_margin_disagreement"] = frame["a0_expected_margin"] - frame["market_margin"]
    frame["a0_market_total_disagreement"] = frame["a0_expected_total"] - frame["market_total"]
    frame["market_horizon_label"] = MARKET_HORIZON_LABEL
    return frame


def _tune(
    frame: pd.DataFrame,
    outer_target: int,
    features: list[str],
    residual_target: str,
    market_col: str,
    actual_col: str,
) -> C0ArmSelection:
    folds = inner_validation_seasons(outer_target)
    if len(folds) < 2:
        return C0ArmSelection(C0_ALPHA_FALLBACK, "DEFAULT_INSUFFICIENT_INNER_HISTORY", None)
    scored: list[tuple[float, float]] = []
    for alpha in C0_ALPHA_GRID:
        maes = []
        for season in folds:
            tr = frame[(frame["season"] < season) & frame[residual_target].notna()].copy()
            va = frame[(frame["season"] == season) & frame[residual_target].notna()].copy()
            # A0 OOF representation begins after the 2016 floor; all available
            # C0 rows remain genuinely prior-time A0 forecasts.
            if tr.empty or va.empty:
                continue
            assert_prior_only(tr, va)
            model = _ridge(alpha)
            model.fit(tr[features], tr[residual_target].astype(float))
            residual_pred = model.predict(va[features])
            hybrid = va[market_col].to_numpy(dtype=float) + residual_pred
            maes.append(float(np.mean(np.abs(va[actual_col].to_numpy(dtype=float) - hybrid))))
        if len(maes) >= 2:
            scored.append((float(np.mean(maes)), float(alpha)))
    if not scored:
        return C0ArmSelection(C0_ALPHA_FALLBACK, "DEFAULT_INSUFFICIENT_INNER_HISTORY", None)
    scored.sort(key=lambda x: (round(x[0], 8), -x[1]))
    mae, alpha = scored[0]
    return C0ArmSelection(alpha, "NONE", mae)


def _fit_arm(
    train: pd.DataFrame,
    target: pd.DataFrame,
    features: list[str],
    residual_target: str,
    market_col: str,
    actual_col: str,
    outer_target: int,
) -> tuple[np.ndarray, C0ArmSelection]:
    selection = _tune(train=pd.DataFrame()) if False else _tune(
        pd.concat([train, target], ignore_index=True),
        outer_target,
        features,
        residual_target,
        market_col,
        actual_col,
    )
    model = _ridge(selection.alpha)
    model.fit(train[features], train[residual_target].astype(float))
    return model.predict(target[features]), selection


def fit_predict_c0_outer(
    cframe: pd.DataFrame,
    target_season: int,
    *,
    code_sha: str,
    config_sha: str,
) -> tuple[pd.DataFrame, dict]:
    target_season = guard_phase3_target_seasons([target_season])[0]
    eligible = cframe[
        cframe["market_margin"].notna()
        & cframe["market_total"].notna()
        & cframe["actual_margin"].notna()
        & cframe["actual_total"].notna()
    ].copy()
    train = eligible[eligible["season"] < target_season].copy()
    target = eligible[eligible["season"] == target_season].copy()
    if train.empty or target.empty:
        raise ValueError(f"C0 season {target_season}: missing paired train/target rows")
    assert_prior_only(train, target)

    # Tune each arm and target independently with the frozen Ridge grid.
    m1_sel = _tune(eligible, target_season, MARGIN_M1, "margin_residual_target", "market_margin", "actual_margin")
    m2_sel = _tune(eligible, target_season, MARGIN_M2, "margin_residual_target", "market_margin", "actual_margin")
    m3_sel = _tune(eligible, target_season, MARGIN_M3, "margin_residual_target", "market_margin", "actual_margin")
    t1_sel = _tune(eligible, target_season, TOTAL_M1, "total_residual_target", "market_total", "actual_total")
    t2_sel = _tune(eligible, target_season, TOTAL_M2, "total_residual_target", "market_total", "actual_total")
    t3_sel = _tune(eligible, target_season, TOTAL_M3, "total_residual_target", "market_total", "actual_total")

    def pred(features: list[str], target_col: str, sel: C0ArmSelection) -> np.ndarray:
        model = _ridge(sel.alpha)
        model.fit(train[features], train[target_col].astype(float))
        return model.predict(target[features])

    m1_r = pred(MARGIN_M1, "margin_residual_target", m1_sel)
    m2_r = pred(MARGIN_M2, "margin_residual_target", m2_sel)
    m3_r = pred(MARGIN_M3, "margin_residual_target", m3_sel)
    t1_r = pred(TOTAL_M1, "total_residual_target", t1_sel)
    t2_r = pred(TOTAL_M2, "total_residual_target", t2_sel)
    t3_r = pred(TOTAL_M3, "total_residual_target", t3_sel)

    out_cols = [
        "game_id",
        "season",
        "week",
        "gameday",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "actual_margin",
        "actual_total",
        "rest_diff",
        "market_margin",
        "market_total",
        "market_horizon_label",
        "a0_expected_margin",
        "a0_expected_total",
        "offense_strength_diff",
        "defense_strength_diff",
        "summed_offense_strength",
        "summed_defense_strength",
    ]
    games = target[[c for c in out_cols if c in target.columns]].copy().reset_index(drop=True)
    market_m = games["market_margin"].to_numpy(dtype=float)
    market_t = games["market_total"].to_numpy(dtype=float)
    games["m0_margin"] = market_m
    games["m1_margin_residual"] = m1_r
    games["m1_margin"] = market_m + m1_r
    games["m2_margin_residual"] = m2_r
    games["m2_margin"] = market_m + m2_r
    games["predicted_margin_residual"] = m3_r
    games["hybrid_margin"] = market_m + m3_r
    games["m3_margin"] = games["hybrid_margin"]

    games["m0_total"] = market_t
    games["m1_total_residual"] = t1_r
    games["m1_total"] = market_t + t1_r
    games["m2_total_residual"] = t2_r
    games["m2_total"] = market_t + t2_r
    games["predicted_total_residual"] = t3_r
    games["hybrid_total"] = market_t + t3_r
    games["m3_total"] = games["hybrid_total"]

    games["expected_margin"] = games["hybrid_margin"]
    games["expected_total"] = games["hybrid_total"]
    games["expected_home_points"] = (games["hybrid_total"] + games["hybrid_margin"]) / 2.0
    games["expected_away_points"] = (games["hybrid_total"] - games["hybrid_margin"]) / 2.0
    games["candidate_id"] = C0_ID
    games["outer_target_season"] = int(target_season)
    games["train_through_season"] = int(target_season - 1)
    games["training_through_boundary"] = f"{target_season - 1}-REG-END"
    games["selected_margin_alpha_m1"] = float(m1_sel.alpha)
    games["selected_margin_alpha_m2"] = float(m2_sel.alpha)
    games["selected_margin_alpha_m3"] = float(m3_sel.alpha)
    games["selected_total_alpha_m1"] = float(t1_sel.alpha)
    games["selected_total_alpha_m2"] = float(t2_sel.alpha)
    games["selected_total_alpha_m3"] = float(t3_sel.alpha)
    games["source_contract_version"] = SOURCE_CONTRACT_VERSION
    games["code_sha"] = str(code_sha)
    games["config_sha"] = str(config_sha)
    fallbacks = [
        m1_sel.fallback_state,
        m2_sel.fallback_state,
        m3_sel.fallback_state,
        t1_sel.fallback_state,
        t2_sel.fallback_state,
        t3_sel.fallback_state,
    ]
    games["fallback_state"] = (
        "DEFAULT_INSUFFICIENT_INNER_HISTORY" if any(x != "NONE" for x in fallbacks) else "NONE"
    )
    assert_prediction_receipt(games, C0_ID)

    meta = {
        "candidate_id": C0_ID,
        "target_season": int(target_season),
        "market_horizon_label": MARKET_HORIZON_LABEL,
        "paired_games": int(len(games)),
        "margin": {
            "M1": {"alpha": m1_sel.alpha, "inner_mae": m1_sel.inner_mae, "fallback": m1_sel.fallback_state},
            "M2": {"alpha": m2_sel.alpha, "inner_mae": m2_sel.inner_mae, "fallback": m2_sel.fallback_state},
            "M3": {"alpha": m3_sel.alpha, "inner_mae": m3_sel.inner_mae, "fallback": m3_sel.fallback_state},
        },
        "total": {
            "M1": {"alpha": t1_sel.alpha, "inner_mae": t1_sel.inner_mae, "fallback": t1_sel.fallback_state},
            "M2": {"alpha": t2_sel.alpha, "inner_mae": t2_sel.inner_mae, "fallback": t2_sel.fallback_state},
            "M3": {"alpha": t3_sel.alpha, "inner_mae": t3_sel.inner_mae, "fallback": t3_sel.fallback_state},
        },
    }
    return games, meta


def generate_c0_oof(
    cframe: pd.DataFrame,
    target_seasons: list[int] | tuple[int, ...],
    *,
    code_sha: str,
    config_sha: str,
) -> tuple[pd.DataFrame, list[dict]]:
    seasons = guard_phase3_target_seasons(target_seasons)
    parts: list[pd.DataFrame] = []
    meta: list[dict] = []
    for season in seasons:
        pred, receipt = fit_predict_c0_outer(
            cframe, int(season), code_sha=code_sha, config_sha=config_sha
        )
        parts.append(pred)
        meta.append(receipt)
    out = pd.concat(parts, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    assert_prediction_receipt(out, C0_ID)
    return out, meta
