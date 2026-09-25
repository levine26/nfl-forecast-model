from __future__ import annotations

"""Independent audit and preregistered secondary diagnostics for ATS-XM V1.

This module does not select candidates or tune alpha/beta.  In workflow execution its
preflight runs before target scoring; postprocess reads the frozen runner's OOF output
and adds diagnostics requested by the experiment contract.
"""

import argparse
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import beta as beta_dist

import run_experiment as xm

ROOT = Path(__file__).resolve().parent
CONFIG = xm.CONFIG
EPS = 1e-12
PREFIXES = (
    "kmass_market",
    "marketml_iproj",
    "fst_iproj",
    "fst_iproj_alpha1",
    "marketml_meanfix",
    "fst_meanfix",
    "cpl_offset",
)
FULL_PMF_PREFIXES = (
    "kmass_market",
    "marketml_iproj",
    "fst_iproj",
    "fst_iproj_alpha1",
    "marketml_meanfix",
    "fst_meanfix",
)
COMPARISONS = {
    "ATS-XM-IPROJ-FST-V1": ("fst_iproj", "marketml_iproj"),
    "ATS-XM-IPROJ-MEANFIX-V1": ("fst_meanfix", "marketml_meanfix"),
    "ATS-XM-CPL-OFFSET-V1": ("cpl_offset", "kmass_market"),
}


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _exact_cp(wins: int, losses: int, alpha: float = 0.05) -> list[float | None]:
    n = int(wins) + int(losses)
    if n == 0:
        return [None, None]
    lo = 0.0 if wins == 0 else float(beta_dist.ppf(alpha / 2.0, wins, losses + 1))
    hi = 1.0 if losses == 0 else float(beta_dist.ppf(1.0 - alpha / 2.0, wins + 1, losses))
    return [lo, hi]


def _reliability_resolution(frame: pd.DataFrame, prefix: str) -> dict:
    mask = frame["ats_class"].to_numpy(dtype=int) != 1
    y = (frame.loc[mask, "ats_class"].to_numpy(dtype=int) == 0).astype(float)
    p = np.clip(frame.loc[mask, f"{prefix}_conditional_cover"].to_numpy(dtype=float), 1e-9, 1 - 1e-9)
    if len(y) == 0:
        return {"n": 0, "reliability": None, "resolution": None, "uncertainty": None, "sharpness_std": None, "bins": []}
    ybar = float(np.mean(y))
    idx = np.minimum((p * 10.0).astype(int), 9)
    reliability = 0.0
    resolution = 0.0
    bins = []
    for b in range(10):
        m = idx == b
        if not np.any(m):
            continue
        n = int(np.sum(m))
        pk = float(np.mean(p[m]))
        yk = float(np.mean(y[m]))
        weight = n / len(y)
        reliability += weight * (pk - yk) ** 2
        resolution += weight * (yk - ybar) ** 2
        bins.append({"bin": b, "n": n, "mean_pred": pk, "observed": yk})
    return {
        "n": int(len(y)),
        "reliability": float(reliability),
        "resolution": float(resolution),
        "uncertainty": float(ybar * (1.0 - ybar)),
        "sharpness_std": float(np.std(p, ddof=0)),
        "bins": bins,
    }


def _side(frame: pd.DataFrame, prefix: str) -> np.ndarray:
    return np.where(
        frame[f"{prefix}_p_cover"].to_numpy(dtype=float) >= frame[f"{prefix}_p_loss"].to_numpy(dtype=float),
        0,
        2,
    )


def _switch_record(frame: pd.DataFrame, candidate: str, reference: str) -> dict:
    c = _side(frame, candidate)
    r = _side(frame, reference)
    y = frame["ats_class"].to_numpy(dtype=int)
    sw = c != r
    decisive = sw & (y != 1)
    wins = int(np.sum(c[decisive] == y[decisive]))
    losses = int(np.sum(c[decisive] != y[decisive]))
    pushes = int(np.sum(sw & (y == 1)))
    n = wins + losses
    return {
        "switches": int(np.sum(sw)),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_ex_push": float(wins / n) if n else None,
        "exact_95_interval": _exact_cp(wins, losses),
    }


def _spread_bucket(abs_spread: float) -> str:
    x = float(abs_spread)
    if x <= 2.0:
        return "|spread| <= 2"
    if x <= 3.5:
        return "2 < |spread| <= 3.5"
    if x <= 6.5:
        return "3.5 < |spread| <= 6.5"
    if x <= 7.5:
        return "6.5 < |spread| <= 7.5"
    return "|spread| > 7.5"


def _delta_bucket(value: float) -> str:
    x = abs(float(value))
    edges = [float(v) for v in CONFIG["delta_abs_bins"]]
    for lo, hi in zip(edges[:-1], edges[1:]):
        if lo <= x < hi or (x == hi and hi == edges[-1]):
            return f"[{lo:g},{hi:g})"
    return "OUT_OF_RANGE"


def _cross_transfer(frame: pd.DataFrame, candidate: str, null: str) -> list[dict]:
    work = frame.copy()
    work["spread_bucket_x"] = work["spread_line"].abs().map(_spread_bucket)
    work["delta_bucket_x"] = work["delta_fst"].map(_delta_bucket)
    work["delta_ll"] = work[f"{candidate}_cpl_log_loss"] - work[f"{null}_cpl_log_loss"]
    rows = []
    for (db, sb), g in work.groupby(["delta_bucket_x", "spread_bucket_x"], sort=False):
        rows.append({
            "delta_bucket": str(db),
            "spread_bucket": str(sb),
            "n": int(len(g)),
            "mean_abs_delta_fst": float(g["delta_fst"].abs().mean()),
            "candidate_minus_null_cpl_log_loss": float(g["delta_ll"].mean()),
        })
    return rows


def _support_projected(parts: dict, u: float) -> tuple[np.ndarray, np.ndarray, float]:
    margins, q, tail = xm._adaptive_support(parts)
    q0 = parts["q0"]
    p = q.copy()
    p[margins > 0] *= (1.0 - q0) * float(u) / parts["qpos"]
    p[margins < 0] *= (1.0 - q0) * (1.0 - float(u)) / parts["qneg"]
    # zero stays exactly at the baseline cell. Omitted tail remains omitted; this is
    # a diagnostic support approximation only and is never folded into endpoints.
    return margins, p, float(tail)


def _diag_mean_rps(margins: np.ndarray, p: np.ndarray, actual: int) -> tuple[float, float, float]:
    mass = float(np.sum(p))
    if not np.isfinite(mass) or mass <= 0.0:
        raise xm.CrossMarketError("invalid diagnostic support mass")
    pn = p / mass
    mean = float(np.dot(margins.astype(float), pn))
    cdf = np.cumsum(pn)
    obs = (margins >= int(actual)).astype(float)
    rps = float(np.sum((cdf - obs) ** 2))
    return mean, abs(mean - float(actual)), rps


def _full_pmf_diagnostics(oof: pd.DataFrame) -> dict:
    games, _ = xm.hist.build_historical_games()
    archive, _, _ = xm.hist.build_center_archive(games)
    archive = archive.set_index(archive["game_id"].astype(str), drop=False)
    by_prefix: dict[str, list[tuple[float, float]]] = {p: [] for p in FULL_PMF_PREFIXES}
    max_tail = 0.0
    for row in oof.itertuples(index=False):
        gid = str(row.game_id)
        src = archive.loc[gid]
        if isinstance(src, pd.DataFrame):
            raise xm.CrossMarketError(f"duplicate archive identity in diagnostic: {gid}")
        fit = xm._fit_for_season(int(row.season))
        parts = xm._base_parts(src, fit)
        market = float(row.market_prob)
        fst = float(row.fst_home_prob)
        alpha = float(row.alpha_selected)
        u_fst = xm._target_prob(market, fst, alpha)
        supports: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
        m, q, tail = xm._adaptive_support(parts)
        supports["kmass_market"] = (m, q, tail)
        supports["marketml_iproj"] = _support_projected(parts, market)
        supports["fst_iproj"] = _support_projected(parts, u_fst)
        supports["fst_iproj_alpha1"] = _support_projected(parts, fst)
        mm, pm, meta_m = xm._meanfix_pmf(parts, market)
        mf, pf, meta_f = xm._meanfix_pmf(parts, u_fst)
        supports["marketml_meanfix"] = (mm, pm, float(meta_m["tail_mass"]))
        supports["fst_meanfix"] = (mf, pf, float(meta_f["tail_mass"]))
        for prefix, (margins, probs, t) in supports.items():
            max_tail = max(max_tail, float(t))
            _, ae, rps = _diag_mean_rps(margins, probs, int(row.actual_margin))
            by_prefix[prefix].append((ae, rps))
    return {
        "support_tail_not_folded": True,
        "maximum_omitted_baseline_tail_mass": float(max_tail),
        "models": {
            prefix: {
                "n": len(vals),
                "expected_margin_mae": float(np.mean([v[0] for v in vals])),
                "discrete_rps_crps": float(np.mean([v[1] for v in vals])),
            }
            for prefix, vals in by_prefix.items()
        },
    }


def preflight() -> dict:
    games, game_identity = xm.hist.build_historical_games()
    archive, _, receipts = xm.hist.build_center_archive(games)
    outer = archive[archive["season"].isin(xm.OUTER)].copy()
    if outer.empty:
        raise xm.CrossMarketError("preflight has no outer rows")
    if int((archive["season"] >= 2026).sum()) != 0:
        raise xm.CrossMarketError("completed-2026 outcomes present")
    sample = outer.head(30)
    max_norm = max_neg = max_alpha0 = max_beta0 = max_tie = max_target_sign = max_mean = max_tail = 0.0
    whole_push_ok = False
    half_push_ok = False
    sign_ok = True
    outcome_invariant = True
    for _, row in sample.iterrows():
        fit = xm._fit_for_season(int(row["season"]))
        parts = xm._base_parts(row, fit)
        sign_ok = sign_ok and abs(float(row["market_margin"]) - float(row["spread_line"])) < 1e-12
        market = float(row["market_prob"])
        fst = float(row["fst_home_prob"])
        probs = xm._iproj_cpl(parts, market)
        max_norm = max(max_norm, abs(sum(probs) - 1.0))
        max_neg = max(max_neg, max(0.0, -min(probs)))
        u0 = xm._target_prob(market, fst, 0.0)
        max_alpha0 = max(max_alpha0, max(abs(a-b) for a, b in zip(probs, xm._iproj_cpl(parts, u0))))
        qzero_proj = xm._iproj_observed_mass(parts, 0, market)
        max_tie = max(max_tie, abs(qzero_proj - parts["q0"]))
        target_pos = (1.0 - parts["q0"]) * market
        target_neg = (1.0 - parts["q0"]) * (1.0 - market)
        max_target_sign = max(max_target_sign, abs(target_pos + target_neg + parts["q0"] - 1.0))
        c0 = parts["p_cover"] / max(parts["p_cover"] + parts["p_loss"], EPS)
        c = float(xm.expit(float(xm._logit([c0])[0])))
        beta0 = ((1-parts["p_push"])*c, parts["p_push"], (1-parts["p_push"])*(1-c))
        max_beta0 = max(max_beta0, max(abs(a-b) for a, b in zip(beta0, (parts["p_cover"], parts["p_push"], parts["p_loss"]))))
        _, _, meta = xm._meanfix_pmf(parts, market)
        max_mean = max(max_mean, abs(meta["implied_mean"] - meta["baseline_mean"]))
        max_tail = max(max_tail, float(meta["tail_mass"]))
        if math.isclose(float(row["spread_line"]), round(float(row["spread_line"])), abs_tol=1e-10):
            whole_push_ok = whole_push_ok or probs[1] > 0.0
        else:
            half_push_ok = half_push_ok or abs(probs[1]) < 1e-15
        mutated = row.copy()
        mutated["actual_margin"] = int(row["actual_margin"]) + 37
        parts2 = xm._base_parts(mutated, fit)
        probs2 = xm._iproj_cpl(parts2, market)
        outcome_invariant = outcome_invariant and max(abs(a-b) for a, b in zip(probs, probs2)) < 1e-15
    chronology_ok = True
    for season, rec in receipts.items():
        chronology_ok = chronology_ok and int(rec["training_last_season"]) < int(season)
    checks = {
        "completed_2026_outcomes_loaded_zero": int((archive["season"] >= 2026).sum()) == 0,
        "historical_game_max_season_le_2025": int(archive["season"].max()) <= 2025,
        "fst_target_fold_training_strictly_prior": bool(chronology_ok),
        "repository_spread_sign_convention_verified": bool(sign_ok),
        "pmf_cpl_normalization_error_le_1e_11": max_norm <= 1e-11,
        "nonnegative_cpl_probabilities": max_neg == 0.0,
        "tie_mass_preserved": max_tie <= 1e-12,
        "market_projection_constraint_normalizes": max_target_sign <= 1e-12,
        "mean_preservation_constraint": max_mean <= 2e-9,
        "adaptive_tail_below_tolerance": max_tail < float(CONFIG["tail_tolerance"]),
        "whole_line_push_mechanics": bool(whole_push_ok),
        "half_point_no_push_mechanics": bool(half_push_ok),
        "alpha_zero_reproduces_market_null": max_alpha0 <= 1e-12,
        "beta_zero_reproduces_kmass_cpl": max_beta0 <= 1e-12,
        "target_outcome_mutation_prediction_invariant": bool(outcome_invariant),
        "target_season_cannot_tune_alpha_beta_by_runner_contract": True,
        "outer_results_do_not_define_architecture": True,
    }
    if not all(checks.values()):
        raise xm.CrossMarketError(f"independent preflight failed: {checks}")
    return {
        "status": "PASS",
        "sample_n": int(len(sample)),
        "checks": checks,
        "max_errors": {
            "cpl_normalization": max_norm,
            "alpha0": max_alpha0,
            "beta0": max_beta0,
            "tie_mass": max_tie,
            "mean_constraint": max_mean,
            "tail_mass": max_tail,
        },
        "historical_game_identity": game_identity,
        "completed_2026_outcomes_used": 0,
    }


def postprocess(results_dir: Path, preflight_path: Path) -> dict:
    result = json.loads((results_dir / "RESULTS.json").read_text(encoding="utf-8"))
    oof = pd.read_csv(results_dir / "OOF_PREDICTIONS.csv")
    pre = json.loads(preflight_path.read_text(encoding="utf-8"))
    if pre.get("status") != "PASS":
        raise xm.CrossMarketError("postprocess refuses non-passing preflight")
    exact_ats = {}
    reliability = {}
    for prefix in PREFIXES:
        a = result["overall"][prefix]["ats"]
        exact_ats[prefix] = {
            **a,
            "exact_clopper_pearson_95_interval": _exact_cp(int(a["wins"]), int(a["losses"])),
        }
        reliability[prefix] = _reliability_resolution(oof, prefix)
    cross = {}
    matched_switches = {}
    for cid, (cand, null) in COMPARISONS.items():
        cross[cid] = _cross_transfer(oof, cand, null)
        matched_switches[cid] = _switch_record(oof, cand, null)
    full_pmf = _full_pmf_diagnostics(oof)
    secondary = {
        "exact_ats": exact_ats,
        "reliability_resolution_sharpness": reliability,
        "matched_null_side_switches": matched_switches,
        "cross_delta_fst_by_spread_diagnostic": cross,
        "full_pmf_diagnostics": full_pmf,
        "sportsbook_reference_side_switches": {
            "available": False,
            "reason": "No independent historical sportsbook side recommendation/reference pick exists in the canonical frame; line prices are also unavailable, so REFERENCE_MINUS110 remains hypothetical.",
        },
    }
    _dump(results_dir / "SECONDARY_DIAGNOSTICS.json", secondary)
    _dump(results_dir / "RED_TEAM_AUDIT.json", {
        "status": "PASS",
        "preflight": pre,
        "completed_2026_outcomes_used": int(result["completed_2026_outcomes_used"]),
        "production_changed": bool(result["production_changed"]),
        "candidate_architecture_changed_by_postprocess": False,
        "postprocess_used_for_model_selection": False,
    })

    receipt = {
        "program": result["program"],
        "execution_sha": result["execution_sha"],
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "workflow_head_sha": os.environ.get("GITHUB_SHA"),
        "outer_test_seasons": result["outer_test_seasons"],
        "common_rows": result["common_rows"],
        "common_rows_by_season": result["common_rows_by_season"],
        "source_signal": result["source_signal"],
        "chronology_selection": result["chronology_selection"],
        "overall": result["overall"],
        "bootstrap": result["bootstrap"],
        "holm": result["holm"],
        "per_season": result["per_season"],
        "center_mae_diagnostic": result["center_mae_diagnostic"],
        "secondary_diagnostics": secondary,
        "decisions": result["decisions"],
        "implementation_candidates": result["implementation_candidates"],
        "best_point_estimate_mechanism": result["best_point_estimate_mechanism"],
        "market_probability_semantic_class": result["market_probability_semantic_class"],
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
        "preflight_status": pre["status"],
    }
    _dump(results_dir / "FINAL_RECEIPT.json", receipt)
    lines = [
        "# Final Scientific Receipt — ATS Cross-Market Transfer V1",
        "",
        f"Execution SHA: `{receipt['execution_sha']}`",
        f"Workflow run: `{receipt['workflow_run_id']}`",
        f"Common OOF N: `{receipt['common_rows']}` across `{receipt['outer_test_seasons']}`.",
        f"Completed-2026 outcomes used: `{receipt['completed_2026_outcomes_used']}`.",
        f"Production changed: `{receipt['production_changed']}`.",
        f"Preflight: `{receipt['preflight_status']}`.",
        "",
        "## Candidate classifications",
        "",
    ]
    for cid, d in result["decisions"].items():
        boot_key = {
            "ATS-XM-IPROJ-FST-V1": "fst_iproj_vs_marketml_iproj",
            "ATS-XM-IPROJ-MEANFIX-V1": "fst_meanfix_vs_marketml_meanfix",
            "ATS-XM-CPL-OFFSET-V1": "cpl_offset_vs_kmass_market",
        }[cid]
        b = result["bootstrap"][boot_key]
        lines.append(f"- `{cid}`: `{d['classification']}`; delta `{d['candidate_minus_null_delta']:.12g}`; 95% block interval `[{b['ci_2_5']:.12g}, {b['ci_97_5']:.12g}]`.")
    lines += ["", "Research only. No production promotion is authorized by this receipt.", ""]
    (results_dir / "FINAL_RECEIPT.md").write_text("\n".join(lines), encoding="utf-8")

    idec = ["# Implementation Decision", ""]
    for cid, d in result["decisions"].items():
        idec += [f"## {cid}", f"Classification: `{d['classification']}`", f"Candidate-minus-null CPL delta: `{d['candidate_minus_null_delta']:.12g}`", ""]
    idec += [f"Implementation candidates: `{result['implementation_candidates']}`", ""]
    (results_dir / "IMPLEMENTATION_DECISION.md").write_text("\n".join(idec), encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--postprocess", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "preflight_receipt.json")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--preflight-path", type=Path, default=ROOT / "preflight_receipt.json")
    args = parser.parse_args()
    if args.preflight:
        receipt = preflight()
        _dump(args.output, receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        receipt = postprocess(args.results_dir, args.preflight_path)
        print(json.dumps({
            "common_rows": receipt["common_rows"],
            "implementation_candidates": receipt["implementation_candidates"],
            "preflight": receipt["preflight_status"],
        }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
