from __future__ import annotations

"""Portable production implementation of the frozen F-ST nested PURE architecture.

Frozen historical inputs are immutable forensic reconstructions captured from workflow
34538432305. Ordinary production never regenerates them and never forces a CPU-specific
OpenBLAS core type. The recovered artifacts are keyed by game_id and fail closed on any
byte, identity, ordering, target, season, or probability mismatch.
"""

from dataclasses import dataclass
import base64
import gzip
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from .models import _win_models

EPS = 1e-6
BASE_MODEL_NAMES = ("logistic", "extra_trees", "xgboost", "catboost")
BASE_OOF_START = 2018
HISTORICAL_END = 2025
TARGET_SEASONS = (2022, 2023, 2024, 2025)
MIN_META_GAMES = 300

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

# Archival generic v0.8 OOF. This is intentionally NOT authoritative for F-ST-01.
ARCHIVED_GENERIC_BASE_OOF_PATH = ARTIFACT_DIR / "F-ST-01-FROZEN-2026-base-oof.csv"
ARCHIVED_GENERIC_BASE_OOF_SHA256 = "4e5a72f545982465b2401876dfb60c293403ceb89eac1f87778b85d9f5b988e7"

# Authoritative forensic reconstruction from workflow 34538432305, explicit SKYLAKEX job.
RECOVERED_BASE_OOF_PREFIX = "F-ST-01-FROZEN-2026-base-oof-keyed.csv.gz.b64.part"
RECOVERED_BASE_OOF_RAW_SHA256 = "5563b2c9eeb193891ad0ae3809f3fcc9fac04b6451376fc28fa5888c070a78fa"
RECOVERED_BASE_OOF_GZIP_SHA256 = "ca0bcc0844e9e7272d687d8fc5a226c1dbb68e4aaf43b2ce2fab0313c894c713"
RECOVERED_BASE_OOF_SEQUENCE_SHA256 = "5f4eda7d5df86ab13e4d6a6b90653be3160bd857e00eb1d412eae0e78eb2c7b3"
RECOVERED_BASE_OOF_GAME_ID_SEQUENCE_SHA256 = "dff495fa86c9c53b1a76213afcb351c01ed691db9c225bdd911717ccd2ce236c"
FROZEN_BASE_OOF_ROWS = 2127
FROZEN_BASE_OOF_FIRST_SEASON = 2018
FROZEN_BASE_OOF_LAST_SEASON = 2025

RECOVERED_TRAINING_PREFIX = "F-ST-01-FROZEN-2026-training-frame-keyed.csv.gz.b64.part"
RECOVERED_TRAINING_RAW_SHA256 = "174be982d5ac7f3e9f93bda824641eae95c612ec0c1e9546472479a5f6cb55d5"
RECOVERED_TRAINING_GZIP_SHA256 = "28f3c2a0e479e95482e2989f172b143c8eb50ee18b14d15931b6641c9d54d10d"
RECOVERED_TRAINING_SEQUENCE_SHA256 = "0716b93e01eaba82c8b807b26d75a2b35558a4be162461b9d0bfd43d43d0a3ab"
RECOVERED_TRAINING_GAME_ID_SEQUENCE_SHA256 = "d23d72a2c1226a3dd23ffab6dd2c783f96e76f772f73ca649e687a09b248f209"
FROZEN_TRAINING_ROWS = 1615
FROZEN_TRAINING_FIRST_SEASON = 2020
FROZEN_TRAINING_LAST_SEASON = 2025
FROZEN_TRAINING_DIGEST = "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0"

FROZEN_BASE_OOF_COLUMNS = (
    "game_id", "row_position", *BASE_MODEL_NAMES, "home_win", "season"
)
FROZEN_TRAINING_COLUMNS = (
    "game_id", "row_position", "season", "home_win", "market_prob", "pure_prob"
)


@dataclass(frozen=True)
class NestedStackResult:
    base_oof: pd.DataFrame
    target_oof: pd.DataFrame


def _clip(values) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def _logit(values) -> np.ndarray:
    p = _clip(values)
    return np.log(p / (1.0 - p))


def _meta_template(seed: int) -> Pipeline:
    return Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("model", LogisticRegression(C=0.5, max_iter=3000, random_state=seed)),
    ])


def _assert_historical_cutoff(frame: pd.DataFrame, season_col: str = "season") -> None:
    if season_col not in frame.columns:
        raise ValueError(f"F-ST historical frame missing {season_col!r}")
    season = pd.to_numeric(frame[season_col], errors="coerce")
    if season.dropna().gt(HISTORICAL_END).any():
        raise ValueError("F-ST nested PURE fitting may not use outcomes after 2025")


def _read_chunked_artifact(
    prefix: str,
    *,
    expected_gzip_sha256: str,
    expected_raw_sha256: str,
    artifact_dir: str | Path = ARTIFACT_DIR,
) -> bytes:
    root = Path(artifact_dir)
    parts = sorted(root.glob(prefix + "*"))
    if not parts:
        raise RuntimeError(f"Frozen F-ST artifact parts missing for {prefix}")
    encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
    try:
        compressed = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise RuntimeError(f"Frozen F-ST artifact base64 decode failed for {prefix}") from exc
    gzip_sha = hashlib.sha256(compressed).hexdigest()
    if gzip_sha != expected_gzip_sha256:
        raise RuntimeError(
            f"Frozen F-ST compressed artifact hash mismatch: {gzip_sha} != {expected_gzip_sha256}"
        )
    try:
        raw = gzip.decompress(compressed)
    except Exception as exc:
        raise RuntimeError(f"Frozen F-ST artifact gzip decode failed for {prefix}") from exc
    raw_sha = hashlib.sha256(raw).hexdigest()
    if raw_sha != expected_raw_sha256:
        raise RuntimeError(
            f"Frozen F-ST artifact hash mismatch: {raw_sha} != {expected_raw_sha256}"
        )
    return raw


def _validate_game_ids(frame: pd.DataFrame, label: str) -> None:
    game_id = frame["game_id"].astype(str)
    if game_id.isna().any() or game_id.str.strip().eq("").any() or game_id.duplicated().any():
        raise RuntimeError(f"Frozen F-ST {label} game_id identity invalid")


def _validate_row_position(frame: pd.DataFrame, label: str) -> None:
    pos = pd.to_numeric(frame["row_position"], errors="coerce")
    expected = np.arange(len(frame), dtype=int)
    if pos.isna().any() or not np.array_equal(pos.astype(int).to_numpy(), expected):
        raise RuntimeError(f"Frozen F-ST {label} row-position mismatch")


def _validate_probability_columns(frame: pd.DataFrame, columns: list[str], label: str) -> None:
    probs = frame[columns].apply(pd.to_numeric, errors="coerce")
    values = probs.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise RuntimeError(f"Frozen F-ST {label} contains non-finite probabilities")
    if ((probs <= 0.0) | (probs >= 1.0)).any().any():
        raise RuntimeError(f"Frozen F-ST {label} probability outside (0, 1)")


def _sequence_hash(frame: pd.DataFrame) -> str:
    text = frame.to_csv(index=False, float_format="%.17g", lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _game_id_sequence_hash(frame: pd.DataFrame) -> str:
    text = "\n".join(frame["game_id"].astype(str).tolist()) + "\n"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _align_base_oof_to_historical(frame: pd.DataFrame, historical: pd.DataFrame) -> pd.DataFrame:
    _assert_historical_cutoff(historical)
    required = {"game_id", "season", "home_win"}
    missing = required - set(historical.columns)
    if missing:
        raise ValueError(f"F-ST historical alignment missing fields: {sorted(missing)}")
    if not historical.index.is_unique:
        raise RuntimeError("F-ST historical alignment index is not unique")

    hist = historical.loc[
        pd.to_numeric(historical["season"], errors="coerce").between(
            FROZEN_BASE_OOF_FIRST_SEASON, FROZEN_BASE_OOF_LAST_SEASON
        )
        & historical["home_win"].notna(),
        ["game_id", "season", "home_win"],
    ].copy()
    hist["_historical_index"] = hist.index
    if hist["game_id"].astype(str).duplicated().any():
        raise RuntimeError("F-ST historical game_id is not unique")
    hist["game_id"] = hist["game_id"].astype(str)

    expected_ids = set(frame["game_id"].astype(str))
    actual_ids = set(hist["game_id"])
    missing_games = expected_ids - actual_ids
    unexpected_games = actual_ids - expected_ids
    if missing_games:
        raise RuntimeError(f"F-ST historical alignment missing expected games: {len(missing_games)}")
    if unexpected_games:
        raise RuntimeError(f"F-ST historical alignment has unexpected games: {len(unexpected_games)}")

    keyed = frame.merge(hist, on="game_id", how="left", suffixes=("", "_historical"), validate="one_to_one")
    artifact_season = pd.to_numeric(keyed["season"], errors="raise").astype(int)
    historical_season = pd.to_numeric(keyed["season_historical"], errors="raise").astype(int)
    if not np.array_equal(artifact_season.to_numpy(), historical_season.to_numpy()):
        raise RuntimeError("F-ST historical season mismatch")
    artifact_target = pd.to_numeric(keyed["home_win"], errors="raise").astype(int)
    historical_target = pd.to_numeric(keyed["home_win_historical"], errors="raise").astype(int)
    if not np.array_equal(artifact_target.to_numpy(), historical_target.to_numpy()):
        raise RuntimeError("F-ST historical target mismatch")

    out = frame.copy()
    out.index = pd.Index(keyed["_historical_index"].tolist())
    return out


def load_frozen_base_oof(
    *,
    historical: pd.DataFrame | None = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
) -> pd.DataFrame:
    raw = _read_chunked_artifact(
        RECOVERED_BASE_OOF_PREFIX,
        expected_gzip_sha256=RECOVERED_BASE_OOF_GZIP_SHA256,
        expected_raw_sha256=RECOVERED_BASE_OOF_RAW_SHA256,
        artifact_dir=artifact_dir,
    )
    frame = pd.read_csv(io.BytesIO(raw))
    if tuple(frame.columns) != FROZEN_BASE_OOF_COLUMNS:
        raise RuntimeError(f"Frozen F-ST base OOF columns changed: {tuple(frame.columns)!r}")
    if len(frame) != FROZEN_BASE_OOF_ROWS:
        raise RuntimeError(f"Frozen F-ST base OOF row count mismatch: {len(frame)}")
    _validate_game_ids(frame, "base OOF")
    _validate_row_position(frame, "base OOF")
    season = pd.to_numeric(frame["season"], errors="coerce")
    if season.isna().any() or int(season.min()) != 2018 or int(season.max()) != 2025:
        raise RuntimeError("Frozen F-ST base OOF season mismatch")
    if season.gt(2025).any():
        raise RuntimeError("Frozen F-ST base OOF contains post-2025 outcomes")
    target = pd.to_numeric(frame["home_win"], errors="coerce")
    if not target.isin([0, 1]).all():
        raise RuntimeError("Frozen F-ST base OOF target mismatch")
    _validate_probability_columns(frame, list(BASE_MODEL_NAMES), "base OOF")
    if _sequence_hash(frame) != RECOVERED_BASE_OOF_SEQUENCE_SHA256:
        raise RuntimeError("Frozen F-ST base OOF serialized sequence mismatch")
    if _game_id_sequence_hash(frame) != RECOVERED_BASE_OOF_GAME_ID_SEQUENCE_SHA256:
        raise RuntimeError("Frozen F-ST base OOF game sequence mismatch")
    if historical is not None:
        frame = _align_base_oof_to_historical(frame, historical)
    return frame.copy()


def canonical_training_hash(frame: pd.DataFrame) -> str:
    required = {"season", "home_win", "market_prob", "pure_prob"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"F-ST training digest frame missing fields: {sorted(missing)}")
    work = frame.copy()
    work["season_num"] = pd.to_numeric(work["season"], errors="coerce")
    if work["season_num"].dropna().ge(2026).any():
        raise RuntimeError("F-ST digest validation refuses 2026-or-later outcomes")
    work["home_win_num"] = pd.to_numeric(work["home_win"], errors="coerce")
    work["market_prob_num"] = pd.to_numeric(work["market_prob"], errors="coerce")
    work["pure_prob_num"] = pd.to_numeric(work["pure_prob"], errors="coerce")
    work = work[
        work["season_num"].notna()
        & work["home_win_num"].notna()
        & work["market_prob_num"].notna()
        & work["pure_prob_num"].notna()
        & work["season_num"].le(2025)
    ].copy()
    canonical = work[["season_num", "home_win_num", "market_prob_num", "pure_prob_num"]].copy()
    canonical = canonical.sort_values(
        ["season_num", "market_prob_num", "pure_prob_num", "home_win_num"],
        kind="mergesort",
    )
    text = canonical.to_csv(index=False, float_format="%.12g", lineterminator="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_frozen_training_frame(
    *,
    historical: pd.DataFrame | None = None,
    artifact_dir: str | Path = ARTIFACT_DIR,
) -> pd.DataFrame:
    raw = _read_chunked_artifact(
        RECOVERED_TRAINING_PREFIX,
        expected_gzip_sha256=RECOVERED_TRAINING_GZIP_SHA256,
        expected_raw_sha256=RECOVERED_TRAINING_RAW_SHA256,
        artifact_dir=artifact_dir,
    )
    frame = pd.read_csv(io.BytesIO(raw))
    if tuple(frame.columns) != FROZEN_TRAINING_COLUMNS:
        raise RuntimeError(f"Frozen F-ST training-frame columns changed: {tuple(frame.columns)!r}")
    if len(frame) != FROZEN_TRAINING_ROWS:
        raise RuntimeError(f"Frozen F-ST training row count mismatch: {len(frame)}")
    _validate_game_ids(frame, "training frame")
    _validate_row_position(frame, "training frame")
    season = pd.to_numeric(frame["season"], errors="coerce")
    if (
        season.isna().any()
        or int(season.min()) != FROZEN_TRAINING_FIRST_SEASON
        or int(season.max()) != FROZEN_TRAINING_LAST_SEASON
    ):
        raise RuntimeError("Frozen F-ST training season mismatch")
    if season.ge(2026).any():
        raise RuntimeError("Frozen F-ST training frame contains post-2025 outcomes")
    target = pd.to_numeric(frame["home_win"], errors="coerce")
    if not target.isin([0, 1]).all():
        raise RuntimeError("Frozen F-ST training target mismatch")
    _validate_probability_columns(frame, ["market_prob", "pure_prob"], "training frame")
    if _sequence_hash(frame) != RECOVERED_TRAINING_SEQUENCE_SHA256:
        raise RuntimeError("Frozen F-ST training serialized sequence mismatch")
    if _game_id_sequence_hash(frame) != RECOVERED_TRAINING_GAME_ID_SEQUENCE_SHA256:
        raise RuntimeError("Frozen F-ST training game sequence mismatch")
    digest = canonical_training_hash(frame)
    if digest != FROZEN_TRAINING_DIGEST:
        raise RuntimeError(f"Frozen F-ST training digest mismatch: {digest} != {FROZEN_TRAINING_DIGEST}")

    if historical is not None:
        _assert_historical_cutoff(historical)
        required = {"game_id", "season", "home_win"}
        missing = required - set(historical.columns)
        if missing:
            raise ValueError(f"F-ST historical training check missing fields: {sorted(missing)}")
        hist = historical[["game_id", "season", "home_win"]].copy()
        hist["game_id"] = hist["game_id"].astype(str)
        if hist["game_id"].duplicated().any():
            raise RuntimeError("F-ST historical training check has duplicate game IDs")
        lookup = hist.set_index("game_id")
        missing_games = set(frame["game_id"].astype(str)) - set(lookup.index)
        if missing_games:
            raise RuntimeError(
                f"F-ST training frame missing expected historical games: {len(missing_games)}"
            )
        rows = lookup.loc[frame["game_id"].astype(str)]
        if not np.array_equal(
            pd.to_numeric(frame["season"]).astype(int).to_numpy(),
            pd.to_numeric(rows["season"]).astype(int).to_numpy(),
        ):
            raise RuntimeError("F-ST training historical season mismatch")
        if not np.array_equal(
            pd.to_numeric(frame["home_win"]).astype(int).to_numpy(),
            pd.to_numeric(rows["home_win"]).astype(int).to_numpy(),
        ):
            raise RuntimeError("F-ST training historical target mismatch")
    return frame.copy()


def reconstruct_frozen_coefficients(training: pd.DataFrame) -> dict[str, float]:
    """Re-fit only for validation; registered literals remain authoritative for scoring."""
    digest = canonical_training_hash(training)
    if digest != FROZEN_TRAINING_DIGEST:
        raise RuntimeError("Refusing F-ST reconstruction from non-frozen training inputs")
    x = np.column_stack([
        _logit(pd.to_numeric(training["market_prob"], errors="raise")),
        _logit(pd.to_numeric(training["pure_prob"], errors="raise")),
    ])
    y = pd.to_numeric(training["home_win"], errors="raise").astype(int).to_numpy()
    model = LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=3000)
    model.fit(x, y)
    return {
        "intercept": float(model.intercept_[0]),
        "market_logit_coefficient": float(model.coef_[0, 0]),
        "pure_logit_coefficient": float(model.coef_[0, 1]),
    }


def build_nested_stack_oof(
    base_oof: pd.DataFrame,
    *,
    target_seasons: tuple[int, ...] = TARGET_SEASONS,
    target: str = "home_win",
    season_col: str = "season",
    seed: int = 26,
    min_meta_games: int = MIN_META_GAMES,
) -> NestedStackResult:
    season = pd.to_numeric(base_oof[season_col], errors="coerce")
    if season.dropna().gt(HISTORICAL_END).any():
        raise ValueError("F-ST nested meta-model may not load post-2025 OOF rows")
    parts: list[pd.DataFrame] = []
    for test_season in [int(x) for x in target_seasons]:
        meta_train = base_oof[base_oof[season_col] < test_season]
        test = base_oof[base_oof[season_col] == test_season]
        if test.empty:
            continue
        if len(meta_train) < min_meta_games or meta_train[target].nunique() < 2:
            raise ValueError(
                f"Insufficient pre-{test_season} F-ST meta training sample: {len(meta_train)}"
            )
        meta = _meta_template(seed)
        meta.fit(meta_train[list(BASE_MODEL_NAMES)], meta_train[target].astype(int))
        part = test[[target, season_col]].copy()
        part["pure_prob"] = meta.predict_proba(test[list(BASE_MODEL_NAMES)])[:, 1]
        parts.append(part)
    if not parts:
        raise ValueError("No nested F-ST target seasons were generated")
    target_oof = pd.concat(parts).sort_index()
    missing = set(target_seasons) - set(target_oof[season_col].astype(int).unique())
    if missing:
        raise RuntimeError(f"F-ST nested PURE missing target seasons: {sorted(missing)}")
    return NestedStackResult(base_oof=base_oof, target_oof=target_oof)


def fit_future_nested_stack(
    historical: pd.DataFrame,
    base_oof: pd.DataFrame,
    current: pd.DataFrame,
    feature_cols: list[str],
    *,
    target: str = "home_win",
    seed: int = 26,
) -> np.ndarray:
    """Score live nested PURE from frozen OOF meta-inputs and through-2025 base fits."""
    _assert_historical_cutoff(historical)
    if base_oof[target].nunique() < 2:
        raise ValueError("F-ST meta training target has fewer than two classes")
    meta = _meta_template(seed)
    meta.fit(base_oof[list(BASE_MODEL_NAMES)], base_oof[target].astype(int))

    base_current = pd.DataFrame(index=current.index)
    templates = _win_models(seed)
    if tuple(templates) != BASE_MODEL_NAMES:
        raise RuntimeError(f"F-ST base-model template identity changed: {tuple(templates)!r}")
    for name, template in templates.items():
        model = clone(template)
        model.fit(historical[feature_cols], historical[target].astype(int))
        base_current[name] = model.predict_proba(current[feature_cols])[:, 1]
    probability = _clip(meta.predict_proba(base_current[list(BASE_MODEL_NAMES)])[:, 1])
    if not np.isfinite(probability).all() or ((probability <= 0.0) | (probability >= 1.0)).any():
        raise RuntimeError("F-ST live nested PURE produced invalid probabilities")
    return probability
