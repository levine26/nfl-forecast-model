from __future__ import annotations

"""Fail-closed preflight for frozen ATS-JSIP-V1.

This script deliberately runs before any ATS-JSIP-V1 target-season proper score is
computed. It (1) reproduces the accepted KMASS-MARKETML-IPROJ null on the canonical
2022-2025 rows and (2) tests the frozen Student-t adaptive-support invariant across
all legal nuisance pairs. If no legal pair can satisfy the 1e-12 upper-tail tolerance
at support <=160, the frozen experiment is classified FAILED and target scoring is
not run.
"""

from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
OUTER = (2022, 2023, 2024, 2025)
DF_GRID = (4, 6, 10)
SCALE_GRID = (8.0, 10.0, 12.0, 14.0)
TAIL_TOL = 1e-12
INITIAL_BOUND = 80
BOUND_STEP = 20
MAX_BOUND = 160
MIN_INNER_TRAINING_ROWS = 100
CANONICAL_OOF_SHA256 = "c50fa8b5aaa088cfe19ef809e0e92f1a3fef0d979073187f8ba69fd545a38f7b"
CONTROLLING_COMMITS = [
    "930320c94ffc1d554f72589328b48a98a3373662",
    "f67cd216b73ee1861e8019c2eb6553438c3aeb64",
    "50264684a74b34dbb1d9fa3b4c6c4455c6e111d3",
]


class PreflightError(RuntimeError):
    pass


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_probability_entrypoint():
    path = REPO_ROOT / "research" / "ats-crossmarket-transfer" / "probability_only_entrypoint.py"
    spec = importlib.util.spec_from_file_location("jsip_crossmarket_probability_entry", path)
    if spec is None or spec.loader is None:
        raise PreflightError(f"cannot load canonical cross-market entrypoint: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_null_reproduction(prob) -> dict[str, Any]:
    runner = prob.runner
    games, historical_identity = prob.build_schedule_only_historical_games()
    archive, coverage, _ = prob.build_probability_archive(games)
    target = archive[archive["season"].isin(OUTER)].copy()
    target = target.sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    if len(target) != 1087:
        raise PreflightError(f"canonical target-row count drift: {len(target)} != 1087")
    if pd.to_numeric(target["season"], errors="raise").ge(2026).any():
        raise PreflightError("completed-2026 row entered canonical target frame")

    canonical_path = REPO_ROOT / "research" / "ats-crossmarket-transfer" / "results" / "OOF_PREDICTIONS.csv"
    if _sha(canonical_path) != CANONICAL_OOF_SHA256:
        raise PreflightError("accepted cross-market OOF artifact hash drift")
    canonical = pd.read_csv(canonical_path, low_memory=False)
    canonical = canonical[canonical["season"].isin(OUTER)].copy()
    canonical = canonical.sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    if len(canonical) != len(target):
        raise PreflightError("canonical OOF row count does not match reconstructed target frame")

    key_cols = ["season", "week", "game_id"]
    left_keys = target[key_cols].astype({"season": int, "week": int, "game_id": str})
    right_keys = canonical[key_cols].astype({"season": int, "week": int, "game_id": str})
    if not left_keys.equals(right_keys):
        raise PreflightError("canonical primary-null row identity mismatch")

    generated: list[tuple[float, float, float, float]] = []
    for _, row in target.iterrows():
        fit = runner._fit_for_season(int(row["season"]))
        parts = runner._base_parts(row, fit)
        probs = runner._iproj_cpl(parts, float(row["market_prob"]))
        cls = runner._observed_class(int(row["actual_margin"]), float(row["spread_line"]))
        loss = runner._cpl_loss(cls, probs)
        generated.append((float(probs[0]), float(probs[1]), float(probs[2]), float(loss)))
    arr = np.asarray(generated, dtype=float)
    expected = canonical[[
        "marketml_iproj_p_cover",
        "marketml_iproj_p_push",
        "marketml_iproj_p_loss",
        "marketml_iproj_cpl_log_loss",
    ]].to_numpy(dtype=float)
    max_abs = float(np.max(np.abs(arr - expected)))
    if not np.isfinite(max_abs) or max_abs > 5e-12:
        raise PreflightError(f"KMASS-MARKETML-IPROJ reproduction failed: max_abs={max_abs}")

    row_payload = "\n".join(
        f"{int(r.season)}|{int(r.week)}|{str(r.game_id)}" for r in target.itertuples(index=False)
    ) + "\n"
    prob_payload = "\n".join(
        "|".join(format(float(x), ".17g") for x in vals) for vals in arr
    ) + "\n"
    return {
        "status": "PASS",
        "canonical_oof_sha256": CANONICAL_OOF_SHA256,
        "common_rows": int(len(target)),
        "outer_seasons": list(OUTER),
        "row_identity_sha256": sha256(row_payload.encode("utf-8")).hexdigest(),
        "reproduced_probability_payload_sha256": sha256(prob_payload.encode("utf-8")).hexdigest(),
        "max_abs_probability_or_loss_difference": max_abs,
        "historical_identity": historical_identity,
        "coverage": coverage,
        "target_frame": target,
        "historical_games": games,
    }


def _conditional_upper_tail(mu: float, df: int, scale: float, bound: int) -> float:
    z_floor = (-0.5 - float(mu)) / float(scale)
    z_upper = (float(bound) + 0.5 - float(mu)) / float(scale)
    denom = float(student_t.sf(z_floor, df=int(df)))
    numer = float(student_t.sf(z_upper, df=int(df)))
    if not math.isfinite(denom) or not math.isfinite(numer) or denom <= 0.0:
        raise PreflightError("nonfinite conditional Student-t support tail")
    return numer / denom


def _min_allowed_tail(mu: float, bound: int) -> tuple[float, tuple[int, float]]:
    vals: list[tuple[float, tuple[int, float]]] = []
    for df in DF_GRID:
        for scale in SCALE_GRID:
            vals.append((_conditional_upper_tail(mu, df, scale, bound), (df, scale)))
    return min(vals, key=lambda x: x[0])


def _required_best_case_bound(mu: float, cap: int = 1000) -> int | None:
    for bound in range(INITIAL_BOUND, cap + BOUND_STEP, BOUND_STEP):
        tail, _ = _min_allowed_tail(mu, bound)
        if tail < TAIL_TOL:
            return int(bound)
    return None


def _support_audit(target: pd.DataFrame, historical_games: pd.DataFrame) -> dict[str, Any]:
    if target.empty:
        raise PreflightError("empty canonical target frame")
    # The canonical common rows all carry total_line, but retain the frozen fallback
    # implementation for completeness without using target outcomes.
    rows: list[dict[str, Any]] = []
    by_season_median: dict[int, float] = {}
    for season in OUTER:
        train = historical_games[pd.to_numeric(historical_games["season"], errors="coerce") < season].copy()
        totals = pd.to_numeric(train["total_line"], errors="coerce")
        totals = totals[np.isfinite(totals.to_numpy(dtype=float))]
        if len(train) < MIN_INNER_TRAINING_ROWS or totals.empty:
            raise PreflightError(f"insufficient pre-{season} support-audit history")
        by_season_median[int(season)] = float(totals.median())

    for _, row in target.iterrows():
        season = int(row["season"])
        spread = float(row["spread_line"])
        center = -spread
        total_raw = pd.to_numeric(pd.Series([row.get("total_line")]), errors="coerce").iloc[0]
        total_missing = not np.isfinite(float(total_raw))
        total = by_season_median[season] if total_missing else float(total_raw)
        mu_h = (total + center) / 2.0
        mu_a = (total - center) / 2.0
        h_tail, h_pair = _min_allowed_tail(mu_h, MAX_BOUND)
        a_tail, a_pair = _min_allowed_tail(mu_a, MAX_BOUND)
        h_req = _required_best_case_bound(mu_h)
        a_req = _required_best_case_bound(mu_a)
        rows.append({
            "game_id": str(row["game_id"]),
            "season": season,
            "week": int(row["week"]),
            "mu_home": float(mu_h),
            "mu_away": float(mu_a),
            "total_missing": bool(total_missing),
            "best_case_home_tail_at_160": float(h_tail),
            "best_case_away_tail_at_160": float(a_tail),
            "home_best_pair": {"df": int(h_pair[0]), "scale": float(h_pair[1])},
            "away_best_pair": {"df": int(a_pair[0]), "scale": float(a_pair[1])},
            "home_best_case_required_bound": h_req,
            "away_best_case_required_bound": a_req,
            "home_fails_all_frozen_pairs_at_160": bool(h_tail >= TAIL_TOL),
            "away_fails_all_frozen_pairs_at_160": bool(a_tail >= TAIL_TOL),
        })

    frame = pd.DataFrame(rows)
    axes = np.concatenate([
        frame["best_case_home_tail_at_160"].to_numpy(dtype=float),
        frame["best_case_away_tail_at_160"].to_numpy(dtype=float),
    ])
    required = [
        x for x in (
            frame["home_best_case_required_bound"].tolist()
            + frame["away_best_case_required_bound"].tolist()
        ) if x is not None
    ]
    all_rows_fail = bool(
        frame["home_fails_all_frozen_pairs_at_160"].all()
        or frame["away_fails_all_frozen_pairs_at_160"].all()
    )
    # Stronger statement used for the receipt: every team-axis on every canonical row
    # fails even under the thinnest-tailed allowed nuisance pair.
    all_axes_fail = bool(
        frame["home_fails_all_frozen_pairs_at_160"].all()
        and frame["away_fails_all_frozen_pairs_at_160"].all()
    )
    return {
        "status": "FAIL" if all_rows_fail else "PASS",
        "invariant": "adaptive omitted upper-tail mass < 1e-12 per team marginal at support <= 160",
        "tail_tolerance": TAIL_TOL,
        "maximum_support_bound": MAX_BOUND,
        "rows_audited": int(len(frame)),
        "team_axes_audited": int(2 * len(frame)),
        "all_rows_have_at_least_one_axis_failing_all_frozen_pairs": all_rows_fail,
        "all_team_axes_fail_all_frozen_pairs_at_160": all_axes_fail,
        "minimum_best_case_tail_at_160": float(np.min(axes)),
        "median_best_case_tail_at_160": float(np.median(axes)),
        "maximum_best_case_tail_at_160": float(np.max(axes)),
        "best_case_required_bound_min": int(min(required)) if required else None,
        "best_case_required_bound_median": float(np.median(required)) if required else None,
        "best_case_required_bound_max": int(max(required)) if required else None,
        "total_missing_rows": int(frame["total_missing"].sum()),
        "best_case_definition": "minimum conditional structural Student-t upper tail over every frozen (df, scale) pair",
        "frozen_df_grid": list(DF_GRID),
        "frozen_scale_grid": list(SCALE_GRID),
        "diagnostic_rows": rows[:12],
    }


def run(output: Path) -> dict[str, Any]:
    canonical = _canonical_null_reproduction(_load_probability_entrypoint())
    target = canonical.pop("target_frame")
    historical_games = canonical.pop("historical_games")
    support = _support_audit(target, historical_games)

    failed = support["status"] != "PASS"
    receipt: dict[str, Any] = {
        "candidate": "ATS-JSIP-V1",
        "scientific_status": "FAILED" if failed else "PREFLIGHT_PASS",
        "phase_disposition": "FAIL_CLOSED_BEFORE_TARGET_SCORING" if failed else "AUTHORIZED_FOR_FROZEN_TARGET_SCORING",
        "failure_reason": (
            "Frozen adaptive-support invariant is infeasible at the preregistered 160-point ceiling; "
            "no legal (df, scale) pair reaches omitted upper-tail mass <1e-12."
            if failed else None
        ),
        "git_sha": _git_sha(),
        "controlling_preregistration_commits": CONTROLLING_COMMITS,
        "implementation_clarification": "research/ats-joint-score-iprojection-v1/IMPLEMENTATION_CLARIFICATION_001.md",
        "completed_2026_outcomes_used": 0,
        "candidate_target_probabilities_generated": False,
        "candidate_target_proper_scores_generated": False,
        "candidate_target_ats_results_generated": False,
        "production_changed": False,
        "primary_null_reproduction": canonical,
        "support_invariant": support,
        "preflight_invariants": {
            "completed_2026_firewall": "PASS",
            "canonical_primary_null_identity_and_hash": canonical["status"],
            "adaptive_support_tail": support["status"],
            "joint_pmf_normalization": "NOT_RUN_FAIL_CLOSED" if failed else "PENDING",
            "ml_projection_tie_preservation": "NOT_RUN_FAIL_CLOSED" if failed else "PENDING",
            "ml_projection_conditional_win_constraint": "NOT_RUN_FAIL_CLOSED" if failed else "PENDING",
            "half_point_push_zero": "NOT_RUN_FAIL_CLOSED" if failed else "PENDING",
            "whole_number_push_margin_identity": "NOT_RUN_FAIL_CLOSED" if failed else "PENDING",
            "target_outcome_mutation_invariance": "NOT_RUN_FAIL_CLOSED" if failed else "PENDING",
            "outer_nuisance_chronology": "NOT_RUN_FAIL_CLOSED" if failed else "PENDING",
            "production_firewall": "PASS",
        },
        "no_post_result_rescue_authorized": True,
        "next_phase_allowed": (
            "Close ATS-JSIP-V1 as FAILED; a new candidate ID/preregistration is required for any numerical redesign."
            if failed else "Execute the frozen chronology-correct 2022-2025 target evaluation."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    output = ROOT / "PREFLIGHT_RECEIPT.json"
    receipt = run(output)
    print(json.dumps({
        "candidate": receipt["candidate"],
        "scientific_status": receipt["scientific_status"],
        "phase_disposition": receipt["phase_disposition"],
        "primary_null_reproduction": receipt["primary_null_reproduction"]["status"],
        "support_invariant": receipt["support_invariant"]["status"],
        "candidate_target_proper_scores_generated": receipt["candidate_target_proper_scores_generated"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
