from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json
import re

import nflreadpy as nfl
import pandas as pd

from nfl_forecast.coaching import load_coaching_history
from nfl_forecast.context import (
    NFLVERSE_SCHEDULE_URL,
    build_contextual_evidence,
    fetch_espn_injuries,
)
from nfl_forecast.context_plus import upgrade_contextual_evidence
from nfl_forecast.data import configure_cache
from nfl_forecast.injuries import fetch_nfl_injuries, practice_status_evidence
from nfl_forecast.narrative import build_game_previews
from nfl_forecast.qb_history import add_portable_qb_history


def _pandas(frame):
    if frame is None:
        return None
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _load_best_effort(season: int, cache_dir: str) -> tuple[pd.DataFrame | None, pd.DataFrame | None, pd.DataFrame | None, dict]:
    configure_cache(cache_dir)
    status = {}
    pbp_years = list(range(max(2020, season - 6), season))
    try:
        pbp = _pandas(nfl.load_pbp(pbp_years)); status["pbp"] = {"status":"healthy", "seasons":pbp_years}
    except Exception as exc:
        pbp = None; status["pbp"] = {"status":"degraded", "error":str(exc)[:240]}
    ftn_years = list(range(max(2022, season - 4), season + 1))
    try:
        ftn = _pandas(nfl.load_ftn_charting(ftn_years)); status["ftn"] = {"status":"healthy", "requested_seasons":ftn_years}
    except Exception:
        try:
            fallback = [y for y in ftn_years if y < season]; ftn = _pandas(nfl.load_ftn_charting(fallback)); status["ftn"] = {"status":"healthy", "requested_seasons":fallback, "note":"current season charting not yet available"}
        except Exception as exc:
            ftn = None; status["ftn"] = {"status":"degraded", "error":str(exc)[:240]}
    try:
        depth = _pandas(nfl.load_depth_charts(season)); status["depth_charts"] = {"status":"healthy", "season":season}
    except Exception:
        try:
            depth = _pandas(nfl.load_depth_charts(season - 1)); status["depth_charts"] = {"status":"degraded", "season":season-1, "note":"current season depth chart unavailable; QB-specific context may be stale"}
        except Exception as exc:
            depth = None; status["depth_charts"] = {"status":"degraded", "error":str(exc)[:240]}
    return pbp, ftn, depth, status


def _fetch_injuries(season: int, week: int):
    nfl_rows, nfl_status = fetch_nfl_injuries(season, week)
    if nfl_status.get("status") == "healthy":
        return nfl_rows, nfl_status, True
    espn_rows, espn_status = fetch_espn_injuries()
    return espn_rows, {"status":"degraded","provider":"NFL.com primary / ESPN fallback","primary":nfl_status,"fallback":espn_status,"source":nfl_status.get("source"),"as_of":datetime.now(timezone.utc).isoformat()}, False


def _editorial_audit(previews: dict[str, dict]) -> dict:
    headlines = [str(p.get("headline") or "").strip() for p in previews.values() if p.get("headline")]
    first_paragraphs = [str((p.get("paragraphs") or [""])[0]).strip() for p in previews.values() if p.get("paragraphs")]
    lead_sentences = []
    all_sentences = []
    counter_led = []
    for game_id, preview in previews.items():
        paragraph = str((preview.get("paragraphs") or [""])[0]).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
        if sentences:
            lead_sentences.append(sentences[0])
        all_sentences.extend(sentence for sentence in sentences if len(sentence) >= 36)
        if (preview.get("story_spine") or {}).get("primary_mode") == "counter":
            counter_led.append(game_id)
    counts = Counter(all_sentences)
    repeats = {sentence: count for sentence, count in counts.items() if count > 1}
    return {
        "unique_headlines": len(set(headlines)),
        "headline_count": len(headlines),
        "unique_read_leads": len(set(lead_sentences)),
        "read_count": len(first_paragraphs),
        "repeated_read_sentences": repeats,
        "repeated_read_sentence_count": len(repeats),
        "counter_led_reads": sorted(counter_led),
    }


def _require_editorial_quality(audit: dict, game_count: int) -> None:
    """Fail closed on obvious template regression before publishing prose."""
    if game_count <= 1:
        return
    failures = []
    if int(audit.get("headline_count", 0)) != game_count:
        failures.append("missing headlines")
    if int(audit.get("read_count", 0)) != game_count:
        failures.append("missing Reads")
    if int(audit.get("unique_headlines", 0)) != game_count:
        failures.append(f"headlines are not unique ({audit.get('unique_headlines')}/{game_count})")
    if int(audit.get("unique_read_leads", 0)) != game_count:
        failures.append(f"Read leads are not unique ({audit.get('unique_read_leads')}/{game_count})")
    if int(audit.get("repeated_read_sentence_count", 0)):
        failures.append(f"repeated Read sentences remain: {audit.get('repeated_read_sentences')}")
    if failures:
        raise SystemExit("Sunday Signal editorial quality gate failed: " + "; ".join(failures))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--season",type=int,default=2026); parser.add_argument("--predictions",default="outputs/this_week.csv"); parser.add_argument("--output-dir",default="outputs"); parser.add_argument("--cache-dir",default=".cache/nflreadpy"); args=parser.parse_args()
    pred_path=Path(args.predictions)
    if not pred_path.exists(): raise SystemExit(f"Missing predictions file: {pred_path}")
    predictions=pd.read_csv(pred_path); required={"game_id","gameday","gametime","away_team","home_team"}; missing=sorted(required-set(predictions.columns))
    if missing: raise SystemExit(f"Prediction feed missing required fields: {missing}")
    week_values=pd.to_numeric(predictions.get("week"),errors="coerce").dropna()
    if week_values.empty: raise SystemExit("Prediction feed does not contain a valid week number")
    week=int(week_values.iloc[0]); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); generated=datetime.now(timezone.utc).isoformat(); source_status={"generated_utc":generated}
    try:
        schedules=pd.read_csv(NFLVERSE_SCHEDULE_URL,low_memory=False); schedules=schedules[pd.to_numeric(schedules.get("season"),errors="coerce").eq(args.season)].copy(); source_status["schedule"]={"status":"healthy","source":NFLVERSE_SCHEDULE_URL,"rows":int(len(schedules))}
    except Exception as exc:
        schedules=None; source_status["schedule"]={"status":"degraded","source":NFLVERSE_SCHEDULE_URL,"error":str(exc)[:240]}

    injuries,injury_status,official_injuries=_fetch_injuries(args.season,week); source_status["injuries"]=injury_status
    teams=sorted(set(predictions["away_team"].astype(str)).union(predictions["home_team"].astype(str)))
    coaches,coach_status=load_coaching_history(teams=teams,season=args.season,cache_path=out/"coaching_cache.json",lookback=4)
    current_staff=sum(1 for t in teams if coaches.get(t,{}).get(args.season)); coach_status["current_team_coverage"]=current_staff; coach_status["requested_teams"]=len(teams)
    if coach_status.get("status")=="degraded" and current_staff>=max(8,int(.65*len(teams))):
        coach_status["status"]="partial"; coach_status["note"]="Current staff coverage is usable; older coordinator pages are incomplete, so opponent-history fallback remains active."
    source_status["coaching"]=coach_status

    pbp,ftn,depth,advanced_status=_load_best_effort(args.season,args.cache_dir); source_status.update(advanced_status)
    evidence,context_status=build_contextual_evidence(predictions=predictions,pbp=pbp,ftn=ftn,depth=depth,schedules=schedules,coaching_history=coaches,injuries=injuries,season=args.season)
    if official_injuries:
        for items in evidence.values():
            for item in items:
                if item.get("category") in {"personnel","scenario"} and "ESPN" in str(item.get("source_name","")):
                    item["source_name"]="NFL.com official injury report"; item["summary"]=str(item.get("summary","")).replace("ESPN currently lists","The official NFL injury report lists")
        practice=practice_status_evidence(predictions,injuries)
        for gid,items in practice.items(): evidence.setdefault(gid,[]).extend(items)
    for items in evidence.values():
        for item in items:
            if item.get("category")=="structural_change": item["category"]="coaching"

    # Build/diversify generic editorial context first. Portable QB history is
    # deliberately applied last so its game-level meeting metadata (date,
    # postseason round, score, team-change context) replaces the generic
    # same-team fallback instead of getting crowded out by it.
    evidence,editorial_status=upgrade_contextual_evidence(predictions=predictions,evidence=evidence,pbp=pbp,ftn=ftn,depth=depth,injuries=injuries,season=args.season)
    evidence=add_portable_qb_history(predictions=predictions,evidence=evidence,pbp=pbp,depth=depth,season=args.season)
    portable_count=sum(1 for items in evidence.values() for item in items if (item.get("metadata") or {}).get("family")=="qb_opponent_history" and (item.get("metadata") or {}).get("meetings"))
    previews=build_game_previews(predictions,evidence)
    editorial_audit=_editorial_audit(previews)
    _require_editorial_quality(editorial_audit,len(previews))

    source_status.update(context_status); source_status["editorial_intelligence"]=editorial_status
    source_status["qb_history"]={"status":"healthy","games_with_player_opponent_history":portable_count,"game_level_meeting_metadata":True,"team_change_safe":True,"guardrail":"Historical quarterback evidence follows the player across team changes but remains explanatory and is discounted for system/personnel changes."}
    source_status["evidence"]={"status":"healthy","games":len(evidence),"signals":sum(len(v) for v in evidence.values()),"generated_utc":generated,"guardrail":"Context is explanatory only unless a feature is separately validated and promoted into the numerical model."}
    source_status["previews"]={"status":"healthy","games":len(previews),"generator":"Sunday Signal ranked story-spine composer","engine":"LevLine","editorial_audit":editorial_audit,"guardrail":"Written previews synthesize verified context but do not alter numerical probabilities."}
    (out/"contextual_evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True),encoding="utf-8"); (out/"game_previews.json").write_text(json.dumps(previews,indent=2,sort_keys=True),encoding="utf-8"); (out/"context_source_status.json").write_text(json.dumps(source_status,indent=2,sort_keys=True),encoding="utf-8")
    counts={gid:len(items) for gid,items in evidence.items()}; print(f"Sunday Signal context refresh complete: {sum(counts.values())} evidence signals across {len(counts)} games"); print(f"Written previews generated: {len(previews)}")
    print("Editorial diversity audit:",json.dumps(editorial_audit,sort_keys=True))
    for gid in sorted(previews):
        preview=previews[gid]; lead=(preview.get("paragraphs") or [""])[0]
        spine=preview.get("story_spine") or {}
        print(f"EDITORIAL {gid} | {preview.get('headline','')} | {spine.get('primary_mode')}:{spine.get('primary_family')} | {lead}")
    print(json.dumps(source_status,indent=2))


if __name__ == "__main__":
    main()
