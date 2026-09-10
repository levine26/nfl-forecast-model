from __future__ import annotations

"""Validation and reproducibility helpers for predeclared LevLine experiments."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
from typing import Any, Iterable

import numpy as np
import pandas as pd
import sklearn

REQUIRED_FIELDS = {
    "experiment_id",
    "candidate_version",
    "hypothesis",
    "feature_family",
    "training_seasons",
    "validation_seasons",
    "data_timestamp_policy",
    "allowed_inputs",
    "prohibited_inputs",
    "model_family",
    "hyperparameter_search_policy",
    "primary_metric",
    "secondary_metrics",
    "candidate_created_at",
    "git_sha",
    "status",
    "historical_result",
    "prospective_shadow_status",
}

ALLOWED_STATUSES = {"planned", "running", "historically_qualified", "rejected", "shadowing", "complete"}
TIMESTAMP_CLASSES = {
    "known_before_game",
    "knowable_by_t120",
    "historically_reconstructable",
    "only_available_after_kickoff",
    "unknown_unsafe",
}


def validate_experiment(record: dict[str, Any]) -> None:
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        raise ValueError(f"Experiment missing required fields: {sorted(missing)}")
    if not str(record["experiment_id"]).strip():
        raise ValueError("experiment_id must be non-empty")
    if record["status"] not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid experiment status: {record['status']}")
    training = [int(x) for x in record["training_seasons"]]
    validation = [int(x) for x in record["validation_seasons"]]
    if not training or not validation:
        raise ValueError("training_seasons and validation_seasons must be non-empty")
    if max(training) >= min(validation):
        raise ValueError("training seasons must precede the first validation season")
    if any(season >= 2026 for season in validation):
        raise ValueError("2026 outcomes are prohibited from historical validation/model selection")
    if not isinstance(record["allowed_inputs"], list) or not isinstance(record["prohibited_inputs"], list):
        raise ValueError("allowed_inputs and prohibited_inputs must be lists")
    if not record["prohibited_inputs"]:
        raise ValueError("prohibited_inputs must explicitly enumerate leakage-prone inputs")
    policy = record["data_timestamp_policy"]
    if not isinstance(policy, dict) or not policy:
        raise ValueError("data_timestamp_policy must classify the experiment's data families")
    bad_classes = {str(value) for value in policy.values()} - TIMESTAMP_CLASSES
    if bad_classes:
        raise ValueError(f"Unknown timestamp classifications: {sorted(bad_classes)}")
    sha = str(record["git_sha"])
    if len(sha) < 7:
        raise ValueError("git_sha must identify the source commit")


def load_registry(path: str | Path = "research/experiments.json") -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("experiments"), list):
        raise ValueError("Registry must contain an experiments list")
    experiments = payload["experiments"]
    ids: set[str] = set()
    for record in experiments:
        if not isinstance(record, dict):
            raise ValueError("Every registry experiment must be an object")
        validate_experiment(record)
        experiment_id = str(record["experiment_id"])
        if experiment_id in ids:
            raise ValueError(f"Duplicate experiment_id: {experiment_id}")
        ids.add(experiment_id)
    return experiments


def feature_manifest_hash(features: Iterable[str]) -> str:
    normalized = "\n".join(sorted(str(feature) for feature in features))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def reproducibility_metadata(
    *,
    candidate_version: str,
    features: Iterable[str],
    data_seasons: Iterable[int],
    max_pbp_season: int | None,
    random_seed: int,
    games: int,
    player_observations: int = 0,
    play_observations: int = 0,
    exclusions: dict[str, int] | None = None,
    missing_data_rates: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return the minimum reproducibility envelope required for serious research."""
    return {
        "git_sha": _git_sha(),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_version": candidate_version,
        "data_seasons": sorted(int(x) for x in data_seasons),
        "maximum_pbp_season": int(max_pbp_season) if max_pbp_season is not None else None,
        "feature_set_hash": feature_manifest_hash(features),
        "feature_count": len(set(str(x) for x in features)),
        "random_seed": int(random_seed),
        "games": int(games),
        "player_observations": int(player_observations),
        "play_observations": int(play_observations),
        "exclusions": exclusions or {},
        "missing_data_rates": missing_data_rates or {},
        "package_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
