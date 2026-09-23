from __future__ import annotations

"""Research-only Phase-2 data, chronology, grading, and provenance gate.

This module implements the pre-result gates frozen by ``research/ats-nextgen``.
It does not fit Q1/Q2/Q3, score candidate performance, or feed production
forecasts. Historical schedule market fields retain their preregistered
``historical_closing_late_benchmark_exact_horizon_opaque`` evidence label;
only timestamped run-history rows selected by :mod:`nfl_forecast.market_t120`
may be described as T-120 evidence.

Important source-sign boundary: nflverse ``spread_line`` is the home-margin
market center (positive when the home team is favored). The ATS preregistration
uses sportsbook home-spread notation ``L`` (negative when the home team is
favored), so ``L = -spread_line`` and ``C = spread_line``.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROGRAM_ID = "LEVLINE_ATS_NEXTGEN"
PHASE = 2
TRAINING_FLOOR = 2015
HISTORICAL_END = 2025
OUTER_TARGET_SEASONS = (2022, 2023, 2024, 2025)
INNER_TARGET_FLOOR = 2019
HISTORICAL_MARKET_EVIDENCE_CLASS = (
    "historical_closing_late_benchmark_exact_horizon_opaque"
)
NFLVERSE_SPREAD_SOURCE_CONVENTION = (
    "spread_line is positive when home is favored; canonical sportsbook home_spread=-spread_line"
)
FLOAT_FORMAT = "%.17g"
LINE_TERMINATOR = "\n"

# Canonical V1 semantic mapping frozen in DATA_AND_PIT_INVENTORY.md. Values are
# existing leakage-safe matchup columns produced by features.build_matchup_features.
FOOTBALL_FEATURE_LINEAGE = {
    "pregame_elo_diff": "home_elo-away_elo",
    "off_epa_diff": "diff_off_epa_ewma",
    "def_epa_allowed_diff": "diff_def_epa_allowed_ewma",
    "pass_epa_diff": "diff_pass_epa_ewma",
    "def_pass_epa_allowed_diff": "diff_def_pass_epa_allowed_ewma",
    "rush_epa_diff": "diff_rush_epa_ewma",
    "def_rush_epa_allowed_diff": "diff_def_rush_epa_allowed_ewma",
    "success_rate_diff": "diff_success_rate_ewma",
    "def_success_allowed_diff": "diff_def_success_allowed_ewma",
    "neutral_epa_diff": "diff_neutral_epa_ewma",
    "rest_diff": "rest_diff",
}

MARKET_SOURCE_COLUMNS = (
    "spread_line",
    "total_line",
    "home_moneyline",
    "away_moneyline",
)


@dataclass(frozen=True)
class ChronologyPlan:
    outer_target_season: int
    outer_training_seasons: tuple[int, ...]
    inner_target_seasons: tuple[int, ...]
    inner_training_seasons: dict[int, tuple[int, ...]]


@dataclass(frozen=True)
class AtsGrade:
    margin: float
    home_spread: float
    ats_residual: float
    outcome: str
    home_cover_binary: float | None
    push: bool


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(
        index=False,
        float_format=FLOAT_FORMAT,
        lineterminator=LINE_TERMINATOR,
    ).encode("utf-8")


def _canonical_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if "game_id" not in frame.columns:
        raise ValueError("ATS Phase-2 frame is missing game_id")
    return frame.sort_values("game_id", kind="mergesort").reset_index(drop=True)


def _require_unique_game_ids(frame: pd.DataFrame) -> None:
    game_id = frame.get("game_id")
    if game_id is None:
        raise ValueError("ATS Phase-2 frame is missing game_id")
    text = game_id.astype("string")
    if text.isna().any() or text.str.strip().eq("").any():
        raise ValueError("ATS Phase-2 frame contains missing/blank game_id")
    duplicated = text.duplicated(keep=False)
    if duplicated.any():
        values = sorted(text[duplicated].astype(str).unique().tolist())
        raise ValueError(f"ATS Phase-2 frame contains duplicate game_id: {values[:5]}")


def _american_implied_probability(odds: pd.Series) -> pd.Series:
    x = pd.to_numeric(odds, errors="coerce")
    out = pd.Series(np.nan, index=x.index, dtype=float)
    positive = x > 0
    negative = x < 0
    out.loc[positive] = 100.0 / (x.loc[positive] + 100.0)
    out.loc[negative] = (-x.loc[negative]) / ((-x.loc[negative]) + 100.0)
    return out


def no_vig_home_moneyline_probability(
    home_moneyline: pd.Series,
    away_moneyline: pd.Series,
) -> pd.Series:
    """Return a two-way no-vig home probability where both moneylines are valid."""
    home = _american_implied_probability(home_moneyline)
    away = _american_implied_probability(away_moneyline)
    denom = home + away
    valid = home.notna() & away.notna() & denom.gt(0.0)
    out = pd.Series(np.nan, index=home.index, dtype=float)
    out.loc[valid] = home.loc[valid] / denom.loc[valid]
    return out


def grade_home_ats(
    home_score: float,
    away_score: float,
    home_spread: float,
    *,
    atol: float = 1e-9,
) -> AtsGrade:
    """Grade the frozen home-side ATS contract ``R=(H-A)+L``.

    ``home_spread`` is sportsbook convention: a home favorite of three points is
    ``-3``. Pushes are never coerced into wins/losses and therefore receive a
    ``None`` binary target.
    """
    values = np.asarray([home_score, away_score, home_spread], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("ATS grading requires finite home score, away score, and spread")
    margin = float(home_score) - float(away_score)
    residual = margin + float(home_spread)
    if np.isclose(residual, 0.0, atol=atol, rtol=0.0):
        return AtsGrade(margin, float(home_spread), 0.0, "PUSH", None, True)
    if residual > 0.0:
        return AtsGrade(margin, float(home_spread), residual, "HOME_COVER", 1.0, False)
    return AtsGrade(margin, float(home_spread), residual, "HOME_LOSS", 0.0, False)


def chronology_plan(outer_target_season: int) -> ChronologyPlan:
    """Return the exact expanding-window plan frozen in Phase 1."""
    season = int(outer_target_season)
    if season not in OUTER_TARGET_SEASONS:
        raise ValueError(
            f"outer target season must be one of {OUTER_TARGET_SEASONS}; got {season}"
        )
    outer_train = tuple(range(TRAINING_FLOOR, season))
    inner_targets = tuple(range(INNER_TARGET_FLOOR, season))
    inner_train = {
        target: tuple(range(TRAINING_FLOOR, target)) for target in inner_targets
    }
    plan = ChronologyPlan(season, outer_train, inner_targets, inner_train)
    assert_chronology_plan(plan)
    return plan


def assert_chronology_plan(plan: ChronologyPlan) -> None:
    """Fail closed if any outer/inner training season reaches its target season."""
    target = int(plan.outer_target_season)
    if target not in OUTER_TARGET_SEASONS:
        raise ValueError("unregistered outer target season")
    if any(s < TRAINING_FLOOR or s >= target for s in plan.outer_training_seasons):
        raise ValueError("outer chronology violation")
    expected_inner = tuple(range(INNER_TARGET_FLOOR, target))
    if tuple(plan.inner_target_seasons) != expected_inner:
        raise ValueError("inner target seasons do not match frozen rolling-origin plan")
    for inner_target in plan.inner_target_seasons:
        train = tuple(plan.inner_training_seasons.get(int(inner_target), ()))
        if not train or train[0] != TRAINING_FLOOR:
            raise ValueError(f"inner {inner_target} training floor violation")
        if train[-1] != int(inner_target) - 1:
            raise ValueError(f"inner {inner_target} chronology violation")
        if any(s >= int(inner_target) for s in train):
            raise ValueError(f"inner {inner_target} contains target/future season")


def _validate_historical_source(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "game_id",
        "season",
        "home_score",
        "away_score",
        "spread_line",
        "home_elo",
        "away_elo",
        *MARKET_SOURCE_COLUMNS,
        *(v for v in FOOTBALL_FEATURE_LINEAGE.values() if "-" not in v),
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"ATS Phase-2 source frame missing fields: {sorted(missing)}")

    work = frame.copy()
    _require_unique_game_ids(work)
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    if work["season"].isna().any():
        raise ValueError("ATS Phase-2 source frame contains invalid season")
    if work["season"].ge(HISTORICAL_END + 1).any():
        raise ValueError("ATS Phase-2 historical candidate frame may not contain 2026+ rows")
    if work["season"].lt(TRAINING_FLOOR).any():
        raise ValueError("ATS Phase-2 historical candidate frame may not contain pre-2015 rows")
    if "game_type" in work.columns and not work["game_type"].astype(str).eq("REG").all():
        raise ValueError("ATS Phase-2 V1 historical candidate frame is regular-season only")
    return work


def build_historical_ats_gate(frame: pd.DataFrame) -> pd.DataFrame:
    """Build the pre-fit, provenance-preserving ATS V1 historical gate frame.

    Rows are not silently dropped for optional-feature missingness. ``ats_eligible``
    explicitly marks rows with a final score and mandatory spread. Candidate code
    must filter on that field later. This function performs no fitting or target-
    period scoring.
    """
    work = _validate_historical_source(frame)
    out_cols = [
        c for c in (
            "game_id", "season", "week", "gameday", "gametime", "home_team",
            "away_team", "game_type", "home_score", "away_score", *MARKET_SOURCE_COLUMNS,
        ) if c in work.columns
    ]
    out = work[out_cols].copy()

    out["market_evidence_class"] = HISTORICAL_MARKET_EVIDENCE_CLASS
    out["pregame_elo_diff"] = pd.to_numeric(work["home_elo"], errors="coerce") - pd.to_numeric(
        work["away_elo"], errors="coerce"
    )
    for semantic, source in FOOTBALL_FEATURE_LINEAGE.items():
        if semantic == "pregame_elo_diff":
            continue
        out[semantic] = pd.to_numeric(work[source], errors="coerce")

    # nflverse spread_line is a home-margin market center: +3 means home favored
    # by three. Convert it once, explicitly, to the frozen sportsbook notation
    # where a home favorite is -3. Preserve the raw source field alongside it.
    source_center = pd.to_numeric(work["spread_line"], errors="coerce")
    out["home_spread"] = -source_center
    out["market_home_margin_center"] = source_center
    out["favorite_size"] = source_center.abs()
    out["market_total"] = pd.to_numeric(work["total_line"], errors="coerce")
    out["no_vig_home_moneyline_prob"] = no_vig_home_moneyline_probability(
        work["home_moneyline"], work["away_moneyline"]
    )
    out["market_total_missing"] = out["market_total"].isna()
    out["moneyline_probability_missing"] = out["no_vig_home_moneyline_prob"].isna()

    hs = pd.to_numeric(work["home_score"], errors="coerce")
    aw = pd.to_numeric(work["away_score"], errors="coerce")
    spread = out["home_spread"]
    finite_scores = np.isfinite(hs.to_numpy(dtype=float)) & np.isfinite(aw.to_numpy(dtype=float))
    finite_spread = np.isfinite(spread.to_numpy(dtype=float))
    eligible = finite_scores & finite_spread
    out["ats_eligible"] = eligible
    out["margin"] = np.where(eligible, hs - aw, np.nan)
    out["ats_residual"] = np.where(eligible, out["margin"] + spread, np.nan)
    push = eligible & np.isclose(
        out["ats_residual"].to_numpy(dtype=float), 0.0, atol=1e-9, rtol=0.0
    )
    cover = eligible & (out["ats_residual"].to_numpy(dtype=float) > 0.0) & ~push
    loss = eligible & (out["ats_residual"].to_numpy(dtype=float) < 0.0) & ~push
    out["ats_outcome"] = pd.Series(pd.NA, index=out.index, dtype="string")
    out.loc[cover, "ats_outcome"] = "HOME_COVER"
    out.loc[push, "ats_outcome"] = "PUSH"
    out.loc[loss, "ats_outcome"] = "HOME_LOSS"
    out["ats_home_cover"] = pd.array(
        np.where(cover, 1.0, np.where(loss, 0.0, np.nan)), dtype="Float64"
    )
    out["ats_push"] = push

    # A half-point home spread cannot push against integer NFL final scores. This
    # is a mechanical integrity check, not an empirical performance condition.
    half_line = eligible & np.isclose(
        np.mod(np.abs(spread.to_numpy(dtype=float)), 1.0), 0.5, atol=1e-9, rtol=0.0
    )
    if np.any(half_line & push):
        raise RuntimeError("ATS grading produced an impossible push on a half-point line")

    return out.reset_index(drop=True)


def validate_gate_frame(frame: pd.DataFrame) -> None:
    """Validate a built Phase-2 gate frame before any candidate fitting."""
    _require_unique_game_ids(frame)
    required = {
        "season", "spread_line", "market_evidence_class", "home_spread",
        "market_home_margin_center", "ats_eligible", "margin", "ats_residual",
        "ats_outcome", "ats_home_cover", "ats_push", *FOOTBALL_FEATURE_LINEAGE.keys(),
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"ATS Phase-2 gate frame missing fields: {sorted(missing)}")
    season = pd.to_numeric(frame["season"], errors="coerce")
    if season.isna().any() or season.lt(TRAINING_FLOOR).any() or season.gt(HISTORICAL_END).any():
        raise ValueError("ATS Phase-2 gate frame season boundary violation")
    if not frame["market_evidence_class"].eq(HISTORICAL_MARKET_EVIDENCE_CLASS).all():
        raise ValueError("historical market horizon was relabeled")

    source_center = pd.to_numeric(frame["spread_line"], errors="coerce")
    canonical_spread = pd.to_numeric(frame["home_spread"], errors="coerce")
    market_center = pd.to_numeric(frame["market_home_margin_center"], errors="coerce")
    finite = source_center.notna()
    if not np.allclose(
        canonical_spread.loc[finite].to_numpy(),
        -source_center.loc[finite].to_numpy(),
        atol=1e-9,
        rtol=0.0,
    ):
        raise ValueError("nflverse spread_line was not converted to sportsbook home-spread sign")
    if not np.allclose(
        market_center.loc[finite].to_numpy(),
        source_center.loc[finite].to_numpy(),
        atol=1e-9,
        rtol=0.0,
    ):
        raise ValueError("market home-margin center does not preserve nflverse spread_line")

    eligible = frame["ats_eligible"].astype(bool)
    expected = pd.to_numeric(frame.loc[eligible, "margin"], errors="raise") + pd.to_numeric(
        frame.loc[eligible, "home_spread"], errors="raise"
    )
    actual = pd.to_numeric(frame.loc[eligible, "ats_residual"], errors="raise")
    if not np.allclose(expected.to_numpy(), actual.to_numpy(), atol=1e-9, rtol=0.0):
        raise ValueError("ATS residual violates canonical margin + home_spread contract")

    push = np.isclose(actual.to_numpy(dtype=float), 0.0, atol=1e-9, rtol=0.0)
    outcomes = frame.loc[eligible, "ats_outcome"].astype(str).to_numpy()
    expected_outcome = np.where(
        push, "PUSH", np.where(actual.to_numpy() > 0, "HOME_COVER", "HOME_LOSS")
    )
    if not np.array_equal(outcomes, expected_outcome):
        raise ValueError("ATS outcome labels disagree with canonical residual")
    binary = frame.loc[eligible, "ats_home_cover"]
    if binary[push].notna().any():
        raise ValueError("ATS pushes may not be coerced into a binary cover target")


def _artifact_summary(frame: pd.DataFrame) -> dict:
    raw = _csv_bytes(frame)
    canonical = _csv_bytes(_canonical_frame(frame))
    season = pd.to_numeric(frame["season"], errors="raise")
    return {
        "rows": int(len(frame)),
        "first_season": int(season.min()) if len(frame) else None,
        "last_season": int(season.max()) if len(frame) else None,
        "raw_sha256": _sha256(raw),
        "canonical_game_keyed_sha256": _sha256(canonical),
        "game_ids_unique": bool(frame["game_id"].astype(str).is_unique),
    }


def write_phase2_gate_artifacts(
    frame: pd.DataFrame,
    output_dir: str | Path,
    *,
    source_description: str,
) -> dict:
    """Persist the exact pre-fit gate frame plus its scientific lineage manifest."""
    validate_gate_frame(frame)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "phase2_gate_frame.csv"
    raw = _csv_bytes(frame)
    csv_path.write_bytes(raw)

    manifest = {
        "schema_version": 1,
        "program": PROGRAM_ID,
        "phase": PHASE,
        "stage": "pre_result_pre_fit_gate",
        "candidate_fitting_performed": False,
        "candidate_performance_generated": False,
        "completed_2026_outcomes_authorized": False,
        "historical_training_floor": TRAINING_FLOOR,
        "historical_outcome_cutoff_season": HISTORICAL_END,
        "outer_target_seasons": list(OUTER_TARGET_SEASONS),
        "inner_target_floor": INNER_TARGET_FLOOR,
        "random_kfold_allowed": False,
        "canonical_sign": {
            "margin": "home_score-away_score",
            "home_spread": "sportsbook home spread; home favorite is negative",
            "ats_residual": "margin+home_spread",
            "cover": "ats_residual>0",
            "push": "ats_residual==0",
            "loss": "ats_residual<0",
        },
        "market_evidence_class": HISTORICAL_MARKET_EVIDENCE_CLASS,
        "source_spread_convention": NFLVERSE_SPREAD_SOURCE_CONVENTION,
        "source_description": str(source_description),
        "market_lineage": {
            "source_spread_line": "nflverse spread_line; positive when home favored",
            "home_spread": "-spread_line",
            "market_home_margin_center": "spread_line",
            "favorite_size": "abs(spread_line)",
            "market_total": "total_line",
            "no_vig_home_moneyline_prob": "two_way_no_vig(home_moneyline,away_moneyline)",
            "q1_fixed_interactions": (
                "derived inside each training fold after training-fold total centering; "
                "no full-sample centering in this gate"
            ),
        },
        "football_feature_lineage": FOOTBALL_FEATURE_LINEAGE,
        "artifact": {
            "path": csv_path.name,
            **_artifact_summary(frame),
            "raw_sha256": _sha256(raw),
        },
        "eligibility": {
            "ats_eligible_rows": int(frame["ats_eligible"].astype(bool).sum()),
            "push_rows": int(frame["ats_push"].astype(bool).sum()),
            "ineligible_rows": int((~frame["ats_eligible"].astype(bool)).sum()),
        },
        "chronology_plans": {
            str(season): asdict(chronology_plan(season)) for season in OUTER_TARGET_SEASONS
        },
    }
    manifest_path = out / "phase2_gate_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
