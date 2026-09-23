from __future__ import annotations

"""Phase 5 F-ST-anchored residual stack.

Research-only implementation of LEVLINE-HISTORICAL-RESIDUAL-STACK-V1.
The scientific contract is frozen in the sibling CANDIDATE5_* documents.
"""

import argparse
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import binomtest

from nfl_forecast.challenger_stacking import build_chronological_logit_stack

ROOT = Path(__file__).resolve().parents[3]
PHASE5_DIR = ROOT / "research" / "spread-points-nextgen" / "phase5"
OOF_PATH = ROOT / "research" / "spread-points-nextgen" / "phase3" / "evidence" / "FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv"
A0_2025_PATH = ROOT / "research" / "spread-points-nextgen" / "phase4" / "A0_HOLDOUT_2025.csv"
B0_2025_PATH = ROOT / "research" / "spread-points-nextgen" / "phase4" / "B0_HOLDOUT_2025.csv"
C0_2025_PATH = ROOT / "research" / "spread-points-nextgen" / "phase4" / "C0_HOLDOUT_2025.csv"
FST_SOURCE = ROOT / "challenger_outputs" / "fst" / "provenance" / "training_frame_keyed.csv"
CONFIG_PATH = PHASE5_DIR / "candidate5_config.json"
FREEZE_RECEIPT = PHASE5_DIR / "CANDIDATE5_FREEZE_RECEIPT.json"

CANDIDATE_ID = "LEVLINE-HISTORICAL-RESIDUAL-STACK-V1"
A0_ID = "A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1"
B0_ID = "B0-POSSESSION-DRIVE-SCORE-PROCESS-V1"
C0_ID = "C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1"
FST_ID = "F-ST-01-FROZEN-2026"
FROZEN_CODE_SHA = "5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579"
FROZEN_CONFIG_SHA = "2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543"
MARKET_HORIZON = "historical_closing_late_benchmark_exact_horizon_opaque"
PREREG_SHA = "df14e51d73aad96899d3ba4364cbb76989f0d2bf"

A0_FEATURES = [
    "a0_logit_delta",
    "a0_expected_margin",
    "a0_score_uncertainty",
    "a0_offense_strength_diff",
    "a0_defense_strength_diff",
]
B0_FEATURES = [
    "b0_logit_delta",
    "b0_expected_margin",
    "b0_expected_total",
    "b0_margin_sd",
    "b0_total_sd",
]
UNION_FEATURES = A0_FEATURES + B0_FEATURES
PRIMARY_FEATURES = UNION_FEATURES + [
    "fst_confidence",
    "a0_b0_logit_gap",
    "component_prob_dispersion",
]
MARKET_FEATURES = PRIMARY_FEATURES + [
    "market_logit_delta",
    "c0_market_margin",
    "c0_predicted_margin_residual",
    "c0_market_total",
    "c0_predicted_total_residual",
]
ARM_FEATURES = {
    "FST_PLUS_A0": A0_FEATURES,
    "FST_PLUS_B0": B0_FEATURES,
    "FST_PLUS_A0_PLUS_B0": UNION_FEATURES,
    "PRIMARY_COMPACT_FOOTBALL": PRIMARY_FEATURES,
    "MARKET_AWARE_DIAGNOSTIC": MARKET_FEATURES,
}
MODELED_ARMS = tuple(ARM_FEATURES)
EPS = 1e-6


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _logit(values: Iterable[float] | np.ndarray | pd.Series) -> np.ndarray:
    p = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def _sigmoid(values: Iterable[float] | np.ndarray | float) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    out = np.empty_like(x, dtype=float)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    ex = np.exp(x[~pos])
    out[~pos] = ex / (1.0 + ex)
    return out


def _log_loss(prob: Iterable[float], y: Iterable[int]) -> float:
    p = np.clip(np.asarray(prob, dtype=float), EPS, 1.0 - EPS)
    target = np.asarray(y, dtype=float)
    return float(np.mean(-(target * np.log(p) + (1.0 - target) * np.log(1.0 - p))))


def _parse_game_id(game_id: str) -> tuple[int, int, str, str]:
    parts = str(game_id).split("_")
    if len(parts) != 4:
        raise ValueError(f"unexpected game_id: {game_id!r}")
    season, week, away, home = parts
    return int(season), int(week), away, home


def _strict_pick(prob: Iterable[float]) -> np.ndarray:
    return (np.asarray(prob, dtype=float) > 0.5).astype(int)


def load_config() -> dict:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert cfg["candidate_id"] == CANDIDATE_ID
    assert cfg["preregistration_commit_sha"] == PREREG_SHA
    assert cfg["lambda_grid"] == [0.1, 1.0, 10.0, 100.0]
    assert cfg["winner_rule"] == "probability_strictly_greater_than_0.5"
    return cfg


def validate_freeze_receipt() -> dict:
    receipt = json.loads(FREEZE_RECEIPT.read_text(encoding="utf-8"))
    if receipt["preregistration_commit_sha"] != PREREG_SHA:
        raise RuntimeError("Candidate 5 preregistration SHA drift")
    if receipt["candidate5_specific_results_inspected_before_freeze"] is not False:
        raise RuntimeError("invalid Candidate 5 result chronology")
    if receipt["completed_2026_outcomes_used_for_design_selection_or_evaluation"] is not False:
        raise RuntimeError("completed-2026 firewall receipt failed")
    if receipt["production_changed"] is not False:
        raise RuntimeError("production firewall receipt failed")
    return receipt


def load_fst_history() -> pd.DataFrame:
    source = pd.read_csv(FST_SOURCE)
    required = {"game_id", "season", "home_win", "market_prob", "pure_prob"}
    missing = required - set(source.columns)
    if missing:
        raise ValueError(f"F-ST provenance frame missing {sorted(missing)}")
    if source["game_id"].astype(str).duplicated().any():
        raise ValueError("F-ST provenance frame contains duplicate game_id")
    seasons = pd.to_numeric(source["season"], errors="raise").astype(int)
    if int(seasons.max()) > 2025:
        raise RuntimeError("Candidate 5 F-ST history may not load outcomes after 2025")

    stack = build_chronological_logit_stack(
        source, target_seasons=(2022, 2023, 2024, 2025)
    )
    pred = stack.predictions.copy()
    idx = pred.index
    pred["game_id"] = source.loc[idx, "game_id"].astype(str).to_numpy()
    pred["market_prob"] = pd.to_numeric(source.loc[idx, "market_prob"], errors="raise").to_numpy()
    parsed = pred["game_id"].map(_parse_game_id)
    pred["season_num"] = [x[0] for x in parsed]
    pred["week"] = [x[1] for x in parsed]
    pred["away_team"] = [x[2] for x in parsed]
    pred["home_team"] = [x[3] for x in parsed]
    pred["home_win"] = pd.to_numeric(pred["home_win"], errors="raise").astype(int)
    pred["fst_prob"] = pd.to_numeric(pred["stack_probability"], errors="raise")
    pred = pred[
        [
            "game_id",
            "season_num",
            "week",
            "home_team",
            "away_team",
            "home_win",
            "fst_prob",
            "market_prob",
        ]
    ].rename(columns={"season_num": "season"})
    pred = pred.sort_values(["season", "week", "game_id"], kind="stable").reset_index(drop=True)

    if len(pred) != 1087:
        raise RuntimeError(f"F-ST reproduction row drift: {len(pred)} != 1087")
    fst_correct = int((_strict_pick(pred["fst_prob"]) == pred["home_win"].to_numpy()).sum())
    if fst_correct != 741:
        raise RuntimeError(f"F-ST reproduction accuracy drift: {fst_correct} != 741")
    return pred


def _assert_component_identity(frame: pd.DataFrame, prefix: str, candidate_id: str) -> None:
    cid = f"{prefix}_candidate_id"
    code = f"{prefix}_code_sha"
    config = f"{prefix}_config_sha"
    train = f"{prefix}_train_through_season"
    for col in (cid, code, config, train):
        if col not in frame:
            raise ValueError(f"missing frozen provenance column {col}")
    if not frame[cid].astype(str).eq(candidate_id).all():
        raise RuntimeError(f"{prefix} candidate identity drift")
    if not frame[code].astype(str).eq(FROZEN_CODE_SHA).all():
        raise RuntimeError(f"{prefix} code identity drift")
    if not frame[config].astype(str).eq(FROZEN_CONFIG_SHA).all():
        raise RuntimeError(f"{prefix} config identity drift")
    if not (
        pd.to_numeric(frame[train], errors="raise").astype(int)
        < pd.to_numeric(frame["season"], errors="raise").astype(int)
    ).all():
        raise RuntimeError(f"{prefix} OOF chronology breach")


def _merge_with_fst(components: pd.DataFrame, fst: pd.DataFrame) -> pd.DataFrame:
    left = components.copy()
    right = fst.rename(
        columns={
            "season": "fst_season",
            "week": "fst_week",
            "home_team": "fst_home_team",
            "away_team": "fst_away_team",
        }
    )
    merged = left.merge(right, on="game_id", how="inner", validate="one_to_one")
    if len(merged) != len(left):
        raise RuntimeError(
            f"component/F-ST exact-pair mismatch: components={len(left)} paired={len(merged)}"
        )
    checks = [
        ("season", "fst_season"),
        ("week", "fst_week"),
        ("home_team", "fst_home_team"),
        ("away_team", "fst_away_team"),
    ]
    for a, b in checks:
        if not merged[a].astype(str).eq(merged[b].astype(str)).all():
            raise RuntimeError(f"game identity mismatch: {a} != {b}")
    return merged.drop(columns=[b for _, b in checks])


def load_development_surface(fst: pd.DataFrame) -> pd.DataFrame:
    oof = pd.read_csv(OOF_PATH)
    if len(oof) != 815:
        raise RuntimeError(f"preserved Candidate 5 OOF row drift: {len(oof)} != 815")
    if oof["game_id"].astype(str).duplicated().any():
        raise ValueError("preserved OOF surface contains duplicate game_id")
    if not oof["oof_provenance_assertion"].astype(bool).all():
        raise RuntimeError("base OOF provenance assertion failed")
    if sorted(pd.to_numeric(oof["season"], errors="raise").astype(int).unique().tolist()) != [
        2022,
        2023,
        2024,
    ]:
        raise RuntimeError("development surface season boundary drift")
    _assert_component_identity(oof, "a0", A0_ID)
    _assert_component_identity(oof, "b0", B0_ID)
    _assert_component_identity(oof, "c0", C0_ID)
    if not oof["c0_market_horizon_label"].astype(str).eq(MARKET_HORIZON).all():
        raise RuntimeError("C0 historical market horizon label drift")
    dev_fst = fst[fst["season"].between(2022, 2024)].copy()
    return derive_features(_merge_with_fst(oof, dev_fst))


def load_2025_surface(fst: pd.DataFrame) -> pd.DataFrame:
    a = pd.read_csv(A0_2025_PATH)
    b = pd.read_csv(B0_2025_PATH)
    c = pd.read_csv(C0_2025_PATH)
    for name, frame in (("A0", a), ("B0", b), ("C0", c)):
        if len(frame) != 272:
            raise RuntimeError(f"{name} 2025 row drift: {len(frame)} != 272")
        if frame["game_id"].astype(str).duplicated().any():
            raise RuntimeError(f"{name} 2025 duplicate game_id")

    def base_checks(frame: pd.DataFrame, cid: str) -> None:
        if not frame["candidate_id"].astype(str).eq(cid).all():
            raise RuntimeError(f"{cid} 2025 candidate identity drift")
        if not frame["code_sha"].astype(str).eq(FROZEN_CODE_SHA).all():
            raise RuntimeError(f"{cid} 2025 code identity drift")
        if not frame["config_sha"].astype(str).eq(FROZEN_CONFIG_SHA).all():
            raise RuntimeError(f"{cid} 2025 config identity drift")
        if not pd.to_numeric(frame["train_through_season"], errors="raise").astype(int).eq(2024).all():
            raise RuntimeError(f"{cid} 2025 train-through drift")

    base_checks(a, A0_ID)
    base_checks(b, B0_ID)
    base_checks(c, C0_ID)
    if not c["market_horizon_label"].astype(str).eq(MARKET_HORIZON).all():
        raise RuntimeError("2025 C0 market horizon drift")

    a_keep = a[
        [
            "game_id",
            "season",
            "week",
            "home_team",
            "away_team",
            "home_win_probability",
            "expected_margin",
            "expected_total",
            "score_uncertainty",
            "offense_strength_diff",
            "defense_strength_diff",
        ]
    ].rename(
        columns={
            "home_win_probability": "a0_home_win_probability",
            "expected_margin": "a0_expected_margin",
            "expected_total": "a0_expected_total",
            "score_uncertainty": "a0_score_uncertainty",
            "offense_strength_diff": "a0_offense_strength_diff",
            "defense_strength_diff": "a0_defense_strength_diff",
        }
    )
    b_keep = b[
        [
            "game_id",
            "home_win_probability",
            "expected_margin",
            "expected_total",
            "margin_variance",
            "total_variance",
        ]
    ].rename(
        columns={
            "home_win_probability": "b0_home_win_probability",
            "expected_margin": "b0_expected_margin",
            "expected_total": "b0_expected_total",
            "margin_variance": "b0_margin_variance",
            "total_variance": "b0_total_variance",
        }
    )
    c_keep = c[
        [
            "game_id",
            "market_margin",
            "market_total",
            "predicted_margin_residual",
            "predicted_total_residual",
            "market_horizon_label",
        ]
    ].rename(
        columns={
            "market_margin": "c0_market_margin",
            "market_total": "c0_market_total",
            "predicted_margin_residual": "c0_predicted_margin_residual",
            "predicted_total_residual": "c0_predicted_total_residual",
            "market_horizon_label": "c0_market_horizon_label",
        }
    )
    comp = a_keep.merge(b_keep, on="game_id", validate="one_to_one").merge(
        c_keep, on="game_id", validate="one_to_one"
    )
    surface = _merge_with_fst(comp, fst[fst["season"].eq(2025)].copy())
    if not surface["c0_market_horizon_label"].astype(str).eq(MARKET_HORIZON).all():
        raise RuntimeError("2025 market horizon label lost during assembly")
    return derive_features(surface)


def derive_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    numeric = [
        "fst_prob",
        "market_prob",
        "a0_home_win_probability",
        "a0_expected_margin",
        "a0_score_uncertainty",
        "a0_offense_strength_diff",
        "a0_defense_strength_diff",
        "b0_home_win_probability",
        "b0_expected_margin",
        "b0_expected_total",
        "b0_margin_variance",
        "b0_total_variance",
        "c0_market_margin",
        "c0_market_total",
        "c0_predicted_margin_residual",
        "c0_predicted_total_residual",
    ]
    for col in numeric:
        if col not in out:
            raise ValueError(f"Candidate 5 surface missing {col}")
        out[col] = pd.to_numeric(out[col], errors="raise")
    if (out["b0_margin_variance"] < 0).any() or (out["b0_total_variance"] < 0).any():
        raise RuntimeError("negative B0 variance")
    out["a0_logit_delta"] = _logit(out["a0_home_win_probability"]) - _logit(out["fst_prob"])
    out["b0_logit_delta"] = _logit(out["b0_home_win_probability"]) - _logit(out["fst_prob"])
    out["b0_margin_sd"] = np.sqrt(out["b0_margin_variance"])
    out["b0_total_sd"] = np.sqrt(out["b0_total_variance"])
    out["fst_confidence"] = np.abs(out["fst_prob"] - 0.5)
    out["a0_b0_logit_gap"] = _logit(out["a0_home_win_probability"]) - _logit(
        out["b0_home_win_probability"]
    )
    probs = out[["fst_prob", "a0_home_win_probability", "b0_home_win_probability"]].to_numpy(float)
    out["component_prob_dispersion"] = np.std(probs, axis=1, ddof=0)
    out["market_logit_delta"] = _logit(out["market_prob"]) - _logit(out["fst_prob"])

    required = sorted(set(MARKET_FEATURES + ["home_win", "season", "week"]))
    values = out[required].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(values.to_numpy(float)).all():
        raise RuntimeError("non-finite Candidate 5 required feature/target")
    return out.sort_values(["season", "week", "game_id"], kind="stable").reset_index(drop=True)


def _fit_offset(train: pd.DataFrame, features: list[str], lam: float, min_rows: int) -> dict:
    if len(train) < min_rows:
        raise RuntimeError(f"insufficient meta-training rows: {len(train)} < {min_rows}")
    y = train["home_win"].to_numpy(int)
    if np.unique(y).size != 2:
        raise RuntimeError("meta-training target lacks both classes")
    x = train[features].to_numpy(float)
    offset = _logit(train["fst_prob"])
    mean = x.mean(axis=0)
    std = x.std(axis=0, ddof=0)
    zero = (~np.isfinite(std)) | (std < 1e-12)
    safe_std = std.copy()
    safe_std[zero] = 1.0
    z = (x - mean) / safe_std
    if zero.any():
        z[:, zero] = 0.0

    def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
        eta = offset + z @ beta
        prob = _sigmoid(eta)
        loss = float(np.mean(np.logaddexp(0.0, eta) - y * eta) + 0.5 * lam * np.dot(beta, beta))
        grad = (z.T @ (prob - y)) / len(y) + lam * beta
        return loss, grad

    result = minimize(
        fun=lambda beta: objective(beta)[0],
        x0=np.zeros(len(features), dtype=float),
        jac=lambda beta: objective(beta)[1],
        method="L-BFGS-B",
        options={"maxiter": 5000, "ftol": 1e-12, "gtol": 1e-8},
    )
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f"offset logistic convergence failure: {result.message}")
    return {
        "lambda": float(lam),
        "features": list(features),
        "beta": result.x.astype(float),
        "mean": mean.astype(float),
        "std": safe_std.astype(float),
        "zero_variance": zero.astype(bool),
        "training_games": int(len(train)),
        "training_seasons": sorted(train["season"].astype(int).unique().tolist()),
        "optimizer_message": str(result.message),
    }


def _predict_offset(model: dict, frame: pd.DataFrame) -> np.ndarray:
    x = frame[model["features"]].to_numpy(float)
    z = (x - model["mean"]) / model["std"]
    if np.any(model["zero_variance"]):
        z[:, model["zero_variance"]] = 0.0
    eta = _logit(frame["fst_prob"]) + z @ model["beta"]
    return np.clip(_sigmoid(eta), EPS, 1.0 - EPS)


def _serializable_model(model: dict) -> dict:
    return {
        "lambda": model["lambda"],
        "features": model["features"],
        "beta": model["beta"].tolist(),
        "mean": model["mean"].tolist(),
        "std": model["std"].tolist(),
        "zero_variance": model["zero_variance"].astype(bool).tolist(),
        "training_games": model["training_games"],
        "training_seasons": model["training_seasons"],
        "optimizer_message": model["optimizer_message"],
    }


def choose_lambda(dev: pd.DataFrame, features: list[str], validation_seasons: list[int], cfg: dict) -> tuple[float, list[dict]]:
    scores: list[dict] = []
    for lam in cfg["lambda_grid"]:
        probabilities: list[np.ndarray] = []
        outcomes: list[np.ndarray] = []
        fold_rows: list[dict] = []
        for season in validation_seasons:
            train = dev[dev["season"].astype(int) < int(season)].copy()
            val = dev[dev["season"].astype(int) == int(season)].copy()
            if val.empty:
                raise RuntimeError(f"lambda validation season {season} missing")
            model = _fit_offset(train, features, float(lam), cfg["minimum_meta_training_rows"])
            prob = _predict_offset(model, val)
            probabilities.append(prob)
            outcomes.append(val["home_win"].to_numpy(int))
            fold_rows.append(
                {
                    "validation_season": int(season),
                    "training_seasons": model["training_seasons"],
                    "training_games": model["training_games"],
                }
            )
        score = _log_loss(np.concatenate(probabilities), np.concatenate(outcomes))
        scores.append({"lambda": float(lam), "log_loss": score, "folds": fold_rows})

    best_loss = min(row["log_loss"] for row in scores)
    tol = float(cfg["lambda_tie_tolerance_log_loss"])
    eligible = [row for row in scores if row["log_loss"] <= best_loss + tol]
    selected = max(row["lambda"] for row in eligible)
    return float(selected), scores


def development_predictions(dev: pd.DataFrame, arm: str, cfg: dict) -> tuple[pd.Series, list[dict], list[dict]]:
    features = ARM_FEATURES[arm]
    pred = pd.Series(np.nan, index=dev.index, dtype=float)
    fits: list[dict] = []
    tuning: list[dict] = []
    for target in (2022, 2023, 2024):
        test = dev[dev["season"].astype(int) == target]
        if target == 2022:
            pred.loc[test.index] = test["fst_prob"].to_numpy(float)
            fits.append(
                {
                    "arm": arm,
                    "target_season": target,
                    "fallback": True,
                    "reason": "NO_PRIOR_CANDIDATE5_META_TRAINING_SURFACE",
                    "selected_lambda": None,
                    "training_seasons": [],
                    "tuning_seasons": [],
                }
            )
            continue

        train = dev[dev["season"].astype(int) < target].copy()
        if target == 2023:
            lam = float(cfg["default_lambda"])
            tuning_seasons: list[int] = []
        else:
            lam, tune_rows = choose_lambda(dev, features, [2023], cfg)
            tuning_seasons = [2023]
            tuning.append(
                {
                    "arm": arm,
                    "target_season": target,
                    "selected_lambda": lam,
                    "validation_seasons": tuning_seasons,
                    "grid": tune_rows,
                }
            )
        model = _fit_offset(train, features, lam, cfg["minimum_meta_training_rows"])
        if max(model["training_seasons"]) >= target:
            raise RuntimeError("future-season meta-training leakage detected")
        pred.loc[test.index] = _predict_offset(model, test)
        fits.append(
            {
                "arm": arm,
                "target_season": target,
                "fallback": False,
                "selected_lambda": lam,
                "training_seasons": model["training_seasons"],
                "tuning_seasons": tuning_seasons,
                "model": _serializable_model(model),
            }
        )
    if pred.isna().any():
        raise RuntimeError(f"{arm} development predictions incomplete")
    return pred, fits, tuning


def diagnostic_2025_prediction(dev: pd.DataFrame, test: pd.DataFrame, arm: str, cfg: dict) -> tuple[np.ndarray, dict, dict]:
    features = ARM_FEATURES[arm]
    lam, grid = choose_lambda(dev, features, [2023, 2024], cfg)
    model = _fit_offset(dev, features, lam, cfg["minimum_meta_training_rows"])
    if max(model["training_seasons"]) >= 2025:
        raise RuntimeError("2025 diagnostic meta-training leakage")
    prediction = _predict_offset(model, test)
    tuning = {
        "arm": arm,
        "target_season": 2025,
        "label": "POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC",
        "selected_lambda": lam,
        "validation_seasons": [2023, 2024],
        "grid": grid,
    }
    fit = {
        "arm": arm,
        "target_season": 2025,
        "fallback": False,
        "selected_lambda": lam,
        "training_seasons": model["training_seasons"],
        "tuning_seasons": [2023, 2024],
        "model": _serializable_model(model),
    }
    return prediction, fit, tuning


def calibration_stats(prob: Iterable[float], y: Iterable[int]) -> dict:
    p = np.clip(np.asarray(prob, dtype=float), EPS, 1.0 - EPS)
    target = np.asarray(y, dtype=int)
    x = _logit(p)

    def objective(theta: np.ndarray) -> tuple[float, np.ndarray]:
        eta = theta[0] + theta[1] * x
        q = _sigmoid(eta)
        loss = float(np.sum(np.logaddexp(0.0, eta) - target * eta))
        grad = np.array([np.sum(q - target), np.sum((q - target) * x)], dtype=float)
        return loss, grad

    fit = minimize(
        fun=lambda t: objective(t)[0],
        x0=np.array([0.0, 1.0]),
        jac=lambda t: objective(t)[1],
        method="BFGS",
        options={"maxiter": 5000, "gtol": 1e-8},
    )
    if not np.isfinite(fit.x).all():
        return {"intercept": None, "slope": None, "converged": False}
    return {
        "intercept": float(fit.x[0]),
        "slope": float(fit.x[1]),
        "converged": bool(fit.success),
    }


def reliability_rows(prob: Iterable[float], y: Iterable[int], arm: str, sample: str) -> list[dict]:
    p = np.asarray(prob, dtype=float)
    target = np.asarray(y, dtype=int)
    bins = np.linspace(0.0, 1.0, 11)
    ids = np.minimum(np.searchsorted(bins, p, side="right") - 1, 9)
    ids = np.maximum(ids, 0)
    rows: list[dict] = []
    for i in range(10):
        mask = ids == i
        rows.append(
            {
                "sample": sample,
                "arm": arm,
                "bin": i,
                "lower": float(bins[i]),
                "upper": float(bins[i + 1]),
                "games": int(mask.sum()),
                "mean_probability": float(p[mask].mean()) if mask.any() else None,
                "home_win_rate": float(target[mask].mean()) if mask.any() else None,
            }
        )
    return rows


def evaluate_probs(frame: pd.DataFrame, candidate_prob: Iterable[float]) -> dict:
    cand = np.asarray(candidate_prob, dtype=float)
    ref = frame["fst_prob"].to_numpy(float)
    y = frame["home_win"].to_numpy(int)
    cand_pick = _strict_pick(cand)
    ref_pick = _strict_pick(ref)
    cand_correct = cand_pick == y
    ref_correct = ref_pick == y
    changed = cand_pick != ref_pick
    candidate_only = int(np.sum(changed & cand_correct & ~ref_correct))
    fst_only = int(np.sum(changed & ref_correct & ~cand_correct))
    switches = int(changed.sum())
    change_rate = float(changed.mean())
    changed_acc = float(candidate_only / switches) if switches else None
    cand_acc = float(cand_correct.mean())
    fst_acc = float(ref_correct.mean())
    delta = cand_acc - fst_acc
    if switches:
        mechanism = change_rate * (2.0 * changed_acc - 1.0)
        if abs(delta - mechanism) > 1e-12:
            raise RuntimeError(f"winner-change identity failed: delta={delta} mechanism={mechanism}")
        mcnemar = float(binomtest(candidate_only, switches, 0.5).pvalue)
    else:
        mechanism = 0.0
        if abs(delta) > 1e-12:
            raise RuntimeError("zero-switch candidate changed accuracy")
        mcnemar = None

    cand_brier = float(np.mean((cand - y) ** 2))
    fst_brier = float(np.mean((ref - y) ** 2))
    cand_log = _log_loss(cand, y)
    fst_log = _log_loss(ref, y)
    return {
        "games": int(len(frame)),
        "candidate_correct": int(cand_correct.sum()),
        "fst_correct": int(ref_correct.sum()),
        "candidate_only_correct": candidate_only,
        "fst_only_correct": fst_only,
        "accuracy": cand_acc,
        "fst_accuracy": fst_acc,
        "accuracy_delta": delta,
        "accuracy_delta_pp": 100.0 * delta,
        "changed_winners": switches,
        "changed_winner_rate": change_rate,
        "changed_winner_accuracy": changed_acc,
        "mechanism_identity_delta": mechanism,
        "mcnemar_exact_two_sided_p": mcnemar,
        "brier": cand_brier,
        "fst_brier": fst_brier,
        "brier_delta": cand_brier - fst_brier,
        "log_loss": cand_log,
        "fst_log_loss": fst_log,
        "log_loss_delta": cand_log - fst_log,
        "calibration": calibration_stats(cand, y),
        "fst_calibration": calibration_stats(ref, y),
    }


def block_bootstrap(frame: pd.DataFrame, candidate_prob: Iterable[float], samples: int, seed: int) -> dict:
    cand = np.asarray(candidate_prob, dtype=float)
    ref = frame["fst_prob"].to_numpy(float)
    y = frame["home_win"].to_numpy(int)
    block = frame["season"].astype(str) + "-W" + frame["week"].astype(str)
    codes, uniques = pd.factorize(block, sort=True)
    n_blocks = len(uniques)

    cand_acc_row = (_strict_pick(cand) == y).astype(float)
    ref_acc_row = (_strict_pick(ref) == y).astype(float)
    brier_diff = (cand - y) ** 2 - (ref - y) ** 2
    cand_clip = np.clip(cand, EPS, 1 - EPS)
    ref_clip = np.clip(ref, EPS, 1 - EPS)
    cand_ll = -(y * np.log(cand_clip) + (1 - y) * np.log(1 - cand_clip))
    ref_ll = -(y * np.log(ref_clip) + (1 - y) * np.log(1 - ref_clip))
    log_diff = cand_ll - ref_ll

    arrays = {}
    for name, row in {
        "candidate_accuracy": cand_acc_row,
        "accuracy_delta": cand_acc_row - ref_acc_row,
        "brier_delta": brier_diff,
        "log_loss_delta": log_diff,
    }.items():
        sums = np.bincount(codes, weights=row, minlength=n_blocks).astype(float)
        arrays[name] = sums
    counts = np.bincount(codes, minlength=n_blocks).astype(float)

    rng = np.random.default_rng(seed)
    draws = {name: np.empty(samples, dtype=float) for name in arrays}
    for i in range(samples):
        chosen = rng.integers(0, n_blocks, size=n_blocks)
        denom = float(counts[chosen].sum())
        for name, sums in arrays.items():
            draws[name][i] = float(sums[chosen].sum() / denom)

    return {
        "blocks": n_blocks,
        "samples": int(samples),
        "seed": int(seed),
        "intervals": {
            name: {
                "p2_5": float(np.quantile(values, 0.025)),
                "median": float(np.quantile(values, 0.5)),
                "p97_5": float(np.quantile(values, 0.975)),
            }
            for name, values in draws.items()
        },
    }


def _group_metric_rows(frame: pd.DataFrame, candidate_prob: np.ndarray, grouping: pd.Series, slice_type: str) -> list[dict]:
    rows: list[dict] = []
    for value in pd.unique(grouping):
        mask = grouping == value
        if not bool(mask.any()):
            continue
        metrics = evaluate_probs(frame.loc[mask].reset_index(drop=True), candidate_prob[mask.to_numpy()])
        rows.append(
            {
                "slice_type": slice_type,
                "slice_value": str(value),
                "games": metrics["games"],
                "accuracy": metrics["accuracy"],
                "fst_accuracy": metrics["fst_accuracy"],
                "accuracy_delta_pp": metrics["accuracy_delta_pp"],
                "changed_winners": metrics["changed_winners"],
                "changed_winner_accuracy": metrics["changed_winner_accuracy"],
                "candidate_only_correct": metrics["candidate_only_correct"],
                "fst_only_correct": metrics["fst_only_correct"],
            }
        )
    return rows


def diagnostic_slices(frame: pd.DataFrame, candidate_prob: Iterable[float]) -> pd.DataFrame:
    cand = np.asarray(candidate_prob, dtype=float)
    rows: list[dict] = []
    rows += _group_metric_rows(frame, cand, frame["season"].astype(int), "season")
    week_key = frame["season"].astype(str) + "-W" + frame["week"].astype(int).astype(str)
    rows += _group_metric_rows(frame, cand, week_key, "season_week")

    conf_bins = pd.cut(
        frame["fst_confidence"],
        bins=[-np.inf, 0.05, 0.10, 0.20, np.inf],
        labels=["<0.05", "0.05-0.10", "0.10-0.20", "0.20+"],
        right=False,
    )
    rows += _group_metric_rows(frame, cand, conf_bins.astype(str), "fst_confidence")

    disp_bins = pd.cut(
        frame["component_prob_dispersion"],
        bins=[-np.inf, 0.025, 0.05, 0.10, np.inf],
        labels=["<0.025", "0.025-0.05", "0.05-0.10", "0.10+"],
        right=False,
    )
    rows += _group_metric_rows(frame, cand, disp_bins.astype(str), "component_disagreement")

    market_conf = np.abs(frame["market_prob"] - 0.5)
    market_bins = pd.cut(
        market_conf,
        bins=[-np.inf, 0.05, 0.10, 0.20, np.inf],
        labels=["<0.05", "0.05-0.10", "0.10-0.20", "0.20+"],
        right=False,
    )
    rows += _group_metric_rows(frame, cand, market_bins.astype(str), "late_market_favorite_confidence_descriptive")

    ref_pick = _strict_pick(frame["fst_prob"])
    cand_pick = _strict_pick(cand)
    y = frame["home_win"].to_numpy(int)
    changed = cand_pick != ref_pick
    cand_correct = cand_pick == y
    ref_correct = ref_pick == y
    team_rows = []
    for i, rec in frame.reset_index(drop=True).iterrows():
        for team in (str(rec["home_team"]), str(rec["away_team"])):
            team_rows.append(
                {
                    "team": team,
                    "changed": bool(changed[i]),
                    "candidate_only": bool(changed[i] and cand_correct[i] and not ref_correct[i]),
                    "fst_only": bool(changed[i] and ref_correct[i] and not cand_correct[i]),
                }
            )
    team_df = pd.DataFrame(team_rows)
    for team, part in team_df.groupby("team", sort=True):
        switches = int(part["changed"].sum())
        c_only = int(part["candidate_only"].sum())
        f_only = int(part["fst_only"].sum())
        rows.append(
            {
                "slice_type": "team_concentration",
                "slice_value": team,
                "games": int(len(part)),
                "accuracy": None,
                "fst_accuracy": None,
                "accuracy_delta_pp": None,
                "changed_winners": switches,
                "changed_winner_accuracy": float(c_only / switches) if switches else None,
                "candidate_only_correct": c_only,
                "fst_only_correct": f_only,
            }
        )
    return pd.DataFrame(rows)


def baseline_metrics(frame: pd.DataFrame, probability_col: str, name: str, sample: str) -> dict:
    y = frame["home_win"].to_numpy(int)
    p = np.clip(frame[probability_col].to_numpy(float), EPS, 1 - EPS)
    picks = _strict_pick(p)
    cal = calibration_stats(p, y)
    return {
        "sample": sample,
        "arm": name,
        "games": int(len(frame)),
        "correct": int((picks == y).sum()),
        "accuracy": float((picks == y).mean()),
        "brier": float(np.mean((p - y) ** 2)),
        "log_loss": _log_loss(p, y),
        "calibration_intercept": cal["intercept"],
        "calibration_slope": cal["slope"],
    }


def classification(primary: dict) -> str:
    switches = int(primary["changed_winners"])
    changed_acc = primary["changed_winner_accuracy"]
    if primary["accuracy_delta"] <= 0:
        return "REJECTED"
    if switches and (changed_acc is None or changed_acc <= 0.5):
        return "REJECTED"
    if primary["brier_delta"] <= 0 and primary["log_loss_delta"] <= 0:
        return "ELIGIBLE_FOR_PROSPECTIVE_PHASE6_SHADOW_VALIDATION"
    return "INCONCLUSIVE_BUT_COHERENT"


def _fmt(value, digits=4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float) and not isfinite(value):
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_markdown_reports(out: Path, dev_metrics: dict[str, dict], diag_metrics: dict[str, dict], bootstrap: dict, calibration_rows: list[dict], disposition: str) -> None:
    order = [
        "FST",
        "FST_PLUS_A0",
        "FST_PLUS_B0",
        "FST_PLUS_A0_PLUS_B0",
        "PRIMARY_COMPACT_FOOTBALL",
        "MARKET_AWARE_DIAGNOSTIC",
        "RAW_A0",
        "RAW_B0",
        "MARKET_BENCHMARK",
    ]
    lines = [
        "# Candidate 5 Historical Results",
        "",
        f"Final Phase 5 scientific disposition: **`{disposition}`**.",
        "",
        "Primary development/evaluation surface: chronology-clean 2022–2024 OOF evidence. 2022 Candidate 5 meta-predictions deterministically fall back to F-ST because no earlier Candidate 5 component surface exists.",
        "",
        "| Arm | Games | Accuracy | Delta vs F-ST (pp) | Switch rate | Changed-winner accuracy | Brier delta | Log-loss delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in order:
        m = dev_metrics[arm]
        if arm in {"FST", "RAW_A0", "RAW_B0", "MARKET_BENCHMARK"}:
            delta_pp = 100.0 * (m["accuracy"] - dev_metrics["FST"]["accuracy"])
            switch_rate = None
            changed_acc = None
            bdelta = m["brier"] - dev_metrics["FST"]["brier"]
            ldelta = m["log_loss"] - dev_metrics["FST"]["log_loss"]
        else:
            delta_pp = m["accuracy_delta_pp"]
            switch_rate = m["changed_winner_rate"]
            changed_acc = m["changed_winner_accuracy"]
            bdelta = m["brier_delta"]
            ldelta = m["log_loss_delta"]
        lines.append(
            f"| {arm} | {m['games']} | {_fmt(m['accuracy'], 6)} | {_fmt(delta_pp, 4)} | "
            f"{_fmt(switch_rate, 4)} | {_fmt(changed_acc, 4)} | {_fmt(bdelta, 6)} | {_fmt(ldelta, 6)} |"
        )
    p = dev_metrics["PRIMARY_COMPACT_FOOTBALL"]
    changed_pct = _fmt(100 * p["changed_winner_accuracy"], 3) if p["changed_winner_accuracy"] is not None else "NA"
    lines += [
        "",
        "## Primary mechanism",
        "",
        f"- F-ST correct: **{p['fst_correct']}**",
        f"- Candidate 5 correct: **{p['candidate_correct']}**",
        f"- Candidate-5-only correct: **{p['candidate_only_correct']}**",
        f"- F-ST-only correct: **{p['fst_only_correct']}**",
        f"- winner changes: **{p['changed_winners']}** ({_fmt(100*p['changed_winner_rate'], 3)}%)",
        f"- changed-winner accuracy: **{changed_pct}%**",
        f"- exact McNemar p: **{_fmt(p['mcnemar_exact_two_sided_p'], 6)}**",
        f"- mechanism identity verified: `{_fmt(p['accuracy_delta'], 12)} = {_fmt(p['mechanism_identity_delta'], 12)}`",
        "",
        "## 2025 fixed-model diagnostic",
        "",
        "**`POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`** — 2025 is not an untouched Candidate 5 holdout and did not select or rescue the architecture.",
        "",
        "| Arm | Games | Accuracy | Delta vs F-ST (pp) | Changed winners | Changed-winner accuracy | Brier delta | Log-loss delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ["FST_PLUS_A0", "FST_PLUS_B0", "FST_PLUS_A0_PLUS_B0", "PRIMARY_COMPACT_FOOTBALL", "MARKET_AWARE_DIAGNOSTIC"]:
        m = diag_metrics[arm]
        lines.append(
            f"| {arm} | {m['games']} | {_fmt(m['accuracy'], 6)} | {_fmt(m['accuracy_delta_pp'], 4)} | "
            f"{m['changed_winners']} | {_fmt(m['changed_winner_accuracy'], 4)} | {_fmt(m['brier_delta'], 6)} | {_fmt(m['log_loss_delta'], 6)} |"
        )
    (out / "CANDIDATE5_HISTORICAL_RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    ints = bootstrap["intervals"]
    uncertainty = f"""# Candidate 5 Uncertainty Report

Primary arm: `PRIMARY_COMPACT_FOOTBALL` on chronology-clean 2022–2024 exact-paired rows.

Season+week block bootstrap: **{bootstrap['samples']:,}** resamples, **{bootstrap['blocks']}** blocks, seed `{bootstrap['seed']}`.

| Quantity | 2.5% | Median | 97.5% |
|---|---:|---:|---:|
| Candidate accuracy | {_fmt(ints['candidate_accuracy']['p2_5'], 6)} | {_fmt(ints['candidate_accuracy']['median'], 6)} | {_fmt(ints['candidate_accuracy']['p97_5'], 6)} |
| Accuracy delta | {_fmt(ints['accuracy_delta']['p2_5'], 6)} | {_fmt(ints['accuracy_delta']['median'], 6)} | {_fmt(ints['accuracy_delta']['p97_5'], 6)} |
| Brier delta | {_fmt(ints['brier_delta']['p2_5'], 6)} | {_fmt(ints['brier_delta']['median'], 6)} | {_fmt(ints['brier_delta']['p97_5'], 6)} |
| Log-loss delta | {_fmt(ints['log_loss_delta']['p2_5'], 6)} | {_fmt(ints['log_loss_delta']['median'], 6)} | {_fmt(ints['log_loss_delta']['p97_5'], 6)} |

Intervals are uncertainty diagnostics, not post-hoc tuning gates.
"""
    (out / "CANDIDATE5_UNCERTAINTY_REPORT.md").write_text(uncertainty, encoding="utf-8")

    cal = pd.DataFrame(calibration_rows)
    primary_cal = cal[(cal["sample"] == "2022_2024") & (cal["arm"] == "PRIMARY_COMPACT_FOOTBALL")].iloc[0]
    fst_cal = cal[(cal["sample"] == "2022_2024") & (cal["arm"] == "FST")].iloc[0]
    calibration = f"""# Candidate 5 Calibration Report

Calibration is diagnostic only; no recalibration was applied.

| Forecast | Intercept | Slope |
|---|---:|---:|
| F-ST | {_fmt(fst_cal['intercept'], 6)} | {_fmt(fst_cal['slope'], 6)} |
| Candidate 5 primary | {_fmt(primary_cal['intercept'], 6)} | {_fmt(primary_cal['slope'], 6)} |

Brier and log-loss deltas are reported in `CANDIDATE5_HISTORICAL_RESULTS.md`. Fixed ten-bin reliability evidence is preserved in `CANDIDATE5_RELIABILITY.csv`.
"""
    (out / "CANDIDATE5_CALIBRATION_REPORT.md").write_text(calibration, encoding="utf-8")

    red_team = f"""# Candidate 5 Red-Team Audit

Final audit status: **PASS with scientific disposition `{disposition}`**.

- same-row base-prediction leakage: PASS — A0/B0/C0 OOF assertions and train-through seasons were verified.
- meta-model future leakage: PASS — every fitted target uses only earlier seasons; 2022 is deterministic F-ST fallback.
- outcome-derived feature leakage: PASS — only preregistered pregame component outputs are model inputs.
- post-result feature/component choice: PASS — scientific freeze commit `{PREREG_SHA}` predates execution.
- 2025 tuning: PASS — 2025 outcomes never select lambda, features, architecture, or classification.
- completed-2026 contamination: PASS — execution loads historical sources only through 2025; no `outputs/` grading surface is read.
- closing-line-as-T-120 contamination: PASS — C0 is isolated to the diagnostic arm and retains `{MARKET_HORIZON}`.
- F-ST surface mismatch: PASS — historical F-ST is reproduced through the accepted chronology-clean annual stack and reproduces 741/1,087.
- game-ID mismatches / duplicate games: PASS — hard one-to-one identity checks.
- scaling leakage: PASS — means/standard deviations are fit on meta-training rows only.
- hyperparameter leakage: PASS — fixed grid and prior-season log-loss tuning only.
- threshold fishing: PASS — winner rule remains strict `P > 0.5`.
- outcome-dependent filtering: PASS — complete-case eligibility is fixed by the feature contract and required finite fields.
- production modifications: PASS — runner writes only Phase 5 research evidence; CI separately diffs protected production surfaces.
- model rescue: PASS — no learner, feature, grid, calibration or threshold changes occurred after results.

The inspection of current 2026 repository state before branching was limited to integration/provenance resolution and did not enter Candidate 5 modeling or grading.
"""
    (out / "CANDIDATE5_RED_TEAM_AUDIT.md").write_text(red_team, encoding="utf-8")


def preflight() -> dict:
    cfg = load_config()
    receipt = validate_freeze_receipt()
    required_paths = [OOF_PATH, A0_2025_PATH, B0_2025_PATH, C0_2025_PATH, FST_SOURCE, CONFIG_PATH, FREEZE_RECEIPT]
    missing = [str(p) for p in required_paths if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Candidate 5 preflight missing files: {missing}")
    oof = pd.read_csv(OOF_PATH, nrows=2)
    raw_required = {
        "game_id", "season", "week", "home_team", "away_team",
        "a0_home_win_probability", "a0_expected_margin", "a0_score_uncertainty",
        "a0_offense_strength_diff", "a0_defense_strength_diff",
        "b0_home_win_probability", "b0_expected_margin", "b0_expected_total",
        "b0_margin_variance", "b0_total_variance", "c0_market_margin", "c0_market_total",
        "c0_predicted_margin_residual", "c0_predicted_total_residual",
        "c0_market_horizon_label", "oof_provenance_assertion",
    }
    missing_raw = raw_required - set(oof.columns)
    if missing_raw:
        raise RuntimeError(f"Candidate 5 OOF schema drift: {sorted(missing_raw)}")
    return {
        "candidate_id": CANDIDATE_ID,
        "status": "PASS",
        "preregistration_commit_sha": receipt["preregistration_commit_sha"],
        "branch_base_main_sha": receipt["branch_base_main_sha"],
        "config_sha256": _sha256(CONFIG_PATH),
        "candidate5_specific_metrics_generated": False,
        "completed_2026_outcomes_used": False,
        "production_changed": False,
    }


def run(output_dir: str | Path) -> dict:
    cfg = load_config()
    receipt = validate_freeze_receipt()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    fst = load_fst_history()
    dev = load_development_surface(fst)
    diag = load_2025_surface(fst)

    dev_predictions = dev[["game_id", "season", "week", "home_team", "away_team", "home_win", "fst_prob", "market_prob", "a0_home_win_probability", "b0_home_win_probability", "fst_confidence", "component_prob_dispersion"]].copy()
    diag_predictions = diag[["game_id", "season", "week", "home_team", "away_team", "home_win", "fst_prob", "market_prob", "a0_home_win_probability", "b0_home_win_probability", "fst_confidence", "component_prob_dispersion"]].copy()

    model_fits: list[dict] = []
    tuning_records: list[dict] = []
    dev_metrics: dict[str, dict] = {}
    diag_metrics: dict[str, dict] = {}
    calibration_rows: list[dict] = []
    reliability: list[dict] = []

    for name, col in (("FST", "fst_prob"), ("RAW_A0", "a0_home_win_probability"), ("RAW_B0", "b0_home_win_probability"), ("MARKET_BENCHMARK", "market_prob")):
        m = baseline_metrics(dev, col, name, "2022_2024")
        dev_metrics[name] = m
        cal = calibration_stats(dev[col], dev["home_win"])
        calibration_rows.append({"sample": "2022_2024", "arm": name, **cal})
        reliability += reliability_rows(dev[col], dev["home_win"], name, "2022_2024")

    for arm in MODELED_ARMS:
        pred, fits, tuning = development_predictions(dev, arm, cfg)
        dev_predictions[f"{arm.lower()}_prob"] = pred.to_numpy(float)
        metrics = evaluate_probs(dev, pred)
        dev_metrics[arm] = metrics
        model_fits.extend(fits)
        tuning_records.extend(tuning)
        calibration_rows.append({"sample": "2022_2024", "arm": arm, **metrics["calibration"]})
        reliability += reliability_rows(pred, dev["home_win"], arm, "2022_2024")

        diag_pred, fit_2025, tuning_2025 = diagnostic_2025_prediction(dev, diag, arm, cfg)
        diag_predictions[f"{arm.lower()}_prob"] = diag_pred
        dmetrics = evaluate_probs(diag, diag_pred)
        diag_metrics[arm] = dmetrics
        model_fits.append(fit_2025)
        tuning_records.append(tuning_2025)
        calibration_rows.append({"sample": "2025_non_pristine", "arm": arm, **dmetrics["calibration"]})
        reliability += reliability_rows(diag_pred, diag["home_win"], arm, "2025_non_pristine")

    for name, col in (("FST", "fst_prob"), ("RAW_A0", "a0_home_win_probability"), ("RAW_B0", "b0_home_win_probability"), ("MARKET_BENCHMARK", "market_prob")):
        diag_metrics[name] = baseline_metrics(diag, col, name, "2025_non_pristine")
        cal = calibration_stats(diag[col], diag["home_win"])
        calibration_rows.append({"sample": "2025_non_pristine", "arm": name, **cal})
        reliability += reliability_rows(diag[col], diag["home_win"], name, "2025_non_pristine")

    primary = dev_metrics["PRIMARY_COMPACT_FOOTBALL"]
    disposition = classification(primary)
    bootstrap = block_bootstrap(dev, dev_predictions["primary_compact_football_prob"], int(cfg["bootstrap_samples"]), int(cfg["bootstrap_seed"]))
    slices = diagnostic_slices(dev, dev_predictions["primary_compact_football_prob"].to_numpy(float))

    ablation_rows = []
    for sample, metrics_map in (("2022_2024", dev_metrics), ("2025_non_pristine", diag_metrics)):
        for arm, m in metrics_map.items():
            if "candidate_correct" in m:
                row = {
                    "sample": sample, "arm": arm, "games": m["games"], "correct": m["candidate_correct"],
                    "accuracy": m["accuracy"], "accuracy_delta_pp": m["accuracy_delta_pp"],
                    "changed_winners": m["changed_winners"], "changed_winner_rate": m["changed_winner_rate"],
                    "changed_winner_accuracy": m["changed_winner_accuracy"], "candidate_only_correct": m["candidate_only_correct"],
                    "fst_only_correct": m["fst_only_correct"], "mcnemar_exact_two_sided_p": m["mcnemar_exact_two_sided_p"],
                    "brier": m["brier"], "brier_delta": m["brier_delta"], "log_loss": m["log_loss"], "log_loss_delta": m["log_loss_delta"],
                }
            else:
                fst_m = metrics_map["FST"]
                row = {
                    "sample": sample, "arm": arm, "games": m["games"], "correct": m["correct"], "accuracy": m["accuracy"],
                    "accuracy_delta_pp": 100.0 * (m["accuracy"] - fst_m["accuracy"]), "changed_winners": None,
                    "changed_winner_rate": None, "changed_winner_accuracy": None, "candidate_only_correct": None,
                    "fst_only_correct": None, "mcnemar_exact_two_sided_p": None, "brier": m["brier"],
                    "brier_delta": m["brier"] - fst_m["brier"], "log_loss": m["log_loss"],
                    "log_loss_delta": m["log_loss"] - fst_m["log_loss"],
                }
            ablation_rows.append(row)

    manifest = {
        "run_id": "LEVLINE-SPREAD-POINTS-PHASE5-CANDIDATE5-V1",
        "candidate_id": CANDIDATE_ID,
        "preregistration_commit_sha": receipt["preregistration_commit_sha"],
        "branch_base_main_sha": receipt["branch_base_main_sha"],
        "code_sha256": _sha256(Path(__file__)),
        "config_sha256": _sha256(CONFIG_PATH),
        "fst_identity": FST_ID,
        "fst_historical_provenance": {
            "source": str(FST_SOURCE.relative_to(ROOT)),
            "stack_code": "src/nfl_forecast/challenger_stacking.py",
            "interpretation": "chronology-clean historical reproduction, not original prospective locks",
            "reproduced_2022_2025_games": 1087,
            "reproduced_correct": 741,
        },
        "development": {
            "seasons": [2022, 2023, 2024],
            "games": int(len(dev)),
            "oof_component_surface": str(OOF_PATH.relative_to(ROOT)),
            "2022_meta_fallback": "FST_ZERO_RESIDUAL_CORRECTION",
        },
        "diagnostic_2025": {
            "label": "POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC",
            "games": int(len(diag)),
            "used_for_architecture_or_selection": False,
            "may_trigger_rescue": False,
        },
        "market_horizon_label": MARKET_HORIZON,
        "D_disposition": "ENSEMBLE_NOT_ELIGIBLE",
        "scientific_disposition": disposition,
        "phase6_eligible": disposition == "ELIGIBLE_FOR_PROSPECTIVE_PHASE6_SHADOW_VALIDATION",
        "completed_2026_outcomes_used": False,
        "production_changed": False,
        "winner_threshold_tuned": False,
        "posthoc_calibration_applied": False,
        "nonlinear_learner_used": False,
        "bootstrap": bootstrap,
        "primary_metrics": primary,
    }

    dev_predictions.to_csv(out / "CANDIDATE5_DEVELOPMENT_PREDICTIONS_2022_2024.csv", index=False)
    diag_predictions.to_csv(out / "CANDIDATE5_2025_DIAGNOSTIC.csv", index=False)
    pd.DataFrame(ablation_rows).to_csv(out / "CANDIDATE5_ABLATION_METRICS.csv", index=False)
    pd.DataFrame(calibration_rows).to_csv(out / "CANDIDATE5_CALIBRATION.csv", index=False)
    pd.DataFrame(reliability).to_csv(out / "CANDIDATE5_RELIABILITY.csv", index=False)
    slices.to_csv(out / "CANDIDATE5_SLICES.csv", index=False)
    (out / "CANDIDATE5_MODEL_FITS.json").write_text(json.dumps({"fits": model_fits, "tuning": tuning_records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "CANDIDATE5_RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "CANDIDATE5_RESULTS.json").write_text(json.dumps({"development": dev_metrics, "diagnostic_2025": diag_metrics, "scientific_disposition": disposition}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "CANDIDATE5_BOOTSTRAP_SUMMARY.json").write_text(json.dumps(bootstrap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown_reports(out, dev_metrics, diag_metrics, bootstrap, calibration_rows, disposition)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="/tmp/levline-phase5")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        print(json.dumps(preflight(), indent=2, sort_keys=True))
    else:
        run(args.output_dir)


if __name__ == "__main__":
    main()
