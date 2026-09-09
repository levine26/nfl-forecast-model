from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


DIVISIONS = {
    "ARI": "NFCW", "LA": "NFCW", "SF": "NFCW", "SEA": "NFCW",
    "DAL": "NFCE", "NYG": "NFCE", "PHI": "NFCE", "WAS": "NFCE",
    "CHI": "NFCN", "DET": "NFCN", "GB": "NFCN", "MIN": "NFCN",
    "ATL": "NFCS", "CAR": "NFCS", "NO": "NFCS", "TB": "NFCS",
    "BAL": "AFCN", "CIN": "AFCN", "CLE": "AFCN", "PIT": "AFCN",
    "BUF": "AFCE", "MIA": "AFCE", "NE": "AFCE", "NYJ": "AFCE",
    "HOU": "AFCS", "IND": "AFCS", "JAX": "AFCS", "TEN": "AFCS",
    "DEN": "AFCW", "KC": "AFCW", "LAC": "AFCW", "LV": "AFCW",
}

NFL_MELBOURNE_URL = "https://www.nfl.com/international/games/melbourne/"
NFL_TRAVEL_URL = "https://www.nfl.com/news/2026-nfl-schedule-release-how-do-travel-rest-prime-time-and-outdoor-games-impact-teams"
NINERS_SCHEDULE_URL = "https://www.49ers.com/news/a-game-by-game-look-at-the-san-francisco-49ers-2026-schedule-release"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(team: Any) -> str:
    value = str(team or "").upper()
    return "JAX" if value == "JAC" else value


def _completed_between(schedules: pd.DataFrame | None, a: str, b: str, since: int = 2021) -> pd.DataFrame:
    if schedules is None or schedules.empty:
        return pd.DataFrame()
    s = schedules.copy()
    for col in ("home_team", "away_team"):
        if col in s.columns:
            s[col] = s[col].astype(str).map(_norm)
    if "season" in s.columns:
        s["season"] = pd.to_numeric(s["season"], errors="coerce")
        s = s[s["season"].ge(since)]
    mask = ((s.get("home_team") == a) & (s.get("away_team") == b)) | ((s.get("home_team") == b) & (s.get("away_team") == a))
    s = s[mask].copy()
    if {"home_score", "away_score"}.issubset(s.columns):
        s = s[pd.to_numeric(s["home_score"], errors="coerce").notna() & pd.to_numeric(s["away_score"], errors="coerce").notna()]
    sort_cols = [c for c in ("season", "week", "gameday") if c in s.columns]
    return s.sort_values(sort_cols, ascending=False) if sort_cols else s


def _recent_series_note(away: str, home: str, schedules: pd.DataFrame | None) -> dict[str, Any] | None:
    sample = _completed_between(schedules, away, home, since=2021)
    if sample.empty:
        return None
    wins = {away: 0, home: 0, "ties": 0}
    for _, row in sample.iterrows():
        hs = float(row.get("home_score"))
        as_ = float(row.get("away_score"))
        if hs == as_:
            wins["ties"] += 1
        elif hs > as_:
            wins[_norm(row.get("home_team"))] += 1
        else:
            wins[_norm(row.get("away_team"))] += 1
    latest = sample.iloc[0]
    latest_score = f"{_norm(latest.get('away_team'))} {int(float(latest.get('away_score')))}, {_norm(latest.get('home_team'))} {int(float(latest.get('home_score')))}"
    rivalry = DIVISIONS.get(away) and DIVISIONS.get(away) == DIVISIONS.get(home)
    label = "division rivalry" if rivalry else "recent series"
    ties = f" with {wins['ties']} tie{'s' if wins['ties'] != 1 else ''}" if wins["ties"] else ""
    return {
        "category": "history",
        "title": f"{away}-{home}: {label}",
        "summary": (
            f"Since 2021, {away} and {home} have played {len(sample)} completed games in the nflverse schedule sample: "
            f"{away} is {wins[away]}-{wins[home]}{ties}. The most recent finished {latest_score}."
        ),
        "strength": "Strong" if rivalry or len(sample) >= 5 else "Moderate",
        "source_name": "nflverse schedule/results",
        "source_url": "https://github.com/nflverse/nfldata",
        "as_of": _now(),
        "side": "neutral",
        "sample_size": int(len(sample)),
        "relevance": "Recent team-vs-team history, explicitly limited to the stated sample window",
        "metadata": {"family": "rivalry" if rivalry else "recent_series", "sample_start_season": 2021},
    }


def _melbourne_notes(away: str, home: str, season: int, week: int) -> list[dict[str, Any]]:
    if season != 2026 or week != 1 or {away, home} != {"SF", "LA"}:
        return []
    return [
        {
            "category": "travel",
            "title": "The NFL's first regular-season game in Australia",
            "summary": (
                "Rams-49ers is being played at the Melbourne Cricket Ground, the first NFL regular-season game in Australia. "
                "The novelty is part of the football story too: both teams are dealing with an extreme time-zone and travel adjustment before a division game."
            ),
            "strength": "Strong",
            "source_name": "NFL International",
            "source_url": NFL_MELBOURNE_URL,
            "as_of": _now(),
            "side": "neutral",
            "relevance": "Verified one-off event context",
            "metadata": {"family": "international_event", "venue": "Melbourne Cricket Ground", "city": "Melbourne, Australia", "provenance_grade": "B"},
        },
        {
            "category": "travel",
            "title": "The longest regular-season trip in NFL history",
            "summary": (
                "NFL schedule analysis lists the Rams' Los Angeles-to-Melbourne trip at 7,937 miles and San Francisco's at 7,872 miles, "
                "making this the longest city-to-city trip for a regular-season game in league history."
            ),
            "strength": "Strong",
            "source_name": "NFL.com schedule analysis",
            "source_url": NFL_TRAVEL_URL,
            "as_of": _now(),
            "side": "neutral",
            "relevance": "Verified travel burden and historical event context",
            "metadata": {"family": "international_travel", "rams_miles": 7937, "49ers_miles": 7872, "provenance_grade": "B"},
        },
        {
            "category": "history",
            "title": "A 154-game rivalry leaves the country",
            "summary": (
                "The 49ers' official 2026 schedule notes list San Francisco ahead 79-72-3 in the all-time series with the Rams. "
                "That is 154 meetings before this Melbourne opener, which makes the setting new even if the opponent is anything but."
            ),
            "strength": "Strong",
            "source_name": "San Francisco 49ers official schedule notes",
            "source_url": NINERS_SCHEDULE_URL,
            "as_of": _now(),
            "side": "neutral",
            "sample_size": 154,
            "relevance": "Official franchise rivalry history",
            "metadata": {"family": "rivalry", "all_time_series": "SF 79-72-3", "provenance_grade": "B"},
        },
    ]


def build_story_context(predictions: pd.DataFrame, schedules: pd.DataFrame | None) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        away, home = _norm(game.get("away_team")), _norm(game.get("home_team"))
        try:
            season = int(float(game.get("season")))
        except Exception:
            season = 2026
        try:
            week = int(float(game.get("week")))
        except Exception:
            week = 0
        items: list[dict[str, Any]] = []
        recent = _recent_series_note(away, home, schedules)
        if recent:
            items.append(recent)
        items.extend(_melbourne_notes(away, home, season, week))
        if items:
            out[gid] = items
    return out
