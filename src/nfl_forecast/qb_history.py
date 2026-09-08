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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        move_note = (
            f" Those meetings came while {starter['name']} played for {', '.join(prior_offenses)}, not {off}; "
            "the history follows the quarterback but is explicitly discounted for the new offensive system and personnel."
            if moved else
            " This is opponent history rather than proof of a stable matchup law, so current staff and personnel still determine its weight."
        )

        items.append(Evidence(
            category="history",
            title=f"{starter['name']} vs {opponent}: player history",
            summary=(
                f"Across {games} prior meeting{'s' if games != 1 else ''} with {opponent}, {starter['name']} averaged "
                f"{epa:+.2f} EPA/dropback with a {success:.0%} positive-EPA rate over {dropbacks} dropbacks."
                + move_note
            ),
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
