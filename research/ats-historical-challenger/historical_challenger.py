from __future__ import annotations

"""Leakage-safe historical center challenger for the accepted V2 key-mass model.

Research only. This runner never loads completed 2026 outcomes and never writes production
artifacts. It reuses the accepted V2 CONSTANT_SCALE_KEY numerical model verbatim and varies
only the location center: market, reconstructed LevLine/F-ST fair margin, or a training-only
blend of the two.
"""

import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "research" / "ats-frontier-v2"))

import phase4_core as v2core  # noqa: E402
from nfl_forecast.challenger_fst import frozen_stack_probability  # noqa: E402
from nfl_forecast.config import load_config  # noqa: E402
from nfl_forecast.data import load_core_data  # noqa: E402
from nfl_forecast.elo import build_pregame_elo  # noqa: E402
from nfl_forecast.features import (  # noqa: E402
    add_game_results,
    aggregate_team_games,
    build_matchup_features,
    core_columns,
)
from nfl_forecast.fst_nested_pure import load_frozen_training_frame  # noqa: E402
from nfl_forecast.models import fit_weighted_regression  # noqa: E402

CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
V2_FREEZE = json.loads((ROOT / "v2_nuisance_freeze.json").read_text(encoding="utf-8"))
OUTER = tuple(int(x) for x in CONFIG["outer_test_seasons"])
CENTER_SEASONS = tuple(int(x) for x in CONFIG["center_archive_seasons"])
EPS = 1e-12


class HistoricalChallengerError(RuntimeError):
    pass


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "UNKNOWN"


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _logit(values) -> np.ndarray:
    p = np.clip(np.asarray(values, dtype=float), 1e-6, 1.0 - 1e-6)
    return np.log(p / (1.0 - p))


def _finite(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    mask = pd.Series(True, index=frame.index)
    for col in columns:
        mask &= np.isfinite(pd.to_numeric(frame[col], errors="coerce").to_numpy(dtype=float))
    return mask


def build_historical_games() -> tuple[pd.DataFrame, dict]:
    model_cfg = load_config(str(REPO_ROOT / "config" / "model.yaml"))
    start = int(model_cfg["data"]["core_start_season"])
    max_season = int(CONFIG["source_season_max"])
    if max_season != 2025:
        raise HistoricalChallengerError("source season max must remain frozen at 2025")

    seasons = list(range(start, max_season + 1))
    if any(s >= 2026 for s in seasons):
        raise HistoricalChallengerError("completed-2026 firewall violated before data load")

    bundle = load_core_data(seasons, model_cfg["data"]["cache_dir"])
    schedules = bundle.schedules.copy()
    schedules["season"] = pd.to_numeric(schedules["season"], errors="coerce")
    if schedules["season"].dropna().ge(2026).any():
        raise HistoricalChallengerError("completed-2026 schedule row entered research frame")

    elo = build_pregame_elo(
        schedules,
        initial=model_cfg["elo"]["initial"],
        k_factor=model_cfg["elo"]["k_factor"],
        home_advantage=model_cfg["elo"]["home_advantage"],
        offseason_regression=model_cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(
        bundle.pbp,
        model_cfg["data"]["neutral_wp_lower"],
        model_cfg["data"]["neutral_wp_upper"],
    )
    team_games = add_game_results(team_games, schedules)
    games = build_matchup_features(team_games, schedules, elo)
    games["season"] = pd.to_numeric(games["season"], errors="coerce")
    games["week"] = pd.to_numeric(games["week"], errors="coerce")
    games = games[
        games["season"].between(start, max_season, inclusive="both")
        & games["home_win"].notna()
    ].copy()
    if games["season"].ge(2026).any():
        raise HistoricalChallengerError("completed-2026 outcome entered historical games")

    games["actual_margin"] = pd.to_numeric(games["margin"], errors="coerce").round()
    if not np.allclose(
        games["actual_margin"].dropna().to_numpy(dtype=float),
        np.round(games["actual_margin"].dropna().to_numpy(dtype=float)),
        atol=1e-9,
    ):
        raise HistoricalChallengerError("non-integer NFL final margin detected")
    games["actual_margin"] = games["actual_margin"].astype("Int64")
    games["spread_line"] = pd.to_numeric(games["spread_line"], errors="coerce")
    games["total_line"] = pd.to_numeric(games["total_line"], errors="coerce")
    games["market_margin"] = v2core.market_margin(games["spread_line"])

    completed = games["actual_margin"].notna()
    identity = {
        "requested_seasons": seasons,
        "historical_rows": int(len(games)),
        "completed_rows": int(completed.sum()),
        "first_season": int(games["season"].min()),
        "last_season": int(games["season"].max()),
        "completed_2026_rows": int((games["season"] >= 2026).sum()),
        "game_ids_sha256": sha256(
            ("\n".join(sorted(games["game_id"].astype(str))) + "\n").encode("utf-8")
        ).hexdigest(),
    }
    return games, identity


def fit_margin_sigmas(games: pd.DataFrame) -> tuple[dict[int, float], dict[int, dict]]:
    model_cfg = load_config(str(REPO_ROOT / "config" / "model.yaml"))
    seed = int(model_cfg["model"]["random_state"])
    start = int(model_cfg["data"]["core_start_season"])
    features = core_columns(games)
    if not features:
        raise HistoricalChallengerError("production margin-regression feature set is empty")

    sigmas: dict[int, float] = {}
    receipts: dict[int, dict] = {}
    for target in CENTER_SEASONS:
        train = games[games["season"] < target].copy()
        if train.empty or train["season"].ge(target).any():
            raise HistoricalChallengerError(f"invalid pre-{target} margin training frame")
        validation_start = max(start + 1, target - 4)
        fit = fit_weighted_regression(
            train,
            features,
            "margin",
            seed=seed,
            validation_start=validation_start,
            validation_end=target - 1,
        )
        sigma = float(fit.residual_std)
        if not np.isfinite(sigma) or sigma <= 0.0:
            raise HistoricalChallengerError(f"invalid pre-{target} margin sigma: {sigma}")
        sigmas[target] = sigma
        receipts[target] = {
            "target_season": target,
            "training_rows": int(len(train)),
            "training_first_season": int(train["season"].min()),
            "training_last_season": int(train["season"].max()),
            "validation_start": validation_start,
            "validation_end": target - 1,
            "feature_count": int(len(features)),
            "margin_sigma": sigma,
            "validation_mae": None if not np.isfinite(fit.validation_mae) else float(fit.validation_mae),
        }
    return sigmas, receipts


def fit_fst_fold(training: pd.DataFrame, target_season: int) -> tuple[np.ndarray, dict]:
    cfg = CONFIG["fst_stack"]
    train = training[pd.to_numeric(training["season"], errors="coerce") < target_season].copy()
    test = training[pd.to_numeric(training["season"], errors="coerce") == target_season].copy()
    if len(train) < int(cfg["minimum_training_rows"]):
        raise HistoricalChallengerError(
            f"insufficient pre-{target_season} F-ST rows: {len(train)}"
        )
    if test.empty or train["home_win"].nunique() < 2:
        raise HistoricalChallengerError(f"invalid F-ST fold for {target_season}")
    if pd.to_numeric(train["season"], errors="coerce").ge(target_season).any():
        raise HistoricalChallengerError("F-ST target leakage detected")

    x = np.column_stack([_logit(train["market_prob"]), _logit(train["pure_prob"])])
    y = pd.to_numeric(train["home_win"], errors="raise").astype(int).to_numpy()
    model = LogisticRegression(
        C=float(cfg["C"]),
        penalty=str(cfg["penalty"]),
        solver=str(cfg["solver"]),
        max_iter=int(cfg["max_iter"]),
    )
    model.fit(x, y)
    probs = frozen_stack_probability(
        pd.to_numeric(test["market_prob"], errors="raise"),
        pd.to_numeric(test["pure_prob"], errors="raise"),
        intercept=float(model.intercept_[0]),
        market_logit_coefficient=float(model.coef_[0, 0]),
        pure_logit_coefficient=float(model.coef_[0, 1]),
    )
    receipt = {
        "target_season": int(target_season),
        "training_rows": int(len(train)),
        "test_rows": int(len(test)),
        "training_first_season": int(pd.to_numeric(train["season"]).min()),
        "training_last_season": int(pd.to_numeric(train["season"]).max()),
        "intercept": float(model.intercept_[0]),
        "market_logit_coefficient": float(model.coef_[0, 0]),
        "pure_logit_coefficient": float(model.coef_[0, 1]),
    }
    return probs, receipt


def build_center_archive(games: pd.DataFrame) -> tuple[pd.DataFrame, dict, dict]:
    frozen = load_frozen_training_frame()
    frozen["season"] = pd.to_numeric(frozen["season"], errors="raise").astype(int)
    if frozen["season"].ge(2026).any():
        raise HistoricalChallengerError("frozen F-ST training frame contains 2026 outcomes")

    sigmas, sigma_receipts = fit_margin_sigmas(games)
    game_cols = [
        "game_id", "season", "week", "gameday", "home_team", "away_team",
        "actual_margin", "spread_line", "total_line", "market_margin",
    ]
    parts: list[pd.DataFrame] = []
    receipts: dict[str, dict] = {}
    fst_receipts: dict[str, dict] = {}

    for season in CENTER_SEASONS:
        probs, fst_receipt = fit_fst_fold(frozen, season)
        target_fst = frozen[frozen["season"] == season].copy().reset_index(drop=True)
        if len(probs) != len(target_fst):
            raise HistoricalChallengerError(f"F-ST probability alignment failed for {season}")
        target_fst["fst_home_prob"] = probs
        target_fst["margin_sigma"] = float(sigmas[season])
        target_fst["levline_margin"] = norm.ppf(
            np.clip(target_fst["fst_home_prob"].to_numpy(dtype=float), 1e-6, 1.0 - 1e-6)
        ) * float(sigmas[season])

        season_games = games[games["season"] == season][game_cols].copy()
        eligible = season_games[
            _finite(season_games, ["actual_margin", "spread_line", "total_line", "market_margin"])
        ].copy()
        joined = target_fst.merge(
            season_games,
            on=["game_id", "season"],
            how="inner",
            validate="one_to_one",
        )
        common_mask = _finite(
            joined,
            [
                "actual_margin", "spread_line", "total_line", "market_margin",
                "fst_home_prob", "margin_sigma", "levline_margin",
            ],
        )
        common = joined[common_mask].copy()
        common["actual_margin"] = common["actual_margin"].astype(int)
        parts.append(common)

        eligible_ids = set(eligible["game_id"].astype(str))
        fst_ids = set(target_fst["game_id"].astype(str))
        joined_ids = set(joined["game_id"].astype(str))
        common_ids = set(common["game_id"].astype(str))
        receipts[str(season)] = {
            "historical_eligible_rows": int(len(eligible)),
            "fst_archived_rows": int(len(target_fst)),
            "joined_rows": int(len(joined)),
            "common_rows": int(len(common)),
            "eligible_missing_fst_row": int(len(eligible_ids - fst_ids)),
            "fst_missing_historical_row": int(len(fst_ids - set(season_games["game_id"].astype(str)))),
            "joined_removed_missing_required_value": int(len(joined_ids - common_ids)),
        }
        fst_receipts[str(season)] = fst_receipt

    archive = pd.concat(parts, ignore_index=True).sort_values(
        ["season", "week", "game_id"]
    ).reset_index(drop=True)
    if archive["season"].ge(2026).any():
        raise HistoricalChallengerError("2026 outcome entered center archive")
    return archive, {
        "coverage_by_season": receipts,
        "margin_sigma_fits": {str(k): v for k, v in sigma_receipts.items()},
    }, fst_receipts


def _score_with_fit(frame: pd.DataFrame, center: np.ndarray, fit: dict) -> pd.DataFrame:
    work = frame.copy()
    work["market_margin"] = np.asarray(center, dtype=float)
    scored = v2core.predict_m4(work, fit)
    return scored


def _select_blend_weight(train: pd.DataFrame, fit: dict) -> tuple[float, list[dict]]:
    rows: list[dict] = []
    for weight in [float(x) for x in CONFIG["blend_weight_grid_market"]]:
        center = (
            weight * train["market_margin"].to_numpy(dtype=float)
            + (1.0 - weight) * train["levline_margin"].to_numpy(dtype=float)
        )
        scored = _score_with_fit(train, center, fit)
        score = float(scored["integer_log_score"].mean())
        rows.append({
            "market_weight": weight,
            "training_rows": int(len(train)),
            "training_integer_log_score": score,
        })
    best = min(
        rows,
        key=lambda r: (
            r["training_integer_log_score"],
            abs(r["market_weight"] - 0.5),
            r["market_weight"],
        ),
    )
    return float(best["market_weight"]), rows


def run_outer_folds(archive: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    oof_parts: list[pd.DataFrame] = []
    tuning: dict[str, dict] = {}
    candidate_map = {
        "KMASS-MARKET": "market_margin",
        "KMASS-LEVLINE": "levline_margin",
    }

    for target in OUTER:
        train = archive[archive["season"] < target].copy()
        test = archive[archive["season"] == target].copy()
        if len(train) < 100 or test.empty:
            raise HistoricalChallengerError(
                f"insufficient common center rows for outer {target}: train={len(train)} test={len(test)}"
            )
        if train["season"].ge(target).any():
            raise HistoricalChallengerError("outer target leakage detected")

        freeze = V2_FREEZE["outer_seasons"][str(target)]
        key_fit = dict(freeze["CONSTANT_SCALE_KEY"])
        no_key_fit = dict(freeze["CONSTANT_SCALE_NO_KEY"])
        weight, weight_table = _select_blend_weight(train, key_fit)
        tuning[str(target)] = {
            "training_rows": int(len(train)),
            "training_seasons": sorted(int(x) for x in train["season"].unique()),
            "selected_market_weight": weight,
            "blend_weight_training_scores": weight_table,
            "v2_key_fit": key_fit,
            "v2_no_key_fit": no_key_fit,
        }

        out = test[
            [
                "game_id", "season", "week", "gameday", "home_team", "away_team",
                "actual_margin", "spread_line", "total_line", "market_margin",
                "levline_margin", "fst_home_prob", "margin_sigma",
            ]
        ].copy().reset_index(drop=True)
        centers = {
            "KMASS-MARKET": test["market_margin"].to_numpy(dtype=float),
            "KMASS-LEVLINE": test["levline_margin"].to_numpy(dtype=float),
            "KMASS-BLEND": (
                weight * test["market_margin"].to_numpy(dtype=float)
                + (1.0 - weight) * test["levline_margin"].to_numpy(dtype=float)
            ),
        }

        for candidate, center in centers.items():
            scored = _score_with_fit(test, center, key_fit).reset_index(drop=True)
            no_key = _score_with_fit(test, center, no_key_fit).reset_index(drop=True)
            prefix = candidate.lower().replace("-", "_")
            out[f"{prefix}_center"] = center
            out[f"{prefix}_integer_log_score"] = scored["integer_log_score"].to_numpy(dtype=float)
            out[f"{prefix}_cpl_log_loss"] = scored["cpl_log_loss"].to_numpy(dtype=float)
            out[f"{prefix}_p_cover"] = scored["p_cover"].to_numpy(dtype=float)
            out[f"{prefix}_p_push"] = scored["p_push"].to_numpy(dtype=float)
            out[f"{prefix}_p_loss"] = scored["p_loss"].to_numpy(dtype=float)
            out[f"{prefix}_sigma"] = scored["sigma"].to_numpy(dtype=float)
            out[f"{prefix}_no_key_integer_log_score"] = no_key["integer_log_score"].to_numpy(dtype=float)
            if "ats_class" not in out:
                out["ats_class"] = scored["ats_class"].to_numpy(dtype=int)
        out["blend_market_weight"] = weight
        oof_parts.append(out)

    return pd.concat(oof_parts, ignore_index=True), tuning


def _candidate_metrics(oof: pd.DataFrame, candidate: str) -> dict:
    prefix = candidate.lower().replace("-", "_")
    score_col = f"{prefix}_integer_log_score"
    no_key_col = f"{prefix}_no_key_integer_log_score"
    center_col = f"{prefix}_center"
    probs = oof[[f"{prefix}_p_cover", f"{prefix}_p_push", f"{prefix}_p_loss"]].to_numpy(dtype=float)
    classes = oof["ats_class"].to_numpy(dtype=int)
    error = oof[center_col].to_numpy(dtype=float) - oof["actual_margin"].to_numpy(dtype=float)
    ats_frame = pd.DataFrame({
        "p_cover": probs[:, 0],
        "p_push": probs[:, 1],
        "p_loss": probs[:, 2],
        "ats_class": classes,
    })
    per = []
    for season, part in oof.groupby("season", sort=True):
        per.append({
            "season": int(season),
            "n": int(len(part)),
            "integer_log_score": float(part[score_col].mean()),
            "no_key_integer_log_score": float(part[no_key_col].mean()),
            "key_minus_no_key": float((part[score_col] - part[no_key_col]).mean()),
            "center_mae": float(np.mean(np.abs(part[center_col] - part["actual_margin"]))),
            "center_rmse": float(np.sqrt(np.mean((part[center_col] - part["actual_margin"]) ** 2))),
        })
    return {
        "n": int(len(oof)),
        "integer_log_score": float(oof[score_col].mean()),
        "cpl_log_loss": float(oof[f"{prefix}_cpl_log_loss"].mean()),
        "multiclass_brier": v2core.multiclass_brier(classes, probs),
        "calibration": v2core.calibration_report(classes, probs),
        "ats_diagnostic": v2core.full_slate_ats_diagnostic(ats_frame),
        "center_mae": float(np.mean(np.abs(error))),
        "center_rmse": float(np.sqrt(np.mean(error ** 2))),
        "no_key_integer_log_score": float(oof[no_key_col].mean()),
        "key_minus_no_key": float((oof[score_col] - oof[no_key_col]).mean()),
        "per_season": per,
    }


def _paired_comparison(oof: pd.DataFrame, candidate: str, reference: str) -> dict:
    cp = candidate.lower().replace("-", "_")
    rp = reference.lower().replace("-", "_")
    delta_col = f"delta_{cp}_minus_{rp}"
    work = oof[["season", "week", f"{cp}_integer_log_score", f"{rp}_integer_log_score"]].copy()
    work[delta_col] = work[f"{cp}_integer_log_score"] - work[f"{rp}_integer_log_score"]
    season_delta = {
        str(int(season)): float(part[delta_col].mean())
        for season, part in work.groupby("season", sort=True)
    }
    return {
        "candidate": candidate,
        "reference": reference,
        "n": int(len(work)),
        "paired_delta_candidate_minus_reference": float(work[delta_col].mean()),
        "per_season_delta": season_delta,
        "favorable_seasons": int(sum(v < 0.0 for v in season_delta.values())),
        "bootstrap": v2core.paired_week_bootstrap(
            work,
            delta_col,
            resamples=int(CONFIG["bootstrap_resamples"]),
            seed=int(CONFIG["bootstrap_seed"]),
        ),
    }


def _decision(metrics: dict, comparisons: dict, oof: pd.DataFrame) -> dict:
    candidates = ["KMASS-LEVLINE", "KMASS-BLEND"]
    passed: list[str] = []
    evaluations: dict[str, dict] = {}
    per_counts = oof.groupby("season").size().to_dict()
    coverage_pass = len(oof) >= 800 and all(int(per_counts.get(s, 0)) >= 200 for s in OUTER)
    for candidate in candidates:
        comp = comparisons[f"{candidate}_vs_KMASS-MARKET"]
        boot = comp["bootstrap"]
        checks = {
            "aggregate_delta_favorable": comp["paired_delta_candidate_minus_reference"] < 0.0,
            "bootstrap_upper_below_zero": float(boot["ci_97_5"]) < 0.0,
            "favorable_at_least_3_of_4_seasons": int(comp["favorable_seasons"]) >= 3,
            "coverage_gate": bool(coverage_pass),
        }
        evaluations[candidate] = {"checks": checks, "passes": all(checks.values())}
        if all(checks.values()):
            passed.append(candidate)

    if not passed:
        selected = "KMASS-MARKET"
        disposition = "RETAIN_KMASS_MARKET"
    elif len(passed) == 1:
        selected = passed[0]
        disposition = "ADVANCE_NONMARKET_CENTER_TO_NEXT_RESEARCH_STAGE"
    else:
        lev = float(metrics["KMASS-LEVLINE"]["integer_log_score"])
        blend = float(metrics["KMASS-BLEND"]["integer_log_score"])
        selected = "KMASS-LEVLINE" if lev <= blend else "KMASS-BLEND"
        disposition = "ADVANCE_NONMARKET_CENTER_TO_NEXT_RESEARCH_STAGE"
    return {
        "selected_research_center": selected,
        "disposition": disposition,
        "candidate_gate_evaluations": evaluations,
        "production_authorized": False,
    }


def execute(output_dir: Path) -> dict:
    games, data_identity = build_historical_games()
    archive, archive_receipt, fst_receipts = build_center_archive(games)
    oof, tuning = run_outer_folds(archive)

    expected = set(OUTER)
    actual = set(int(x) for x in oof["season"].unique())
    if actual != expected:
        raise HistoricalChallengerError(f"outer season mismatch: {sorted(actual)} != {sorted(expected)}")
    if oof["season"].ge(2026).any():
        raise HistoricalChallengerError("2026 outcome entered OOF result")
    if oof["game_id"].duplicated().any():
        raise HistoricalChallengerError("duplicate OOF game ID")

    candidates = ["KMASS-MARKET", "KMASS-LEVLINE", "KMASS-BLEND"]
    metrics = {candidate: _candidate_metrics(oof, candidate) for candidate in candidates}
    comparisons = {
        "KMASS-LEVLINE_vs_KMASS-MARKET": _paired_comparison(oof, "KMASS-LEVLINE", "KMASS-MARKET"),
        "KMASS-BLEND_vs_KMASS-MARKET": _paired_comparison(oof, "KMASS-BLEND", "KMASS-MARKET"),
        "KMASS-BLEND_vs_KMASS-LEVLINE": _paired_comparison(oof, "KMASS-BLEND", "KMASS-LEVLINE"),
    }
    decision = _decision(metrics, comparisons, oof)

    common_by_season = {
        str(int(season)): int(len(part)) for season, part in oof.groupby("season", sort=True)
    }
    result = {
        "program": CONFIG["program"],
        "status": "COMPLETE",
        "git_sha": _git_sha(),
        "production_changed": False,
        "completed_2026_outcomes_used": 0,
        "outer_test_seasons": list(OUTER),
        "common_rows": int(len(oof)),
        "common_rows_by_season": common_by_season,
        "data_identity": data_identity,
        "center_archive_receipt": archive_receipt,
        "fst_fold_receipts": fst_receipts,
        "metrics": metrics,
        "paired_comparisons": comparisons,
        "decision": decision,
        "v2_nuisance_source": {
            key: V2_FREEZE[key]
            for key in (
                "source_workflow_run", "source_artifact_id", "source_artifact_digest",
                "source_execution_commit_sha", "freeze_rule",
            )
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    oof.sort_values(["season", "week", "game_id"]).to_csv(
        output_dir / "OOF_PREDICTIONS_2022_2025.csv", index=False, lineterminator="\n"
    )
    _json_dump(output_dir / "RESULTS.json", result)
    _json_dump(output_dir / "TUNING_AND_BLEND_WEIGHTS.json", tuning)
    _json_dump(output_dir / "CENTER_ARCHIVE_RECEIPT.json", {
        "archive_rows": int(len(archive)),
        "archive_first_season": int(archive["season"].min()),
        "archive_last_season": int(archive["season"].max()),
        "receipt": archive_receipt,
        "fst_folds": fst_receipts,
    })
    hashes = {
        p.name: _sha256_file(p)
        for p in sorted(output_dir.iterdir())
        if p.is_file() and p.name != "OUTPUT_HASHES.json"
    }
    _json_dump(output_dir / "OUTPUT_HASHES.json", hashes)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(ROOT / "results"))
    args = parser.parse_args()
    result = execute(Path(args.output_dir))
    summary = {
        "status": result["status"],
        "common_rows": result["common_rows"],
        "scores": {
            key: value["integer_log_score"] for key, value in result["metrics"].items()
        },
        "decision": result["decision"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
