from __future__ import annotations

"""Nested rolling-origin experiment driver for frozen ATS NextGen Q2 Stage B."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from nfl_forecast.challenger_ats_nextgen_gate import (
    OUTER_TARGET_SEASONS,
    TRAINING_FLOOR,
    validate_gate_frame,
)
from nfl_forecast.challenger_ats_nextgen_q2 import (
    BOUNDARY_MASS_LIMIT,
    GN_BETA_GRID,
    KEY_PENALTY_GRID,
    TIE_TOLERANCE,
    T_DF_GRID,
    Ablation,
    CenterMode,
    Family,
    _eligible,
    discrete_crps,
    empirical_residual_pmf,
    endpoint_mass,
    fit_continuous_distribution,
    predict_continuous_distribution,
    q1_median_center_for_target,
)


@dataclass(frozen=True)
class CandidateSpec:
    family: Family
    shape: float | None
    ablation: Ablation
    key_penalty: float | None


@dataclass(frozen=True)
class TargetData:
    target_season: int
    train: pd.DataFrame
    target: pd.DataFrame
    train_centers: np.ndarray
    target_centers: np.ndarray
    q1_alpha: float | None
    q1_inner_targets_used: tuple[int, ...]
    q1_inner_targets_omitted: tuple[int, ...]


ARM_CONFIGS: dict[str, tuple[Family, Ablation]] = {
    "GN_NO_KEY": ("gennorm", "no_key_conditional_scale"),
    "GN_KEY_CONST": ("gennorm", "key_constant_scale"),
    "GN_FULL": ("gennorm", "key_conditional_scale"),
    "N_FULL": ("norm", "key_conditional_scale"),
    "T_FULL": ("t", "key_conditional_scale"),
}
EMP_ARM = "EMP"


def _spec_grid(family: Family, ablation: Ablation) -> tuple[CandidateSpec, ...]:
    if family == "gennorm":
        shapes: tuple[float | None, ...] = tuple(float(x) for x in GN_BETA_GRID)
    elif family == "t":
        shapes = tuple(float(x) for x in T_DF_GRID)
    elif family == "norm":
        shapes = (None,)
    else:
        raise ValueError(f"unsupported Q2 family {family}")
    penalties: tuple[float | None, ...]
    if ablation == "no_key_conditional_scale":
        penalties = (None,)
    else:
        penalties = tuple(float(x) for x in KEY_PENALTY_GRID)
    return tuple(
        CandidateSpec(family, shape, ablation, penalty)
        for shape in shapes
        for penalty in penalties
    )


def target_data(
    frame: pd.DataFrame,
    target_season: int,
    center_mode: CenterMode,
    *,
    q1_cache: dict[int, object] | None = None,
) -> TargetData:
    validate_gate_frame(frame)
    target_year = int(target_season)
    if target_year < 2020 or target_year > 2025:
        raise ValueError("Q2 target data is registered only for 2020..2025")
    train = _eligible(frame, list(range(TRAINING_FLOOR, target_year)))
    target = _eligible(frame, (target_year,))
    if train.empty or target.empty:
        raise RuntimeError(f"Q2 target {target_year} lacks eligible train/target rows")
    market_train = pd.to_numeric(
        train["market_home_margin_center"], errors="raise"
    ).to_numpy(dtype=float)
    market_target = pd.to_numeric(
        target["market_home_margin_center"], errors="raise"
    ).to_numpy(dtype=float)

    if center_mode == "M1":
        return TargetData(
            target_year,
            train,
            target,
            market_train,
            market_target,
            None,
            (),
            (),
        )
    if center_mode != "Q2":
        raise ValueError("Q2 center mode must be M1 or Q2")

    cache = q1_cache if q1_cache is not None else {}
    if target_year not in cache:
        cache[target_year] = q1_median_center_for_target(frame, target_year)
    q1 = cache[target_year]
    if tuple(train["game_id"].astype(str)) != tuple(q1.train_game_ids):
        raise RuntimeError("Q2 training rows do not align with frozen upstream Q1 center")
    if tuple(target["game_id"].astype(str)) != tuple(q1.target_game_ids):
        raise RuntimeError("Q2 target rows do not align with frozen upstream Q1 center")
    train_center = market_train + np.asarray(q1.train_residual_prediction, dtype=float)
    target_center = market_target + np.asarray(q1.target_residual_prediction, dtype=float)
    return TargetData(
        target_year,
        train,
        target,
        train_center,
        target_center,
        float(q1.selected_alpha),
        tuple(q1.inner_targets_used),
        tuple(q1.inner_targets_omitted),
    )


def _candidate_crps_for_target(
    data: TargetData,
    spec: CandidateSpec,
) -> np.ndarray:
    fit = fit_continuous_distribution(
        data.train,
        data.train_centers,
        family=spec.family,
        shape=spec.shape,
        ablation=spec.ablation,
        key_penalty=spec.key_penalty,
    )
    pmf = predict_continuous_distribution(
        data.target,
        data.target_centers,
        fit,
        enforce_boundary=False,
    )
    max_boundary = float(endpoint_mass(pmf).max())
    if max_boundary > BOUNDARY_MASS_LIMIT:
        raise RuntimeError(
            f"Q2 candidate {spec} exceeded frozen endpoint-mass threshold: {max_boundary}"
        )
    y = pd.to_numeric(data.target["margin"], errors="raise").to_numpy(dtype=float)
    return discrete_crps(pmf, y)


def _simplicity_key(spec: CandidateSpec) -> tuple[float, float]:
    shape = float(spec.shape) if spec.shape is not None else float("inf")
    penalty = float(spec.key_penalty) if spec.key_penalty is not None else float("inf")
    return shape, penalty


def select_spec(
    frame: pd.DataFrame,
    *,
    outer_target_season: int,
    center_mode: CenterMode,
    family: Family,
    ablation: Ablation,
    q1_cache: dict[int, object] | None = None,
    score_cache: dict[tuple, np.ndarray] | None = None,
) -> tuple[CandidateSpec, pd.DataFrame]:
    """Select a frozen continuous spec using pooled prior-time row-level CRPS."""
    outer = int(outer_target_season)
    if outer not in OUTER_TARGET_SEASONS:
        raise ValueError("Q2 outer target is outside the frozen set")
    inner_targets = tuple(range(2020, outer))  # 2019 is frozen as mechanically omitted.
    if not inner_targets:
        raise RuntimeError("Q2 has no usable inner target after frozen 2019 omission")
    qcache = q1_cache if q1_cache is not None else {}
    scache = score_cache if score_cache is not None else {}
    rows: list[dict] = []
    specs = _spec_grid(family, ablation)

    for spec in specs:
        pooled: list[np.ndarray] = []
        per_target: list[tuple[int, float, int]] = []
        for target_year in inner_targets:
            key = (
                int(target_year),
                center_mode,
                spec.family,
                spec.shape,
                spec.ablation,
                spec.key_penalty,
            )
            if key not in scache:
                data = target_data(frame, target_year, center_mode, q1_cache=qcache)
                scache[key] = _candidate_crps_for_target(data, spec)
            score = np.asarray(scache[key], dtype=float)
            pooled.append(score)
            per_target.append((target_year, float(np.mean(score)), int(len(score))))
        all_scores = np.concatenate(pooled)
        rows.append(
            {
                "outer_target_season": outer,
                "center_mode": center_mode,
                "family": spec.family,
                "shape": spec.shape,
                "ablation": spec.ablation,
                "key_penalty": spec.key_penalty,
                "inner_targets_used": ",".join(map(str, inner_targets)),
                "inner_target_2019_omitted": True,
                "inner_rows": int(len(all_scores)),
                "mean_discrete_crps": float(np.mean(all_scores)),
                "per_target_mean_crps": ";".join(
                    f"{year}:{score:.17g}:{n}" for year, score, n in per_target
                ),
            }
        )

    table = pd.DataFrame(rows)
    best = float(table["mean_discrete_crps"].min())
    tied = table[np.abs(table["mean_discrete_crps"] - best) <= TIE_TOLERANCE].copy()
    candidates = [
        spec
        for spec in specs
        if (
            ((spec.shape is None and tied["shape"].isna()) | (tied["shape"] == spec.shape))
            & (
                (spec.key_penalty is None and tied["key_penalty"].isna())
                | (tied["key_penalty"] == spec.key_penalty)
            )
        ).any()
    ]
    if not candidates:
        raise RuntimeError("Q2 tuning could not resolve a frozen candidate")
    selected = max(candidates, key=_simplicity_key)
    table["selected"] = False
    mask = (
        (table["family"] == selected.family)
        & (table["ablation"] == selected.ablation)
        & (
            table["shape"].isna()
            if selected.shape is None
            else table["shape"].eq(selected.shape)
        )
        & (
            table["key_penalty"].isna()
            if selected.key_penalty is None
            else table["key_penalty"].eq(selected.key_penalty)
        )
    )
    table.loc[mask, "selected"] = True
    return selected, table


def _fit_outer_continuous(
    data: TargetData,
    spec: CandidateSpec,
) -> np.ndarray:
    fit = fit_continuous_distribution(
        data.train,
        data.train_centers,
        family=spec.family,
        shape=spec.shape,
        ablation=spec.ablation,
        key_penalty=spec.key_penalty,
    )
    return predict_continuous_distribution(
        data.target,
        data.target_centers,
        fit,
        enforce_boundary=True,
    )


def generate_q2_outer_oof(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, np.ndarray], pd.DataFrame]:
    """Generate the 12 frozen paired M1/Q2 Stage-B OOF distribution arms."""
    validate_gate_frame(frame)
    metadata_parts: list[pd.DataFrame] = []
    arm_parts: dict[str, list[np.ndarray]] = {}
    tuning_parts: list[pd.DataFrame] = []
    q1_cache: dict[int, object] = {}
    score_cache: dict[tuple, np.ndarray] = {}

    for outer in OUTER_TARGET_SEASONS:
        m1_data = target_data(frame, int(outer), "M1", q1_cache=q1_cache)
        q2_data = target_data(frame, int(outer), "Q2", q1_cache=q1_cache)
        if tuple(m1_data.target["game_id"].astype(str)) != tuple(
            q2_data.target["game_id"].astype(str)
        ):
            raise RuntimeError("Q2 paired M1/Q2 targets are not exact common rows")

        result_cols = [
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
                "ats_outcome",
                "market_evidence_class",
            )
            if c in m1_data.target.columns
        ]
        meta = m1_data.target[result_cols].copy()
        meta["q1_median_alpha"] = q2_data.q1_alpha
        metadata_parts.append(meta)

        for center_mode, data in (("M1", m1_data), ("Q2", q2_data)):
            for arm_suffix, (family, ablation) in ARM_CONFIGS.items():
                selected, tuning = select_spec(
                    frame,
                    outer_target_season=int(outer),
                    center_mode=center_mode,
                    family=family,
                    ablation=ablation,
                    q1_cache=q1_cache,
                    score_cache=score_cache,
                )
                tuning = tuning.copy()
                tuning["arm"] = f"{center_mode}_{arm_suffix}"
                tuning_parts.append(tuning)
                pmf = _fit_outer_continuous(data, selected)
                arm_parts.setdefault(f"{center_mode}_{arm_suffix}", []).append(pmf)

            emp = empirical_residual_pmf(
                pd.to_numeric(data.train["margin"], errors="raise").to_numpy(dtype=float),
                data.train_centers,
                data.target_centers,
            )
            if float(endpoint_mass(emp).max()) > BOUNDARY_MASS_LIMIT:
                raise RuntimeError("Q2 empirical reference exceeded frozen endpoint-mass threshold")
            arm_parts.setdefault(f"{center_mode}_{EMP_ARM}", []).append(emp)

    metadata = pd.concat(metadata_parts, ignore_index=True)
    if metadata["game_id"].astype(str).duplicated().any():
        raise RuntimeError("Q2 outer OOF contains duplicate game_id")
    order = metadata.assign(_row=np.arange(len(metadata))).sort_values(
        ["season", "game_id"], kind="mergesort"
    )["_row"].to_numpy(dtype=int)
    metadata = metadata.iloc[order].reset_index(drop=True)
    arms = {name: np.vstack(parts)[order] for name, parts in arm_parts.items()}
    expected = {
        f"{mode}_{suffix}"
        for mode in ("M1", "Q2")
        for suffix in (*ARM_CONFIGS.keys(), EMP_ARM)
    }
    if set(arms) != expected:
        raise RuntimeError("Q2 historical arm set changed from frozen Stage-B contract")
    for name, pmf in arms.items():
        if len(pmf) != len(metadata):
            raise RuntimeError(f"Q2 arm {name} is not aligned to metadata")
    tuning = pd.concat(tuning_parts, ignore_index=True).sort_values(
        ["outer_target_season", "arm", "mean_discrete_crps", "shape", "key_penalty"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)
    return metadata, arms, tuning
