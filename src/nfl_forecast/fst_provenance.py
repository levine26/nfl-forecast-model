from __future__ import annotations

"""Durable, game-keyed provenance capture for F-ST research inputs.

The capture happens before the frozen stack is fit. Raw artifact hashes preserve
exact serialization and row order; canonical keyed hashes separately identify
the semantic game-keyed content independent of row order.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .challenger_fst import FrozenStackFit
from .challenger_stacking import HISTORICAL_END

SERIALIZATION_VERSION = 1
FLOAT_FORMAT = "%.17g"
LINE_TERMINATOR = "\n"
BASE_OOF_COLUMNS = (
    "logistic",
    "extra_trees",
    "xgboost",
    "catboost",
    "home_win",
    "season",
)
TRAINING_COLUMNS = ("season", "home_win", "market_prob", "pure_prob")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_exact_fit_frame(frame: pd.DataFrame) -> None:
    required = set(TRAINING_COLUMNS)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"F-ST provenance training frame missing fields: {sorted(missing)}")
    numeric = frame[list(TRAINING_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("F-ST provenance training frame contains non-finite values")
    if not numeric["home_win"].isin([0, 1]).all():
        raise ValueError("F-ST provenance training target is not binary")
    if numeric["season"].ge(HISTORICAL_END + 1).any():
        raise ValueError("F-ST provenance training frame may not contain post-2025 rows")
    for col in ("market_prob", "pure_prob"):
        if ((numeric[col] <= 0.0) | (numeric[col] >= 1.0)).any():
            raise ValueError(f"F-ST provenance {col} must be strictly between 0 and 1")


def _require_base_oof(frame: pd.DataFrame) -> None:
    missing = set(BASE_OOF_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"F-ST provenance base OOF missing fields: {sorted(missing)}")
    numeric = frame[list(BASE_OOF_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("F-ST provenance base OOF contains non-finite values")
    if not numeric["home_win"].isin([0, 1]).all():
        raise ValueError("F-ST provenance base OOF target is not binary")
    if numeric["season"].ge(HISTORICAL_END + 1).any():
        raise ValueError("F-ST provenance base OOF may not contain post-2025 rows")
    for col in ("logistic", "extra_trees", "xgboost", "catboost"):
        if ((numeric[col] <= 0.0) | (numeric[col] >= 1.0)).any():
            raise ValueError(f"F-ST provenance base OOF {col} must be strictly between 0 and 1")


def _keyed(
    historical: pd.DataFrame,
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    *,
    label: str,
) -> pd.DataFrame:
    if "game_id" not in historical.columns:
        raise ValueError("F-ST provenance historical frame missing 'game_id'")
    if not historical.index.is_unique:
        raise ValueError("F-ST provenance historical index is not unique")
    if not frame.index.is_unique:
        raise ValueError(f"F-ST provenance {label} index is not unique")

    missing_index = frame.index.difference(historical.index)
    if len(missing_index):
        raise ValueError(
            f"F-ST provenance {label} contains {len(missing_index)} rows absent from historical frame"
        )

    game_id = historical.loc[frame.index, "game_id"]
    if game_id.isna().any() or game_id.astype(str).str.strip().eq("").any():
        raise ValueError(f"F-ST provenance {label} contains missing game_id")
    game_id = game_id.astype(str)
    if game_id.duplicated().any():
        duplicates = sorted(game_id[game_id.duplicated(keep=False)].unique().tolist())
        raise ValueError(f"F-ST provenance {label} contains duplicate game_id: {duplicates[:5]}")

    keyed = frame.loc[:, list(columns)].copy()
    keyed.insert(0, "row_position", np.arange(len(keyed), dtype=int))
    keyed.insert(0, "game_id", game_id.to_numpy())
    return keyed


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    text = frame.to_csv(
        index=False,
        float_format=FLOAT_FORMAT,
        lineterminator=LINE_TERMINATOR,
    )
    return text.encode("utf-8")


def _canonical_keyed_sha(frame: pd.DataFrame) -> str:
    canonical = frame.drop(columns=["row_position"]).sort_values(
        "game_id", kind="mergesort"
    )
    return _sha256(_csv_bytes(canonical))


def _sequence_sha(frame: pd.DataFrame) -> str:
    text = LINE_TERMINATOR.join(frame["game_id"].astype(str).tolist()) + LINE_TERMINATOR
    return _sha256(text.encode("utf-8"))


def _artifact_summary(path: Path, frame: pd.DataFrame, raw: bytes) -> dict[str, Any]:
    season = pd.to_numeric(frame["season"], errors="raise")
    return {
        "path": path.name,
        "rows": int(len(frame)),
        "first_season": int(season.min()),
        "last_season": int(season.max()),
        "columns": list(frame.columns),
        "raw_sha256": _sha256(raw),
        "canonical_game_keyed_sha256": _canonical_keyed_sha(frame),
        "game_id_sequence_sha256": _sequence_sha(frame),
    }


def capture_fst_pre_fit_provenance(
    historical: pd.DataFrame,
    base_oof: pd.DataFrame,
    training_frame: pd.DataFrame,
    output_dir: str | Path,
    *,
    candidate_id: str,
) -> dict[str, Any]:
    """Persist exact F-ST model inputs before fitting and return their manifest."""

    _require_base_oof(base_oof)
    _require_exact_fit_frame(training_frame)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    keyed_oof = _keyed(historical, base_oof, BASE_OOF_COLUMNS, label="base OOF")
    keyed_training = _keyed(
        historical, training_frame, TRAINING_COLUMNS, label="training frame"
    )

    oof_path = out / "base_oof_keyed.csv"
    training_path = out / "training_frame_keyed.csv"
    oof_raw = _csv_bytes(keyed_oof)
    training_raw = _csv_bytes(keyed_training)
    oof_path.write_bytes(oof_raw)
    training_path.write_bytes(training_raw)

    manifest = {
        "schema_version": SERIALIZATION_VERSION,
        "capture_stage": "pre_fit",
        "candidate_id": str(candidate_id),
        "historical_outcome_cutoff_season": HISTORICAL_END,
        "serialization": {
            "format": "csv",
            "encoding": "utf-8",
            "float_format": FLOAT_FORMAT,
            "line_terminator": "LF",
            "row_order_preserved": True,
            "row_position_explicit": True,
        },
        "base_oof": _artifact_summary(oof_path, keyed_oof, oof_raw),
        "training_frame": _artifact_summary(training_path, keyed_training, training_raw),
    }
    manifest_path = out / "inputs_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def write_fst_fit_provenance(
    output_dir: str | Path,
    input_manifest: dict[str, Any],
    fit: FrozenStackFit,
) -> dict[str, Any]:
    """Bind a completed fit to the already-persisted pre-fit input artifacts."""

    out = Path(output_dir)
    input_manifest_path = out / "inputs_manifest.json"
    if not input_manifest_path.exists():
        raise RuntimeError("F-ST fit provenance requires persisted pre-fit inputs")
    persisted = json.loads(input_manifest_path.read_text(encoding="utf-8"))
    if persisted != input_manifest:
        raise RuntimeError("F-ST pre-fit manifest changed before fit provenance was recorded")

    manifest = {
        "schema_version": SERIALIZATION_VERSION,
        "candidate_id": input_manifest["candidate_id"],
        "inputs_manifest_sha256": _sha256(input_manifest_path.read_bytes()),
        "base_oof_raw_sha256": input_manifest["base_oof"]["raw_sha256"],
        "training_frame_raw_sha256": input_manifest["training_frame"]["raw_sha256"],
        "training_frame_canonical_game_keyed_sha256": input_manifest["training_frame"][
            "canonical_game_keyed_sha256"
        ],
        "model_training_data_sha256": fit.training_data_sha256,
        "fit": fit.as_dict(),
    }
    (out / "fit_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
