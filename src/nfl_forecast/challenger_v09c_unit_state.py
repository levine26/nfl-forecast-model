from __future__ import annotations

"""Leakage-safe snap-continuity unit state for LevLine v0.9C research.

For game G, every feature here is derived only from completed games G-1 and G-2 for
the same team and season. Current-game snaps are post-kickoff data and never enter G's
feature row. PFR snap IDs are bridged through nflverse's exact PFR->GSIS crosswalk;
unresolved/ambiguous mappings are excluded from overlap and quantified as unknown snap
weight rather than name-matched.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .player_state_research import normalize_team_code

OL_POSITIONS = {"C", "G", "LG", "RG", "T", "LT", "RT", "OL"}
SKILL_POSITIONS = {"WR", "TE", "RB", "FB", "HB"}
FRONT7_POSITIONS = {"DE", "DT", "DL", "NT", "LB", "ILB", "OLB", "MLB", "EDGE"}
SECONDARY_POSITIONS = {"CB", "DB", "S", "FS", "SS"}
UNIT_NAMES = ("offense", "defense", "ol", "skill", "front7", "secondary")
STATE_FEATURES = (
    "offense_continuity",
    "defense_continuity",
    "ol_continuity",
    "skill_continuity",
    "front7_continuity",
    "secondary_continuity",
    "offense_concentration",
    "defense_concentration",
    "offense_unmapped_weight",
    "defense_unmapped_weight",
)


@dataclass(frozen=True)
class UnitStateBuild:
    snap_rows: pd.DataFrame
    team_game_unit_state: pd.DataFrame
    team_pregame_state: pd.DataFrame
    audit: dict[str, Any]


def _text(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype="string")
    return frame[column].astype("string").fillna("").str.strip()


def _number(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(0.0, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(0.0).clip(lower=0.0)


def _valid_id(series: pd.Series) -> pd.Series:
    values = series.astype("string").fillna("").str.strip()
    return values.ne("") & values.ne("<NA>") & values.str.lower().ne("nan")


def attach_stable_snap_ids(
    snap_counts: pd.DataFrame,
    players: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Attach unique GSIS IDs to PFR snap rows and audit the fail-closed crosswalk."""
    required_snap = {
        "game_id",
        "season",
        "week",
        "team",
        "pfr_player_id",
        "position",
        "offense_pct",
        "defense_pct",
    }
    missing_snap = required_snap - set(snap_counts.columns)
    if missing_snap:
        raise ValueError(f"snap counts missing required fields: {sorted(missing_snap)}")
    required_players = {"pfr_id", "gsis_id"}
    missing_players = required_players - set(players.columns)
    if missing_players:
        raise ValueError(f"player crosswalk missing required fields: {sorted(missing_players)}")

    crosswalk = players[["pfr_id", "gsis_id"]].copy()
    crosswalk["pfr_id"] = _text(crosswalk, "pfr_id")
    crosswalk["gsis_id"] = _text(crosswalk, "gsis_id")
    crosswalk = crosswalk[_valid_id(crosswalk.pfr_id) & _valid_id(crosswalk.gsis_id)].drop_duplicates()
    variants = crosswalk.groupby("pfr_id", sort=False).gsis_id.nunique()
    ambiguous_ids = set(variants[variants.gt(1)].index.astype(str))
    crosswalk = crosswalk[~crosswalk.pfr_id.isin(ambiguous_ids)].drop_duplicates("pfr_id", keep="first")

    work = snap_counts.copy()
    work["pfr_player_id"] = _text(work, "pfr_player_id")
    work["position"] = _text(work, "position").str.upper()
    work["team"] = _text(work, "team").map(normalize_team_code)
    work["season"] = pd.to_numeric(work.season, errors="coerce")
    work["week"] = pd.to_numeric(work.week, errors="coerce")
    work = work[
        work.season.notna()
        & work.week.notna()
        & work.game_id.notna()
        & work.team.ne("")
    ].copy()
    work["season"] = work.season.astype(int)
    work["week"] = work.week.astype(int)
    work["offense_weight"] = _number(work, "offense_pct")
    work["defense_weight"] = _number(work, "defense_pct")
    work = work.merge(
        crosswalk,
        left_on="pfr_player_id",
        right_on="pfr_id",
        how="left",
        validate="many_to_one",
    )
    work["stable_player_id"] = _text(work, "gsis_id")
    work["stable_id_known"] = _valid_id(work.stable_player_id)

    total_offense = float(work.offense_weight.sum())
    total_defense = float(work.defense_weight.sum())
    missing_offense = float(work.loc[~work.stable_id_known, "offense_weight"].sum())
    missing_defense = float(work.loc[~work.stable_id_known, "defense_weight"].sum())
    audit = {
        "snap_rows": int(len(work)),
        "crosswalk_unique_pfr_ids": int(len(crosswalk)),
        "crosswalk_ambiguous_pfr_ids": int(len(ambiguous_ids)),
        "stable_id_known_rows": int(work.stable_id_known.sum()),
        "stable_id_missing_rows": int((~work.stable_id_known).sum()),
        "stable_id_missing_row_rate": float((~work.stable_id_known).mean()) if len(work) else None,
        "offense_unmapped_weight_rate": missing_offense / total_offense if total_offense > 0 else None,
        "defense_unmapped_weight_rate": missing_defense / total_defense if total_defense > 0 else None,
        "identity_policy": "exact PFR->GSIS only; ambiguous/unmapped rows excluded from overlap and retained as unknown weight",
    }
    return work, audit


def _unit_mask(frame: pd.DataFrame, unit: str) -> pd.Series:
    if unit == "offense":
        return frame.offense_weight.gt(0)
    if unit == "defense":
        return frame.defense_weight.gt(0)
    if unit == "ol":
        return frame.offense_weight.gt(0) & frame.position.isin(OL_POSITIONS)
    if unit == "skill":
        return frame.offense_weight.gt(0) & frame.position.isin(SKILL_POSITIONS)
    if unit == "front7":
        return frame.defense_weight.gt(0) & frame.position.isin(FRONT7_POSITIONS)
    if unit == "secondary":
        return frame.defense_weight.gt(0) & frame.position.isin(SECONDARY_POSITIONS)
    raise ValueError(f"unknown unit: {unit}")


def _weight_column(unit: str) -> str:
    return "offense_weight" if unit in {"offense", "ol", "skill"} else "defense_weight"


def _distribution(rows: pd.DataFrame, unit: str) -> tuple[dict[str, float], float, float]:
    """Return normalized mapped distribution, HHI concentration, and unknown weight."""
    piece = rows.loc[_unit_mask(rows, unit)].copy()
    weight_col = _weight_column(unit)
    total = float(piece[weight_col].sum())
    if piece.empty or total <= 0:
        return {}, np.nan, np.nan

    # Concentration uses source-stable PFR identities so crosswalk coverage cannot alter
    # the rotation statistic. Cross-game continuity requires the validated GSIS bridge.
    pfr_piece = piece[_valid_id(piece.pfr_player_id)]
    pfr = pfr_piece.groupby("pfr_player_id", sort=False)[weight_col].sum()
    pfr_total = float(pfr.sum())
    pfr_dist = pfr / pfr_total if pfr_total > 0 else pfr
    concentration = float((pfr_dist**2).sum()) if len(pfr_dist) else np.nan

    mapped_piece = piece[piece.stable_id_known]
    mapped = mapped_piece.groupby("stable_player_id", sort=False)[weight_col].sum()
    mapped_total = float(mapped.sum())
    mapped_dist = (
        {str(player_id): float(weight / mapped_total) for player_id, weight in mapped.items()}
        if mapped_total > 0
        else {}
    )
    unmapped_share = float(piece.loc[~piece.stable_id_known, weight_col].sum() / total)
    return mapped_dist, concentration, unmapped_share


def build_team_game_unit_state(snap_rows: pd.DataFrame) -> pd.DataFrame:
    """Compress each completed team-game snap file into stable unit distributions."""
    records: list[dict[str, Any]] = []
    keys = ["game_id", "season", "week", "team"]
    for key, rows in snap_rows.groupby(keys, sort=False):
        game_id, season, week, team = key
        record: dict[str, Any] = {
            "game_id": str(game_id),
            "season": int(season),
            "week": int(week),
            "team": str(team),
        }
        for unit in UNIT_NAMES:
            distribution, concentration, unmapped_share = _distribution(rows, unit)
            record[f"{unit}_distribution"] = distribution
            record[f"{unit}_concentration"] = concentration
            record[f"{unit}_unmapped_weight"] = unmapped_share
        records.append(record)
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records).sort_values(["team", "season", "week", "game_id"]).reset_index(drop=True)


def _overlap(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return np.nan
    players = set(left) | set(right)
    return float(
        sum(min(float(left.get(player, 0.0)), float(right.get(player, 0.0))) for player in players)
    )


def build_team_pregame_unit_state(team_game_state: pd.DataFrame) -> pd.DataFrame:
    """For G, compare only completed G-1 and G-2 team snap distributions."""
    if team_game_state.empty:
        return pd.DataFrame()
    records: list[dict[str, Any]] = []
    for (team, season), group in team_game_state.groupby(["team", "season"], sort=False):
        ordered = group.sort_values(["week", "game_id"]).reset_index(drop=True)
        for index, current in ordered.iterrows():
            record: dict[str, Any] = {
                "game_id": str(current.game_id),
                "season": int(season),
                "week": int(current.week),
                "team": str(team),
                "unit_state_missing": bool(index < 2),
            }
            if index < 2:
                for feature in STATE_FEATURES:
                    record[feature] = np.nan
                records.append(record)
                continue

            prior = ordered.iloc[index - 1]
            prior2 = ordered.iloc[index - 2]
            for unit in UNIT_NAMES:
                record[f"{unit}_continuity"] = _overlap(
                    prior[f"{unit}_distribution"],
                    prior2[f"{unit}_distribution"],
                )
            record["offense_concentration"] = (
                float(prior.offense_concentration) if pd.notna(prior.offense_concentration) else np.nan
            )
            record["defense_concentration"] = (
                float(prior.defense_concentration) if pd.notna(prior.defense_concentration) else np.nan
            )
            record["offense_unmapped_weight"] = (
                float(prior.offense_unmapped_weight) if pd.notna(prior.offense_unmapped_weight) else np.nan
            )
            record["defense_unmapped_weight"] = (
                float(prior.defense_unmapped_weight) if pd.notna(prior.defense_unmapped_weight) else np.nan
            )
            records.append(record)
    return pd.DataFrame(records).sort_values(["season", "week", "game_id", "team"]).reset_index(drop=True)


def build_game_unit_features(
    schedules: pd.DataFrame,
    team_pregame_state: pd.DataFrame,
) -> pd.DataFrame:
    """Join home/away unit state and emit the fixed v0.9C 11-feature vector."""
    required = {"game_id", "season", "week", "home_team", "away_team"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"schedules missing unit-state keys: {sorted(missing)}")
    games = schedules.copy()
    games["home_team"] = games.home_team.map(normalize_team_code)
    games["away_team"] = games.away_team.map(normalize_team_code)
    state = team_pregame_state.copy()
    state["team"] = state.team.map(normalize_team_code)

    raw = [*STATE_FEATURES, "unit_state_missing"]
    for side in ("home", "away"):
        team_col = f"{side}_team"
        piece = state[["game_id", "team", *raw]].copy()
        piece = piece.rename(
            columns={"team": team_col, **{column: f"{side}_{column}" for column in raw}}
        )
        games = games.merge(piece, on=["game_id", team_col], how="left", validate="one_to_one")

    for feature in STATE_FEATURES:
        games[f"v09c_diff_{feature}"] = (
            pd.to_numeric(games[f"home_{feature}"], errors="coerce")
            - pd.to_numeric(games[f"away_{feature}"], errors="coerce")
        )
    home_missing = games["home_unit_state_missing"].fillna(True).astype(bool)
    away_missing = games["away_unit_state_missing"].fillna(True).astype(bool)
    games["v09c_unit_state_missing_count"] = home_missing.astype(int) + away_missing.astype(int)
    return games


def v09c_feature_columns(frame: pd.DataFrame) -> list[str]:
    columns = sorted(column for column in frame.columns if column.startswith("v09c_"))
    if len(columns) != 11:
        raise RuntimeError(f"Expected exactly 11 predeclared v0.9C features; found {len(columns)}")
    return columns


def build_unit_state(snap_counts: pd.DataFrame, players: pd.DataFrame) -> UnitStateBuild:
    snap_rows, audit = attach_stable_snap_ids(snap_counts, players)
    game_state = build_team_game_unit_state(snap_rows)
    pregame = build_team_pregame_unit_state(game_state)
    audit = {
        **audit,
        "team_game_rows": int(len(game_state)),
        "team_pregame_rows": int(len(pregame)),
        "pregame_rows_with_two_prior_games": int((~pregame.unit_state_missing).sum()) if len(pregame) else 0,
        "current_game_snap_rows_used_for_current_game_features": 0,
        "2026_outcomes_used": 0,
    }
    return UnitStateBuild(
        snap_rows=snap_rows,
        team_game_unit_state=game_state,
        team_pregame_state=pregame,
        audit=audit,
    )
