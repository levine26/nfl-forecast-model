from __future__ import annotations

"""Event-level yardage distribution diagnostics for Props 2.0.

This module tests distribution shape, not player skill. Candidate empirical mixtures and the
nonnegative Gamma baseline receive the same historical event population. The goal is to determine
whether a support-correct event family is warranted before changing the coherent game simulator.
"""

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.stats import gamma as gamma_dist

CONTRACT_VERSION="levline-props-v2-event-distribution-v0.1.0"
RANDOM_STATE=20260918
SAMPLE_SIZE=4096
SUPPORTED_POSITIONS=frozenset({"QB","RB","WR","TE"})


class DistributionStudyError(ValueError):
    pass


@dataclass(frozen=True)
class SampleForecast:
    sample: np.ndarray
    mean: float
    q05: float
    q25: float
    q50: float
    q75: float
    q95: float


def _finite_array(values:Sequence[float])->np.ndarray:
    arr=np.asarray(values,dtype=float)
    return arr[np.isfinite(arr)]


def _crps_from_sample(sample:np.ndarray,y:float)->float:
    x=np.sort(_finite_array(sample))
    if x.size==0:
        raise DistributionStudyError("CRPS sample is empty")
    first=float(np.mean(np.abs(x-float(y))))
    # E|X-X'| over the empirical distribution, O(n log n).
    n=x.size
    coeff=2*np.arange(1,n+1)-n-1
    pair=float(2.0*np.sum(coeff*x)/(n*n))
    return first-0.5*pair


def _sample_summary(sample:np.ndarray)->SampleForecast:
    x=_finite_array(sample)
    if x.size==0:
        raise DistributionStudyError("forecast sample is empty")
    q=np.quantile(x,[0.05,0.25,0.50,0.75,0.95])
    return SampleForecast(
        sample=x,
        mean=float(np.mean(x)),
        q05=float(q[0]),q25=float(q[1]),q50=float(q[2]),q75=float(q[3]),q95=float(q[4]),
    )


def _gamma_sample(values:np.ndarray,rng:np.random.Generator)->np.ndarray:
    """Moment-matched nonnegative Gamma, mirroring the simulator's support restriction."""
    x=_finite_array(values)
    if x.size<2:
        raise DistributionStudyError("insufficient Gamma training events")
    mean=max(float(np.mean(x)),1e-6)
    sd=max(float(np.std(x,ddof=1)),1e-3)
    shape=max((mean/sd)**2,1e-4)
    scale=max(sd*sd/mean,1e-6)
    return rng.gamma(shape=shape,scale=scale,size=SAMPLE_SIZE)


def _empirical_sample(
    values:np.ndarray,
    league_values:np.ndarray,
    rng:np.random.Generator,
    *,
    position_weight:float=0.90,
)->np.ndarray:
    x=_finite_array(values)
    league=_finite_array(league_values)
    if x.size<10 or league.size<10:
        raise DistributionStudyError("insufficient empirical training events")
    choose_position=rng.random(SAMPLE_SIZE)<float(position_weight)
    out=np.empty(SAMPLE_SIZE,dtype=float)
    out[choose_position]=rng.choice(x,size=int(choose_position.sum()),replace=True)
    out[~choose_position]=rng.choice(league,size=int((~choose_position).sum()),replace=True)
    return out


def _bin_spec(kind:str)->tuple[list[float],list[str]]:
    if kind=="rushing":
        return [-math.inf,-0.5,0.5,2.5,9.5,math.inf],[
            "negative","zero","short_1_2","normal_3_9","explosive_10_plus"
        ]
    if kind=="receiving":
        return [-math.inf,0.5,7.5,19.5,math.inf],[
            "nonpositive","short_1_7","intermediate_8_19","explosive_20_plus"
        ]
    raise DistributionStudyError(f"unsupported kind: {kind}")


def _bin_probabilities(sample:np.ndarray,kind:str)->np.ndarray:
    edges,_=_bin_spec(kind)
    x=_finite_array(sample)
    counts,_=np.histogram(x,bins=np.asarray(edges,dtype=float))
    probs=counts.astype(float)/max(float(counts.sum()),1.0)
    return probs


def _bin_index(y:float,kind:str)->int:
    edges,_=_bin_spec(kind)
    # right=False semantics: [edge_i, edge_{i+1})
    idx=int(np.searchsorted(np.asarray(edges[1:-1]),float(y),side="right"))
    return idx


def _multiclass_brier(probabilities:np.ndarray,index:int)->float:
    target=np.zeros_like(probabilities,dtype=float)
    target[index]=1.0
    return float(np.sum(np.square(probabilities-target)))


def evaluate_distribution_pair(
    train_position:Sequence[float],
    train_league:Sequence[float],
    test:Sequence[float],
    *,
    kind:str,
    seed:int=RANDOM_STATE,
)->dict[str,Any]:
    pos=_finite_array(train_position)
    league=_finite_array(train_league)
    observed=_finite_array(test)
    if observed.size==0:
        raise DistributionStudyError("test events are empty")
    rng=np.random.default_rng(int(seed))
    empirical=_sample_summary(_empirical_sample(pos,league,rng))
    gamma=_sample_summary(_gamma_sample(pos,rng))
    forecasts={"empirical_mixture":empirical,"nonnegative_gamma":gamma}
    result={}
    for name,forecast in forecasts.items():
        probs=_bin_probabilities(forecast.sample,kind)
        crps=[]
        log_losses=[]
        briers=[]
        cover50=[]
        cover90=[]
        for y in observed:
            idx=_bin_index(float(y),kind)
            p=max(float(probs[idx]),1e-12)
            crps.append(_crps_from_sample(forecast.sample,float(y)))
            log_losses.append(-math.log(p))
            briers.append(_multiclass_brier(probs,idx))
            cover50.append(float(forecast.q25<=y<=forecast.q75))
            cover90.append(float(forecast.q05<=y<=forecast.q95))
        result[name]={
            "crps":float(np.mean(crps)),
            "bin_log_loss":float(np.mean(log_losses)),
            "bin_brier":float(np.mean(briers)),
            "interval_50_coverage":float(np.mean(cover50)),
            "interval_90_coverage":float(np.mean(cover90)),
            "forecast_mean":forecast.mean,
            "forecast_quantiles":{
                "q05":forecast.q05,"q25":forecast.q25,"q50":forecast.q50,
                "q75":forecast.q75,"q95":forecast.q95,
            },
            "bin_probabilities":probs.tolist(),
        }
    result["n_test"]=int(observed.size)
    result["negative_or_zero_rate"]=float(np.mean(observed<=0))
    result["negative_rate"]=float(np.mean(observed<0))
    result["empirical_minus_gamma"]={
        "crps":result["empirical_mixture"]["crps"]-result["nonnegative_gamma"]["crps"],
        "bin_log_loss":result["empirical_mixture"]["bin_log_loss"]-result["nonnegative_gamma"]["bin_log_loss"],
        "bin_brier":result["empirical_mixture"]["bin_brier"]-result["nonnegative_gamma"]["bin_brier"],
    }
    return result


def evaluate_rolling_event_distributions(events:pd.DataFrame)->dict[str,Any]:
    required={"season","event_kind","position","yards"}
    missing=required-set(events.columns)
    if missing:
        raise DistributionStudyError(f"events missing fields: {sorted(missing)}")
    work=events.copy()
    work["season"]=pd.to_numeric(work["season"],errors="coerce")
    work["yards"]=pd.to_numeric(work["yards"],errors="coerce")
    work["position"]=work["position"].astype("string").fillna("").str.upper().str.strip()
    work=work[
        work["season"].notna() & work["yards"].notna() &
        work["event_kind"].isin({"rushing","receiving"}) &
        work["position"].isin(SUPPORTED_POSITIONS)
    ].copy()
    rows={}
    for season in (2024,2025):
        train=work[work["season"]<season]
        test=work[work["season"].eq(season)]
        for kind in ("rushing","receiving"):
            league=train[train["event_kind"].eq(kind)]["yards"].to_numpy(dtype=float)
            positions=sorted(test[test["event_kind"].eq(kind)]["position"].unique().tolist())
            for position in positions:
                train_pos=train[
                    train["event_kind"].eq(kind) & train["position"].eq(position)
                ]["yards"].to_numpy(dtype=float)
                test_pos=test[
                    test["event_kind"].eq(kind) & test["position"].eq(position)
                ]["yards"].to_numpy(dtype=float)
                if len(train_pos)<50 or len(test_pos)<20:
                    continue
                key=f"{season}|{kind}|{position}"
                rows[key]=evaluate_distribution_pair(
                    train_pos,league,test_pos,kind=kind,
                    seed=RANDOM_STATE+season+sum(map(ord,position+kind)),
                )
    if not rows:
        raise DistributionStudyError("no evaluable season/kind/position cells")
    weighted={}
    for model in ("empirical_mixture","nonnegative_gamma"):
        total=sum(row["n_test"] for row in rows.values())
        weighted[model]={
            metric:float(sum(row["n_test"]*row[model][metric] for row in rows.values())/total)
            for metric in ("crps","bin_log_loss","bin_brier","interval_50_coverage","interval_90_coverage")
        }
    total=sum(row["n_test"] for row in rows.values())
    weighted["n_test"]=int(total)
    weighted["negative_event_count"]=int(
        sum(round(row["negative_rate"]*row["n_test"]) for row in rows.values())
    )
    weighted["empirical_minus_gamma"]={
        metric:weighted["empirical_mixture"][metric]-weighted["nonnegative_gamma"][metric]
        for metric in ("crps","bin_log_loss","bin_brier")
    }
    return {
        "contract_version":CONTRACT_VERSION,
        "research_only":True,
        "production_authorized":False,
        "cells":rows,
        "aggregate":weighted,
        "game_outcomes_used_for_model_selection":0,
        "completed_2026_outcomes_used":0,
    }
