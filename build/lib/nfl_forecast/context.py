from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import math
import re
import time
from typing import Any
from urllib.parse import quote, urlencode

import numpy as np
import pandas as pd
import requests


ESPN_INJURIES_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
NFLVERSE_SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
FTN_SOURCE_URL = "https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html"
PBP_SOURCE_URL = "https://github.com/nflverse/nflverse-data/releases/tag/pbp"
DEPTH_SOURCE_URL = "https://github.com/nflverse/nflverse-data/releases/tag/depth_charts"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Static venue coordinates are infrastructure, not weekly inputs. Retractable roofs are
# deliberately treated as uncertain unless a future source explicitly reports roof state.
TEAM_META: dict[str, dict[str, Any]] = {
    "ARI": {"name":"Arizona Cardinals","lat":33.5280,"lon":-112.2630,"tz":"America/Phoenix","roof":"retractable"},
    "ATL": {"name":"Atlanta Falcons","lat":33.7554,"lon":-84.4008,"tz":"America/New_York","roof":"retractable"},
    "BAL": {"name":"Baltimore Ravens","lat":39.2780,"lon":-76.6227,"tz":"America/New_York","roof":"outdoor"},
    "BUF": {"name":"Buffalo Bills","lat":42.7738,"lon":-78.7868,"tz":"America/New_York","roof":"outdoor"},
    "CAR": {"name":"Carolina Panthers","lat":35.2258,"lon":-80.8528,"tz":"America/New_York","roof":"outdoor"},
    "CHI": {"name":"Chicago Bears","lat":41.8623,"lon":-87.6167,"tz":"America/Chicago","roof":"outdoor"},
    "CIN": {"name":"Cincinnati Bengals","lat":39.0955,"lon":-84.5161,"tz":"America/New_York","roof":"outdoor"},
    "CLE": {"name":"Cleveland Browns","lat":41.5061,"lon":-81.6995,"tz":"America/New_York","roof":"outdoor"},
    "DAL": {"name":"Dallas Cowboys","lat":32.7473,"lon":-97.0945,"tz":"America/Chicago","roof":"retractable"},
    "DEN": {"name":"Denver Broncos","lat":39.7439,"lon":-105.0201,"tz":"America/Denver","roof":"outdoor"},
    "DET": {"name":"Detroit Lions","lat":42.3400,"lon":-83.0456,"tz":"America/Detroit","roof":"indoor"},
    "GB": {"name":"Green Bay Packers","lat":44.5013,"lon":-88.0622,"tz":"America/Chicago","roof":"outdoor"},
    "HOU": {"name":"Houston Texans","lat":29.6847,"lon":-95.4107,"tz":"America/Chicago","roof":"retractable"},
    "IND": {"name":"Indianapolis Colts","lat":39.7601,"lon":-86.1639,"tz":"America/Indiana/Indianapolis","roof":"retractable"},
    "JAC": {"name":"Jacksonville Jaguars","lat":30.3239,"lon":-81.6373,"tz":"America/New_York","roof":"outdoor"},
    "JAX": {"name":"Jacksonville Jaguars","lat":30.3239,"lon":-81.6373,"tz":"America/New_York","roof":"outdoor"},
    "KC": {"name":"Kansas City Chiefs","lat":39.0489,"lon":-94.4839,"tz":"America/Chicago","roof":"outdoor"},
    "LA": {"name":"Los Angeles Rams","lat":33.9535,"lon":-118.3392,"tz":"America/Los_Angeles","roof":"indoor"},
    "LAC": {"name":"Los Angeles Chargers","lat":33.9535,"lon":-118.3392,"tz":"America/Los_Angeles","roof":"indoor"},
    "LV": {"name":"Las Vegas Raiders","lat":36.0908,"lon":-115.1830,"tz":"America/Los_Angeles","roof":"indoor"},
    "MIA": {"name":"Miami Dolphins","lat":25.9580,"lon":-80.2389,"tz":"America/New_York","roof":"outdoor"},
    "MIN": {"name":"Minnesota Vikings","lat":44.9738,"lon":-93.2577,"tz":"America/Chicago","roof":"indoor"},
    "NE": {"name":"New England Patriots","lat":42.0909,"lon":-71.2643,"tz":"America/New_York","roof":"outdoor"},
    "NO": {"name":"New Orleans Saints","lat":29.9511,"lon":-90.0812,"tz":"America/Chicago","roof":"indoor"},
    "NYG": {"name":"New York Giants","lat":40.8135,"lon":-74.0745,"tz":"America/New_York","roof":"outdoor"},
    "NYJ": {"name":"New York Jets","lat":40.8135,"lon":-74.0745,"tz":"America/New_York","roof":"outdoor"},
    "PHI": {"name":"Philadelphia Eagles","lat":39.9008,"lon":-75.1675,"tz":"America/New_York","roof":"outdoor"},
    "PIT": {"name":"Pittsburgh Steelers","lat":40.4468,"lon":-80.0158,"tz":"America/New_York","roof":"outdoor"},
    "SEA": {"name":"Seattle Seahawks","lat":47.5952,"lon":-122.3316,"tz":"America/Los_Angeles","roof":"outdoor"},
    "SF": {"name":"San Francisco 49ers","lat":37.4030,"lon":-121.9700,"tz":"America/Los_Angeles","roof":"outdoor"},
    "TB": {"name":"Tampa Bay Buccaneers","lat":27.9759,"lon":-82.5033,"tz":"America/New_York","roof":"outdoor"},
    "TEN": {"name":"Tennessee Titans","lat":36.1665,"lon":-86.7713,"tz":"America/Chicago","roof":"outdoor"},
    "WAS": {"name":"Washington Commanders","lat":38.9078,"lon":-76.8645,"tz":"America/New_York","roof":"outdoor"},
}

POSITION_WEIGHT = {
    "QB": 5.0, "LT": 2.0, "RT": 1.7, "OL": 1.5, "C": 1.4, "G": 1.3,
    "WR": 1.6, "TE": 1.2, "RB": 1.0,
    "DE": 1.5, "EDGE": 1.6, "DT": 1.1, "DL": 1.1, "LB": 1.1,
    "CB": 1.5, "S": 1.2, "DB": 1.2, "K": .4, "P": .2,
}
STATUS_WEIGHT = {"out": 1.0, "injured reserve": 1.0, "ir": 1.0, "doubtful": .8, "questionable": .5, "probable": .15, "day-to-day": .3}


@dataclass
class Evidence:
    category: str
    title: str
    summary: str
    strength: str
    source_name: str
    source_url: str
    as_of: str
    side: str = "neutral"
    sample_size: int | None = None
    relevance: str | None = None
    promoted_to_model: bool = False
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        return {k: v for k, v in out.items() if v is not None}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(v) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _norm_team(team: str) -> str:
    return "JAX" if str(team).upper() == "JAC" else str(team).upper()


def _norm_name(name: str | None) -> str:
    return re.sub(r"[^a-z]", "", str(name or "").lower())


def _status_text(item: dict[str, Any]) -> str:
    for key in ["status", "type", "details"]:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            for inner in ["description", "name", "displayName", "status", "type"]:
                if value.get(inner):
                    return str(value[inner])
    return "Unspecified"


def fetch_espn_injuries(session=requests) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    as_of = utc_now()
    try:
        r = session.get(ESPN_INJURIES_URL, timeout=20, headers={"User-Agent": "nfl-forecast-model/1.0"})
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        return {}, {"status":"degraded", "as_of":as_of, "source":ESPN_INJURIES_URL, "error":str(exc)[:240]}

    out: dict[str, list[dict[str, Any]]] = {}
    for block in data.get("injuries", []) or []:
        team_obj = block.get("team", {}) if isinstance(block, dict) else {}
        team = _norm_team(team_obj.get("abbreviation", ""))
        if team not in TEAM_META:
            continue
        team_id = team_obj.get("id")
        team_url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/injuries" if team_id else ESPN_INJURIES_URL
        rows = []
        for item in block.get("injuries", []) or []:
            athlete = item.get("athlete", {}) if isinstance(item, dict) else {}
            pos = athlete.get("position", {}) if isinstance(athlete.get("position"), dict) else {}
            rows.append({
                "name": athlete.get("fullName") or athlete.get("displayName") or "Unknown player",
                "position": pos.get("abbreviation") or item.get("position") or "",
                "status": _status_text(item),
                "description": item.get("shortComment") or item.get("longComment") or "",
                "source_url": team_url,
            })
        if rows:
            out[team] = rows
    return out, {"status":"healthy", "as_of":as_of, "source":ESPN_INJURIES_URL, "teams":len(out)}


def _clean_wiki(value: str) -> str:
    value = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^/]*/>", "", value, flags=re.I)
    value = re.sub(r"\{\{[^{}]*\}\}", "", value)
    value = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    return re.sub(r"\s+", " ", value).strip(" |'")


def _coach_page_title(team: str, season: int) -> str:
    name = TEAM_META[_norm_team(team)]["name"]
    return f"{season} {name} season"


def fetch_coaching_staff(team: str, season: int, session=requests) -> tuple[dict[str, Any] | None, str]:
    title = _coach_page_title(team, season)
    source_url = "https://en.wikipedia.org/wiki/" + quote(title.replace(" ", "_"))
    params = {"action":"parse", "page":title, "prop":"wikitext", "format":"json", "formatversion":2}
    try:
        r = session.get(WIKIPEDIA_API, params=params, timeout=20, headers={"User-Agent":"nfl-forecast-model/1.0 (public research project)"})
        r.raise_for_status()
        text = r.json().get("parse", {}).get("wikitext", "")
    except Exception:
        return None, source_url
    if not text:
        return None, source_url

    aliases = {
        "head_coach": ["head_coach", "coach"],
        "off_coach": ["off_coach", "offensive_coach", "offensive_coordinator"],
        "def_coach": ["def_coach", "defensive_coach", "defensive_coordinator"],
    }
    result: dict[str, Any] = {"team":_norm_team(team), "season":season, "source_url":source_url}
    for key, fields in aliases.items():
        found = None
        for field in fields:
            m = re.search(rf"(?mi)^\s*\|\s*{re.escape(field)}\s*=\s*(.+)$", text)
            if m:
                found = _clean_wiki(m.group(1))
                if found:
                    break
        result[key] = found
    if not any(result.get(k) for k in ["head_coach","off_coach","def_coach"]):
        return None, source_url
    return result, source_url


def load_coaching_history(
    teams: list[str],
    season: int,
    cache_path: str | Path,
    lookback: int = 4,
    session=requests,
) -> tuple[dict[str, dict[int, dict[str, Any]]], dict[str, Any]]:
    cache_path = Path(cache_path)
    cache: dict[str, Any] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    now = datetime.now(timezone.utc)
    changed = False
    history: dict[str, dict[int, dict[str, Any]]] = {}
    failures = 0

    for raw_team in sorted(set(teams)):
        team = _norm_team(raw_team)
        history[team] = {}
        for year in range(season, max(season-lookback-1, 2019), -1):
            key = f"{team}:{year}"
            entry = cache.get(key)
            refresh = entry is None
            if entry and year == season:
                try:
                    fetched = datetime.fromisoformat(entry["fetched_at"])
                    if fetched.tzinfo is None:
                        fetched = fetched.replace(tzinfo=timezone.utc)
                    refresh = (now - fetched).total_seconds() > 7*24*3600
                except Exception:
                    refresh = True
            if refresh:
                data, _ = fetch_coaching_staff(team, year, session=session)
                cache[key] = {"fetched_at":utc_now(), "data":data}
                entry = cache[key]
                changed = True
                time.sleep(.03)
            data = (entry or {}).get("data")
            if data:
                history[team][year] = data
            else:
                failures += 1
    if changed:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
    status = {"status":"healthy" if failures < max(2, len(teams)) else "degraded", "as_of":utc_now(), "source":"Wikipedia season pages", "pages_missing":failures}
    return history, status


def coordinator_tenure(history: dict[str, dict[int, dict[str, Any]]], team: str, season: int, role: str) -> tuple[str | None, list[int]]:
    team = _norm_team(team)
    current = history.get(team, {}).get(season, {}).get(role)
    if not current:
        return None, []
    years = []
    for year in sorted(history.get(team, {}), reverse=True):
        if year > season:
            continue
        if _norm_name(history[team][year].get(role)) == _norm_name(current):
            years.append(year)
        elif year < season:
            break
    return current, years


def current_starting_qbs(depth: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if depth is None or depth.empty:
        return {}
    d = depth.copy()
    if {"team","player_name","pos_abb","pos_rank"}.issubset(d.columns):
        if "dt" in d.columns:
            d["_dt"] = pd.to_datetime(d["dt"], errors="coerce", utc=True)
            d = d.sort_values("_dt")
        q = d[d["pos_abb"].astype(str).str.upper().eq("QB")].copy()
        q["pos_rank"] = pd.to_numeric(q["pos_rank"], errors="coerce")
        q = q[q["pos_rank"].eq(1)]
        q = q.drop_duplicates("team", keep="last")
        return {_norm_team(r.team): {"name":r.player_name, "gsis_id":r.get("gsis_id"), "espn_id":r.get("espn_id")} for _, r in q.iterrows()}
    return {}


def _bool_mean(s: pd.Series) -> float:
    if s is None or len(s) == 0:
        return np.nan
    return pd.to_numeric(s, errors="coerce").mean()


def build_scheme_tables(ftn: pd.DataFrame | None, pbp: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    as_of = utc_now()
    if ftn is None or pbp is None or ftn.empty or pbp.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {"status":"degraded","as_of":as_of,"source":FTN_SOURCE_URL,"error":"FTN or PBP unavailable"}
    f = ftn.copy()
    p = pbp.copy()
    game_col = "nflverse_game_id" if "nflverse_game_id" in f.columns else "game_id"
    play_col = "nflverse_play_id" if "nflverse_play_id" in f.columns else "play_id"
    need_pbp = [c for c in ["game_id","play_id","season","posteam","defteam","epa","passer_player_id","passer_player_name"] if c in p.columns]
    if not {"game_id","play_id","posteam","defteam","epa"}.issubset(need_pbp):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {"status":"degraded","as_of":as_of,"source":FTN_SOURCE_URL,"error":"PBP join keys unavailable"}
    p2 = p[need_pbp].drop_duplicates(["game_id","play_id"], keep="last")
    m = f.merge(p2, left_on=[game_col,play_col], right_on=["game_id","play_id"], how="left", suffixes=("","_pbp"))
    if "season" not in m.columns and "season_pbp" in m.columns:
        m["season"] = m["season_pbp"]
    m["season"] = pd.to_numeric(m["season"], errors="coerce")
    latest = int(m["season"].dropna().max()) if m["season"].notna().any() else None
    if latest is None:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {"status":"degraded","as_of":as_of,"source":FTN_SOURCE_URL,"error":"No charted season"}
    cur = m[m["season"].eq(latest)].copy()
    cur["blitz"] = pd.to_numeric(cur.get("n_blitzers"), errors="coerce").fillna(0).gt(0)
    cur["shotgun"] = cur.get("qb_location", pd.Series(index=cur.index, dtype=object)).astype(str).eq("S")

    concepts = {
        "motion": "is_motion",
        "play_action": "is_play_action",
        "rpo": "is_rpo",
        "screen": "is_screen_pass",
    }
    off_rows = []
    for team, g in cur.groupby("posteam", dropna=True):
        row: dict[str, Any] = {"team":_norm_team(team), "season":latest, "plays":len(g), "shotgun_rate":_bool_mean(g["shotgun"])}
        for label, col in concepts.items():
            flag = g.get(col, pd.Series(False,index=g.index)).fillna(False).astype(bool)
            row[f"{label}_rate"] = float(flag.mean()) if len(flag) else np.nan
            row[f"{label}_plays"] = int(flag.sum())
            row[f"{label}_epa"] = float(pd.to_numeric(g.loc[flag,"epa"], errors="coerce").mean()) if flag.any() else np.nan
        off_rows.append(row)
    def_rows = []
    for team, g in cur.groupby("defteam", dropna=True):
        row = {"team":_norm_team(team), "season":latest, "plays":len(g), "blitz_rate":float(g["blitz"].mean()), "box_avg":float(pd.to_numeric(g.get("n_defense_box"), errors="coerce").mean())}
        for label, col in concepts.items():
            flag = g.get(col, pd.Series(False,index=g.index)).fillna(False).astype(bool)
            row[f"{label}_plays"] = int(flag.sum())
            row[f"{label}_epa_allowed"] = float(pd.to_numeric(g.loc[flag,"epa"], errors="coerce").mean()) if flag.any() else np.nan
        def_rows.append(row)

    q = m[m.get("passer_player_id", pd.Series(index=m.index,dtype=object)).notna()].copy()
    q["blitz"] = pd.to_numeric(q.get("n_blitzers"), errors="coerce").fillna(0).gt(0)
    qb_rows = []
    for (pid, name), g in q.groupby(["passer_player_id","passer_player_name"], dropna=True):
        recent = g[g["season"].ge(max(latest-1, 2022))]
        b = recent[recent["blitz"]]
        qb_rows.append({"gsis_id":pid, "name":name, "seasons":f"{max(latest-1,2022)}-{latest}", "dropbacks":len(recent), "blitz_dropbacks":len(b), "blitz_epa":float(pd.to_numeric(b["epa"], errors="coerce").mean()) if len(b) else np.nan})
    return pd.DataFrame(off_rows), pd.DataFrame(def_rows), pd.DataFrame(qb_rows), {"status":"healthy","as_of":as_of,"source":FTN_SOURCE_URL,"season":latest,"charted_plays":len(cur)}


def _strength_from_sample(sample: int, strong: int, moderate: int) -> str:
    return "Strong" if sample >= strong else "Moderate" if sample >= moderate else "Weak"


def scheme_evidence(game: pd.Series, offense: pd.DataFrame, defense: pd.DataFrame, qbs: pd.DataFrame, starters: dict[str,dict[str,Any]], coaches: dict[str,dict[int,dict[str,Any]]], season: int) -> list[Evidence]:
    if offense.empty or defense.empty:
        return []
    items: list[Evidence] = []
    off_idx = offense.set_index("team")
    def_idx = defense.set_index("team")
    concept_names = {"motion":"pre-snap motion","play_action":"play action","rpo":"RPOs","screen":"screens"}
    for off_team, def_team, side in [(game.away_team, game.home_team, "away"),(game.home_team, game.away_team, "home")]:
        off_team, def_team = _norm_team(off_team), _norm_team(def_team)
        if off_team not in off_idx.index or def_team not in def_idx.index:
            continue
        o, d = off_idx.loc[off_team], def_idx.loc[def_team]
        candidates = []
        for key, label in concept_names.items():
            rate = _num(o.get(f"{key}_rate")); oepa = _num(o.get(f"{key}_epa")); depa = _num(d.get(f"{key}_epa_allowed"))
            plays = int(min(_num(o.get(f"{key}_plays")) or 0, _num(d.get(f"{key}_plays")) or 0))
            if rate is None or oepa is None or depa is None or plays < 20:
                continue
            league_rate = pd.to_numeric(offense[f"{key}_rate"], errors="coerce").median()
            league_def = pd.to_numeric(defense[f"{key}_epa_allowed"], errors="coerce").median()
            score = abs(rate - league_rate) + abs(depa - league_def) + max(0, oepa) / 4
            candidates.append((score,key,label,rate,oepa,depa,plays,float(league_rate),float(league_def)))
        if candidates:
            _, key, label, rate, oepa, depa, plays, league_rate, league_def = max(candidates)
            direction = "potential advantage" if oepa > 0 and depa > league_def else "tactical tension" if (oepa>0) != (depa>league_def) else "matchup to monitor"
            items.append(Evidence(
                category="scheme",
                title=f"{off_team} {label} vs {def_team}",
                summary=f"{off_team} used {label} on {rate:.0%} of charted plays in {int(o.get('season'))}, versus a league median of {league_rate:.0%}, and produced {oepa:+.2f} EPA/play on those snaps. {def_team} allowed {depa:+.2f} EPA/play against the same concept. That creates a {direction}; it is contextual evidence, not a silently added model feature.",
                strength=_strength_from_sample(plays,80,40), source_name="FTN Data via nflverse", source_url=FTN_SOURCE_URL, as_of=utc_now(), side=side, sample_size=plays,
                relevance="Current offensive tendency matched to opponent results against the same charted concept", metadata={"concept":key,"offense_rate":rate,"offense_epa":oepa,"defense_epa_allowed":depa,"league_rate":league_rate}
            ))

        blitz = _num(d.get("blitz_rate"))
        starter = starters.get(off_team)
        if blitz is not None and starter and not qbs.empty and starter.get("gsis_id"):
            qr = qbs[qbs["gsis_id"].astype(str).eq(str(starter["gsis_id"]))]
            if not qr.empty:
                qr = qr.iloc[-1]
                n_blitz = int(_num(qr.get("blitz_dropbacks")) or 0)
                q_epa = _num(qr.get("blitz_epa"))
                league_blitz = float(pd.to_numeric(defense["blitz_rate"], errors="coerce").median())
                if n_blitz >= 25 and q_epa is not None and (blitz >= league_blitz + .04 or blitz <= league_blitz - .04):
                    dc, tenure = coordinator_tenure(coaches, def_team, season, "def_coach")
                    dc_text = f" under {dc}" if dc else ""
                    items.append(Evidence(
                        category="scheme",
                        title=f"{starter['name']} vs {def_team} pressure profile",
                        summary=f"{def_team}{dc_text} blitzed on {blitz:.0%} of charted plays in the latest complete FTN season (league median {league_blitz:.0%}). {starter['name']} produced {q_epa:+.2f} EPA/dropback across {n_blitz} charted blitzed dropbacks over the two most recent available seasons. The sample describes a pressure-style matchup; it does not prove the quarterback will repeat that result.",
                        strength=_strength_from_sample(n_blitz,100,50), source_name="FTN Data + nflverse PBP", source_url=FTN_SOURCE_URL, as_of=utc_now(), side=side, sample_size=n_blitz,
                        relevance="Quarterback performance against blitz paired with opponent blitz tendency", metadata={"defense_blitz_rate":blitz,"league_blitz_rate":league_blitz,"qb_blitz_epa":q_epa,"dc":dc,"dc_tenure":tenure}
                    ))
    return items


def history_and_change_evidence(game: pd.Series, pbp: pd.DataFrame | None, starters: dict[str,dict[str,Any]], coaches: dict[str,dict[int,dict[str,Any]]], season: int) -> list[Evidence]:
    items: list[Evidence] = []
    if pbp is None or pbp.empty:
        return items
    p = pbp.copy()
    p["season"] = pd.to_numeric(p.get("season"), errors="coerce")
    for off_team, def_team, side in [(game.away_team,game.home_team,"away"),(game.home_team,game.away_team,"home")]:
        off_team, def_team = _norm_team(off_team), _norm_team(def_team)
        starter = starters.get(off_team)
        current_staff = coaches.get(off_team,{}).get(season,{})
        prior_staff = coaches.get(off_team,{}).get(season-1,{})
        if current_staff and prior_staff:
            changed = []
            if current_staff.get("head_coach") and _norm_name(current_staff.get("head_coach")) != _norm_name(prior_staff.get("head_coach")):
                changed.append(f"head coach {current_staff['head_coach']}")
            if current_staff.get("off_coach") and _norm_name(current_staff.get("off_coach")) != _norm_name(prior_staff.get("off_coach")):
                changed.append(f"offensive coordinator {current_staff['off_coach']}")
            if changed:
                items.append(Evidence(
                    category="structural_change", title=f"{off_team} offense changed its decision-makers",
                    summary=f"{off_team} enters {season} with " + " and ".join(changed) + ". Historical quarterback/team matchup results from the prior offensive staff are therefore down-weighted in the written analysis rather than treated as directly transferable.",
                    strength="Strong", source_name="Wikipedia season staff records", source_url=current_staff.get("source_url", ""), as_of=utc_now(), side=side,
                    relevance="Offensive coaching continuity changes the applicability of older matchup history", metadata={"previous_head_coach":prior_staff.get("head_coach"),"previous_off_coach":prior_staff.get("off_coach")}
                ))

        cur_def = coaches.get(def_team,{}).get(season,{})
        prior_def = coaches.get(def_team,{}).get(season-1,{})
        if cur_def and prior_def and cur_def.get("def_coach") and _norm_name(cur_def.get("def_coach")) != _norm_name(prior_def.get("def_coach")):
            items.append(Evidence(
                category="structural_change", title=f"New defensive coordinator in {def_team}",
                summary=f"{def_team} is coordinated by {cur_def['def_coach']} in {season}, replacing {prior_def.get('def_coach') or 'the prior defensive staff'}. Older {off_team}-vs-{def_team} results are not labeled as quarterback-vs-coordinator history because the defensive decision-maker changed.",
                strength="Strong", source_name="Wikipedia season staff records", source_url=cur_def.get("source_url", ""), as_of=utc_now(), side=side,
                relevance="Prevents stale head-to-head history from being attributed to a new coordinator"
            ))

        if not starter or not starter.get("gsis_id"):
            continue
        dc, tenure = coordinator_tenure(coaches, def_team, season, "def_coach")
        hist_years = [y for y in tenure if y < season]
        if not dc or not hist_years:
            continue
        if "passer_player_id" not in p.columns:
            continue
        q = p[
            p["season"].isin(hist_years)
            & p.get("posteam",pd.Series(index=p.index,dtype=object)).astype(str).map(_norm_team).eq(off_team)
            & p.get("defteam",pd.Series(index=p.index,dtype=object)).astype(str).map(_norm_team).eq(def_team)
            & p["passer_player_id"].astype(str).eq(str(starter["gsis_id"]))
        ].copy()
        if q.empty:
            continue
        q["epa"] = pd.to_numeric(q.get("epa"), errors="coerce")
        game_count = q.get("game_id", pd.Series(index=q.index,dtype=object)).nunique()
        dropbacks = int(q["epa"].notna().sum())
        if game_count < 1 or dropbacks < 20:
            continue
        epa = float(q["epa"].mean())
        success = float((q["epa"] > 0).mean())
        strength = "Strong" if game_count >= 5 and dropbacks >= 150 else "Moderate" if game_count >= 3 and dropbacks >= 75 else "Weak"
        items.append(Evidence(
            category="history", title=f"{starter['name']} vs {dc}'s {def_team} defense",
            summary=f"Across {game_count} prior game{'s' if game_count != 1 else ''} in seasons when {dc} was the listed {def_team} defensive coordinator, {starter['name']} averaged {epa:+.2f} EPA/dropback with a {success:.0%} positive-EPA rate over {dropbacks} charted dropbacks. The sample is labeled {strength.lower()} evidence and is explicitly discounted when offensive personnel or coaching context has changed.",
            strength=strength, source_name="nflverse PBP + Wikipedia staff records", source_url=cur_def.get("source_url", PBP_SOURCE_URL), as_of=utc_now(), side=side, sample_size=dropbacks,
            relevance="Same quarterback, same opponent, verified continuity of the current defensive coordinator", metadata={"games":int(game_count),"epa_per_dropback":epa,"success_rate":success,"dc":dc,"tenure_years":tenure}
        ))
    return items


def personnel_evidence(game: pd.Series, injuries: dict[str,list[dict[str,Any]]], starters: dict[str,dict[str,Any]]) -> list[Evidence]:
    items: list[Evidence] = []
    for team_raw, side in [(game.away_team,"away"),(game.home_team,"home")]:
        team = _norm_team(team_raw)
        rows = []
        for inj in injuries.get(team,[]):
            status = str(inj.get("status","")).lower()
            status_factor = max([v for k,v in STATUS_WEIGHT.items() if k in status] or [0])
            if status_factor <= 0:
                continue
            pos = str(inj.get("position","")).upper()
            importance = POSITION_WEIGHT.get(pos, 1.0)
            starter_bonus = 1.35 if starters.get(team) and _norm_name(starters[team].get("name")) == _norm_name(inj.get("name")) else 1.0
            rows.append((status_factor*importance*starter_bonus,inj,starter_bonus>1))
        for _, inj, is_qb_starter in sorted(rows, reverse=True, key=lambda x:x[0])[:3]:
            status = str(inj.get("status") or "Unspecified")
            pos = str(inj.get("position") or "")
            strength = "Strong" if any(k in status.lower() for k in ["out","injured reserve","doubtful"]) else "Moderate" if "questionable" in status.lower() else "Weak"
            role = "projected starting quarterback" if is_qb_starter else pos or "player"
            summary = f"ESPN currently lists {inj['name']} ({role}) as {status}."
            if inj.get("description"):
                summary += f" {inj['description']}"
            summary += " The status is surfaced as personnel evidence; no unvalidated point-value adjustment is silently applied to the official forecast."
            items.append(Evidence(category="personnel",title=f"{team}: {inj['name']} — {status}",summary=summary,strength=strength,source_name="ESPN injury report",source_url=inj.get("source_url") or ESPN_INJURIES_URL,as_of=utc_now(),side=side,relevance="Current availability information"))
            if is_qb_starter and "questionable" in status.lower():
                items.append(Evidence(category="scenario",title=f"Scenario watch: {inj['name']} availability",summary=f"The live forecast assumes the currently published team state. If {inj['name']} is ruled out or materially limited, the site will flag the forecast as personnel-sensitive. A conditional probability will only be shown once the player-impact transformation is historically validated; v1 does not invent a quarterback penalty.",strength="Strong",source_name="ESPN injury report",source_url=inj.get("source_url") or ESPN_INJURIES_URL,as_of=utc_now(),side=side,relevance="Material binary personnel scenario",metadata={"condition":"starting_qb_active"}))
    return items


def _kickoff_utc(game: pd.Series) -> datetime | None:
    try:
        dt = datetime.strptime(f"{str(game.gameday)[:10]} {str(game.gametime)[:5]}", "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
    except Exception:
        return None


def fetch_game_weather(game: pd.Series, session=requests) -> tuple[Evidence | None, dict[str,Any] | None]:
    home = _norm_team(game.home_team)
    meta = TEAM_META.get(home)
    if not meta or meta["roof"] == "indoor":
        return None, None
    ko = _kickoff_utc(game)
    if not ko:
        return None, None
    days = (ko - datetime.now(timezone.utc)).total_seconds()/86400
    if days < -1 or days > 16:
        return None, None
    params = {
        "latitude":meta["lat"], "longitude":meta["lon"],
        "hourly":"temperature_2m,precipitation_probability,wind_speed_10m,wind_gusts_10m",
        "temperature_unit":"fahrenheit", "wind_speed_unit":"mph", "timezone":meta["tz"], "forecast_days":16,
    }
    url = OPEN_METEO_URL + "?" + urlencode(params)
    try:
        r = session.get(OPEN_METEO_URL, params=params, timeout=20, headers={"User-Agent":"nfl-forecast-model/1.0"})
        r.raise_for_status(); data = r.json(); hourly = data.get("hourly",{})
        times = [datetime.fromisoformat(x).replace(tzinfo=ZoneInfo(meta["tz"])) for x in hourly.get("time",[])]
        local_ko = ko.astimezone(ZoneInfo(meta["tz"]))
        if not times:
            raise ValueError("No hourly forecast")
        idx = min(range(len(times)), key=lambda i: abs((times[i]-local_ko).total_seconds()))
        temp = _num(hourly.get("temperature_2m",[])[idx]); precip = _num(hourly.get("precipitation_probability",[])[idx]); wind = _num(hourly.get("wind_speed_10m",[])[idx]); gust = _num(hourly.get("wind_gusts_10m",[])[idx])
    except Exception as exc:
        return None, {"status":"degraded","source":url,"as_of":utc_now(),"error":str(exc)[:200]}
    notable = (wind or 0)>=12 or (gust or 0)>=20 or (precip or 0)>=30 or (temp is not None and (temp<=35 or temp>=88))
    if not notable:
        return None, {"status":"healthy","source":url,"as_of":utc_now(),"notable":False}
    strength = "Strong" if (wind or 0)>=20 or (gust or 0)>=30 or (precip or 0)>=60 or (temp is not None and temp<=20) else "Moderate" if (wind or 0)>=15 or (gust or 0)>=24 or (precip or 0)>=40 else "Weak"
    roof_note = " The venue has a retractable roof, so this matters only if the roof is open." if meta["roof"] == "retractable" else ""
    summary = f"Open-Meteo's forecast nearest kickoff is {temp:.0f}°F" if temp is not None else "Open-Meteo's nearest-kickoff forecast"
    summary += f", {wind:.0f} mph sustained wind" if wind is not None else ""
    summary += f" with gusts near {gust:.0f} mph" if gust is not None else ""
    summary += f", and {precip:.0f}% precipitation probability" if precip is not None else ""
    summary += "." + roof_note + " Weather is shown as context until its incremental forecast value is validated chronologically."
    return Evidence(category="weather",title=f"Kickoff weather in {home}",summary=summary,strength=strength,source_name="Open-Meteo",source_url=url,as_of=utc_now(),side="neutral",relevance="Nearest-hour forecast at home venue",metadata={"temp_f":temp,"wind_mph":wind,"gust_mph":gust,"precip_pct":precip,"roof":meta["roof"]}), {"status":"healthy","source":url,"as_of":utc_now(),"notable":True}


def _haversine_miles(a: tuple[float,float], b: tuple[float,float]) -> float:
    lat1,lon1,lat2,lon2 = map(math.radians,[a[0],a[1],b[0],b[1]])
    dlat=lat2-lat1; dlon=lon2-lon1
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 3958.8*2*math.asin(math.sqrt(h))


def travel_rest_evidence(game: pd.Series, schedules: pd.DataFrame | None) -> list[Evidence]:
    if schedules is None or schedules.empty:
        return []
    away, home = _norm_team(game.away_team), _norm_team(game.home_team)
    meta_a, meta_h = TEAM_META.get(away), TEAM_META.get(home)
    if not meta_a or not meta_h:
        return []
    items=[]
    distance=_haversine_miles((meta_a["lat"],meta_a["lon"]),(meta_h["lat"],meta_h["lon"]))
    tz_delta = abs((datetime.now(ZoneInfo(meta_a["tz"])).utcoffset() - datetime.now(ZoneInfo(meta_h["tz"])).utcoffset()).total_seconds()/3600)
    if distance >= 1800 and tz_delta >= 2:
        items.append(Evidence(category="travel",title=f"Long travel spot for {away}",summary=f"{away} travels roughly {distance:,.0f} miles to {home} and crosses about {tz_delta:.0f} time zones. Travel is treated as a situational context signal; the model already contains rest/schedule features and this narrative layer does not double-count it.",strength="Moderate",source_name="nflverse schedule + venue geography",source_url=NFLVERSE_SCHEDULE_URL,as_of=utc_now(),side="away",relevance="Long-distance multi-time-zone road trip"))

    try:
        current_date = pd.Timestamp(str(game.gameday)[:10])
        s=schedules.copy(); s["gameday"]=pd.to_datetime(s["gameday"],errors="coerce")
        rest={}
        for team in [away,home]:
            team_alt = "JAC" if team=="JAX" else team
            mask=((s["home_team"].astype(str).isin([team,team_alt]))|(s["away_team"].astype(str).isin([team,team_alt]))) & (s["gameday"]<current_date)
            prev=s.loc[mask,"gameday"].dropna()
            if len(prev): rest[team]=int((current_date-prev.max()).days)
        if away in rest and home in rest and abs(rest[away]-rest[home])>=2:
            advantaged=away if rest[away]>rest[home] else home
            items.append(Evidence(category="travel",title=f"Rest differential favors {advantaged}",summary=f"Based on the published schedule, {away} has {rest[away]} days between games and {home} has {rest[home]}. The {abs(rest[away]-rest[home])}-day differential is already represented in the quantitative rest features; it is surfaced here only to explain the forecast context.",strength="Moderate",source_name="nflverse schedule",source_url=NFLVERSE_SCHEDULE_URL,as_of=utc_now(),side="neutral",relevance="Schedule/rest asymmetry",metadata={"away_rest_days":rest[away],"home_rest_days":rest[home]}))
    except Exception:
        pass
    return items


def build_contextual_evidence(
    predictions: pd.DataFrame,
    pbp: pd.DataFrame | None,
    ftn: pd.DataFrame | None,
    depth: pd.DataFrame | None,
    schedules: pd.DataFrame | None,
    coaching_history: dict[str,dict[int,dict[str,Any]]],
    injuries: dict[str,list[dict[str,Any]]],
    season: int,
    session=requests,
) -> tuple[dict[str,list[dict[str,Any]]], dict[str,Any]]:
    off, deff, qb_table, scheme_status = build_scheme_tables(ftn,pbp)
    starters=current_starting_qbs(depth)
    evidence_map: dict[str,list[dict[str,Any]]] = {}
    weather_health=[]
    for _,game in predictions.iterrows():
        items: list[Evidence]=[]
        items += personnel_evidence(game,injuries,starters)
        items += scheme_evidence(game,off,deff,qb_table,starters,coaching_history,season)
        items += history_and_change_evidence(game,pbp,starters,coaching_history,season)
        items += travel_rest_evidence(game,schedules)
        weather,status = fetch_game_weather(game,session=session)
        if status: weather_health.append(status)
        if weather: items.append(weather)
        # Keep the page readable: strongest evidence first, with diversity preserved by category.
        rank={"Strong":3,"Moderate":2,"Weak":1}
        items=sorted(items,key=lambda e:(rank.get(e.strength,0),e.category),reverse=True)
        evidence_map[str(game.game_id)] = [e.to_dict() for e in items[:10]]
    status={"scheme":scheme_status,"weather":{"status":"healthy" if not any(x.get("status")=="degraded" for x in weather_health) else "degraded","as_of":utc_now(),"games_checked":len(weather_health)}}
    return evidence_map,status
