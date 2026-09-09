from __future__ import annotations

"""Editorial context upgrades for Sunday Signal.

This module sits after the numerical forecast. It creates richer, more diverse
football evidence for the written matchup pages without changing LevLine unless
a feature is separately validated and promoted into the model.
"""

from collections import defaultdict
from datetime import datetime, timezone
import math
import re
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
    p["success_n"] = p["epa_n"].gt(0)
    p["explosive_pass_n"] = p["pass_play_n"] & p["yards_n"].ge(20)
    p["early_down_n"] = p["down_n"].isin([1, 2])
    p["third_down_n"] = p["down_n"].eq(3)
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
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for team, g in f.groupby("posteam_n", dropna=True):
        shotgun = g[g["shotgun_n"]]
        under = g[~g["shotgun_n"]]
        out[team].update({
            "shotgun_rate": float(g["shotgun_n"].mean()) if len(g) else np.nan,
            "shotgun_epa": float(shotgun["epa_n"].mean()) if len(shotgun) else np.nan,
            "under_center_epa": float(under["epa_n"].mean()) if len(under) else np.nan,
            "ftn_plays": float(len(g)),
        })
    for team, g in f.groupby("defteam_n", dropna=True):
        shotgun = g[g["shotgun_n"]]
        under = g[~g["shotgun_n"]]
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
    if metadata:
        md.update(metadata)
    if advantage_team:
        md["advantage_team"] = advantage_team
    return Evidence(category=category,title=title,summary=summary,strength=strength,source_name="nflverse PBP + FTN charting",source_url=FTN_SOURCE_URL if category == "scheme" else PBP_SOURCE_URL,as_of=_now(),side=side,sample_size=sample_size,relevance=relevance,metadata=md).to_dict()


def matchup_candidates(game: pd.Series, pbp_metrics: dict[str, dict[str, float]], ftn_metrics: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for off_raw, def_raw, side in [(game.away_team, game.home_team, "away"), (game.home_team, game.away_team, "home")]:
        off, deff = _norm_team(off_raw), _norm_team(def_raw)
        o, d, of, df = pbp_metrics.get(off, {}), pbp_metrics.get(deff, {}), ftn_metrics.get(off, {}), ftn_metrics.get(deff, {})
        pass_n = int(min(o.get("pass_plays", 0) or 0, d.get("pass_plays", 0) or 0))
        rush_n = int(min(o.get("rush_plays", 0) or 0, d.get("rush_plays", 0) or 0))

        sack_allowed, sack_def = _num(o.get("sack_allowed_rate")), _num(d.get("sack_rate"))
        if pass_n >= 80 and sack_allowed is not None and sack_def is not None:
            off_pct = _rank_percentile(_league_metric(pbp_metrics,"sack_allowed_rate"),sack_allowed,False)
            def_pct = _rank_percentile(_league_metric(pbp_metrics,"sack_rate"),sack_def,True)
            if off_pct is not None and def_pct is not None and (off_pct < .35 or def_pct > .65):
                advantage = deff if def_pct > (1-off_pct) else off
                summary = f"{off} gave up sacks on {sack_allowed:.1%} of pass plays last season; {deff} got home on {sack_def:.1%}. If this turns into an obvious-passing-down game, that matchup gets loud fast."
                items.append(_evidence(category="scheme",family="pressure",title=f"{off} protection vs {deff} pass rush",summary=summary,strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Pass protection paired directly with opponent sack creation",advantage_team=advantage,metadata={"editorial_score":abs(def_pct-.5)+abs(off_pct-.5)}))

        ex_off, ex_def = _num(o.get("explosive_pass_rate")), _num(d.get("explosive_pass_allowed"))
        if pass_n >= 80 and ex_off is not None and ex_def is not None:
            off_pct = _rank_percentile(_league_metric(pbp_metrics,"explosive_pass_rate"),ex_off,True)
            def_pct = _rank_percentile(_league_metric(pbp_metrics,"explosive_pass_allowed"),ex_def,False)
            if off_pct is not None and def_pct is not None and (off_pct>.67 or def_pct<.33 or def_pct>.67):
                advantage = off if off_pct+def_pct>=1 else deff
                summary = f"{off} hit a 20+ yard pass on {ex_off:.1%} of pass plays; {deff} allowed one on {ex_def:.1%}. The short version: {off} wants chunks, and {deff} would rather make it earn twelve-play drives."
                items.append(_evidence(category="scheme",family="explosives",title=f"{off} explosives vs {deff} prevention",summary=summary,strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Explosive pass generation paired with opponent prevention",advantage_team=advantage,metadata={"editorial_score":abs(off_pct-.5)+abs(def_pct-.5)}))

        ed_rate, ed_epa, ed_def = _num(o.get("early_pass_rate")), _num(o.get("early_pass_epa")), _num(d.get("early_pass_epa_allowed"))
        if pass_n >= 80 and ed_rate is not None and ed_epa is not None and ed_def is not None:
            rate_pct = _rank_percentile(_league_metric(pbp_metrics,"early_pass_rate"),ed_rate,True)
            if rate_pct is not None and (rate_pct>.70 or rate_pct<.30):
                advantage = off if ed_epa>ed_def else deff
                summary = f"{off} threw on {ed_rate:.0%} of first- and second-down plays and averaged {ed_epa:+.2f} EPA per early-down pass. {deff} allowed {ed_def:+.2f}. Win early downs and the playbook stays open; lose them and everybody knows what is coming."
                items.append(_evidence(category="scheme",family="early_down",title=f"{off} early-down approach vs {deff}",summary=summary,strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Early-down play selection paired with opponent efficiency allowed",advantage_team=advantage,metadata={"editorial_score":abs(rate_pct-.5)+abs(ed_epa-ed_def)}))

        sg_rate, sg_epa, sg_def = _num(of.get("shotgun_rate")), _num(of.get("shotgun_epa")), _num(df.get("shotgun_epa_allowed"))
        if pass_n >= 80 and sg_rate is not None and sg_epa is not None and sg_def is not None:
            rate_pct = _rank_percentile(_league_metric(ftn_metrics,"shotgun_rate"),sg_rate,True)
            if rate_pct is not None and (rate_pct>.72 or rate_pct<.28):
                identity = "shotgun-heavy" if rate_pct>.5 else "under-center-heavy"
                advantage = off if sg_epa>sg_def else deff
                summary = f"{off} was {identity}, lining up in shotgun on {sg_rate:.0%} of charted snaps. It produced {sg_epa:+.2f} EPA/play from shotgun; {deff} allowed {sg_def:+.2f}. Formation is part of the matchup here, not decoration."
                items.append(_evidence(category="scheme",family="alignment",title=f"{off} formation identity vs {deff}",summary=summary,strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="Offensive formation identity paired with opponent results",advantage_team=advantage,metadata={"editorial_score":abs(rate_pct-.5)+abs(sg_epa-sg_def)}))

        third, third_def = _num(o.get("third_down_success")), _num(d.get("third_down_success_allowed"))
        third_n = int(min(o.get("third_down_plays",0) or 0,d.get("third_down_plays",0) or 0))
        if third_n>=45 and third is not None and third_def is not None and abs(third-third_def)>=.05:
            advantage = off if third>third_def else deff
            summary = f"{off} produced positive EPA on {third:.0%} of third downs; {deff} allowed it on {third_def:.0%}. In a close game, a couple of these possessions can become the whole story."
            items.append(_evidence(category="matchup",family="third_down",title=f"{off} third downs vs {deff}",summary=summary,strength=_strength(third_n,90,45),side=side,sample_size=third_n,relevance="Third-down offense paired with opponent prevention",advantage_team=advantage,metadata={"editorial_score":abs(third-third_def)}))

        yac, yac_def = _num(o.get("yac_per_completion")), _num(d.get("yac_allowed_per_completion"))
        if pass_n>=80 and yac is not None and yac_def is not None and abs(yac-yac_def)>=.6:
            advantage = off if yac>yac_def else deff
            summary = f"{off} averaged {yac:.1f} yards after catch per completion; {deff} allowed {yac_def:.1f}. The five-yard throw becoming a fifteen-yard gain is the thing to watch."
            items.append(_evidence(category="matchup",family="yac",title=f"{off} YAC creation vs {deff} tackling",summary=summary,strength=_strength(pass_n),side=side,sample_size=pass_n,relevance="YAC creation paired with opponent YAC allowed",advantage_team=advantage,metadata={"editorial_score":abs(yac-yac_def)/3}))

        rush_epa, rush_def, box = _num(o.get("rush_epa")), _num(d.get("rush_epa_allowed")), _num(df.get("box_avg"))
        if rush_n>=70 and rush_epa is not None and rush_def is not None and box is not None:
            box_pct = _rank_percentile(_league_metric(ftn_metrics,"box_avg"),box,True)
            if box_pct is not None and (box_pct>.65 or box_pct<.35):
                descriptor = "heavier" if box_pct>.5 else "lighter"
                advantage = off if rush_epa>rush_def else deff
                summary = f"{deff} used a {descriptor}-than-typical box, averaging {box:.1f} defenders near the line. {off} ran for {rush_epa:+.2f} EPA/play; {deff} allowed {rush_def:+.2f}. The first few series should tell us whether {off} can run on its own terms."
                items.append(_evidence(category="scheme",family="run_front",title=f"{off} run game vs {deff} box structure",summary=summary,strength=_strength(rush_n,130,60),side=side,sample_size=rush_n,relevance="Rushing efficiency paired with opponent box structure",advantage_team=advantage,metadata={"editorial_score":abs(box_pct-.5)+abs(rush_epa-rush_def)}))
    return items


def fallback_history_evidence(game: pd.Series, pbp: pd.DataFrame | None, depth: pd.DataFrame | None, season: int) -> list[dict[str, Any]]:
    if pbp is None or pbp.empty or "passer_player_id" not in pbp.columns:
        return []
    p = pbp.copy()
    p["season_n"] = pd.to_numeric(p.get("season"),errors="coerce")
    p["posteam_n"] = _team_series(p,"posteam")
    p["defteam_n"] = _team_series(p,"defteam")
    p["epa_n"] = pd.to_numeric(p.get("epa"),errors="coerce")
    try:
        starters = current_starting_qbs(depth)
    except Exception:
        starters = {}
    items=[]
    for off_raw,def_raw,side in [(game.away_team,game.home_team,"away"),(game.home_team,game.away_team,"home")]:
        off,deff = _norm_team(off_raw),_norm_team(def_raw)
        starter = starters.get(off)
        if not starter or not starter.get("gsis_id"):
            continue
        q = p[p["season_n"].ge(max(2021,season-5)) & p["season_n"].lt(season) & p["posteam_n"].eq(off) & p["defteam_n"].eq(deff) & p["passer_player_id"].astype(str).eq(str(starter["gsis_id"]))].copy()
        if q.empty:
            continue
        dropbacks = int(q["epa_n"].notna().sum())
        games = int(q.get("game_id",pd.Series(index=q.index,dtype=object)).nunique())
        if dropbacks<20 or games<1:
            continue
        epa = float(q["epa_n"].mean())
        success = float(q["epa_n"].gt(0).mean())
        strength = "Strong" if games>=5 and dropbacks>=150 else "Moderate" if games>=3 and dropbacks>=75 else "Weak"
        summary = f"{starter['name']} has seen {deff} {games} time{'s' if games!=1 else ''}: {epa:+.2f} EPA/dropback and a {success:.0%} positive-EPA rate across {dropbacks} dropbacks. Same opponent, not necessarily the same defense."
        items.append(Evidence(category="history",title=f"{starter['name']} vs {deff}: prior meetings",summary=summary,strength=strength,source_name="nflverse play-by-play",source_url=PBP_SOURCE_URL,as_of=_now(),side=side,sample_size=dropbacks,relevance="Same quarterback versus the same franchise; secondary to exact coordinator history",metadata={"family":"qb_opponent_history","games":games,"epa_per_dropback":epa,"success_rate":success,"advantage_team":off if epa>0 else deff}).to_dict())
    return items


def _position_group(position: str) -> str:
    p = str(position or "").upper()
    if p in {"LT","RT","OT","T","G","C","OL"}:
        return "ol"
    if p in {"EDGE","DE","DT","DL","LB"}:
        return "front"
    if p in {"CB","S","DB"}:
        return "secondary"
    if p in {"WR","TE","QB"}:
        return "pass_skill"
    if p == "RB":
        return "run_skill"
    return "other"


def _humanize_existing_summary(text: str) -> str:
    """Remove machine-sounding guardrail prose from evidence shown to readers.

    The underlying metadata/relevance fields keep the technical guardrails. This
    function changes presentation copy only.
    """
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    replacements = {
        " Historical quarterback/team matchup results from the prior offensive staff are therefore down-weighted in the written analysis rather than treated as directly transferable.": " Older matchup history gets a haircut here: the people calling the offense are different.",
        " The status is surfaced as personnel evidence; no unvalidated point-value adjustment is silently applied to the official forecast.": " LevLine does not make up an injury point value for it.",
        " Weather is shown as context until its incremental forecast value is validated chronologically.": " For now, weather stays in the scouting report rather than becoming a hand-entered adjustment.",
        " The sample describes a pressure-style matchup; it does not prove the quarterback will repeat that result.": " Useful pressure history, not a promise that Sunday will look the same.",
        " The sample is labeled weak evidence and is explicitly discounted when offensive personnel or coaching context has changed.": " Small sample. Treat it accordingly.",
        " The sample is labeled moderate evidence and is explicitly discounted when offensive personnel or coaching context has changed.": " Useful sample, but coaching and personnel changes still matter.",
        " The sample is labeled strong evidence and is explicitly discounted when offensive personnel or coaching context has changed.": " A real sample, though not immune to coaching and personnel changes.",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(
        r"Older ([A-Z]{2,3})-vs-([A-Z]{2,3}) results are not labeled as quarterback-vs-coordinator history because the defensive decision-maker changed\.",
        r"Older \1-vs-\2 tape came against a different defensive play-caller.",
        text,
    )
    text = text.replace(
        " A conditional probability will only be shown once the player-impact transformation is historically validated; v1 does not invent a quarterback penalty.",
        " Sunday Signal will flag the uncertainty instead of inventing a quarterback penalty.",
    )
    text = text.replace(
        " The live forecast assumes the currently published team state.",
        " The current forecast assumes the published availability is right.",
    )
    text = re.sub(
        r"Travel is treated as a situational context signal; the model already contains rest/schedule features and this narrative layer does not double-count it\.",
        "The model already knows about schedule and rest, so this note is explanation rather than a second travel penalty.",
        text,
    )
    text = re.sub(
        r"The (\d+)-day differential is already represented in the quantitative rest features; it is surfaced here only to explain the forecast context\.",
        r"That \1-day gap is already in the rest features; this is the plain-English version.",
        text,
    )
    text = text.replace(
        "That creates a potential advantage; it is contextual evidence, not a silently added model feature.",
        "That is a matchup edge worth watching. For now it stays in the scouting report, not the formula.",
    ).replace(
        "That creates a tactical tension; it is contextual evidence, not a silently added model feature.",
        "The offense and defense are good at the same thing. Something has to give; for now this stays in the scouting report, not the formula.",
    ).replace(
        "That creates a matchup to monitor; it is contextual evidence, not a silently added model feature.",
        "It is worth watching, but it stays in the scouting report rather than being hand-wired into the formula.",
    )
    return text


def enrich_personnel(items: list[dict[str, Any]], game: pd.Series, injuries: dict[str,list[dict[str,Any]]], metrics: dict[str,dict[str,float]]) -> None:
    lookup = {f"{_norm_team(team)}:{_norm_name(row.get('name'))}":row for team,rows in injuries.items() for row in rows}
    for item in items:
        if str(item.get("category","")).lower() not in {"personnel","injury"}:
            continue
        side = item.get("side")
        team = _norm_team(game.away_team if side=="away" else game.home_team if side=="home" else "")
        opp = _norm_team(game.home_team if side=="away" else game.away_team if side=="home" else "")
        if not team or not opp:
            continue
        name = str(item.get("title","")).split(":",1)[-1].split("—",1)[0].strip()
        row = lookup.get(f"{team}:{_norm_name(name)}",{})
        pos = str((item.get("metadata") or {}).get("position") or row.get("position") or "")
        group = _position_group(pos)
        o, d = metrics.get(team,{}), metrics.get(opp,{})
        note = ""
        if group=="ol" and _num(d.get("sack_rate")) is not None:
            note = f" That matters a little more against {opp}, which generated sacks on {_num(d.get('sack_rate')):.1%} of opponent pass plays last season."
        elif group in {"pass_skill","secondary"}:
            value = _num(d.get("pass_epa_allowed")) if group=="pass_skill" else _num(o.get("pass_epa"))
            if value is not None:
                note = f" The passing-game backdrop: the relevant opponent-side profile was {value:+.2f} EPA/play last season."
        elif group=="run_skill" and _num(d.get("rush_epa_allowed")) is not None:
            note = f" The run-game backdrop is {opp} at {_num(d.get('rush_epa_allowed')):+.2f} rushing EPA allowed per play last season."
        item["summary"] = _humanize_existing_summary(str(item.get("summary","")).rstrip()) + note
        md = dict(item.get("metadata") or {})
        md.update({"position":pos,"family":"availability","team":team,"opponent":opp})
        item["metadata"] = md
        item["relevance"] = "Official availability status plus position-specific matchup context; no automatic point penalty"


def _polish_reader_copy(items: list[dict[str, Any]]) -> None:
    for item in items:
        item["summary"] = _humanize_existing_summary(item.get("summary", ""))


def _family(item: dict[str, Any]) -> str:
    md = item.get("metadata") or {}
    family = str(md.get("family") or md.get("concept") or "").lower()
    if family:
        return family
    title = str(item.get("title","")).lower()
    if "pressure" in title:
        return "pressure"
    if "play action" in title:
        return "play_action"
    if "screen" in title:
        return "screen"
    if "motion" in title:
        return "motion"
    if "rpo" in title:
        return "rpo"
    return str(item.get("category","context")).lower()


def _editorial_score(item: dict[str, Any]) -> float:
    md = item.get("metadata") or {}
    score = _num(md.get("editorial_score")) or 0.0
    return STRENGTH_RANK.get(str(item.get("strength")),0)*10 + min((item.get("sample_size") or 0)/100,4)+score


def diversify_game_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scheme = [x for x in items if str(x.get("category","")).lower() in {"scheme","matchup"}]
    other = [x for x in items if str(x.get("category","")).lower() not in {"scheme","matchup"}]
    selected=[]
    used=set()
    side_count=defaultdict(int)
    for item in sorted(scheme,key=_editorial_score,reverse=True):
        family = _family(item)
        side = str(item.get("side","neutral"))
        if family in used or side_count[side]>=2:
            continue
        md = dict(item.get("metadata") or {})
        md["family"] = family
        item["metadata"] = md
        selected.append(item)
        used.add(family)
        side_count[side] += 1
        if len(selected)>=3:
            break
    history = [x for x in other if str(x.get("category","")).lower()=="history"]
    history.sort(key=lambda x:("coordinator" in str(x.get("relevance","")).lower(),_editorial_score(x)),reverse=True)
    rest = [x for x in other if str(x.get("category","")).lower()!="history"]
    rest.sort(key=_editorial_score,reverse=True)
    return (selected+history[:2]+rest)[:16]


def upgrade_contextual_evidence(predictions: pd.DataFrame,evidence: dict[str,list[dict[str,Any]]],pbp: pd.DataFrame|None,ftn: pd.DataFrame|None,depth: pd.DataFrame|None,injuries: dict[str,list[dict[str,Any]]],season: int) -> tuple[dict[str,list[dict[str,Any]]],dict[str,Any]]:
    pbp_metrics = _pbp_team_metrics(pbp)
    ftn_metrics = _ftn_matchup_metrics(ftn)
    added = 0
    for _,game in predictions.iterrows():
        gid = str(game.get("game_id"))
        items = list(evidence.get(gid,[]))
        titles = {str(x.get("title")) for x in items}
        for item in matchup_candidates(game,pbp_metrics,ftn_metrics)+fallback_history_evidence(game,pbp,depth,season):
            if str(item.get("title")) not in titles:
                items.append(item)
                titles.add(str(item.get("title")))
                added += 1
        _polish_reader_copy(items)
        enrich_personnel(items,game,injuries,pbp_metrics)
        evidence[gid] = diversify_game_evidence(items)
    return evidence,{"status":"healthy","as_of":_now(),"games":len(predictions),"signals_added_before_diversity_filter":added,"families":["pressure","explosives","early_down","run_front","alignment","third_down","yac","motion","play_action","rpo","screen"],"guardrail":"Diversity ranking changes only explanatory evidence, never LevLine probabilities."}
