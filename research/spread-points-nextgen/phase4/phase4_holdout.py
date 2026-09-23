from __future__ import annotations

"""One-time 2025 holdout runner for frozen Spread & Points A0/B0/C0.

This module does not alter the frozen Phase 3 implementation. It verifies the
Phase 3 implementation/config hashes first, then installs a narrow Phase 4
runtime authorization that permits target season 2025 while continuing to
block 2026+. The modeling, feature, tuning, simulation and market-residual
functions remain the exact frozen Phase 3 functions.

The full holdout run computes all candidate outputs and evaluation objects in
memory before any result file is written. This prevents an engineering failure
from leaving a selectively inspectable partial result package.
"""

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
from typing import Iterable

import numpy as np
import pandas as pd

from nfl_forecast.data import load_core_data

from ..phase3 import phase3_a0 as a0_mod
from ..phase3 import phase3_b0 as b0_mod
from ..phase3 import phase3_c0 as c0_mod
from ..phase3 import phase3_data as data_mod
from ..phase3 import phase3_scaffold as scaffold
from ..phase3 import run_phase3 as phase3_runner
from ..phase3.phase3_evaluation import (
    attach_market,
    baseline_metrics,
    build_baselines,
    diagnostic_slices,
    evaluate_a0,
    evaluate_b0,
    evaluate_c0,
    market_relative,
)

ROOT = Path(__file__).resolve().parent
PROGRAM_ROOT = ROOT.parent
PHASE3_ROOT = PROGRAM_ROOT / "phase3"
OPENING_RECEIPT = ROOT / "HOLDOUT_OPENING_RECEIPT.json"
CANDIDATE_REGISTRY = PHASE3_ROOT / "CANDIDATE_REGISTRY.json"
PHASE3_MANIFEST = PHASE3_ROOT / "evidence" / "RUN_MANIFEST.json"
D_RECEIPT = PHASE3_ROOT / "evidence" / "D_ELIGIBILITY_RECEIPT.json"
PHASE1_SUMMARY = PROGRAM_ROOT / "phase1" / "PHASE1_SUMMARY.json"

FROZEN_IMPLEMENTATION_SHA256 = "5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579"
FROZEN_CONFIG_SHA256 = "2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543"
OPENING_RECEIPT_COMMIT = "362af7af7db43a715b9ab9537a52d2749c37e7a6"
TARGET_SEASON = 2025
BOOTSTRAP_RESAMPLES = 10_000
B0_SIMULATIONS = 10_000
A0_ID = scaffold.A0_ID
B0_ID = scaffold.B0_ID
C0_ID = scaffold.C0_ID
MARKET_LABEL = scaffold.MARKET_HORIZON_LABEL
SOURCE_CONTRACT = scaffold.SOURCE_CONTRACT_VERSION


class Phase4HoldoutError(RuntimeError):
    pass


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN"


def _sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _phase4_guard_target_seasons(seasons: Iterable[int]) -> tuple[int, ...]:
    vals = tuple(int(s) for s in seasons)
    if not vals:
        raise Phase4HoldoutError("Phase 4 requires a target season")
    if any(s < scaffold.TRAINING_FLOOR for s in vals):
        raise Phase4HoldoutError("target predates frozen 2016 training floor")
    bad = sorted(s for s in vals if s >= 2026)
    if bad:
        raise Phase4HoldoutError(f"completed-2026-or-later outcomes remain blocked: {bad}")
    if any(s > TARGET_SEASON for s in vals):
        raise Phase4HoldoutError("Phase 4 authorization extends only through 2025")
    return vals


def _phase4_assert_loaded_universe(frame: pd.DataFrame, *, season_col: str = "season") -> None:
    seasons = pd.to_numeric(frame[season_col], errors="coerce").dropna().astype(int)
    if seasons.empty:
        raise Phase4HoldoutError("loaded universe has no seasons")
    if int(seasons.min()) < scaffold.TRAINING_FLOOR:
        raise Phase4HoldoutError("loaded pre-2016 rows")
    if (seasons >= 2026).any():
        seen = sorted(seasons[seasons >= 2026].unique().tolist())
        raise Phase4HoldoutError(f"2026+ firewall breached: {seen}")


def _phase4_assert_prediction_receipt(frame: pd.DataFrame, candidate_id: str) -> None:
    required = {
        "game_id",
        "season",
        "week",
        "home_team",
        "away_team",
        "candidate_id",
        "outer_target_season",
        "train_through_season",
        "source_contract_version",
        "code_sha",
        "config_sha",
        "fallback_state",
    }
    missing = required - set(frame.columns)
    if missing:
        raise Phase4HoldoutError(f"{candidate_id}: prediction receipt missing {sorted(missing)}")
    if not frame["candidate_id"].eq(candidate_id).all():
        raise Phase4HoldoutError(f"{candidate_id}: candidate identity drift")
    seasons = pd.to_numeric(frame["season"], errors="coerce")
    if seasons.ge(2026).any():
        raise Phase4HoldoutError(f"{candidate_id}: 2026+ prediction row")
    target = pd.to_numeric(frame["outer_target_season"], errors="coerce")
    train_through = pd.to_numeric(frame["train_through_season"], errors="coerce")
    if not (train_through < target).all():
        raise Phase4HoldoutError(f"{candidate_id}: invalid training boundary")
    if not frame["code_sha"].astype(str).eq(FROZEN_IMPLEMENTATION_SHA256).all():
        raise Phase4HoldoutError(f"{candidate_id}: implementation hash drift in receipt")
    if not frame["config_sha"].astype(str).eq(FROZEN_CONFIG_SHA256).all():
        raise Phase4HoldoutError(f"{candidate_id}: config hash drift in receipt")
    if not frame["source_contract_version"].astype(str).eq(SOURCE_CONTRACT).all():
        raise Phase4HoldoutError(f"{candidate_id}: source contract drift")


@contextmanager
def _phase4_authorization():
    """Narrowly authorize 2025 without editing or weakening Phase 3 source code."""
    patches = [
        (a0_mod, "guard_phase3_target_seasons", _phase4_guard_target_seasons),
        (b0_mod, "guard_phase3_target_seasons", _phase4_guard_target_seasons),
        (c0_mod, "guard_phase3_target_seasons", _phase4_guard_target_seasons),
        (a0_mod, "assert_prediction_receipt", _phase4_assert_prediction_receipt),
        (b0_mod, "assert_prediction_receipt", _phase4_assert_prediction_receipt),
        (c0_mod, "assert_prediction_receipt", _phase4_assert_prediction_receipt),
        (data_mod, "assert_phase3_loaded_universe", _phase4_assert_loaded_universe),
    ]
    previous = [(module, name, getattr(module, name)) for module, name, _ in patches]
    try:
        for module, name, replacement in patches:
            setattr(module, name, replacement)
        yield
    finally:
        for module, name, original in previous:
            setattr(module, name, original)


def verify_frozen_contracts() -> dict:
    """Pre-holdout verification. This function does not load 2025 data."""
    if not OPENING_RECEIPT.exists():
        raise Phase4HoldoutError("holdout opening receipt is missing")
    opening = _read_json(OPENING_RECEIPT)
    if opening.get("holdout_state_at_receipt") != "UNOPENED":
        raise Phase4HoldoutError("opening receipt does not establish an unopened boundary")
    if opening.get("target_season") != TARGET_SEASON:
        raise Phase4HoldoutError("opening receipt target season drift")
    if opening.get("implementation_sha256") != FROZEN_IMPLEMENTATION_SHA256:
        raise Phase4HoldoutError("opening receipt implementation hash drift")
    if opening.get("config_sha256") != FROZEN_CONFIG_SHA256:
        raise Phase4HoldoutError("opening receipt config hash drift")

    current_code_hash = phase3_runner._code_hash()
    current_config_hash = phase3_runner._config_hash()
    if current_code_hash != FROZEN_IMPLEMENTATION_SHA256:
        raise Phase4HoldoutError(
            f"frozen Phase 3 implementation changed: {current_code_hash}"
        )
    if current_config_hash != FROZEN_CONFIG_SHA256:
        raise Phase4HoldoutError(f"frozen Phase 3 config changed: {current_config_hash}")

    registry = _read_json(CANDIDATE_REGISTRY)
    candidates = registry["candidates"]
    expected = {"A0": A0_ID, "B0": B0_ID, "C0": C0_ID}
    for key, candidate_id in expected.items():
        if candidates[key]["id"] != candidate_id:
            raise Phase4HoldoutError(f"{key} registry identity drift")
    if int(candidates["B0"]["simulation_draws"]) < B0_SIMULATIONS:
        raise Phase4HoldoutError("B0 final simulation contract fell below 10,000")
    if candidates["B0"].get("consumes_a0") is not False:
        raise Phase4HoldoutError("B0 independence contract drift")
    if candidates["C0"].get("football_base") != "A0":
        raise Phase4HoldoutError("C0 football base is not frozen A0")
    if candidates["C0"].get("market_horizon_label") != MARKET_LABEL:
        raise Phase4HoldoutError("C0 market horizon label drift")
    if candidates["C0"].get("null_hierarchy") != ["M0", "M1", "M2", "M3"]:
        raise Phase4HoldoutError("C0 null hierarchy drift")

    manifest = _read_json(PHASE3_MANIFEST)
    if manifest.get("2025_loaded") is not False or manifest.get("2025_challenger_scored") is not False:
        raise Phase4HoldoutError("Phase 3 manifest says 2025 was already opened")
    if manifest.get("candidate5_trained") is not False:
        raise Phase4HoldoutError("Candidate 5 was trained before Phase 4")
    if manifest.get("completed_2026_outcomes_used") is not False:
        raise Phase4HoldoutError("completed 2026 outcomes entered Phase 3 selection")
    if manifest.get("market_horizon_label") != MARKET_LABEL:
        raise Phase4HoldoutError("Phase 3 market horizon label drift")

    d = _read_json(D_RECEIPT)
    if d["margin"].get("disposition") != "ENSEMBLE_NOT_ELIGIBLE":
        raise Phase4HoldoutError("D margin unexpectedly eligible")
    if d["total"].get("disposition") != "ENSEMBLE_NOT_ELIGIBLE":
        raise Phase4HoldoutError("D total unexpectedly eligible")

    # Prove the original Phase 3 firewall was not weakened.
    try:
        scaffold.guard_phase3_target_seasons([2025])
    except scaffold.Phase3FirewallError:
        pass
    else:
        raise Phase4HoldoutError("original Phase 3 2025 firewall no longer fails closed")

    # Sign convention sanity check from the frozen contract.
    check = scaffold.canonical_targets(
        pd.DataFrame({"home_score": [27.0], "away_score": [20.0]})
    )
    if float(check.loc[0, "actual_margin"]) != 7.0 or float(check.loc[0, "actual_total"]) != 47.0:
        raise Phase4HoldoutError("canonical sign/target convention drift")

    # Phase 4 guard is intentionally narrow and still blocks 2026.
    if _phase4_guard_target_seasons([2025]) != (2025,):
        raise Phase4HoldoutError("Phase 4 2025 authorization failed")
    try:
        _phase4_guard_target_seasons([2026])
    except Phase4HoldoutError:
        pass
    else:
        raise Phase4HoldoutError("Phase 4 completed-2026 firewall failed")

    return {
        "status": "PASS",
        "implementation_sha256": current_code_hash,
        "config_sha256": current_config_hash,
        "candidate_ids": expected,
        "D_margin": "ENSEMBLE_NOT_ELIGIBLE",
        "D_total": "ENSEMBLE_NOT_ELIGIBLE",
        "market_horizon_label": MARKET_LABEL,
        "source_contract": SOURCE_CONTRACT,
        "B0_simulations": B0_SIMULATIONS,
        "candidate5_trained": False,
        "completed_2026_used": False,
        "phase3_2025_firewall_intact": True,
    }


def _load_phase4_data() -> data_mod.Phase3Data:
    seasons = list(range(scaffold.TRAINING_FLOOR, TARGET_SEASON + 1))
    bundle = load_core_data(seasons)

    schedules = bundle.schedules.copy()
    if "game_type" in schedules.columns:
        schedules = schedules[schedules["game_type"].eq("REG")].copy()
    elif "season_type" in schedules.columns:
        schedules = schedules[schedules["season_type"].eq("REG")].copy()
    schedules["season"] = pd.to_numeric(schedules["season"], errors="coerce")
    schedules["week"] = pd.to_numeric(schedules["week"], errors="coerce")
    schedules = schedules[schedules["season"].between(2016, 2025, inclusive="both")].copy()
    if "gameday" in schedules.columns:
        schedules["gameday"] = pd.to_datetime(schedules["gameday"], errors="coerce")
    schedules = scaffold.canonical_targets(schedules)
    _phase4_assert_loaded_universe(schedules)

    pbp = bundle.pbp.copy()
    if "season_type" in pbp.columns:
        pbp = pbp[pbp["season_type"].eq("REG")].copy()
    pbp["season"] = pd.to_numeric(pbp["season"], errors="coerce")
    pbp = pbp[pbp["season"].between(2016, 2025, inclusive="both")].copy()
    _phase4_assert_loaded_universe(pbp)

    with _phase4_authorization():
        team_states = data_mod.build_team_states(pbp, schedules)
        a0_team_rows = data_mod.build_a0_team_rows(team_states)
        drives = data_mod.build_drive_table(pbp, schedules)
        b0_team_rows, b0_outcome_rows = data_mod.build_b0_frames(
            drives, team_states, schedules
        )
        rare_points = data_mod.build_rare_points(pbp, schedules)
    return data_mod.Phase3Data(
        schedules=schedules,
        pbp=pbp,
        team_states=team_states,
        a0_team_rows=a0_team_rows,
        drives=drives,
        b0_team_rows=b0_team_rows,
        b0_outcome_rows=b0_outcome_rows,
        rare_points=rare_points,
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    ordered = frame.copy()
    if {"season", "week", "game_id"}.issubset(ordered.columns):
        ordered = ordered.sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    ordered.to_csv(path, index=False, lineterminator="\n")


def _probability_tie_excluded(frame: pd.DataFrame) -> dict:
    actual_margin = pd.to_numeric(frame["actual_margin"], errors="coerce")
    p = pd.to_numeric(frame["home_win_probability"], errors="coerce")
    mask = actual_margin.notna() & p.notna() & actual_margin.ne(0) & np.isfinite(p)
    y = (actual_margin.loc[mask] > 0).astype(int).to_numpy()
    prob = np.clip(p.loc[mask].to_numpy(dtype=float), 1e-12, 1.0 - 1e-12)
    if not len(y):
        return {"games": 0, "excluded_ties": int(actual_margin.eq(0).sum())}
    pred = (prob >= 0.5).astype(int)
    brier = float(np.mean((prob - y) ** 2))
    logloss = float(-np.mean(y * np.log(prob) + (1 - y) * np.log(1 - prob)))
    return {
        "games": int(len(y)),
        "excluded_ties": int(actual_margin.eq(0).sum()),
        "winner_accuracy": float(np.mean(pred == y)),
        "brier": brier,
        "log_loss": logloss,
    }


def _a0_extra_distribution_metrics(frame: pd.DataFrame) -> dict:
    nll_margin: list[float] = []
    nll_total: list[float] = []
    joint_nll: list[float] = []
    energy: list[float] = []
    for _, row in frame.iterrows():
        var_h = float(row["cov_home_var"])
        var_a = float(row["cov_away_var"])
        cov_ha = float(row["cov_home_away"])
        cov = np.array([[var_h, cov_ha], [cov_ha, var_a]], dtype=float)
        margin_var = max(var_h + var_a - 2.0 * cov_ha, 1e-9)
        total_var = max(var_h + var_a + 2.0 * cov_ha, 1e-9)
        em = float(row["expected_margin"])
        et = float(row["expected_total"])
        am = float(row["actual_margin"])
        at = float(row["actual_total"])
        nll_margin.append(
            0.5 * (math.log(2.0 * math.pi * margin_var) + (am - em) ** 2 / margin_var)
        )
        nll_total.append(
            0.5 * (math.log(2.0 * math.pi * total_var) + (at - et) ** 2 / total_var)
        )
        y = np.array([float(row["home_score"]), float(row["away_score"])], dtype=float)
        mu = np.array(
            [float(row["expected_home_points"]), float(row["expected_away_points"])],
            dtype=float,
        )
        sign, logdet = np.linalg.slogdet(cov)
        if sign > 0:
            diff = y - mu
            joint_nll.append(
                float(math.log(2.0 * math.pi) + 0.5 * logdet + 0.5 * diff.T @ np.linalg.solve(cov, diff))
            )
        seed = scaffold.stable_seed(A0_ID, str(row["game_id"]))
        rng = np.random.default_rng(seed)
        sims = rng.multivariate_normal(mu, cov, size=B0_SIMULATIONS)
        energy.append(
            scaffold.empirical_energy_score(
                y[0], y[1], sims, seed=seed
            )
        )
    return {
        "margin_log_score_negative_log_density": float(np.mean(nll_margin)),
        "total_log_score_negative_log_density": float(np.mean(nll_total)),
        "joint_gaussian_log_score_negative_log_density": float(np.mean(joint_nll)) if joint_nll else None,
        "joint_energy_score_monte_carlo": float(np.mean(energy)),
        "joint_energy_draws_per_game": B0_SIMULATIONS,
        "joint_energy_seed_policy": "stable_seed(A0_ID, game_id, base_seed=2603)",
    }


def _paired_uncertainty(
    frame: pd.DataFrame,
    actual_col: str,
    candidate_col: str,
    reference_col: str,
    seed: int,
) -> dict:
    work = frame[["season", "week", actual_col, candidate_col, reference_col]].dropna().copy()
    cand_err = np.abs(work[actual_col].to_numpy(float) - work[candidate_col].to_numpy(float))
    ref_err = np.abs(work[actual_col].to_numpy(float) - work[reference_col].to_numpy(float))
    return scaffold.season_week_block_bootstrap(
        work,
        cand_err,
        ref_err,
        samples=BOOTSTRAP_RESAMPLES,
        seed=seed,
    )


def _ats_ou_diagnostics(frame: pd.DataFrame, pred_margin: str, pred_total: str) -> dict:
    out: dict[str, dict] = {}
    if "market_margin" in frame.columns:
        work = frame[["actual_margin", "market_margin", pred_margin]].dropna().copy()
        model_edge = work[pred_margin] - work["market_margin"]
        realized_edge = work["actual_margin"] - work["market_margin"]
        mask = ~np.isclose(model_edge, 0.0) & ~np.isclose(realized_edge, 0.0)
        out["ATS"] = {
            "graded_games": int(mask.sum()),
            "pushes_excluded": int(np.isclose(realized_edge, 0.0).sum()),
            "no_edge_excluded": int(np.isclose(model_edge, 0.0).sum()),
            "hit_rate": float(np.mean(np.sign(model_edge[mask]) == np.sign(realized_edge[mask]))) if mask.any() else None,
            "role": "secondary_diagnostic_only",
        }
    if "market_total" in frame.columns:
        work = frame[["actual_total", "market_total", pred_total]].dropna().copy()
        model_edge = work[pred_total] - work["market_total"]
        realized_edge = work["actual_total"] - work["market_total"]
        mask = ~np.isclose(model_edge, 0.0) & ~np.isclose(realized_edge, 0.0)
        out["OU"] = {
            "graded_games": int(mask.sum()),
            "pushes_excluded": int(np.isclose(realized_edge, 0.0).sum()),
            "no_edge_excluded": int(np.isclose(model_edge, 0.0).sum()),
            "hit_rate": float(np.mean(np.sign(model_edge[mask]) == np.sign(realized_edge[mask]))) if mask.any() else None,
            "role": "secondary_diagnostic_only",
        }
    return out


def _c0_holdout_incremental(c0: pd.DataFrame) -> dict:
    margin = _paired_uncertainty(c0, "actual_margin", "m3_margin", "m0_margin", 26031)
    total = _paired_uncertainty(c0, "actual_total", "m3_total", "m0_total", 26032)
    return {
        "question": "Does frozen C0 M3 add incremental information beyond raw market M0 on exact 2025 holdout rows?",
        "margin": {
            "M3_minus_M0_MAE": margin.get("candidate_minus_reference_mean"),
            "ci95": margin.get("ci95"),
            "probability_M3_lower_absolute_error": margin.get("probability_candidate_lower"),
            "games": margin.get("games"),
            "blocks": margin.get("blocks"),
            "samples": margin.get("samples"),
        },
        "total": {
            "M3_minus_M0_MAE": total.get("candidate_minus_reference_mean"),
            "ci95": total.get("ci95"),
            "probability_M3_lower_absolute_error": total.get("probability_candidate_lower"),
            "games": total.get("games"),
            "blocks": total.get("blocks"),
            "samples": total.get("samples"),
        },
        "interpretation_policy": "No post-hoc threshold. Nominal direction, uncertainty, development consistency and complexity are interpreted together after the complete holdout package exists.",
    }


def _row_counts(a0: pd.DataFrame, b0: pd.DataFrame, c0: pd.DataFrame, baselines: pd.DataFrame) -> dict:
    sets = {name: set(frame["game_id"].astype(str)) for name, frame in (("A0", a0), ("B0", b0), ("C0", c0), ("baselines", baselines))}
    return {
        "A0": int(len(a0)),
        "B0": int(len(b0)),
        "C0": int(len(c0)),
        "baselines": int(len(baselines)),
        "A0_B0_C0_common": int(len(sets["A0"] & sets["B0"] & sets["C0"])),
        "A0_market_common": int(a0["market_margin"].notna().sum()) if "market_margin" in a0 else 0,
        "B0_market_common": int(b0["market_margin"].notna().sum()) if "market_margin" in b0 else 0,
        "C0_market_common": int(c0["market_margin"].notna().sum()),
    }


def _development_reference() -> dict:
    return {
        "games": 815,
        "seasons": [2022, 2023, 2024],
        "A0_margin_mae": 9.882508546957865,
        "A0_total_mae": 10.386912200041253,
        "B0_margin_mae": 10.21317018404908,
        "B0_total_mae": 11.30440920245399,
        "C0_M3_margin_mae": 9.43895668195999,
        "C0_M3_total_mae": 10.13763752934022,
        "market_M0_margin_mae": 9.4184,
        "market_M0_total_mae": 10.1209,
        "C0_margin_disposition": "NO_INCREMENTAL_FOOTBALL_EDGE",
        "C0_total_disposition": "NO_INCREMENTAL_FOOTBALL_EDGE",
        "D_margin": "ENSEMBLE_NOT_ELIGIBLE",
        "D_total": "ENSEMBLE_NOT_ELIGIBLE",
    }


def _sanitize(value):
    return scaffold.sanitize_json(value)


def run_holdout(output_dir: Path, *, simulations: int = B0_SIMULATIONS) -> dict:
    if int(simulations) < B0_SIMULATIONS:
        raise Phase4HoldoutError("final B0 holdout requires at least 10,000 simulations/game")

    preflight = verify_frozen_contracts()

    # HOLDOUT OPENS HERE. Do not print or write candidate-specific results until
    # the entire frozen A0/B0/C0/evaluation package has completed in memory.
    data = _load_phase4_data()
    target_schedule = data.schedules[
        data.schedules["season"].eq(TARGET_SEASON)
        & data.schedules["home_score"].notna()
        & data.schedules["away_score"].notna()
    ].copy()
    if target_schedule.empty:
        raise Phase4HoldoutError("2025 regular-season holdout contains no completed games")

    with _phase4_authorization():
        a0_all, a0_receipts = a0_mod.generate_a0_oof(
            data.a0_team_rows,
            tuple(range(2017, TARGET_SEASON + 1)),
            code_sha=FROZEN_IMPLEMENTATION_SHA256,
            config_sha=FROZEN_CONFIG_SHA256,
        )
        a0 = a0_all[a0_all["season"].eq(TARGET_SEASON)].copy().reset_index(drop=True)

        b0, b0_receipt = b0_mod.fit_predict_b0_outer(
            data.b0_team_rows,
            data.b0_outcome_rows,
            data.drives,
            data.rare_points,
            data.schedules,
            TARGET_SEASON,
            code_sha=FROZEN_IMPLEMENTATION_SHA256,
            config_sha=FROZEN_CONFIG_SHA256,
            simulations=int(simulations),
        )

        cframe = c0_mod.build_c0_frame(a0_all, data.schedules)
        c0, c0_receipt = c0_mod.fit_predict_c0_outer(
            cframe,
            TARGET_SEASON,
            code_sha=FROZEN_IMPLEMENTATION_SHA256,
            config_sha=FROZEN_CONFIG_SHA256,
        )

    _phase4_assert_prediction_receipt(a0, A0_ID)
    _phase4_assert_prediction_receipt(b0, B0_ID)
    _phase4_assert_prediction_receipt(c0, C0_ID)
    for frame, name in ((a0, "A0"), (b0, "B0"), (c0, "C0")):
        if not frame["season"].eq(TARGET_SEASON).all():
            raise Phase4HoldoutError(f"{name}: non-2025 row escaped holdout surface")
        if not frame["train_through_season"].eq(2024).all():
            raise Phase4HoldoutError(f"{name}: model fitting boundary is not 2024")

    a0_market = attach_market(a0, data.schedules)
    b0_market = attach_market(b0, data.schedules)
    if not c0["market_horizon_label"].astype(str).eq(MARKET_LABEL).all():
        raise Phase4HoldoutError("C0 emitted a non-frozen market horizon label")

    baselines = build_baselines(data.schedules, data.team_states, (TARGET_SEASON,))
    baselines = baselines[baselines["season"].eq(TARGET_SEASON)].copy().reset_index(drop=True)

    a0_eval = evaluate_a0(a0)
    a0_eval["probability_tie_excluded"] = _probability_tie_excluded(a0)
    a0_eval["distribution"].update(_a0_extra_distribution_metrics(a0))
    a0_eval["market_relative"] = market_relative(a0_market, "expected_margin", "expected_total")
    a0_eval["ATS_OU"] = _ats_ou_diagnostics(a0_market, "expected_margin", "expected_total")

    b0_eval = evaluate_b0(b0)
    b0_eval["probability_tie_excluded"] = _probability_tie_excluded(b0)
    b0_eval["market_relative"] = market_relative(b0_market, "expected_margin", "expected_total")
    b0_eval["ATS_OU"] = _ats_ou_diagnostics(b0_market, "expected_margin", "expected_total")

    c0_eval = evaluate_c0(c0)
    c0_eval["market_relative_M3"] = market_relative(c0, "m3_margin", "m3_total")
    c0_eval["incremental_M3_vs_M0"] = _c0_holdout_incremental(c0)
    c0_eval["ATS_OU_M3"] = _ats_ou_diagnostics(c0, "m3_margin", "m3_total")

    base_eval = baseline_metrics(baselines)

    diag_parts: list[pd.DataFrame] = []
    for candidate, frame, pm, pt in (
        (A0_ID, a0_market, "expected_margin", "expected_total"),
        (B0_ID, b0_market, "expected_margin", "expected_total"),
        (C0_ID, c0, "m3_margin", "m3_total"),
    ):
        part = diagnostic_slices(frame, pm, pt)
        part.insert(0, "candidate_id", candidate)
        diag_parts.append(part)
    diagnostics = pd.concat(diag_parts, ignore_index=True)

    counts = _row_counts(a0_market, b0_market, c0, baselines)
    summary = {
        "schema_version": "spread-points-phase4-holdout-summary-v1",
        "phase": 4,
        "evidence_scope": "2025 final historical challenger holdout; broad baseline 2025 errors had informed earlier research questions, but no A0/B0/C0 challenger output was inspected before Phase 4",
        "target_season": TARGET_SEASON,
        "holdout_opened": True,
        "candidate_ids": {"A0": A0_ID, "B0": B0_ID, "C0": C0_ID},
        "D": {"margin": "ENSEMBLE_NOT_ELIGIBLE", "total": "ENSEMBLE_NOT_ELIGIBLE"},
        "row_counts": counts,
        "A0": a0_eval,
        "B0": b0_eval,
        "C0": c0_eval,
        "baselines": base_eval,
        "development_reference": _development_reference(),
        "phase1_current_levline_context": _read_json(PHASE1_SUMMARY).get("baseline") if PHASE1_SUMMARY.exists() else None,
        "phase1_context_note": "Phase 1 LevLine baseline context is not substituted for a chronology-clean exact-row 2025 F-ST comparator. No 2025 F-ST artifact trained with 2025 outcomes is scored as out-of-sample here.",
        "FST_2025_OOS_comparator": "NOT_INCLUDED_UNLESS_EXISTING_CHRONOLOGY_CLEAN_REPRESENTATION_IS_ESTABLISHED; production F-ST is not re-fit or backcast in Phase 4",
        "Candidate5": "NOT_STARTED",
        "candidate5_trained": False,
        "completed_2026_outcomes_used": False,
        "production_model": "F-ST-01-FROZEN-2026",
        "production_changed": False,
        "finalist_disposition": "PENDING_POST_PACKAGE_INTERPRETATION",
    }

    run_manifest = {
        "schema_version": "spread-points-phase4-run-manifest-v1",
        "generator_git_head": _git_sha(),
        "opening_receipt_commit": OPENING_RECEIPT_COMMIT,
        "holdout_description": "final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions",
        "loaded_seasons": list(range(2016, 2026)),
        "model_fit_training_seasons": list(range(2016, 2025)),
        "target_season": TARGET_SEASON,
        "target_feature_state_note": "Frozen shifted pregame states may update sequentially from prior completed 2025 games; no current-game or future 2025 outcome enters its own forecast, and estimator fitting remains through 2024 only.",
        "eligible_game_counts": counts,
        "candidate_ids": {"A0": A0_ID, "B0": B0_ID, "C0": C0_ID},
        "D_margin": "ENSEMBLE_NOT_ELIGIBLE",
        "D_total": "ENSEMBLE_NOT_ELIGIBLE",
        "implementation_sha256": FROZEN_IMPLEMENTATION_SHA256,
        "config_sha256": FROZEN_CONFIG_SHA256,
        "source_contract": SOURCE_CONTRACT,
        "market_horizon_label": MARKET_LABEL,
        "B0_simulations_per_game": int(simulations),
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "bootstrap_block": "season+week; target season 2025 means week is operative resampling block",
        "random_seeds": {"base": 2603, "market_margin": 26031, "market_total": 26032},
        "2025_opened": True,
        "candidate5_trained": False,
        "completed_2026_outcomes_used": False,
        "production_changed": False,
        "preflight": preflight,
        "candidate_run_receipts": {
            "A0_2025": next((x for x in a0_receipts if int(x.get("target_season", -1)) == TARGET_SEASON), None),
            "B0_2025": b0_receipt,
            "C0_2025": c0_receipt,
        },
    }

    # Only now, after the complete frozen package exists in memory, persist it.
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(a0, output_dir / "A0_HOLDOUT_2025.csv")
    _write_csv(b0, output_dir / "B0_HOLDOUT_2025.csv")
    _write_csv(c0, output_dir / "C0_HOLDOUT_2025.csv")
    _write_csv(baselines, output_dir / "BASELINES_HOLDOUT_2025.csv")
    _write_csv(diagnostics, output_dir / "DIAGNOSTIC_SLICES_2025.csv")
    scaffold.write_json(output_dir / "HOLDOUT_SUMMARY.json", _sanitize(summary))

    evidence_files = [
        "A0_HOLDOUT_2025.csv",
        "B0_HOLDOUT_2025.csv",
        "C0_HOLDOUT_2025.csv",
        "BASELINES_HOLDOUT_2025.csv",
        "DIAGNOSTIC_SLICES_2025.csv",
        "HOLDOUT_SUMMARY.json",
    ]
    run_manifest["evidence_sha256"] = {
        name: _sha256_file(output_dir / name) for name in evidence_files
    }
    scaffold.write_json(output_dir / "HOLDOUT_RUN_MANIFEST.json", _sanitize(run_manifest))

    print("PHASE4_HOLDOUT_PACKAGE_COMPLETE")
    print(f"target_season={TARGET_SEASON}")
    print(f"A0_games={counts['A0']} B0_games={counts['B0']} C0_games={counts['C0']}")
    print("candidate5_trained=false completed_2026_used=false production_changed=false")
    return _sanitize(summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/levline-phase4"))
    parser.add_argument("--simulations", type=int, default=B0_SIMULATIONS)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        result = verify_frozen_contracts()
        print("PHASE4_PREFLIGHT_PASS")
        print(f"implementation_sha256={result['implementation_sha256']}")
        print(f"config_sha256={result['config_sha256']}")
        return
    run_holdout(args.output_dir, simulations=args.simulations)


if __name__ == "__main__":
    main()
