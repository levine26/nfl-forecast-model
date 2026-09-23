from __future__ import annotations

"""Frozen Challenger B0: independent possession / drive score process."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .phase3_scaffold import (
    B0_DRIVE_ALPHA_FALLBACK,
    B0_DRIVE_ALPHA_GRID,
    B0_ID,
    B0_OUTCOME_C_FALLBACK,
    B0_OUTCOME_C_GRID,
    B0_SIMULATIONS,
    SOURCE_CONTRACT_VERSION,
    assert_prediction_receipt,
    assert_prior_only,
    empirical_crps,
    empirical_energy_score,
    guard_phase3_target_seasons,
    inner_validation_seasons,
    poisson_deviance_safe,
    stable_seed,
)

DRIVE_NUM = [
    "drive_count_state",
    "opp_drive_count_allowed_state",
    "plays_per_drive_state",
    "opp_plays_per_drive_allowed_state",
    "home_indicator",
    "rest_diff_team",
]

OUTCOME_CAT = ["offense_team", "defense_team"]
OUTCOME_NUM = [
    "home_indicator",
    "rest_diff_team",
    "off_epa_state",
    "opp_def_epa_allowed_state",
    "success_rate_state",
    "opp_def_success_allowed_state",
    "turnover_per_drive_state",
    "opp_takeaway_per_drive_state",
    "explosive_rate_state",
    "opp_explosive_rate_allowed_state",
    "rz_td_state",
    "opp_rz_td_allowed_state",
]


@dataclass(frozen=True)
class B0Selection:
    drive_alpha: float
    outcome_c: float
    drive_fallback: str
    outcome_fallback: str
    drive_inner_deviance: float | None
    outcome_inner_log_loss: float | None


def _drive_pipeline(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("poisson", PoissonRegressor(alpha=float(alpha), max_iter=2000)),
        ]
    )


def _outcome_pipeline(c: float) -> Pipeline:
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
    pre = ColumnTransformer([("cat", cat, OUTCOME_CAT), ("num", num, OUTCOME_NUM)], remainder="drop")
    return Pipeline(
        [
            ("pre", pre),
            (
                "logit",
                LogisticRegression(
                    C=float(c),
                    penalty="l2",
                    solver="lbfgs",
                    max_iter=5000,
                    random_state=2603,
                ),
            ),
        ]
    )


def tune_drive_count(team_rows: pd.DataFrame, outer_target: int) -> tuple[float, str, float | None]:
    folds = inner_validation_seasons(outer_target)
    if len(folds) < 2:
        return B0_DRIVE_ALPHA_FALLBACK, "DEFAULT_INSUFFICIENT_INNER_HISTORY", None
    scored: list[tuple[float, float]] = []
    for alpha in B0_DRIVE_ALPHA_GRID:
        fold_scores = []
        for season in folds:
            tr = team_rows[(team_rows["season"] >= 2016) & (team_rows["season"] < season) & team_rows["drive_count"].notna()].copy()
            va = team_rows[(team_rows["season"] == season) & team_rows["drive_count"].notna()].copy()
            if tr.empty or va.empty:
                continue
            assert_prior_only(tr, va)
            model = _drive_pipeline(alpha)
            model.fit(tr[DRIVE_NUM], tr["drive_count"].astype(float))
            pred = np.clip(model.predict(va[DRIVE_NUM]), 1e-6, None)
            fold_scores.append(poisson_deviance_safe(va["drive_count"], pred))
        if len(fold_scores) >= 2:
            scored.append((float(np.mean(fold_scores)), float(alpha)))
    if not scored:
        return B0_DRIVE_ALPHA_FALLBACK, "DEFAULT_INSUFFICIENT_INNER_HISTORY", None
    # Display-precision tie -> stronger regularization.
    scored.sort(key=lambda x: (round(x[0], 8), -x[1]))
    best = scored[0]
    return best[1], "NONE", best[0]


def tune_outcome(outcome_rows: pd.DataFrame, outer_target: int) -> tuple[float, str, float | None]:
    folds = inner_validation_seasons(outer_target)
    if len(folds) < 2:
        return B0_OUTCOME_C_FALLBACK, "DEFAULT_INSUFFICIENT_INNER_HISTORY", None
    scored: list[tuple[float, float]] = []
    labels = ["EMPTY", "FG", "TD"]
    for c in B0_OUTCOME_C_GRID:
        fold_scores = []
        for season in folds:
            tr = outcome_rows[(outcome_rows["season"] >= 2016) & (outcome_rows["season"] < season)].copy()
            va = outcome_rows[outcome_rows["season"] == season].copy()
            if tr.empty or va.empty or set(labels) - set(tr["outcome"].astype(str).unique()):
                continue
            assert_prior_only(tr, va)
            model = _outcome_pipeline(c)
            model.fit(tr[OUTCOME_CAT + OUTCOME_NUM], tr["outcome"].astype(str))
            prob = model.predict_proba(va[OUTCOME_CAT + OUTCOME_NUM])
            fold_scores.append(float(log_loss(va["outcome"].astype(str), prob, labels=list(model.named_steps["logit"].classes_))))
        if len(fold_scores) >= 2:
            scored.append((float(np.mean(fold_scores)), float(c)))
    if not scored:
        return B0_OUTCOME_C_FALLBACK, "DEFAULT_INSUFFICIENT_INNER_HISTORY", None
    # Smaller C is more regularized and wins displayed-precision ties.
    scored.sort(key=lambda x: (round(x[0], 8), x[1]))
    best = scored[0]
    return best[1], "NONE", best[0]


def select_b0(team_rows: pd.DataFrame, outcome_rows: pd.DataFrame, outer_target: int) -> B0Selection:
    alpha, d_fb, dev = tune_drive_count(team_rows, outer_target)
    c, o_fb, ll = tune_outcome(outcome_rows, outer_target)
    return B0Selection(
        drive_alpha=float(alpha),
        outcome_c=float(c),
        drive_fallback=d_fb,
        outcome_fallback=o_fb,
        drive_inner_deviance=dev,
        outcome_inner_log_loss=ll,
    )


def _class_probabilities(model: Pipeline, frame: pd.DataFrame) -> pd.DataFrame:
    probs = model.predict_proba(frame[OUTCOME_CAT + OUTCOME_NUM])
    classes = [str(x) for x in model.named_steps["logit"].classes_]
    out = pd.DataFrame(probs, columns=classes, index=frame.index)
    for label in ("TD", "FG", "EMPTY"):
        if label not in out.columns:
            out[label] = 0.0
    return out[["TD", "FG", "EMPTY"]]


def _td_point_probs(train_drives: pd.DataFrame) -> np.ndarray:
    td = pd.to_numeric(
        train_drives.loc[train_drives["outcome"].eq("TD"), "td_points"], errors="coerce"
    ).dropna()
    counts = np.array([(td == 6).sum(), (td == 7).sum(), (td == 8).sum()], dtype=float)
    if counts.sum() <= 0:
        return np.array([0.0, 1.0, 0.0], dtype=float)
    return counts / counts.sum()


def _td_points_from_counts(rng: np.random.Generator, td_count: np.ndarray, probs: np.ndarray) -> np.ndarray:
    td_count = np.asarray(td_count, dtype=int)
    p6, p7, p8 = [float(x) for x in probs]
    n6 = rng.binomial(td_count, p6) if p6 > 0 else np.zeros_like(td_count)
    rem = td_count - n6
    denom = p7 + p8
    p8_cond = p8 / denom if denom > 0 else 0.0
    n8 = rng.binomial(rem, p8_cond) if p8_cond > 0 else np.zeros_like(rem)
    n7 = rem - n8
    return 6 * n6 + 7 * n7 + 8 * n8


def _simulate_team_scores(
    rng: np.random.Generator,
    n_drives: np.ndarray,
    p_td: float,
    p_fg: float,
    td_point_probs: np.ndarray,
    rare_values: np.ndarray,
) -> np.ndarray:
    n = np.asarray(n_drives, dtype=int)
    td = rng.binomial(n, float(np.clip(p_td, 0.0, 1.0)))
    remaining = n - td
    denom = max(1.0 - float(p_td), 1e-12)
    fg_cond = float(np.clip(p_fg / denom, 0.0, 1.0))
    fg = rng.binomial(remaining, fg_cond)
    td_points = _td_points_from_counts(rng, td, td_point_probs)
    rare = rng.choice(rare_values, size=len(n), replace=True) if len(rare_values) else np.zeros(len(n))
    return td_points.astype(float) + 3.0 * fg.astype(float) + rare.astype(float)


def _quantiles(values: np.ndarray) -> dict[str, float]:
    return {
        "p10": float(np.quantile(values, 0.10)),
        "p25": float(np.quantile(values, 0.25)),
        "p50": float(np.quantile(values, 0.50)),
        "p75": float(np.quantile(values, 0.75)),
        "p90": float(np.quantile(values, 0.90)),
    }


def fit_predict_b0_outer(
    team_rows: pd.DataFrame,
    outcome_rows: pd.DataFrame,
    drives: pd.DataFrame,
    rare_points: pd.DataFrame,
    schedules: pd.DataFrame,
    target_season: int,
    *,
    code_sha: str,
    config_sha: str,
    simulations: int = B0_SIMULATIONS,
) -> tuple[pd.DataFrame, dict]:
    target_season = guard_phase3_target_seasons([target_season])[0]
    selection = select_b0(team_rows, outcome_rows, target_season)

    train_team = team_rows[(team_rows["season"] >= 2016) & (team_rows["season"] < target_season) & team_rows["drive_count"].notna()].copy()
    target_team = team_rows[(team_rows["season"] == target_season) & team_rows["drive_count"].notna()].copy()
    train_out = outcome_rows[(outcome_rows["season"] >= 2016) & (outcome_rows["season"] < target_season)].copy()
    if train_team.empty or target_team.empty or train_out.empty:
        raise ValueError(f"B0 season {target_season}: missing train/target data")
    assert_prior_only(train_team, target_team)
    if set(["EMPTY", "FG", "TD"]) - set(train_out["outcome"].astype(str).unique()):
        raise ValueError(f"B0 season {target_season}: training taxonomy lacks a required outcome class")

    drive_model = _drive_pipeline(selection.drive_alpha)
    drive_model.fit(train_team[DRIVE_NUM], train_team["drive_count"].astype(float))
    outcome_model = _outcome_pipeline(selection.outcome_c)
    outcome_model.fit(train_out[OUTCOME_CAT + OUTCOME_NUM], train_out["outcome"].astype(str))

    target_team = target_team.copy()
    target_team["expected_drives"] = np.clip(drive_model.predict(target_team[DRIVE_NUM]), 1.0, None)
    probs = _class_probabilities(outcome_model, target_team)
    target_team[["p_td", "p_fg", "p_empty"]] = probs[["TD", "FG", "EMPTY"]].to_numpy()

    # Training-only shared game-volume empirical residual.
    train_pred = np.clip(drive_model.predict(train_team[DRIVE_NUM]), 1e-6, None)
    volume = train_team[["game_id"]].copy()
    volume["resid"] = train_team["drive_count"].to_numpy(dtype=float) - train_pred
    volume_resid = volume.groupby("game_id")["resid"].mean().to_numpy(dtype=float)
    volume_resid = volume_resid[np.isfinite(volume_resid)]
    if not len(volume_resid):
        volume_resid = np.array([0.0], dtype=float)

    train_drives = drives[(drives["season"] >= 2016) & (drives["season"] < target_season)].copy()
    td_probs = _td_point_probs(train_drives)
    rare_train = rare_points[(rare_points["season"] >= 2016) & (rare_points["season"] < target_season)]
    rare_values = pd.to_numeric(rare_train["rare_points"], errors="coerce").dropna().to_numpy(dtype=float)
    rare_fallback = "NONE"
    if not len(rare_values):
        rare_values = np.array([0.0], dtype=float)
        rare_fallback = "RARE_SOURCE_UNAVAILABLE_ZERO_FALLBACK"

    # Diagnostic only; never switches the count family.
    pearson = np.sum((train_team["drive_count"].to_numpy(float) - train_pred) ** 2 / np.clip(train_pred, 1e-6, None))
    dof = max(len(train_team) - len(DRIVE_NUM) - 1, 1)
    overdispersion = float(pearson / dof)

    schedule_target = schedules[schedules["season"].eq(target_season)].drop_duplicates("game_id").set_index("game_id")
    home = target_team[target_team["home_indicator"].eq(1)].set_index("game_id")
    away = target_team[target_team["home_indicator"].eq(0)].set_index("game_id")
    common = sorted(set(home.index).intersection(away.index).intersection(schedule_target.index))
    rows: list[dict] = []
    for game_id in common:
        h = home.loc[game_id]
        a = away.loc[game_id]
        s = schedule_target.loc[game_id]
        if isinstance(h, pd.DataFrame):
            h = h.iloc[0]
        if isinstance(a, pd.DataFrame):
            a = a.iloc[0]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[0]
        seed = stable_seed(B0_ID, str(game_id))
        rng = np.random.default_rng(seed)
        shared = rng.choice(volume_resid, size=int(simulations), replace=True)
        lam_h = np.clip(float(h["expected_drives"]) + shared, 1.0, None)
        lam_a = np.clip(float(a["expected_drives"]) + shared, 1.0, None)
        n_h = rng.poisson(lam_h)
        n_a = rng.poisson(lam_a)
        score_h = _simulate_team_scores(rng, n_h, float(h["p_td"]), float(h["p_fg"]), td_probs, rare_values)
        score_a = _simulate_team_scores(rng, n_a, float(a["p_td"]), float(a["p_fg"]), td_probs, rare_values)
        margin = score_h - score_a
        total = score_h + score_a
        qh, qa, qm, qt = _quantiles(score_h), _quantiles(score_a), _quantiles(margin), _quantiles(total)
        actual_h = float(s["home_score"])
        actual_a = float(s["away_score"])
        actual_m = actual_h - actual_a
        actual_t = actual_h + actual_a
        score_pairs = np.column_stack([score_h, score_a])
        rows.append(
            {
                "game_id": str(game_id),
                "season": int(target_season),
                "week": int(s["week"]),
                "gameday": s.get("gameday"),
                "home_team": str(s["home_team"]),
                "away_team": str(s["away_team"]),
                "home_score": actual_h,
                "away_score": actual_a,
                "actual_margin": actual_m,
                "actual_total": actual_t,
                "expected_home_points": float(score_h.mean()),
                "expected_away_points": float(score_a.mean()),
                "expected_margin": float(margin.mean()),
                "expected_total": float(total.mean()),
                "home_win_probability": float(np.mean(margin > 0) + 0.5 * np.mean(margin == 0)),
                "home_score_variance": float(np.var(score_h, ddof=1)),
                "away_score_variance": float(np.var(score_a, ddof=1)),
                "margin_variance": float(np.var(margin, ddof=1)),
                "total_variance": float(np.var(total, ddof=1)),
                "expected_home_drives": float(h["expected_drives"]),
                "expected_away_drives": float(a["expected_drives"]),
                "home_p_td": float(h["p_td"]),
                "home_p_fg": float(h["p_fg"]),
                "away_p_td": float(a["p_td"]),
                "away_p_fg": float(a["p_fg"]),
                "home_p10": qh["p10"],
                "home_p25": qh["p25"],
                "home_p50": qh["p50"],
                "home_p75": qh["p75"],
                "home_p90": qh["p90"],
                "away_p10": qa["p10"],
                "away_p25": qa["p25"],
                "away_p50": qa["p50"],
                "away_p75": qa["p75"],
                "away_p90": qa["p90"],
                "margin_p10": qm["p10"],
                "margin_p25": qm["p25"],
                "margin_p50": qm["p50"],
                "margin_p75": qm["p75"],
                "margin_p90": qm["p90"],
                "total_p10": qt["p10"],
                "total_p25": qt["p25"],
                "total_p50": qt["p50"],
                "total_p75": qt["p75"],
                "total_p90": qt["p90"],
                "home_crps": empirical_crps(actual_h, score_h),
                "away_crps": empirical_crps(actual_a, score_a),
                "margin_crps": empirical_crps(actual_m, margin),
                "total_crps": empirical_crps(actual_t, total),
                "joint_energy_score": empirical_energy_score(actual_h, actual_a, score_pairs, seed=seed),
                "simulation_seed": int(seed),
            }
        )

    games = pd.DataFrame(rows)
    fallback_parts = [x for x in (selection.drive_fallback, selection.outcome_fallback, rare_fallback) if x != "NONE"]
    games["candidate_id"] = B0_ID
    games["outer_target_season"] = int(target_season)
    games["train_through_season"] = int(target_season - 1)
    games["training_through_boundary"] = f"{target_season - 1}-REG-END"
    games["selected_drive_alpha"] = float(selection.drive_alpha)
    games["selected_outcome_c"] = float(selection.outcome_c)
    games["source_contract_version"] = SOURCE_CONTRACT_VERSION
    games["code_sha"] = str(code_sha)
    games["config_sha"] = str(config_sha)
    games["fallback_state"] = ";".join(fallback_parts) if fallback_parts else "NONE"
    games["simulation_version"] = "B0-poisson-multinomial-rare-tail-v1"
    games["simulation_draws"] = int(simulations)
    assert_prediction_receipt(games, B0_ID)

    meta = {
        "candidate_id": B0_ID,
        "target_season": int(target_season),
        "selected_drive_alpha": float(selection.drive_alpha),
        "selected_outcome_c": float(selection.outcome_c),
        "drive_fallback": selection.drive_fallback,
        "outcome_fallback": selection.outcome_fallback,
        "rare_fallback": rare_fallback,
        "drive_inner_poisson_deviance": selection.drive_inner_deviance,
        "outcome_inner_log_loss": selection.outcome_inner_log_loss,
        "drive_overdispersion_diagnostic": overdispersion,
        "td_point_probabilities_6_7_8": td_probs.tolist(),
        "training_team_rows": int(len(train_team)),
        "training_drive_rows": int(len(train_out)),
        "target_games": int(len(games)),
        "simulations_per_game": int(simulations),
    }
    return games, meta


def generate_b0_oof(
    team_rows: pd.DataFrame,
    outcome_rows: pd.DataFrame,
    drives: pd.DataFrame,
    rare_points: pd.DataFrame,
    schedules: pd.DataFrame,
    target_seasons: list[int] | tuple[int, ...],
    *,
    code_sha: str,
    config_sha: str,
    simulations: int = B0_SIMULATIONS,
) -> tuple[pd.DataFrame, list[dict]]:
    seasons = guard_phase3_target_seasons(target_seasons)
    parts: list[pd.DataFrame] = []
    meta: list[dict] = []
    for season in seasons:
        pred, receipt = fit_predict_b0_outer(
            team_rows,
            outcome_rows,
            drives,
            rare_points,
            schedules,
            int(season),
            code_sha=code_sha,
            config_sha=config_sha,
            simulations=simulations,
        )
        parts.append(pred)
        meta.append(receipt)
    out = pd.concat(parts, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    assert_prediction_receipt(out, B0_ID)
    return out, meta
