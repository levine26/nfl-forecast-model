from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from bs4 import BeautifulSoup
import pandas as pd
import requests

NFL_INJURY_URL = "https://www.nfl.com/injuries/league/{season}/reg{week}"

TEAM_ALIASES = {
    "ARI": ["cardinals", "arizona cardinals", "az cardinals"],
    "ATL": ["falcons", "atlanta falcons", "atl falcons"],
    "BAL": ["ravens", "baltimore ravens", "bal ravens"],
    "BUF": ["bills", "buffalo bills", "buf bills"],
    "CAR": ["panthers", "carolina panthers", "car panthers"],
    "CHI": ["bears", "chicago bears", "chi bears"],
    "CIN": ["bengals", "cincinnati bengals", "cin bengals"],
    "CLE": ["browns", "cleveland browns", "cle browns"],
    "DAL": ["cowboys", "dallas cowboys", "dal cowboys"],
    "DEN": ["broncos", "denver broncos", "den broncos"],
    "DET": ["lions", "detroit lions", "det lions"],
    "GB": ["packers", "green bay packers", "gb packers"],
    "HOU": ["texans", "houston texans", "hou texans"],
    "IND": ["colts", "indianapolis colts", "ind colts"],
    "JAX": ["jaguars", "jacksonville jaguars", "jax jaguars", "jac jaguars"],
    "KC": ["chiefs", "kansas city chiefs", "kc chiefs"],
    "LA": ["rams", "los angeles rams", "lar rams", "la rams"],
    "LAC": ["chargers", "los angeles chargers", "lac chargers"],
    "LV": ["raiders", "las vegas raiders", "lv raiders"],
    "MIA": ["dolphins", "miami dolphins", "mia dolphins"],
    "MIN": ["vikings", "minnesota vikings", "min vikings"],
    "NE": ["patriots", "new england patriots", "ne patriots"],
    "NO": ["saints", "new orleans saints", "no saints"],
    "NYG": ["giants", "new york giants", "nyg giants"],
    "NYJ": ["jets", "new york jets", "nyj jets"],
    "PHI": ["eagles", "philadelphia eagles", "phi eagles"],
    "PIT": ["steelers", "pittsburgh steelers", "pit steelers"],
    "SEA": ["seahawks", "seattle seahawks", "sea seahawks"],
    "SF": ["49ers", "san francisco 49ers", "sf 49ers"],
    "TB": ["buccaneers", "tampa bay buccaneers", "tb buccaneers"],
    "TEN": ["titans", "tennessee titans", "ten titans"],
    "WAS": ["commanders", "washington commanders", "was commanders"],
}

_ALIAS_TO_TEAM = {alias: team for team, aliases in TEAM_ALIASES.items() for alias in aliases}
POSITION_PRIORITY = {
    "QB": 6.0, "T": 2.4, "OT": 2.4, "LT": 2.5, "RT": 2.2, "C": 2.0, "G": 1.8,
    "WR": 2.1, "TE": 1.5, "RB": 1.2, "CB": 2.0, "S": 1.5, "LB": 1.4,
    "DE": 1.8, "EDGE": 1.9, "DT": 1.4, "DL": 1.4,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(text: str | None) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    return text


def _team_from_table(table) -> str | None:
    # NFL.com's server-rendered page places the club name directly before each
    # injury table. Walk backward through nearby text rather than relying on CSS
    # class names, which change more often than the page's semantic content.
    for raw in table.find_all_previous(string=True, limit=80):
        text = _clean(raw)
        if not text or text in {"player", "position", "injuries", "practice status", "game status"}:
            continue
        if text in _ALIAS_TO_TEAM:
            return _ALIAS_TO_TEAM[text]
        # Match strings such as "NE Patriots" without accepting arbitrary prose.
        for alias, team in _ALIAS_TO_TEAM.items():
            if len(alias) >= 5 and (text == alias or text.endswith(" " + alias)):
                return team
    return None


def parse_nfl_injury_html(html: str, source_url: str) -> dict[str, list[dict[str, Any]]]:
    soup = BeautifulSoup(html, "lxml")
    out: dict[str, list[dict[str, Any]]] = {}
    for table in soup.find_all("table"):
        team = _team_from_table(table)
        if not team:
            continue
        trs = table.find_all("tr")
        if not trs:
            continue
        headers = [_clean(x.get_text(" ", strip=True)) for x in trs[0].find_all(["th", "td"])]
        if "player" not in headers or "position" not in headers:
            continue
        idx = {name: i for i, name in enumerate(headers)}
        rows = []
        for tr in trs[1:]:
            cells = [x.get_text(" ", strip=True) for x in tr.find_all(["td", "th"])]
            if len(cells) < 2:
                continue
            def val(key: str) -> str:
                i = idx.get(key)
                return cells[i].strip() if i is not None and i < len(cells) else ""
            name = val("player")
            if not name:
                continue
            practice = val("practice status")
            game = val("game status")
            injury = val("injuries")
            rows.append({
                "name": name,
                "position": val("position").upper(),
                "status": game or practice or "Unspecified",
                "game_status": game,
                "practice_status": practice,
                "description": injury,
                "source_name": "NFL.com official injury report",
                "source_url": source_url,
            })
        if rows:
            out[team] = rows
    return out


def fetch_nfl_injuries(season: int, week: int, session=requests) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    url = NFL_INJURY_URL.format(season=season, week=week)
    as_of = _now()
    try:
        r = session.get(
            url,
            timeout=25,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; nfl-forecast-model/1.0; +https://github.com/levine26/nfl-forecast-model)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        r.raise_for_status()
        injuries = parse_nfl_injury_html(r.text, url)
        # A page with tables but zero parsed clubs indicates our parser no longer
        # matches the official markup and must be treated as degraded.
        table_count = r.text.lower().count("<table")
        if table_count and not injuries:
            raise ValueError("NFL injury tables were present but no team rows parsed")
        return injuries, {
            "status": "healthy",
            "provider": "NFL.com",
            "source": url,
            "as_of": as_of,
            "teams_with_reported_players": len(injuries),
            "players": sum(len(v) for v in injuries.values()),
        }
    except Exception as exc:
        return {}, {
            "status": "degraded",
            "provider": "NFL.com",
            "source": url,
            "as_of": as_of,
            "error": str(exc)[:240],
        }


def practice_status_evidence(
    predictions: pd.DataFrame,
    injuries: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Create conservative practice-only evidence when no game designation exists.

    DNP/limited practice information can matter before final game statuses are
    published, but we do not convert it into an assumed absence or a point-value
    adjustment.  Only the most material practice items are surfaced per team.
    """
    out: dict[str, list[dict[str, Any]]] = {}
    for _, game in predictions.iterrows():
        gid = str(game.get("game_id"))
        items: list[dict[str, Any]] = []
        for team, side in [(str(game.get("away_team")), "away"), (str(game.get("home_team")), "home")]:
            team = "JAX" if team == "JAC" else team
            ranked = []
            for row in injuries.get(team, []):
                if str(row.get("game_status") or "").strip():
                    continue
                practice = str(row.get("practice_status") or "").lower()
                if "did not participate" not in practice and "limited" not in practice:
                    continue
                pos = str(row.get("position") or "").upper()
                score = POSITION_PRIORITY.get(pos, 1.0) * (1.0 if "did not participate" in practice else 0.55)
                ranked.append((score, row))
            for _, row in sorted(ranked, key=lambda x: x[0], reverse=True)[:3]:
                practice = str(row.get("practice_status") or "")
                strength = "Moderate" if "Did Not Participate" in practice else "Weak"
                injury = f" ({row.get('description')})" if row.get("description") else ""
                items.append({
                    "category": "personnel",
                    "title": f"{team}: {row['name']} — {practice}",
                    "summary": f"The official NFL injury report lists {row['name']} ({row.get('position') or 'player'}) as {practice}{injury}. No game-status designation is posted yet, so this is treated as availability context rather than an assumption the player will be inactive.",
                    "strength": strength,
                    "source_name": "NFL.com official injury report",
                    "source_url": row.get("source_url"),
                    "as_of": _now(),
                    "side": side,
                    "relevance": "Current official practice participation; no game-status inference",
                    "promoted_to_model": False,
                    "metadata": {
                        "practice_status": row.get("practice_status"),
                        "game_status": row.get("game_status"),
                        "position": row.get("position"),
                    },
                })
        if items:
            out[gid] = items
    return out
