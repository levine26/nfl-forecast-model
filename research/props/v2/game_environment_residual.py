from __future__ import annotations

"""Low-dimensional game-environment residuals for Props opportunity forecasting.

This component is evaluated on team offensive plays and dropback rate only. Player-prop outcomes,
sportsbook prop outcomes, Fair-Line errors and completed 2026 results are prohibited from fitting.
"""

from dataclasses import dataclass, asdict
import math
from typing import Any, Iterable

import numpy as np
import pandas as pd

CONTRACT_VERSION="levline-props-v2-game-environment-v0.1.0"
RIDGE_L2=10.0
EPS=1e-4
FEATURES_PLAYS=("game_total","abs_team_spread","opponent_base_plays")
FEATURES_DROPBACK=("team_spread","game_total","abs_team_spread")
BOOTSTRAP_SEED=20260918


class GameEnvironmentError(ValueError):
    pass


@dataclass(frozen=True)
class RidgeResidualFit:
    target: str
    features: tuple[str,...]
    means: dict[str,float]
    scales: dict[str,float]
    intercept: float
    coefficients: dict[str,float]
    l2: float
    training_rows: int

    def to_dict(self)->dict[str,Any]:
        value=asdict(self)
        value["features"]=list(self.features)
        return value


def _logit(p: float)->float:
    x=float(np.clip(float(p),EPS,1.0-EPS))
    return math.log(x/(1.0-x))


def _inv_logit(x: float)->float:
    if x>=0:
        z=math.exp(-x)
        return 1.0/(1.0+z)
    z=math.exp(x)
    return z/(1.0+z)


def _fit_ridge(frame: pd.DataFrame, *, target: str, features: tuple[str,...])->RidgeResidualFit:
    needed=set(features)|{target}
    missing=needed-set(frame.columns)
    if missing:
        raise GameEnvironmentError(f"fit missing columns: {sorted(missing)}")
    work=frame[list(features)+[target]].apply(pd.to_numeric,errors="coerce").dropna()
    if len(work)<50:
        raise GameEnvironmentError(f"insufficient training rows for {target}: {len(work)}")

    means={f:float(work[f].mean()) for f in features}
    scales={}
    Xcols=[]
    for f in features:
        sd=float(work[f].std(ddof=0))
        if not math.isfinite(sd) or sd<1e-9:
            sd=1.0
        scales[f]=sd
        Xcols.append((work[f].to_numpy(dtype=float)-means[f])/sd)
    X=np.column_stack([np.ones(len(work)),*Xcols])
    y=work[target].to_numpy(dtype=float)
    penalty=np.eye(X.shape[1],dtype=float)*RIDGE_L2
    penalty[0,0]=0.0
    beta=np.linalg.solve(X.T@X+penalty,X.T@y)
    return RidgeResidualFit(
        target=target,
        features=features,
        means=means,
        scales=scales,
        intercept=float(beta[0]),
        coefficients={f:float(beta[i+1]) for i,f in enumerate(features)},
        l2=RIDGE_L2,
        training_rows=int(len(work)),
    )


def _predict_residual(row: pd.Series, fit: RidgeResidualFit)->float:
    value=float(fit.intercept)
    for feature in fit.features:
        raw=float(row[feature])
        value += fit.coefficients[feature]*(
            (raw-fit.means[feature])/fit.scales[feature]
        )
    return float(value)


def prepare_environment_rows(diagnostics: pd.DataFrame, market_state: pd.DataFrame)->pd.DataFrame:
    """Join one-step-ahead V1 team-volume diagnostics to pregame game spread/total state."""
    d=diagnostics.copy()
    m=market_state.copy()
    required_d={
        "game_id","season","week","team","pred_team_plays_mean","actual_team_plays",
        "pred_dropback_rate_mean","actual_dropback_rate",
    }
    required_m={"game_id","team","team_spread","game_total"}
    if required_d-set(d.columns):
        raise GameEnvironmentError(f"diagnostics missing {sorted(required_d-set(d.columns))}")
    if required_m-set(m.columns):
        raise GameEnvironmentError(f"market state missing {sorted(required_m-set(m.columns))}")

    d["team"]=d["team"].astype(str).str.upper().replace({"JAC":"JAX","LA":"LAR","WSH":"WAS"})
    m["team"]=m["team"].astype(str).str.upper().replace({"JAC":"JAX","LA":"LAR","WSH":"WAS"})
    m=m.drop_duplicates(["game_id","team"],keep="last")
    out=d.merge(
        m[["game_id","team","team_spread","game_total"]],
        on=["game_id","team"],how="inner",validate="many_to_one",
    )
    opp=out[["game_id","team","pred_team_plays_mean"]].copy()
    teams=out[["game_id","team"]].copy()
    # Self-join by game and remove same team; NFL game should resolve exactly one opponent.
    pairs=teams.merge(opp,on="game_id",suffixes=("_self","_opp"))
    pairs=pairs[pairs["team_self"].ne(pairs["team_opp"])]
    counts=pairs.groupby(["game_id","team_self"]).size()
    if len(counts) and int(counts.max())>1:
        raise GameEnvironmentError("ambiguous opponent team diagnostics")
    opp_map=pairs.set_index(["game_id","team_self"])["pred_team_plays_mean"].to_dict()
    out["opponent_base_plays"]=[
        opp_map.get((g,t),np.nan) for g,t in zip(out["game_id"],out["team"])
    ]
    out["abs_team_spread"]=pd.to_numeric(out["team_spread"],errors="coerce").abs()
    out["play_residual"]=(
        pd.to_numeric(out["actual_team_plays"],errors="coerce")
        - pd.to_numeric(out["pred_team_plays_mean"],errors="coerce")
    )
    actual_rate=pd.to_numeric(out["actual_dropback_rate"],errors="coerce")
    pred_rate=pd.to_numeric(out["pred_dropback_rate_mean"],errors="coerce")
    out["dropback_logit_residual"]=[
        _logit(a)-_logit(p) if pd.notna(a) and pd.notna(p) else np.nan
        for a,p in zip(actual_rate,pred_rate)
    ]
    return out


def fit_environment_residuals(
    rows: pd.DataFrame,
    *,
    trained_through_season: int,
)->dict[str,RidgeResidualFit]:
    train=rows[pd.to_numeric(rows["season"],errors="coerce").le(int(trained_through_season))].copy()
    if train.empty:
        raise GameEnvironmentError("empty season-forward training set")
    return {
        "plays":_fit_ridge(train,target="play_residual",features=FEATURES_PLAYS),
        "dropback":_fit_ridge(train,target="dropback_logit_residual",features=FEATURES_DROPBACK),
    }


def evaluate_environment_season(
    rows: pd.DataFrame,
    *,
    evaluation_season: int,
)->tuple[pd.DataFrame,dict[str,Any]]:
    train_end=int(evaluation_season)-1
    fits=fit_environment_residuals(rows,trained_through_season=train_end)
    test=rows[pd.to_numeric(rows["season"],errors="coerce").eq(int(evaluation_season))].copy()
    required=[
        *FEATURES_PLAYS,*FEATURES_DROPBACK,
        "pred_team_plays_mean","actual_team_plays","pred_dropback_rate_mean","actual_dropback_rate"
    ]
    test=test.dropna(subset=list(dict.fromkeys(required))).copy()
    if test.empty:
        raise GameEnvironmentError(f"no evaluation rows for {evaluation_season}")

    test["challenger_team_plays"]=[
        max(1.0,float(row.pred_team_plays_mean)+_predict_residual(row,fits["plays"]))
        for _,row in test.iterrows()
    ]
    test["challenger_dropback_rate"]=[
        _inv_logit(_logit(float(row.pred_dropback_rate_mean))+_predict_residual(row,fits["dropback"]))
        for _,row in test.iterrows()
    ]
    test["baseline_play_abs_error"]=(
        test["pred_team_plays_mean"]-test["actual_team_plays"]
    ).abs()
    test["challenger_play_abs_error"]=(
        test["challenger_team_plays"]-test["actual_team_plays"]
    ).abs()
    test["baseline_dropback_abs_error"]=(
        test["pred_dropback_rate_mean"]-test["actual_dropback_rate"]
    ).abs()
    test["challenger_dropback_abs_error"]=(
        test["challenger_dropback_rate"]-test["actual_dropback_rate"]
    ).abs()

    return test,{
        "contract_version":CONTRACT_VERSION,
        "evaluation_season":int(evaluation_season),
        "trained_through_season":train_end,
        "n":int(len(test)),
        "unique_games":int(test["game_id"].astype(str).nunique()),
        "baseline_team_plays_mae":float(test["baseline_play_abs_error"].mean()),
        "challenger_team_plays_mae":float(test["challenger_play_abs_error"].mean()),
        "challenger_minus_baseline_team_plays_mae":float(
            (test["challenger_play_abs_error"]-test["baseline_play_abs_error"]).mean()
        ),
        "baseline_dropback_rate_mae":float(test["baseline_dropback_abs_error"].mean()),
        "challenger_dropback_rate_mae":float(test["challenger_dropback_abs_error"].mean()),
        "challenger_minus_baseline_dropback_rate_mae":float(
            (test["challenger_dropback_abs_error"]-test["baseline_dropback_abs_error"]).mean()
        ),
        "fits":{name:fit.to_dict() for name,fit in fits.items()},
        "prop_outcomes_used":0,
        "completed_2026_outcomes_used":0,
        "production_authorized":False,
    }


def clustered_difference_interval(
    scored: pd.DataFrame,
    challenger_col: str,
    baseline_col: str,
    *,
    replicates: int=3000,
    seed: int=BOOTSTRAP_SEED,
)->list[float|None]:
    games=np.asarray(sorted(scored["game_id"].astype(str).unique()))
    if len(games)<2:
        return [None,None]
    grouped={g:scored[scored["game_id"].astype(str).eq(g)] for g in games}
    rng=np.random.default_rng(seed)
    vals=np.empty(replicates,dtype=float)
    for i in range(replicates):
        sample=rng.choice(games,size=len(games),replace=True)
        boot=pd.concat([grouped[g] for g in sample],ignore_index=True)
        vals[i]=float((boot[challenger_col]-boot[baseline_col]).mean())
    return [float(np.quantile(vals,0.025)),float(np.quantile(vals,0.975))]
