from __future__ import annotations

"""Research-only point-in-time personnel state from nflverse 2025+ depth charts.

Depth-chart movement is personnel information, not an injury label.  Every target game
uses only the most recent team snapshot whose source timestamp is at or before T-120.
No outcomes, postgame snaps, or later depth-chart revisions are inputs.
"""

from dataclasses import dataclass
from datetime import timezone
from zoneinfo import ZoneInfo
from typing import Any

import numpy as np
import pandas as pd

DECISION_HORIZON_MINUTES = 120
SUPPORTED_SEASONS = (2025,)
TEAM_NORMALIZATION = {"JAC": "JAX"}
OL_ABBREVIATIONS = {"C", "G", "LG", "RG", "T", "LT", "RT", "OL"}
REQUIRED_DEPTH_FIELDS = {
    "dt",
    "team",
    "gsis_id",
    "pos_grp",
    "pos_abb",
    "pos_slot",
    "pos_rank",
}
REQUIRED_SCHEDULE_FIELDS = {"game_id", "season", "week", "home_team", "away_team"}


@dataclass(frozen=True)
class DepthStateBuild:
    team_game_state: pd.DataFrame
    game_features: pd.DataFrame
    audit: dict[str, Any]


def normalize_team(value: Any) -> str:
    code = str(value or "").strip().upper()
    return TEAM_NORMALIZATION.get(code, code)


def _valid_id(series: pd.Series) -> pd.Series:
    value = series.astype("string").fillna("").str.strip()
    return value.ne("") & ~value.str.lower().isin({"nan", "<na>", "none"})


def _kickoff_utc(schedules: pd.DataFrame) -> pd.Series:
    if "kickoff_utc" in schedules.columns:
        parsed = pd.to_datetime(schedules["kickoff_utc"], errors="coerce", utc=True)
        if parsed.isna().any():
            raise ValueError("schedule kickoff_utc contains unparseable values")
        return parsed
    required = {"gameday", "gametime"}
    missing = required - set(schedules.columns)
    if missing:
        raise ValueError(f"schedule requires kickoff_utc or {sorted(required)}; missing {sorted(missing)}")
    text = schedules["gameday"].astype(str).str.strip() + " " + schedules["gametime"].astype(str).str.strip()
    local = pd.to_datetime(text, errors="coerce")
    if local.isna().any():
        raise ValueError("schedule gameday/gametime contains unparseable values")
    eastern = ZoneInfo("America/New_York")
    return local.map(lambda value: value.replace(tzinfo=eastern).astimezone(timezone.utc))


def _prepare_depth(depth: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_DEPTH_FIELDS - set(depth.columns)
    if missing:
        raise ValueError(f"depth charts missing fields: {sorted(missing)}")
    frame = depth.copy()
    frame["snapshot_utc"] = pd.to_datetime(frame["dt"], errors="coerce", utc=True)
    if frame["snapshot_utc"].isna().any():
        raise ValueError("depth-chart timestamps must all parse as timezone-aware instants")
    frame["team"] = frame["team"].map(normalize_team)
    frame["stable_id"] = frame["gsis_id"].astype("string").fillna("").str.strip()
    frame["pos_rank_num"] = pd.to_numeric(frame["pos_rank"], errors="coerce")
    frame["pos_slot_num"] = pd.to_numeric(frame["pos_slot"], errors="coerce")
    frame["pos_abb_norm"] = frame["pos_abb"].astype("string").fillna("").str.upper().str.strip()
    frame["pos_grp_norm"] = frame["pos_grp"].astype("string").fillna("").str.lower().str.strip()
    return frame


def _prepare_schedule(schedules: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_SCHEDULE_FIELDS - set(schedules.columns)
    if missing:
        raise ValueError(f"schedules missing fields: {sorted(missing)}")
    games = schedules.copy()
    games["season"] = pd.to_numeric(games["season"], errors="coerce")
    games["week"] = pd.to_numeric(games["week"], errors="coerce")
    if games[["season", "week"]].isna().any().any():
        raise ValueError("schedule season/week contains missing values")
    games["season"] = games["season"].astype(int)
    games["week"] = games["week"].astype(int)
    unexpected = sorted(set(games["season"]) - set(SUPPORTED_SEASONS))
    if unexpected:
        raise ValueError(f"depth-state v1 is frozen to seasons {SUPPORTED_SEASONS}; got {unexpected}")
    games["home_team"] = games["home_team"].map(normalize_team)
    games["away_team"] = games["away_team"].map(normalize_team)
    games["kickoff_utc"] = _kickoff_utc(games)
    games["decision_utc"] = games["kickoff_utc"] - pd.to_timedelta(DECISION_HORIZON_MINUTES, unit="m")
    if games["game_id"].astype(str).duplicated().any():
        raise ValueError("schedule game_id must be unique")
    return games


def _rank1_ids(snapshot: pd.DataFrame, *, group: str | None = None, ol: bool = False) -> set[str]:
    rows = snapshot[snapshot["pos_rank_num"].eq(1)].copy()
    if group == "offense":
        rows = rows[rows["pos_grp_norm"].str.startswith("off")]
    elif group == "defense":
        rows = rows[rows["pos_grp_norm"].str.startswith("def")]
    if ol:
        rows = rows[rows["pos_abb_norm"].isin(OL_ABBREVIATIONS)]
    rows = rows[_valid_id(rows["stable_id"])]
    return set(rows["stable_id"].astype(str))


def _continuity(current: set[str], previous: set[str] | None) -> float | None:
    if previous is None or not previous:
        return None
    return float(len(current & previous) / len(previous))


def _new_count(current: set[str], previous: set[str] | None) -> float | None:
    if previous is None:
        return None
    return float(len(current - previous))


def build_team_game_state(depth: pd.DataFrame, schedules: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = _prepare_depth(depth)
    games = _prepare_schedule(schedules)

    team_games = pd.concat(
        [
            games[["game_id", "season", "week", "kickoff_utc", "decision_utc", "home_team"]].rename(columns={"home_team": "team"}),
            games[["game_id", "season", "week", "kickoff_utc", "decision_utc", "away_team"]].rename(columns={"away_team": "team"}),
        ],
        ignore_index=True,
    ).sort_values(["team", "kickoff_utc", "game_id"])
    if team_games.duplicated(["game_id", "team"]).any():
        raise ValueError("team-game identity is not unique")

    prior: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for target in team_games.itertuples(index=False):
        candidates = frame[
            frame["team"].eq(target.team)
            & frame["snapshot_utc"].le(target.decision_utc)
        ]
        if candidates.empty:
            rows.append(
                {
                    "game_id": target.game_id,
                    "season": int(target.season),
                    "week": int(target.week),
                    "team": target.team,
                    "kickoff_utc": target.kickoff_utc,
                    "decision_utc": target.decision_utc,
                    "snapshot_utc": pd.NaT,
                    "snapshot_age_minutes": np.nan,
                    "state_missing": True,
                    "rank1_gsis_coverage": np.nan,
                    "qb1_id": None,
                    "qb1_ambiguous": False,
                    "qb1_changed": np.nan,
                    "offense_rank1_count": np.nan,
                    "defense_rank1_count": np.nan,
                    "ol_rank1_count": np.nan,
                    "offense_rank1_new_count": np.nan,
                    "defense_rank1_new_count": np.nan,
                    "ol_rank1_new_count": np.nan,
                    "offense_rank1_continuity": np.nan,
                    "defense_rank1_continuity": np.nan,
                    "ol_rank1_continuity": np.nan,
                    "research_only": True,
                    "production_authorized": False,
                }
            )
            continue

        snapshot_time = candidates["snapshot_utc"].max()
        snapshot = candidates[candidates["snapshot_utc"].eq(snapshot_time)].copy()
        if snapshot_time > target.decision_utc:
            raise RuntimeError("future depth-chart snapshot crossed the T-120 firewall")

        rank1 = snapshot[snapshot["pos_rank_num"].eq(1)].copy()
        rank1_known = _valid_id(rank1["stable_id"])
        rank1_coverage = float(rank1_known.mean()) if len(rank1) else np.nan
        offense = _rank1_ids(snapshot, group="offense")
        defense = _rank1_ids(snapshot, group="defense")
        ol = _rank1_ids(snapshot, ol=True)
        qb_rows = rank1[rank1["pos_abb_norm"].eq("QB") & rank1_known]
        qb_ids = sorted(set(qb_rows["stable_id"].astype(str)))
        qb1_id = qb_ids[0] if len(qb_ids) == 1 else None
        previous = prior.get(target.team)
        previous_qb = previous.get("qb1_id") if previous else None
        qb_changed = (
            float(qb1_id != previous_qb)
            if qb1_id is not None and previous_qb is not None
            else np.nan
        )
        age = float((target.decision_utc - snapshot_time).total_seconds() / 60.0)
        rows.append(
            {
                "game_id": target.game_id,
                "season": int(target.season),
                "week": int(target.week),
                "team": target.team,
                "kickoff_utc": target.kickoff_utc,
                "decision_utc": target.decision_utc,
                "snapshot_utc": snapshot_time,
                "snapshot_age_minutes": age,
                "state_missing": False,
                "rank1_gsis_coverage": rank1_coverage,
                "qb1_id": qb1_id,
                "qb1_ambiguous": len(qb_ids) > 1,
                "qb1_changed": qb_changed,
                "offense_rank1_count": float(len(offense)),
                "defense_rank1_count": float(len(defense)),
                "ol_rank1_count": float(len(ol)),
                "offense_rank1_new_count": _new_count(offense, previous.get("offense") if previous else None),
                "defense_rank1_new_count": _new_count(defense, previous.get("defense") if previous else None),
                "ol_rank1_new_count": _new_count(ol, previous.get("ol") if previous else None),
                "offense_rank1_continuity": _continuity(offense, previous.get("offense") if previous else None),
                "defense_rank1_continuity": _continuity(defense, previous.get("defense") if previous else None),
                "ol_rank1_continuity": _continuity(ol, previous.get("ol") if previous else None),
                "research_only": True,
                "production_authorized": False,
            }
        )
        prior[target.team] = {"offense": offense, "defense": defense, "ol": ol, "qb1_id": qb1_id}

    state = pd.DataFrame(rows).sort_values(["season", "week", "game_id", "team"]).reset_index(drop=True)
    known = state[~state["state_missing"]]
    audit = {
        "schema_version": 1,
        "source": "nflverse_depth_charts_2025_plus",
        "season_scope": list(SUPPORTED_SEASONS),
        "decision_horizon_minutes": DECISION_HORIZON_MINUTES,
        "depth_rows": int(len(frame)),
        "depth_snapshots": int(frame[["team", "snapshot_utc"]].drop_duplicates().shape[0]),
        "depth_timestamp_parse_rate": 1.0,
        "raw_gsis_coverage": float(_valid_id(frame["stable_id"]).mean()) if len(frame) else 0.0,
        "team_games": int(len(state)),
        "team_games_with_state": int((~state["state_missing"]).sum()),
        "team_game_coverage": float((~state["state_missing"]).mean()) if len(state) else 0.0,
        "rank1_gsis_coverage_mean": float(known["rank1_gsis_coverage"].mean()) if len(known) else None,
        "future_snapshot_violations": int((known["snapshot_utc"] > known["decision_utc"]).sum()) if len(known) else 0,
        "injury_status_inferred": False,
        "practice_status_inferred": False,
        "postgame_snaps_used": 0,
        "completed_2026_outcomes_used": 0,
        "probability_feature_authorized": False,
        "production_authorized": False,
    }
    if audit["future_snapshot_violations"]:
        raise RuntimeError("depth-state audit found future snapshot leakage")
    return state, audit


def build_game_features(schedules: pd.DataFrame, team_state: pd.DataFrame) -> pd.DataFrame:
    games = _prepare_schedule(schedules)
    state = team_state.copy()
    keep = [
        "game_id", "team", "state_missing", "snapshot_age_minutes", "rank1_gsis_coverage",
        "qb1_changed", "offense_rank1_new_count", "defense_rank1_new_count", "ol_rank1_new_count",
        "offense_rank1_continuity", "defense_rank1_continuity", "ol_rank1_continuity",
    ]
    for side in ("home", "away"):
        team_col = f"{side}_team"
        piece = state[keep].rename(
            columns={"team": team_col, **{column: f"depth_{side}_{column}" for column in keep if column not in {"game_id", "team"}}}
        )
        games = games.merge(piece, on=["game_id", team_col], how="left", validate="one_to_one")

    for metric in ("offense_rank1_continuity", "defense_rank1_continuity", "ol_rank1_continuity", "rank1_gsis_coverage"):
        home = pd.to_numeric(games[f"depth_home_{metric}"], errors="coerce")
        away = pd.to_numeric(games[f"depth_away_{metric}"], errors="coerce")
        games[f"depth_{metric}_diff"] = home - away
    home_qb = pd.to_numeric(games["depth_home_qb1_changed"], errors="coerce").fillna(0.0)
    away_qb = pd.to_numeric(games["depth_away_qb1_changed"], errors="coerce").fillna(0.0)
    games["depth_qb_change_count"] = home_qb + away_qb
    home_missing = games["depth_home_state_missing"].fillna(True).astype(bool)
    away_missing = games["depth_away_state_missing"].fillna(True).astype(bool)
    games["depth_state_missing_count"] = home_missing.astype(int) + away_missing.astype(int)
    return games


def build_depth_state(depth: pd.DataFrame, schedules: pd.DataFrame) -> DepthStateBuild:
    team_state, audit = build_team_game_state(depth, schedules)
    features = build_game_features(schedules, team_state)
    return DepthStateBuild(team_game_state=team_state, game_features=features, audit=audit)
