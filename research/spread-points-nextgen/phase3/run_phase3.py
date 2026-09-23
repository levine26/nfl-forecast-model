from __future__ import annotations

"""Reproduce Spread & Points Phase 3 development evidence.

Run with:

    python -m research.spread-points-nextgen.phase3.run_phase3 \
        --output-dir /tmp/levline-phase3

The source loader is hard-capped at 2016-2024. This runner cannot emit a 2025
challenger forecast or use completed-2026 outcomes for any selection path.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .phase3_a0 import generate_a0_oof
from .phase3_b0 import generate_b0_oof
from .phase3_c0 import build_c0_frame, generate_c0_oof
from .phase3_data import build_phase3_data
from .phase3_evaluation import (
    attach_market,
    baseline_metrics,
    build_baselines,
    diagnostic_slices,
    evaluate_a0,
    evaluate_b0,
    evaluate_c0,
    evaluate_d_target,
    market_relative,
    season_metrics,
)
from .phase3_scaffold import (
    A0_ID,
    B0_ID,
    B0_SIMULATIONS,
    C0_ID,
    DEVELOPMENT_SEASONS,
    MARKET_HORIZON_LABEL,
    assert_prediction_receipt,
    file_sha,
    git_sha,
    sanitize_json,
    write_json,
)

ROOT = Path(__file__).resolve().parent
PROGRAM_ROOT = ROOT.parent
PHASE1_SUMMARY = PROGRAM_ROOT / "phase1" / "PHASE1_SUMMARY.json"


def _code_hash() -> str:
    paths = [
        ROOT / "phase3_scaffold.py",
        ROOT / "phase3_data.py",
        ROOT / "phase3_a0.py",
        ROOT / "phase3_b0.py",
        ROOT / "phase3_c0.py",
        ROOT / "phase3_evaluation.py",
        ROOT / "run_phase3.py",
    ]
    return file_sha(paths)


def _config_hash() -> str:
    return file_sha(
        [
            ROOT / "PRE_RESULT_GATE.json",
            ROOT / "CANDIDATE_REGISTRY.json",
            ROOT / "FEATURE_PROVENANCE_CONTRACT.md",
        ]
    )


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = frame.copy()
    if {"season", "week", "game_id"}.issubset(ordered.columns):
        ordered = ordered.sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    ordered.to_csv(path, index=False, lineterminator="\n")


def _future_candidate5_surface(
    a0: pd.DataFrame,
    b0: pd.DataFrame,
    c0: pd.DataFrame,
    d_margin: pd.DataFrame | None,
    d_total: pd.DataFrame | None,
) -> pd.DataFrame:
    a = a0[
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
            "train_through_season",
            "candidate_id",
            "code_sha",
            "config_sha",
        ]
    ].rename(
        columns={
            "home_win_probability": "a0_home_win_probability",
            "expected_margin": "a0_expected_margin",
            "expected_total": "a0_expected_total",
            "score_uncertainty": "a0_score_uncertainty",
            "offense_strength_diff": "a0_offense_strength_diff",
            "defense_strength_diff": "a0_defense_strength_diff",
            "train_through_season": "a0_train_through_season",
            "candidate_id": "a0_candidate_id",
            "code_sha": "a0_code_sha",
            "config_sha": "a0_config_sha",
        }
    )
    b = b0[
        [
            "game_id",
            "home_win_probability",
            "expected_margin",
            "expected_total",
            "margin_variance",
            "total_variance",
            "margin_p10",
            "margin_p90",
            "total_p10",
            "total_p90",
            "train_through_season",
            "candidate_id",
            "code_sha",
            "config_sha",
        ]
    ].rename(
        columns={
            "home_win_probability": "b0_home_win_probability",
            "expected_margin": "b0_expected_margin",
            "expected_total": "b0_expected_total",
            "margin_variance": "b0_margin_variance",
            "total_variance": "b0_total_variance",
            "margin_p10": "b0_margin_p10",
            "margin_p90": "b0_margin_p90",
            "total_p10": "b0_total_p10",
            "total_p90": "b0_total_p90",
            "train_through_season": "b0_train_through_season",
            "candidate_id": "b0_candidate_id",
            "code_sha": "b0_code_sha",
            "config_sha": "b0_config_sha",
        }
    )
    c = c0[
        [
            "game_id",
            "market_margin",
            "market_total",
            "predicted_margin_residual",
            "predicted_total_residual",
            "hybrid_margin",
            "hybrid_total",
            "market_horizon_label",
            "train_through_season",
            "candidate_id",
            "code_sha",
            "config_sha",
        ]
    ].rename(
        columns={
            "market_margin": "c0_market_margin",
            "market_total": "c0_market_total",
            "predicted_margin_residual": "c0_predicted_margin_residual",
            "predicted_total_residual": "c0_predicted_total_residual",
            "hybrid_margin": "c0_hybrid_margin",
            "hybrid_total": "c0_hybrid_total",
            "market_horizon_label": "c0_market_horizon_label",
            "train_through_season": "c0_train_through_season",
            "candidate_id": "c0_candidate_id",
            "code_sha": "c0_code_sha",
            "config_sha": "c0_config_sha",
        }
    )
    out = a.merge(b, on="game_id", how="inner").merge(c, on="game_id", how="inner")
    if d_margin is not None:
        dm = d_margin[["game_id", "blend_prediction", "weight_A0", "weight_B0", "weight_C0", "train_through_season"]].rename(
            columns={
                "blend_prediction": "d_margin_prediction",
                "weight_A0": "d_margin_weight_a0",
                "weight_B0": "d_margin_weight_b0",
                "weight_C0": "d_margin_weight_c0",
                "train_through_season": "d_margin_train_through_season",
            }
        )
        out = out.merge(dm, on="game_id", how="left")
    if d_total is not None:
        dt = d_total[["game_id", "blend_prediction", "weight_A0", "weight_B0", "weight_C0", "train_through_season"]].rename(
            columns={
                "blend_prediction": "d_total_prediction",
                "weight_A0": "d_total_weight_a0",
                "weight_B0": "d_total_weight_b0",
                "weight_C0": "d_total_weight_c0",
                "train_through_season": "d_total_train_through_season",
            }
        )
        out = out.merge(dt, on="game_id", how="left")
    out["oof_provenance_assertion"] = (
        (out["a0_train_through_season"] < out["season"])
        & (out["b0_train_through_season"] < out["season"])
        & (out["c0_train_through_season"] < out["season"])
    )
    if not out["oof_provenance_assertion"].all():
        raise RuntimeError("future Candidate 5 surface contains non-OOF component state")
    return out


def run(output_dir: Path, *, simulations: int = B0_SIMULATIONS) -> dict:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    code_sha = _code_hash()
    config_sha = _config_hash()

    data = build_phase3_data()
    if data.schedules["season"].max() >= 2025 or data.pbp["season"].max() >= 2025:
        raise RuntimeError("Phase 3 2025 firewall breached during source construction")

    # Earlier OOF rows are generated only to make C0 and D prior-time training legal.
    # Only 2022-2024 component surfaces are committed as Phase 3 development evidence.
    a0_all, a0_receipts = generate_a0_oof(
        data.a0_team_rows,
        tuple(range(2017, 2025)),
        code_sha=code_sha,
        config_sha=config_sha,
    )
    b0_all, b0_receipts = generate_b0_oof(
        data.b0_team_rows,
        data.b0_outcome_rows,
        data.drives,
        data.rare_points,
        data.schedules,
        tuple(range(2019, 2025)),
        code_sha=code_sha,
        config_sha=config_sha,
        simulations=int(simulations),
    )
    cframe = build_c0_frame(a0_all, data.schedules)
    c0_all, c0_receipts = generate_c0_oof(
        cframe,
        tuple(range(2019, 2025)),
        code_sha=code_sha,
        config_sha=config_sha,
    )

    dev = set(DEVELOPMENT_SEASONS)
    a0 = a0_all[a0_all["season"].isin(dev)].copy().reset_index(drop=True)
    b0 = b0_all[b0_all["season"].isin(dev)].copy().reset_index(drop=True)
    c0 = c0_all[c0_all["season"].isin(dev)].copy().reset_index(drop=True)
    for candidate, frame in ((A0_ID, a0), (B0_ID, b0), (C0_ID, c0)):
        assert_prediction_receipt(frame, candidate)
        if not set(frame["season"].astype(int).unique()).issubset(dev):
            raise RuntimeError(f"{candidate}: development surface escaped 2022-2024")

    a0_market = attach_market(a0, data.schedules)
    b0_market = attach_market(b0, data.schedules)

    d_margin_receipt, d_margin = evaluate_d_target(
        a0_all[a0_all["season"].between(2019, 2024)],
        b0_all,
        c0_all,
        target="margin",
        code_sha=code_sha,
        config_sha=config_sha,
    )
    d_total_receipt, d_total = evaluate_d_target(
        a0_all[a0_all["season"].between(2019, 2024)],
        b0_all,
        c0_all,
        target="total",
        code_sha=code_sha,
        config_sha=config_sha,
    )

    baselines = build_baselines(data.schedules, data.team_states, DEVELOPMENT_SEASONS)
    base_metrics = baseline_metrics(baselines)
    phase1_context = json.loads(PHASE1_SUMMARY.read_text(encoding="utf-8")) if PHASE1_SUMMARY.exists() else None

    evaluation = {
        "schema_version": "phase3-development-summary-v1",
        "phase": 3,
        "evidence_scope": "2022-2024 rolling-origin out-of-sample development only",
        "holdout_2025": "UNOPENED",
        "completed_2026_selection": "NOT_USED",
        "candidate5": "NOT_TRAINED",
        "production_model": "F-ST-01-FROZEN-2026",
        "production_change": False,
        "implementation_code_sha256": code_sha,
        "config_sha256": config_sha,
        "A0": {
            "pooled": evaluate_a0(a0),
            "season_by_season": season_metrics(a0, "expected_margin", "expected_total"),
            "market_relative": market_relative(a0_market, "expected_margin", "expected_total"),
        },
        "B0": {
            "pooled": evaluate_b0(b0),
            "season_by_season": season_metrics(b0, "expected_margin", "expected_total"),
            "market_relative": market_relative(b0_market, "expected_margin", "expected_total"),
        },
        "C0": {
            "pooled": evaluate_c0(c0),
            "season_by_season_M3": season_metrics(c0, "m3_margin", "m3_total"),
            "market_relative_M3": market_relative(c0, "m3_margin", "m3_total"),
        },
        "baselines": base_metrics,
        "phase1_current_levline_context": phase1_context.get("baseline") if phase1_context else None,
        "phase1_context_note": "Phase 1 LevLine values cover 2022-2025 and are contextual, not substituted for the exact Phase 3 paired 2022-2024 baseline rows.",
        "D": {"margin": d_margin_receipt, "total": d_total_receipt},
    }

    diag_parts = []
    for candidate, frame, pm, pt in (
        (A0_ID, a0_market, "expected_margin", "expected_total"),
        (B0_ID, b0_market, "expected_margin", "expected_total"),
        (C0_ID, c0, "m3_margin", "m3_total"),
    ):
        part = diagnostic_slices(frame, pm, pt)
        part.insert(0, "candidate_id", candidate)
        diag_parts.append(part)
    diagnostics = pd.concat(diag_parts, ignore_index=True)

    candidate5_surface = _future_candidate5_surface(a0, b0, c0, d_margin, d_total)

    _write_csv(a0, output_dir / "A0_OOF_2022_2024.csv")
    _write_csv(b0, output_dir / "B0_OOF_2022_2024.csv")
    _write_csv(c0, output_dir / "C0_OOF_2022_2024.csv")
    _write_csv(baselines, output_dir / "BASELINES_2022_2024.csv")
    _write_csv(diagnostics, output_dir / "DIAGNOSTIC_SLICES.csv")
    _write_csv(candidate5_surface, output_dir / "FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv")
    if d_margin is not None:
        _write_csv(d_margin, output_dir / "D_MARGIN_OOF_2022_2024.csv")
    if d_total is not None:
        _write_csv(d_total, output_dir / "D_TOTAL_OOF_2022_2024.csv")

    write_json(output_dir / "DEVELOPMENT_SUMMARY.json", sanitize_json(evaluation))
    write_json(
        output_dir / "CANDIDATE_RUN_RECEIPTS.json",
        sanitize_json({"A0": a0_receipts, "B0": b0_receipts, "C0": c0_receipts}),
    )
    write_json(
        output_dir / "D_ELIGIBILITY_RECEIPT.json",
        sanitize_json({"margin": d_margin_receipt, "total": d_total_receipt}),
    )
    manifest = {
        "schema_version": "phase3-run-manifest-v1",
        "generator_git_head": git_sha(),
        "implementation_code_sha256": code_sha,
        "config_sha256": config_sha,
        "source_contract": "phase3-feature-provenance-v1",
        "market_horizon_label": MARKET_HORIZON_LABEL,
        "loaded_seasons": list(range(2016, 2025)),
        "development_seasons": list(DEVELOPMENT_SEASONS),
        "2025_loaded": False,
        "2025_challenger_scored": False,
        "completed_2026_outcomes_used": False,
        "candidate5_trained": False,
        "simulations_per_b0_game": int(simulations),
        "files": sorted(p.name for p in output_dir.iterdir() if p.is_file()),
    }
    write_json(output_dir / "RUN_MANIFEST.json", sanitize_json(manifest))

    # Human-readable CI summary, deliberately omitting any 2025 quantity.
    print("PHASE3_DEVELOPMENT_COMPLETE")
    print(f"code_sha256={code_sha}")
    print(f"config_sha256={config_sha}")
    for label, frame in (("A0", a0), ("B0", b0), ("C0", c0)):
        print(f"{label}_development_games={len(frame)}")
    print(f"D_margin={d_margin_receipt['disposition']}")
    print(f"D_total={d_total_receipt['disposition']}")
    print("holdout_2025=UNOPENED")
    print("candidate5=NOT_TRAINED")
    print("production=F-ST-01-FROZEN-2026")
    return evaluation


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--simulations", type=int, default=B0_SIMULATIONS)
    args = parser.parse_args()
    if int(args.simulations) < 10_000:
        raise SystemExit("Final Phase 3 development requires at least 10,000 B0 simulations per game")
    run(args.output_dir, simulations=int(args.simulations))


if __name__ == "__main__":
    main()
