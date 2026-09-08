from __future__ import annotations

"""Player-centric quarterback history that survives team changes.

A quarterback's prior meetings with an opponent belong to the player, not the
team he happened to play for at the time. This layer intentionally stays
explanatory and never modifies LevLine probabilities.
"""

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from nfl_forecast.context import Evidence, PBP_SOURCE_URL, _norm_team, current_starting_qbs


_POSTSEASON_ROUND = {
    19: "Wild Card",
    20: "Divisional Round",
    21: "Conference Championship",
    22: "Super Bowl",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _first(frame: pd.DataFrame, column: str) -> Any | None:
    if column not in frame.columns:
        return None
    values = frame[column].dropna()
    return values.iloc[0] if not values.empty else None


def _meeting_stage(frame: pd.DataFrame) -> tuple[int | None, str]:
    week_raw = _first(frame, "week")
    try:
        week = int(float(week_raw)) if week_raw is not None else None
    except Exception:
        week = None
    season_type = str(_first(frame, "season_type") or "").upper()
    if season_type in {"POST", "POSTSEASON", "PLAYOFF"}:
        return week, _POSTSEASON_ROUND.get(week, "Postseason")
    return week, f"Week {week}" if week is not None else "Regular season"


def _meeting_date(frame: pd.DataFrame) -> str | None:
    for column in ("game_date", "gameday"):
        value = _first(frame, column)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _meeting_score(frame: pd.DataFrame) -> str | None:
    home = _first(frame, "home_team")
    away = _first(frame, "away_team")
    if not home or not away:
        return None
    for home_col, away_col in (("total_home_score", "total_away_score"), ("home_score", "away_score")):
        if home_col not in frame.columns or away_col not in frame.columns:
            continue
        home_scores = pd.to_numeric(frame[home_col], errors="coerce").dropna()
        away_scores = pd.to_numeric(frame[away_col], errors="coerce").dropna()
        if home_scores.empty or away_scores.empty:
            continue
        return f"{_norm_team(away)} {int(away_scores.iloc[-1])}, {_norm_team(home)} {int(home_scores.iloc[-1])}"
    return None


def _meeting_details(q: pd.DataFrame, season: int) -> list[dict[str, Any]]:
    if "game_id" not in q.columns:
        return []
    details: list[dict[str, Any]] = []
    for game_id, frame in q.groupby("game_id", sort=False):
        season_raw = _first(frame, "season_n")
        try:
            meeting_season = int(float(season_raw)) if season_raw is not None else None
        except Exception:
            meeting_season = None
        week, stage = _meeting_stage(frame)
        dropbacks = int(frame["epa_n"].notna().sum())
        if not dropbacks:
            continue
        epa = float(frame["epa_n"].mean())
        success = float(frame["epa_n"].gt(0).mean())
        offense = _norm_team(str(_first(frame, "posteam") or ""))
        label = f"{meeting_season} {stage}" if meeting_season is not None else stage
        if meeting_season == season - 1 and stage == "Super Bowl":
            human_label = "last season's Super Bowl"
        elif meeting_season == season - 1:
            human_label = f"last season, {stage}"
        else:
            human_label = label
        details.append({
            "game_id": str(game_id),
            "season": meeting_season,
            "week": week,
            "stage": stage,
            "label": label,
            "human_label": human_label,
            "date": _meeting_date(frame),
            "offense": offense or None,
            "dropbacks": dropbacks,
            "epa_per_dropback": epa,
            "success_rate": success,
            "score": _meeting_score(frame),
        })
    details.sort(key=lambda row: ((row.get("season") or 0), (row.get("week") or 0)), reverse=True)
    return details


def portable_qb_history(
    game: pd.Series,
    pbp: pd.DataFrame | None,
    depth: pd.DataFrame | None,
    season: int,
) -> list[dict[str, Any]]:
    if pbp is None or pbp.empty or "passer_player_id" not in pbp.columns:
        return []
    try:
        starters = current_starting_qbs(depth)
    except Exception:
        starters = {}
    if not starters:
        return []

    p = pbp.copy()
    p["season_n"] = pd.to_numeric(p.get("season"), errors="coerce")
    p["defteam_n"] = p.get("defteam", pd.Series(index=p.index, dtype=object)).astype(str).map(_norm_team)
    p["epa_n"] = pd.to_numeric(p.get("epa"), errors="coerce")

    items: list[dict[str, Any]] = []
    for off_raw, def_raw, side in [
        (game.away_team, game.home_team, "away"),
        (game.home_team, game.away_team, "home"),
    ]:
        off = _norm_team(off_raw)
        opponent = _norm_team(def_raw)
        starter = starters.get(off)
        if not starter or not starter.get("gsis_id"):
            continue

        q = p[
            p["season_n"].ge(max(2021, season - 5))
            & p["season_n"].lt(season)
            & p["defteam_n"].eq(opponent)
            & p["passer_player_id"].astype(str).eq(str(starter["gsis_id"]))
        ].copy()
        if q.empty:
            continue

        dropbacks = int(q["epa_n"].notna().sum())
        games = int(q.get("game_id", pd.Series(index=q.index, dtype=object)).nunique())
        if dropbacks < 20 or games < 1:
            continue

        epa = float(q["epa_n"].mean())
        success = float(q["epa_n"].gt(0).mean())
        strength = "Strong" if games >= 5 and dropbacks >= 150 else "Moderate" if games >= 3 and dropbacks >= 75 else "Weak"
        prior_offenses = sorted(set(
            q.get("posteam", pd.Series(index=q.index, dtype=object)).astype(str).map(_norm_team).dropna().tolist()
        ))
        moved = bool(prior_offenses and off not in prior_offenses)
        meetings = _meeting_details(q, season)
        latest = meetings[0] if meetings else None

        if games == 1 and latest:
            history_lead = f"{starter['name']} has faced {opponent} once before: {latest['human_label']}."
        elif latest:
            history_lead = f"{starter['name']} has faced {opponent} {games} times; the most recent was {latest['human_label']}."
        else:
            history_lead = f"{starter['name']} has {games} prior meeting{'s' if games != 1 else ''} with {opponent}."

        performance = (
            f" Across those snaps he averaged {epa:+.2f} EPA per dropback with a {success:.0%} positive-EPA rate "
            f"over {dropbacks} dropbacks."
        )
        if moved:
            transfer = (
                f" Those games came with {', '.join(prior_offenses)}, not {off}. The quarterback history travels; "
                "the old playbook does not."
            )
        else:
            transfer = " The opponent is familiar, but current staff and personnel still decide how much of that history carries forward."

        items.append(Evidence(
            category="history",
            title=f"{starter['name']} vs {opponent}: player history",
            summary=history_lead + performance + transfer,
            strength=strength,
            source_name="nflverse play-by-play",
            source_url=PBP_SOURCE_URL,
            as_of=_now(),
            side=side,
            sample_size=dropbacks,
            relevance="Same quarterback versus the same opponent, independent of the quarterback's prior team",
            metadata={
                "family":"qb_opponent_history",
                "games":games,
                "epa_per_dropback":epa,
                "success_rate":success,
                "current_team":off,
                "prior_offenses":prior_offenses,
                "team_changed":moved,
                "meetings":meetings,
                "latest_meeting":latest,
                "advantage_team":off if epa > 0 else opponent,
            },
        ).to_dict())
    return items


def add_portable_qb_history(
    predictions: pd.DataFrame,
    evidence: dict[str, list[dict[str, Any]]],
    pbp: pd.DataFrame | None,
    depth: pd.DataFrame | None,
    season: int,
) -> dict[str, list[dict[str, Any]]]:
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        generated = portable_qb_history(game, pbp, depth, season)
        if not generated:
            continue

        # The older fallback used current-team filtering and can duplicate the
        # same QB/opponent sample when a quarterback has not changed teams.
        # Portable history supersedes only that generic family; exact verified
        # QB-vs-coordinator history remains untouched.
        items = [
            item for item in list(evidence.get(gid, []))
            if (item.get("metadata") or {}).get("family") != "qb_opponent_history"
        ]
        titles = {str(item.get("title")) for item in items}
        for item in generated:
            if item["title"] not in titles:
                items.append(item)
                titles.add(item["title"])
        evidence[gid] = items
    return evidence
