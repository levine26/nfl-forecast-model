from __future__ import annotations

"""Prospective component-resolved capture for LevLine 4 Boundary Gate research.

This module is research-only. It refits the already-defined base model families on
completed pre-2026 seasons and records their probabilities for the unresolved 2026
slate. It does not alter F-ST, production forecasts, Sunday Signal, or any production
workflow. Captures are descriptive evidence; no winner-switch threshold is defined.
"""

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd
from sklearn.base import clone

from nfl_forecast.models import _win_models
from scripts.run_challenger_v08 import LIVE_SEASON, SHADOW_BASE_COLUMNS, build_research_frame

COMPONENTS = ("logistic", "extra_trees", "xgboost", "catboost")
MAX_TRAINING_SEASON = 2025
SCHEMA_VERSION = "levline4-component-snapshot-v1"


def _utc(value: datetime | None = None) -> datetime:
    out = value or datetime.now(timezone.utc)
    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)


def _validate_inputs(historical: pd.DataFrame, current: pd.DataFrame, feature_cols: list[str]) -> None:
    required_history = {"season", "home_win", "game_id", *feature_cols}
    required_current = {"season", "home_win", "game_id", *feature_cols}
    missing_history = required_history - set(historical.columns)
    missing_current = required_current - set(current.columns)
    if missing_history:
        raise ValueError(f"historical frame missing fields: {sorted(missing_history)}")
    if missing_current:
        raise ValueError(f"current frame missing fields: {sorted(missing_current)}")
    if not feature_cols:
        raise ValueError("component snapshot requires a non-empty feature set")
    if historical.empty or current.empty:
        raise ValueError("component snapshot requires historical and current rows")
    seasons = pd.to_numeric(historical["season"], errors="coerce")
    if seasons.isna().any() or int(seasons.max()) > MAX_TRAINING_SEASON:
        raise ValueError("component snapshot model fitting is restricted to seasons <= 2025")
    if historical["home_win"].isna().any():
        raise ValueError("historical fitting rows must have outcomes")
    current_season = pd.to_numeric(current["season"], errors="coerce")
    if current_season.isna().any() or not current_season.eq(LIVE_SEASON).all():
        raise ValueError("component snapshot current rows must belong to the 2026 live season")
    if current["home_win"].notna().any():
        raise ValueError("component snapshot refuses already-graded current games")
    if historical["game_id"].astype(str).duplicated().any():
        raise ValueError("historical frame contains duplicate game IDs")
    if current["game_id"].astype(str).duplicated().any():
        raise ValueError("current frame contains duplicate game IDs")


def build_component_snapshot(
    historical: pd.DataFrame,
    current: pd.DataFrame,
    feature_cols: list[str],
    *,
    seed: int,
    generated_utc: datetime | None = None,
    source_sha: str = "unknown",
    model_templates: Mapping[str, object] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Fit frozen-family components on pre-2026 outcomes and score unresolved games."""

    _validate_inputs(historical, current, feature_cols)
    templates = dict(model_templates or _win_models(seed))
    if tuple(templates.keys()) != COMPONENTS:
        raise ValueError(
            f"component model identity mismatch: expected {COMPONENTS}, got {tuple(templates.keys())}"
        )

    generated = _utc(generated_utc)
    probabilities: dict[str, np.ndarray] = {}
    target = pd.to_numeric(historical["home_win"], errors="raise").astype(int)
    for name in COMPONENTS:
        model = clone(templates[name])
        model.fit(historical[feature_cols], target)
        values = np.asarray(model.predict_proba(current[feature_cols])[:, 1], dtype=float)
        if len(values) != len(current) or not np.isfinite(values).all():
            raise RuntimeError(f"{name} returned invalid current probabilities")
        if ((values <= 0.0) | (values >= 1.0)).any():
            raise RuntimeError(f"{name} returned probabilities outside the open interval (0,1)")
        probabilities[name] = values

    base_columns = [column for column in SHADOW_BASE_COLUMNS if column in current.columns]
    snapshot = current[base_columns].copy().reset_index(drop=True)
    matrix = np.column_stack([probabilities[name] for name in COMPONENTS])
    for idx, name in enumerate(COMPONENTS):
        snapshot[f"{name}_home_prob"] = matrix[:, idx]
    snapshot["component_home_votes"] = (matrix >= 0.5).sum(axis=1).astype(int)
    snapshot["component_mean_home_prob"] = matrix.mean(axis=1)
    snapshot["component_std_home_prob"] = matrix.std(axis=1, ddof=0)
    snapshot["component_min_home_prob"] = matrix.min(axis=1)
    snapshot["component_max_home_prob"] = matrix.max(axis=1)
    snapshot["component_range_home_prob"] = (
        snapshot["component_max_home_prob"] - snapshot["component_min_home_prob"]
    )
    snapshot["generated_utc"] = generated.isoformat()
    snapshot["source_sha"] = str(source_sha)
    snapshot["feature_set"] = "production_compatible"
    snapshot["feature_count"] = int(len(feature_cols))
    snapshot["training_first_season"] = int(pd.to_numeric(historical.season).min())
    snapshot["training_last_season"] = int(pd.to_numeric(historical.season).max())
    snapshot["training_games"] = int(len(historical))
    snapshot["completed_2026_outcomes_used_in_model_fitting"] = 0
    snapshot["research_only"] = True
    snapshot["production_authorized"] = False

    status = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated.isoformat(),
        "source_sha": str(source_sha),
        "games": int(len(snapshot)),
        "components": list(COMPONENTS),
        "feature_set": "production_compatible",
        "feature_count": int(len(feature_cols)),
        "training_first_season": int(pd.to_numeric(historical.season).min()),
        "training_last_season": int(pd.to_numeric(historical.season).max()),
        "training_games": int(len(historical)),
        "completed_2026_outcomes_used_in_model_fitting": 0,
        "winner_switch_rule_defined": False,
        "threshold_defined": False,
        "research_only": True,
        "production_authorized": False,
    }
    return snapshot, status


def _append_manifest(path: Path, record: dict) -> None:
    prior: list[dict] = []
    if path.exists() and path.stat().st_size:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                prior.append(json.loads(line))
    capture_id = record["capture_id"]
    if any(item.get("capture_id") == capture_id for item in prior):
        return
    prior.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in prior), encoding="utf-8")


def write_capture(output_dir: Path, snapshot: pd.DataFrame, status: dict) -> dict:
    generated = _utc(datetime.fromisoformat(status["generated_utc"]))
    stamp = generated.strftime("%Y%m%dT%H%M%SZ")
    capture_id = f"components-{stamp}-{status['source_sha'][:12]}"
    capture_dir = output_dir / "captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    csv_path = capture_dir / f"{capture_id}.csv"
    if csv_path.exists():
        raise RuntimeError(f"append-only capture already exists: {csv_path}")
    snapshot.to_csv(csv_path, index=False, quoting=csv.QUOTE_MINIMAL)
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()

    manifest_record = {
        "capture_id": capture_id,
        "generated_utc": status["generated_utc"],
        "source_sha": status["source_sha"],
        "games": status["games"],
        "sha256": digest,
        "path": str(csv_path),
        "completed_2026_outcomes_used_in_model_fitting": 0,
        "research_only": True,
        "production_authorized": False,
    }
    _append_manifest(output_dir / "manifest.jsonl", manifest_record)
    latest = {**status, **manifest_record}
    (output_dir / "status.json").write_text(json.dumps(latest, indent=2, sort_keys=True), encoding="utf-8")
    return latest


def run(config_path: str, output_dir: Path, *, source_sha: str | None = None) -> dict:
    cfg, historical, current, feature_sets, _, _ = build_research_frame(config_path)
    seed = int(cfg["model"]["random_state"])
    features = feature_sets["production_compatible"]
    snapshot, status = build_component_snapshot(
        historical,
        current,
        features,
        seed=seed,
        source_sha=source_sha or os.environ.get("GITHUB_SHA", "unknown"),
    )
    latest = write_capture(output_dir, snapshot, status)
    print(json.dumps(latest, indent=2, sort_keys=True))
    return latest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/levline4_component_snapshot_v1"),
    )
    parser.add_argument("--source-sha", default=None)
    args = parser.parse_args()
    run(args.config, args.output_dir, source_sha=args.source_sha)


if __name__ == "__main__":
    main()
