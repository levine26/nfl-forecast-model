from __future__ import annotations

"""Season-forward availability/workload mixtures for LevLine Props 2.0 research.

The model target is offensive workload conditional on a historical pregame injury designation.
No player-prop outcome, sportsbook result, Fair-Line error, or completed-2026 outcome is consumed.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping

import numpy as np
import pandas as pd

CONTRACT_VERSION = "levline-props-v2-availability-workload-v0.1.0"
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
SUPPORTED_STATES = ("OUT", "ACTIVE_LIMITED", "ACTIVE_NORMAL", "ACTIVE_ELEVATED")
SUPPORTED_DESIGNATIONS = ("QUESTIONABLE", "DOUBTFUL")

BASELINE_LOOKBACK_GAMES = 4
MIN_BASELINE_GAMES = 2
MIN_BASELINE_SNAP_SHARE = 0.15
LIMITED_THRESHOLD = 0.75
ELEVATED_THRESHOLD = 1.25
MAX_WORKLOAD_RATIO = 2.0
DIRICHLET_ALPHA = 1.0
BETA_ALPHA = 1.0
BETA_BETA = 1.0
MIN_POSITION_DESIGNATION_ROWS = 40
EPS = 1e-12


class AvailabilityMixtureError(ValueError):
    pass


@dataclass(frozen=True)
class MixtureFit:
    designation: str
    position: str
    fit_scope: str
    training_rows: int
    state_counts: dict[str, int]
    state_probabilities: dict[str, float]
    state_mean_workload_ratio: dict[str, float]
    state_sd_workload_ratio: dict[str, float]
    active_probability: float
    expected_workload_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _team(value: Any) -> str:
    text = str(value or "").upper().strip()
    return {
        "JAC": "JAX",
        "LA": "LAR",
        "STL": "LAR",
        "WSH": "WAS",
    }.get(text, text)


def _valid_id(value: Any) -> bool:
    try:
        if value is None or pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return bool(text) and text.lower() not in {"nan", "<na>", "none", "null"}


def _designation(value: Any) -> str:
    text = str(value or "").lower().strip()
    if "questionable" in text:
        return "QUESTIONABLE"
    if "doubtful" in text:
        return "DOUBTFUL"
    return ""


def normalize_injury_designations(
    injuries: pd.DataFrame,
    *,
    max_season: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {"season", "week", "team", "gsis_id", "position", "report_status"}
    missing = required - set(injuries.columns)
    if missing:
        raise AvailabilityMixtureError(
            f"injury history missing required columns: {sorted(missing)}"
        )

    work = injuries.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    work["team"] = work["team"].map(_team)
    work["player_id"] = work["gsis_id"].astype("string").fillna("").str.strip()
    work["position"] = (
        work["position"].astype("string").fillna("").str.upper().str.strip()
    )
    work["designation"] = work["report_status"].map(_designation)
    work = work[
        work["season"].notna()
        & work["week"].notna()
        & work["season"].le(int(max_season))
        & work["week"].between(1, 18)
        & work["position"].isin(SUPPORTED_POSITIONS)
        & work["designation"].isin(SUPPORTED_DESIGNATIONS)
        & work["player_id"].map(_valid_id)
        & work["team"].ne("")
    ].copy()
    if "season_type" in work.columns:
        work = work[
            work["season_type"].astype(str).str.upper().eq("REG")
        ].copy()
    elif "game_type" in work.columns:
        work = work[
            work["game_type"].astype(str).str.upper().eq("REG")
        ].copy()

    dedupe = ["season", "week", "team", "player_id"]
    if "date_modified" in work.columns:
        work["_modified"] = pd.to_datetime(
            work["date_modified"], utc=True, errors="coerce"
        )
        work = (
            work.sort_values(dedupe + ["_modified"], na_position="first")
            .drop_duplicates(dedupe, keep="last")
        )
    else:
        work = work.drop_duplicates(dedupe, keep="last")

    return work.reset_index(drop=True), {
        "contract_version": CONTRACT_VERSION,
        "rows": int(len(work)),
        "seasons": sorted(work["season"].astype(int).unique().tolist()) if len(work) else [],
        "designations": work["designation"].value_counts().to_dict(),
        "positions": work["position"].value_counts().to_dict(),
        "historical_publication_timestamp_claimed": False,
        "prop_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def normalize_snap_history(
    snap_counts: pd.DataFrame,
    *,
    max_season: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    required = {"season", "week", "team", "player_id"}
    missing = required - set(snap_counts.columns)
    if missing:
        raise AvailabilityMixtureError(
            f"snap history missing required columns: {sorted(missing)}"
        )

    work = snap_counts.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    work["team"] = work["team"].map(_team)
    work["player_id"] = (
        work["player_id"].astype("string").fillna("").str.strip()
    )
    work = work[
        work["season"].notna()
        & work["week"].notna()
        & work["season"].le(int(max_season))
        & work["week"].between(1, 18)
        & work["player_id"].map(_valid_id)
        & work["team"].ne("")
    ].copy()
    if "game_type" in work.columns:
        work = work[work["game_type"].astype(str).str.upper().eq("REG")].copy()
    elif "season_type" in work.columns:
        work = work[
            work["season_type"].astype(str).str.upper().eq("REG")
        ].copy()

    pct_col = next(
        (
            c
            for c in (
                "offense_pct",
                "offensive_snap_pct",
                "offense_snaps_pct",
                "snap_share",
            )
            if c in work.columns
        ),
        None,
    )
    snap_col = next(
        (
            c
            for c in ("offense_snaps", "offensive_snaps", "off_snaps")
            if c in work.columns
        ),
        None,
    )
    if pct_col is None and snap_col is None:
        raise AvailabilityMixtureError(
            "snap history requires offensive snap percentage or count"
        )

    share = pd.Series(np.nan, index=work.index, dtype=float)
    source_parts: list[str] = []
    if pct_col is not None:
        pct = pd.to_numeric(work[pct_col], errors="coerce")
        pct = pd.Series(np.where(pct > 1.0, pct / 100.0, pct), index=work.index)
        share.loc[pct.notna()] = pct.loc[pct.notna()]
        source_parts.append(f"provider:{pct_col}")

    derived_rows = 0
    if snap_col is not None:
        snaps = pd.to_numeric(work[snap_col], errors="coerce")
        work["_offense_snaps"] = snaps
        denom = (
            pd.DataFrame(
                {
                    "season": work["season"],
                    "week": work["week"],
                    "team": work["team"],
                    "snaps": snaps,
                },
                index=work.index,
            )
            .groupby(["season", "week", "team"], sort=False)["snaps"]
            .transform("max")
        )
        derived = snaps / denom.replace(0.0, np.nan)
        fill = share.isna() & derived.notna()
        share.loc[fill] = derived.loc[fill]
        derived_rows = int(fill.sum())
        if fill.any():
            source_parts.append("derived_team_week_snap_ratio")
    else:
        work["_offense_snaps"] = np.nan

    work["snap_share"] = pd.to_numeric(share, errors="coerce")
    work = work[work["snap_share"].between(0.0, 1.0, inclusive="both")].copy()

    # One player/team/week observation. Max protects against accidental duplicated source rows.
    grouped = (
        work.groupby(
            ["season", "week", "team", "player_id"],
            as_index=False,
            sort=False,
        )
        .agg(
            snap_share=("snap_share", "max"),
            offense_snaps=("_offense_snaps", "max"),
        )
    )
    return grouped, {
        "contract_version": CONTRACT_VERSION,
        "rows": int(len(grouped)),
        "unique_players": int(grouped["player_id"].nunique()) if len(grouped) else 0,
        "source": "+".join(source_parts) or "unknown",
        "derived_share_rows": derived_rows,
        "prop_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def _period_key(season: int, week: int) -> int:
    return int(season) * 100 + int(week)


def _prior_baseline(
    snap_history: pd.DataFrame,
    *,
    player_id: str,
    season: int,
    week: int,
) -> tuple[float | None, int]:
    prior = snap_history[
        snap_history["player_id"].astype(str).eq(str(player_id))
        & (
            (snap_history["season"].astype(int) < int(season))
            | (
                snap_history["season"].astype(int).eq(int(season))
                & snap_history["week"].astype(int).lt(int(week))
            )
        )
    ].copy()
    if prior.empty:
        return None, 0
    prior["_period"] = [
        _period_key(s, w)
        for s, w in zip(prior["season"], prior["week"])
    ]
    prior = prior.sort_values("_period").tail(BASELINE_LOOKBACK_GAMES)
    values = pd.to_numeric(prior["snap_share"], errors="coerce").dropna()
    if len(values) < MIN_BASELINE_GAMES:
        return None, int(len(values))
    return float(values.mean()), int(len(values))


def build_workload_examples(
    injuries: pd.DataFrame,
    snap_history: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Join historical designations to strictly prior workload baselines and realized snap share.

    Missing player rows are interpreted as zero only when the team-week has snap-count coverage.
    """
    if injuries.empty or snap_history.empty:
        return pd.DataFrame(), {"rows": 0, "reason": "empty_inputs"}

    coverage = set(
        zip(
            snap_history["season"].astype(int),
            snap_history["week"].astype(int),
            snap_history["team"].astype(str),
        )
    )
    current = {
        (int(row.season), int(row.week), str(row.team), str(row.player_id)): float(row.snap_share)
        for row in snap_history.itertuples(index=False)
    }

    rows: list[dict[str, Any]] = []
    exclusions: dict[str, int] = {}
    def exclude(reason: str) -> None:
        exclusions[reason] = exclusions.get(reason, 0) + 1

    for row in injuries.itertuples(index=False):
        key_team = (int(row.season), int(row.week), str(row.team))
        if key_team not in coverage:
            exclude("team_week_snap_coverage_missing")
            continue
        baseline, baseline_games = _prior_baseline(
            snap_history,
            player_id=str(row.player_id),
            season=int(row.season),
            week=int(row.week),
        )
        if baseline is None:
            exclude("insufficient_prior_workload_history")
            continue
        if baseline < MIN_BASELINE_SNAP_SHARE:
            exclude("baseline_role_too_small")
            continue

        actual_share = current.get(
            (int(row.season), int(row.week), str(row.team), str(row.player_id)),
            0.0,
        )
        ratio_raw = float(actual_share) / max(float(baseline), EPS)
        ratio = float(np.clip(ratio_raw, 0.0, MAX_WORKLOAD_RATIO))
        if actual_share <= EPS:
            state = "OUT"
        elif ratio < LIMITED_THRESHOLD:
            state = "ACTIVE_LIMITED"
        elif ratio <= ELEVATED_THRESHOLD:
            state = "ACTIVE_NORMAL"
        else:
            state = "ACTIVE_ELEVATED"

        rows.append(
            {
                "contract_version": CONTRACT_VERSION,
                "season": int(row.season),
                "week": int(row.week),
                "team": str(row.team),
                "player_id": str(row.player_id),
                "position": str(row.position),
                "designation": str(row.designation),
                "baseline_snap_share": float(baseline),
                "baseline_games": int(baseline_games),
                "actual_snap_share": float(actual_share),
                "workload_ratio_raw": float(ratio_raw),
                "workload_ratio": float(ratio),
                "workload_state": state,
                "active": bool(state != "OUT"),
            }
        )
    out = pd.DataFrame(rows)
    return out, {
        "contract_version": CONTRACT_VERSION,
        "rows": int(len(out)),
        "exclusions": exclusions,
        "thresholds": {
            "limited_below": LIMITED_THRESHOLD,
            "normal_upper": ELEVATED_THRESHOLD,
            "max_workload_ratio": MAX_WORKLOAD_RATIO,
            "baseline_lookback_games": BASELINE_LOOKBACK_GAMES,
            "minimum_baseline_games": MIN_BASELINE_GAMES,
            "minimum_baseline_snap_share": MIN_BASELINE_SNAP_SHARE,
        },
        "prop_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }


def _fit_rows(rows: pd.DataFrame, designation: str, position: str) -> tuple[pd.DataFrame, str]:
    exact = rows[
        rows["designation"].eq(designation)
        & rows["position"].eq(position)
    ].copy()
    if len(exact) >= MIN_POSITION_DESIGNATION_ROWS:
        return exact, "designation_position"
    pooled = rows[rows["designation"].eq(designation)].copy()
    if pooled.empty:
        raise AvailabilityMixtureError(
            f"no training rows for designation {designation}"
        )
    return pooled, "designation_pooled"


def _state_distribution(rows: pd.DataFrame) -> tuple[dict[str, float], dict[str, int]]:
    counts = {
        state: int(rows["workload_state"].eq(state).sum())
        for state in SUPPORTED_STATES
    }
    denom = len(rows) + DIRICHLET_ALPHA * len(SUPPORTED_STATES)
    probs = {
        state: (counts[state] + DIRICHLET_ALPHA) / denom
        for state in SUPPORTED_STATES
    }
    return probs, counts


def _state_moments(rows: pd.DataFrame) -> tuple[dict[str, float], dict[str, float]]:
    means: dict[str, float] = {}
    sds: dict[str, float] = {}
    for state in SUPPORTED_STATES:
        if state == "OUT":
            means[state] = 0.0
            sds[state] = 0.0
            continue
        values = pd.to_numeric(
            rows.loc[rows["workload_state"].eq(state), "workload_ratio"],
            errors="coerce",
        ).dropna()
        if values.empty:
            # Semantic state midpoint fallbacks are fixed and outcome-independent.
            fallback = {
                "ACTIVE_LIMITED": LIMITED_THRESHOLD / 2.0,
                "ACTIVE_NORMAL": 1.0,
                "ACTIVE_ELEVATED": (ELEVATED_THRESHOLD + MAX_WORKLOAD_RATIO) / 2.0,
            }[state]
            means[state] = float(fallback)
            sds[state] = 0.0
        else:
            means[state] = float(values.mean())
            sds[state] = float(values.std(ddof=1)) if len(values) >= 2 else 0.0
    return means, sds


def fit_workload_mixtures(
    examples: pd.DataFrame,
    *,
    trained_through_season: int,
) -> dict[tuple[str, str], MixtureFit]:
    train = examples[
        pd.to_numeric(examples["season"], errors="coerce").le(int(trained_through_season))
    ].copy()
    if train.empty:
        raise AvailabilityMixtureError("no training examples before evaluation season")

    fits: dict[tuple[str, str], MixtureFit] = {}
    for designation in SUPPORTED_DESIGNATIONS:
        for position in sorted(SUPPORTED_POSITIONS):
            rows, scope = _fit_rows(train, designation, position)
            probs, counts = _state_distribution(rows)
            means, sds = _state_moments(rows)
            active_p = 1.0 - probs["OUT"]
            expected = sum(probs[state] * means[state] for state in SUPPORTED_STATES)
            fits[(designation, position)] = MixtureFit(
                designation=designation,
                position=position,
                fit_scope=scope,
                training_rows=int(len(rows)),
                state_counts=counts,
                state_probabilities=probs,
                state_mean_workload_ratio=means,
                state_sd_workload_ratio=sds,
                active_probability=float(active_p),
                expected_workload_ratio=float(expected),
            )
    return fits


def fit_active_only_priors(
    examples: pd.DataFrame,
    *,
    trained_through_season: int,
) -> dict[str, float]:
    train = examples[
        pd.to_numeric(examples["season"], errors="coerce").le(int(trained_through_season))
    ].copy()
    result: dict[str, float] = {}
    for designation in SUPPORTED_DESIGNATIONS:
        rows = train[train["designation"].eq(designation)]
        if rows.empty:
            raise AvailabilityMixtureError(
                f"no active-only training rows for {designation}"
            )
        successes = int(rows["active"].astype(bool).sum())
        failures = int(len(rows) - successes)
        alpha = BETA_ALPHA + successes
        beta = BETA_BETA + failures
        result[designation] = float(alpha / (alpha + beta))
    return result


def multiclass_brier(probabilities: Mapping[str, float], actual_state: str) -> float:
    if actual_state not in SUPPORTED_STATES:
        raise AvailabilityMixtureError(f"unsupported actual state {actual_state}")
    return float(
        sum(
            (float(probabilities.get(state, 0.0)) - (1.0 if state == actual_state else 0.0)) ** 2
            for state in SUPPORTED_STATES
        )
    )


def evaluate_season_forward(
    examples: pd.DataFrame,
    *,
    evaluation_season: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    train_end = int(evaluation_season) - 1
    fits = fit_workload_mixtures(
        examples,
        trained_through_season=train_end,
    )
    active_only = fit_active_only_priors(
        examples,
        trained_through_season=train_end,
    )
    test = examples[examples["season"].astype(int).eq(int(evaluation_season))].copy()
    if test.empty:
        raise AvailabilityMixtureError(
            f"no evaluation examples for {evaluation_season}"
        )

    rows: list[dict[str, Any]] = []
    for row in test.itertuples(index=False):
        fit = fits[(str(row.designation), str(row.position))]
        mix_expected = float(fit.expected_workload_ratio)
        active_expected = float(active_only[str(row.designation)])
        actual = float(row.workload_ratio)
        actual_active = 1.0 if bool(row.active) else 0.0
        mix_active = float(fit.active_probability)

        rows.append(
            {
                **row._asdict(),
                "trained_through_season": train_end,
                "fit_scope": fit.fit_scope,
                "fit_training_rows": fit.training_rows,
                "mixture_expected_workload_ratio": mix_expected,
                "active_only_expected_workload_ratio": active_expected,
                "mixture_abs_error": abs(mix_expected - actual),
                "active_only_abs_error": abs(active_expected - actual),
                "mixture_active_probability": mix_active,
                "active_only_probability": active_expected,
                "mixture_active_brier": (mix_active - actual_active) ** 2,
                "active_only_brier": (active_expected - actual_active) ** 2,
                "mixture_state_brier": multiclass_brier(
                    fit.state_probabilities, str(row.workload_state)
                ),
                "mixture_state_log_loss": -math.log(
                    max(float(fit.state_probabilities[str(row.workload_state)]), EPS)
                ),
            }
        )
    scored = pd.DataFrame(rows)
    summary = {
        "contract_version": CONTRACT_VERSION,
        "evaluation_season": int(evaluation_season),
        "trained_through_season": train_end,
        "n": int(len(scored)),
        "unique_players": int(scored["player_id"].nunique()),
        "mixture_workload_mae": float(scored["mixture_abs_error"].mean()),
        "active_only_workload_mae": float(scored["active_only_abs_error"].mean()),
        "mixture_minus_active_only_mae": float(
            (scored["mixture_abs_error"] - scored["active_only_abs_error"]).mean()
        ),
        "mixture_active_brier": float(scored["mixture_active_brier"].mean()),
        "active_only_brier": float(scored["active_only_brier"].mean()),
        "mixture_state_brier": float(scored["mixture_state_brier"].mean()),
        "mixture_state_log_loss": float(scored["mixture_state_log_loss"].mean()),
        "state_counts": scored["workload_state"].value_counts().to_dict(),
        "designation_counts": scored["designation"].value_counts().to_dict(),
        "position_counts": scored["position"].value_counts().to_dict(),
        "mixture_fits": {
            f"{designation}:{position}": fit.to_dict()
            for (designation, position), fit in fits.items()
        },
        "active_only_priors": active_only,
        "prop_outcomes_used_for_fit_or_evaluation": 0,
        "completed_2026_outcomes_used": 0,
        "production_authorized": False,
    }
    return scored, summary
