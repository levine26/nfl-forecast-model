from __future__ import annotations

"""Materialize the frozen F-ST-01 candidate into the research-only live shadow slate.

Historical reconstruction is verified under the recovered frozen-candidate runtime.
Current-game nested-PURE scoring is isolated into a native-CPU subprocess because a
forced historical OpenBLAS core type is not a safe execution target on heterogeneous
hosted runners. Final F-ST scoring always uses registered frozen coefficient literals.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

from nfl_forecast.challenger_fst import (
    FROZEN_CANDIDATE_ID,
    FROZEN_FEATURE_SET,
    FROZEN_METHOD,
    fit_frozen_2026_stack,
    frozen_stack_probability,
)
from nfl_forecast.fst_nested_pure import load_frozen_base_oof, load_frozen_training_frame
from nfl_forecast.fst_provenance import (
    TRAINING_COLUMNS,
    capture_fst_pre_fit_provenance,
    write_fst_fit_provenance,
)
from nfl_forecast.fst_reconstruction import (
    frozen_fit_from_identity,
    require_fst_reconstruction_runtime,
    verify_fst_reconstruction_identity,
)
from scripts.run_challenger_v08 import SHADOW_BASE_COLUMNS, build_research_frame

SPEC_PATH = Path("research/fst/F-ST-01-FROZEN-2026.json")


def _load_spec() -> dict:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if spec.get("candidate_id") != FROZEN_CANDIDATE_ID:
        raise RuntimeError("Frozen F-ST candidate spec identity mismatch")
    if spec.get("production_promotion_authorized") is not False:
        raise RuntimeError("Frozen F-ST spec must explicitly prohibit production promotion")
    if not isinstance(spec.get("frozen_identity"), dict):
        raise RuntimeError("Frozen F-ST spec must include the registered frozen identity")
    return spec


def _training_frame_on_historical_index(
    historical: pd.DataFrame,
    frozen_training: pd.DataFrame,
) -> pd.DataFrame:
    """Restore frozen training rows to the current historical frame's game-keyed index."""

    if "game_id" not in historical.columns or not historical.index.is_unique:
        raise RuntimeError("Historical frame cannot support frozen F-ST game-key alignment")
    historical_ids = historical["game_id"].astype(str)
    if historical_ids.duplicated().any():
        raise RuntimeError("Historical frame contains duplicate game IDs")
    lookup = pd.Series(historical.index.to_numpy(), index=historical_ids.to_numpy())

    game_ids = frozen_training["game_id"].astype(str)
    missing = sorted(set(game_ids) - set(lookup.index))
    if missing:
        raise RuntimeError(
            f"Frozen F-ST training frame is missing {len(missing)} games from historical data"
        )
    aligned = frozen_training.loc[:, list(TRAINING_COLUMNS)].copy()
    aligned.index = pd.Index([lookup.at[game_id] for game_id in game_ids])
    if not aligned.index.is_unique:
        raise RuntimeError("Frozen F-ST training alignment produced duplicate historical indexes")
    return aligned


def _score_current_pure_native(
    historical: pd.DataFrame,
    base_oof: pd.DataFrame,
    current: pd.DataFrame,
    feature_cols: list[str],
    *,
    seed: int,
) -> np.ndarray:
    """Run only live base-model fitting outside the forced forensic CPU architecture."""

    with tempfile.TemporaryDirectory(prefix="levline-fst-native-") as raw_tmp:
        tmp = Path(raw_tmp)
        historical_path = tmp / "historical.pkl"
        base_oof_path = tmp / "base_oof.pkl"
        current_path = tmp / "current.pkl"
        features_path = tmp / "features.json"
        output_path = tmp / "current_pure.npy"
        historical.to_pickle(historical_path)
        base_oof.to_pickle(base_oof_path)
        current.to_pickle(current_path)
        features_path.write_text(json.dumps(feature_cols), encoding="utf-8")

        env = os.environ.copy()
        # OPENBLAS_CORETYPE selects an instruction-set implementation. Retain benign
        # thread-count controls but let OpenBLAS detect the actual hosted CPU.
        env.pop("OPENBLAS_CORETYPE", None)
        subprocess.run(
            [
                sys.executable,
                "scripts/run_fst_native_pure_score.py",
                "--historical",
                str(historical_path),
                "--base-oof",
                str(base_oof_path),
                "--current",
                str(current_path),
                "--features",
                str(features_path),
                "--output",
                str(output_path),
                "--seed",
                str(seed),
            ],
            check=True,
            env=env,
        )
        probability = np.load(output_path, allow_pickle=False)
    values = np.asarray(probability, dtype=float)
    if len(values) != len(current) or not np.isfinite(values).all():
        raise RuntimeError("Native F-ST current PURE subprocess returned invalid probabilities")
    return values


def run(config_path: str = "config/model.yaml", output_dir: str = "challenger_outputs") -> dict:
    out = Path(output_dir)
    slate_path = out / "candidate_shadow_slate.csv"
    if not slate_path.exists():
        raise RuntimeError("v0.8 candidate shadow slate must exist before F-ST materialization")

    spec = _load_spec()
    registered = spec["frozen_identity"]
    runtime_check = require_fst_reconstruction_runtime()
    authoritative_fit = frozen_fit_from_identity(registered)

    cfg, historical, current, feature_sets, _, _ = build_research_frame(config_path)
    seed = int(cfg["model"]["random_state"])
    base_features = feature_sets["production_compatible"]

    # Use immutable forensic artifacts recovered from the successful frozen-candidate
    # workflow rather than regenerating base OOF. Their loaders verify compressed/raw
    # hashes, row identity/order, outcomes, training digest and historical season bounds.
    base_oof = load_frozen_base_oof(historical=historical)
    frozen_training = load_frozen_training_frame(historical=historical)
    training_for_fit = _training_frame_on_historical_index(historical, frozen_training)

    provenance_dir = out / "fst" / "provenance"
    input_provenance = capture_fst_pre_fit_provenance(
        historical,
        base_oof,
        training_for_fit,
        provenance_dir,
        candidate_id=FROZEN_CANDIDATE_ID,
        capture_context="prospective_shadow_reconstruction",
    )

    # This small two-input refit remains under the recovered reconstruction runtime and
    # exists only to verify historical identity. It is never used to score current games.
    reconstruction_fit = fit_frozen_2026_stack(training_for_fit)
    fit_provenance = write_fst_fit_provenance(
        provenance_dir, input_provenance, reconstruction_fit
    )
    identity_check = verify_fst_reconstruction_identity(
        provenance_dir,
        input_provenance,
        reconstruction_fit,
        registered,
    )

    # CPU-heavy current base-model fitting is portable and isolated from the historical
    # architecture pin. The frozen OOF matrix is still the meta-model input universe.
    current_pure = _score_current_pure_native(
        historical,
        base_oof,
        current,
        base_features,
        seed=seed,
    )
    current_market = pd.to_numeric(current.market_home_prob, errors="coerce").to_numpy(dtype=float)
    preview = frozen_stack_probability(
        current_market,
        current_pure,
        intercept=authoritative_fit.intercept,
        market_logit_coefficient=authoritative_fit.market_logit_coefficient,
        pure_logit_coefficient=authoritative_fit.pure_logit_coefficient,
    )

    fst = current[SHADOW_BASE_COLUMNS].copy()
    fst["challenger_pure_home_prob"] = np.asarray(current_pure, dtype=float)
    fst["market_home_prob"] = current_market
    fst["challenger_final_home_prob"] = preview
    fst["challenger_pick"] = np.where(preview >= 0.5, fst.home_team, fst.away_team)
    fst["effective_pure_weight"] = np.nan
    fst["effective_market_weight"] = np.nan
    fst["research_candidate"] = "F-ST-01"
    fst["research_method"] = FROZEN_METHOD
    fst["research_feature_set"] = FROZEN_FEATURE_SET
    fst["challenger_version"] = FROZEN_CANDIDATE_ID
    fst["selected_shadow_candidate"] = True
    fst["training_cutoff"] = "2025"
    fst["training_games"] = authoritative_fit.training_games
    fst["training_first_season"] = authoritative_fit.training_first_season
    fst["training_last_season"] = authoritative_fit.training_last_season
    fst["training_data_sha256"] = authoritative_fit.training_data_sha256
    fst["stack_intercept"] = authoritative_fit.intercept
    fst["stack_market_logit_coefficient"] = authoritative_fit.market_logit_coefficient
    fst["stack_pure_logit_coefficient"] = authoritative_fit.pure_logit_coefficient
    fst["candidate_freeze_utc"] = spec["freeze_timestamp_utc"]
    fst["candidate_code_sha"] = spec["freeze_implementation_sha"]

    slate = pd.read_csv(slate_path)
    slate["selected_shadow_candidate"] = False
    slate = pd.concat([slate, fst], ignore_index=True, sort=False)
    identity = ["game_id", "challenger_version", "research_candidate"]
    if slate.duplicated(identity).any():
        raise RuntimeError("Duplicate frozen F-ST candidate identity in shadow slate")
    selected_per_game = slate.groupby("game_id").selected_shadow_candidate.sum()
    if not selected_per_game.eq(1).all():
        raise RuntimeError("Frozen F-ST must be the sole selected research shadow per game")

    reconstruction_dict = reconstruction_fit.as_dict()
    authoritative_dict = authoritative_fit.as_dict()
    runtime = {
        "candidate_id": FROZEN_CANDIDATE_ID,
        "mode": "research_only_frozen_shadow",
        "target_season": 2026,
        "training_cutoff": 2025,
        "2026_outcomes_used_in_fitting": 0,
        "production_promotion_authorized": False,
        **authoritative_dict,
        "scoring_parameter_source": "registered_frozen_identity",
        "base_oof_source": "immutable_recovered_forensic_artifact",
        "training_frame_source": "immutable_recovered_forensic_artifact",
        "reconstruction_fit": reconstruction_dict,
        "reconstruction_execution_policy": "recovered_runtime_against_immutable_inputs",
        "current_pure_execution_policy": "native_cpu_subprocess_with_frozen_oof",
        "reconstruction_runtime": runtime_check,
        "freeze_timestamp_utc": spec["freeze_timestamp_utc"],
        "freeze_implementation_sha": spec["freeze_implementation_sha"],
        "provenance": {
            "capture_stage": "pre_fit",
            "capture_context": input_provenance["capture_context"],
            "inputs_manifest": "fst/provenance/inputs_manifest.json",
            "fit_manifest": "fst/provenance/fit_manifest.json",
            "frozen_identity_check": "fst/provenance/frozen_identity_check.json",
            "frozen_identity_verified": bool(identity_check["matches"]),
            "frozen_identity_source": identity_check["expected_source"],
            "numeric_abs_tolerance": identity_check["refit_abs_tolerance"],
            "numeric_absolute_deltas": identity_check["numerical_absolute_deltas"],
            "base_oof_raw_sha256": input_provenance["base_oof"]["raw_sha256"],
            "training_frame_raw_sha256": input_provenance["training_frame"]["raw_sha256"],
            "training_frame_canonical_game_keyed_sha256": input_provenance["training_frame"][
                "canonical_game_keyed_sha256"
            ],
            "inputs_manifest_sha256": fit_provenance["inputs_manifest_sha256"],
        },
    }

    slate.to_csv(slate_path, index=False)
    fst.to_csv(out / "this_week_shadow.csv", index=False)
    model_dir = out / "fst"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "runtime_model.json").write_text(json.dumps(runtime, indent=2), encoding="utf-8")

    report_path = out / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update({
        "selected_shadow_candidate": "F-ST-01",
        "selected_shadow_method": FROZEN_METHOD,
        "selected_shadow_feature_set": FROZEN_FEATURE_SET,
        "selected_shadow_version": FROZEN_CANDIDATE_ID,
        "shadow_candidate_count": int(slate.research_candidate.nunique()),
        "current_shadow_candidate_rows": int(len(slate)),
        "current_shadow_games": int(len(fst)),
        "frozen_fst": runtime,
        "2026_outcomes_used_in_fitting": 0,
        "production_outputs_modified": 0,
        "promotion_authorized": False,
    })
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(runtime, indent=2))
    return runtime


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output-dir", default="challenger_outputs")
    args = parser.parse_args()
    run(args.config, args.output_dir)


if __name__ == "__main__":
    main()
