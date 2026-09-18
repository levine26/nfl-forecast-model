from __future__ import annotations

"""Pre-2026 workload-mixture research for LevLine Props 2.0.

The model asks a narrower question than prop forecasting: conditional on an injury-report state,
what distribution of offensive workload relative to the player's own strictly prior baseline is
historically observed? No prop result or sportsbook information is consumed.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

CONTRACT_VERSION = "levline-props-v2-availability-mixture-v0.1.0"
STATE_NAMES = ("ACTIVE_LIMITED", "ACTIVE_NORMAL", "ACTIVE_ELEVATED")
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
BASELINE_GAMES = 4
MIN_BASELINE_GAMES = 2
LOG_RATIO_CLIP = (-2.0, 1.0)
DIRICHLET_ALPHA = 1.0
RANDOM_STATE = 20260918


class AvailabilityMixtureError(ValueError):
    pass


@dataclass(frozen=True)
class WorkloadObservation:
    season: int
    week: int
    team: str
    player_id: str
    position: str
    report_status: str
    report_timestamp_utc: str
    kickoff_utc: str
    offense_snap_share: float
    prior_baseline_snap_share: float
    workload_ratio: float
    active: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _team(value: Any) -> str:
    text=str(value or "").upper().strip()
    return {"JAC":"JAX","LA":"LAR"}.get(text,text)


def _status(value: Any) -> str:
    text=str(value or "").upper().strip().replace(" ","_")
    aliases={"QUESTIONABLE":"QUESTIONABLE","DOUBTFUL":"DOUBTFUL","OUT":"OUT"}
    return aliases.get(text,text)


def _timestamp(value: Any) -> pd.Timestamp:
    ts=pd.Timestamp(value)
    if pd.isna(ts) or ts.tzinfo is None:
        raise AvailabilityMixtureError(f"timestamp must be timezone-aware: {value!r}")
    return ts.tz_convert("UTC")


def _prepare_schedule(schedules: pd.DataFrame) -> pd.DataFrame:
    required={"season","week","home_team","away_team"}
    missing=required-set(schedules.columns)
    if missing:
        raise AvailabilityMixtureError(f"schedule missing fields: {sorted(missing)}")
    work=schedules.copy()
    if "game_type" in work.columns:
        work=work[work["game_type"].astype(str).str.upper().eq("REG")].copy()
    work["season"]=pd.to_numeric(work["season"],errors="coerce")
    work["week"]=pd.to_numeric(work["week"],errors="coerce")
    work["home_team"]=work["home_team"].map(_team)
    work["away_team"]=work["away_team"].map(_team)
    if "kickoff" in work.columns:
        kickoff=pd.to_datetime(work["kickoff"],utc=True,errors="coerce")
    elif {"gameday","gametime"}.issubset(work.columns):
        naive=pd.to_datetime(
            work["gameday"].astype("string")+" "+work["gametime"].astype("string"),
            errors="coerce",
        )
        kickoff=naive.dt.tz_localize(
            "America/New_York",ambiguous="NaT",nonexistent="NaT"
        ).dt.tz_convert("UTC")
    else:
        raise AvailabilityMixtureError("schedule has no kickoff timestamp source")
    work["kickoff_utc"]=kickoff
    rows=[]
    for row in work.dropna(subset=["season","week","kickoff_utc"]).itertuples(index=False):
        for team in (row.home_team,row.away_team):
            rows.append({
                "season":int(row.season),
                "week":int(row.week),
                "team":_team(team),
                "kickoff_utc":row.kickoff_utc,
            })
    out=pd.DataFrame(rows)
    if out.empty or out.duplicated(["season","week","team"]).any():
        raise AvailabilityMixtureError("schedule team-week kickoff mapping is ambiguous")
    return out


def _prepare_snaps(snaps: pd.DataFrame) -> pd.DataFrame:
    required={"season","week","team","player_id","offense_snaps"}
    missing=required-set(snaps.columns)
    if missing:
        raise AvailabilityMixtureError(f"snap history missing fields: {sorted(missing)}")
    work=snaps.copy()
    if "game_type" in work.columns:
        work=work[work["game_type"].astype(str).str.upper().eq("REG")].copy()
    work["season"]=pd.to_numeric(work["season"],errors="coerce")
    work["week"]=pd.to_numeric(work["week"],errors="coerce")
    work["team"]=work["team"].map(_team)
    work["player_id"]=work["player_id"].astype("string").fillna("").str.strip()
    work["offense_snaps"]=pd.to_numeric(work["offense_snaps"],errors="coerce")
    work=work[
        work["season"].notna() & work["week"].notna() &
        work["player_id"].ne("") & work["offense_snaps"].notna()
    ].copy()
    work["season"]=work["season"].astype(int)
    work["week"]=work["week"].astype(int)
    work["offense_snaps"]=work["offense_snaps"].clip(lower=0)
    denom=work.groupby(["season","week","team"],sort=False)["offense_snaps"].transform("max")
    work["offense_snap_share"]=work["offense_snaps"]/denom.replace(0,np.nan)
    work=work[work["offense_snap_share"].between(0,1,inclusive="both")].copy()
    return (
        work.sort_values(["season","week","team","player_id"])
        .drop_duplicates(["season","week","team","player_id"],keep="last")
    )


def _prepare_injuries(injuries: pd.DataFrame, schedule: pd.DataFrame) -> tuple[pd.DataFrame,dict[str,Any]]:
    required={"season","week","team","gsis_id","position","report_status","date_modified"}
    missing=required-set(injuries.columns)
    if missing:
        raise AvailabilityMixtureError(
            "historical injury rows require timestamped fields; missing "
            + str(sorted(missing))
        )
    work=injuries.copy()
    season_type=next((c for c in ("season_type","game_type") if c in work.columns),None)
    if season_type:
        work=work[work[season_type].astype(str).str.upper().eq("REG")].copy()
    work["season"]=pd.to_numeric(work["season"],errors="coerce")
    work["week"]=pd.to_numeric(work["week"],errors="coerce")
    work["team"]=work["team"].map(_team)
    work["player_id"]=work["gsis_id"].astype("string").fillna("").str.strip()
    work["position"]=work["position"].astype("string").fillna("").str.upper().str.strip()
    work["report_status"]=work["report_status"].map(_status)
    work["report_timestamp_utc"]=pd.to_datetime(work["date_modified"],utc=True,errors="coerce")
    work=work[
        work["season"].notna() & work["week"].notna() &
        work["player_id"].ne("") & work["position"].isin(SUPPORTED_POSITIONS) &
        work["report_status"].isin({"QUESTIONABLE","DOUBTFUL","OUT"}) &
        work["report_timestamp_utc"].notna()
    ].copy()
    work["season"]=work["season"].astype(int)
    work["week"]=work["week"].astype(int)
    merged=work.merge(schedule,on=["season","week","team"],how="left",validate="many_to_one")
    missing_kickoff=int(merged["kickoff_utc"].isna().sum())
    post_or_at=merged["kickoff_utc"].notna() & merged["report_timestamp_utc"].ge(merged["kickoff_utc"])
    post_count=int(post_or_at.sum())
    eligible=merged[merged["kickoff_utc"].notna() & ~post_or_at].copy()
    # Latest known status strictly before kickoff.
    eligible=(
        eligible.sort_values(["season","week","team","player_id","report_timestamp_utc"])
        .drop_duplicates(["season","week","team","player_id"],keep="last")
    )
    return eligible,{
        "rows_received":int(len(injuries)),
        "timestamped_supported_rows":int(len(work)),
        "missing_kickoff_rows_dropped":missing_kickoff,
        "post_kickoff_rows_dropped":post_count,
        "latest_pregame_rows":int(len(eligible)),
    }


def build_workload_observations(
    injuries: pd.DataFrame,
    snaps: pd.DataFrame,
    schedules: pd.DataFrame,
    *,
    trained_through_season: int=2025,
) -> tuple[pd.DataFrame,dict[str,Any]]:
    if int(trained_through_season)>2025:
        raise AvailabilityMixtureError("completed 2026 outcomes are prohibited from workload fitting")
    schedule=_prepare_schedule(schedules)
    snap=_prepare_snaps(snaps)
    injury,injury_audit=_prepare_injuries(injuries,schedule)

    snap_lookup={
        (int(r.season),int(r.week),_team(r.team),str(r.player_id)):float(r.offense_snap_share)
        for r in snap.itertuples(index=False)
    }
    player_hist:dict[str,list[tuple[int,int,float]]]=defaultdict(list)
    for r in snap.sort_values(["season","week"]).itertuples(index=False):
        player_hist[str(r.player_id)].append((int(r.season),int(r.week),float(r.offense_snap_share)))

    rows=[]
    no_baseline=0
    no_snap_coverage=0
    # Team-week coverage means another player has snaps, so absence can truthfully mean zero.
    covered_team_weeks=set(zip(snap["season"],snap["week"],snap["team"]))
    for r in injury.itertuples(index=False):
        season=int(r.season); week=int(r.week); team=_team(r.team); pid=str(r.player_id)
        if season>int(trained_through_season):
            continue
        if (season,week,team) not in covered_team_weeks:
            no_snap_coverage+=1
            continue
        prior=[
            share for s,w,share in player_hist.get(pid,[])
            if (s<season or (s==season and w<week)) and share>0
        ]
        if len(prior)<MIN_BASELINE_GAMES:
            no_baseline+=1
            continue
        baseline=float(np.median(prior[-BASELINE_GAMES:]))
        if baseline<=0:
            no_baseline+=1
            continue
        share=float(snap_lookup.get((season,week,team,pid),0.0))
        ratio=share/baseline if share>0 else 0.0
        rows.append(WorkloadObservation(
            season=season,week=week,team=team,player_id=pid,position=str(r.position),
            report_status=str(r.report_status),
            report_timestamp_utc=pd.Timestamp(r.report_timestamp_utc).isoformat(),
            kickoff_utc=pd.Timestamp(r.kickoff_utc).isoformat(),
            offense_snap_share=share,
            prior_baseline_snap_share=baseline,
            workload_ratio=ratio,
            active=share>0,
        ).to_dict())

    frame=pd.DataFrame(rows)
    return frame,{
        "contract_version":CONTRACT_VERSION,
        "trained_through_season":int(trained_through_season),
        "injury_source":injury_audit,
        "snap_rows":int(len(snap)),
        "eligible_observations":int(len(frame)),
        "no_prior_baseline_rows_dropped":no_baseline,
        "uncovered_team_week_rows_dropped":no_snap_coverage,
        "completed_2026_outcomes_used":0,
        "prop_outcomes_used":0,
    }


def fit_workload_mixture(observations: pd.DataFrame) -> dict[str,Any]:
    if observations is None or observations.empty:
        raise AvailabilityMixtureError("no workload observations")
    active=observations[observations["active"].astype(bool)].copy()
    if len(active)<30:
        raise AvailabilityMixtureError("insufficient active workload observations for 3-state mixture")
    log_ratio=np.log(
        pd.to_numeric(active["workload_ratio"],errors="coerce").clip(lower=math.exp(LOG_RATIO_CLIP[0]))
    ).clip(*LOG_RATIO_CLIP)
    if log_ratio.isna().any():
        raise AvailabilityMixtureError("invalid workload ratios")
    model=GaussianMixture(
        n_components=3,
        covariance_type="full",
        n_init=20,
        random_state=RANDOM_STATE,
        reg_covar=1e-4,
    ).fit(log_ratio.to_numpy().reshape(-1,1))
    means=model.means_.reshape(-1)
    order=np.argsort(means)
    component_to_state={int(component):STATE_NAMES[idx] for idx,component in enumerate(order)}
    assigned=model.predict(log_ratio.to_numpy().reshape(-1,1))
    active["workload_state"]=[component_to_state[int(x)] for x in assigned]

    state_params={}
    for component,state in component_to_state.items():
        variance=float(model.covariances_[component].reshape(-1)[0])
        state_params[state]={
            "log_workload_ratio_mean":float(model.means_[component,0]),
            "log_workload_ratio_sd":float(math.sqrt(max(variance,0.0))),
            "mixture_weight":float(model.weights_[component]),
            "median_workload_ratio":float(math.exp(model.means_[component,0])),
            "n_assigned":int((active["workload_state"]==state).sum()),
        }

    full=observations.copy()
    full["workload_state"]="OUT"
    full.loc[full["active"].astype(bool),"workload_state"]=active["workload_state"].to_numpy()

    conditional={}
    for (status,position),group in full.groupby(["report_status","position"],sort=True):
        counts={state:int((group["workload_state"]==state).sum()) for state in ("OUT",*STATE_NAMES)}
        total=sum(counts.values())
        k=len(counts)
        probs={
            state:float((count+DIRICHLET_ALPHA)/(total+DIRICHLET_ALPHA*k))
            for state,count in counts.items()
        }
        conditional[f"{status}|{position}"]={
            "observations":total,
            "counts":counts,
            "smoothed_probabilities":probs,
        }

    out_rate=float((full["workload_state"]=="OUT").mean())
    return {
        "contract_version":CONTRACT_VERSION,
        "research_only":True,
        "production_authorized":False,
        "n_observations":int(len(full)),
        "n_active":int(len(active)),
        "out_rate":out_rate,
        "active_state_parameters":state_params,
        "conditional_state_probabilities":conditional,
        "fit":{
            "algorithm":"3_component_gaussian_mixture_on_log_current_to_prior_snap_share",
            "baseline_games":BASELINE_GAMES,
            "min_baseline_games":MIN_BASELINE_GAMES,
            "log_ratio_clip":list(LOG_RATIO_CLIP),
            "random_state":RANDOM_STATE,
            "dirichlet_alpha":DIRICHLET_ALPHA,
            "bic":float(model.bic(log_ratio.to_numpy().reshape(-1,1))),
            "aic":float(model.aic(log_ratio.to_numpy().reshape(-1,1))),
        },
        "diagnostic_gate":{
            "enough_active_rows":bool(len(active)>=300),
            "each_active_state_weight_at_least_0_05":bool(
                all(v["mixture_weight"]>=0.05 for v in state_params.values())
            ),
            "ordered_median_ratios":[state_params[s]["median_workload_ratio"] for s in STATE_NAMES],
        },
        "prop_outcomes_used":0,
        "completed_2026_outcomes_used":0,
    }
