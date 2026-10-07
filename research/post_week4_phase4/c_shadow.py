"""Frozen Candidate C shadow scorer. Research-only; no network, no training, no production writes.

Snapshot input is a sealed per-game statement of point-in-time team observations.
The scorer reconstructs *exact* historical C state features from past games; it
never accepts a caller-supplied candidate probability or precomputed state.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.special import expit, logit

CANDIDATE_ID = "EARLY-STATE-SHRINKAGE-V1-SHADOW-2026-10-07"
PRODUCTION_ID = "F-ST-01-FROZEN-2026"
CONTRACT_ID = "c_shadow_pit_v1"
FEATURES = ("off_state_diff", "def_state_diff", "state_uncertainty")
METRICS = ("off_epa", "def_epa_allowed")
TRAINING_DIGEST = "6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0"
EPS = 1e-6


def canonical_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def iso_utc(value: object, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: timestamp missing")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name}: timestamp invalid") from exc
    if t.tzinfo is None or t.utcoffset() is None or t.utcoffset().total_seconds() != 0:
        raise ValueError(f"{name}: explicit UTC timezone required")
    return t.astimezone(timezone.utc)


def number(value: object, name: str, *, prob: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name}: expected finite number")
    x = float(value)
    if prob and not 0.0 < x < 1.0:
        raise ValueError(f"{name}: probability outside (0,1)")
    return x


def hexsha(value: object, name: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name}: expected sha256 hex digest")
    return value


def validate_model(model: dict) -> None:
    if model.get("candidate_id") != CANDIDATE_ID or model.get("training_cutoff") != 2025:
        raise ValueError("Model identity or training cutoff changed")
    if model.get("training_games") != 1615 or model.get("training_data_sha256") != TRAINING_DIGEST:
        raise ValueError("Model historical training identity changed")
    if model.get("feature_names") != list(FEATURES) or model.get("penalty") != 0.02:
        raise ValueError("Model feature/penalty identity mismatch")
    if model.get("production_promotion_authorized") is not False or model.get("outcomes_2026_used") != 0:
        raise ValueError("Model violates research-only outcome firewall")
    iso_utc(model.get("frozen_at_utc"), "model frozen_at_utc")
    for name, size in (("theta",4),("means",3),("stds",3)):
        seq=model.get(name)
        if not isinstance(seq,list) or len(seq)!=size:
            raise ValueError(f"Model {name} invalid shape")
        for value in seq:
            number(value,"model."+name)
    if any(x<=0 for x in model["stds"]):
        raise ValueError("Model standard deviation must be positive")
    hexsha(model.get("builder_source_sha256"),"builder_source_sha256")
    hexsha(model.get("historical_state_source_sha256"),"historical_state_source_sha256")


def _game_stat(row: dict, *, season: int, team: str, cutoff: datetime, label: str) -> dict:
    if not isinstance(row, dict) or row.get("team") != team or row.get("season") != season:
        raise ValueError(f"{label}: wrong team/season")
    gameid=row.get("game_id")
    if not isinstance(gameid,str) or not gameid.startswith(str(season)+"_"):
        raise ValueError(f"{label}: wrong game ID")
    kickoff=iso_utc(row.get("kickoff_utc"),label+".kickoff")
    observed=iso_utc(row.get("stats_observed_utc"),label+".stats_observed")
    if kickoff >= cutoff or observed > cutoff or observed <= kickoff:
        raise ValueError(f"{label}: post-cutoff or not-completed game data")
    values={}
    for metric in METRICS:
        v=row.get(metric)
        values[metric] = float("nan") if v is None else number(v,label+"."+metric)
    if all(math.isnan(v) for v in values.values()):
        raise ValueError(f"{label}: missing completed-game EPA")
    return {"id":gameid,"kickoff":kickoff,"data":values}


def _team_state(s: dict, *, team: str, season: int, cutoff: datetime) -> dict:
    if not isinstance(s,dict) or s.get("team") != team:
        raise ValueError("Team snapshot does not match game identity")
    prev=s.get("last_eight_previous_season")
    current=s.get("current_season_completed")
    league=s.get("previous_season_league_mean")
    if not isinstance(prev,list) or len(prev)!=8 or not isinstance(current,list) or not isinstance(league,dict):
        raise ValueError("Incomplete historical team state/league reference")
    p=[_game_stat(x,season=season-1,team=team,cutoff=cutoff,label="prior") for x in prev]
    c=[_game_stat(x,season=season,team=team,cutoff=cutoff,label="current") for x in current]
    if len({r["id"] for r in p+c})!=len(p)+len(c):
        raise ValueError("Duplicate historical team fixture")
    if any(p[i]["kickoff"]>=p[i+1]["kickoff"] for i in range(len(p)-1)) or any(c[i]["kickoff"]>=c[i+1]["kickoff"] for i in range(len(c)-1)):
        raise ValueError("Unsorted source games")
    n=s.get("expected_completed_current_season_games")
    if isinstance(n,bool) or not isinstance(n,int) or n != len(c) or n<0 or n>18:
        raise ValueError("Incomplete current-season completed-game count")
    values={}
    for metric in METRICS:
        mean=number(league.get(metric),"league."+metric)
        previous=[r["data"][metric] for r in p if math.isfinite(r["data"][metric])]
        prior_form=float(np.mean(previous)) if previous else mean
        prior_center=0.6*prior_form+0.4*mean
        fresh=[r["data"][metric] for r in c if math.isfinite(r["data"][metric])]
        form=float(np.mean(fresh)) if fresh else prior_center
        values[metric]=(n*form+6.0*prior_center)/(n+6.0)
    return {"n":n, **values}


def derive_features(snapshot: dict, cutoff: datetime) -> list[float]:
    teams=snapshot.get("team_states")
    if not isinstance(teams,dict) or set(teams)!={"home","away"}:
        raise ValueError("Team state source missing/mismatched")
    season=snapshot["season"]
    h=_team_state(teams["home"],team=snapshot["home_team"],season=season,cutoff=cutoff)
    a=_team_state(teams["away"],team=snapshot["away_team"],season=season,cutoff=cutoff)
    return [h["off_epa"]-a["off_epa"],h["def_epa_allowed"]-a["def_epa_allowed"],
            abs(h["n"]-a["n"])/(h["n"]+a["n"]+6.0)]


def score_snapshot(snapshot: dict, model: dict) -> dict:
    validate_model(model)
    if not isinstance(snapshot,dict) or snapshot.get("contract")!=CONTRACT_ID:
        raise ValueError("Unknown snapshot contract")
    game_id=snapshot.get("game_id")
    season=snapshot.get("season")
    week=snapshot.get("week")
    home=snapshot.get("home_team");away=snapshot.get("away_team")
    if isinstance(season,bool) or not isinstance(season,int) or season<2026:
        raise ValueError("Not a prospective NFL season")
    if isinstance(week,bool) or not isinstance(week,int) or not 1<=week<=18:
        raise ValueError("NFL week invalid")
    if (not isinstance(home,str) or not isinstance(away,str) or home==away or
        not isinstance(game_id,str) or game_id!=f"{season}_{week:02d}_{away}_{home}"):
        raise ValueError("Game ID / teams do not match official identity")
    frozen=iso_utc(model["frozen_at_utc"],"model frozen")
    kickoff=iso_utc(snapshot.get("kickoff_utc"),"kickoff")
    lock=iso_utc(snapshot.get("fst_lock_timestamp_utc"),"fst lock")
    captured=iso_utc(snapshot.get("snapshot_captured_utc"),"capture")
    observed=iso_utc(snapshot.get("features_observed_at_utc"),"observed")
    source_asof=iso_utc(snapshot.get("feature_source_asof_utc"),"source asof")
    if not (frozen <= observed <= captured <= lock < kickoff):
        raise ValueError("Snapshot is not independently frozen before official lock/kickoff")
    if source_asof>observed or source_asof>lock:
        raise ValueError("Feature source is from the future")
    if (lock-captured).total_seconds() > 120*60 or (captured-source_asof).total_seconds()>120*60:
        raise ValueError("Stale feature source relative to official lock")
    if snapshot.get("fst_lock_status")!="LOCKED" or snapshot.get("fst_candidate_id")!=PRODUCTION_ID:
        raise ValueError("Frozen official F-ST lock identity required")
    market=number(snapshot.get("market_home_prob"),"market",prob=True)
    fst=number(snapshot.get("fst_home_prob"),"locked F-ST",prob=True)
    hexsha(snapshot.get("raw_source_sha256"),"raw source")
    hexsha(snapshot.get("schedule_source_sha256"),"schedule source")
    if snapshot.get("team_state_builder_id")!="EARLY-STATE-SHRINKAGE-V1":
        raise ValueError("Unregistered team state builder")
    if snapshot.get("upstream_completion_audit_passed") is not True:
        raise ValueError("Prior-game completeness audit unavailable")
    if snapshot.get("outcome") is not None:
        raise ValueError("Pregame snapshot may not contain labels/outcomes")
    features=derive_features(snapshot,cutoff=lock)
    x=np.asarray(features,dtype=float)
    if not np.isfinite(x).all() or x[2]<0 or x[2]>1:
        raise ValueError("State features invalid")
    t=np.asarray(model["theta"],dtype=float)
    z=(x-np.asarray(model["means"],dtype=float))/np.asarray(model["stds"],dtype=float)
    eta=float(logit(np.clip(market,EPS,1-EPS))+t[0]+z@t[1:])
    probability=float(np.clip(expit(eta),EPS,1-EPS))
    out={
        "contract":CONTRACT_ID, "candidate_id":CANDIDATE_ID,
        "game_id":game_id,"season":season,"week":week,"home_team":home,"away_team":away,
        "kickoff_utc":snapshot["kickoff_utc"],"fst_lock_timestamp_utc":snapshot["fst_lock_timestamp_utc"],
        "snapshot_captured_utc":snapshot["snapshot_captured_utc"],
        "source_observed_utc":snapshot["features_observed_at_utc"],
        "source_sha256":snapshot["raw_source_sha256"],
        "schedule_sha256":snapshot["schedule_source_sha256"],
        "input_snapshot_sha256":canonical_hash(snapshot),
        "frozen_model_sha256":canonical_hash(model),
        "fst_candidate_id":PRODUCTION_ID,
        "fst_home_prob":fst,"market_home_prob":market,
        "candidate_home_prob":probability,
        "candidate_pick":home if probability>=.5 else away,
        "fst_pick":home if fst>=.5 else away,
        "frozen_features":dict(zip(FEATURES,features)),
        "production_changed":False,"promotion_authorized":False,
        "completed_2026_outcomes_used_in_training":0,
    }
    return out


def write_once(path: Path, record: dict) -> str:
    """O_EXCL prevents silent edits or backfills to a saved prediction."""
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    body=json.dumps(record,indent=2,sort_keys=True,allow_nan=False)+"\n"
    with path.open("x",encoding="utf-8") as f:
        f.write(body)
    return hashlib.sha256(body.encode()).hexdigest()
