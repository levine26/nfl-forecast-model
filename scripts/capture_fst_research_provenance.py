from __future__ import annotations

"""Capture stable game-keyed provenance for the exact frozen F-ST research fit.

This is validation/research tooling only. Production code never imports this module.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_fst import fit_frozen_2026_stack
from scripts.run_challenger_v08 import build_nested_research, build_research_frame

EXPECTED_DIGEST = "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0"
EXPECTED_INTERCEPT = -0.06954359363166639
EXPECTED_MARKET_COEF = 1.1939087340527093
EXPECTED_PURE_COEF = -0.19342747983803402
EXPECTED_GAMES = 1615
EXPECTED_FIRST_SEASON = 2020
EXPECTED_LAST_SEASON = 2025
NUMERIC_TOLERANCE = 1e-12


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="deployment_audits/research_provenance")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cfg, historical, _, feature_sets, _, _ = build_research_frame(args.config)
    seed = int(cfg["model"]["random_state"])
    base_features = feature_sets["production_compatible"]
    base_oof, research = build_nested_research(historical, base_features, seed)
    fit = fit_frozen_2026_stack(research)

    coefficient_deltas = {
        "intercept": abs(fit.intercept - EXPECTED_INTERCEPT),
        "market_logit_coefficient": abs(fit.market_logit_coefficient - EXPECTED_MARKET_COEF),
        "pure_logit_coefficient": abs(fit.pure_logit_coefficient - EXPECTED_PURE_COEF),
    }
    exact_identity_matches = bool(
        fit.training_data_sha256 == EXPECTED_DIGEST
        and fit.training_games == EXPECTED_GAMES
        and fit.training_first_season == EXPECTED_FIRST_SEASON
        and fit.training_last_season == EXPECTED_LAST_SEASON
    )
    numeric_parity_matches = bool(
        max(coefficient_deltas.values(), default=0.0) <= NUMERIC_TOLERANCE
    )
    summary = {
        "training_data_sha256": fit.training_data_sha256,
        "training_games": fit.training_games,
        "training_first_season": fit.training_first_season,
        "training_last_season": fit.training_last_season,
        "intercept": fit.intercept,
        "market_logit_coefficient": fit.market_logit_coefficient,
        "pure_logit_coefficient": fit.pure_logit_coefficient,
        "coefficient_absolute_deltas": coefficient_deltas,
        "numeric_parity_tolerance": NUMERIC_TOLERANCE,
        "base_oof_rows": int(len(base_oof)),
        "base_oof_first_season": int(pd.to_numeric(base_oof.season).min()),
        "base_oof_last_season": int(pd.to_numeric(base_oof.season).max()),
        "feature_count": int(len(base_features)),
        "exact_training_identity_matches": exact_identity_matches,
        "numeric_refit_parity_matches": numeric_parity_matches,
        "frozen_identity_matches": bool(exact_identity_matches and numeric_parity_matches),
        "authoritative_scoring_source": "registered_frozen_artifact_constants",
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if historical.index.duplicated().any():
        raise SystemExit("Research historical index is not unique; cannot key frozen OOF")
    missing_oof = base_oof.index.difference(historical.index)
    missing_training = research.index.difference(historical.index)
    if len(missing_oof) or len(missing_training):
        raise SystemExit(
            f"Research provenance index mismatch: base_oof={len(missing_oof)} training={len(missing_training)}"
        )

    keyed_oof = base_oof.copy()
    keyed_oof.insert(0, "game_id", historical.loc[base_oof.index, "game_id"].astype(str).to_numpy())
    if keyed_oof.game_id.duplicated().any():
        raise SystemExit("Research base OOF game_id is not unique")
    keyed_oof.to_csv(out / "base_oof_keyed.csv", index=False)

    keyed_training = research[["season", "home_win", "market_prob", "pure_prob"]].copy()
    keyed_training.insert(
        0,
        "game_id",
        historical.loc[research.index, "game_id"].astype(str).to_numpy(),
    )
    if keyed_training.game_id.duplicated().any():
        raise SystemExit("Research F-ST training game_id is not unique")
    keyed_training.to_csv(out / "training_frame_keyed.csv", index=False)

    print(json.dumps(summary, indent=2))
    if not exact_identity_matches:
        raise SystemExit(
            "Current research path does not reproduce the frozen F-ST training identity; "
            "do not promote a reconstructed mapping"
        )
    if not numeric_parity_matches:
        raise SystemExit(
            "Current research refit exceeds the fixed 1e-12 coefficient parity bound; "
            "do not promote a reconstructed mapping"
        )


if __name__ == "__main__":
    main()
