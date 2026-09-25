from __future__ import annotations

"""Chronology-strict entrypoint for ATS cross-market transfer V1.

The frozen outer candidates are unchanged. This entrypoint tightens only the inner
alpha/beta selection evaluation: every prior validation season is scored with a KMASS
nuisance fit trained strictly before that validation season. The accepted frozen V2
fits are reused for 2022-2025. A 2021 nuisance fit is constructed once from pre-2021
history with the already-frozen CONSTANT_SCALE_KEY hyperparameters (nu=30,
lambda_scale=10, lambda_key=1, conditional=False, use_key=True).

For execution speed only, the deterministic KMASS base parts for an inner-validation
game are cached by season/game_id. This changes no probability, loss, grid or selection
rule; each cached object is computed with the same season-forward nuisance fit.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import probability_only_entrypoint as probability_entry

runner = probability_entry.runner
ROOT = Path(__file__).resolve().parent
_PRE2021_FIT: dict[str, Any] | None = None
_PRE2021_RECEIPT: dict[str, Any] | None = None
_INNER_PARTS_CACHE: dict[tuple[int, str], dict] = {}


def _build_pre2021_fit() -> tuple[dict, dict]:
    global _PRE2021_FIT, _PRE2021_RECEIPT
    if _PRE2021_FIT is not None and _PRE2021_RECEIPT is not None:
        return _PRE2021_FIT, _PRE2021_RECEIPT
    games, identity = runner.hist.build_historical_games()
    train = games[games["season"] < 2021].copy()
    required = ["actual_margin", "market_margin", "total_line", "spread_line"]
    train = train.dropna(subset=required)
    if len(train) < 100 or int(train["season"].max()) >= 2021:
        raise runner.CrossMarketError("invalid pre-2021 KMASS nuisance training frame")
    fit = runner.v2.fit_m4(
        train,
        nu=30,
        lambda_scale=10.0,
        lambda_key=1.0,
        conditional=False,
        use_key=True,
    )
    receipt = {
        "validation_season": 2021,
        "training_n": int(len(train)),
        "training_first_season": int(train["season"].min()),
        "training_last_season": int(train["season"].max()),
        "hyperparameters_inherited_from_accepted_constant_scale_key": {
            "nu": 30,
            "lambda_scale": 10.0,
            "lambda_key": 1.0,
            "conditional": False,
            "use_key": True,
        },
        "fit": fit,
        "historical_identity": identity,
    }
    _PRE2021_FIT, _PRE2021_RECEIPT = fit, receipt
    return fit, receipt


def _inner_fit(season: int) -> dict:
    season = int(season)
    if season == 2021:
        return _build_pre2021_fit()[0]
    if season in runner.OUTER:
        return runner._fit_for_season(season)
    raise runner.CrossMarketError(f"no chronology-clean inner KMASS fit for season {season}")


def _inner_parts(row: pd.Series) -> dict:
    season = int(row["season"])
    game_id = str(row["game_id"])
    key = (season, game_id)
    cached = _INNER_PARTS_CACHE.get(key)
    if cached is not None:
        return cached
    parts = runner._base_parts(row, _inner_fit(season))
    _INNER_PARTS_CACHE[key] = parts
    return parts


def _strict_select_alpha(train: pd.DataFrame, ignored_outer_fit: dict) -> tuple[float, list[dict]]:
    rows = []
    for alpha in runner.ALPHAS:
        losses = []
        by_season: dict[int, list[float]] = {}
        for _, row in train.iterrows():
            season = int(row["season"])
            parts = _inner_parts(row)
            u = runner._target_prob(float(row["market_prob"]), float(row["fst_home_prob"]), alpha)
            probs = runner._iproj_cpl(parts, u)
            loss = runner._cpl_loss(
                runner._observed_class(int(row["actual_margin"]), float(row["spread_line"])),
                probs,
            )
            losses.append(loss)
            by_season.setdefault(season, []).append(loss)
        rows.append({
            "alpha": float(alpha),
            "n": int(len(losses)),
            "cpl_log_loss": float(np.mean(losses)),
            "season_forward_inner": True,
            "per_season": {str(s): float(np.mean(v)) for s, v in sorted(by_season.items())},
        })
    best = min(rows, key=lambda r: (r["cpl_log_loss"], r["alpha"]))
    return float(best["alpha"]), rows


def _strict_select_beta(train: pd.DataFrame, ignored_outer_fit: dict) -> tuple[float, list[dict]]:
    rows = []
    for beta in runner.BETAS:
        losses = []
        by_season: dict[int, list[float]] = {}
        for _, row in train.iterrows():
            season = int(row["season"])
            parts = _inner_parts(row)
            c0 = parts["p_cover"] / max(parts["p_cover"] + parts["p_loss"], runner.EPS)
            d = float(runner._logit([row["fst_home_prob"]])[0] - runner._logit([row["market_prob"]])[0])
            c = float(runner.expit(float(runner._logit([c0])[0]) + float(beta) * d))
            probs = (
                (1.0 - parts["p_push"]) * c,
                parts["p_push"],
                (1.0 - parts["p_push"]) * (1.0 - c),
            )
            loss = runner._cpl_loss(
                runner._observed_class(int(row["actual_margin"]), float(row["spread_line"])),
                probs,
            )
            losses.append(loss)
            by_season.setdefault(season, []).append(loss)
        rows.append({
            "beta": float(beta),
            "n": int(len(losses)),
            "cpl_log_loss": float(np.mean(losses)),
            "season_forward_inner": True,
            "per_season": {str(s): float(np.mean(v)) for s, v in sorted(by_season.items())},
        })
    best = min(rows, key=lambda r: (r["cpl_log_loss"], r["beta"]))
    return float(best["beta"]), rows


def _write_inner_receipt(output_dir: Path) -> None:
    _, pre = _build_pre2021_fit()
    payload = {
        "status": "PASS",
        "selection_rule": "each inner validation season uses nuisance fit trained strictly before that season",
        "2021_nuisance": pre,
        "2022_2025_nuisance_source": "research/ats-historical-challenger/v2_nuisance_freeze.json",
        "frozen_outer_fit_seasons": [2022, 2023, 2024, 2025],
        "target_season_never_used_to_choose_alpha_beta": True,
        "inner_parts_cache_is_deterministic_execution_optimization_only": True,
    }
    (output_dir / "INNER_CHRONOLOGY_RECEIPT.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    # probability_only_entrypoint has already replaced the historical scaffold and
    # center archive with exact, hard-gated probability-only equivalents. Replace only
    # the two inner selection functions.
    runner._select_alpha = _strict_select_alpha
    runner._select_beta = _strict_select_beta
    result = runner.run(args.output_dir)
    _write_inner_receipt(args.output_dir)
    print(json.dumps({
        "common_rows": result["common_rows"],
        "selection": [
            {"season": x["season"], "alpha": x["alpha_selected"], "beta": x["beta_selected"]}
            for x in result["chronology_selection"]
        ],
        "implementation_candidates": result["implementation_candidates"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
