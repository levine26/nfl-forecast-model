from __future__ import annotations

"""Point-in-time upstream assembly for LevLine Props Research Beta.

This module removes hand-built intermediate tables without introducing new model
assumptions. It derives strictly lagged observable counts from PBP and requires every
non-observable prior/context explicitly from the caller.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import math

import numpy as np
import pandas as pd

from .props_efficiency_td import SOURCE_STATES, build_efficiency_td_parameters
from .props_integration import build_efficiency_player_inputs, build_efficiency_team_input
from .props_opportunity import ForecastContext
from .props_opportunity_handoff import build_simulation_ready_opportunity_projection
from .props_player_state import normalize_team_code


SUPPORTED_POSITIONS = {"QB", "RB", "WR", "TE"}
EFFICIENCY_PRIOR_FIELDS = {
    "prior_completion_rate",
    "prior_yards_per_completion_mean",
    "prior_yards_per_completion_sd",
    "prior_qb_rush_ypc_mean",
    "prior_qb_rush_ypc_sd",
    "prior_rush_ypc_mean",
    "prior_rush_ypc_sd",
    "prior_catch_rate",
    "prior_receiving_ypr_mean",
    "prior_receiving_ypr_sd",
    "prior_red_zone_target_rate",
    "prior_end_zone_target_rate",
    "prior_goal_line_carry_rate",
}
SCORING_CONTEXT_FIELDS = {
    "expected_drives",
    "expected_red_zone_trips",
    "prior_red_zone_td_rate",
    "prior_pass_td_fraction",
    "expected_non_red_zone_pass_tds",
    "expected_non_red_zone_rush_tds",
}


class PropsUpstreamError(ValueError):
    pass


@dataclass(frozen=True)
class LaggedPropsHistory:
    team_history: pd.DataFrame
    player_history: pd.DataFrame
    efficiency_history: pd.DataFrame
    audit: dict[str, Any]


@dataclass(frozen=True)
class PropsGameUpstreamPackage:
    game_id: str
    opportunity_projections: tuple[dict[str, Any], ...]
    efficiency_player_parameters: tuple[dict[str, Any], ...]
    team_td_parameters: tuple[dict[str, Any], ...]
    residual_efficiency_by_team: dict[str, Any]
    audit: dict[str, Any]


def _number(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        raise PropsUpstreamError(f"PBP missing required column: {column}")
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0)


def _text(frame: pd.DataFrame, *candidates: str) -> pd.Series:
    column = next((name for name in candidates if name in frame.columns), None)
    if column is None:
        return pd.Series("", index=frame.index, dtype="string")
    return frame[column].astype("string").fillna("").str.strip()


def _valid_id(series: pd.Series) -> pd.Series:
    text = series.astype("string").fillna("").str.strip()
    return text.ne("") & text.ne("<NA>") & text.str.lower().ne("nan")


def normalize_nflverse_scramble_semantics(
    pbp: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Normalize nflverse scramble labels to official rushing-stat semantics.

    nflverse's `rush_attempt` is the statistical run indicator, while
    `qb_scramble` is also derived from play-description evidence. A nullified or
    otherwise non-statistical play may therefore retain a scramble description
    without being an official rushing attempt. LevLine needs `qb_scramble` to be a
    strict subset of official rushing attempts so it can separate QB scrambles from
    designed carries without creating phantom opportunities.

    For an official scramble, nflverse may identify the player in the rusher field
    rather than `passer_player_id`. Existing stable rusher identity is authoritative;
    only when it is absent do we fill it from the passer/QB identity. We fail closed
    only when an official scramble has neither stable rusher nor passer identity.

    This adapter never promotes a non-rush into a rush and never consults outcomes,
    markets, or evaluation targets.
    """

    required = {"qb_scramble", "rush_attempt"}
    missing = required - set(pbp.columns)
    if missing:
        raise PropsUpstreamError(
            f"PBP missing scramble-normalization fields: {sorted(missing)}"
        )

    out = pbp.copy()
    scramble_raw = pd.to_numeric(
        out["qb_scramble"], errors="coerce"
    ).fillna(0.0).eq(1)
    rush = pd.to_numeric(out["rush_attempt"], errors="coerce").fillna(0.0).eq(1)

    non_stat_scramble = scramble_raw & ~rush
    out.loc[non_stat_scramble, "qb_scramble"] = 0
    countable_scramble = scramble_raw & rush

    passer = _text(out, "passer_player_id", "passer_id")
    rusher_col = next(
        (name for name in ("rusher_player_id", "rusher_id") if name in out.columns),
        None,
    )
    if rusher_col is None:
        out["rusher_player_id"] = ""
        rusher_col = "rusher_player_id"
    rusher = out[rusher_col].astype("string").fillna("").str.strip()

    rusher_valid = _valid_id(rusher)
    passer_valid = _valid_id(passer)
    missing_all_identity = countable_scramble & ~rusher_valid & ~passer_valid
    if missing_all_identity.any():
        examples = []
        for idx in out.index[missing_all_identity][:5]:
            examples.append(
                {
                    "game_id": str(out.at[idx, "game_id"])
                    if "game_id" in out.columns
                    else None,
                    "play_id": _jsonable_play_id(out.at[idx, "play_id"])
                    if "play_id" in out.columns
                    else None,
                }
            )
        raise PropsUpstreamError(
            "countable qb_scramble row is missing stable rusher/QB identity; "
            f"refusing source repair: {examples}"
        )

    missing_rusher = countable_scramble & ~rusher_valid & passer_valid
    out.loc[missing_rusher, rusher_col] = passer[missing_rusher].astype(str)

    audit = {
        "policy": "qb_scramble_must_be_official_rush_attempt",
        "identity_policy": "existing_rusher_then_passer_fallback",
        "raw_scramble_rows": int(scramble_raw.sum()),
        "countable_scramble_rows": int(countable_scramble.sum()),
        "non_statistical_scramble_labels_suppressed": int(non_stat_scramble.sum()),
        "rush_attempt_promotions": 0,
        "countable_scrambles_with_existing_rusher_id": int(
            (countable_scramble & rusher_valid).sum()
        ),
        "rusher_identity_repairs_from_passer": int(missing_rusher.sum()),
        "non_scramble_rows_modified": 0,
        "outcome_or_market_fields_used_for_repair": False,
    }
    return out, audit



def _jsonable_play_id(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _safe_history(pbp: pd.DataFrame, *, season: int, week: int) -> pd.DataFrame:
    required = {"game_id", "season", "week", "posteam"}
    missing = required - set(pbp.columns)
    if missing:
        raise PropsUpstreamError(f"PBP missing history keys: {sorted(missing)}")
    if "qb_scramble" not in pbp.columns:
        raise PropsUpstreamError(
            "PBP requires explicit qb_scramble for coherent designed-carry history"
        )
    for yardage in ("passing_yards", "rushing_yards", "receiving_yards"):
        if yardage not in pbp.columns:
            raise PropsUpstreamError(f"PBP missing efficiency field: {yardage}")

    out = pbp.copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce")
    out["week"] = pd.to_numeric(out["week"], errors="coerce")
    valid_period = out["season"].notna() & out["week"].notna()
    safe = out["season"].lt(season) | (
        out["season"].eq(season) & out["week"].lt(week)
    )
    out = out[valid_period & safe].copy()
    if out.empty:
        raise PropsUpstreamError("No strictly prior-week PBP is available")
    out["season"] = out["season"].astype(int)
    out["week"] = out["week"].astype(int)
    out["team"] = out["posteam"].map(normalize_team_code)
    out = out[out["team"].astype(str).str.strip().ne("")].copy()
    return out


def _position_lookup(player_identity: pd.DataFrame) -> tuple[dict[str, str], dict[str, Any]]:
    if player_identity is None or player_identity.empty:
        raise PropsUpstreamError("player identity crosswalk is required")
    id_col = next(
        (name for name in ("gsis_id", "player_id", "nflverse_id") if name in player_identity.columns),
        None,
    )
    position_col = next(
        (name for name in ("position", "position_group") if name in player_identity.columns),
        None,
    )
    if id_col is None or position_col is None:
        raise PropsUpstreamError("player identity requires stable ID and position columns")

    work = player_identity[[id_col, position_col]].copy()
    work["player_id"] = work[id_col].astype("string").fillna("").str.strip()
    work["position"] = work[position_col].astype("string").fillna("").str.upper().str.strip()
    work = work[_valid_id(work["player_id"]) & work["position"].isin(SUPPORTED_POSITIONS)]

    grouped = work.groupby("player_id", sort=False)["position"].agg(lambda values: sorted(set(values)))
    ambiguous = {str(pid) for pid, values in grouped.items() if len(values) != 1}
    safe = {
        str(pid): values[0]
        for pid, values in grouped.items()
        if len(values) == 1
    }
    return safe, {
        "identity_rows_received": int(len(player_identity)),
        "supported_unique_ids": len(safe),
        "ambiguous_position_ids": sorted(ambiguous),
    }


def build_lagged_props_history(
    pbp: pd.DataFrame,
    player_identity: pd.DataFrame,
    *,
    season: int,
    week: int,
) -> LaggedPropsHistory:
    """Build opportunity and efficiency sufficient statistics from strictly lagged PBP."""

    work = _safe_history(pbp, season=season, week=week)
    positions, identity_audit = _position_lookup(player_identity)

    pass_attempt = _number(work, "pass_attempt").eq(1)
    sack = _number(work, "sack").eq(1)
    rush_attempt = _number(work, "rush_attempt").eq(1)
    scramble = _number(work, "qb_scramble").eq(1)
    complete = _number(work, "complete_pass").eq(1)
    if (scramble & ~rush_attempt).any():
        raise PropsUpstreamError("qb_scramble rows must also be rush_attempt rows")

    receiver_id = _text(work, "receiver_player_id", "receiver_id")
    passer_id = _text(work, "passer_player_id", "passer_id")
    rusher_id = _text(work, "rusher_player_id", "rusher_id")
    target = pass_attempt & _valid_id(receiver_id)

    event_counts = work[["game_id", "season", "week", "team"]].copy()
    event_counts["pass_attempts"] = pass_attempt.astype(float)
    event_counts["sacks"] = sack.astype(float)
    event_counts["qb_scrambles"] = scramble.astype(float)
    event_counts["team_rush_attempts"] = rush_attempt.astype(float)
    event_counts["team_targets"] = target.astype(float)
    team_history = (
        event_counts.groupby(["game_id", "season", "week", "team"], as_index=False, sort=False)
        .sum(numeric_only=True)
    )
    team_history["designed_rush_attempts"] = (
        team_history["team_rush_attempts"] - team_history["qb_scrambles"]
    )
    if (team_history["designed_rush_attempts"] < -1e-9).any():
        raise PropsUpstreamError("qb scrambles exceed team rush attempts")
    team_history["designed_rush_attempts"] = team_history["designed_rush_attempts"].clip(lower=0)
    team_history["dropbacks"] = (
        team_history["pass_attempts"] + team_history["sacks"] + team_history["qb_scrambles"]
    )
    team_history["offensive_plays"] = (
        team_history["dropbacks"] + team_history["designed_rush_attempts"]
    )
    if (team_history["team_targets"] > team_history["pass_attempts"] + 1e-9).any():
        raise PropsUpstreamError("derived team targets exceed pass attempts")

    yardline = (
        pd.to_numeric(work["yardline_100"], errors="coerce")
        if "yardline_100" in work.columns
        else pd.Series(np.nan, index=work.index, dtype=float)
    )
    red_zone = yardline.le(20)
    goal_line = yardline.le(5)
    air_yards = (
        pd.to_numeric(work["air_yards"], errors="coerce")
        if "air_yards" in work.columns
        else pd.Series(np.nan, index=work.index, dtype=float)
    )
    end_zone_target = target & yardline.notna() & air_yards.notna() & air_yards.ge(yardline)

    events: list[pd.DataFrame] = []
    rusher_mask = rush_attempt & _valid_id(rusher_id)
    if rusher_mask.any():
        part = work.loc[rusher_mask, ["game_id", "season", "week", "team"]].copy()
        ids = rusher_id.loc[rusher_mask].astype(str)
        part["player_id"] = ids.to_numpy()
        part["position"] = ids.map(positions).to_numpy()
        scramble_rows = scramble.loc[rusher_mask]
        part["designed_carries"] = (~scramble_rows).astype(float).to_numpy()
        part["qb_scrambles"] = scramble_rows.astype(float).to_numpy()
        part["targets"] = 0.0
        part["receptions"] = 0.0
        part["red_zone_carries"] = red_zone.loc[rusher_mask].fillna(False).astype(float).to_numpy()
        part["goal_line_carries"] = goal_line.loc[rusher_mask].fillna(False).astype(float).to_numpy()
        part["red_zone_targets"] = 0.0
        part["end_zone_targets"] = 0.0
        part["routes"] = np.nan
        events.append(part)

    receiver_mask = target
    if receiver_mask.any():
        part = work.loc[receiver_mask, ["game_id", "season", "week", "team"]].copy()
        ids = receiver_id.loc[receiver_mask].astype(str)
        part["player_id"] = ids.to_numpy()
        part["position"] = ids.map(positions).to_numpy()
        part["designed_carries"] = 0.0
        part["qb_scrambles"] = 0.0
        part["targets"] = 1.0
        part["receptions"] = complete.loc[receiver_mask].astype(float).to_numpy()
        part["red_zone_carries"] = 0.0
        part["goal_line_carries"] = 0.0
        part["red_zone_targets"] = red_zone.loc[receiver_mask].fillna(False).astype(float).to_numpy()
        part["end_zone_targets"] = end_zone_target.loc[receiver_mask].fillna(False).astype(float).to_numpy()
        part["routes"] = np.nan
        events.append(part)

    if not events:
        raise PropsUpstreamError("No supported historical player opportunities were derived")

    raw_player_events = pd.concat(events, ignore_index=True)
    unresolved_player_events = int(raw_player_events["position"].isna().sum())
    player_events = raw_player_events[
        raw_player_events["position"].isin(SUPPORTED_POSITIONS)
    ].copy()
    player_history = (
        player_events.groupby(
            ["game_id", "season", "week", "team", "player_id", "position"],
            as_index=False,
            sort=False,
        )
        .agg(
            designed_carries=("designed_carries", "sum"),
            qb_scrambles=("qb_scrambles", "sum"),
            targets=("targets", "sum"),
            receptions=("receptions", "sum"),
            red_zone_carries=("red_zone_carries", "sum"),
            goal_line_carries=("goal_line_carries", "sum"),
            red_zone_targets=("red_zone_targets", "sum"),
            end_zone_targets=("end_zone_targets", "sum"),
            routes=("routes", "sum"),
        )
    )
    # A sum over all-missing routes becomes 0 in pandas; restore missing evidence.
    player_history["routes"] = np.nan

    stats: dict[str, dict[str, float]] = {}

    def stat_row(pid: str) -> dict[str, float]:
        return stats.setdefault(
            pid,
            {
                "hist_pass_attempts": 0.0,
                "hist_completions": 0.0,
                "hist_passing_yards": 0.0,
                "hist_qb_rush_attempts": 0.0,
                "hist_qb_rush_yards": 0.0,
                "hist_carries": 0.0,
                "hist_rushing_yards": 0.0,
                "hist_targets": 0.0,
                "hist_receptions": 0.0,
                "hist_receiving_yards": 0.0,
                "hist_red_zone_targets": 0.0,
                "hist_end_zone_targets": 0.0,
                "hist_goal_line_carries": 0.0,
            },
        )

    passing_yards = _number(work, "passing_yards")
    passer_mask = (pass_attempt | sack) & _valid_id(passer_id)
    for idx in work.index[passer_mask]:
        pid = str(passer_id.loc[idx])
        if positions.get(pid) != "QB":
            continue
        row = stat_row(pid)
        row["hist_pass_attempts"] += float(pass_attempt.loc[idx])
        row["hist_completions"] += float(complete.loc[idx])
        row["hist_passing_yards"] += float(passing_yards.loc[idx])

    rushing_yards = _number(work, "rushing_yards")
    for idx in work.index[rusher_mask]:
        pid = str(rusher_id.loc[idx])
        pos = positions.get(pid)
        if pos not in SUPPORTED_POSITIONS:
            continue
        row = stat_row(pid)
        if pos == "QB":
            row["hist_qb_rush_attempts"] += 1.0
            row["hist_qb_rush_yards"] += float(rushing_yards.loc[idx])
        else:
            row["hist_carries"] += 1.0
            row["hist_rushing_yards"] += float(rushing_yards.loc[idx])
        row["hist_goal_line_carries"] += float(goal_line.loc[idx]) if pd.notna(goal_line.loc[idx]) else 0.0

    receiving_yards = _number(work, "receiving_yards")
    for idx in work.index[receiver_mask]:
        pid = str(receiver_id.loc[idx])
        if positions.get(pid) not in SUPPORTED_POSITIONS:
            continue
        row = stat_row(pid)
        row["hist_targets"] += 1.0
        row["hist_receptions"] += float(complete.loc[idx])
        row["hist_receiving_yards"] += float(receiving_yards.loc[idx])
        row["hist_red_zone_targets"] += float(red_zone.loc[idx]) if pd.notna(red_zone.loc[idx]) else 0.0
        row["hist_end_zone_targets"] += float(end_zone_target.loc[idx])

    efficiency_rows = [{"player_id": pid, **row} for pid, row in sorted(stats.items())]
    efficiency_history = pd.DataFrame(efficiency_rows)
    if efficiency_history.empty:
        raise PropsUpstreamError("No supported efficiency history was derived")

    historical_max = work[["season", "week"]].sort_values(["season", "week"]).tail(1).iloc[0]
    audit = {
        "history_policy": "STRICT_PRIOR_WEEK",
        "target_season": int(season),
        "target_week": int(week),
        "historical_max_period_used": {
            "season": int(historical_max["season"]),
            "week": int(historical_max["week"]),
        },
        "pbp_rows_used": int(len(work)),
        "team_game_rows": int(len(team_history)),
        "player_game_rows": int(len(player_history)),
        "efficiency_player_rows": int(len(efficiency_history)),
        "unresolved_supported_player_events_dropped": unresolved_player_events,
        "identity": identity_audit,
        "target_week_rows_used": 0,
    }
    return LaggedPropsHistory(
        team_history=team_history,
        player_history=player_history,
        efficiency_history=efficiency_history,
        audit=audit,
    )




def fit_pre2026_injury_availability_priors(
    injuries: pd.DataFrame,
    snap_counts: pd.DataFrame,
    *,
    trained_through_season: int = 2024,
) -> dict[str, Any]:
    """Fit Q/D offensive-participation priors from historical pregame designations.

    The outcome is whether the player recorded at least one offensive snap in that
    week. This is intentionally narrower than generic roster membership and matches
    the Props engine's question of whether offensive opportunity can be allocated.
    A fixed Beta(1,1) structural prior provides finite smoothing; no 2026 data or
    outcome-driven hyperparameter selection is used.
    """

    if int(trained_through_season) > 2025:
        raise PropsUpstreamError("availability priors may not be fit on completed 2026 outcomes")
    injury_required = {
        "season", "week", "team", "gsis_id", "position", "report_status",
    }
    missing = injury_required - set(injuries.columns)
    if missing:
        raise PropsUpstreamError(f"injury history missing fields: {sorted(missing)}")
    snap_required = {"season", "week", "team", "player_id", "offense_snaps"}
    missing = snap_required - set(snap_counts.columns)
    if missing:
        raise PropsUpstreamError(f"snap history missing fields: {sorted(missing)}")

    inj = injuries.copy()
    inj["season"] = pd.to_numeric(inj["season"], errors="coerce")
    inj["week"] = pd.to_numeric(inj["week"], errors="coerce")
    inj["team"] = inj["team"].map(normalize_team_code)
    inj["player_id"] = inj["gsis_id"].astype("string").fillna("").str.strip()
    inj["position"] = inj["position"].astype("string").fillna("").str.upper().str.strip()
    inj = inj[
        inj["season"].notna()
        & inj["week"].notna()
        & inj["season"].le(int(trained_through_season))
        & inj["position"].isin(SUPPORTED_POSITIONS)
        & _valid_id(inj["player_id"])
    ].copy()
    season_type_col = next(
        (column for column in ("season_type", "game_type") if column in inj.columns),
        None,
    )
    if season_type_col is not None:
        inj = inj[inj[season_type_col].astype(str).str.upper().eq("REG")].copy()

    status = inj["report_status"].astype("string").fillna("").str.lower().str.strip()
    inj["_state"] = np.select(
        [
            status.str.contains("questionable", regex=False),
            status.str.contains("doubtful", regex=False),
        ],
        ["QUESTIONABLE", "DOUBTFUL"],
        default="",
    )
    inj = inj[inj["_state"].ne("")].copy()
    if inj.empty:
        raise PropsUpstreamError("no historical QUESTIONABLE/DOUBTFUL injury rows available")

    if "date_modified" in inj.columns:
        modified = pd.to_datetime(inj["date_modified"], utc=True, errors="coerce")
        inj["_modified"] = modified
        inj = inj.sort_values(
            ["season", "week", "team", "player_id", "_modified"],
            na_position="first",
        ).drop_duplicates(
            ["season", "week", "team", "player_id"],
            keep="last",
        )
    else:
        inj = inj.drop_duplicates(
            ["season", "week", "team", "player_id"],
            keep="last",
        )

    snaps = snap_counts.copy()
    snaps["season"] = pd.to_numeric(snaps["season"], errors="coerce")
    snaps["week"] = pd.to_numeric(snaps["week"], errors="coerce")
    snaps["team"] = snaps["team"].map(normalize_team_code)
    snaps["player_id"] = snaps["player_id"].astype("string").fillna("").str.strip()
    snaps["offense_snaps"] = pd.to_numeric(snaps["offense_snaps"], errors="coerce")
    snaps = snaps[
        snaps["season"].notna()
        & snaps["week"].notna()
        & snaps["season"].le(int(trained_through_season))
        & _valid_id(snaps["player_id"])
    ].copy()
    game_type_col = next(
        (column for column in ("game_type", "season_type") if column in snaps.columns),
        None,
    )
    if game_type_col is not None:
        snaps = snaps[snaps[game_type_col].astype(str).str.upper().eq("REG")].copy()
    if snaps.empty:
        raise PropsUpstreamError("no historical snap-count rows available for availability fit")

    team_week_coverage = set(
        zip(
            snaps["season"].astype(int),
            snaps["week"].astype(int),
            snaps["team"].astype(str),
        )
    )
    injury_keys = list(
        zip(
            inj["season"].astype(int),
            inj["week"].astype(int),
            inj["team"].astype(str),
        )
    )
    covered = pd.Series(
        [key in team_week_coverage for key in injury_keys],
        index=inj.index,
        dtype=bool,
    )
    uncovered_rows = int((~covered).sum())
    inj = inj[covered].copy()
    if inj.empty:
        raise PropsUpstreamError("injury rows have no matching team-week snap coverage")

    snap_player = (
        snaps.groupby(
            ["season", "week", "team", "player_id"],
            as_index=False,
            sort=False,
        )["offense_snaps"]
        .max()
    )
    joined = inj.merge(
        snap_player,
        on=["season", "week", "team", "player_id"],
        how="left",
        validate="one_to_one",
    )
    joined["offense_snaps"] = pd.to_numeric(
        joined["offense_snaps"], errors="coerce"
    ).fillna(0.0)
    joined["_offensive_available"] = joined["offense_snaps"].gt(0)

    priors: dict[str, dict[str, float]] = {}
    state_audit: dict[str, Any] = {}
    for state in ("QUESTIONABLE", "DOUBTFUL"):
        rows = joined[joined["_state"].eq(state)]
        if rows.empty:
            continue
        successes = int(rows["_offensive_available"].sum())
        failures = int(len(rows) - successes)
        alpha = 1.0 + successes
        beta = 1.0 + failures
        priors[state] = {"alpha": alpha, "beta": beta}
        state_audit[state] = {
            "observations": int(len(rows)),
            "offensive_snap_positive": successes,
            "offensive_snap_zero": failures,
            "posterior_mean": alpha / (alpha + beta),
        }
    if not priors:
        raise PropsUpstreamError("no covered injury designations available for availability fit")

    return {
        "trained_through_season": int(trained_through_season),
        "availability_beta_priors": priors,
        "audit": {
            "method": "injury_report_status_to_offensive_snap_beta_1_1",
            "trained_through_season": int(trained_through_season),
            "uncovered_team_week_rows_dropped": uncovered_rows,
            "states": state_audit,
            "completed_2026_outcomes_used_for_prior_fit": 0,
        },
    }

def _clip_probability(value: float, *, label: str) -> float:
    if not math.isfinite(value):
        raise PropsUpstreamError(f"{label} is non-finite")
    return float(min(1.0 - 1e-4, max(1e-4, value)))


def _event_mean_sd(values: pd.Series, *, label: str) -> tuple[float, float]:
    clean = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if clean.empty:
        raise PropsUpstreamError(f"no pre-2026 event evidence for {label}")
    mean = float(clean.mean())
    sd = float(clean.std(ddof=0)) if len(clean) > 1 else 0.0
    return mean, max(sd, 0.25)


def fit_pre2026_efficiency_priors(
    pbp: pd.DataFrame,
    player_identity: pd.DataFrame,
    *,
    trained_through_season: int = 2025,
) -> dict[str, Any]:
    """Fit empirical efficiency priors using only seasons at/before the frozen horizon."""

    if int(trained_through_season) > 2025:
        raise PropsUpstreamError("efficiency priors may not be fit on completed 2026 outcomes")
    required = {
        "season",
        "pass_attempt",
        "rush_attempt",
        "complete_pass",
        "passing_yards",
        "rushing_yards",
        "receiving_yards",
        "yardline_100",
        "air_yards",
    }
    missing = required - set(pbp.columns)
    if missing:
        raise PropsUpstreamError(f"PBP missing prior-fit fields: {sorted(missing)}")

    positions, identity_audit = _position_lookup(player_identity)
    work = pbp.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work = work[work["season"].notna() & work["season"].le(int(trained_through_season))].copy()
    if "season_type" in work.columns:
        work = work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    if work.empty:
        raise PropsUpstreamError("no pre-2026 regular-season PBP is available for priors")

    pass_attempt = _number(work, "pass_attempt").eq(1)
    rush_attempt = _number(work, "rush_attempt").eq(1)
    complete = _number(work, "complete_pass").eq(1)
    passer_id = _text(work, "passer_player_id", "passer_id")
    rusher_id = _text(work, "rusher_player_id", "rusher_id")
    receiver_id = _text(work, "receiver_player_id", "receiver_id")
    passer_pos = passer_id.map(positions)
    rusher_pos = rusher_id.map(positions)
    receiver_pos = receiver_id.map(positions)
    target = pass_attempt & _valid_id(receiver_id) & receiver_pos.isin(SUPPORTED_POSITIONS)

    qb_pass = pass_attempt & passer_pos.eq("QB")
    qb_completions = qb_pass & complete
    qb_attempts_n = int(qb_pass.sum())
    if qb_attempts_n <= 0:
        raise PropsUpstreamError("no pre-2026 QB pass-attempt evidence for efficiency priors")
    completion_rate = _clip_probability(
        float(qb_completions.sum()) / qb_attempts_n,
        label="prior_completion_rate",
    )
    ypc_mean, ypc_sd = _event_mean_sd(
        pd.to_numeric(work.loc[qb_completions, "passing_yards"], errors="coerce"),
        label="yards_per_completion",
    )

    qb_rush = rush_attempt & rusher_pos.eq("QB")
    qb_rush_mean, qb_rush_sd = _event_mean_sd(
        pd.to_numeric(work.loc[qb_rush, "rushing_yards"], errors="coerce"),
        label="qb_rushing_yards_per_attempt",
    )

    supported_rush = rush_attempt & rusher_pos.isin(SUPPORTED_POSITIONS)
    non_qb_rush = supported_rush & ~rusher_pos.eq("QB")
    fallback_rush = non_qb_rush if bool(non_qb_rush.any()) else supported_rush
    fallback_rush_mean, fallback_rush_sd = _event_mean_sd(
        pd.to_numeric(work.loc[fallback_rush, "rushing_yards"], errors="coerce"),
        label="fallback_rushing_yards_per_attempt",
    )

    if int(target.sum()) <= 0:
        raise PropsUpstreamError("no pre-2026 receiving target evidence for efficiency priors")
    global_catch_rate = _clip_probability(
        float((target & complete).sum()) / float(target.sum()),
        label="global_prior_catch_rate",
    )
    global_rec = target & complete
    global_rec_mean, global_rec_sd = _event_mean_sd(
        pd.to_numeric(work.loc[global_rec, "receiving_yards"], errors="coerce"),
        label="fallback_receiving_yards_per_reception",
    )
    yardline = pd.to_numeric(work["yardline_100"], errors="coerce")
    air_yards = pd.to_numeric(work["air_yards"], errors="coerce")
    red_zone_target = target & yardline.le(20)
    end_zone_target = target & yardline.notna() & air_yards.notna() & air_yards.ge(yardline)
    global_rz_target_rate = _clip_probability(
        float(red_zone_target.sum()) / float(target.sum()),
        label="global_prior_red_zone_target_rate",
    )
    global_ez_target_rate = _clip_probability(
        float(end_zone_target.sum()) / float(target.sum()),
        label="global_prior_end_zone_target_rate",
    )
    goal_line = supported_rush & yardline.le(5)
    global_goal_line_rate = _clip_probability(
        float(goal_line.sum()) / float(supported_rush.sum()),
        label="global_prior_goal_line_carry_rate",
    )

    priors: dict[str, dict[str, float]] = {}
    for position in sorted(SUPPORTED_POSITIONS):
        pos_rush = supported_rush & rusher_pos.eq(position)
        if bool(pos_rush.any()):
            rush_mean, rush_sd = _event_mean_sd(
                pd.to_numeric(work.loc[pos_rush, "rushing_yards"], errors="coerce"),
                label=f"{position}_rushing_yards_per_attempt",
            )
            goal_rate = _clip_probability(
                float((pos_rush & yardline.le(5)).sum()) / float(pos_rush.sum()),
                label=f"{position}_prior_goal_line_carry_rate",
            )
        else:
            rush_mean, rush_sd = fallback_rush_mean, fallback_rush_sd
            goal_rate = global_goal_line_rate

        pos_targets = target & receiver_pos.eq(position)
        if bool(pos_targets.any()):
            catch_rate = _clip_probability(
                float((pos_targets & complete).sum()) / float(pos_targets.sum()),
                label=f"{position}_prior_catch_rate",
            )
            rz_rate = _clip_probability(
                float((pos_targets & yardline.le(20)).sum()) / float(pos_targets.sum()),
                label=f"{position}_prior_red_zone_target_rate",
            )
            ez_rate = _clip_probability(
                float(
                    (
                        pos_targets
                        & yardline.notna()
                        & air_yards.notna()
                        & air_yards.ge(yardline)
                    ).sum()
                )
                / float(pos_targets.sum()),
                label=f"{position}_prior_end_zone_target_rate",
            )
            pos_receptions = pos_targets & complete
            if bool(pos_receptions.any()):
                rec_mean, rec_sd = _event_mean_sd(
                    pd.to_numeric(work.loc[pos_receptions, "receiving_yards"], errors="coerce"),
                    label=f"{position}_receiving_yards_per_reception",
                )
            else:
                rec_mean, rec_sd = global_rec_mean, global_rec_sd
        else:
            catch_rate = global_catch_rate
            rz_rate = global_rz_target_rate
            ez_rate = global_ez_target_rate
            rec_mean, rec_sd = global_rec_mean, global_rec_sd

        priors[position] = {
            "prior_completion_rate": completion_rate,
            "prior_yards_per_completion_mean": ypc_mean,
            "prior_yards_per_completion_sd": ypc_sd,
            "prior_qb_rush_ypc_mean": qb_rush_mean,
            "prior_qb_rush_ypc_sd": qb_rush_sd,
            "prior_rush_ypc_mean": rush_mean,
            "prior_rush_ypc_sd": rush_sd,
            "prior_catch_rate": catch_rate,
            "prior_receiving_ypr_mean": rec_mean,
            "prior_receiving_ypr_sd": rec_sd,
            "prior_red_zone_target_rate": rz_rate,
            "prior_end_zone_target_rate": ez_rate,
            "prior_goal_line_carry_rate": goal_rate,
        }

    return {
        "trained_through_season": int(trained_through_season),
        "efficiency_position_priors": priors,
        "residual_efficiency": {
            "catch_rate": global_catch_rate,
            "receiving_yards_per_reception": global_rec_mean,
            "rushing_yards_per_carry": fallback_rush_mean,
        },
        "audit": {
            "method": "empirical_pre2026_regular_season_pbp",
            "trained_through_season": int(trained_through_season),
            "pbp_rows": int(len(work)),
            "qb_pass_attempts": qb_attempts_n,
            "receiving_targets": int(target.sum()),
            "supported_rush_attempts": int(supported_rush.sum()),
            "completed_2026_outcomes_used_for_prior_fit": 0,
            "identity": identity_audit,
        },
    }


def build_empirical_scoring_context(
    pbp: pd.DataFrame,
    *,
    teams: Sequence[str],
    season: int,
    week: int,
    trained_through_season: int = 2025,
) -> dict[str, Any]:
    """Build current team scoring-volume state with priors frozen through 2025."""

    if int(trained_through_season) > 2025:
        raise PropsUpstreamError("scoring priors may not be fit on completed 2026 outcomes")
    for field in ("drive", "yardline_100", "pass_touchdown", "rush_touchdown"):
        if field not in pbp.columns:
            raise PropsUpstreamError(
                f"PBP missing scoring-context field {field}; provide explicit scoring context"
            )
    work = _safe_history(pbp, season=season, week=week)
    if "season_type" in work.columns:
        work = work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    if work.empty:
        raise PropsUpstreamError("no strictly lagged regular-season PBP for scoring context")

    work["_drive"] = pd.to_numeric(work["drive"], errors="coerce")
    yardline = pd.to_numeric(work["yardline_100"], errors="coerce")
    pass_td = _number(work, "pass_touchdown").eq(1)
    rush_td = _number(work, "rush_touchdown").eq(1)
    work["_rz_play"] = yardline.le(20)
    work["_pass_td"] = pass_td
    work["_rush_td"] = rush_td
    work["_off_td"] = pass_td | rush_td
    work["_non_rz_pass_td"] = pass_td & yardline.gt(20)
    work["_non_rz_rush_td"] = rush_td & yardline.gt(20)

    drive_rows = work[work["_drive"].notna()].copy()
    if drive_rows.empty:
        raise PropsUpstreamError("no valid drive identifiers in lagged PBP")
    drives = (
        drive_rows.groupby(
            ["game_id", "season", "week", "team", "_drive"],
            as_index=False,
            sort=False,
        )
        .agg(
            reached_red_zone=("_rz_play", "max"),
            offensive_td=("_off_td", "max"),
            passing_td=("_pass_td", "max"),
            rushing_td=("_rush_td", "max"),
        )
    )
    team_games = (
        drives.groupby(["game_id", "season", "week", "team"], as_index=False, sort=False)
        .agg(
            drives=("_drive", "nunique"),
            red_zone_trips=("reached_red_zone", "sum"),
        )
    )
    non_rz = (
        work.groupby(["game_id", "season", "week", "team"], as_index=False, sort=False)
        .agg(
            non_red_zone_pass_tds=("_non_rz_pass_td", "sum"),
            non_red_zone_rush_tds=("_non_rz_rush_td", "sum"),
        )
    )
    team_games = team_games.merge(
        non_rz,
        on=["game_id", "season", "week", "team"],
        how="left",
        validate="one_to_one",
    )

    pre = work[work["season"].le(int(trained_through_season))].copy()
    if pre.empty:
        raise PropsUpstreamError("no pre-2026 PBP available for scoring priors")
    pre_drives = drives[drives["season"].le(int(trained_through_season))].copy()
    pre_rz = pre_drives[pre_drives["reached_red_zone"].astype(bool)]
    if pre_rz.empty:
        raise PropsUpstreamError("no pre-2026 red-zone drive evidence")
    red_zone_td_rate = _clip_probability(
        float(pre_rz["offensive_td"].sum()) / float(len(pre_rz)),
        label="prior_red_zone_td_rate",
    )
    red_zone_scoring_drives = pre_rz[
        pre_rz["passing_td"].astype(bool) | pre_rz["rushing_td"].astype(bool)
    ]
    red_zone_td_events = int(
        red_zone_scoring_drives["passing_td"].sum()
        + red_zone_scoring_drives["rushing_td"].sum()
    )
    if red_zone_td_events <= 0:
        raise PropsUpstreamError("no pre-2026 red-zone passing/rushing TD evidence")
    pass_td_fraction = _clip_probability(
        float(red_zone_scoring_drives["passing_td"].sum())
        / float(red_zone_td_events),
        label="prior_pass_td_fraction",
    )

    normalized_teams = [normalize_team_code(team) for team in teams]
    league_means = {
        column: float(pd.to_numeric(team_games[column], errors="coerce").mean())
        for column in (
            "drives",
            "red_zone_trips",
            "non_red_zone_pass_tds",
            "non_red_zone_rush_tds",
        )
    }
    contexts: dict[str, dict[str, float]] = {}
    team_audit: dict[str, Any] = {}
    for team in normalized_teams:
        rows = team_games[team_games["team"].map(normalize_team_code).eq(team)].copy()
        source = "team_strictly_lagged_history"
        if rows.empty:
            source = "league_strictly_lagged_fallback"
        def avg(column: str) -> float:
            if rows.empty:
                return league_means[column]
            value = float(pd.to_numeric(rows[column], errors="coerce").mean())
            return league_means[column] if not math.isfinite(value) else value

        expected_drives = max(avg("drives"), 0.0)
        expected_rz = max(min(avg("red_zone_trips"), expected_drives), 0.0)
        contexts[team] = {
            "expected_drives": expected_drives,
            "expected_red_zone_trips": expected_rz,
            "prior_red_zone_td_rate": red_zone_td_rate,
            "prior_pass_td_fraction": pass_td_fraction,
            "expected_non_red_zone_pass_tds": max(avg("non_red_zone_pass_tds"), 0.0),
            "expected_non_red_zone_rush_tds": max(avg("non_red_zone_rush_tds"), 0.0),
        }
        team_audit[team] = {
            "state_source": source,
            "historical_team_games": int(len(rows)),
        }

    return {
        "scoring_context_by_team": contexts,
        "audit": {
            "method": "strictly_lagged_team_means_with_pre2026_league_scoring_priors",
            "trained_through_season": int(trained_through_season),
            "red_zone_td_prior_source": "league_pre2026",
            "pass_td_fraction_prior_source": "league_pre2026",
            "completed_2026_outcomes_used_for_prior_fit": 0,
            "prior_2026_games_allowed_for_chronological_team_state": True,
            "teams": team_audit,
        },
    }


def residual_efficiency_by_team_from_empirical_priors(
    teams: Sequence[str],
    fitted_priors: Mapping[str, Any],
) -> dict[str, dict[str, float]]:
    residual = fitted_priors.get("residual_efficiency")
    if not isinstance(residual, Mapping):
        raise PropsUpstreamError("fitted empirical priors missing residual_efficiency")
    required = {
        "catch_rate",
        "receiving_yards_per_reception",
        "rushing_yards_per_carry",
    }
    missing = required - set(residual)
    if missing:
        raise PropsUpstreamError(f"residual empirical priors missing: {sorted(missing)}")
    values = {key: float(residual[key]) for key in required}
    if not all(math.isfinite(value) for value in values.values()):
        raise PropsUpstreamError("residual empirical priors must be finite")
    return {
        normalize_team_code(team): dict(values)
        for team in teams
    }

def build_efficiency_baselines(
    *,
    projection_players: Sequence[Mapping[str, Any]],
    efficiency_history: pd.DataFrame,
    position_priors: Mapping[str, Mapping[str, Any]],
) -> pd.DataFrame:
    """Join observable historical sufficient statistics to explicit position priors."""

    if "player_id" not in efficiency_history.columns:
        raise PropsUpstreamError("efficiency history requires player_id")
    history = {
        str(row["player_id"]): row.to_dict()
        for _, row in efficiency_history.iterrows()
    }
    rows: list[dict[str, Any]] = []
    for raw in projection_players:
        pid = str(raw.get("player_id") or "").strip()
        position = str(raw.get("position") or "").upper().strip()
        if not pid or position not in SUPPORTED_POSITIONS:
            raise PropsUpstreamError("projection player has invalid stable identity/position")
        prior = position_priors.get(position)
        if not isinstance(prior, Mapping):
            raise PropsUpstreamError(f"missing explicit efficiency priors for {position}")
        missing_prior = EFFICIENCY_PRIOR_FIELDS - set(prior)
        if missing_prior:
            raise PropsUpstreamError(
                f"efficiency priors for {position} missing: {sorted(missing_prior)}"
            )
        numeric_prior: dict[str, float] = {}
        for field in EFFICIENCY_PRIOR_FIELDS:
            try:
                value = float(prior[field])
            except (TypeError, ValueError) as exc:
                raise PropsUpstreamError(f"invalid efficiency prior {position}/{field}") from exc
            if not math.isfinite(value):
                raise PropsUpstreamError(f"non-finite efficiency prior {position}/{field}")
            numeric_prior[field] = value

        hist = history.get(pid, {})
        row = {"player_id": pid}
        for field in (
            "hist_pass_attempts",
            "hist_completions",
            "hist_passing_yards",
            "hist_qb_rush_attempts",
            "hist_qb_rush_yards",
            "hist_carries",
            "hist_rushing_yards",
            "hist_targets",
            "hist_receptions",
            "hist_receiving_yards",
            "hist_red_zone_targets",
            "hist_end_zone_targets",
            "hist_goal_line_carries",
        ):
            row[field] = float(hist.get(field, 0.0) or 0.0)
        row.update(numeric_prior)
        rows.append(row)
    return pd.DataFrame(rows)


def build_game_upstream_package(
    *,
    player_state: pd.DataFrame,
    history: LaggedPropsHistory,
    game_id: str,
    season: int,
    week: int,
    forecast_timestamp: object,
    route_prior_means: Mapping[str, float],
    availability_priors: Mapping[str, Any],
    position_efficiency_priors: Mapping[str, Mapping[str, Any]],
    scoring_context_by_team: Mapping[str, Mapping[str, Any]],
    residual_efficiency_by_team: Mapping[str, Mapping[str, Any]],
    source_status: str,
    prior_model_trained_through_season: int,
    primary_qb_by_team: Mapping[str, Mapping[str, str]] | None = None,
) -> PropsGameUpstreamPackage:
    """Build validated opportunity + efficiency handoffs for one canonical game."""

    if source_status not in SOURCE_STATES:
        raise PropsUpstreamError(f"invalid source_status: {source_status}")
    if int(prior_model_trained_through_season) > 2025:
        raise PropsUpstreamError("completed 2026 outcomes cannot train efficiency priors")

    state = player_state[player_state["game_id"].astype(str).eq(str(game_id))].copy()
    if state.empty:
        raise PropsUpstreamError(f"player_state has no rows for game {game_id}")
    teams = sorted(set(state["team"].map(normalize_team_code)))
    if len(teams) != 2:
        raise PropsUpstreamError("game player_state must resolve to exactly two teams")

    kickoff_values = pd.to_datetime(state["kickoff_timestamp"], utc=True, errors="coerce").dropna().unique()
    if len(kickoff_values) != 1:
        raise PropsUpstreamError("game player_state requires one known kickoff timestamp")
    kickoff = pd.Timestamp(kickoff_values[0]).tz_convert("UTC")
    forecast = pd.Timestamp(forecast_timestamp)
    if forecast.tzinfo is None:
        raise PropsUpstreamError("forecast_timestamp must be timezone-aware")
    forecast = forecast.tz_convert("UTC")
    if forecast >= kickoff:
        raise PropsUpstreamError("forecast_timestamp must be pregame")

    projections: list[dict[str, Any]] = []
    efficiency_inputs: list[pd.DataFrame] = []
    team_inputs: list[pd.DataFrame] = []
    team_audit: dict[str, Any] = {}
    qb_overrides = primary_qb_by_team or {}

    for team in teams:
        team_rows = state[state["team"].map(normalize_team_code).eq(team)]
        opponents = sorted(set(team_rows["opponent"].map(normalize_team_code)))
        if len(opponents) != 1:
            raise PropsUpstreamError(f"team {team} has ambiguous opponent")
        opponent = opponents[0]
        context = ForecastContext(
            game_id=str(game_id),
            season=int(season),
            week=int(week),
            team=team,
            opponent=opponent,
            forecast_timestamp=forecast.isoformat(),
            data_horizon=forecast.isoformat(),
        )
        override = qb_overrides.get(team)
        kwargs: dict[str, Any] = {}
        if override is not None:
            player_id = str(override.get("player_id") or "").strip()
            provenance = str(override.get("provenance") or "").strip()
            if not player_id or not provenance:
                raise PropsUpstreamError(
                    f"primary QB override for {team} requires player_id and provenance"
                )
            selected = team_rows[
                team_rows["player_id"].astype(str).eq(player_id)
                & team_rows["position"].astype(str).str.upper().eq("QB")
            ]
            if len(selected) != 1:
                raise PropsUpstreamError(
                    f"primary QB override for {team} does not identify exactly one canonical QB"
                )
            active_state = str(
                selected.iloc[0].get("expected_active_state") or "UNKNOWN"
            ).upper().strip()
            if active_state == "OUT":
                raise PropsUpstreamError(
                    f"primary QB override for {team} selects a player explicitly OUT: {player_id}"
                )
            kwargs.update(
                primary_qb_player_id=player_id,
                primary_qb_provenance=provenance,
            )

        projection = build_simulation_ready_opportunity_projection(
            history.team_history,
            history.player_history,
            state,
            context,
            availability_priors=availability_priors,
            route_prior_means=route_prior_means,
            **kwargs,
        )
        projection_dict = projection.to_dict()
        projections.append(projection_dict)

        baselines = build_efficiency_baselines(
            projection_players=projection.players,
            efficiency_history=history.efficiency_history,
            position_priors=position_efficiency_priors,
        )
        efficiency_inputs.append(
            build_efficiency_player_inputs(
                projection_dict,
                baselines,
                kickoff_timestamp=kickoff,
                source_status=source_status,
                prior_model_trained_through_season=prior_model_trained_through_season,
            )
        )

        scoring = scoring_context_by_team.get(team)
        if not isinstance(scoring, Mapping):
            raise PropsUpstreamError(f"missing explicit scoring context for {team}")
        missing_scoring = SCORING_CONTEXT_FIELDS - set(scoring)
        if missing_scoring:
            raise PropsUpstreamError(
                f"scoring context for {team} missing: {sorted(missing_scoring)}"
            )
        team_inputs.append(
            build_efficiency_team_input(
                projection_dict,
                scoring,
                kickoff_timestamp=kickoff,
                source_status=source_status,
                prior_model_trained_through_season=prior_model_trained_through_season,
            )
        )
        team_audit[team] = {
            "opportunity_data_quality": projection.audit.get("data_quality"),
            "opportunity_pricing_ready": projection.audit.get("pricing_ready"),
            "unseen_current_player_ids": projection.audit.get("unseen_current_player_ids", []),
        }

    residual = {
        normalize_team_code(team): dict(value)
        for team, value in residual_efficiency_by_team.items()
    }
    if not set(teams).issubset(residual):
        raise PropsUpstreamError("residual efficiency requires both game teams")

    build = build_efficiency_td_parameters(
        pd.concat(efficiency_inputs, ignore_index=True),
        pd.concat(team_inputs, ignore_index=True),
    )
    if not bool(build.diagnostics["reconciled"].all()):
        raise PropsUpstreamError("efficiency/TD output failed reconciliation")

    return PropsGameUpstreamPackage(
        game_id=str(game_id),
        opportunity_projections=tuple(projections),
        efficiency_player_parameters=tuple(build.player_parameters.to_dict("records")),
        team_td_parameters=tuple(build.team_td_parameters.to_dict("records")),
        residual_efficiency_by_team={team: residual[team] for team in teams},
        audit={
            "research_only": True,
            "winner_probability_modified": False,
            "history": history.audit,
            "teams": team_audit,
            "efficiency_td": build.audit,
            "source_status": source_status,
            "prior_model_trained_through_season": int(prior_model_trained_through_season),
        },
    )
