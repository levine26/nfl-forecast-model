from __future__ import annotations

"""Strictly lagged FTN charting matchup state for LevLine Props 2.0 research.

This module is a feature-state gate only. It joins FTN charting to nflverse PBP on
canonical game/play IDs, derives team offense/defense scheme profiles from completed
prior games, and exposes state that may later support validated matchup coefficients.

Important chronology boundary:
- target-week and future rows are excluded;
- completed 2026 outcomes are not accepted for coefficient fitting here;
- historical FTN charting availability is not claimed to be an exact timestamped
  archive. Retrospective state is therefore development evidence only;
- live/prospective use must preserve the actual pregame capture timestamp.

FTN charting is an in-season-updating source, unlike 2023+ nflverse participation,
which is postseason-only. Participation coverage shells therefore do not enter this
live-capable state builder.
"""

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd

ENGINE_VERSION = "levline-props-ftn-matchup-state-v0.1.0"
RESEARCH_LABEL = "RESEARCH FEATURE STATE - NO PRODUCTION AUTHORIZATION"
HALF_LIFE_GAMES = 6.0

FTN_KEY = ("nflverse_game_id", "nflverse_play_id")
PBP_KEY = ("game_id", "play_id")

BOOLEAN_FIELDS = (
    "is_no_huddle",
    "is_motion",
    "is_play_action",
    "is_screen_pass",
    "is_rpo",
    "is_trick_play",
    "is_qb_out_of_pocket",
    "is_interception_worthy",
    "is_throw_away",
    "is_catchable_ball",
    "is_contested_ball",
    "is_created_reception",
    "is_drop",
    "is_qb_sneak",
    "is_qb_fault_sack",
)

OFFENSE_FEATURES = (
    "motion_rate",
    "play_action_rate",
    "screen_rate",
    "rpo_rate",
    "no_huddle_rate",
    "qb_out_of_pocket_rate",
    "shotgun_rate",
    "pistol_rate",
    "mean_offense_backfield",
    "catchable_rate",
    "drop_rate",
)

DEFENSE_FEATURES = (
    "mean_defense_box",
    "blitz_play_rate",
    "mean_blitzers",
    "mean_pass_rushers",
    "contested_ball_rate",
    "catchable_allowed_rate",
    "created_reception_allowed_rate",
)

ALL_FEATURES = OFFENSE_FEATURES + DEFENSE_FEATURES


class FTNMatchupStateError(ValueError):
    pass


@dataclass(frozen=True)
class FTNTeamMatchupState:
    team: str
    season: int
    week: int
    offense: dict[str, float | None]
    defense: dict[str, float | None]
    evidence: dict[str, int | float | str | None]
    engine_version: str = ENGINE_VERSION
    research_label: str = RESEARCH_LABEL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _team(value: Any) -> str:
    text = str(value or "").upper().strip()
    return {"JAC": "JAX", "LA": "LAR", "STL": "LAR"}.get(text, text)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _boolean(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    raw = frame[column]
    if pd.api.types.is_bool_dtype(raw):
        return raw.astype(float)
    text = raw.astype("string").str.strip().str.lower()
    mapped = text.map(
        {
            "true": 1.0,
            "false": 0.0,
            "1": 1.0,
            "0": 0.0,
            "yes": 1.0,
            "no": 0.0,
        }
    )
    numeric = pd.to_numeric(raw, errors="coerce")
    return mapped.fillna(numeric).where(lambda x: x.isin([0.0, 1.0]))


def _strict_prior(frame: pd.DataFrame, *, season: int, week: int) -> pd.DataFrame:
    s = pd.to_numeric(frame["season"], errors="coerce")
    w = pd.to_numeric(frame["week"], errors="coerce")
    safe = s.notna() & w.notna() & (
        s.lt(int(season)) | (s.eq(int(season)) & w.lt(int(week)))
    )
    out = frame[safe].copy()
    out["season"] = pd.to_numeric(out["season"], errors="raise").astype(int)
    out["week"] = pd.to_numeric(out["week"], errors="raise").astype(int)
    return out


def join_ftn_to_pbp(
    ftn: pd.DataFrame,
    pbp: pd.DataFrame,
    *,
    season: int,
    week: int,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Join strictly prior FTN charting to canonical PBP team identities."""

    if ftn is None or ftn.empty:
        return pd.DataFrame(), {
            "status": "unavailable",
            "reason": "empty_ftn_charting",
            "target_week_rows_used": 0,
        }
    if pbp is None or pbp.empty:
        raise FTNMatchupStateError("PBP is required to resolve offense/defense teams")

    ftn_required = {"nflverse_game_id", "nflverse_play_id", "season", "week"}
    pbp_required = {"game_id", "play_id", "season", "week", "posteam", "defteam"}
    missing_ftn = ftn_required - set(ftn.columns)
    missing_pbp = pbp_required - set(pbp.columns)
    if missing_ftn:
        raise FTNMatchupStateError(f"FTN charting missing fields: {sorted(missing_ftn)}")
    if missing_pbp:
        raise FTNMatchupStateError(f"PBP missing fields: {sorted(missing_pbp)}")

    chart = _strict_prior(ftn, season=season, week=week)
    plays = _strict_prior(pbp, season=season, week=week)
    if chart.empty:
        return pd.DataFrame(), {
            "status": "unavailable",
            "reason": "no_strictly_prior_ftn_rows",
            "target_week_rows_used": 0,
        }

    chart["nflverse_game_id"] = chart["nflverse_game_id"].astype(str)
    chart["nflverse_play_id"] = pd.to_numeric(
        chart["nflverse_play_id"], errors="coerce"
    )
    chart = chart[chart["nflverse_play_id"].notna()].copy()
    chart["nflverse_play_id"] = chart["nflverse_play_id"].astype(int)

    plays["game_id"] = plays["game_id"].astype(str)
    plays["play_id"] = pd.to_numeric(plays["play_id"], errors="coerce")
    plays = plays[
        plays["play_id"].notna()
        & plays["posteam"].notna()
        & plays["defteam"].notna()
    ].copy()
    plays["play_id"] = plays["play_id"].astype(int)
    plays["posteam"] = plays["posteam"].map(_team)
    plays["defteam"] = plays["defteam"].map(_team)
    plays = plays[
        plays["posteam"].ne("")
        & plays["defteam"].ne("")
        & plays["posteam"].ne(plays["defteam"])
    ].copy()

    if chart.duplicated(list(FTN_KEY)).any():
        dupes = int(chart.duplicated(list(FTN_KEY), keep=False).sum())
        raise FTNMatchupStateError(f"FTN charting has duplicate canonical play keys: {dupes}")
    pbp_identity = plays[
        ["game_id", "play_id", "season", "week", "posteam", "defteam"]
    ].drop_duplicates()
    if pbp_identity.duplicated(list(PBP_KEY)).any():
        dupes = int(pbp_identity.duplicated(list(PBP_KEY), keep=False).sum())
        raise FTNMatchupStateError(f"PBP has ambiguous canonical play keys: {dupes}")

    joined = chart.merge(
        pbp_identity,
        left_on=list(FTN_KEY),
        right_on=list(PBP_KEY),
        how="left",
        validate="one_to_one",
        suffixes=("_ftn", "_pbp"),
        indicator=True,
    )
    matched = joined[joined["_merge"].eq("both")].copy()
    if matched.empty:
        return pd.DataFrame(), {
            "status": "unavailable",
            "reason": "no_ftn_pbp_play_matches",
            "ftn_rows": int(len(chart)),
            "target_week_rows_used": 0,
        }

    # Require period identity to agree where both sides supply it.
    mismatch = (
        pd.to_numeric(matched["season_ftn"], errors="coerce")
        .ne(pd.to_numeric(matched["season_pbp"], errors="coerce"))
        | pd.to_numeric(matched["week_ftn"], errors="coerce")
        .ne(pd.to_numeric(matched["week_pbp"], errors="coerce"))
    )
    if mismatch.any():
        raise FTNMatchupStateError(
            f"FTN/PBP season-week mismatch on {int(mismatch.sum())} matched plays"
        )

    for field in BOOLEAN_FIELDS:
        matched[f"_{field}"] = _boolean(matched, field)
    for field in ("n_offense_backfield", "n_defense_box", "n_blitzers", "n_pass_rushers"):
        matched[f"_{field}"] = _numeric(matched, field)
    matched["_qb_location"] = (
        matched.get("qb_location", pd.Series("", index=matched.index))
        .astype("string")
        .fillna("")
        .str.upper()
        .str.strip()
    )

    return matched, {
        "status": "available",
        "ftn_rows_strictly_prior": int(len(chart)),
        "matched_rows": int(len(matched)),
        "match_rate": float(len(matched) / len(chart)) if len(chart) else None,
        "unique_games": int(matched["nflverse_game_id"].nunique()),
        "target_season": int(season),
        "target_week": int(week),
        "target_week_rows_used": 0,
        "historical_exact_publication_timestamp_qualified": False,
        "source_note": (
            "FTN charting is live-capable in season; this historical state uses "
            "strictly prior game/week identity but is not an exact archived as-of snapshot."
        ),
    }


def _rate(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def _game_profiles(joined: pd.DataFrame) -> pd.DataFrame:
    if joined.empty:
        return pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for (game_id, season, week, offense, defense), group in joined.groupby(
        ["nflverse_game_id", "season_pbp", "week_pbp", "posteam", "defteam"],
        sort=True,
    ):
        pass_play = pd.to_numeric(
            group.get("pass_attempt", pd.Series(np.nan, index=group.index)),
            errors="coerce",
        ).eq(1)
        if not pass_play.any():
            # FTN itself identifies several pass-only charting fields. Use their
            # observed nonmissing subset when PBP pass_attempt was not carried through.
            pass_play = (
                group["_is_play_action"].notna()
                | group["_is_screen_pass"].notna()
                | group["_is_qb_out_of_pocket"].notna()
                | group["_n_pass_rushers"].notna()
            )

        def pass_rate(field: str) -> float | None:
            sub = group.loc[pass_play, field]
            return _rate(sub)

        blitz = group.loc[pass_play, "_n_blitzers"]
        blitz_rate = (
            float((blitz.dropna() > 0).mean()) if not blitz.dropna().empty else None
        )

        rows.append(
            {
                "game_id": str(game_id),
                "season": int(season),
                "week": int(week),
                "offense": _team(offense),
                "defense": _team(defense),
                "charted_plays": int(len(group)),
                "charted_pass_plays": int(pass_play.sum()),
                "motion_rate": _rate(group["_is_motion"]),
                "play_action_rate": pass_rate("_is_play_action"),
                "screen_rate": pass_rate("_is_screen_pass"),
                "rpo_rate": _rate(group["_is_rpo"]),
                "no_huddle_rate": _rate(group["_is_no_huddle"]),
                "qb_out_of_pocket_rate": pass_rate("_is_qb_out_of_pocket"),
                "shotgun_rate": float(group["_qb_location"].eq("S").mean()),
                "pistol_rate": float(group["_qb_location"].eq("P").mean()),
                "mean_offense_backfield": _rate(group["_n_offense_backfield"]),
                "catchable_rate": pass_rate("_is_catchable_ball"),
                "drop_rate": pass_rate("_is_drop"),
                "mean_defense_box": _rate(group["_n_defense_box"]),
                "blitz_play_rate": blitz_rate,
                "mean_blitzers": _rate(blitz),
                "mean_pass_rushers": pass_rate("_n_pass_rushers"),
                "contested_ball_rate": pass_rate("_is_contested_ball"),
                "catchable_allowed_rate": pass_rate("_is_catchable_ball"),
                "created_reception_allowed_rate": pass_rate("_is_created_reception"),
            }
        )
    return pd.DataFrame(rows)


def _weights(n: int) -> np.ndarray:
    if n <= 0:
        return np.array([], dtype=float)
    age = np.arange(n - 1, -1, -1, dtype=float)
    return np.power(0.5, age / HALF_LIFE_GAMES)


def _weighted_profile(
    games: pd.DataFrame,
    features: tuple[str, ...],
) -> tuple[dict[str, float | None], int]:
    games = games.sort_values(["season", "week", "game_id"]).copy()
    weights = _weights(len(games))
    out: dict[str, float | None] = {}
    for feature in features:
        values = pd.to_numeric(games[feature], errors="coerce")
        valid = values.notna().to_numpy()
        if not valid.any():
            out[feature] = None
            continue
        w = weights[valid]
        x = values.to_numpy(float)[valid]
        out[feature] = (
            float(np.average(x, weights=w))
            if w.sum() > 0
            else float(np.mean(x))
        )
    return out, int(len(games))


def build_ftn_matchup_state(
    ftn: pd.DataFrame,
    pbp: pd.DataFrame,
    *,
    season: int,
    week: int,
    teams: list[str] | tuple[str, ...] | set[str] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build strictly lagged offense and defense profiles for requested teams."""

    joined, join_audit = join_ftn_to_pbp(ftn, pbp, season=season, week=week)
    if joined.empty:
        return pd.DataFrame(), {
            "engine_version": ENGINE_VERSION,
            "research_label": RESEARCH_LABEL,
            "join": join_audit,
            "target_week_rows_used": 0,
        }

    profiles = _game_profiles(joined)
    discovered = set(profiles["offense"].astype(str)) | set(
        profiles["defense"].astype(str)
    )
    requested = sorted(
        {_team(value) for value in (teams if teams is not None else discovered) if _team(value)}
    )

    records: list[dict[str, Any]] = []
    for team in requested:
        offense_games = profiles[profiles["offense"].eq(team)].copy()
        defense_games = profiles[profiles["defense"].eq(team)].copy()
        offense_state, offense_n = _weighted_profile(offense_games, OFFENSE_FEATURES)
        defense_state, defense_n = _weighted_profile(defense_games, DEFENSE_FEATURES)
        latest = pd.concat(
            [
                offense_games[["season", "week"]],
                defense_games[["season", "week"]],
            ],
            ignore_index=True,
        )
        latest_period = None
        if not latest.empty:
            last = latest.sort_values(["season", "week"]).iloc[-1]
            latest_period = f"{int(last['season'])}-W{int(last['week'])}"
        records.append(
            {
                "team": team,
                "target_season": int(season),
                "target_week": int(week),
                **{f"ftn_off_{key}": value for key, value in offense_state.items()},
                **{f"ftn_def_{key}": value for key, value in defense_state.items()},
                "ftn_off_games": offense_n,
                "ftn_def_games": defense_n,
                "ftn_latest_period": latest_period,
            }
        )

    frame = pd.DataFrame(records)
    return frame, {
        "engine_version": ENGINE_VERSION,
        "research_label": RESEARCH_LABEL,
        "target_season": int(season),
        "target_week": int(week),
        "half_life_games": HALF_LIFE_GAMES,
        "teams_requested": int(len(requested)),
        "teams_with_any_state": int(
            0
            if frame.empty
            else (
                frame[["ftn_off_games", "ftn_def_games"]].sum(axis=1).gt(0).sum()
            )
        ),
        "join": join_audit,
        "target_week_rows_used": 0,
        "completed_2026_outcomes_used_for_model_selection": 0,
        "live_source_capable": True,
        "postseason_participation_used": False,
    }


def load_ftn_and_pbp(seasons: list[int] | tuple[int, ...]):
    """Load FTN charting and PBP without adding either to production data bundles."""

    import nflreadpy as nfl

    def pandas(frame):
        return frame.to_pandas() if hasattr(frame, "to_pandas") else frame

    season_list = sorted({int(value) for value in seasons})
    ftn = pandas(nfl.load_ftn_charting(season_list))
    pbp = pandas(nfl.load_pbp(season_list))
    return ftn, pbp
