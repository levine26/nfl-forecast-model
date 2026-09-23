from __future__ import annotations

"""Execute the one-time 2025 Spread & Points Phase 4 historical holdout.

The pre-result opening receipt must already be committed.  This runner verifies
that the Phase 3 implementation/config hashes are unchanged, authorizes only the
frozen A0/B0/C0 implementation through 2025, and evaluates the complete frozen
package without modifying any estimator, feature, hyperparameter grid, threshold,
or production surface.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.data import load_core_data

from ..phase3 import phase3_data
from ..phase3.phase3_a0 import generate_a0_oof
from ..phase3.phase3_b0 import fit_predict_b0_outer
from ..phase3.phase3_c0 import build_c0_frame, fit_predict_c0_outer
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
from ..phase3.phase3_scaffold import (
    A0_ID,
    B0_ID,
    B0_SIMULATIONS,
    C0_ID,
    MARKET_HORIZON_LABEL,
    SOURCE_CONTRACT_VERSION,
    git_sha,
    probability_metrics,
    sanitize_json,
    season_week_block_bootstrap,
    write_json,
)
from .phase4_adapter import (
    FROZEN_CONFIG_SHA256,
    FROZEN_IMPLEMENTATION_SHA256,
    HOLDOUT_SEASON,
    assert_phase4_loaded_universe,
    assert_phase4_prediction_receipt,
    authorize_frozen_phase4_execution,
    verify_frozen_hashes,
)

ROOT = Path(__file__).resolve().parent
PROGRAM_ROOT = ROOT.parent
OPENING_RECEIPT = ROOT / "HOLDOUT_OPENING_RECEIPT.json"
PHASE3_D_RECEIPT = PROGRAM_ROOT / "phase3" / "evidence" / "D_ELIGIBILITY_RECEIPT.json"
PHASE3_FUTURE_SURFACE = PROGRAM_ROOT / "phase3" / "evidence" / "FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv"
TARGET = 2025
BOOTSTRAP_SAMPLES = 10_000


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_opening_boundary() -> dict:
    if not OPENING_RECEIPT.exists():
        raise RuntimeError("Phase 4 opening receipt is missing")
    receipt = _read_json(OPENING_RECEIPT)
    if receipt.get("holdout_state_at_receipt") != "UNOPENED":
        raise RuntimeError("opening receipt does not record an unopened holdout")
    if int(receipt.get("target_season", -1)) != TARGET:
        raise RuntimeError("opening receipt target is not 2025")
    if receipt.get("implementation_sha256") != FROZEN_IMPLEMENTATION_SHA256:
        raise RuntimeError("opening receipt implementation hash mismatch")
    if receipt.get("config_sha256") != FROZEN_CONFIG_SHA256:
        raise RuntimeError("opening receipt config hash mismatch")
    if receipt.get("Candidate5_trained") is not False:
        raise RuntimeError("opening receipt does not preserve Candidate 5 firewall")
    if receipt.get("completed_2026_outcomes_used") is not False:
        raise RuntimeError("opening receipt does not preserve completed-2026 firewall")
    if receipt.get("production_changed") is not False:
        raise RuntimeError("opening receipt does not preserve production firewall")
    return receipt


def _load_phase4_data():
    seasons = list(range(2016, 2026))
    bundle = load_core_data(seasons)
    schedules = bundle.schedules.copy()
    if "game_type" in schedules.columns:
        schedules = schedules[schedules["game_type"].eq("REG")].copy()
    elif "season_type" in schedules.columns:
        schedules = schedules[schedules["season_type"].eq("REG")].copy()
    schedules["season"] = pd.to_numeric(schedules["season"], errors="coerce")
    schedules["week"] = pd.to_numeric(schedules["week"], errors="coerce")
    schedules = schedules[schedules["season"].between(2016, TARGET, inclusive="both")].copy()
    if "gameday" in schedules.columns:
        schedules["gameday"] = pd.to_datetime(schedules["gameday"], errors="coerce")
    schedules = schedules.drop_duplicates("game_id").copy()
    schedules["actual_margin"] = pd.to_numeric(schedules["home_score"], errors="coerce") - pd.to_numeric(schedules["away_score"], errors="coerce")
    schedules["actual_total"] = pd.to_numeric(schedules["home_score"], errors="coerce") + pd.to_numeric(schedules["away_score"], errors="coerce")
    assert_phase4_loaded_universe(schedules)

    pbp = bundle.pbp.copy()
    if "season_type" in pbp.columns:
        pbp = pbp[pbp["season_type"].eq("REG")].copy()
    pbp["season"] = pd.to_numeric(pbp["season"], errors="coerce")
    pbp = pbp[pbp["season"].between(2016, TARGET, inclusive="both")].copy()
    assert_phase4_loaded_universe(pbp)

    with authorize_frozen_phase4_execution():
        team_states = phase3_data.build_team_states(pbp, schedules)
        a0_team_rows = phase3_data.build_a0_team_rows(team_states)
        drives = phase3_data.build_drive_table(pbp, schedules)
        b0_team_rows, b0_outcome_rows = phase3_data.build_b0_frames(drives, team_states, schedules)
        rare_points = phase3_data.build_rare_points(pbp, schedules)

    return {
        "schedules": schedules,
        "pbp": pbp,
        "team_states": team_states,
        "a0_team_rows": a0_team_rows,
        "drives": drives,
        "b0_team_rows": b0_team_rows,
        "b0_outcome_rows": b0_outcome_rows,
        "rare_points": rare_points,
    }


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    out = frame.copy()
    if {"season", "week", "game_id"}.issubset(out.columns):
        out = out.sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, lineterminator="\n")


def _tie_excluded_probability(frame: pd.DataFrame) -> dict:
    ties = pd.to_numeric(frame["actual_margin"], errors="coerce").eq(0)
    part = frame.loc[~ties].copy()
    y = (part["actual_margin"] > 0).astype(int)
    result = probability_metrics(y, part["home_win_probability"])
    result["ties_excluded"] = int(ties.sum())
    result["sensitivity"] = "tie_excluded"
    return result


def _ats_ou(frame: pd.DataFrame, pred_margin: str, pred_total: str) -> dict:
    work = frame.copy()
    market_margin = pd.to_numeric(work["market_margin"], errors="coerce")
    market_total = pd.to_numeric(work["market_total"], errors="coerce")
    actual_margin = pd.to_numeric(work["actual_margin"], errors="coerce")
    actual_total = pd.to_numeric(work["actual_total"], errors="coerce")
    pm = pd.to_numeric(work[pred_margin], errors="coerce")
    pt = pd.to_numeric(work[pred_total], errors="coerce")

    actual_cover = actual_margin - market_margin
    model_edge = pm - market_margin
    ats_mask = actual_cover.notna() & model_edge.notna() & actual_cover.ne(0) & model_edge.ne(0)
    ats_hit = np.sign(actual_cover[ats_mask].to_numpy(float)) == np.sign(model_edge[ats_mask].to_numpy(float))

    actual_ou = actual_total - market_total
    model_ou = pt - market_total
    ou_mask = actual_ou.notna() & model_ou.notna() & actual_ou.ne(0) & model_ou.ne(0)
    ou_hit = np.sign(actual_ou[ou_mask].to_numpy(float)) == np.sign(model_ou[ou_mask].to_numpy(float))
    return {
        "ats": {
            "games": int(ats_mask.sum()),
            "excluded_pushes_or_zero_model_edge": int(len(work) - ats_mask.sum()),
            "hit_rate": float(np.mean(ats_hit)) if len(ats_hit) else None,
        },
        "over_under": {
            "games": int(ou_mask.sum()),
            "excluded_pushes_or_zero_model_edge": int(len(work) - ou_mask.sum()),
            "hit_rate": float(np.mean(ou_hit)) if len(ou_hit) else None,
        },
        "policy": "secondary diagnostic only; no edge threshold tuned or used for model selection",
    }


def _c0_arm_uncertainty(c0: pd.DataFrame) -> dict:
    result: dict[str, dict] = {"margin": {}, "total": {}}
    for target, actual, seed_base in (("margin", "actual_margin", 260410), ("total", "actual_total", 260420)):
        ref = np.abs(pd.to_numeric(c0[actual], errors="coerce") - pd.to_numeric(c0[f"m0_{target}"], errors="coerce"))
        for idx, arm in enumerate(("m1", "m2", "m3"), start=1):
            cand = np.abs(pd.to_numeric(c0[actual], errors="coerce") - pd.to_numeric(c0[f"{arm}_{target}"], errors="coerce"))
            result[target][f"{arm.upper()}_vs_M0"] = season_week_block_bootstrap(
                c0, cand, ref, samples=BOOTSTRAP_SAMPLES, seed=seed_base + idx
            )
    return result


def _baseline_game_counts(frame: pd.DataFrame) -> dict:
    cols = {
        "market": ("baseline_market_margin", "baseline_market_total"),
        "naive_hfa_league_total": ("baseline_hfa_margin", "baseline_league_total"),
        "historical_scoring_average": ("baseline_scoring_margin", "baseline_scoring_total"),
        "simple_epa_team_strength": ("baseline_epa_margin", "baseline_epa_total"),
    }
    out = {}
    for name, (m, t) in cols.items():
        out[name] = {
            "margin_games": int(pd.to_numeric(frame.get(m), errors="coerce").notna().sum()) if m in frame else 0,
            "total_games": int(pd.to_numeric(frame.get(t), errors="coerce").notna().sum()) if t in frame else 0,
        }
    return out


def run(output_dir: Path, *, simulations: int = B0_SIMULATIONS) -> dict:
    if int(simulations) < 10_000:
        raise RuntimeError("Phase 4 final B0 evaluation requires at least 10,000 simulations/game")
    receipt = _validate_opening_boundary()
    hashes = verify_frozen_hashes()
    d_receipt = _read_json(PHASE3_D_RECEIPT)
    for target in ("margin", "total"):
        if d_receipt[target]["disposition"] != "ENSEMBLE_NOT_ELIGIBLE":
            raise RuntimeError(f"D {target} frozen disposition drift")
    if not PHASE3_FUTURE_SURFACE.exists():
        raise RuntimeError("preserved 2022-2024 Candidate 5 OOF surface is missing")

    data = _load_phase4_data()
    schedules = data["schedules"]
    if sorted(schedules["season"].dropna().astype(int).unique().tolist()) != list(range(2016, 2026)):
        raise RuntimeError("Phase 4 schedule universe is not exactly 2016-2025")

    with authorize_frozen_phase4_execution():
        # Earlier A0 OOF rows are regenerated only because C0's 2025 training
        # requires genuine prior-time A0 representations.  Only 2025 rows are
        # emitted as Phase 4 holdout evidence.
        a0_all, a0_receipts = generate_a0_oof(
            data["a0_team_rows"],
            tuple(range(2017, 2026)),
            code_sha=hashes["implementation_sha256"],
            config_sha=hashes["config_sha256"],
        )
        a0 = a0_all[a0_all["season"].eq(TARGET)].copy().reset_index(drop=True)
        b0, b0_receipt = fit_predict_b0_outer(
            data["b0_team_rows"],
            data["b0_outcome_rows"],
            data["drives"],
            data["rare_points"],
            schedules,
            TARGET,
            code_sha=hashes["implementation_sha256"],
            config_sha=hashes["config_sha256"],
            simulations=int(simulations),
        )
        cframe = build_c0_frame(a0_all, schedules)
        c0, c0_receipt = fit_predict_c0_outer(
            cframe,
            TARGET,
            code_sha=hashes["implementation_sha256"],
            config_sha=hashes["config_sha256"],
        )

    for candidate, frame in ((A0_ID, a0), (B0_ID, b0), (C0_ID, c0)):
        assert_phase4_prediction_receipt(frame, candidate)
        if not frame["season"].eq(TARGET).all():
            raise RuntimeError(f"{candidate}: non-2025 row escaped holdout output")
        if not frame["train_through_season"].astype(int).lt(TARGET).all():
            raise RuntimeError(f"{candidate}: target-season outcome entered model training boundary")

    a0_market = attach_market(a0, schedules)
    b0_market = attach_market(b0, schedules)
    baselines = build_baselines(schedules, data["team_states"], (TARGET,))

    a0_eval = evaluate_a0(a0)
    b0_eval = evaluate_b0(b0)
    c0_eval = evaluate_c0(c0)
    a0_eval["probability_tie_excluded"] = _tie_excluded_probability(a0)
    b0_eval["probability_tie_excluded"] = _tie_excluded_probability(b0)
    a0_eval["market_relative"] = market_relative(a0_market, "expected_margin", "expected_total")
    b0_eval["market_relative"] = market_relative(b0_market, "expected_margin", "expected_total")
    c0_eval["market_relative_M3"] = market_relative(c0, "m3_margin", "m3_total")
    a0_eval["secondary_ats_ou"] = _ats_ou(a0_market, "expected_margin", "expected_total")
    b0_eval["secondary_ats_ou"] = _ats_ou(b0_market, "expected_margin", "expected_total")
    c0_eval["secondary_ats_ou_M3"] = _ats_ou(c0, "m3_margin", "m3_total")

    c0_uncertainty = _c0_arm_uncertainty(c0)
    base_eval = baseline_metrics(baselines)

    diagnostics = []
    for candidate, frame, pm, pt in (
        (A0_ID, a0_market, "expected_margin", "expected_total"),
        (B0_ID, b0_market, "expected_margin", "expected_total"),
        (C0_ID, c0, "m3_margin", "m3_total"),
    ):
        part = diagnostic_slices(frame, pm, pt)
        part.insert(0, "candidate_id", candidate)
        diagnostics.append(part)
    diagnostic_frame = pd.concat(diagnostics, ignore_index=True)

    common_ids = sorted(set(a0["game_id"].astype(str)) & set(b0["game_id"].astype(str)) & set(c0["game_id"].astype(str)))
    target_sched = schedules[schedules["season"].eq(TARGET)].copy()
    summary = {
        "schema_version": "spread-points-phase4-holdout-summary-v1",
        "phase": 4,
        "evidence_scope": "one-time 2025 final historical challenger holdout",
        "holdout_limitation": "final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions",
        "holdout_opened": True,
        "target_season": TARGET,
        "eligible_regular_season_games": int(target_sched["actual_margin"].notna().sum()),
        "exact_common_A0_B0_C0_games": int(len(common_ids)),
        "candidate_ids": {"A0": A0_ID, "B0": B0_ID, "C0": C0_ID},
        "D": {"margin": "ENSEMBLE_NOT_ELIGIBLE", "total": "ENSEMBLE_NOT_ELIGIBLE"},
        "A0": a0_eval,
        "B0": b0_eval,
        "C0": c0_eval,
        "C0_M0_M1_M2_M3_uncertainty": c0_uncertainty,
        "baselines": base_eval,
        "baseline_game_counts": _baseline_game_counts(baselines),
        "current_levline_score_baseline_note": "Phase 1 current LevLine score baseline is retained as historical context only here because its documented inverse-MAE ensemble weights were estimated across the same 2022-2025 OOF block; it is not represented as a clean standalone 2025 selector comparator.",
        "FST_probability_comparator_note": "No F-ST probability result is recomputed in Phase 4. Phase 1 chronology-clean F-ST context remains separate to avoid an in-sample production-artifact comparison.",
        "bootstrap": {"method": "season+week block; one-season Phase 4 therefore effectively week-blocked", "samples": BOOTSTRAP_SAMPLES, "single_season_inference_limitation": True},
        "implementation_sha256": hashes["implementation_sha256"],
        "config_sha256": hashes["config_sha256"],
        "source_contract": SOURCE_CONTRACT_VERSION,
        "market_horizon_label": MARKET_HORIZON_LABEL,
        "simulations_per_b0_game": int(simulations),
        "Candidate5_state": "NOT_STARTED",
        "Candidate5_trained": False,
        "completed_2026_outcomes_used": False,
        "production_model": "F-ST-01-FROZEN-2026",
        "production_changed": False,
        "phase3_OOF_surface_preserved": str(PHASE3_FUTURE_SURFACE.relative_to(PROGRAM_ROOT.parent.parent)),
    }

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(a0, output_dir / "A0_HOLDOUT_2025.csv")
    _write_csv(b0, output_dir / "B0_HOLDOUT_2025.csv")
    _write_csv(c0, output_dir / "C0_HOLDOUT_2025.csv")
    _write_csv(baselines, output_dir / "BASELINES_HOLDOUT_2025.csv")
    _write_csv(diagnostic_frame, output_dir / "DIAGNOSTIC_SLICES_2025.csv")
    write_json(output_dir / "HOLDOUT_SUMMARY.json", sanitize_json(summary))
    write_json(
        output_dir / "CANDIDATE_RUN_RECEIPTS_2025.json",
        sanitize_json({
            "A0_all_prior_time_receipts": a0_receipts,
            "A0_2025_receipt": next(x for x in a0_receipts if int(x["target_season"]) == TARGET),
            "B0_2025_receipt": b0_receipt,
            "C0_2025_receipt": c0_receipt,
        }),
    )
    manifest = {
        "schema_version": "spread-points-phase4-run-manifest-v1",
        "generator_git_head": git_sha(),
        "opening_receipt_commit": "362af7af7db43a715b9ab9537a52d2749c37e7a6",
        "holdout_opened": True,
        "loaded_seasons": list(range(2016, 2026)),
        "model_fit_training_seasons": list(range(2016, 2025)),
        "target_season": TARGET,
        "sequential_within_2025_feature_state": "allowed only through frozen shifted prior-completed-game state construction; 2025 outcomes never enter model fitting/tuning for 2025",
        "eligible_regular_season_games": int(target_sched["actual_margin"].notna().sum()),
        "exact_paired_counts": {
            "A0": int(len(a0)), "B0": int(len(b0)), "C0_market_paired": int(len(c0)), "A0_B0_C0_common": int(len(common_ids))
        },
        "candidate_ids": {"A0": A0_ID, "B0": B0_ID, "C0": C0_ID},
        "D_margin": "ENSEMBLE_NOT_ELIGIBLE",
        "D_total": "ENSEMBLE_NOT_ELIGIBLE",
        "implementation_sha256": hashes["implementation_sha256"],
        "config_sha256": hashes["config_sha256"],
        "source_contract": SOURCE_CONTRACT_VERSION,
        "market_horizon_label": MARKET_HORIZON_LABEL,
        "B0_simulations_per_game": int(simulations),
        "bootstrap_resamples": BOOTSTRAP_SAMPLES,
        "random_seeds": {"base_phase3_seed": 2603, "market_margin": 26031, "market_total": 26032, "C0_arm_uncertainty_base": 260410},
        "Candidate5_trained": False,
        "completed_2026_outcomes_used": False,
        "production_changed": False,
        "production_model": "F-ST-01-FROZEN-2026",
        "opening_receipt_holdout_state": receipt["holdout_state_at_receipt"],
        "files": sorted(p.name for p in output_dir.iterdir() if p.is_file()),
    }
    write_json(output_dir / "HOLDOUT_RUN_MANIFEST.json", sanitize_json(manifest))

    print("PHASE4_HOLDOUT_COMPLETE")
    print(f"target_season={TARGET}")
    print(f"eligible_games={manifest['eligible_regular_season_games']}")
    print(f"A0_games={len(a0)} B0_games={len(b0)} C0_games={len(c0)}")
    print(f"implementation_sha256={FROZEN_IMPLEMENTATION_SHA256}")
    print(f"config_sha256={FROZEN_CONFIG_SHA256}")
    print("candidate5_trained=false completed_2026_outcomes_used=false production_changed=false")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--simulations", type=int, default=B0_SIMULATIONS)
    args = parser.parse_args()
    run(args.output_dir, simulations=args.simulations)


if __name__ == "__main__":
    main()
