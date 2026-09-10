from __future__ import annotations

"""Forensic-only reconstruction probe for the registered F-ST-01 identity.

This script does not score 2026 games and does not select, tune, or mutate a
candidate. It rebuilds the frozen historical path through 2025 under a declared
numerical runtime, persists the exact pre-fit inputs, and reports whether the
result equals the already-registered F-ST-01 identity.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from threadpoolctl import threadpool_info

from nfl_forecast.challenger_fst import (
    FROZEN_CANDIDATE_ID,
    fit_frozen_2026_stack,
    prepare_frozen_training_frame,
)
from scripts.run_challenger_v08 import build_nested_research, build_research_frame

EXPECTED = {
    "candidate_id": "F-ST-01-FROZEN-2026",
    "training_data_sha256": "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0",
    "training_games": 1615,
    "training_first_season": 2020,
    "training_last_season": 2025,
    "intercept": -0.06954359363166639,
    "market_logit_coefficient": 1.1939087340527093,
    "pure_logit_coefficient": -0.19342747983803402,
}
BASE_COLUMNS = ("logistic", "extra_trees", "xgboost", "catboost", "home_win", "season")
TRAINING_COLUMNS = ("season", "home_win", "market_prob", "pure_prob")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keyed(historical: pd.DataFrame, frame: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
    if not historical.index.is_unique or not frame.index.is_unique:
        raise RuntimeError("Forensic reconstruction requires unique dataframe indexes")
    missing = frame.index.difference(historical.index)
    if len(missing):
        raise RuntimeError(f"Forensic frame contains {len(missing)} rows absent from historical frame")
    game_id = historical.loc[frame.index, "game_id"].astype(str)
    if game_id.isna().any() or game_id.str.strip().eq("").any() or game_id.duplicated().any():
        raise RuntimeError("Forensic reconstruction requires unique non-empty game_id values")
    keyed = frame.loc[:, list(columns)].copy()
    keyed.insert(0, "row_position", np.arange(len(keyed), dtype=int))
    keyed.insert(0, "game_id", game_id.to_numpy())
    return keyed


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")


def _lscpu() -> dict:
    try:
        raw = subprocess.check_output(["lscpu", "-J"], text=True)
        return json.loads(raw)
    except Exception as exc:  # diagnostic only
        return {"error": repr(exc)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cfg, historical, _current, feature_sets, _, _ = build_research_frame(args.config)
    seed = int(cfg["model"]["random_state"])
    features = feature_sets["production_compatible"]
    base_oof, research = build_nested_research(historical, features, seed)

    prepared = prepare_frozen_training_frame(research)
    training = research.loc[prepared.index, list(TRAINING_COLUMNS)].copy()
    if pd.to_numeric(training["season"], errors="raise").max() > 2025:
        raise RuntimeError("Forensic probe may not use post-2025 outcomes")

    keyed_oof = _keyed(historical, base_oof, BASE_COLUMNS)
    keyed_training = _keyed(historical, training, TRAINING_COLUMNS)
    oof_path = out / "base_oof_keyed.csv"
    training_path = out / "training_frame_keyed.csv"
    _write_csv(keyed_oof, oof_path)
    _write_csv(keyed_training, training_path)

    fit = fit_frozen_2026_stack(training)
    actual = {"candidate_id": FROZEN_CANDIDATE_ID, **fit.as_dict()}
    compare_fields = [
        "candidate_id",
        "training_data_sha256",
        "training_games",
        "training_first_season",
        "training_last_season",
        "intercept",
        "market_logit_coefficient",
        "pure_logit_coefficient",
    ]
    mismatches = [field for field in compare_fields if actual[field] != EXPECTED[field]]

    result = {
        "purpose": "forensic_reconstruction_only",
        "uses_2026_outcomes_for_fitting_or_selection": False,
        "expected": EXPECTED,
        "actual": actual,
        "matches_registered_identity": not mismatches,
        "mismatched_fields": mismatches,
        "pre_fit_artifacts": {
            "base_oof_rows": int(len(keyed_oof)),
            "base_oof_raw_sha256": _sha256(oof_path),
            "training_rows": int(len(keyed_training)),
            "training_frame_raw_sha256": _sha256(training_path),
        },
        "runtime": {
            "probe_coretype": os.environ.get("PROBE_CORETYPE"),
            "openblas_coretype": os.environ.get("OPENBLAS_CORETYPE"),
            "openblas_num_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
            "omp_num_threads": os.environ.get("OMP_NUM_THREADS"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "threadpools": threadpool_info(),
            "lscpu": _lscpu(),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        },
    }
    result_path = out / f"result_{os.environ.get('PROBE_CORETYPE', 'UNKNOWN')}.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
