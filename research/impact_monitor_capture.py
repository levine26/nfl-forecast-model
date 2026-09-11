from __future__ import annotations

"""Research-only current availability capture for the LevLine Impact Monitor.

This adapter resolves current NFL.com injury-report names to nflverse roster GSIS IDs by
strict normalized team+name matching.  Ambiguous or unresolved identities are skipped.
It creates availability-only cards: no observed advanced statistic and no modeled impact
is fabricated merely to populate the monitor.
"""

import argparse
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nflreadpy as nfl
import pandas as pd

from nfl_forecast.injuries import load_official_injury_report
from nfl_forecast.player_impact_monitor import build_impact_monitor_payload


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _game_lookup(schedule: pd.DataFrame, season: int, week: int) -> dict[str, str]:
    required = {"game_id", "season", "week", "home_team", "away_team"}
    missing = required - set(schedule.columns)
    if missing:
        raise ValueError(f"schedule missing fields: {sorted(missing)}")
    work = schedule.copy()
    work["season"] = pd.to_numeric(work.season, errors="coerce")
    work["week"] = pd.to_numeric(work.week, errors="coerce")
    work = work[work.season.eq(int(season)) & work.week.eq(int(week))]
    lookup: dict[str, str] = {}
    for _, row in work.iterrows():
        game_id = str(row.game_id)
        for team in (str(row.home_team), str(row.away_team)):
            if team in lookup and lookup[team] != game_id:
                raise ValueError(f"multiple games found for {team} in {season} week {week}")
            lookup[team] = game_id
    return lookup


def resolve_availability_cards(
    injury_report: pd.DataFrame,
    rosters: pd.DataFrame,
    schedule: pd.DataFrame,
    *,
    season: int,
    week: int,
    retrieved_at_utc: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    injury_required = {"team", "player", "position", "practice_status", "game_status", "report_date", "source_url"}
    roster_required = {"team", "full_name", "position", "gsis_id"}
    missing_injury = injury_required - set(injury_report.columns)
    missing_roster = roster_required - set(rosters.columns)
    if missing_injury:
        raise ValueError(f"injury report missing fields: {sorted(missing_injury)}")
    if missing_roster:
        raise ValueError(f"roster missing fields: {sorted(missing_roster)}")

    games = _game_lookup(schedule, season, week)
    roster = rosters.copy()
    if "season" in roster.columns:
        roster["season"] = pd.to_numeric(roster.season, errors="coerce")
        roster = roster[roster.season.eq(int(season))]
    roster["_full_name_norm"] = roster.full_name.map(normalize_name)
    if "football_name" in roster.columns:
        roster["_football_name_norm"] = roster.football_name.map(normalize_name)
    else:
        roster["_football_name_norm"] = ""
    roster["_gsis"] = roster.gsis_id.astype("string").fillna("").str.strip()

    cards: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    for _, row in injury_report.iterrows():
        team = str(row.team).strip()
        player = str(row.player).strip()
        position = str(row.position).strip()
        name_norm = normalize_name(player)
        if not name_norm or team not in games:
            unresolved.append({"team": team, "player": player, "reason": "missing_name_or_schedule_game"})
            continue
        candidates = roster[
            roster.team.astype(str).eq(team)
            & (
                roster._full_name_norm.eq(name_norm)
                | roster._football_name_norm.eq(name_norm)
            )
            & roster._gsis.ne("")
        ].copy()
        unique_ids = candidates._gsis.drop_duplicates().tolist()
        if len(unique_ids) > 1 and position:
            narrowed = candidates[candidates.position.astype(str).str.upper().eq(position.upper())]
            if narrowed._gsis.nunique() == 1:
                candidates = narrowed
                unique_ids = candidates._gsis.drop_duplicates().tolist()
        if len(unique_ids) == 0:
            unresolved.append({"team": team, "player": player, "reason": "no_exact_normalized_team_name_match"})
            continue
        if len(unique_ids) != 1:
            ambiguous.append({"team": team, "player": player, "candidate_ids": sorted(unique_ids)})
            continue

        stable_id = str(unique_ids[0])
        matched = candidates[candidates._gsis.eq(stable_id)].iloc[-1]
        cards.append(
            {
                "schema_version": 1,
                "research_only": True,
                "game_id": games[team],
                "team": team,
                "player_id": stable_id,
                "player_name": player,
                "position": position or str(matched.position),
                "observed_statistics": [],
                "levline_impacts": [],
                "availability": {
                    "practice_status": row.practice_status if pd.notna(row.practice_status) else None,
                    "game_status": row.game_status if pd.notna(row.game_status) else None,
                    "source_status": "prospective_unqualified",
                    "source_name": "NFL.com official injury report",
                    "source_url": str(row.source_url),
                    "source_data_as_of": str(row.report_date),
                },
                "data_quality": {
                    "identity_confidence": "stable_id",
                    "coverage_status": "availability_context_only",
                    "missing_fields": [],
                    "identity_method": "exact_normalized_team_name_to_nflverse_roster_gsis_id",
                    "retrieved_at_utc": retrieved_at_utc,
                },
            }
        )

    audit = {
        "season": int(season),
        "week": int(week),
        "injury_rows": int(len(injury_report)),
        "resolved_cards": int(len(cards)),
        "unresolved_rows": int(len(unresolved)),
        "ambiguous_rows": int(len(ambiguous)),
        "unresolved": unresolved,
        "ambiguous": ambiguous,
        "identity_method": "exact_normalized_team_name_to_nflverse_roster_gsis_id",
        "availability_source_status": "prospective_unqualified",
        "modeled_player_impacts_created": 0,
        "advanced_observed_statistics_created": 0,
        "probability_feature_authorized": False,
    }
    return cards, audit


def capture_current_monitor(
    *,
    season: int,
    week: int,
    schedule_path: str = "outputs/this_week.csv",
    output_dir: str = "research_outputs/player_impact_monitor",
) -> dict[str, Any]:
    retrieved = datetime.now(timezone.utc).isoformat()
    schedule = pd.read_csv(schedule_path)
    injury_report = load_official_injury_report()
    roster = _pandas(nfl.load_rosters([int(season)]))
    cards, audit = resolve_availability_cards(
        injury_report,
        roster,
        schedule,
        season=int(season),
        week=int(week),
        retrieved_at_utc=retrieved,
    )
    payload = build_impact_monitor_payload(cards, generated_utc=retrieved)
    payload["capture_audit"] = audit
    payload["live_site_consumes_this_file"] = False
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "current_impact_monitor.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--schedule-path", default="outputs/this_week.csv")
    parser.add_argument("--output-dir", default="research_outputs/player_impact_monitor")
    args = parser.parse_args()
    capture_current_monitor(
        season=args.season,
        week=args.week,
        schedule_path=args.schedule_path,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
