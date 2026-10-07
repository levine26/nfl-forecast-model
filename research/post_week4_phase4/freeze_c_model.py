"""One-time, research-only freeze of preregistered prospective Candidate C coefficients.

NO 2026 data or outcomes are loaded for fitting. No model selection or tuning.
"""
from __future__ import annotations

import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from research.post_week4_phase3.run_candidates import (
    frozen_panel, historical_features, audit_historical_identity,
    early_state_features, fit_offset,
)
from research.post_week4_phase4.c_shadow import (
    CANDIDATE_ID, FEATURES, TRAINING_DIGEST, validate_model, write_once,
)


def freeze(output: Path) -> dict:
    panel=frozen_panel()
    if panel.season.gt(2025).any():
        raise RuntimeError("No future seasons in frozen candidate historical panel")
    games,tg,schedules,_ = historical_features()
    if games.season.gt(2025).any() or schedules.season.gt(2025).any():
        raise RuntimeError("No post-2025 games eligible in candidate training builder")
    aligned=audit_historical_identity(panel,games)
    if aligned != 1615:
        raise RuntimeError("Historical feature-source identity changed")
    built=early_state_features(tg,schedules)
    cols=list(FEATURES)
    train=panel.loc[panel.season.between(2020,2025),
                    ["game_id","season","home_win","market_prob"]].merge(
        built[["game_id",*cols]],on="game_id",how="left",validate="one_to_one")
    if len(train)!=1615 or train[["market_prob","home_win",*cols]].isna().any().any():
        raise RuntimeError("C historical training population incomplete")
    if train.game_id.duplicated().any() or train.season.max()!=2025:
        raise RuntimeError("Invalid frozen training identity")
    fitted=fit_offset(train.home_win.to_numpy(int),train.market_prob.to_numpy(float),
                      train[cols].to_numpy(float))
    theta,means,stds=fitted
    source_hash=hashlib.sha256(
        train[["game_id","season","home_win","market_prob",*cols]]
        .to_csv(index=False,float_format="%.17g",lineterminator="\n").encode()
    ).hexdigest()
    builder_hash=hashlib.sha256(
        Path("research/post_week4_phase3/run_candidates.py").read_bytes()
    ).hexdigest()
    artifact={
        "candidate_id":CANDIDATE_ID,
        "training_cutoff":2025,"training_first_season":2020,"training_last_season":2025,
        "training_games":len(train),"training_data_sha256":TRAINING_DIGEST,
        "historical_state_source_sha256":source_hash,
        "builder_source_sha256":builder_hash,
        "frozen_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "feature_names":cols,"penalty":0.02,
        "theta":[float(v) for v in theta],
        "means":[float(v) for v in means],
        "stds":[float(v) for v in stds],
        "optimizer":"L-BFGS-B","optimizer_maxiter":1000,"optimizer_ftol":1e-12,
        "market_logit_offset_coefficient":1,
        "pretarget_only":True,
        "prior_games_last_season":8,
        "previous_season_team_share":0.6,"previous_season_league_share":0.4,
        "current_season_effective_prior_games":6,
        "includes_next_starter_information":False,
        "legacy_tie_label_caveat":True,
        "outcomes_2026_used":0,
        "production_promotion_authorized":False,
    }
    validate_model(artifact)
    write_once(output,artifact)
    return artifact


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    args=p.parse_args()
    a=freeze(Path(args.output))
    print(json.dumps({k:a[k] for k in
        ("candidate_id","training_games","training_cutoff","historical_state_source_sha256",
         "builder_source_sha256","frozen_at_utc","outcomes_2026_used")},indent=2))


if __name__=="__main__":
    main()
