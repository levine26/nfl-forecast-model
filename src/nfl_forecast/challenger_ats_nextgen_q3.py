from __future__ import annotations

"""Frozen Stage-C Q3 direct cover/push/loss hurdle model.

Research only.  This module implements ``ATS-Q3-DIRECT-CPL-HURDLE-V1``
under the Phase-2 chronology/firewall contract.  It does not use Q2 output,
completed-2026 outcomes, class reweighting, or post-hoc calibration.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from nfl_forecast.challenger_ats_nextgen_gate import (
    OUTER_TARGET_SEASONS,
    chronology_plan,
    validate_gate_frame,
)
from nfl_forecast.challenger_ats_nextgen_q1 import Q1Preprocessor, fit_preprocessor

CANDIDATE_ID = "ATS-Q3-DIRECT-CPL-HURDLE-V1"
NULL_ID = "ATS-Q3-M2-MARKET-HURDLE-V1"
C_GRID = (0.01, 0.1, 1.0, 10.0)
KEY_SPREADS = (3.0, 6.0, 7.0, 10.0, 14.0)
LINE_TOLERANCE = 1e-9
PROBABILITY_TOLERANCE = 1e-12
LOGLOSS_FLOOR = 1e-15
TIE_TOLERANCE = 1e-12
MIN_TRAIN_ROWS = 100

Arm = Literal["Q3_M2", "Q3"]


@dataclass(frozen=True)
class PushPreprocessor:
    base: Q1Preprocessor
    key_means: tuple[float, ...]
    key_scales: tuple[float, ...]
    design_columns: tuple[str, ...]

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        base = self.base.transform(frame)
        key = _key_indicator_matrix(frame)
        mean = np.asarray(self.key_means, dtype=float)
        scale = np.asarray(self.key_scales, dtype=float)
        standardized = (key - mean) / scale
        result = np.column_stack([base, standardized])
        if result.shape[1] != len(self.design_columns):
            raise RuntimeError("Q3 push design columns changed after preprocessing fit")
        if not np.isfinite(result).all():
            raise RuntimeError("Q3 push design contains non-finite values")
        return result


@dataclass(frozen=True)
class HurdleFit:
    arm: Arm
    C_push: float
    C_cover: float
    push_preprocessor: PushPreprocessor
    cover_preprocessor: Q1Preprocessor
    push_model: LogisticRegression
    cover_model: LogisticRegression


@dataclass(frozen=True)
class PairSelection:
    outer_target_season: int
    arm: Arm
    C_push: float
    C_cover: float
    mean_multinomial_log_loss: float
    inner_rows: int
    inner_targets_used: tuple[int, ...]
    pair_losses: dict[tuple[float, float], float]


def _eligible(frame: pd.DataFrame, seasons: tuple[int, ...] | list[int]) -> pd.DataFrame:
    season = pd.to_numeric(frame["season"], errors="coerce")
    eligible = frame["ats_eligible"].astype(bool)
    outcome = frame["ats_outcome"].astype("string")
    mask = season.isin(list(seasons)) & eligible & outcome.notna()
    return frame.loc[mask].copy()


def line_lattice(frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return whole/half-line masks and fail on any off-lattice spread."""
    spread = pd.to_numeric(frame["home_spread"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(spread).all():
        raise ValueError("Q3 spread lattice requires finite home_spread")
    frac = np.mod(np.abs(spread), 1.0)
    whole = np.isclose(frac, 0.0, atol=LINE_TOLERANCE, rtol=0.0) | np.isclose(
        frac, 1.0, atol=LINE_TOLERANCE, rtol=0.0
    )
    half = np.isclose(frac, 0.5, atol=LINE_TOLERANCE, rtol=0.0)
    if not np.all(whole | half):
        bad = spread[~(whole | half)]
        raise ValueError(f"Q3 encountered off-lattice spread(s): {bad[:5].tolist()}")
    return whole, half


def _key_indicator_matrix(frame: pd.DataFrame) -> np.ndarray:
    spread = pd.to_numeric(frame["home_spread"], errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(spread).all():
        raise ValueError("Q3 key indicators require finite home_spread")
    size = np.abs(spread)
    return np.column_stack(
        [np.isclose(size, key, atol=LINE_TOLERANCE, rtol=0.0).astype(float) for key in KEY_SPREADS]
    )


def fit_push_preprocessor(frame: pd.DataFrame) -> PushPreprocessor:
    """Fit market preprocessing plus frozen key indicators on whole-line training rows."""
    whole, _ = line_lattice(frame)
    if not np.all(whole):
        raise ValueError("Q3 push preprocessor may be fit only on whole-line rows")
    base = fit_preprocessor(frame, "market")
    key = _key_indicator_matrix(frame)
    mean = np.mean(key, axis=0)
    scale = np.std(key, axis=0, ddof=0)
    scale[~np.isfinite(scale) | np.isclose(scale, 0.0)] = 1.0
    columns = tuple(base.design_columns) + tuple(f"abs_spread_is_{int(k)}" for k in KEY_SPREADS)
    return PushPreprocessor(
        base=base,
        key_means=tuple(float(x) for x in mean),
        key_scales=tuple(float(x) for x in scale),
        design_columns=columns,
    )


def _outcome_index(frame: pd.DataFrame) -> np.ndarray:
    mapping = {"HOME_COVER": 0, "PUSH": 1, "HOME_LOSS": 2}
    mapped = frame["ats_outcome"].astype(str).map(mapping)
    if mapped.isna().any():
        raise ValueError("Q3 encountered unknown ATS outcome")
    return mapped.to_numpy(dtype=int)


def _fit_binary(x: np.ndarray, y: np.ndarray, C: float, label: str) -> LogisticRegression:
    if float(C) not in C_GRID:
        raise ValueError("Q3 C is outside the frozen grid")
    yy = np.asarray(y, dtype=int).reshape(-1)
    if len(yy) < MIN_TRAIN_ROWS:
        raise RuntimeError(f"Q3 {label} head has fewer than {MIN_TRAIN_ROWS} training rows")
    if set(np.unique(yy).tolist()) != {0, 1}:
        raise RuntimeError(f"Q3 {label} head requires both binary classes")
    model = LogisticRegression(
        penalty="l2",
        C=float(C),
        solver="lbfgs",
        fit_intercept=True,
        class_weight=None,
        max_iter=2000,
    )
    model.fit(np.asarray(x, dtype=float), yy)
    if int(model.n_iter_[0]) >= 2000:
        raise RuntimeError(f"Q3 {label} logistic solver hit the iteration limit")
    return model


def _cover_feature_set(arm: Arm) -> str:
    if arm == "Q3_M2":
        return "market"
    if arm == "Q3":
        return "full"
    raise ValueError("Q3 arm must be Q3_M2 or Q3")


def fit_hurdle(
    train: pd.DataFrame,
    *,
    arm: Arm,
    C_push: float,
    C_cover: float,
) -> HurdleFit:
    """Fit both frozen binary heads using only prior-time training rows."""
    whole, half = line_lattice(train)
    outcome = _outcome_index(train)
    if np.any(half & (outcome == 1)):
        raise RuntimeError("Q3 observed an impossible push on a half-point training line")

    push_train = train.loc[whole].copy()
    push_y = (_outcome_index(push_train) == 1).astype(int)
    push_prep = fit_push_preprocessor(push_train)
    push_x = push_prep.transform(push_train)
    push_model = _fit_binary(push_x, push_y, float(C_push), "push")

    nonpush = outcome != 1
    cover_train = train.loc[nonpush].copy()
    cover_y = (_outcome_index(cover_train) == 0).astype(int)
    cover_prep = fit_preprocessor(cover_train, _cover_feature_set(arm))
    cover_x = cover_prep.transform(cover_train)
    cover_model = _fit_binary(cover_x, cover_y, float(C_cover), "cover")

    return HurdleFit(
        arm=arm,
        C_push=float(C_push),
        C_cover=float(C_cover),
        push_preprocessor=push_prep,
        cover_preprocessor=cover_prep,
        push_model=push_model,
        cover_model=cover_model,
    )


def predict_hurdle(frame: pd.DataFrame, fit: HurdleFit) -> np.ndarray:
    """Return columns [cover, push, loss] with structural half-line zero pushes."""
    whole, half = line_lattice(frame)
    p_push = np.zeros(len(frame), dtype=float)
    if whole.any():
        x_push = fit.push_preprocessor.transform(frame.loc[whole])
        p_push[whole] = fit.push_model.predict_proba(x_push)[:, 1]
    if not np.array_equal(p_push[half], np.zeros(int(half.sum()), dtype=float)):
        raise RuntimeError("Q3 half-point push probability is not structurally zero")

    x_cover = fit.cover_preprocessor.transform(frame)
    q_cover = fit.cover_model.predict_proba(x_cover)[:, 1]
    probability = np.column_stack(
        [
            (1.0 - p_push) * q_cover,
            p_push,
            (1.0 - p_push) * (1.0 - q_cover),
        ]
    )
    if not np.isfinite(probability).all():
        raise RuntimeError("Q3 produced non-finite probabilities")
    if (probability < -PROBABILITY_TOLERANCE).any() or (probability > 1.0 + PROBABILITY_TOLERANCE).any():
        raise RuntimeError("Q3 produced probability outside [0,1]")
    if not np.allclose(probability.sum(axis=1), 1.0, atol=PROBABILITY_TOLERANCE, rtol=0.0):
        raise RuntimeError("Q3 cover/push/loss probabilities do not sum to one")
    if not np.all(probability[half, 1] == 0.0):
        raise RuntimeError("Q3 assigned nonzero push probability to half-point line")
    return probability


def multinomial_log_loss(probability: np.ndarray, outcomes: pd.Series | np.ndarray) -> np.ndarray:
    p = np.asarray(probability, dtype=float)
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError("Q3 probability must have cover/push/loss columns")
    if not np.allclose(p.sum(axis=1), 1.0, atol=PROBABILITY_TOLERANCE, rtol=0.0):
        raise ValueError("Q3 probability rows must sum to one")
    if isinstance(outcomes, pd.Series):
        mapping = {"HOME_COVER": 0, "PUSH": 1, "HOME_LOSS": 2}
        idx = outcomes.astype(str).map(mapping)
        if idx.isna().any():
            raise ValueError("Q3 scoring encountered unknown ATS outcome")
        y = idx.to_numpy(dtype=int)
    else:
        y = np.asarray(outcomes, dtype=int).reshape(-1)
    if len(y) != len(p) or not np.isin(y, [0, 1, 2]).all():
        raise ValueError("Q3 outcome vector is not aligned three-class data")
    rows = np.arange(len(p))
    return -np.log(np.maximum(p[rows, y], LOGLOSS_FLOOR))


def _select_pair(losses: dict[tuple[float, float], float]) -> tuple[float, float, float]:
    expected = {(a, b) for a in C_GRID for b in C_GRID}
    if set(losses) != expected:
        raise ValueError("Q3 pair search must contain exactly the frozen 16 C pairs")
    finite = {k: float(v) for k, v in losses.items() if np.isfinite(v)}
    if len(finite) != 16:
        raise ValueError("Q3 pair search contains non-finite loss")
    best = min(finite.values())
    tied = sorted(k for k, v in finite.items() if abs(v - best) <= TIE_TOLERANCE)
    C_push, C_cover = tied[0]
    return float(C_push), float(C_cover), float(finite[(C_push, C_cover)])


def select_c_pair(frame: pd.DataFrame, *, outer_target_season: int, arm: Arm) -> PairSelection:
    validate_gate_frame(frame)
    plan = chronology_plan(int(outer_target_season))
    losses_by_pair: dict[tuple[float, float], list[np.ndarray]] = {
        (a, b): [] for a in C_GRID for b in C_GRID
    }
    targets_used: list[int] = []
    total_rows = 0

    for target in plan.inner_target_seasons:
        train = _eligible(frame, plan.inner_training_seasons[int(target)])
        valid = _eligible(frame, (int(target),))
        if train.empty or valid.empty:
            raise RuntimeError(f"Q3 inner target {target} lacks eligible train/validation rows")
        # Validate the line lattice before any model fit.
        line_lattice(train)
        whole_valid, half_valid = line_lattice(valid)
        valid_outcome = _outcome_index(valid)
        if np.any(half_valid & (valid_outcome == 1)):
            raise RuntimeError("Q3 validation contains impossible half-point push")
        targets_used.append(int(target))
        total_rows += len(valid)
        for C_push in C_GRID:
            for C_cover in C_GRID:
                fit = fit_hurdle(
                    train,
                    arm=arm,
                    C_push=float(C_push),
                    C_cover=float(C_cover),
                )
                probability = predict_hurdle(valid, fit)
                losses_by_pair[(float(C_push), float(C_cover))].append(
                    multinomial_log_loss(probability, valid["ats_outcome"])
                )

    pooled = {
        pair: float(np.mean(np.concatenate(parts))) for pair, parts in losses_by_pair.items()
    }
    C_push, C_cover, best = _select_pair(pooled)
    return PairSelection(
        outer_target_season=int(outer_target_season),
        arm=arm,
        C_push=C_push,
        C_cover=C_cover,
        mean_multinomial_log_loss=best,
        inner_rows=int(total_rows),
        inner_targets_used=tuple(targets_used),
        pair_losses=pooled,
    )


def generate_q3_outer_oof(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate frozen 2022-2025 Q3_M2/Q3 outer OOF probabilities."""
    validate_gate_frame(frame)
    outputs: list[pd.DataFrame] = []
    tuning_rows: list[dict] = []

    for outer in OUTER_TARGET_SEASONS:
        plan = chronology_plan(int(outer))
        train = _eligible(frame, plan.outer_training_seasons)
        target = _eligible(frame, (int(outer),))
        if train.empty or target.empty:
            raise RuntimeError(f"Q3 outer season {outer} lacks eligible train/target rows")
        whole_target, half_target = line_lattice(target)
        outcome = _outcome_index(target)
        if np.any(half_target & (outcome == 1)):
            raise RuntimeError("Q3 outer target contains impossible half-point push")

        cols = [
            c
            for c in (
                "game_id", "season", "week", "gameday", "home_team", "away_team",
                "home_spread", "market_home_margin_center", "favorite_size", "market_total",
                "ats_outcome", "market_evidence_class",
            )
            if c in target.columns
        ]
        result = target[cols].copy().reset_index(drop=True)

        for arm, prefix in (("Q3_M2", "q3_m2"), ("Q3", "q3")):
            selection = select_c_pair(frame, outer_target_season=int(outer), arm=arm)
            fit = fit_hurdle(
                train,
                arm=arm,
                C_push=selection.C_push,
                C_cover=selection.C_cover,
            )
            probability = predict_hurdle(target, fit)
            result[f"{prefix}_p_cover"] = probability[:, 0]
            result[f"{prefix}_p_push"] = probability[:, 1]
            result[f"{prefix}_p_loss"] = probability[:, 2]
            result[f"{prefix}_C_push"] = selection.C_push
            result[f"{prefix}_C_cover"] = selection.C_cover
            tuning_rows.append(
                {
                    "outer_target_season": int(outer),
                    "arm": arm,
                    "selected_C_push": selection.C_push,
                    "selected_C_cover": selection.C_cover,
                    "selected_mean_multinomial_log_loss": selection.mean_multinomial_log_loss,
                    "inner_rows": selection.inner_rows,
                    "inner_targets_used": ",".join(map(str, selection.inner_targets_used)),
                    **{
                        f"Cpush_{a:g}_Ccover_{b:g}_loss": selection.pair_losses[(float(a), float(b))]
                        for a in C_GRID
                        for b in C_GRID
                    },
                }
            )
        outputs.append(result)

    oof = pd.concat(outputs, ignore_index=True)
    if oof["game_id"].astype(str).duplicated().any():
        raise RuntimeError("Q3 OOF contains duplicate game_id")
    oof = oof.sort_values(["season", "game_id"], kind="mergesort").reset_index(drop=True)
    tuning = pd.DataFrame(tuning_rows).sort_values(
        ["outer_target_season", "arm"], kind="mergesort"
    ).reset_index(drop=True)
    return oof, tuning
