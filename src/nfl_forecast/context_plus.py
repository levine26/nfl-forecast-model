from __future__ import annotations

"""Editorial context upgrades for Sunday Signal.

This module sits after the numerical forecast. It creates richer, more diverse
football evidence for the written matchup pages without changing LevLine unless
a feature is separately validated and promoted into the model.
"""

from collections import defaultdict
from datetime import datetime, timezone
import math
from typing import Any

import numpy as np
import pandas as pd

from nfl_forecast.context import Evidence, FTN_SOURCE_URL, PBP_SOURCE_URL, _norm_name, _norm_team, current_starting_qbs

STRENGTH_RANK = {"Strong": 3, "Moderate": 2, "Weak": 1}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _num(value: Any) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except Exception:
        return None


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    s = frame[column]
    if s.dtype == bool:
        return s.fillna(False)
    return pd.to_numeric(s, errors="coerce").fillna(0).ne(0)


def _team_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series("", index=frame.index, dtype=object)
    return frame[column].astype(str).map(_norm_team)


def _strength(sample: int, strong: int = 160, moderate: int = 70) -> str:
    return "Strong" if sample >= strong else "Moderate" if sample >= moderate else "Weak"


def _rank_percentile(series: pd.Series, value: float | None, higher_is_better: bool = True) -> float | None:
    if value is None:
        return None
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 8:
        return None
    pct = float((s <= value).mean())
    return pct if higher_is_better else 1.0 - pct


def _pbp_team_metrics(pbp: pd.DataFrame | None) -> dict[str, dict[str, float]]:
    if pbp is None or pbp.empty:
        return {}
    p = pbp.copy()
    season = pd.to_numeric(p.get("season"), errors="coerce")
    if season.notna().any():
        latest = int(season.max())
        p = p[season.eq(latest)].copy()
    p["posteam_n"] = _team_series(p, "posteam")
    p["defteam_n"] = _team_series(p, "defteam")
    p["epa_n"] = pd.to_numeric(p.get("epa"), errors="coerce")
    p["yards_n"] = pd.to_numeric(p.get("yards_gained"), errors="coerce")
    p["down_n"] = pd.to_numeric(p.get("down"), errors="coerce")
    p["yardline_n"] = pd.to_numeric(p.get("yardline_100"), errors="coerce")
    p["pass_play_n"] = _bool_series(p, "pass") | p.get("play_type", pd.Series("", index=p.index)).astype(str).eq("pass")
    p["rush_play_n"] = _bool_series(p, "rush") | p.get("play_type", pd.Series("", index=p.index)).astype(str).eq("run")
    p["sack_n"] = _bool_series(p, "sack")
    p["touchdown_n"] = _bool_series(p, "touchdown")
    p["success_n"] = p["epa_n"].gt(0)
    p["explosive_pass_n"] = p["pass_play_n"] & p["yards_n"].ge(20)
    p["early_down_n"] = p["down_n"].isin([1, 2])
    p["third_down_n"] = p["down_n"].eq(3)
    p["red_zone_n"] = p["yardline_n"].le(20)
    p["qb_scramble_n"] = _bool_series(p, "qb_scramble")
    p["yac_n"] = pd.to_numeric(p.get("yards_after_catch"), errors="coerce") if "yards_after_catch" in p.columns else np.nan

    out: dict[str, dict[str, float]] = {}
    teams = sorted(set(p["posteam_n"]).union(set(p["defteam_n"])) - {"", "nan", "None"})
    for team in teams:
        off = p[p["posteam_n"].eq(team)]
        deff = p[p["defteam_n"].eq(team)]
        opass = off[off["pass_play_n"]]
        dpass = deff[deff["pass_play_n"]]
        orush = off[off["rush_play_n"]]
        drush = deff[deff["rush_play_n"]]
        oed = off[off["early_down_n"]]
        ded = deff[deff["early_down_n"]]
        o3 = off[off["third_down_n"]]
        d3 = deff[deff["third_down_n"]]
        scr = off[off["qb_scramble_n"]]
        dscr = deff[deff["qb_scramble_n"]]
        out[team] = {
            "pass_epa": float(opass["epa_n"].mean()) if len(opass) else np.nan,
            "pass_epa_allowed": float(dpass["epa_n"].mean()) if len(dpass) else np.nan,
            "rush_epa": float(orush["epa_n"].mean()) if len(orush) else np.nan,
            "rush_epa_allowed": float(drush["epa_n"].mean()) if len(drush) else np.nan,
            "explosive_pass_rate": float(opass["explosive_pass_n"].mean()) if len(opass) else np.nan,
            "explosive_pass_allowed": float(dpass["explosive_pass_n"].mean()) if len(dpass) else np.nan,
            "sack_allowed_rate": float(opass["sack_n"].mean()) if len(opass) else np.nan,
            "sack_rate": float(dpass["sack_n"].mean()) if len(dpass) else np.nan,
            "early_pass_rate": float(oed["pass_play_n"].mean()) if len(oed) else np.nan,
            "early_pass_epa": float(oed.loc[oed["pass_play_n"], "epa_n"].mean()) if oed["pass_play_n"].any() else np.nan,
            "early_pass_epa_allowed": float(ded.loc[ded["pass_play_n"], "epa_n"].mean()) if ded["pass_play_n"].any() else np.nan,
            "third_down_success": float(o3["success_n"].mean()) if len(o3) else np.nan,
            "third_down_success_allowed": float(d3["success_n"].mean()) if len(d3) else np.nan,
            "scramble_epa": float(scr["epa_n"].mean()) if len(scr) else np.nan,
            "scramble_epa_allowed": float(dscr["epa_n"].mean()) if len(dscr) else np.nan,
            "yac_per_completion": float(opass["yac_n"].dropna().mean()) if "yac_n" in opass and opass["yac_n"].notna().any() else np.nan,
            "yac_allowed_per_completion": float(dpass["yac_n"].dropna().mean()) if "yac_n" in dpass and dpass["yac_n"].notna().any() else np.nan,
            "pass_plays": float(len(opass)), "rush_plays": float(len(orush)), "third_down_plays": float(len(o3)),
        }
    return out


def _ftn_matchup_metrics(ftn: pd.DataFrame | None) -> dict[str, dict[str, float]]:
    if ftn is None or ftn.empty:
        return {}
    f = ftn.copy()
    season = pd.to_numeric(f.get("season"), errors="coerce")
    if season.notna().any():
        latest = int(season.max())
        f = f[season.eq(latest)].copy()
    f["posteam_n"] = _team_series(f, "posteam")
    f["defteam_n"] = _team_series(f, "defteam")
    f["epa_n"] = pd.to_numeric(f.get("epa"), errors="coerce")
    f["shotgun_n"] = _bool_series(f, "shotgun")
    f["blitz_n"] = pd.to_numeric(f.get("n_blitzers"), errors="coerce").fillna(0).gt(0)
    f["box_n"] = pd.to_numeric(f.get("n_defense_box"), errors="coerce")
    f["rush_n"] = _bool_series(f, "rush") | f.get("play_type", pd.Series("", index=f.index)).astype(str).eq("run")
    f["pass_n"] = _bool_series(f, "pass") | f.get("play_type", pd.Series("", index=f.index)).astype(str).eq("pass")
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for team, g in f.groupby("posteam_n", dropna=True):
        shotgun = g[g["shotgun_n"]]; under = g[~g["shotgun_n"]]
        out[team].update({
            "shotgun_rate": float(g["shotgun_n"].mean()) if len(g) else np.nan,
            "shotgun_epa": float(shotgun["epa_n"].mean()) if len(shotgun) else np.nan,
            "under_center_epa": float(under["epa_n"].mean()) if len(under) else np.nan,
            "ftn_plays": float(len(g)),
        })
    for team, g in f.groupby("defteam_n", dropna=True):
        shotgun = g[g["shotgun_n"]]; under = g[~g["shotgun_n"]]
        out[team].update({
            "blitz_rate": float(g["blitz_n"].mean()) if len(g) else np.nan,
            "box_avg": float(g["box_n"].mean()) if g["box_n"].notna().any() else np.nan,
            "shotgun_epa_allowed": float(shotgun["epa_n"].mean()) if len(shotgun) else np.nan,
            "under_center_epa_allowed": float(under["epa_n"].mean()) if len(under) else np.nan,
        })
    return dict(out)


def _league_metric(metrics: dict[str, dict[str, float]], key: str) -> pd.Series:
    return pd.Series([v.get(key) for v in metrics.values()], dtype=float)


def _evidence(*, category: str, family: str, title: str, summary: str, strength: str, side: str, sample_size: int, relevance: str, advantage_team: str | None = None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    md = {"family": family}
    if metadata: md.update(metadata)
    if advantage_team: md["advantage_team"] = advantage_team
    return Evidence(category=category,title=title,summary=summary,strength=strength,source_name="nflverse PBP + FTN charting",source_url=FTN_SOURCE_URL if category == "scheme" else PBP_SOURCE_URL,as_of=_now(),side=side,sample_size=sample_size,relevance=relevance,metadata=md).to_dict()


def matchup_candidates(game: pd.Series, pbp_metrics: dict[str, dict[str, float]], ftn_metrics: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for off_raw, def_raw, side in [(game.away_team, game.home_team, "away"), (game.home_team, game.away_team, "home")]:
        off, deff = _norm_team(off_raw), _norm_team(def_raw)
        o, d, of, df = pbp_metrics.get(off, {}), pbp_metrics.get(deff, {}), ftn_metrics.get(off, {}), ftn_metrics.get(deff, {})
        pass_n = int(min(o.get("pass_plays", 0) or 0, d.get("pass_plays", 0) or 0)); rush_n = int(min(o.get("rush_plays", 0) or 0, d.get("rush_plays", 0) or 0))

        sack_allowed, sack_def = _num(o.get("sack_allowed_rate")), _num(d.get("sack_rate"))
        if pass_n >= 80 and sack_allowed is not None and sack_def is not None:
            off_pct = _rank_percentile(_league_metric(pbp_metrics,"sack_allowed_rate"),sack_allowed,False); def_pct = _rank_percentile(_league_metric(pbp_metrics,"sack_rate"),sack_def,True)
            if off_pct is not None and def_pct is not None and (off_pct < .35 or def_pct > .65):
                advantage = deff if def_pct > (1-off_pct) else off
                items.append(_evidence(category="scheme",family="pressure",title=f"{off} protection vs {deff} pass rush",summary=f"{off} allowed sacks on {sack_allowed:.1%} of pass plays in the latest complete season, while {deff} generated sacks on {sack_def:.1%}. This is a direct trench interaction: if {deff} can force longer downs, the pressure matchup becomes more important than the raw season averages.",strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Pass protection paired directly with opponent sack creation",advantage_team=advantage,metadata={"editorial_score":abs(def_pct-.5)+abs(off_pct-.5)}))

        ex_off, ex_def = _num(o.get("explosive_pass_rate")), _num(d.get("explosive_pass_allowed"))
        if pass_n >= 80 and ex_off is not None and ex_def is not None:
            off_pct=_rank_percentile(_league_metric(pbp_metrics,"explosive_pass_rate"),ex_off,True); def_pct=_rank_percentile(_league_metric(pbp_metrics,"explosive_pass_allowed"),ex_def,False)
            if off_pct is not None and def_pct is not None and (off_pct>.67 or def_pct<.33 or def_pct>.67):
                advantage=off if off_pct+def_pct>=1 else deff
                items.append(_evidence(category="scheme",family="explosives",title=f"{off} explosives vs {deff} prevention",summary=f"{off} produced gains of 20+ yards on {ex_off:.1%} of pass plays, while {deff} allowed them on {ex_def:.1%}. That isolates the vertical-volatility question: whether {off} can create chunk plays before {deff} forces the offense to sustain long drives.",strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Explosive pass generation paired with opponent prevention",advantage_team=advantage,metadata={"editorial_score":abs(off_pct-.5)+abs(def_pct-.5)}))

        ed_rate, ed_epa, ed_def = _num(o.get("early_pass_rate")), _num(o.get("early_pass_epa")), _num(d.get("early_pass_epa_allowed"))
        if pass_n >= 80 and ed_rate is not None and ed_epa is not None and ed_def is not None:
            rate_pct=_rank_percentile(_league_metric(pbp_metrics,"early_pass_rate"),ed_rate,True)
            if rate_pct is not None and (rate_pct>.70 or rate_pct<.30):
                advantage=off if ed_epa>ed_def else deff
                items.append(_evidence(category="scheme",family="early_down",title=f"{off} early-down approach vs {deff}",summary=f"{off} threw on {ed_rate:.0%} of first- and second-down plays and generated {ed_epa:+.2f} EPA per early-down pass. {deff} allowed {ed_def:+.2f} EPA on opponent early-down passes. The question is whether {off} can stay ahead of the sticks without becoming predictable later.",strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Early-down play selection paired with opponent efficiency allowed",advantage_team=advantage,metadata={"editorial_score":abs(rate_pct-.5)+abs(ed_epa-ed_def)}))

        sg_rate, sg_epa, sg_def = _num(of.get("shotgun_rate")), _num(of.get("shotgun_epa")), _num(df.get("shotgun_epa_allowed"))
        if pass_n >= 80 and sg_rate is not None and sg_epa is not None and sg_def is not None:
            rate_pct=_rank_percentile(_league_metric(ftn_metrics,"shotgun_rate"),sg_rate,True)
            if rate_pct is not None and (rate_pct>.72 or rate_pct<.28):
                identity="shotgun-heavy" if rate_pct>.5 else "under-center-heavy"; advantage=off if sg_epa>sg_def else deff
                items.append(_evidence(category="scheme",family="alignment",title=f"{off} formation identity vs {deff}",summary=f"{off} was {identity}, using shotgun on {sg_rate:.0%} of charted snaps. On shotgun plays it produced {sg_epa:+.2f} EPA/play, while {deff} allowed {sg_def:+.2f}. That gives this game a formation-specific matchup rather than another generic concept note.",strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Offensive formation identity paired with opponent results",advantage_team=advantage,metadata={"editorial_score":abs(rate_pct-.5)+abs(sg_epa-sg_def)}))

        third, third_def = _num(o.get("third_down_success")), _num(d.get("third_down_success_allowed")); third_n=int(min(o.get("third_down_plays",0) or 0,d.get("third_down_plays",0) or 0))
        if third_n>=45 and third is not None and third_def is not None and abs(third-third_def)>=.05:
            advantage=off if third>third_def else deff
            items.append(_evidence(category="matchup",family="third_down",title=f"{off} third downs vs {deff}",summary=f"{off} produced positive EPA on {third:.0%} of third downs, versus a {third_def:.0%} positive-EPA rate allowed by {deff}. That makes drive sustainability a matchup-specific hinge.",strength=_strength(third_n,90,45),side=side,sample_size=third_n,relevance="Third-down offense paired with opponent prevention",advantage_team=advantage,metadata={"editorial_score":abs(third-third_def)}))

        yac, yac_def = _num(o.get("yac_per_completion")), _num(d.get("yac_allowed_per_completion"))
        if pass_n>=80 and yac is not None and yac_def is not None and abs(yac-yac_def)>=.6:
            advantage=off if yac>yac_def else deff
            items.append(_evidence(category="matchup",family="yac",title=f"{off} YAC creation vs {deff} tackling",summary=f"{off} averaged {yac:.1f} yards after catch on completed passes; {deff} allowed {yac_def:.1f}. This game can swing on whether routine completions become extra first downs after the catch.",strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="YAC creation paired with opponent YAC allowed",advantage_team=advantage,metadata={"editorial_score":abs(yac-yac_def)/3}))

        rush_epa, rush_def, box = _num(o.get("rush_epa")), _num(d.get("rush_epa_allowed")), _num(df.get("box_avg"))
        if rush_n>=70 and rush_epa is not None and rush_def is not None and box is not None:
            box_pct=_rank_percentile(_league_metric(ftn_metrics,"box_avg"),box,True)
            if box_pct is not None and (box_pct>.65 or box_pct<.35):
                descriptor="heavier" if box_pct>.5 else "lighter"; advantage=off if rush_epa>rush_def else deff
                items.append(_evidence(category="scheme",family="run_front",title=f"{off} run game vs {deff} box structure",summary=f"{deff} played with a {descriptor}-than-typical box profile (average {box:.1f} defenders in the box). {off} generated {rush_epa:+.2f} rushing EPA/play, while {deff} allowed {rush_def:+.2f}. This is the clearest run-structure interaction in the matchup.",strength=_strength(rush_n,130,60),side=side,sample_size=rush_n,relevance="Rushing efficiency paired with opponent box structure",advantage_team=advantage,metadata={"editorial_score":abs(box_pct-.5)+abs(rush_epa-rush_def)}))
    return items


def fallback_history_evidence(game: pd.Series, pbp: pd.DataFrame | None, depth: pd.DataFrame | None, season: int) -> list[dict[str, Any]]:
    if pbp is None or pbp.empty or "passer_player_id" not in pbp.columns:
        return []
    p=pbp.copy(); p["season_n"]=pd.to_numeric(p.get("season"),errors="coerce"); p["posteam_n"]=_team_series(p,"posteam"); p["defteam_n"]=_team_series(p,"defteam"); p["epa_n"]=pd.to_numeric(p.get("epa"),errors="coerce")
    try: starters=current_starting_qbs(depth)
    except Exception: starters={}
    items=[]
    for off_raw,def_raw,side in [(game.away_team,game.home_team,"away"),(game.home_team,game.away_team,"home")]:
        off,deff=_norm_team(off_raw),_norm_team(def_raw); starter=starters.get(off)
        if not starter or not starter.get("gsis_id"): continue
        q=p[p["season_n"].ge(max(2021,season-5)) & p["season_n"].lt(season) & p["posteam_n"].eq(off) & p["defteam_n"].eq(deff) & p["passer_player_id"].astype(str).eq(str(starter["gsis_id"]))].copy()
        if q.empty: continue
        dropbacks=int(q["epa_n"].notna().sum()); games=int(q.get("game_id",pd.Series(index=q.index,dtype=object)).nunique())
        if dropbacks<20 or games<1: continue
        epa=float(q["epa_n"].mean()); success=float(q["epa_n"].gt(0).mean()); strength="Strong" if games>=5 and dropbacks>=150 else "Moderate" if games>=3 and dropbacks>=75 else "Weak"
        items.append(Evidence(category="history",title=f"{starter['name']} vs {deff}: prior meetings",summary=f"Across {games} prior meeting{'s' if games!=1 else ''} with {deff}, {starter['name']} averaged {epa:+.2f} EPA/dropback with a {success:.0%} positive-EPA rate over {dropbacks} dropbacks. This is opponent history, not coordinator-specific history, so current staff and personnel changes determine how much weight it deserves.",strength=strength,source_name="nflverse play-by-play",source_url=PBP_SOURCE_URL,as_of=_now(),side=side,sample_size=dropbacks,relevance="Same quarterback versus the same franchise; secondary to exact coordinator history",metadata={"family":"qb_opponent_history","games":games,"epa_per_dropback":epa,"success_rate":success,"advantage_team":off if epa>0 else deff}).to_dict())
    return items


def _position_group(position: str) -> str:
    p=str(position or "").upper()
    if p in {"LT","RT","OT","T","G","C","OL"}: return "ol"
    if p in {"EDGE","DE","DT","DL","LB"}: return "front"
    if p in {"CB","S","DB"}: return "secondary"
    if p in {"WR","TE","QB"}: return "pass_skill"
    if p=="RB": return "run_skill"
    return "other"


def enrich_personnel(items: list[dict[str, Any]], game: pd.Series, injuries: dict[str,list[dict[str,Any]]], metrics: dict[str,dict[str,float]]) -> None:
    lookup={f"{_norm_team(team)}:{_norm_name(row.get('name'))}":row for team,rows in injuries.items() for row in rows}
    for item in items:
        if str(item.get("category","")).lower() not in {"personnel","injury"}: continue
        side=item.get("side"); team=_norm_team(game.away_team if side=="away" else game.home_team if side=="home" else ""); opp=_norm_team(game.home_team if side=="away" else game.away_team if side=="home" else "")
        if not team or not opp: continue
        name=str(item.get("title","")).split(":",1)[-1].split("—",1)[0].strip(); row=lookup.get(f"{team}:{_norm_name(name)}",{}); pos=str((item.get("metadata") or {}).get("position") or row.get("position") or ""); group=_position_group(pos); o=metrics.get(team,{}); d=metrics.get(opp,{})
        note=""
        if group=="ol" and _num(d.get("sack_rate")) is not None: note=f" The matchup relevance is elevated because {opp} generated sacks on {_num(d.get('sack_rate')):.1%} of opponent pass plays last season."
        elif group in {"pass_skill","secondary"}:
            value=_num(d.get("pass_epa_allowed")) if group=="pass_skill" else _num(o.get("pass_epa"))
            if value is not None: note=f" This availability matters most to the passing-game matchup, where the relevant opponent-side pass EPA profile was {value:+.2f} per play last season."
        elif group=="run_skill" and _num(d.get("rush_epa_allowed")) is not None: note=f" The direct matchup context is {opp}'s {_num(d.get('rush_epa_allowed')):+.2f} rushing EPA allowed per play last season."
        if note: item["summary"]=str(item.get("summary","")).rstrip()+note
        md=dict(item.get("metadata") or {}); md.update({"position":pos,"family":"availability","team":team,"opponent":opp}); item["metadata"]=md; item["relevance"]="Official availability status plus position-specific matchup context; no automatic point penalty"


def _family(item: dict[str, Any]) -> str:
    md=item.get("metadata") or {}; family=str(md.get("family") or md.get("concept") or "").lower()
    if family: return family
    title=str(item.get("title","")).lower()
    if "pressure" in title: return "pressure"
    if "play action" in title: return "play_action"
    if "screen" in title: return "screen"
    if "motion" in title: return "motion"
    if "rpo" in title: return "rpo"
    return str(item.get("category","context")).lower()


def _editorial_score(item: dict[str, Any]) -> float:
    md=item.get("metadata") or {}; score=_num(md.get("editorial_score")) or 0.0
    return STRENGTH_RANK.get(str(item.get("strength")),0)*10 + min((item.get("sample_size") or 0)/100,4)+score


def diversify_game_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scheme=[x for x in items if str(x.get("category","")).lower() in {"scheme","matchup"}]; other=[x for x in items if str(x.get("category","")).lower() not in {"scheme","matchup"}]
    selected=[]; used=set(); side_count=defaultdict(int)
    for item in sorted(scheme,key=_editorial_score,reverse=True):
        family=_family(item); side=str(item.get("side","neutral"))
        if family in used or side_count[side]>=2: continue
        md=dict(item.get("metadata") or {}); md["family"]=family; item["metadata"]=md; selected.append(item); used.add(family); side_count[side]+=1
        if len(selected)>=3: break
    history=[x for x in other if str(x.get("category","")).lower()=="history"]
    history.sort(key=lambda x:("coordinator" in str(x.get("relevance","")).lower(),_editorial_score(x)),reverse=True)
    rest=[x for x in other if str(x.get("category","")).lower()!="history"]; rest.sort(key=_editorial_score,reverse=True)
    return (selected+history[:2]+rest)[:16]


def upgrade_contextual_evidence(predictions: pd.DataFrame,evidence: dict[str,list[dict[str,Any]]],pbp: pd.DataFrame|None,ftn: pd.DataFrame|None,depth: pd.DataFrame|None,injuries: dict[str,list[dict[str,Any]]],season: int) -> tuple[dict[str,list[dict[str,Any]]],dict[str,Any]]:
    pbp_metrics=_pbp_team_metrics(pbp); ftn_metrics=_ftn_matchup_metrics(ftn); added=0
    for _,game in predictions.iterrows():
        gid=str(game.get("game_id")); items=list(evidence.get(gid,[])); titles={str(x.get("title")) for x in items}
        for item in matchup_candidates(game,pbp_metrics,ftn_metrics)+fallback_history_evidence(game,pbp,depth,season):
            if str(item.get("title")) not in titles: items.append(item); titles.add(str(item.get("title"))); added+=1
        enrich_personnel(items,game,injuries,pbp_metrics); evidence[gid]=diversify_game_evidence(items)
    return evidence,{"status":"healthy","as_of":_now(),"games":len(predictions),"signals_added_before_diversity_filter":added,"families":["pressure","explosives","early_down","run_front","alignment","third_down","yac","motion","play_action","rpo","screen"],"guardrail":"Diversity ranking changes only explanatory evidence, never LevLine probabilities."}
