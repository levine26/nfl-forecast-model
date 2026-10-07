"""Research-only Phase 3 A/B/C execution. Frozen specifications: PR #627.

No imports into production, no 2026 outcomes, no candidate selection or tuning.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import traceback

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit, ndtr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nfl_forecast.fst_nested_pure import load_frozen_base_oof, load_frozen_training_frame
from nfl_forecast.challenger_stacking import build_chronological_logit_stack

SEED = 26
TARGET = (2022, 2023, 2024, 2025)
FEATURE_PENALTY = 0.02
EPS = 1e-6
COMPONENTS = ("logistic", "extra_trees", "xgboost", "catboost")
CANDIDATES = ("MKT-COMP-RESIDUAL-V1", "MARGIN-RESIDUAL-WIN-V1", "EARLY-STATE-SHRINKAGE-V1")


def clipped_logit(values):
    return logit(np.clip(np.asarray(values, dtype=float), EPS, 1 - EPS))


def fit_offset(y, market_prob, x, penalty=FEATURE_PENALTY):
    """Fixed market offset; train-only standardizer; deterministic L2 log loss."""
    y = np.asarray(y, dtype=float)
    base = clipped_logit(market_prob)
    x = np.asarray(x, dtype=float)
    if len(y) < 200 or x.ndim != 2 or not np.isfinite(x).all() or not np.isfinite(base).all():
        raise ValueError("Insufficient/invalid strictly earlier-season candidate training rows")
    means = x.mean(axis=0)
    stds = x.std(axis=0)
    stds[stds < 1e-10] = 1.0
    z = (x - means) / stds
    design = np.column_stack([np.ones(len(z)), z])

    def objective(theta):
        eta = base + design @ theta
        # stable binary logistic loss / analytic derivative, intercept unpenalized
        loss = np.logaddexp(0, eta).mean() - (y * eta).mean()
        reg = 0.5 * penalty * np.sum(theta[1:] ** 2)
        grad = design.T @ (expit(eta) - y) / len(y)
        grad[1:] += penalty * theta[1:]
        return loss + reg, grad

    opt = minimize(objective, np.zeros(design.shape[1]), method="L-BFGS-B",
                   jac=True, options={"maxiter": 1000, "ftol": 1e-12})
    if not opt.success and np.linalg.norm(opt.jac) > 1e-5:
        raise RuntimeError(f"Offset logistic optimizer did not converge: {opt.message}")
    return opt.x, means, stds


def predict_offset(market_prob, x, fit):
    theta, means, stds = fit
    x = np.asarray(x, dtype=float)
    z = (x - means) / stds
    return np.clip(expit(clipped_logit(market_prob) + theta[0] + z @ theta[1:]), EPS, 1-EPS)


def frozen_panel():
    """Read checked, *recovered* F-ST artifacts; join only on keyed game identity."""
    base = load_frozen_base_oof()
    frozen = load_frozen_training_frame()
    if len(base) != 2127 or len(frozen) != 1615:
        raise RuntimeError("Recovered immutable F-ST artifact population changed")
    if frozen.game_id.duplicated().any() or base.game_id.duplicated().any():
        raise RuntimeError("Duplicated immutable F-ST game IDs")
    ref = build_chronological_logit_stack(frozen, target_seasons=TARGET).predictions
    ref = pd.DataFrame({"game_id": frozen.loc[ref.index, "game_id"].astype(str).to_numpy(),
                        "fst_prob": ref.stack_probability.to_numpy(dtype=float)})
    data = frozen.merge(base[["game_id", *COMPONENTS]], on="game_id", how="left", validate="one_to_one")
    data = data.merge(ref, on="game_id", how="left", validate="one_to_one")
    if data[list(COMPONENTS)].isna().any().any():
        raise RuntimeError("Frozen component/market game identity mismatch")
    data["week"] = pd.to_numeric(data.game_id.str.split("_").str[1], errors="raise").astype(int)
    data["season"] = pd.to_numeric(data.season, errors="raise").astype(int)
    target = data[data.season.isin(TARGET)].copy()
    if len(target) != 1087 or target.game_id.nunique() != 1087:
        raise RuntimeError(f"Paired target differs from frozen 1087: {len(target)}")
    if target.fst_prob.isna().any():
        raise RuntimeError("Chronological F-ST reference missing probability")
    correct = ((target.fst_prob.to_numpy() >= 0.5) ==
               target.home_win.to_numpy(dtype=int)).sum()
    if int(correct) != 741:
        raise RuntimeError(f"Chronology-clean F-ST NOT 741/1087: observed {correct}")
    if any(data.season >= 2026):
        raise RuntimeError("2026 outcome firewall breached")
    return data


def season_forward(panel, columns, *, offset_col="market_prob", prediction_name="candidate_prob"):
    """Only earlier-season rows fit; no hyperparameter or threshold grid."""
    pieces = []
    for year in TARGET:
        train = panel[(panel.season >= 2020) & (panel.season < year)].copy()
        test = panel[panel.season == year].copy()
        if train.empty or test.empty:
            raise RuntimeError(f"No chronological train/test for {year}")
        if not train[columns + [offset_col, "home_win"]].notna().all().all():
            raise RuntimeError(f"Missing pre-target {year} features; no hindsight imputation")
        if not test[columns + [offset_col]].notna().all().all():
            raise RuntimeError(f"Missing target {year} features; fail-closed coverage")
        fit = fit_offset(train.home_win, train[offset_col], train[columns].to_numpy(float))
        pred = predict_offset(test[offset_col], test[columns].to_numpy(float), fit)
        pieces.append(pd.DataFrame({"game_id": test.game_id.to_numpy(),
                                    prediction_name: pred,
                                    "fit_last_season": int(train.season.max())}))
    return pd.concat(pieces, ignore_index=True)


def run_A(panel):
    work = panel.copy()
    m = clipped_logit(work.market_prob)
    r = np.column_stack([clipped_logit(work[c]) - m for c in COMPONENTS])
    for i, c in enumerate(COMPONENTS):
        work[f"res_{c}"] = r[:, i]
    work["res_mean"] = r.mean(axis=1)
    work["res_std"] = r.std(axis=1)
    work["res_range"] = np.ptp(r, axis=1)
    work["abs_market_logit"] = np.abs(m)
    core = [f"res_{c}" for c in COMPONENTS]
    full = core + ["res_mean", "res_std", "res_range", "abs_market_logit"]
    pred = season_forward(work, full)
    ablation = season_forward(work, core, prediction_name="ablated_prob")
    result = pred.merge(ablation[["game_id", "ablated_prob"]], on="game_id", validate="one_to_one")
    return result, {"features":full,"ablation":"four_component_residuals_only",
                    "training":"frozen OOF component predictions, seasons 2020..S-1",
                    "penalty":FEATURE_PENALTY}


def historical_features():
    """Load only through 2025, never current-year results or late player/injury state."""
    from nfl_forecast.data import load_core_data
    from nfl_forecast.features import aggregate_team_games, add_game_results, build_matchup_features, core_columns
    from nfl_forecast.elo import build_pregame_elo
    bundle = load_core_data(range(2012, 2026), ".cache/nflreadpy")
    schedules = bundle.schedules.copy()
    schedules = schedules[(schedules.season >= 2012) & (schedules.season <= 2025)]
    if "game_type" in schedules:
        schedules = schedules[schedules.game_type.eq("REG")].copy()
    if schedules.game_id.duplicated().any():
        raise RuntimeError("Historical schedule game IDs are not unique")
    tg = aggregate_team_games(bundle.pbp)
    tg = add_game_results(tg, schedules)
    elo = build_pregame_elo(schedules)
    games = build_matchup_features(tg, schedules, elo)
    if games.game_id.duplicated().any():
        raise RuntimeError("Duplicate game IDs in historical feature rebuild")
    features = core_columns(games)
    if any("margin" in c or "score" in c or c.startswith("home_win") for c in features):
        raise RuntimeError("Postgame target detected in model features")
    return games, tg, schedules, features


def audit_historical_identity(panel, games):
    old = panel.loc[panel.season.between(2020, 2025),
                    ["game_id", "home_win", "season"]].copy()
    new = games[["game_id", "season", "home_win"]].copy()
    merged = old.merge(new, on="game_id", how="left",
                       validate="one_to_one", suffixes=("", "_rebuilt"), indicator=True)
    if not merged["_merge"].eq("both").all():
        raise RuntimeError("Historical rebuild lacks frozen F-ST game IDs")
    if not (merged.season == merged.season_rebuilt).all():
        raise RuntimeError("Historical rebuild changes game seasons")
    if not (merged.home_win.astype(int) == merged.home_win_rebuilt.astype(int)).all():
        raise RuntimeError("Historical rebuild changes official binary targets")
    return int(len(merged))


def run_B(panel, games, features):
    """Pretarget fitted margin predictions and pretarget OOF residual scale."""
    work = games[games.margin.notna() & games.season.between(2012, 2025)].copy()
    if work[features].empty:
        raise RuntimeError("Margin historical features are missing")
    oof_parts, residuals = [], []
    for year in range(2015, 2026):
        tr = work[work.season < year].copy()
        te = work[work.season == year].copy()
        if len(tr) < 500 or te.empty:
            raise RuntimeError(f"Insufficient margin history for season {year}")
        # Features and imputers fit ONLY on seasons preceding the target.
        reg = make_pipeline(SimpleImputer(strategy="median", keep_empty_features=True),
                            StandardScaler(), Ridge(alpha=100.0))
        reg.fit(tr[features], tr.margin)
        yhat = np.asarray(reg.predict(te[features]), dtype=float)
        prior = np.asarray(residuals, dtype=float)
        if year >= 2018 and len(prior) < 50:
            raise RuntimeError("No pretarget margin error calibration history")
        if len(prior) >= 50:
            sigma = max(1.0, float(np.sqrt(np.mean(prior ** 2))))
        else:
            sigma = np.nan
        part = pd.DataFrame({"game_id": te.game_id.to_numpy(),
                             "season":year, "model_margin":yhat,
                             "margin_sigma":sigma,
                             "margin_prob": np.clip(ndtr(yhat / sigma), EPS, 1-EPS)
                               if np.isfinite(sigma) else np.nan})
        oof_parts.append(part)
        residuals.extend((te.margin.to_numpy(float) - yhat).tolist())
    merged = panel.merge(pd.concat(oof_parts, ignore_index=True).drop(columns="season"),
                         on="game_id", how="left",validate="one_to_one")
    if merged.loc[merged.season.between(2020,2025),"margin_prob"].isna().any():
        raise RuntimeError("Margin OOF cannot cover canonical frozen game population")
    merged["margin_residual_logit"] = clipped_logit(merged.margin_prob.fillna(0.5)) - clipped_logit(merged.market_prob)
    candidate = season_forward(merged, ["margin_residual_logit"])
    reference = merged[["game_id", "margin_prob", "model_margin", "margin_sigma"]].merge(candidate,on="game_id",validate="one_to_one")
    return reference, {"features":["margin_residual_logit"],"margin_regressor":"Ridge(alpha=100)",
                       "residual_sigma":"pretarget 2015..S-1 OOF RMS; no current target",
                       "penalty":FEATURE_PENALTY}


def early_state_features(team_games, schedules):
    """Create per-team, pre-game state using only prior games and previous season."""
    metrics=("off_epa","def_epa_allowed")
    observed = team_games[["game_id","team",*metrics]].drop_duplicates(["game_id","team"])
    games = schedules[["game_id","season","week","gameday","home_team","away_team"]].copy()
    h=games[["game_id","season","week","gameday","home_team"]].rename(columns={"home_team":"team"})
    a=games[["game_id","season","week","gameday","away_team"]].rename(columns={"away_team":"team"})
    longitudinal = pd.concat([h,a],ignore_index=True).merge(observed, on=["game_id","team"],how="left",
                                                             validate="one_to_one")
    if longitudinal[["game_id","team"]].duplicated().any():
        raise RuntimeError("Duplicate team-game state")
    long_prior=longitudinal.sort_values(["team","season","week","gameday","game_id"]).copy()
    # Previous season mean is allowed; current-season global means would leak.
    league = observed.merge(games[["game_id","season"]],on="game_id",validate="many_to_one")
    league_mean = league.groupby("season",sort=True)[list(metrics)].mean()
    rows=[]
    for team, part in long_prior.groupby("team",sort=True):
        hist=defaultdict(list)
        this_season = None
        for row in part.itertuples(index=False):
            y=int(row.season)
            if y != this_season:
                this_season = y
                current=[]
            prev=hist[y-1][-8:]
            n=len(current)
            vals={}
            for metric in metrics:
                prev_vals=[float(z[metric]) for z in prev if np.isfinite(z[metric])]
                prior_league = float(league_mean.loc[y-1,metric]) if (y-1) in league_mean.index else 0.0
                if not np.isfinite(prior_league):
                    prior_league=0.0
                prior_form=float(np.mean(prev_vals)) if prev_vals else prior_league
                prior_center=0.6*prior_form+0.4*prior_league
                current_vals=[float(z[metric]) for z in current if np.isfinite(z[metric])]
                form=float(np.mean(current_vals)) if current_vals else prior_center
                vals[metric+"_state"]=(n*form+6*prior_center)/(n+6)
            rows.append({"game_id":row.game_id,"team":team,"n_prior":n,**vals})
            measured={metric:float(getattr(row,metric)) if pd.notna(getattr(row,metric)) else np.nan
                      for metric in metrics}
            # Only completed observed team-game data updates next game's state.
            if any(np.isfinite(v) for v in measured.values()):
                current.append(measured)
                hist[y].append(measured)
    out=pd.DataFrame(rows)
    home=out.rename(columns={"team":"home_team",
                             **{c:"home_"+c for c in ["n_prior","off_epa_state","def_epa_allowed_state"]}})
    away=out.rename(columns={"team":"away_team",
                             **{c:"away_"+c for c in ["n_prior","off_epa_state","def_epa_allowed_state"]}})
    frame=games[["game_id","home_team","away_team"]].merge(home,on=["game_id","home_team"],validate="one_to_one").merge(
        away,on=["game_id","away_team"],validate="one_to_one")
    frame["off_state_diff"]=frame.home_off_epa_state-frame.away_off_epa_state
    frame["def_state_diff"]=frame.home_def_epa_allowed_state-frame.away_def_epa_allowed_state
    frame["state_uncertainty"]=np.abs(frame.home_n_prior-frame.away_n_prior)/(frame.home_n_prior+frame.away_n_prior+6)
    return frame[["game_id","off_state_diff","def_state_diff","state_uncertainty"]]


def run_C(panel, tg, schedules):
    state = early_state_features(tg,schedules)
    merged=panel.merge(state,on="game_id",how="left",validate="one_to_one")
    features=["off_state_diff","def_state_diff","state_uncertainty"]
    if not merged.loc[merged.season.between(2020,2025),features].notna().all().all():
        raise RuntimeError("Early-state historical coverage incomplete")
    result=season_forward(merged, features)
    return result, {"features":features,
                    "prior_blend":"0.6 prior 8 team games / 0.4 prior season league",
                    "current_blend":"n/(n+6), n pregame completed team matches",
                    "QB_state":"NOT_QUALIFIED: no retrospective next-starter inference; omitted",
                    "penalty":FEATURE_PENALTY}


def metric_values(y, p):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float)
    if np.isnan(p).any() or ((p<=0)|(p>=1)).any():raise RuntimeError("Invalid probability")
    pred=p>=0.5
    return {"games":int(len(y)),"correct":int((pred==y).sum()),
            "accuracy":float((pred==y).mean()),
            "brier":float(np.mean((p-y)**2)),
            "log_loss":float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p)))}


def paired_results(frame):
    y=frame.home_win.to_numpy(int)
    fst=frame.fst_prob.to_numpy(float)
    cand=frame.candidate_prob.to_numpy(float)
    cm=metric_values(y,cand);fm=metric_values(y,fst)
    a=cand>=0.5;b=fst>=0.5
    sw=a!=b
    only_c=int(((a==y)&(b!=y)).sum())
    only_f=int(((b==y)&(a!=y)).sum())
    if only_c+only_f!=int(sw.sum()) or cm["correct"]-fm["correct"]!=only_c-only_f:
        raise RuntimeError("Paired switch identity check failed")
    if len(frame)!=1087:
        raise RuntimeError("Paired evaluation population changed")
    # season-week BLOCK bootstrap; block-level correct difference avoids 2000x rebuilding rows
    blocks=frame.assign(_delta=(a==y).astype(int)-(b==y).astype(int)).groupby(["season","week"])
    sums=blocks._delta.sum().to_numpy(dtype=float)
    n=blocks.size().to_numpy(dtype=float)
    rng=np.random.default_rng(SEED)
    draws=rng.integers(0,len(n),size=(2000,len(n)))
    deltas=sums[draws].sum(axis=1)/n[draws].sum(axis=1)
    ci=np.quantile(deltas,[0.025,0.975])
    years={}
    for s,d in frame.groupby("season",sort=True):
        years[str(s)]={"candidate":metric_values(d.home_win,d.candidate_prob),
                       "fst":metric_values(d.home_win,d.fst_prob)}
    slices={}
    for label,subset in [("weeks_1_4",frame[frame.week<=4]),
                         ("weeks_1_6",frame[frame.week<=6]),
                         ("weeks_7_plus",frame[frame.week>=7]),
                         ("market_50_55",frame[np.abs(frame.market_prob-0.5)<=0.05]),
                         ("market_55_65",frame[(np.abs(frame.market_prob-0.5)>0.05)&(np.abs(frame.market_prob-0.5)<=0.15)]),
                         ("market_65_plus",frame[np.abs(frame.market_prob-0.5)>0.15])]:
        if len(subset):
            slices[label]={"candidate":metric_values(subset.home_win,subset.candidate_prob),
                           "fst":metric_values(subset.home_win,subset.fst_prob)}
    try:
        reg=LogisticRegression(C=1e6,max_iter=2000)
        reg.fit(clipped_logit(cand).reshape(-1,1),y)
        calibration={"intercept":float(reg.intercept_[0]),"slope":float(reg.coef_[0,0])}
    except Exception as e:
        calibration={"error":str(e)}
    season_delta={z:years[z]["candidate"]["correct"]-years[z]["fst"]["correct"] for z in years}
    season_deletion={}
    for s in TARGET:
        other=frame[frame.season!=s]
        z=metric_values(other.home_win,other.candidate_prob)["correct"]-metric_values(other.home_win,other.fst_prob)["correct"]
        season_deletion[str(s)]=int(z)
    if cm["correct"]<=fm["correct"]:
        decision="REJECT"
    elif sum(d>0 for d in season_delta.values())<3 or ci[0]<=0:
        decision="INCONCLUSIVE"
    elif cm["brier"]-fm["brier"]>0.0025 or cm["log_loss"]>fm["log_loss"]+0.01:
        decision="INCONCLUSIVE"
    else:
        decision="ADVANCE_FOR_INDEPENDENT_PROSPECTIVE_SHADOW"
    return {"candidate":cm,"fst":fm,"delta_accuracy":cm["accuracy"]-fm["accuracy"],
            "switches":int(sw.sum()),"candidate_only_correct":only_c,
            "fst_only_correct":only_f,
            "switch_win_rate":float(only_c/int(sw.sum())) if sw.any() else None,
            "by_season":years,"season_win_delta":season_delta,"slices":slices,
            "season_deletion_correct_delta":season_deletion,
            "week_block_accuracy_delta_ci95":[float(ci[0]),float(ci[1])],
            "bootstrap_samples":2000,"calibration":calibration,
            "decision":decision}


def execute(outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    panel=frozen_panel()
    target=panel[panel.season.isin(TARGET)].copy()
    evidence={"governance":{"prereg_commit":"b13fd61e4092db1aef11983df0fbf81e70f3f41e",
                            "outcomes_2026_used":0,
                            "incumbent":"F-ST-01-FROZEN-2026",
                            "population":1087,"production_changed":False,
                            "alexandria_used":False},
              "candidates":{}}
    # A is independent of downloading NFL historical game source.
    a,notes=run_A(panel)
    m=target[["game_id","season","week","home_win","market_prob","fst_prob"]].merge(
        a,on="game_id",validate="one_to_one")
    metrics=paired_results(m)
    metrics["four_component_only_ablation"]=metric_values(m.home_win,m.ablated_prob)
    evidence["candidates"][CANDIDATES[0]]={"status":"EVALUATED","metrics":metrics,"design":notes}
    m.to_csv(outdir/"candidate_A_oof.csv",index=False,float_format="%.12g")
    print("CANDIDATE_A_RESULT",json.dumps({"decision":metrics["decision"],
                                         "correct":metrics["candidate"]["correct"],
                                         "fst_correct":metrics["fst"]["correct"]}),flush=True)

    # B and C reuse a *single* historical PBP/schedule/feature rebuild.
    try:
        games,tg,schedules,features=historical_features()
        audited=audit_historical_identity(panel,games)
        evidence["historical_rebuild"]={"status":"QUALIFIED","paired_identity_2020_2025":audited,
                                        "sources":"nflreadpy historical REG PBP + nflverse schedules",
                                        "feature_count":len(features),
                                        "last_outcome_season":2025}
    except Exception as exc:
        evidence["historical_rebuild"]={"status":"NOT_QUALIFIED","error":str(exc)}
        for key in CANDIDATES[1:]:
            evidence["candidates"][key]={"status":"NOT_EVALUABLE",
                                         "reason":"Historical PIT/identity rebuild failed; see historical_rebuild"}
        (outdir/"summary.json").write_text(json.dumps(evidence,indent=2,allow_nan=False))
        (outdir/"manifest.json").write_text(json.dumps({"outcomes_2026_used":0,"prereg_commit":evidence["governance"]["prereg_commit"],"status":"historical_rebuild_unqualified"},indent=2))
        return evidence

    for index in [1,2]:
        key=CANDIDATES[index]
        try:
            model,notes=run_B(panel,games,features) if index==1 else run_C(panel,tg,schedules)
            dat=target[["game_id","season","week","home_win","market_prob","fst_prob"]].merge(
                model,on="game_id",validate="one_to_one")
            metrics=paired_results(dat)
            if index==1:
                metrics["margin_only_ablation"]=metric_values(dat.home_win,dat.margin_prob)
            evidence["candidates"][key]={"status":"EVALUATED","metrics":metrics,"design":notes}
            dat.to_csv(outdir/f"candidate_{'B' if index==1 else 'C'}_oof.csv",
                       index=False,float_format="%.12g")
            print("CANDIDATE_RESULT",key,metrics["decision"],metrics["candidate"]["correct"],flush=True)
        except Exception as exc:
            evidence["candidates"][key]={"status":"NOT_EVALUABLE",
                                         "error":str(exc),"traceback":traceback.format_exc()[-12000:]}
            print("NOT_EVALUABLE",key,str(exc),flush=True)

    (outdir/"summary.json").write_text(json.dumps(evidence,indent=2,allow_nan=False))
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in outdir.iterdir()
            if p.is_file()}
    (outdir/"manifest.json").write_text(json.dumps({"sha256":hashes,"outcomes_2026_used":0,
        "prereg_commit":evidence["governance"]["prereg_commit"]},indent=2))
    return evidence


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output-dir",required=True)
    args=parser.parse_args()
    report=execute(args.output_dir)
    print(json.dumps({key:{"status":v["status"],
        "decision":v.get("metrics",{}).get("decision"),
        "correct":v.get("metrics",{}).get("candidate",{}).get("correct")} for key,v in
        report["candidates"].items()},indent=2))
