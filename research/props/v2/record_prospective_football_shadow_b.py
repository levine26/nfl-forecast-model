from __future__ import annotations

"""Record immutable prospective Props 2.0 football Shadow B forecasts.

Shadow B is the frozen secondary candidate:
    V1 + opponent defensive-efficiency residuals + Dynamic Role V0.1 full.

The live V1 manifest remains the source of every non-role input. Dynamic Role V0.1 is derived only
from strictly prior-week snap-count history. Before applying the role multipliers, this runner
reconstructs the captured V1 opportunity distributions from retained evidence and fails closed on
any mismatch.
"""

import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"src"))
HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from nfl_forecast.challenger_props_simulation import (
    build_game_input_from_upstream,
    simulate_game,
)
from nfl_forecast.data import load_advanced_data, load_core_data
from nfl_forecast.props_integration import build_forecast_artifact
from nfl_forecast.props_opportunity import (
    DEFAULT_ALLOCATION_PSEUDOCOUNT,
    _availability_adjusted_allocation,
    _route_redistribution,
)
from nfl_forecast.props_player_sources import normalize_snap_counts_player_ids
from nfl_forecast.props_player_state import normalize_team_code
from nfl_forecast.props_publication import append_jsonl_immutable, read_jsonl

from props_dynamic_role import (
    ENGINE_VERSION as DYNAMIC_ROLE_VERSION,
    build_dynamic_role_adjustments,
)
from record_prospective_football_shadow import (
    FootballShadowError,
    _assert_replay_matches_source,
    _aware,
    _build_game_from_manifest,
    _empirical_distribution_snapshot,
    _finite,
    _forecast_index,
    _load_object,
    _sha,
    apply_shadow_a,
    build_defense_state,
    load_frozen_coefficients,
    load_manifests,
    locate_live_run_root,
)

CONTRACT_VERSION="levline-props-v2-football-shadow-b-v0.1.0"
SHADOW_VERSION="P2-SHADOW-B-DEFENSE-ROLE-v0.1.0"
EVENT_TYPE="FOOTBALL_SHADOW_B_FORECAST_ORIGINAL"
SUPPORTED_PROPS=frozenset({"rushing_yards","receiving_yards"})
ROUTE_PRIORS={"RB":0.55,"WR":0.90,"TE":0.75}
ROUTE_PRIOR_STRENGTH=24.0
HISTORY_START=2019
ATOL=1e-10


class FootballShadowBError(FootballShadowError):
    pass


def _players_frame(projection: Mapping[str,Any])->pd.DataFrame:
    raw=projection.get("players")
    if not isinstance(raw,list) or not raw:
        raise FootballShadowBError("opportunity projection requires non-empty players")
    frame=pd.DataFrame([dict(row) for row in raw if isinstance(row,Mapping)])
    required={"player_id","player_name","position","availability_probability","availability_uncertainty"}
    missing=required-set(frame.columns)
    if missing:
        raise FootballShadowBError(f"projection players missing fields: {sorted(missing)}")
    frame["player_id"]=frame["player_id"].astype(str)
    frame["position"]=frame["position"].astype(str).str.upper()
    frame["role_multiplier"]=1.0
    frame["carry_role_multiplier"]=1.0
    frame["target_role_multiplier"]=1.0
    frame["route_role_multiplier"]=1.0
    return frame


def _ordered(frame: pd.DataFrame, ids: list[str])->pd.DataFrame:
    indexed=frame.set_index("player_id",drop=False)
    missing=[pid for pid in ids if pid not in indexed.index]
    if missing:
        raise FootballShadowBError(f"distribution references missing players: {missing}")
    return indexed.loc[ids].reset_index(drop=True)


def _close(a: Any,b: Any,label: str)->None:
    try:
        av=float(a); bv=float(b)
    except (TypeError,ValueError) as exc:
        raise FootballShadowBError(f"non-numeric baseline comparison for {label}") from exc
    if not (math.isfinite(av) and math.isfinite(bv) and math.isclose(av,bv,rel_tol=0.0,abs_tol=ATOL)):
        raise FootballShadowBError(f"captured V1 opportunity drift for {label}: {av} != {bv}")


def _assert_dirichlet_matches(rebuilt: Mapping[str,Any], captured: Mapping[str,Any], label: str)->None:
    for field in ("concentration","mean_share","variance"):
        left=rebuilt.get(field); right=captured.get(field)
        if not isinstance(left,Mapping) or not isinstance(right,Mapping) or set(left)!=set(right):
            raise FootballShadowBError(f"{label}/{field} identity mismatch")
        for pid in left:
            _close(left[pid],right[pid],f"{label}/{field}/{pid}")
    _close(rebuilt.get("concentration_total"),captured.get("concentration_total"),f"{label}/total")


def _assert_route_matches(rebuilt: list[Mapping[str,Any]], captured: Mapping[str,Any], ids: list[str])->None:
    if set(captured)!=set(ids):
        raise FootballShadowBError("captured route identities differ from target-share identities")
    if len(rebuilt)!=len(ids):
        raise FootballShadowBError("rebuilt route distribution count mismatch")
    for pid,dist in zip(ids,rebuilt):
        current=captured[pid]
        if not isinstance(current,Mapping):
            raise FootballShadowBError(f"captured route distribution invalid for {pid}")
        for field in ("mean","alpha","beta","effective_sample_size"):
            if field in dist or field in current:
                _close(dist.get(field),current.get(field),f"route/{pid}/{field}")


def _apply_adjustments(frame: pd.DataFrame, adjustments: Mapping[str,Mapping[str,float]])->pd.DataFrame:
    out=frame.copy()
    known=set(out["player_id"].astype(str))
    unknown=sorted(set(map(str,adjustments))-known)
    if unknown:
        raise FootballShadowBError(f"role adjustments reference unknown players: {unknown}")
    for pid,values in adjustments.items():
        if not isinstance(values,Mapping):
            raise FootballShadowBError(f"role adjustment for {pid} must be mapping")
        mask=out["player_id"].astype(str).eq(str(pid))
        for field,value in values.items():
            if field not in {"carry_role_multiplier","target_role_multiplier","route_role_multiplier"}:
                raise FootballShadowBError(f"unsupported Shadow B role field: {field}")
            out.loc[mask,field]=float(value)
    return out


def transform_opportunity_projection(
    projection: Mapping[str,Any],
    adjustments: Mapping[str,Mapping[str,float]],
)->tuple[dict[str,Any],dict[str,Any]]:
    out=deepcopy(dict(projection))
    hierarchy=out.get("hierarchy")
    redistribution=out.get("redistribution")
    if not isinstance(hierarchy,dict) or not isinstance(redistribution,dict):
        raise FootballShadowBError("opportunity projection missing hierarchy/redistribution")

    base_players=_players_frame(out)
    dynamic_players=_apply_adjustments(base_players,adjustments)
    audit={"adjustments":{str(k):dict(v) for k,v in adjustments.items()}}

    # Designed carry shares.
    captured_carry=hierarchy.get("designed_carry_share_given_designed_rush")
    if not isinstance(captured_carry,Mapping):
        raise FootballShadowBError("missing designed carry distribution")
    carry_ids=[str(x) for x in captured_carry.get("player_ids",[])]
    carry_base=_ordered(base_players,carry_ids)
    carry_dynamic=_ordered(dynamic_players,carry_ids)
    if "carry_history_effective_opportunities" not in carry_base.columns:
        raise FootballShadowBError("carry history evidence missing from captured projection")
    carry_alpha=(
        pd.to_numeric(carry_base["carry_history_effective_opportunities"],errors="coerce")
        .fillna(0.0).to_numpy(dtype=float)
        + DEFAULT_ALLOCATION_PSEUDOCOUNT
    )
    rebuilt_carry,_,_= _availability_adjusted_allocation(
        carry_base,carry_alpha,label="designed_carry_share",
        multiplier_column="carry_role_multiplier",
    )
    _assert_dirichlet_matches(rebuilt_carry,captured_carry,"carry")
    dynamic_carry,carry_redist,_=_availability_adjusted_allocation(
        carry_dynamic,carry_alpha,label="designed_carry_share",
        multiplier_column="carry_role_multiplier",
    )
    hierarchy["designed_carry_share_given_designed_rush"]=dynamic_carry
    redistribution["designed_carries"]=carry_redist

    # Target shares.
    captured_target=hierarchy.get("target_share_given_team_target")
    if not isinstance(captured_target,Mapping):
        raise FootballShadowBError("missing target distribution")
    target_ids=[str(x) for x in captured_target.get("player_ids",[])]
    target_base=_ordered(base_players,target_ids)
    target_dynamic=_ordered(dynamic_players,target_ids)
    if "target_history_effective_opportunities" not in target_base.columns:
        raise FootballShadowBError("target history evidence missing from captured projection")
    target_alpha=(
        pd.to_numeric(target_base["target_history_effective_opportunities"],errors="coerce")
        .fillna(0.0).to_numpy(dtype=float)
        + DEFAULT_ALLOCATION_PSEUDOCOUNT
    )
    rebuilt_target,_,_=_availability_adjusted_allocation(
        target_base,target_alpha,label="target_share",
        multiplier_column="target_role_multiplier",
    )
    _assert_dirichlet_matches(rebuilt_target,captured_target,"target")
    dynamic_target,target_redist,_=_availability_adjusted_allocation(
        target_dynamic,target_alpha,label="target_share",
        multiplier_column="target_role_multiplier",
    )
    hierarchy["target_share_given_team_target"]=dynamic_target
    redistribution["targets"]=target_redist

    # Route participation.
    captured_routes=hierarchy.get("route_participation_given_dropback")
    route_info=redistribution.get("routes")
    if not isinstance(captured_routes,Mapping) or not isinstance(route_info,Mapping):
        raise FootballShadowBError("missing route distribution/audit")
    baseline_participation=route_info.get("baseline_participation")
    if not isinstance(baseline_participation,Mapping):
        raise FootballShadowBError("captured route baseline participation missing")
    route_ids=target_ids
    route_base=_ordered(base_players,route_ids)
    route_dynamic=_ordered(dynamic_players,route_ids)
    if "route_history_effective_dropbacks" not in route_base.columns:
        raise FootballShadowBError("route history evidence missing from captured projection")
    try:
        route_means=np.asarray([float(baseline_participation[pid]) for pid in route_ids],dtype=float)
    except KeyError as exc:
        raise FootballShadowBError(f"route baseline missing player {exc}") from exc
    route_strength=(
        pd.to_numeric(route_base["route_history_effective_dropbacks"],errors="coerce")
        .fillna(0.0).to_numpy(dtype=float)
        + ROUTE_PRIOR_STRENGTH
    )
    rebuilt_routes,_,_=_route_redistribution(route_base,route_means,route_strength)
    _assert_route_matches(rebuilt_routes,captured_routes,route_ids)
    dynamic_routes,route_redist,_=_route_redistribution(
        route_dynamic,route_means,route_strength
    )
    hierarchy["route_participation_given_dropback"]={
        pid:dist for pid,dist in zip(route_ids,dynamic_routes)
    }
    redistribution["routes"]=route_redist

    audit.update({
        "baseline_reconstruction_verified":True,
        "carry_player_count":len(carry_ids),
        "target_player_count":len(target_ids),
        "route_player_count":len(route_ids),
    })
    return out,audit


def _current_players(projections: list[Mapping[str,Any]])->pd.DataFrame:
    frames=[]
    for projection in projections:
        metadata=projection.get("metadata")
        if not isinstance(metadata,Mapping):
            raise FootballShadowBError("projection metadata missing")
        team=str(metadata.get("team") or "").upper()
        frame=_players_frame(projection)[["player_id","player_name","position"]].copy()
        frame["team"]=team
        frames.append(frame)
    return pd.concat(frames,ignore_index=True)


def role_adjustments_for_manifest(
    manifest: Mapping[str,Any],
    snap_counts: pd.DataFrame,
)->tuple[list[dict[str,Any]],dict[str,Any]]:
    projections=manifest.get("opportunity_projections")
    if not isinstance(projections,list) or len(projections)!=2:
        raise FootballShadowBError("manifest requires two opportunity projections")
    current=_current_players(projections)
    season=int(projections[0]["metadata"]["season"])
    week=int(projections[0]["metadata"]["week"])
    transformed=[]
    audit={}
    for projection in projections:
        team=str(projection["metadata"]["team"]).upper()
        adjustments,role_audit=build_dynamic_role_adjustments(
            snap_counts,current,season=season,week=week,team=team,
            route_prior_means=ROUTE_PRIORS,mode="full",
        )
        updated,transform_audit=transform_opportunity_projection(projection,adjustments)
        transformed.append(updated)
        audit[team]={
            "dynamic_role":role_audit,
            "transform":transform_audit,
        }
    return transformed,audit


def _apply_defense_to_game(game, defense_state: Mapping[str,Any], frozen: Mapping[str,Any]):
    players=[]
    audit={}
    for player in game.players:
        opponent=normalize_team_code(str(player.opponent))
        if opponent not in defense_state:
            raise FootballShadowBError(f"missing defense state for {opponent}")
        rush=defense_state[opponent]["rushing"]
        rec=defense_state[opponent]["receiving"]
        rush_mean=adjusted_mean(
            float(player.rushing_yards_per_carry),
            float(rush["opponent_defense_delta"]),
            frozen["fits"]["rushing"],
        )
        rec_mean=adjusted_mean(
            float(player.receiving_yards_per_reception),
            float(rec["opponent_defense_delta"]),
            frozen["fits"]["receiving"],
        )
        players.append(replace(
            player,
            rushing_yards_per_carry=rush_mean,
            receiving_yards_per_reception=rec_mean,
        ))
        audit[player.player_id]={
            "base_rushing_yards_per_carry":float(player.rushing_yards_per_carry),
            "shadow_rushing_yards_per_carry":rush_mean,
            "rushing_defense_state":dict(rush),
            "base_receiving_yards_per_reception":float(player.receiving_yards_per_reception),
            "shadow_receiving_yards_per_reception":rec_mean,
            "receiving_defense_state":dict(rec),
        }
    return replace(game,players=tuple(players),model_version=SHADOW_VERSION),audit


def _role_player_audit(role_audit: Mapping[str,Any])->dict[str,Any]:
    out={}
    for team,team_audit in role_audit.items():
        dynamic=team_audit.get("dynamic_role",{})
        adjustments=team_audit.get("transform",{}).get("adjustments",{})
        estimates=dynamic.get("estimates",[]) if isinstance(dynamic,Mapping) else []
        estimate_by_id={
            str(row.get("player_id")):dict(row)
            for row in estimates if isinstance(row,Mapping) and row.get("player_id")
        }
        ids=set(estimate_by_id)|set(map(str,adjustments))
        for pid in ids:
            out[pid]={
                "team":team,
                "adjustment":dict(adjustments.get(pid,{})),
                "estimate":estimate_by_id.get(pid),
                "engine_version":dynamic.get("engine_version"),
                "mode":dynamic.get("mode"),
                "history":dynamic.get("history"),
            }
    return out


def _shadow_id(source_forecast_id: str)->str:
    return "props_football_shadow_b_"+_sha({
        "source_forecast_id":source_forecast_id,
        "shadow_version":SHADOW_VERSION,
        "contract_version":CONTRACT_VERSION,
    })[:24]


def build_receipt(
    *,
    source: Mapping[str,Any],
    shadow: Mapping[str,Any],
    manifest: Mapping[str,Any],
    defense_player_audit: Mapping[str,Any],
    role_player_audit: Mapping[str,Any],
    frozen: Mapping[str,Any],
    recorded_utc: datetime,
    source_workflow_run: str,
    source_head_sha: str,
    v1_samples: Any,
    shadow_samples: Any,
)->dict[str,Any]|None:
    source_id=str(source.get("forecast_id") or "").strip()
    prop_type=str(source.get("prop_type") or "").strip()
    if not source_id or prop_type not in SUPPORTED_PROPS:
        return None
    kickoff=_aware(source.get("kickoff_utc"),label="kickoff_utc")
    forecast_at=_aware(source.get("forecast_timestamp_utc"),label="forecast_timestamp_utc")
    market=source.get("market") if isinstance(source.get("market"),Mapping) else {}
    captured=market.get("captured_utc")
    line=_finite(market.get("line"))
    no_vig=_finite(market.get("no_vig_over_probability"))
    if captured is None or line is None or no_vig is None:
        return None
    market_at=_aware(captured,label="market captured_utc")
    recorded=recorded_utc.astimezone(timezone.utc)
    if not (forecast_at<kickoff and market_at<kickoff and recorded<kickoff):
        return None
    if forecast_at>recorded or market_at>recorded:
        return None

    pid=str(source.get("player_id") or "")
    defense=defense_player_audit.get(pid)
    if not isinstance(defense,Mapping):
        raise FootballShadowBError(f"missing defense audit for {pid}")
    role=role_player_audit.get(pid,{
        "adjustment":{},
        "estimate":None,
        "engine_version":DYNAMIC_ROLE_VERSION,
        "mode":"full",
    })
    event_type="rushing" if prop_type=="rushing_yards" else "receiving"
    source_model=source.get("model") if isinstance(source.get("model"),Mapping) else {}
    shadow_model=shadow.get("model") if isinstance(shadow.get("model"),Mapping) else {}

    receipt={
        "contract_version":CONTRACT_VERSION,
        "event_type":EVENT_TYPE,
        "shadow_id":_shadow_id(source_id),
        "shadow_version":SHADOW_VERSION,
        "capture_started_utc":capture_started.isoformat(),
        "capture_completed_utc":capture_clock().isoformat(),
        "source_workflow_run":str(source_workflow_run),
        "source_head_sha":str(source_head_sha),
        "source_forecast_id":source_id,
        "source_forecast_sha256":_sha(dict(source)),
        "source_manifest_sha256":str(manifest.get("manifest_sha256") or ""),
        "source_forecast_timestamp_utc":forecast_at.isoformat(),
        "source_data_horizon_utc":source.get("data_horizon_utc"),
        "source_market_captured_utc":market_at.isoformat(),
        "source_signal_state":str(source.get("signal_state") or ""),
        "source_data_quality":dict(source.get("data_quality")) if isinstance(source.get("data_quality"),Mapping) else {},
        "kickoff_utc":kickoff.isoformat(),
        "game_id":str(source.get("game_id") or ""),
        "player_id":pid,
        "player":str(source.get("player") or ""),
        "position":str(source.get("position") or ""),
        "team":str(source.get("team") or ""),
        "opponent":str(source.get("opponent") or ""),
        "prop_type":prop_type,
        "market":{
            "line":line,
            "no_vig_over_probability":no_vig,
            "over_price_american":_finite(market.get("over_price_american")),
            "under_price_american":_finite(market.get("under_price_american")),
        },
        "v1":{
            "model_version":source_model.get("version"),
            "fair_line":_finite(source_model.get("fair_line")),
            "over_probability":_finite(source_model.get("over_probability")),
            "under_probability":_finite(source_model.get("under_probability")),
            "standard_deviation":_finite(source_model.get("standard_deviation")),
            "prediction_interval":source_model.get("prediction_interval"),
            "empirical_distribution":_empirical_distribution_snapshot(v1_samples),
        },
        "shadow_b":{
            "model_version":shadow_model.get("version"),
            "fair_line":_finite(shadow_model.get("fair_line")),
            "over_probability":_finite(shadow_model.get("over_probability")),
            "under_probability":_finite(shadow_model.get("under_probability")),
            "standard_deviation":_finite(shadow_model.get("standard_deviation")),
            "prediction_interval":shadow_model.get("prediction_interval"),
            "empirical_distribution":_empirical_distribution_snapshot(shadow_samples),
        },
        "defensive_efficiency":{
            "event_type":event_type,
            "base_mean":defense[f"base_{event_type}_yards_per_"+("carry" if event_type=="rushing" else "reception")],
            "shadow_mean":defense[f"shadow_{event_type}_yards_per_"+("carry" if event_type=="rushing" else "reception")],
            "state":defense[f"{event_type}_defense_state"],
            "fit":dict(frozen["fits"][event_type]),
            "coefficient_contract_version":frozen["contract_version"],
        },
        "dynamic_role_v01":dict(role),
        "governance":{
            "production_authorized":False,
            "published_v1_props_mutated":False,
            "winner_model_mutated":False,
            "target_week_outcomes_used":0,
            "completed_2026_outcomes_used_for_model_selection":0,
            "captured_v1_baseline_reconstructed_before_role_transform":True,
            "dynamic_role_mode":"full",
        },
    }
    receipt["shadow_sha256"]=_sha(receipt)
    return receipt


def record_shadow_b(
    artifact_root: Path,
    frozen_path: Path,
    ledger: Path,
    *,
    source_workflow_run: str,
    source_head_sha: str,
    recorded_utc: datetime|None=None,
)->dict[str,Any]:
    frozen=load_frozen_coefficients(frozen_path)
    run_root=locate_live_run_root(artifact_root)
    upstream=_load_object(run_root/"upstream"/"upstream_slate.json")
    season=int(upstream["season"]); week=int(upstream["week"])
    captured=_aware(upstream.get("captured_at_utc"),label="upstream captured_at_utc")
    def capture_clock()->datetime:
        if recorded_utc is not None:
            return recorded_utc.astimezone(timezone.utc)
        return datetime.now(timezone.utc)

    capture_started=capture_clock()
    if capture_started<captured:
        raise FootballShadowBError("shadow cannot precede source upstream capture")

    _,manifests=load_manifests(run_root)
    source_artifact=_load_object(run_root/"forecasts.json")
    source_index=_forecast_index(source_artifact)

    seasons=list(range(HISTORY_START,season+1))
    bundle=load_core_data(seasons)
    bundle=load_advanced_data(bundle,seasons)
    pbp=bundle.pbp.to_pandas() if hasattr(bundle.pbp,"to_pandas") else bundle.pbp.copy()
    players=nfl.load_players()
    players=players.to_pandas() if hasattr(players,"to_pandas") else players.copy()
    snap_counts,snap_identity_audit=normalize_snap_counts_player_ids(bundle.snap_counts,players)

    teams={normalize_team_code(str(m["home_team"])) for m in manifests}|{
        normalize_team_code(str(m["away_team"])) for m in manifests
    }
    defense_state,defense_audit=build_defense_state(
        pbp,target_season=season,target_week=week,teams=teams
    )

    existing=read_jsonl(ledger) if ledger.exists() else []
    existing_ids={
        str(row.get("shadow_id")) for row in existing
        if isinstance(row,dict) and row.get("shadow_id")
    }

    receipts=[]
    skipped_started=0
    skipped_existing=0
    eligible_source_rows=0
    game_audit={}

    for manifest in manifests:
        kickoff=_aware(manifest["kickoff_utc"],label="manifest kickoff_utc")
        if capture_clock()>=kickoff:
            skipped_started+=1
            continue

        baseline_game=_build_game_from_manifest(manifest)
        baseline=simulate_game(
            baseline_game,
            simulations=int(manifest.get("simulations",20000)),
            seed=int(manifest.get("seed",0)),
        )
        baseline_artifact=build_forecast_artifact(
            baseline,manifest["market_artifacts"],
            kickoff_utc=manifest["kickoff_utc"],
            forecast_timestamp_utc=manifest["forecast_timestamp_utc"],
            interval_level=float(manifest.get("prediction_interval_level",0.80)),
        )

        transformed_projections,role_audit=role_adjustments_for_manifest(manifest,snap_counts)
        role_game=build_game_input_from_upstream(
            home_team=str(manifest["home_team"]),
            away_team=str(manifest["away_team"]),
            opportunity_projections=transformed_projections,
            efficiency_player_parameters=manifest["efficiency_player_parameters"],
            team_td_parameters=manifest["team_td_parameters"],
            residual_efficiency_by_team=manifest["residual_efficiency_by_team"],
            model_version="P2-DYNAMIC-ROLE-V01-FULL-PREGAME",
            shared_pace_correlation=float(manifest.get("shared_pace_correlation",0.0)),
            shared_scoring_log_sd=float(manifest.get("shared_scoring_log_sd",0.0)),
            pass_rate_game_script_sensitivity=float(manifest.get("pass_rate_game_script_sensitivity",0.0)),
        )
        role_result=simulate_game(
            role_game,
            simulations=int(manifest.get("simulations",20000)),
            seed=int(manifest.get("seed",0)),
        )
        defense_result,defense_player_audit=apply_shadow_a(
            role_result,defense_state=defense_state,frozen=frozen
        )
        shadow=replace(defense_result,model_version=SHADOW_VERSION)
        shadow_artifact=build_forecast_artifact(
            shadow,manifest["market_artifacts"],
            kickoff_utc=manifest["kickoff_utc"],
            forecast_timestamp_utc=manifest["forecast_timestamp_utc"],
            interval_level=float(manifest.get("prediction_interval_level",0.80)),
        )

        baseline_index=_forecast_index(baseline_artifact)
        shadow_index=_forecast_index(shadow_artifact)
        role_player=_role_player_audit(role_audit)
        game_id=str(manifest["game_id"])
        game_receipts=0

        receipt_recorded=capture_clock()
        if receipt_recorded>=kickoff:
            skipped_started+=1
            continue

        for key,replay in baseline_index.items():
            if key[0]!=game_id or key[2] not in SUPPORTED_PROPS:
                continue
            source=source_index.get(key)
            shadow_row=shadow_index.get(key)
            if source is None or shadow_row is None:
                raise FootballShadowBError(f"missing paired source/shadow row: {key}")
            _assert_replay_matches_source(replay,source)
            eligible_source_rows+=1
            sid=_shadow_id(str(source.get("forecast_id") or ""))
            if sid in existing_ids:
                skipped_existing+=1
                continue
            receipt=build_receipt(
                source=source,shadow=shadow_row,manifest=manifest,
                defense_player_audit=defense_player_audit,
                role_player_audit=role_player,frozen=frozen,
                recorded_utc=receipt_recorded,
                source_workflow_run=source_workflow_run,
                source_head_sha=source_head_sha,
                v1_samples=baseline.player_stats[str(source["player_id"])][str(source["prop_type"])],
                shadow_samples=shadow.player_stats[str(source["player_id"])][str(source["prop_type"])],
            )
            if receipt is None:
                continue
            receipts.append(receipt)
            existing_ids.add(receipt["shadow_id"])
            game_receipts+=1

        game_audit[game_id]={
            "source_manifest_sha256":manifest.get("manifest_sha256"),
            "new_receipts":game_receipts,
            "role_audit":role_audit,
            "captured_v1_baseline_reconstruction_verified":True,
        }

    ledger.parent.mkdir(parents=True,exist_ok=True)
    appended=append_jsonl_immutable(ledger,receipts,identity_key="shadow_id") if receipts else 0
    return {
        "contract_version":CONTRACT_VERSION,
        "shadow_version":SHADOW_VERSION,
        "recorded_utc":recorded.isoformat(),
        "source_workflow_run":str(source_workflow_run),
        "source_head_sha":str(source_head_sha),
        "source_season":season,
        "source_week":week,
        "source_game_count":len(manifests),
        "eligible_source_rows":eligible_source_rows,
        "new_receipts":len(receipts),
        "appended":int(appended),
        "skipped_existing":skipped_existing,
        "skipped_started_games":skipped_started,
        "snap_identity_audit":snap_identity_audit,
        "defense_state_audit":defense_audit,
        "game_audit":game_audit,
        "production_authorized":False,
        "winner_model_mutated":False,
        "published_v1_props_mutated":False,
        "target_outcomes_read":0,
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact-root",type=Path,required=True)
    parser.add_argument("--frozen-coefficients",type=Path,required=True)
    parser.add_argument("--ledger",type=Path,required=True)
    parser.add_argument("--source-workflow-run",required=True)
    parser.add_argument("--source-head-sha",required=True)
    args=parser.parse_args()
    result=record_shadow_b(
        args.artifact_root,args.frozen_coefficients,args.ledger,
        source_workflow_run=args.source_workflow_run,
        source_head_sha=args.source_head_sha,
    )
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
