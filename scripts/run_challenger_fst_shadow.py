from __future__ import annotations

"""Materialize the frozen F-ST-01 candidate into the research-only live shadow slate."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger import fit_future_nested_stack
from nfl_forecast.challenger_fst import (
    FROZEN_CANDIDATE_ID,
    FROZEN_FEATURE_SET,
    FROZEN_METHOD,
    fit_frozen_2026_stack,
    frozen_stack_probability,
    prepare_frozen_training_frame,
)
from nfl_forecast.fst_provenance import (
    TRAINING_COLUMNS,
    capture_fst_pre_fit_provenance,
    verify_fst_frozen_identity,
    write_fst_fit_provenance,
)
from scripts.run_challenger_v08 import SHADOW_BASE_COLUMNS, build_nested_research, build_research_frame

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


def run(config_path: str = "config/model.yaml", output_dir: str = "challenger_outputs") -> dict:
    out = Path(output_dir)
    slate_path = out / "candidate_shadow_slate.csv"
    if not slate_path.exists():
        raise RuntimeError("v0.8 candidate shadow slate must exist before F-ST materialization")

    spec = _load_spec()
    cfg, historical, current, feature_sets, _, _ = build_research_frame(config_path)
    seed = int(cfg["model"]["random_state"])
    base_features = feature_sets["production_compatible"]
    base_oof, research = build_nested_research(historical, base_features, seed)

    # Persist the exact model inputs before fitting. This is a current prospective
    # reconstruction of F-ST-01, not the missing original candidate-freeze capture.
    prepared = prepare_frozen_training_frame(research)
    training_for_fit = research.loc[prepared.index, list(TRAINING_COLUMNS)].copy()
    provenance_dir = out / "fst" / "provenance"
    input_provenance = capture_fst_pre_fit_provenance(
        historical,
        base_oof,
        training_for_fit,
        provenance_dir,
        candidate_id=FROZEN_CANDIDATE_ID,
        capture_context="prospective_shadow_reconstruction",
    )

    # Target season 2026 may only train on earlier-season OOF rows. Persist the
    # completed fit, then require exact agreement with the registered frozen
    # identity before generating any current-game PURE probabilities or scoring.
    fit = fit_frozen_2026_stack(training_for_fit)
    fit_provenance = write_fst_fit_provenance(provenance_dir, input_provenance, fit)
    identity_check = verify_fst_frozen_identity(
        provenance_dir,
        input_provenance,
        fit,
        spec["frozen_identity"],
    )

    current_pure = fit_future_nested_stack(
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
        intercept=fit.intercept,
        market_logit_coefficient=fit.market_logit_coefficient,
        pure_logit_coefficient=fit.pure_logit_coefficient,
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
    fst["training_games"] = fit.training_games
    fst["training_first_season"] = fit.training_first_season
    fst["training_last_season"] = fit.training_last_season
    fst["training_data_sha256"] = fit.training_data_sha256
    fst["stack_intercept"] = fit.intercept
    fst["stack_market_logit_coefficient"] = fit.market_logit_coefficient
    fst["stack_pure_logit_coefficient"] = fit.pure_logit_coefficient
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

    runtime = {
        "candidate_id": FROZEN_CANDIDATE_ID,
        "mode": "research_only_frozen_shadow",
        "target_season": 2026,
        "training_cutoff": 2025,
        "2026_outcomes_used_in_fitting": 0,
        "production_promotion_authorized": False,
        **fit.as_dict(),
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
