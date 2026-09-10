from __future__ import annotations

"""Fail-closed same-snapshot canary for the F-ST-01 production promotion."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger import (
    build_base_oof_predictions as research_build_base_oof,
    fit_future_nested_stack as research_fit_future_nested_stack,
)
from nfl_forecast.challenger_fst import fit_frozen_2026_stack, frozen_stack_probability
from nfl_forecast.features import core_columns
from nfl_forecast.fst_nested_pure import build_base_oof_predictions, build_fst_training_frame
from nfl_forecast.fst_production import load_fst_artifact
from nfl_forecast.pipeline import run

TOLERANCE = 1e-12


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output", default="deployment_audits/fst_predeploy_canary.csv")
    parser.add_argument("--summary", default="deployment_audits/fst_predeploy_canary.json")
    args = parser.parse_args()

    artifacts = run(args.config, season_to_predict=2026, snapshot_type="CANARY")
    proposed = artifacts.predictions.copy()
    games = artifacts.games.copy()
    historical = games[
        games.home_win.notna()
        & pd.to_numeric(games.season, errors="coerce").le(2025)
    ].copy()
    features = core_columns(historical)
    seed = 26

    # Both implementations consume the exact same materialized games/current frames.
    prod_oof = build_base_oof_predictions(
        historical, features, seed=seed, validation_start=2018, validation_end=2025
    )
    training_frame = build_fst_training_frame(historical, prod_oof, seed=seed)
    research_fit = fit_frozen_2026_stack(training_frame)
    artifact = load_fst_artifact()
    for label, actual, expected in (
        ("intercept", research_fit.intercept, artifact.intercept),
        ("market coefficient", research_fit.market_logit_coefficient, artifact.market_logit_coefficient),
        ("PURE coefficient", research_fit.pure_logit_coefficient, artifact.pure_logit_coefficient),
    ):
        if actual != expected:
            raise SystemExit(f"Frozen research {label} mismatch: {actual!r} != {expected!r}")
    if research_fit.training_data_sha256 != artifact.training_data_sha256:
        raise SystemExit("Frozen research training digest differs from production artifact")
    if research_fit.training_games != artifact.training_games:
        raise SystemExit("Frozen research training game count differs from production artifact")

    research_oof = research_build_base_oof(
        historical,
        features,
        seed=seed,
        validation_start=2018,
        validation_end=2025,
    )
    research_pure = research_fit_future_nested_stack(
        historical,
        research_oof,
        proposed,
        features,
        seed=seed,
    )
    proposed_pure = proposed.fst_pure_home_prob.to_numpy(dtype=float)
    nested_abs = np.abs(research_pure - proposed_pure)
    nested_max = float(nested_abs.max()) if len(nested_abs) else 0.0
    if nested_max > TOLERANCE:
        raise SystemExit(f"Nested PURE parity failed: max abs diff {nested_max:.17g}")

    market = pd.to_numeric(proposed.market_home_prob, errors="coerce").to_numpy(dtype=float)
    eligible = np.isfinite(market)
    research_final = np.full(len(proposed), np.nan, dtype=float)
    if eligible.any():
        research_final[eligible] = frozen_stack_probability(
            market[eligible],
            research_pure[eligible],
            intercept=research_fit.intercept,
            market_logit_coefficient=research_fit.market_logit_coefficient,
            pure_logit_coefficient=research_fit.pure_logit_coefficient,
        )
    proposed_final = proposed.final_home_prob.to_numpy(dtype=float)
    final_abs = np.full(len(proposed), np.nan, dtype=float)
    final_abs[eligible] = np.abs(research_final[eligible] - proposed_final[eligible])
    max_abs = float(np.nanmax(final_abs)) if eligible.any() else 0.0
    if max_abs > TOLERANCE:
        raise SystemExit(f"F-ST shadow→production parity failed: max abs diff {max_abs:.17g}")

    legacy_expected = proposed.legacy_pure_home_prob.copy()
    usable_market = pd.Series(eligible, index=proposed.index)
    legacy_expected.loc[usable_market] = (
        0.75 * proposed.loc[usable_market, "legacy_pure_home_prob"]
        + 0.25 * proposed.loc[usable_market, "market_home_prob"]
    )
    np.testing.assert_array_equal(
        proposed.legacy_final_home_prob.to_numpy(dtype=float),
        legacy_expected.to_numpy(dtype=float),
    )

    source_sha = os.environ.get("GITHUB_SHA") or os.environ.get("LEVLINE_SOURCE_SHA") or "unknown"
    audit = pd.DataFrame({
        "game_id": proposed.game_id.astype(str),
        "market_home_prob": proposed.market_home_prob,
        "legacy_production_pure": proposed.legacy_pure_home_prob,
        "legacy_75_25_final": proposed.legacy_final_home_prob,
        "fst_nested_pure": proposed.fst_pure_home_prob,
        "research_fst_probability": research_final,
        "proposed_production_fst_probability": proposed.final_home_prob,
        "absolute_difference": final_abs,
        "intercept": artifact.intercept,
        "market_logit_coefficient": artifact.market_logit_coefficient,
        "pure_logit_coefficient": artifact.pure_logit_coefficient,
        "training_data_sha256": artifact.training_data_sha256,
        "source_sha": source_sha,
        "fst_fallback": proposed.fst_fallback,
        "fst_fallback_reason": proposed.fst_fallback_reason,
    })
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(out, index=False)
    summary = {
        "candidate_id": artifact.candidate_id,
        "source_sha": source_sha,
        "tolerance": TOLERANCE,
        "games": int(len(audit)),
        "games_using_fst": int(eligible.sum()),
        "fallback_games": int((~eligible).sum()),
        "nested_pure_max_absolute_difference": nested_max,
        "fst_max_absolute_difference": max_abs,
        "training_games": artifact.training_games,
        "training_first_season": artifact.training_first_season,
        "training_last_season": artifact.training_last_season,
        "training_data_sha256": artifact.training_data_sha256,
        "intercept": artifact.intercept,
        "market_logit_coefficient": artifact.market_logit_coefficient,
        "pure_logit_coefficient": artifact.pure_logit_coefficient,
        "2026_outcomes_used_in_fitting": artifact.outcomes_2026_used,
        "parity_passed": bool(max_abs <= TOLERANCE and nested_max <= TOLERANCE),
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(audit.to_csv(index=False))


if __name__ == "__main__":
    main()
