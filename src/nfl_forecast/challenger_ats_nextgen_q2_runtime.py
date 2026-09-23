from __future__ import annotations

"""Efficient execution of the frozen Q2 rolling-origin contract.

The scientific result is identical to evaluating each outer window independently:
we fit each target-season/configuration pair once, persist its mean CRPS and row
count, and form each outer tuning pool from the strict prefix of prior targets.
No target/future row is reused and no selection criterion is changed.
"""

from dataclasses import asdict

import numpy as np
import pandas as pd

from nfl_forecast.challenger_ats_nextgen_gate import OUTER_TARGET_SEASONS, validate_gate_frame
from nfl_forecast.challenger_ats_nextgen_q2_eval import (
    ABLATIONS,
    PARAMETRIC_FAMILIES,
    TIE_TOLERANCE,
    CenterMode,
    FamilyName,
    Q2Config,
    Q2Selection,
    _center_bundle,
    _config_tie_key,
    _fit_predict_config,
    _output_rows,
    configs_for,
)
from nfl_forecast.challenger_ats_nextgen_q2 import discrete_crps


CenterBundle = tuple[pd.DataFrame, np.ndarray, pd.DataFrame, np.ndarray, dict]


def build_center_cache(frame: pd.DataFrame, center_mode: CenterMode) -> dict[int, CenterBundle]:
    validate_gate_frame(frame)
    return {
        season: _center_bundle(frame, season, center_mode)
        for season in range(2020, max(OUTER_TARGET_SEASONS) + 1)
    }


def precompute_inner_detail(
    frame: pd.DataFrame,
    *,
    center_mode: CenterMode,
    center_cache: dict[int, CenterBundle] | None = None,
) -> pd.DataFrame:
    """Fit each frozen inner target/config exactly once for targets 2020..2024."""
    validate_gate_frame(frame)
    cache = center_cache or build_center_cache(frame, center_mode)
    rows: list[dict] = []
    for target in range(2020, max(OUTER_TARGET_SEASONS)):
        train, train_center, valid, valid_center, center_meta = cache[target]
        y = pd.to_numeric(valid["margin"], errors="raise").to_numpy(dtype=float)
        for family in PARAMETRIC_FAMILIES:
            for ablation in ABLATIONS:
                for config in configs_for(family, ablation):
                    pmf, _ = _fit_predict_config(
                        train, train_center, valid, valid_center, config
                    )
                    score = discrete_crps(pmf, y)
                    rows.append(
                        {
                            "inner_target_season": int(target),
                            "center_mode": center_mode,
                            "family": family,
                            "ablation": ablation,
                            "shape": config.shape,
                            "key_penalty": config.key_penalty,
                            "rows": int(len(valid)),
                            "mean_crps": float(np.mean(score)),
                            **center_meta,
                        }
                    )
    return pd.DataFrame(rows).sort_values(
        [
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


def _same_optional(value: object, expected: float | None) -> bool:
    if expected is None:
        return pd.isna(value)
    return (not pd.isna(value)) and float(value) == float(expected)


def select_from_precomputed(
    detail: pd.DataFrame,
    *,
    outer_target_season: int,
    center_mode: CenterMode,
    family: FamilyName,
    ablation: str,
) -> Q2Selection:
    """Pool only inner targets before ``outer_target_season`` and apply frozen ties."""
    outer = int(outer_target_season)
    if outer not in OUTER_TARGET_SEASONS:
        raise ValueError("Q2 outer target is outside the frozen 2022-2025 set")
    eligible = detail[
        detail["center_mode"].eq(center_mode)
        & detail["family"].eq(family)
        & detail["ablation"].eq(ablation)
        & pd.to_numeric(detail["inner_target_season"], errors="raise").lt(outer)
    ].copy()
    if eligible.empty:
        raise RuntimeError("Q2 has no eligible prior inner detail")

    candidates = configs_for(family, ablation)  # type: ignore[arg-type]
    pooled: dict[Q2Config, float] = {}
    row_counts: dict[Q2Config, int] = {}
    for config in candidates:
        part = eligible[
            eligible.apply(
                lambda r: _same_optional(r["shape"], config.shape)
                and _same_optional(r["key_penalty"], config.key_penalty),
                axis=1,
            )
        ]
        expected_targets = tuple(range(2020, outer))
        got_targets = tuple(
            sorted(pd.to_numeric(part["inner_target_season"], errors="raise").astype(int).tolist())
        )
        if got_targets != expected_targets:
            raise RuntimeError(
                f"Q2 precomputed chronology mismatch for {config}: "
                f"expected={expected_targets} got={got_targets}"
            )
        weights = pd.to_numeric(part["rows"], errors="raise").to_numpy(dtype=float)
        scores = pd.to_numeric(part["mean_crps"], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(weights).all() or not np.isfinite(scores).all() or np.sum(weights) <= 0:
            raise RuntimeError("Q2 precomputed score pool is invalid")
        pooled[config] = float(np.average(scores, weights=weights))
        row_counts[config] = int(np.sum(weights))

    best = min(pooled.values())
    tied = [config for config, value in pooled.items() if abs(value - best) <= TIE_TOLERANCE]
    selected = max(tied, key=_config_tie_key)
    return Q2Selection(
        outer_target_season=outer,
        center_mode=center_mode,
        family=family,
        ablation=ablation,  # type: ignore[arg-type]
        selected_shape=selected.shape,
        selected_key_penalty=selected.key_penalty,
        mean_inner_crps=float(pooled[selected]),
        inner_rows=int(row_counts[selected]),
        inner_targets_used=tuple(range(2020, outer)),
        inner_targets_omitted=(2019,),
    )


def _sort_target_and_pmf(target: pd.DataFrame, pmf: np.ndarray) -> tuple[pd.DataFrame, np.ndarray]:
    ids = target["game_id"].astype(str).to_numpy()
    order = np.argsort(ids, kind="stable")
    ordered_target = target.iloc[order].reset_index(drop=True)
    ordered_pmf = np.asarray(pmf, dtype=float)[order]
    return ordered_target, ordered_pmf


def generate_q2_outer_oof_cached(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, np.ndarray]]:
    """Generate Q2 OOF using one fit per unique inner fold/configuration."""
    validate_gate_frame(frame)
    outputs: list[pd.DataFrame] = []
    selections: list[dict] = []
    pmf_blocks: dict[str, list[np.ndarray]] = {}

    center_caches: dict[str, dict[int, CenterBundle]] = {
        mode: build_center_cache(frame, mode) for mode in ("M1", "Q2")
    }
    inner_detail_by_mode = {
        mode: precompute_inner_detail(
            frame,
            center_mode=mode,  # type: ignore[arg-type]
            center_cache=center_caches[mode],
        )
        for mode in ("M1", "Q2")
    }
    all_inner_detail = pd.concat(
        [inner_detail_by_mode["M1"], inner_detail_by_mode["Q2"]], ignore_index=True
    ).sort_values(
        [
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

    for outer in OUTER_TARGET_SEASONS:
        for center_mode in ("M1", "Q2"):
            train, train_center, target, target_center, center_meta = center_caches[center_mode][
                int(outer)
            ]
            for family in PARAMETRIC_FAMILIES:
                for ablation in ABLATIONS:
                    selection = select_from_precomputed(
                        inner_detail_by_mode[center_mode],
                        outer_target_season=int(outer),
                        center_mode=center_mode,  # type: ignore[arg-type]
                        family=family,
                        ablation=ablation,
                    )
                    config = Q2Config(
                        family,
                        ablation,
                        selection.selected_shape,
                        selection.selected_key_penalty,
                    )
                    pmf, _ = _fit_predict_config(
                        train, train_center, target, target_center, config
                    )
                    ordered_target, ordered_pmf = _sort_target_and_pmf(target, pmf)
                    outputs.append(
                        _output_rows(
                            ordered_target,
                            ordered_pmf,
                            center_mode=center_mode,  # type: ignore[arg-type]
                            family=family,
                            ablation=ablation,
                            shape=config.shape,
                            key_penalty=config.key_penalty,
                        )
                    )
                    selections.append({**asdict(selection), **center_meta})
                    key = f"{center_mode}__{family}__{ablation}"
                    pmf_blocks.setdefault(key, []).append(ordered_pmf)

            emp_config = Q2Config("emp", "empirical", None, None)
            emp_pmf, _ = _fit_predict_config(
                train, train_center, target, target_center, emp_config
            )
            ordered_target, ordered_emp = _sort_target_and_pmf(target, emp_pmf)
            outputs.append(
                _output_rows(
                    ordered_target,
                    ordered_emp,
                    center_mode=center_mode,  # type: ignore[arg-type]
                    family="emp",
                    ablation="empirical",
                    shape=None,
                    key_penalty=None,
                )
            )
            key = f"{center_mode}__emp__empirical"
            pmf_blocks.setdefault(key, []).append(ordered_emp)

    oof = pd.concat(outputs, ignore_index=True).sort_values(
        ["center_mode", "family", "ablation", "season", "game_id"], kind="mergesort"
    ).reset_index(drop=True)
    selection_frame = pd.DataFrame(selections).sort_values(
        ["outer_target_season", "center_mode", "family", "ablation"], kind="mergesort"
    ).reset_index(drop=True)
    pmfs = {key: np.vstack(parts) for key, parts in pmf_blocks.items()}
    return oof, selection_frame, all_inner_detail, pmfs
