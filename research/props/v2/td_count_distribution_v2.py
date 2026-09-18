from __future__ import annotations

"""Team offensive-TD count distribution study for Props 2.0.

Poisson and negative-binomial forecasts share the same team-specific expected count. The only
challenged assumption is dispersion. This isolates count-family value before altering player TD
allocation.
"""

import math
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson

CONTRACT_VERSION="levline-props-v2-td-count-distribution-v0.1.0"
PRIOR_TEAM_GAMES=8.0
MAX_COUNT=10


class TDDistributionError(ValueError):
    pass


def _team_means(train:pd.DataFrame)->tuple[dict[str,float],float]:
    league=float(train["offensive_tds"].mean())
    grouped=train.groupby("team")["offensive_tds"].agg(["sum","count"])
    means={
        str(team):float((row["sum"]+PRIOR_TEAM_GAMES*league)/(row["count"]+PRIOR_TEAM_GAMES))
        for team,row in grouped.iterrows()
    }
    return means,league


def _fit_overdispersion(train:pd.DataFrame,means:dict[str,float],league:float)->float:
    y=train["offensive_tds"].to_numpy(dtype=float)
    mu=np.asarray([means.get(str(team),league) for team in train["team"]],dtype=float)
    numerator=float(np.sum(np.square(y-mu)-mu))
    denominator=float(np.sum(np.square(mu)))
    return max(numerator/max(denominator,1e-12),0.0)


def _nb_params(mu:float,alpha:float)->tuple[float,float] | None:
    if alpha<=1e-12:
        return None
    size=1.0/alpha
    p=size/(size+mu)
    return size,p


def _pmf(mu:float,alpha:float,model:str)->np.ndarray:
    ks=np.arange(MAX_COUNT+1)
    if model=="poisson":
        probs=poisson.pmf(ks,mu)
    elif model=="negative_binomial":
        params=_nb_params(mu,alpha)
        if params is None:
            probs=poisson.pmf(ks,mu)
        else:
            size,p=params
            probs=nbinom.pmf(ks,size,p)
    else:
        raise TDDistributionError(model)
    # Last bucket includes MAX_COUNT+.
    tail=max(0.0,1.0-float(np.sum(probs[:-1])))
    out=np.asarray(probs,dtype=float)
    out[-1]=tail
    out=out/max(float(out.sum()),1e-15)
    return out


def _crps_discrete(probs:np.ndarray,y:int)->float:
    cdf=np.cumsum(probs)
    # categories 0..MAX_COUNT-1 and MAX_COUNT+
    threshold=np.arange(len(probs))
    obs=(threshold>=min(int(y),MAX_COUNT)).astype(float)
    return float(np.sum(np.square(cdf-obs)))


def _score(probs:np.ndarray,y:int)->tuple[float,float,float]:
    idx=min(max(int(y),0),MAX_COUNT)
    p=max(float(probs[idx]),1e-15)
    target=np.zeros_like(probs); target[idx]=1.0
    log_loss=-math.log(p)
    brier=float(np.sum(np.square(probs-target)))
    crps=_crps_discrete(probs,y)
    return log_loss,brier,crps


def evaluate_td_count_families(team_games:pd.DataFrame)->dict[str,Any]:
    required={"season","game_id","team","offensive_tds"}
    missing=required-set(team_games.columns)
    if missing:
        raise TDDistributionError(f"team_games missing {sorted(missing)}")
    work=team_games.copy()
    work["season"]=pd.to_numeric(work["season"],errors="coerce")
    work["offensive_tds"]=pd.to_numeric(work["offensive_tds"],errors="coerce")
    work=work[
        work["season"].notna() & work["offensive_tds"].notna() &
        work["offensive_tds"].ge(0)
    ].copy()
    results={}
    all_rows=[]
    for season in (2024,2025):
        train=work[work["season"]<season].copy()
        test=work[work["season"].eq(season)].copy()
        if train.empty or test.empty:
            continue
        means,league=_team_means(train)
        alpha=_fit_overdispersion(train,means,league)
        scores={m:{"log_loss":[],"brier":[],"crps":[]} for m in ("poisson","negative_binomial")}
        for row in test.itertuples(index=False):
            mu=means.get(str(row.team),league)
            y=int(row.offensive_tds)
            for model in scores:
                ll,br,cr=_score(_pmf(mu,alpha,model),y)
                scores[model]["log_loss"].append(ll)
                scores[model]["brier"].append(br)
                scores[model]["crps"].append(cr)
            all_rows.append((season,str(row.game_id),str(row.team),y,mu,alpha))
        summary={
            "n":int(len(test)),
            "league_training_mean":league,
            "negative_binomial_alpha":alpha,
        }
        for model,metrics in scores.items():
            summary[model]={k:float(np.mean(v)) for k,v in metrics.items()}
        summary["negative_binomial_minus_poisson"]={
            k:summary["negative_binomial"][k]-summary["poisson"][k]
            for k in ("log_loss","brier","crps")
        }
        results[str(season)]=summary
    if not results:
        raise TDDistributionError("no chronological evaluation seasons")

    total=sum(v["n"] for v in results.values())
    aggregate={}
    for model in ("poisson","negative_binomial"):
        aggregate[model]={
            metric:float(sum(v["n"]*v[model][metric] for v in results.values())/total)
            for metric in ("log_loss","brier","crps")
        }
    aggregate["n"]=int(total)
    aggregate["negative_binomial_minus_poisson"]={
        metric:aggregate["negative_binomial"][metric]-aggregate["poisson"][metric]
        for metric in ("log_loss","brier","crps")
    }
    return {
        "contract_version":CONTRACT_VERSION,
        "research_only":True,
        "production_authorized":False,
        "seasons":results,
        "aggregate":aggregate,
        "completed_2026_outcomes_used":0,
        "player_td_outcomes_used_for_selection":0,
    }
