from __future__ import annotations

"""Shared Phase 3 evaluation, baselines, diagnostic slices and conditional D gate."""

from statistics import NormalDist

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .phase3_scaffold import (
    D_MARGIN_ID,
    D_TOTAL_ID,
    SOURCE_CONTRACT_VERSION,
    d_gate_contract,
    gaussian_crps,
    interval_metrics,
    numeric_metrics,
    paired_market_metrics,
    probability_metrics,
    season_week_block_bootstrap,
)


def evaluate_a0(frame: pd.DataFrame) -> dict:
    win = (frame["actual_margin"] > 0).astype(int)
    result = {
        "home_points": numeric_metrics(frame["home_score"], frame["expected_home_points"]),
        "away_points": numeric_metrics(frame["away_score"], frame["expected_away_points"]),
        "margin": numeric_metrics(frame["actual_margin"], frame["expected_margin"]),
        "total": numeric_metrics(frame["actual_total"], frame["expected_total"]),
        "probability": probability_metrics(win, frame["home_win_probability"]),
        "distribution": {
            "margin_50": interval_metrics(frame["actual_margin"], frame["margin_p25"], frame["margin_p75"]),
            "margin_80": interval_metrics(frame["actual_margin"], frame["margin_p10"], frame["margin_p90"]),
            "total_50": interval_metrics(frame["actual_total"], frame["total_p25"], frame["total_p75"]),
            "total_80": interval_metrics(frame["actual_total"], frame["total_p10"], frame["total_p90"]),
            "margin_crps": gaussian_crps(frame["actual_margin"], frame["expected_margin"], frame["margin_sd"]),
            "total_crps": gaussian_crps(frame["actual_total"], frame["expected_total"], frame["total_sd"]),
            "joint_energy_score": None,
            "joint_energy_score_note": "A0 retained Gaussian covariance parameters rather than raw Monte Carlo draws; univariate proper scores and coverage are primary in Phase 3.",
        },
    }
    return result


def evaluate_b0(frame: pd.DataFrame) -> dict:
    win = (frame["actual_margin"] > 0).astype(int)
    return {
        "home_points": numeric_metrics(frame["home_score"], frame["expected_home_points"]),
        "away_points": numeric_metrics(frame["away_score"], frame["expected_away_points"]),
        "margin": numeric_metrics(frame["actual_margin"], frame["expected_margin"]),
        "total": numeric_metrics(frame["actual_total"], frame["expected_total"]),
        "probability": probability_metrics(win, frame["home_win_probability"]),
        "distribution": {
            "home_50": interval_metrics(frame["home_score"], frame["home_p25"], frame["home_p75"]),
            "home_80": interval_metrics(frame["home_score"], frame["home_p10"], frame["home_p90"]),
            "away_50": interval_metrics(frame["away_score"], frame["away_p25"], frame["away_p75"]),
            "away_80": interval_metrics(frame["away_score"], frame["away_p10"], frame["away_p90"]),
            "margin_50": interval_metrics(frame["actual_margin"], frame["margin_p25"], frame["margin_p75"]),
            "margin_80": interval_metrics(frame["actual_margin"], frame["margin_p10"], frame["margin_p90"]),
            "total_50": interval_metrics(frame["actual_total"], frame["total_p25"], frame["total_p75"]),
            "total_80": interval_metrics(frame["actual_total"], frame["total_p10"], frame["total_p90"]),
            "home_crps": float(frame["home_crps"].mean()),
            "away_crps": float(frame["away_crps"].mean()),
            "margin_crps": float(frame["margin_crps"].mean()),
            "total_crps": float(frame["total_crps"].mean()),
            "joint_energy_score": float(frame["joint_energy_score"].mean()),
            "log_score": None,
            "log_score_note": "Not reported: finite empirical score-mass log scores from 10k draws are too sensitive to zero-cell smoothing for this reference simulator.",
        },
    }


def evaluate_c0(frame: pd.DataFrame) -> dict:
    arms = {}
    for arm in ("m0", "m1", "m2", "m3"):
        arms[arm.upper()] = {
            "margin": numeric_metrics(frame["actual_margin"], frame[f"{arm}_margin"]),
            "total": numeric_metrics(frame["actual_total"], frame[f"{arm}_total"]),
        }
    m2_margin_edge = arms["M2"]["margin"]["mae"] < arms["M0"]["margin"]["mae"]
    m3_margin_edge = arms["M3"]["margin"]["mae"] < arms["M1"]["margin"]["mae"]
    m2_total_edge = arms["M2"]["total"]["mae"] < arms["M0"]["total"]["mae"]
    m3_total_edge = arms["M3"]["total"]["mae"] < arms["M1"]["total"]["mae"]
    return {
        "arms": arms,
        "margin_football_incremental_disposition": (
            "DEVELOPMENT_INCREMENTAL_FOOTBALL_SIGNAL"
            if (m2_margin_edge or m3_margin_edge)
            else "NO_INCREMENTAL_FOOTBALL_EDGE"
        ),
        "total_football_incremental_disposition": (
            "DEVELOPMENT_INCREMENTAL_FOOTBALL_SIGNAL"
            if (m2_total_edge or m3_total_edge)
            else "NO_INCREMENTAL_FOOTBALL_EDGE"
        ),
    }


def season_metrics(frame: pd.DataFrame, pred_margin: str, pred_total: str) -> dict:
    out = {}
    for season, part in frame.groupby("season"):
        out[str(int(season))] = {
            "games": int(len(part)),
            "margin": numeric_metrics(part["actual_margin"], part[pred_margin]),
            "total": numeric_metrics(part["actual_total"], part[pred_total]),
        }
    return out


def market_relative(frame: pd.DataFrame, pred_margin: str, pred_total: str) -> dict:
    margin = frame[frame["market_margin"].notna()].copy() if "market_margin" in frame else pd.DataFrame()
    total = frame[frame["market_total"].notna()].copy() if "market_total" in frame else pd.DataFrame()
    out = {}
    if not margin.empty:
        out["margin"] = paired_market_metrics(margin["actual_margin"], margin[pred_margin], margin["market_margin"])
        out["margin_bootstrap"] = season_week_block_bootstrap(
            margin,
            np.abs(margin["actual_margin"] - margin[pred_margin]),
            np.abs(margin["actual_margin"] - margin["market_margin"]),
            samples=10_000,
            seed=26031,
        )
    if not total.empty:
        out["total"] = paired_market_metrics(total["actual_total"], total[pred_total], total["market_total"])
        out["total_bootstrap"] = season_week_block_bootstrap(
            total,
            np.abs(total["actual_total"] - total[pred_total]),
            np.abs(total["actual_total"] - total["market_total"]),
            samples=10_000,
            seed=26032,
        )
    return out


def attach_market(frame: pd.DataFrame, schedules: pd.DataFrame) -> pd.DataFrame:
    market = schedules[[c for c in ("game_id", "spread_line", "total_line") if c in schedules.columns]].drop_duplicates("game_id")
    market["game_id"] = market["game_id"].astype(str)
    out = frame.copy()
    out["game_id"] = out["game_id"].astype(str)
    out = out.merge(market, on="game_id", how="left", validate="many_to_one")
    out["market_margin"] = pd.to_numeric(out["spread_line"], errors="coerce")
    out["market_total"] = pd.to_numeric(out["total_line"], errors="coerce")
    return out


def _bucket_series(values: pd.Series, bins, labels) -> pd.Series:
    return pd.cut(pd.to_numeric(values, errors="coerce"), bins=bins, labels=labels, right=False, include_lowest=True)


def diagnostic_slices(frame: pd.DataFrame, pred_margin: str, pred_total: str) -> pd.DataFrame:
    work = frame.copy()
    rows: list[dict] = []

    def add(dimension: str, bucket: str, part: pd.DataFrame) -> None:
        if part.empty:
            return
        m = numeric_metrics(part["actual_margin"], part[pred_margin])
        t = numeric_metrics(part["actual_total"], part[pred_total])
        rows.append(
            {
                "dimension": dimension,
                "bucket": str(bucket),
                "games": int(len(part)),
                "margin_mae": m["mae"],
                "margin_bias": m["bias_actual_minus_pred"],
                "total_mae": t["mae"],
                "total_bias": t["bias_actual_minus_pred"],
            }
        )

    for season, part in work.groupby("season"):
        add("season", str(int(season)), part)

    week = pd.to_numeric(work["week"], errors="coerce")
    work["season_segment"] = pd.cut(
        week,
        bins=[1, 5, 10, 15, np.inf],
        labels=["weeks_1_4", "weeks_5_9", "weeks_10_14", "weeks_15_plus"],
        right=False,
    )
    for label, part in work.groupby("season_segment", observed=True):
        add("season_segment", str(label), part)

    if "market_margin" in work:
        work["favorite_size"] = _bucket_series(work["market_margin"].abs(), [0, 3, 7, 10, 14, np.inf], ["0-3", "3-7", "7-10", "10-14", "14+"])
        for label, part in work.groupby("favorite_size", observed=True):
            add("favorite_size_abs", str(label), part)
        work["model_market_gap"] = (work[pred_margin] - work["market_margin"]).abs()
        work["disagreement"] = _bucket_series(work["model_market_gap"], [0, 2, 4, 6, 8, np.inf], ["<2", "2-4", "4-6", "6-8", "8+"])
        for label, part in work.groupby("disagreement", observed=True):
            add("model_market_disagreement", str(label), part)

    if "market_total" in work:
        work["market_total_bucket"] = _bucket_series(work["market_total"], [-np.inf, 42, 45, 48, np.inf], ["<42", "42-45", "45-48", "48+"])
        for label, part in work.groupby("market_total_bucket", observed=True):
            add("market_total", str(label), part)

    work["home_away"] = "home_oriented_prediction"
    add("home_away", "home_oriented_prediction", work)
    for threshold in (14, 21, 28):
        add("realized_blowout", f"abs_margin_ge_{threshold}", work[work["actual_margin"].abs() >= threshold])
    return pd.DataFrame(rows)


def build_baselines(schedules: pd.DataFrame, team_states: pd.DataFrame, development_seasons=(2022, 2023, 2024)) -> pd.DataFrame:
    sched = schedules.copy().sort_values(["season", "week", "game_id"])
    rows: list[pd.DataFrame] = []
    home_state = team_states[team_states["home_indicator"].eq(1)].set_index("game_id")
    away_state = team_states[team_states["home_indicator"].eq(0)].set_index("game_id")

    # Simple EPA/team-strength Ridge baseline: no team indicators, no grid search.
    feature_rows = []
    common_state = sorted(set(home_state.index).intersection(away_state.index))
    for gid in common_state:
        h = home_state.loc[gid]
        a = away_state.loc[gid]
        if isinstance(h, pd.DataFrame):
            h = h.iloc[0]
        if isinstance(a, pd.DataFrame):
            a = a.iloc[0]
        feature_rows.append(
            {
                "game_id": str(gid),
                "season": int(h["season"]),
                "week": int(h["week"]),
                "off_epa_diff": float(h.get("off_epa_state", np.nan)) - float(a.get("off_epa_state", np.nan)),
                "def_epa_diff": float(a.get("def_epa_allowed_state", np.nan)) - float(h.get("def_epa_allowed_state", np.nan)),
                "pass_epa_diff": float(h.get("pass_epa_state", np.nan)) - float(a.get("pass_epa_state", np.nan)),
                "success_diff": float(h.get("success_rate_state", np.nan)) - float(a.get("success_rate_state", np.nan)),
                "off_epa_sum": float(h.get("off_epa_state", np.nan)) + float(a.get("off_epa_state", np.nan)),
                "def_epa_sum": float(h.get("def_epa_allowed_state", np.nan)) + float(a.get("def_epa_allowed_state", np.nan)),
                "rest_diff": float(h.get("rest_diff_team", np.nan)),
            }
        )
    f = pd.DataFrame(feature_rows).merge(
        sched[["game_id", "actual_margin", "actual_total"]], on="game_id", how="left"
    )
    margin_features = ["off_epa_diff", "def_epa_diff", "pass_epa_diff", "success_diff", "rest_diff"]
    total_features = ["off_epa_sum", "def_epa_sum"]

    for season in development_seasons:
        target = sched[sched["season"].eq(season)].copy()
        hist = sched[(sched["season"] >= 2016) & (sched["season"] < season) & sched["actual_margin"].notna()].copy()
        target["baseline_hfa_margin"] = float(hist["actual_margin"].mean())
        target["baseline_league_total"] = float(hist["actual_total"].mean())
        target["baseline_market_margin"] = pd.to_numeric(target.get("spread_line"), errors="coerce")
        target["baseline_market_total"] = pd.to_numeric(target.get("total_line"), errors="coerce")

        ids = target["game_id"].astype(str)
        scoring_rows = []
        for gid in ids:
            if gid not in home_state.index or gid not in away_state.index:
                continue
            h = home_state.loc[gid]
            a = away_state.loc[gid]
            if isinstance(h, pd.DataFrame):
                h = h.iloc[0]
            if isinstance(a, pd.DataFrame):
                a = a.iloc[0]
            hp = np.nanmean([float(h.get("points_for_state", np.nan)), float(a.get("points_against_state", np.nan))])
            ap = np.nanmean([float(a.get("points_for_state", np.nan)), float(h.get("points_against_state", np.nan))])
            scoring_rows.append({"game_id": gid, "baseline_scoring_home": hp, "baseline_scoring_away": ap})
        scoring = pd.DataFrame(scoring_rows)
        if not scoring.empty:
            scoring["baseline_scoring_margin"] = scoring["baseline_scoring_home"] - scoring["baseline_scoring_away"]
            scoring["baseline_scoring_total"] = scoring["baseline_scoring_home"] + scoring["baseline_scoring_away"]
            target = target.merge(scoring, on="game_id", how="left")

        trf = f[f["season"] < season].dropna(subset=["actual_margin", "actual_total"])
        vaf = f[f["season"] == season]
        if not trf.empty and not vaf.empty:
            def fit_ridge(features, target_col):
                pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("ridge", Ridge(alpha=10.0))])
                pipe.fit(trf[features], trf[target_col])
                return pipe.predict(vaf[features])
            ep = vaf[["game_id"]].copy()
            ep["baseline_epa_margin"] = fit_ridge(margin_features, "actual_margin")
            ep["baseline_epa_total"] = fit_ridge(total_features, "actual_total")
            target = target.merge(ep, on="game_id", how="left")
        rows.append(target)
    return pd.concat(rows, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)


def baseline_metrics(frame: pd.DataFrame) -> dict:
    specs = {
        "market": ("baseline_market_margin", "baseline_market_total"),
        "naive_hfa_league_total": ("baseline_hfa_margin", "baseline_league_total"),
        "historical_scoring_average": ("baseline_scoring_margin", "baseline_scoring_total"),
        "simple_epa_team_strength": ("baseline_epa_margin", "baseline_epa_total"),
    }
    out = {}
    for name, (mcol, tcol) in specs.items():
        if mcol not in frame or tcol not in frame:
            continue
        out[name] = {
            "margin": numeric_metrics(frame["actual_margin"], frame[mcol]),
            "total": numeric_metrics(frame["actual_total"], frame[tcol]),
            "season_by_season": season_metrics(frame, mcol, tcol),
        }
    return out


def _softmax(z: np.ndarray) -> np.ndarray:
    z = np.asarray(z, dtype=float)
    z = z - np.max(z)
    e = np.exp(z)
    return e / e.sum()


def _fit_convex_weights(pred_matrix: np.ndarray, actual: np.ndarray) -> np.ndarray:
    x = np.asarray(pred_matrix, dtype=float)
    y = np.asarray(actual, dtype=float)
    if x.ndim != 2 or x.shape[0] != len(y):
        raise ValueError("invalid blend training matrix")
    k = x.shape[1]
    def objective(logits):
        w = _softmax(logits)
        return float(np.mean(np.abs(y - x @ w)))
    res = minimize(objective, np.zeros(k), method="BFGS", options={"maxiter": 2000, "gtol": 1e-8})
    return _softmax(res.x if res.success or np.isfinite(res.fun) else np.zeros(k))


def evaluate_d_target(
    a0: pd.DataFrame,
    b0: pd.DataFrame,
    c0: pd.DataFrame,
    *,
    target: str,
    code_sha: str,
    config_sha: str,
) -> tuple[dict, pd.DataFrame | None]:
    if target not in ("margin", "total"):
        raise ValueError("D target must be margin or total")
    actual_col = f"actual_{target}"
    pred_col = "expected_margin" if target == "margin" else "expected_total"
    components = []
    for label, frame in (("A0", a0), ("B0", b0), ("C0", c0)):
        col = pred_col
        keep = frame[["game_id", "season", "week", "home_team", "away_team", actual_col, col]].copy()
        keep = keep.rename(columns={col: f"pred_{label}"})
        components.append(keep)
    common = components[0]
    for part in components[1:]:
        common = common.merge(
            part[["game_id", f"pred_{'B0' if 'pred_B0' in part.columns else 'C0'}"]],
            on="game_id",
            how="inner",
        )
    common = common.sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    labels = ["A0", "B0", "C0"]
    pred_cols = [f"pred_{x}" for x in labels]

    abs_errors = pd.DataFrame({x: np.abs(common[actual_col] - common[f"pred_{x}"]) for x in labels})
    corr = abs_errors.corr(method="pearson")
    pair_corr = {
        f"{labels[i]}_{labels[j]}": float(abs(corr.loc[labels[i], labels[j]]))
        for i in range(len(labels))
        for j in range(i + 1, len(labels))
    }
    corr_pass = any(v < 0.90 for v in pair_corr.values())

    blend_parts = []
    weight_receipts = []
    for season in (2022, 2023, 2024):
        tr = common[common["season"] < season]
        va = common[common["season"] == season]
        if tr.empty or va.empty:
            continue
        w = _fit_convex_weights(tr[pred_cols].to_numpy(float), tr[actual_col].to_numpy(float))
        part = va.copy()
        part["blend_prediction"] = va[pred_cols].to_numpy(float) @ w
        for label, weight in zip(labels, w, strict=False):
            part[f"weight_{label}"] = float(weight)
        blend_parts.append(part)
        weight_receipts.append({"target_season": season, "training_seasons": sorted(int(x) for x in tr["season"].unique()), "weights": {label: float(weight) for label, weight in zip(labels, w, strict=False)}})
    blend = pd.concat(blend_parts, ignore_index=True) if blend_parts else pd.DataFrame()
    dev = common[common["season"].isin([2022, 2023, 2024])].copy()
    dev_blend = blend[blend["season"].isin([2022, 2023, 2024])].copy()

    component_mae = {label: float(np.mean(np.abs(dev[actual_col] - dev[f"pred_{label}"]))) for label in labels}
    best_label = min(component_mae, key=component_mae.get)
    best_mae = component_mae[best_label]
    blend_mae = float(np.mean(np.abs(dev_blend[actual_col] - dev_blend["blend_prediction"])))
    gain = best_mae - blend_mae
    season_comparison = {}
    season_pass = True
    for season in (2023, 2024):
        part = dev_blend[dev_blend["season"] == season]
        blend_s = float(np.mean(np.abs(part[actual_col] - part["blend_prediction"])))
        best_s = float(np.mean(np.abs(part[actual_col] - part[f"pred_{best_label}"])))
        season_comparison[str(season)] = {"blend_mae": blend_s, "best_constituent_mae": best_s, "improvement": best_s - blend_s}
        season_pass = season_pass and (blend_s < best_s)

    bootstrap = season_week_block_bootstrap(
        dev_blend,
        np.abs(dev_blend[actual_col] - dev_blend["blend_prediction"]),
        np.abs(dev_blend[actual_col] - dev_blend[f"pred_{best_label}"]),
        samples=10_000,
        seed=26040 if target == "margin" else 26041,
    )
    eligible = bool(
        corr_pass
        and gain >= 0.10
        and season_pass
        and bootstrap.get("probability_candidate_lower", 0.0) >= 0.75
    )
    receipt = {
        "target": target,
        "contract": d_gate_contract(),
        "abs_error_correlations": pair_corr,
        "correlation_gate_pass": corr_pass,
        "component_pooled_mae": component_mae,
        "best_constituent": best_label,
        "best_constituent_mae": best_mae,
        "nested_blend_mae": blend_mae,
        "pooled_mae_gain": gain,
        "season_comparison": season_comparison,
        "season_gate_pass": season_pass,
        "bootstrap": bootstrap,
        "weight_receipts": weight_receipts,
        "disposition": "ELIGIBLE" if eligible else "ENSEMBLE_NOT_ELIGIBLE",
    }
    if not eligible:
        return receipt, None

    d_id = D_MARGIN_ID if target == "margin" else D_TOTAL_ID
    out = dev_blend[["game_id", "season", "week", "home_team", "away_team", actual_col, "blend_prediction"] + [f"pred_{x}" for x in labels] + [f"weight_{x}" for x in labels]].copy()
    out["candidate_id"] = d_id
    out["outer_target_season"] = out["season"].astype(int)
    out["train_through_season"] = out["season"].astype(int) - 1
    out["training_through_boundary"] = out["train_through_season"].astype(str) + "-REG-END"
    out["source_contract_version"] = SOURCE_CONTRACT_VERSION
    out["code_sha"] = str(code_sha)
    out["config_sha"] = str(config_sha)
    out["fallback_state"] = "NONE"
    return receipt, out
