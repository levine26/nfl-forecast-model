from __future__ import annotations

"""Test a preserved freeze-era base OOF artifact against the frozen F-ST identity.

Diagnostic tooling only. This does not modify production outputs or authorize promotion.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_fst import fit_frozen_2026_stack
from nfl_forecast.fst_nested_pure import BASE_MODEL_NAMES, build_fst_training_frame
from scripts.run_challenger_v08 import build_research_frame

EXPECTED_DIGEST = "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0"
EXPECTED_INTERCEPT = -0.06954359363166639
EXPECTED_MARKET_COEF = 1.1939087340527093
EXPECTED_PURE_COEF = -0.19342747983803402
EXPECTED_GAMES = 1615


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument(
        "--oof",
        default="src/nfl_forecast/artifacts/diagnostic-F-ST-preexisting-oof.csv",
    )
    parser.add_argument(
        "--output-dir",
        default="deployment_audits/preserved_oof_diagnostic",
    )
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = Path(args.oof)
    raw = path.read_bytes()
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    candidate = pd.read_csv(path)
    required = [*BASE_MODEL_NAMES, "home_win", "season"]
    if list(candidate.columns) != required:
        raise SystemExit(f"Preserved OOF schema mismatch: {list(candidate.columns)!r}")

    cfg, historical, _, feature_sets, _, _ = build_research_frame(args.config)
    seed = int(cfg["model"]["random_state"])

    hist_season = pd.to_numeric(historical["season"], errors="coerce")
    hist_target = pd.to_numeric(historical["home_win"], errors="coerce")
    mask = hist_season.between(2018, 2025) & hist_target.notna()
    reference = historical.loc[mask, ["game_id", "season", "home_win"]].sort_index().copy()
    if not reference.index.is_unique:
        raise SystemExit("Historical reference index is not unique")
    if len(reference) != len(candidate):
        raise SystemExit(f"Preserved OOF row mismatch: {len(candidate)} != {len(reference)}")
    if not np.array_equal(
        pd.to_numeric(candidate["season"]).astype(int).to_numpy(),
        pd.to_numeric(reference["season"]).astype(int).to_numpy(),
    ):
        raise SystemExit("Preserved OOF season sequence does not match historical reference")
    if not np.array_equal(
        pd.to_numeric(candidate["home_win"]).astype(int).to_numpy(),
        pd.to_numeric(reference["home_win"]).astype(int).to_numpy(),
    ):
        raise SystemExit("Preserved OOF target sequence does not match historical reference")

    candidate.index = reference.index
    training = build_fst_training_frame(historical, candidate, seed=seed)
    fit = fit_frozen_2026_stack(training)

    keyed_training = training.copy()
    keyed_training.insert(
        0,
        "game_id",
        historical.loc[training.index, "game_id"].astype(str).to_numpy(),
    )
    if keyed_training["game_id"].duplicated().any():
        raise SystemExit("Preserved OOF training game_id is not unique")
    keyed_training.to_csv(out / "training_frame_keyed.csv", index=False)

    keyed_oof = candidate.copy()
    keyed_oof.insert(
        0,
        "game_id",
        historical.loc[candidate.index, "game_id"].astype(str).to_numpy(),
    )
    keyed_oof.to_csv(out / "base_oof_keyed.csv", index=False)

    summary = {
        "candidate_oof_path": str(path),
        "candidate_oof_sha256": raw_sha256,
        "candidate_oof_rows": int(len(candidate)),
        "candidate_oof_first_season": int(pd.to_numeric(candidate["season"]).min()),
        "candidate_oof_last_season": int(pd.to_numeric(candidate["season"]).max()),
        "feature_count": int(len(feature_sets["production_compatible"])),
        "training_data_sha256": fit.training_data_sha256,
        "training_games": fit.training_games,
        "training_first_season": fit.training_first_season,
        "training_last_season": fit.training_last_season,
        "intercept": fit.intercept,
        "market_logit_coefficient": fit.market_logit_coefficient,
        "pure_logit_coefficient": fit.pure_logit_coefficient,
        "frozen_digest_matches": fit.training_data_sha256 == EXPECTED_DIGEST,
        "frozen_coefficients_match_exactly": bool(
            fit.intercept == EXPECTED_INTERCEPT
            and fit.market_logit_coefficient == EXPECTED_MARKET_COEF
            and fit.pure_logit_coefficient == EXPECTED_PURE_COEF
        ),
        "frozen_identity_matches": bool(
            fit.training_data_sha256 == EXPECTED_DIGEST
            and fit.training_games == EXPECTED_GAMES
            and fit.intercept == EXPECTED_INTERCEPT
            and fit.market_logit_coefficient == EXPECTED_MARKET_COEF
            and fit.pure_logit_coefficient == EXPECTED_PURE_COEF
        ),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
