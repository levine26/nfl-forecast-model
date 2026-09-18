from __future__ import annotations

"""Signed empirical event-yard distribution challenger for Props 2.0.

This is a component-isolation study. Evaluation conditions on the realized event count solely to
compare conditional yardage distributions. It is not a pregame prop forecast and cannot authorize
production.
"""

from dataclasses import dataclass, asdict
import hashlib
import math
from typing import Any

import numpy as np
import pandas as pd

CONTRACT_VERSION="levline-props-v2-signed-event-distribution-v0.1.0"
SUPPORTED_POSITIONS=frozenset({"QB","RB","WR","TE"})
EVENT_TYPES=("rushing","receiving")
PRIOR_STRENGTH={"rushing":65.0,"receiving":45.0}
MIN_EVENT_SD=1.0
SIMULATIONS=5000
EPS=1e-9


class SignedDistributionError(ValueError):
    pass


@dataclass(frozen=True)
class EventPrior:
    event_type: str
    position: str
    trained_through_season: int
    n_events: int
    mean_yards: float
    sd_yards: float
    negative_event_rate: float
    explosive_event_rate: float

    def to_dict(self)->dict[str,Any]:
        return asdict(self)


def empirical_crps(samples: np.ndarray, observation: float)->float:
    values=np.asarray(samples,dtype=float)
    values=values[np.isfinite(values)]
    if values.size==0:
        raise SignedDistributionError("CRPS requires finite samples")
    y=float(observation)
    ordered=np.sort(values)
    n=ordered.size
    first=float(np.mean(np.abs(ordered-y)))
    weights=2.0*np.arange(n,dtype=float)-float(n)+1.0
    half_pairwise=float(np.dot(weights,ordered)/float(n*n))
    return float(max(0.0,first-half_pairwise))


def interval_score(samples: np.ndarray, observation: float, *, level: float=0.80)->tuple[float,bool,float]:
    values=np.asarray(samples,dtype=float)
    alpha=1.0-float(level)
    lo=float(np.quantile(values,alpha/2.0))
    hi=float(np.quantile(values,1.0-alpha/2.0))
    y=float(observation)
    penalty=0.0
    if y<lo:
        penalty=(2.0/alpha)*(lo-y)
    elif y>hi:
        penalty=(2.0/alpha)*(y-hi)
    return float((hi-lo)+penalty),bool(lo<=y<=hi),float(hi-lo)


def build_event_rows(
    pbp: pd.DataFrame,
    player_positions: dict[str,str],
)->pd.DataFrame:
    required={"game_id","season","week"}
    missing=required-set(pbp.columns)
    if missing:
        raise SignedDistributionError(f"PBP missing columns: {sorted(missing)}")

    work=pbp.copy()
    pass_attempt=pd.to_numeric(work.get("pass_attempt",0),errors="coerce").fillna(0).eq(1)
    complete=pd.to_numeric(work.get("complete_pass",0),errors="coerce").fillna(0).eq(1)
    rush=pd.to_numeric(work.get("rush_attempt",0),errors="coerce").fillna(0).eq(1)

    rusher_col=next((c for c in ("rusher_player_id","rusher_id") if c in work.columns),None)
    receiver_col=next((c for c in ("receiver_player_id","receiver_id") if c in work.columns),None)
    if rusher_col is None or receiver_col is None:
        raise SignedDistributionError("PBP missing rusher/receiver stable IDs")

    yard_col=next((c for c in ("yards_gained","receiving_yards") if c in work.columns),None)
    if yard_col is None:
        raise SignedDistributionError("PBP missing event yardage")
    yards=pd.to_numeric(work[yard_col],errors="coerce")

    pieces=[]
    rusher=work[rusher_col].astype("string").fillna("").str.strip()
    rmask=rush & rusher.ne("") & yards.notna()
    if rmask.any():
        frame=work.loc[rmask,["game_id","season","week"]].copy()
        frame["player_id"]=rusher.loc[rmask].astype(str).to_numpy()
        frame["event_type"]="rushing"
        frame["yards"]=yards.loc[rmask].astype(float).to_numpy()
        pieces.append(frame)

    receiver=work[receiver_col].astype("string").fillna("").str.strip()
    recmask=pass_attempt & complete & receiver.ne("") & yards.notna()
    if recmask.any():
        frame=work.loc[recmask,["game_id","season","week"]].copy()
        frame["player_id"]=receiver.loc[recmask].astype(str).to_numpy()
        frame["event_type"]="receiving"
        frame["yards"]=yards.loc[recmask].astype(float).to_numpy()
        pieces.append(frame)

    if not pieces:
        raise SignedDistributionError("no supported event rows")
    out=pd.concat(pieces,ignore_index=True)
    out["season"]=pd.to_numeric(out["season"],errors="coerce").astype(int)
    out["week"]=pd.to_numeric(out["week"],errors="coerce").astype(int)
    out["position"]=out["player_id"].map(player_positions).astype("string").fillna("").str.upper()
    out=out[out["position"].isin(SUPPORTED_POSITIONS)].copy()
    return out.reset_index(drop=True)


def fit_event_priors(
    events: pd.DataFrame,
    *,
    trained_through_season: int,
)->dict[tuple[str,str],EventPrior]:
    train=events[events["season"].astype(int).le(int(trained_through_season))].copy()
    if train.empty:
        raise SignedDistributionError("empty event-prior training set")
    priors={}
    for event_type in EVENT_TYPES:
        for position in sorted(SUPPORTED_POSITIONS):
            rows=train[
                train["event_type"].eq(event_type)
                & train["position"].eq(position)
            ]
            if rows.empty:
                continue
            vals=pd.to_numeric(rows["yards"],errors="coerce").dropna().to_numpy(dtype=float)
            if len(vals)==0:
                continue
            priors[(event_type,position)]=EventPrior(
                event_type=event_type,
                position=position,
                trained_through_season=int(trained_through_season),
                n_events=int(len(vals)),
                mean_yards=float(np.mean(vals)),
                sd_yards=float(max(np.std(vals,ddof=1) if len(vals)>1 else 0.0,MIN_EVENT_SD)),
                negative_event_rate=float(np.mean(vals<0.0)),
                explosive_event_rate=float(np.mean(vals>=20.0)),
            )
    return priors


def _prior_player_events(
    events: pd.DataFrame,
    *,
    player_id: str,
    event_type: str,
    season: int,
    week: int,
)->np.ndarray:
    mask=(
        events["player_id"].astype(str).eq(str(player_id))
        & events["event_type"].eq(event_type)
        & (
            events["season"].astype(int).lt(int(season))
            | (
                events["season"].astype(int).eq(int(season))
                & events["week"].astype(int).lt(int(week))
            )
        )
    )
    return pd.to_numeric(events.loc[mask,"yards"],errors="coerce").dropna().to_numpy(dtype=float)


def shrunken_player_mean(
    prior_player_events: np.ndarray,
    position_prior_mean: float,
    *,
    event_type: str,
)->float:
    vals=np.asarray(prior_player_events,dtype=float)
    vals=vals[np.isfinite(vals)]
    k=float(PRIOR_STRENGTH[event_type])
    return float((vals.sum()+k*float(position_prior_mean))/(len(vals)+k))


def _seed(*parts: Any)->int:
    digest=hashlib.sha256("|".join(map(str,parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8],"big")%(2**32-1)


def gamma_aggregate_samples(
    count: int,
    mean_per_event: float,
    event_sd: float,
    *,
    simulations: int,
    seed: int,
)->np.ndarray:
    if count<=0:
        return np.zeros(simulations,dtype=float)
    mean=max(float(mean_per_event),EPS)
    sd=max(float(event_sd),MIN_EVENT_SD)
    shape_per=(mean/sd)**2
    aggregate_shape=max(float(count)*shape_per,EPS)
    scale=(sd*sd)/mean
    rng=np.random.default_rng(seed)
    return rng.gamma(aggregate_shape,scale,size=int(simulations))


def signed_empirical_aggregate_samples(
    count: int,
    mean_per_event: float,
    training_event_yards: np.ndarray,
    *,
    simulations: int,
    seed: int,
)->np.ndarray:
    if count<=0:
        return np.zeros(simulations,dtype=float)
    vals=np.asarray(training_event_yards,dtype=float)
    vals=vals[np.isfinite(vals)]
    if len(vals)<2:
        raise SignedDistributionError("signed empirical distribution requires >=2 training events")
    residuals=vals-float(vals.mean())
    rng=np.random.default_rng(seed)
    draws=rng.choice(residuals,size=(int(simulations),int(count)),replace=True)
    return draws.sum(axis=1)+float(count)*float(mean_per_event)


def evaluate_component_season(
    events: pd.DataFrame,
    *,
    evaluation_season: int,
    simulations: int=SIMULATIONS,
)->tuple[pd.DataFrame,dict[str,Any]]:
    train_end=int(evaluation_season)-1
    priors=fit_event_priors(events,trained_through_season=train_end)
    train=events[events["season"].astype(int).le(train_end)].copy()
    test=events[events["season"].astype(int).eq(int(evaluation_season))].copy()
    if test.empty:
        raise SignedDistributionError(f"no events for evaluation season {evaluation_season}")

    results=[]
    group_cols=["game_id","season","week","player_id","position","event_type"]
    for key,group in test.groupby(group_cols,sort=False):
        game_id,season,week,player_id,position,event_type=key
        prior=priors.get((str(event_type),str(position)))
        if prior is None:
            continue
        count=int(len(group))
        actual=float(pd.to_numeric(group["yards"],errors="coerce").sum())
        player_prior=_prior_player_events(
            events,
            player_id=str(player_id),
            event_type=str(event_type),
            season=int(season),
            week=int(week),
        )
        mean=shrunken_player_mean(
            player_prior,prior.mean_yards,event_type=str(event_type)
        )
        source_events=pd.to_numeric(
            train.loc[
                train["event_type"].eq(event_type)
                & train["position"].eq(position),
                "yards"
            ],
            errors="coerce",
        ).dropna().to_numpy(dtype=float)
        seed=_seed(CONTRACT_VERSION,game_id,player_id,event_type,season,week)
        gamma=gamma_aggregate_samples(
            count,mean,prior.sd_yards,simulations=simulations,seed=seed
        )
        signed=signed_empirical_aggregate_samples(
            count,mean,source_events,simulations=simulations,seed=seed+1
        )
        g_crps=empirical_crps(gamma,actual)
        s_crps=empirical_crps(signed,actual)
        g_is,g_cov,g_width=interval_score(gamma,actual)
        s_is,s_cov,s_width=interval_score(signed,actual)
        results.append({
            "contract_version":CONTRACT_VERSION,
            "game_id":str(game_id),
            "season":int(season),
            "week":int(week),
            "player_id":str(player_id),
            "position":str(position),
            "event_type":str(event_type),
            "actual_event_count":count,
            "actual_total_yards":actual,
            "pregame_shrunken_mean_per_event":mean,
            "prior_player_event_count":int(len(player_prior)),
            "gamma_crps":g_crps,
            "signed_crps":s_crps,
            "signed_minus_gamma_crps":s_crps-g_crps,
            "gamma_interval_score_80":g_is,
            "signed_interval_score_80":s_is,
            "gamma_covered_80":g_cov,
            "signed_covered_80":s_cov,
            "gamma_interval_width_80":g_width,
            "signed_interval_width_80":s_width,
            "training_negative_event_rate":prior.negative_event_rate,
            "training_explosive_event_rate":prior.explosive_event_rate,
            "conditioned_on_actual_event_count":True,
            "pregame_prop_forecast":False,
        })
    scored=pd.DataFrame(results)
    if scored.empty:
        raise SignedDistributionError("no scorable player-game component rows")
    summary={
        "contract_version":CONTRACT_VERSION,
        "evaluation_season":int(evaluation_season),
        "trained_through_season":train_end,
        "n":int(len(scored)),
        "unique_games":int(scored["game_id"].nunique()),
        "gamma_crps":float(scored["gamma_crps"].mean()),
        "signed_crps":float(scored["signed_crps"].mean()),
        "signed_minus_gamma_crps":float(scored["signed_minus_gamma_crps"].mean()),
        "gamma_interval_score_80":float(scored["gamma_interval_score_80"].mean()),
        "signed_interval_score_80":float(scored["signed_interval_score_80"].mean()),
        "gamma_coverage_80":float(scored["gamma_covered_80"].astype(float).mean()),
        "signed_coverage_80":float(scored["signed_covered_80"].astype(float).mean()),
        "by_event_type":{
            event:{
                "n":int(len(part)),
                "gamma_crps":float(part["gamma_crps"].mean()),
                "signed_crps":float(part["signed_crps"].mean()),
                "signed_minus_gamma_crps":float(part["signed_minus_gamma_crps"].mean()),
                "gamma_coverage_80":float(part["gamma_covered_80"].astype(float).mean()),
                "signed_coverage_80":float(part["signed_covered_80"].astype(float).mean()),
            }
            for event,part in scored.groupby("event_type",sort=True)
        },
        "component_isolation_only":True,
        "conditioned_on_actual_event_count":True,
        "pregame_prop_forecast":False,
        "prop_outcomes_used_for_fit":0,
        "completed_2026_outcomes_used":0,
        "production_authorized":False,
    }
    return scored,summary
