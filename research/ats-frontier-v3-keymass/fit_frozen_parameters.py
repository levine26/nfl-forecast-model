from __future__ import annotations

"""Deterministic historical-development fit for FV3-PROS-KMASS-01.
Only 2010-2025 REG outcomes are loadable; no 2026+ scoring exists here.
"""
from hashlib import sha256
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from nfl_forecast.data import load_core_data
import v3_keymass as core

ROOT = Path(__file__).resolve().parent
DF_CANDIDATES = (4.0, 6.0, 10.0, 30.0)
LAMBDA_KEY = 10.0
TRAIN_START = 2010
TRAIN_END = 2025
CV_START = 2016
class TrainingError(RuntimeError): pass

def _regular(frame):
    out=frame.copy()
    if "game_type" in out: out=out[out["game_type"].eq("REG")].copy()
    elif "season_type" in out: out=out[out["season_type"].eq("REG")].copy()
    return out

def load_training_rows():
    seasons=list(range(TRAIN_START, TRAIN_END + 1))
    bundle=load_core_data(seasons)
    df=_regular(bundle.schedules)
    df["season"]=pd.to_numeric(df["season"], errors="coerce")
    if (df["season"] > TRAIN_END).any(): raise TrainingError("post-2025 row entered V3 historical-development fit")
    for col in ("home_score","away_score","spread_line"): df[col]=pd.to_numeric(df[col], errors="coerce")
    df=df[df["season"].between(TRAIN_START,TRAIN_END,inclusive="both") & df["home_score"].notna() & df["away_score"].notna() & df["spread_line"].notna()].copy()
    df["actual_margin"]=(df["home_score"]-df["away_score"]).round().astype(int)
    df["market_margin"]=df["spread_line"].astype(float)
    return df[["game_id","season","week","actual_margin","market_margin"]].drop_duplicates("game_id").sort_values(["season","week","game_id"]).reset_index(drop=True)

def _null_nll(df,sigma,nu):
    mass=np.asarray([core.cell(int(m),float(loc),float(sigma),float(nu),(0.,0.,0.)) for m,loc in zip(df["actual_margin"],df["market_margin"])])
    return float(np.mean(-np.log(np.clip(mass,core.EPS,1.0))))

def fit_sigma(df,nu):
    if len(df)<100: raise TrainingError("insufficient historical-development rows")
    def obj(x):
        sigma=float(np.exp(x[0])); return 1e9+abs(sigma) if sigma<.25 or sigma>80 else _null_nll(df,sigma,nu)
    init=math.log(max(float(np.std(df["actual_margin"]-df["market_margin"],ddof=1)),1.0))
    res=minimize(obj,np.array([init]),method="L-BFGS-B",bounds=[(math.log(.25),math.log(80.))],options={"maxiter":400,"ftol":1e-11})
    if not res.success or not np.isfinite(res.fun): raise TrainingError(f"scale fit failed: {res.message}")
    return float(np.exp(res.x[0]))

def select_df_null_only(df):
    audit=[]
    for nu in DF_CANDIDATES:
        losses=[]; rows=0
        for season in range(CV_START,TRAIN_END+1):
            train=df[df["season"]<season]; valid=df[df["season"]==season]
            if train.empty or valid.empty: continue
            sigma=fit_sigma(train,nu)
            losses.extend([-math.log(max(core.cell(int(m),float(loc),sigma,nu,(0.,0.,0.)),core.EPS)) for m,loc in zip(valid["actual_margin"],valid["market_margin"])])
            rows += len(valid)
        audit.append({"nu":nu,"validation_rows":rows,"mean_integer_nll":float(np.mean(losses))})
    best=min(range(len(audit)),key=lambda i:(audit[i]["mean_integer_nll"],i))
    return float(audit[best]["nu"]),audit

def fit_key_gammas(df,nu,sigma):
    n=float(len(df))
    def obj(g):
        mass=np.asarray([core.cell(int(m),float(loc),sigma,nu,g) for m,loc in zip(df["actual_margin"],df["market_margin"])])
        return float(np.mean(-np.log(np.clip(mass,core.EPS,1.0)))) + LAMBDA_KEY*float(np.dot(g,g))/n
    res=minimize(obj,np.zeros(3),method="L-BFGS-B",options={"maxiter":400,"ftol":1e-11})
    if not res.success or not np.isfinite(res.fun): raise TrainingError(f"key-mass fit failed: {res.message}")
    return tuple(float(x) for x in res.x)

def main():
    df=load_training_rows()
    if int(df["season"].max())>TRAIN_END: raise TrainingError("2026+ outcome firewall violated")
    nu,cv=select_df_null_only(df); sigma=fit_sigma(df,nu); gammas=fit_key_gammas(df,nu,sigma)
    payload={"candidate_id":core.CANDIDATE_ID,"null_id":core.NULL_ID,"status":"FROZEN_PARAMETER_FIT_FROM_HISTORICAL_DEVELOPMENT_ONLY","historical_confirmation_claimed":False,"training_era":[TRAIN_START,TRAIN_END],"season_type":"REG","rows":int(len(df)),"game_ids_sha256":sha256("\n".join(sorted(df["game_id"].astype(str))).encode()).hexdigest(),"df_selection":"NULL_ONLY_FORWARD_SEASON_CV_2016_2025","df_cv_audit":cv,"degrees_of_freedom":nu,"constant_scale":sigma,"key_log_mass_offsets":{"0":gammas[0],"abs3":gammas[1],"abs7":gammas[2]},"key_regularization_lambda":LAMBDA_KEY,"prospective_refit_allowed":False,"completed_2026_outcomes_used":0}
    raw=json.dumps(payload,indent=2,sort_keys=True)+"\n"; (ROOT/"frozen_parameters.json").write_text(raw,encoding="utf-8"); print(raw,end="")
if __name__=="__main__": main()
