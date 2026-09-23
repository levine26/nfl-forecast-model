from __future__ import annotations

"""Chronology-clean Stage-B Q2 selection and evaluation.

Research only.  This module adds no model family or tuning surface beyond the
frozen Stage-B opening receipt.  Each preregistered ablation is evaluated as a
separate model.  Only the already-frozen family shape and key-shrinkage grids
are selected by prior-time discrete CRPS.
"""

from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
import pandas as pd

from nfl_forecast.challenger_ats_nextgen_gate import OUTER_TARGET_SEASONS, validate_gate_frame
from nfl_forecast.challenger_ats_nextgen_q2 import (
    BOUNDARY_MASS_LIMIT,
    GN_BETA_GRID,
    KEY_PENALTY_GRID,
    SUPPORT,
    T_DF_GRID,
    ContinuousDistributionFit,
    continuous_base_pmf,
    cover_push_loss_probabilities,
    discrete_crps,
    empirical_residual_pmf,
    fit_continuous_distribution,
    predict_continuous_distribution,
    q1_median_center_for_target,
)

CenterMode = Literal["M1", "Q2"]
FamilyName = Literal["gennorm", "norm", "t", "emp"]
Ablation = Literal[
    "no_key_conditional_scale",
    "key_constant_scale",
    "key_conditional_scale",
    "empirical",
]

PARAMETRIC_FAMILIES: tuple[FamilyName, ...] = ("gennorm", "norm", "t")
ABLATIONS: tuple[Ablation, ...] = (
    "no_key_conditional_scale",
    "key_constant_scale",
    "key_conditional_scale",
)
PRIMARY_FAMILY: FamilyName = "gennorm"
PRIMARY_ABLATION: Ablation = "key_conditional_scale"
TIE_TOLERANCE = 1e-12
PROB_FLOOR = 1e-15


@dataclass(frozen=True)
class Q2Config:
    family: FamilyName
    ablation: Ablation
    shape: float | None
    key_penalty: float | None


@dataclass(frozen=True)
class Q2Selection:
    outer_target_season: int
    center_mode: CenterMode
    family: FamilyName
    ablation: Ablation
    selected_shape: float | None
    selected_key_penalty: float | None
    mean_inner_crps: float
    inner_rows: int
    inner_targets_used: tuple[int, ...]
    inner_targets_omitted: tuple[int, ...]


def _eligible(frame: pd.DataFrame, seasons: tuple[int, ...] | list[int]) -> pd.DataFrame:
    season = pd.to_numeric(frame["season"], errors="coerce")
    margin = pd.to_numeric(frame["margin"], errors="coerce")
    mask = (
        season.isin(list(seasons))
        & frame["ats_eligible"].astype(bool)
        & np.isfinite(margin.to_numpy(dtype=float))
    )
    return frame.loc[mask].copy()


def _shape_grid(family: FamilyName) -> tuple[float | None, ...]:
    if family == "gennorm":
        return tuple(float(x) for x in GN_BETA_GRID)
    if family == "norm":
        return (None,)
    if family == "t":
        return tuple(float(x) for x in T_DF_GRID)
    if family == "emp":
        return (None,)
    raise ValueError(f"unregistered Q2 family: {family}")


def configs_for(family: FamilyName, ablation: Ablation) -> tuple[Q2Config, ...]:
    """Enumerate only the frozen grid for one fixed ablation."""
    if family == "emp":
        if ablation != "empirical":
            raise ValueError("Q2-EMP has only the empirical ablation")
        return (Q2Config("emp", "empirical", None, None),)
    if family not in PARAMETRIC_FAMILIES or ablation not in ABLATIONS:
        raise ValueError("Q2 family/ablation is outside the frozen contract")
    penalties: tuple[float | None, ...]
    if ablation == "no_key_conditional_scale":
        penalties = (None,)
    else:
        penalties = tuple(float(x) for x in KEY_PENALTY_GRID)
    return tuple(
        Q2Config(family, ablation, shape, penalty)
        for shape in _shape_grid(family)
        for penalty in penalties
    )


def _center_bundle(
    frame: pd.DataFrame,
    target_season: int,
    center_mode: CenterMode,
) -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray, dict]:
    target = int(target_season)
    train = _eligible(frame, list(range(2015, target)))
    valid = _eligible(frame, (target,))
    if train.empty or valid.empty:
        raise RuntimeError(f"Q2 target {target} lacks eligible training/target rows")
    market_train = pd.to_numeric(
        train["market_home_margin_center"], errors="raise"
    ).to_numpy(dtype=float)
    market_valid = pd.to_numeric(
        valid["market_home_margin_center"], errors="raise"
    ).to_numpy(dtype=float)

    if center_mode == "M1":
        return train, market_train, valid, market_valid, {
            "q1_selected_alpha": None,
            "q1_inner_targets_used": "",
            "q1_inner_targets_omitted": "",
        }
    if center_mode != "Q2":
        raise ValueError("Q2 center mode must be M1 or Q2")

    q1 = q1_median_center_for_target(frame, target)
    train_ids = tuple(train["game_id"].astype(str))
    valid_ids = tuple(valid["game_id"].astype(str))
    if train_ids != q1.train_game_ids or valid_ids != q1.target_game_ids:
        raise RuntimeError("Q2 upstream Q1 center rows are not aligned to gate rows")
    train_center = market_train + np.asarray(q1.train_residual_prediction, dtype=float)
    valid_center = market_valid + np.asarray(q1.target_residual_prediction, dtype=float)
    return train, train_center, valid, valid_center, {
        "q1_selected_alpha": float(q1.selected_alpha),
        "q1_inner_targets_used": ",".join(map(str, q1.inner_targets_used)),
        "q1_inner_targets_omitted": ",".join(map(str, q1.inner_targets_omitted)),
    }


def _fit_predict_config(
    train: pd.DataFrame,
    train_center: np.ndarray,
    target: pd.DataFrame,
    target_center: np.ndarray,
    config: Q2Config,
) -> tuple[np.ndarray, ContinuousDistributionFit | None]:
    if config.family == "emp":
        pmf = empirical_residual_pmf(
            pd.to_numeric(train["margin"], errors="raise").to_numpy(dtype=float),
            train_center,
            target_center,
        )
        # The support guard is a V1-level validity condition.  Empirical tails are
        # folded into endpoints by construction and are checked here as well.
        boundary = pmf[:, 0] + pmf[:, -1]
        if np.max(boundary, initial=0.0) > BOUNDARY_MASS_LIMIT:
            raise RuntimeError("Q2-EMP material endpoint mass exceeds frozen V1 threshold")
        return pmf, None

    fit = fit_continuous_distribution(
        train,
        train_center,
        family=config.family,  # type: ignore[arg-type]
        shape=config.shape,
        ablation=config.ablation,  # type: ignore[arg-type]
        key_penalty=config.key_penalty,
    )
    pmf = predict_continuous_distribution(target, target_center, fit, enforce_boundary=True)
    return pmf, fit


def _config_tie_key(config: Q2Config) -> tuple[float, float]:
    """Frozen tie-break: larger shape, then larger key penalty."""
    shape = float(config.shape) if config.shape is not None else float("inf")
    penalty = float(config.key_penalty) if config.key_penalty is not None else float("inf")
    return (shape, penalty)


def select_config_inner(
    frame: pd.DataFrame,
    *,
    outer_target_season: int,
    center_mode: CenterMode,
    family: FamilyName,
    ablation: Ablation,
) -> tuple[Q2Selection, pd.DataFrame]:
    """Select shape/key shrinkage on pooled prior-time CRPS for one fixed ablation."""
    validate_gate_frame(frame)
    outer = int(outer_target_season)
    if outer not in OUTER_TARGET_SEASONS:
        raise ValueError("Q2 outer target is outside the frozen 2022-2025 set")
    if family == "emp":
        raise ValueError("Q2-EMP has no tunable shape/key parameter")

    inner_targets = tuple(range(2020, outer))
    if not inner_targets:
        raise RuntimeError("Q2 has no registered inner targets after mechanical 2019 omission")
    center_cache = {
        target: _center_bundle(frame, target, center_mode) for target in inner_targets
    }
    rows: list[dict] = []
    scores: dict[Q2Config, list[np.ndarray]] = {c: [] for c in configs_for(family, ablation)}
    targets_used: list[int] = []
    total_rows = 0

    for target in inner_targets:
        train, train_center, valid, valid_center, center_meta = center_cache[target]
        y = pd.to_numeric(valid["margin"], errors="raise").to_numpy(dtype=float)
        targets_used.append(target)
        total_rows += len(valid)
        for config in scores:
            pmf, _ = _fit_predict_config(train, train_center, valid, valid_center, config)
            row_scores = discrete_crps(pmf, y)
            scores[config].append(row_scores)
            rows.append(
                {
                    "outer_target_season": outer,
                    "inner_target_season": target,
                    "center_mode": center_mode,
                    "family": family,
                    "ablation": ablation,
                    "shape": config.shape,
                    "key_penalty": config.key_penalty,
                    "rows": int(len(valid)),
                    "mean_crps": float(np.mean(row_scores)),
                    **center_meta,
                }
            )

    pooled = {config: float(np.mean(np.concatenate(parts))) for config, parts in scores.items()}
    best = min(pooled.values())
    tied = [config for config, value in pooled.items() if abs(value - best) <= TIE_TOLERANCE]
    selected_config = max(tied, key=_config_tie_key)
    selection = Q2Selection(
        outer_target_season=outer,
        center_mode=center_mode,
        family=family,
        ablation=ablation,
        selected_shape=selected_config.shape,
        selected_key_penalty=selected_config.key_penalty,
        mean_inner_crps=float(pooled[selected_config]),
        inner_rows=int(total_rows),
        inner_targets_used=tuple(targets_used),
        inner_targets_omitted=(2019,),
    )
    detail = pd.DataFrame(rows)
    detail["selected"] = (
        detail["shape"].fillna(-999999.0).eq(
            -999999.0 if selected_config.shape is None else float(selected_config.shape)
        )
        & detail["key_penalty"].fillna(-999999.0).eq(
            -999999.0
            if selected_config.key_penalty is None
            else float(selected_config.key_penalty)
        )
    )
    return selection, detail


def _selected_config(selection: Q2Selection) -> Q2Config:
    return Q2Config(
        selection.family,
        selection.ablation,
        selection.selected_shape,
        selection.selected_key_penalty,
    )


def _pmf_median(pmf: np.ndarray) -> np.ndarray:
    cdf = np.cumsum(np.asarray(pmf, dtype=float), axis=1)
    idx = np.argmax(cdf >= 0.5, axis=1)
    return SUPPORT[idx].astype(float)


def _output_rows(
    target: pd.DataFrame,
    pmf: np.ndarray,
    *,
    center_mode: CenterMode,
    family: FamilyName,
    ablation: Ablation,
    shape: float | None,
    key_penalty: float | None,
) -> pd.DataFrame:
    y = pd.to_numeric(target["margin"], errors="raise").to_numpy(dtype=float)
    spread = pd.to_numeric(target["home_spread"], errors="raise").to_numpy(dtype=float)
    cpl = cover_push_loss_probabilities(pmf, spread)
    crps = discrete_crps(pmf, y)
    mean_margin = pmf @ SUPPORT.astype(float)
    median_margin = _pmf_median(pmf)
    endpoint = pmf[:, 0] + pmf[:, -1]
    if np.max(endpoint, initial=0.0) > BOUNDARY_MASS_LIMIT:
        raise RuntimeError("Q2 output exceeded frozen endpoint-mass threshold")

    columns = [
        c
        for c in (
            "game_id",
            "season",
            "week",
            "gameday",
            "home_team",
            "away_team",
            "home_spread",
            "market_home_margin_center",
            "favorite_size",
            "market_total",
            "margin",
            "ats_residual",
            "ats_outcome",
            "market_evidence_class",
        )
        if c in target.columns
    ]
    out = target[columns].copy().reset_index(drop=True)
    out["center_mode"] = center_mode
    out["family"] = family
    out["ablation"] = ablation
    out["shape"] = shape
    out["key_penalty"] = key_penalty
    out["crps"] = crps
    out["pred_mean_margin"] = mean_margin
    out["pred_median_margin"] = median_margin
    out["p_home_cover"] = cpl[:, 0]
    out["p_push"] = cpl[:, 1]
    out["p_home_loss"] = cpl[:, 2]
    out["endpoint_mass"] = endpoint
    return out


def generate_q2_outer_oof(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, np.ndarray]]:
    """Generate frozen 2022-2025 Q2/M1 OOF for every preregistered arm/ablation."""
    validate_gate_frame(frame)
    outputs: list[pd.DataFrame] = []
    selections: list[dict] = []
    inner_details: list[pd.DataFrame] = []
    pmf_blocks: dict[str, list[np.ndarray]] = {}

    for outer in OUTER_TARGET_SEASONS:
        for center_mode in ("M1", "Q2"):
            train, train_center, target, target_center, center_meta = _center_bundle(
                frame, int(outer), center_mode
            )
            for family in PARAMETRIC_FAMILIES:
                for ablation in ABLATIONS:
                    selection, detail = select_config_inner(
                        frame,
                        outer_target_season=int(outer),
                        center_mode=center_mode,
                        family=family,
                        ablation=ablation,
                    )
                    config = _selected_config(selection)
                    pmf, _ = _fit_predict_config(
                        train, train_center, target, target_center, config
                    )
                    outputs.append(
                        _output_rows(
                            target,
                            pmf,
                            center_mode=center_mode,
                            family=family,
                            ablation=ablation,
                            shape=config.shape,
                            key_penalty=config.key_penalty,
                        )
                    )
                    selections.append({**asdict(selection), **center_meta})
                    inner_details.append(detail)
                    key = f"{center_mode}__{family}__{ablation}"
                    pmf_blocks.setdefault(key, []).append(pmf)

            emp = Q2Config("emp", "empirical", None, None)
            emp_pmf, _ = _fit_predict_config(train, train_center, target, target_center, emp)
            outputs.append(
                _output_rows(
                    target,
                    emp_pmf,
                    center_mode=center_mode,
                    family="emp",
                    ablation="empirical",
                    shape=None,
                    key_penalty=None,
                )
            )
            key = f"{center_mode}__emp__empirical"
            pmf_blocks.setdefault(key, []).append(emp_pmf)

    oof = pd.concat(outputs, ignore_index=True)
    oof = oof.sort_values(
        ["center_mode", "family", "ablation", "season", "game_id"], kind="mergesort"
    ).reset_index(drop=True)
    selection_frame = pd.DataFrame(selections).sort_values(
        ["outer_target_season", "center_mode", "family", "ablation"], kind="mergesort"
    ).reset_index(drop=True)
    detail_frame = pd.concat(inner_details, ignore_index=True).sort_values(
        [
            "outer_target_season",
            "center_mode",
            "family",
            "ablation",
            "inner_target_season",
            "shape",
            "key_penalty",
        ],
        kind="mergesort",
        na_position="first",
    ).reset_index(drop=True)
    pmfs = {key: np.vstack(parts) for key, parts in pmf_blocks.items()}
    return oof, selection_frame, detail_frame, pmfs


def q2_metric_table(oof: pd.DataFrame) -> pd.DataFrame:
    """Compute preregistered proper-score/calibration/location metrics."""
    rows: list[dict] = []
    model_cols = ["center_mode", "family", "ablation"]
    for model_key, model in oof.groupby(model_cols, sort=True, dropna=False):
        groups: list[tuple[str, pd.DataFrame]] = [("ALL", model)]
        groups.extend((str(int(s)), part) for s, part in model.groupby("season", sort=True))
        for season_label, part in groups:
            actual_margin = pd.to_numeric(part["margin"], errors="raise").to_numpy(dtype=float)
            actual_residual = pd.to_numeric(
                part["ats_residual"], errors="raise"
            ).to_numpy(dtype=float)
            p_cover = pd.to_numeric(part["p_home_cover"], errors="raise").to_numpy(dtype=float)
            p_push = pd.to_numeric(part["p_push"], errors="raise").to_numpy(dtype=float)
            p_loss = pd.to_numeric(part["p_home_loss"], errors="raise").to_numpy(dtype=float)
            outcome = part["ats_outcome"].astype(str).to_numpy()
            p_observed = np.where(
                outcome == "HOME_COVER",
                p_cover,
                np.where(outcome == "PUSH", p_push, p_loss),
            )
            cpl_logloss = float(-np.mean(np.log(np.maximum(p_observed, PROB_FLOOR))))
            nonpush = outcome != "PUSH"
            cover_binary = (outcome[nonpush] == "HOME_COVER").astype(float)
            p_cover_nonpush = p_cover[nonpush] / np.maximum(
                p_cover[nonpush] + p_loss[nonpush], PROB_FLOOR
            )
            cover_brier = float(np.mean(np.square(p_cover_nonpush - cover_binary)))
            cover_logloss = float(
                -np.mean(
                    cover_binary * np.log(np.maximum(p_cover_nonpush, PROB_FLOOR))
                    + (1.0 - cover_binary)
                    * np.log(np.maximum(1.0 - p_cover_nonpush, PROB_FLOOR))
                )
            )
            mean_pred = pd.to_numeric(
                part["pred_mean_margin"], errors="raise"
            ).to_numpy(dtype=float)
            median_pred = pd.to_numeric(
                part["pred_median_margin"], errors="raise"
            ).to_numpy(dtype=float)
            whole_line = np.isclose(
                np.mod(np.abs(pd.to_numeric(part["home_spread"], errors="raise").to_numpy(dtype=float)), 1.0),
                0.0,
                atol=1e-12,
                rtol=0.0,
            )
            rows.append(
                {
                    "center_mode": model_key[0],
                    "family": model_key[1],
                    "ablation": model_key[2],
                    "season": season_label,
                    "rows": int(len(part)),
                    "mean_crps": float(pd.to_numeric(part["crps"], errors="raise").mean()),
                    "cpl_logloss": cpl_logloss,
                    "cover_brier_nonpush": cover_brier,
                    "cover_logloss_nonpush": cover_logloss,
                    "predicted_push_rate": float(np.mean(p_push)),
                    "observed_push_rate": float(np.mean(outcome == "PUSH")),
                    "whole_line_rows": int(whole_line.sum()),
                    "whole_line_predicted_push_rate": float(np.mean(p_push[whole_line])) if whole_line.any() else np.nan,
                    "whole_line_observed_push_rate": float(np.mean(outcome[whole_line] == "PUSH")) if whole_line.any() else np.nan,
                    "mean_margin_mae": float(np.mean(np.abs(mean_pred - actual_margin))),
                    "mean_margin_rmse": float(np.sqrt(np.mean(np.square(mean_pred - actual_margin)))),
                    "median_margin_mae": float(np.mean(np.abs(median_pred - actual_margin))),
                    "median_margin_rmse": float(np.sqrt(np.mean(np.square(median_pred - actual_margin)))),
                    "max_endpoint_mass": float(pd.to_numeric(part["endpoint_mass"], errors="raise").max()),
                    "mean_abs_market_residual": float(np.mean(np.abs(actual_residual))),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["center_mode", "family", "ablation", "season"], kind="mergesort"
    ).reset_index(drop=True)


def key_calibration_table(
    oof: pd.DataFrame,
    pmfs: dict[str, np.ndarray],
) -> pd.DataFrame:
    """Compare predicted and observed absolute key-margin mass on common OOF rows."""
    rows: list[dict] = []
    for (mode, family, ablation), part in oof.groupby(
        ["center_mode", "family", "ablation"], sort=True
    ):
        key = f"{mode}__{family}__{ablation}"
        pmf = pmfs[key]
        ordered = part.sort_values(["season", "game_id"], kind="mergesort").reset_index(drop=True)
        if len(ordered) != len(pmf):
            raise RuntimeError("Q2 PMF block does not align with OOF rows")
        margin = pd.to_numeric(ordered["margin"], errors="raise").to_numpy(dtype=float)
        for absolute_key in (3, 6, 7, 10, 14):
            positions = [int(-absolute_key - SUPPORT[0]), int(absolute_key - SUPPORT[0])]
            predicted = pmf[:, positions].sum(axis=1)
            observed = np.abs(margin) == float(absolute_key)
            rows.append(
                {
                    "center_mode": mode,
                    "family": family,
                    "ablation": ablation,
                    "absolute_key": absolute_key,
                    "rows": int(len(ordered)),
                    "predicted_rate": float(np.mean(predicted)),
                    "observed_rate": float(np.mean(observed)),
                    "calibration_error": float(np.mean(predicted) - np.mean(observed)),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["center_mode", "family", "ablation", "absolute_key"], kind="mergesort"
    ).reset_index(drop=True)


def primary_comparison(metrics: pd.DataFrame) -> dict:
    """Return the preregistered Q2-GN full-vs-M1-GN full proper-score comparison."""
    overall = metrics[
        metrics["season"].astype(str).eq("ALL")
        & metrics["family"].eq(PRIMARY_FAMILY)
        & metrics["ablation"].eq(PRIMARY_ABLATION)
    ]
    q2 = overall[overall["center_mode"].eq("Q2")]
    m1 = overall[overall["center_mode"].eq("M1")]
    if len(q2) != 1 or len(m1) != 1:
        raise RuntimeError("Q2 primary comparison does not have exactly one Q2 and M1 row")
    q2r = q2.iloc[0]
    m1r = m1.iloc[0]
    return {
        "family": PRIMARY_FAMILY,
        "ablation": PRIMARY_ABLATION,
        "rows": int(q2r["rows"]),
        "q2_mean_crps": float(q2r["mean_crps"]),
        "m1_mean_crps": float(m1r["mean_crps"]),
        "q2_minus_m1_mean_crps": float(q2r["mean_crps"] - m1r["mean_crps"]),
        "q2_cpl_logloss": float(q2r["cpl_logloss"]),
        "m1_cpl_logloss": float(m1r["cpl_logloss"]),
        "q2_minus_m1_cpl_logloss": float(q2r["cpl_logloss"] - m1r["cpl_logloss"]),
    }
