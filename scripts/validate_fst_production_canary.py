from __future__ import annotations

"""Fail-closed same-snapshot canary for the F-ST-01 production promotion."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger import fit_future_nested_stack as research_fit_future_nested_stack
from nfl_forecast.challenger_fst import fit_frozen_2026_stack, frozen_stack_probability
from nfl_forecast.features import core_columns
from nfl_forecast.fst_nested_pure import load_frozen_base_oof, load_frozen_training_frame
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

    # Both implementations consume the immutable OOF matrix preserved from the
    # frozen research path. The loader validates bytes, row universe, season/target
    # sequence, and restores the historical index.
    frozen_oof = load_frozen_base_oof(historical=historical)
    training_frame = load_frozen_training_frame(historical=historical)
    research_refit = fit_frozen_2026_stack(training_frame)
    artifact = load_fst_artifact()

    if research_refit.training_data_sha256 != artifact.training_data_sha256:
        raise SystemExit("Frozen research training digest differs from production artifact")
    if research_refit.training_games != artifact.training_games:
        raise SystemExit("Frozen research training game count differs from production artifact")
    if research_refit.training_first_season != artifact.training_first_season:
        raise SystemExit("Frozen research first training season differs from production artifact")
    if research_refit.training_last_season != artifact.training_last_season:
        raise SystemExit("Frozen research last training season differs from production artifact")

    coefficient_deltas = {
        "intercept": abs(research_refit.intercept - artifact.intercept),
        "market_logit_coefficient": abs(
            research_refit.market_logit_coefficient - artifact.market_logit_coefficient
        ),
        "pure_logit_coefficient": abs(
            research_refit.pure_logit_coefficient - artifact.pure_logit_coefficient
        ),
    }
    max_coefficient_delta = max(coefficient_deltas.values(), default=0.0)
    if max_coefficient_delta > TOLERANCE:
        raise SystemExit(
            "Frozen research coefficient reconstruction parity failed: "
            f"max abs diff {max_coefficient_delta:.17g}"
        )

    # Exercise the research nested-PURE implementation against the proposed
    # production implementation on the same historical/current snapshot and same
    # frozen meta OOF.
    research_pure = research_fit_future_nested_stack(
        historical,
        frozen_oof,
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
        # The refit above is only a reconstruction audit. Both research comparator
        # and production must score with the exact frozen registered constants.
        research_final[eligible] = frozen_stack_probability(
            market[eligible],
            research_pure[eligible],
            intercept=artifact.intercept,
            market_logit_coefficient=artifact.market_logit_coefficient,
            pure_logit_coefficient=artifact.pure_logit_coefficient,
        )
    proposed_final = proposed.final_home_prob.to_numpy(dtype=float)
    final_abs = np.full(len(proposed), np.nan, dtype=float)
    final_abs[eligible] = np.abs(research_final[eligible] - proposed_final[eligible])
    max_abs = float(np.nanmax(final_abs)) if eligible.any() else 0.0
    mean_abs = float(np.nanmean(final_abs)) if eligible.any() else 0.0
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
        "away_team": proposed.away_team.astype(str),
        "home_team": proposed.home_team.astype(str),
        "market_home_prob": proposed.market_home_prob,
        "legacy_production_pure": proposed.legacy_pure_home_prob,
        "legacy_75_25_final": proposed.legacy_final_home_prob,
        "fst_nested_pure": proposed.fst_pure_home_prob,
        "research_fst_probability": research_final,
        "proposed_production_fst_probability": proposed.final_home_prob,
        "research_pick": np.where(research_final >= 0.5, proposed.home_team, proposed.away_team),
        "proposed_pick": proposed.pick,
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
        "fst_mean_absolute_difference": mean_abs,
        "reconstruction_coefficient_absolute_deltas": coefficient_deltas,
        "reconstruction_coefficient_max_absolute_difference": max_coefficient_delta,
        "scoring_parameter_source": "registered_frozen_artifact_constants",
        "training_games": artifact.training_games,
        "training_first_season": artifact.training_first_season,
        "training_last_season": artifact.training_last_season,
        "training_data_sha256": artifact.training_data_sha256,
        "intercept": artifact.intercept,
        "market_logit_coefficient": artifact.market_logit_coefficient,
        "pure_logit_coefficient": artifact.pure_logit_coefficient,
        "2026_outcomes_used_in_fitting": artifact.outcomes_2026_used,
        "parity_passed": bool(
            max_abs <= TOLERANCE
            and nested_max <= TOLERANCE
            and max_coefficient_delta <= TOLERANCE
        ),
    }
    Path(args.summary).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(audit.to_csv(index=False))


if __name__ == "__main__":
    main()
