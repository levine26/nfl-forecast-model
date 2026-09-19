from __future__ import annotations

"""Record immutable prospective Props 2.0 football Shadow A forecasts.

The runner consumes the full audit artifact from a successful main-branch live Props refresh.
It replays V1 from the exact frozen per-game manifest, verifies that replay against the source
forecast artifact, then applies only the frozen opponent defensive-efficiency mechanism.
"""

import argparse
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
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

from nfl_forecast.challenger_props_simulation import (  # noqa:E402
    _compound_yards,
    build_game_input_from_upstream,
    simulate_game,
)
from nfl_forecast.data import load_core_data  # noqa:E402
from nfl_forecast.props_integration import build_forecast_artifact  # noqa:E402
from nfl_forecast.props_manifest import (  # noqa:E402
    verify_manifest_fingerprint,
    verify_manifest_slate_index,
)
from nfl_forecast.props_player_state import normalize_team_code  # noqa:E402
from nfl_forecast.props_publication import append_jsonl_immutable, read_jsonl  # noqa:E402
from nfl_forecast.props_upstream import normalize_nflverse_scramble_semantics  # noqa:E402

CONTRACT_VERSION="levline-props-v2-football-shadow-a-v0.1.0"
SHADOW_VERSION="P2-SHADOW-A-DEFENSE-v0.1.0"
FROZEN_COEFFICIENT_VERSION="levline-props-v2-defensive-efficiency-shadow-v0.1.0"
RETROSPECTIVE_MECHANISM_VERSION="levline-props-v2-defensive-efficiency-pregame-v0.1.0"
EVENT_TYPE="FOOTBALL_SHADOW_FORECAST_ORIGINAL"
SUPPORTED_PROPS=frozenset({"rushing_yards","receiving_yards"})
HISTORY_START=2019
DEFENSE_LOOKBACK_GAMES=8
DEFENSE_PRIOR_EVENTS=80.0
MIN_ADJUSTED_MEAN=0.05
OPPORTUNITY_KEYS=(
    "active",
    "pass_attempts",
    "routes",
    "targets",
    "receptions",
    "carries",
)


class FootballShadowError(ValueError):
    pass


def _canon(value: Any)->str:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    )


def _sha(value: Any)->str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _stable_seed(*parts: Any)->int:
    digest=hashlib.sha256("|".join(map(str,parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:8],"big")%(2**32-1)


def _aware(value: Any, *, label: str)->datetime:
    try:
        parsed=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    except ValueError as exc:
        raise FootballShadowError(f"{label} is not ISO datetime") from exc
    if parsed.tzinfo is None:
        raise FootballShadowError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _finite(value: Any)->float|None:
    try:
        parsed=float(value)
    except (TypeError,ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def load_frozen_coefficients(path: Path)->dict[str,Any]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise FootballShadowError("frozen coefficient file must be an object")
    if payload.get("contract_version")!=FROZEN_COEFFICIENT_VERSION:
        raise FootballShadowError("unexpected defensive-efficiency coefficient version")
    if int(payload.get("trained_through_season",-1))!=2025:
        raise FootballShadowError("defensive coefficients must be frozen through 2025")
    for field in ("completed_2026_outcomes_used","prop_outcomes_used","sportsbook_results_used"):
        if int(payload.get(field,-1))!=0:
            raise FootballShadowError(f"frozen coefficients violate firewall: {field}")
    if payload.get("production_authorized") is not False:
        raise FootballShadowError("frozen coefficients cannot be production authorized")
    fits=payload.get("fits")
    if not isinstance(fits,dict) or set(fits)!={"rushing","receiving"}:
        raise FootballShadowError("frozen coefficients require rushing and receiving fits")
    required={"x_mean","x_sd","intercept","beta_standardized","ridge_alpha","trained_through_season"}
    for event_type,fit in fits.items():
        if not isinstance(fit,dict) or not required.issubset(fit):
            raise FootballShadowError(f"incomplete frozen {event_type} fit")
        if int(fit["trained_through_season"])!=2025:
            raise FootballShadowError(f"{event_type} fit is not frozen through 2025")
        for field in ("x_mean","x_sd","intercept","beta_standardized","ridge_alpha"):
            value=_finite(fit[field])
            if value is None:
                raise FootballShadowError(f"non-finite {event_type}/{field}")
        if float(fit["x_sd"])<=0:
            raise FootballShadowError(f"{event_type} x_sd must be positive")
    return payload


def locate_live_run_root(artifact_root: Path)->Path:
    slates=sorted(artifact_root.rglob("manifest_slate.json"))
    if len(slates)!=1:
        raise FootballShadowError(
            f"expected exactly one manifest_slate.json in live artifact; found {len(slates)}"
        )
    manifest_slate=slates[0]
    run_root=manifest_slate.parent.parent
    required=[
        run_root/"forecasts.json",
        run_root/"market.json",
        run_root/"upstream"/"upstream_slate.json",
        manifest_slate,
    ]
    missing=[str(path) for path in required if not path.is_file()]
    if missing:
        raise FootballShadowError(f"live artifact missing required files: {missing}")
    return run_root


def _load_object(path: Path)->dict[str,Any]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload,dict):
        raise FootballShadowError(f"{path} must contain a JSON object")
    return payload


def load_manifests(run_root: Path)->tuple[dict[str,Any],list[dict[str,Any]]]:
    slate_path=run_root/"manifests"/"manifest_slate.json"
    slate=_load_object(slate_path)
    verify_manifest_slate_index(slate)
    entries=slate.get("games")
    if not isinstance(entries,list) or not entries:
        raise FootballShadowError("manifest slate has no games")

    manifests=[]
    seen=set()
    for entry in entries:
        if not isinstance(entry,dict):
            raise FootballShadowError("manifest slate game entry must be object")
        game_id=str(entry.get("game_id") or "").strip()
        relative=str(entry.get("manifest_file") or "").strip()
        expected_sha=str(entry.get("manifest_sha256") or "").strip()
        if not game_id or not relative or not expected_sha:
            raise FootballShadowError("manifest slate entry missing identity/fingerprint")
        path=(slate_path.parent/relative).resolve()
        try:
            path.relative_to(slate_path.parent.resolve())
        except ValueError as exc:
            raise FootballShadowError("manifest path escapes manifest root") from exc
        manifest=_load_object(path)
        verify_manifest_fingerprint(manifest)
        if str(manifest.get("game_id") or "")!=game_id:
            raise FootballShadowError("manifest game_id disagrees with slate")
        if str(manifest.get("manifest_sha256") or "")!=expected_sha:
            raise FootballShadowError("manifest fingerprint disagrees with slate")
        if game_id in seen:
            raise FootballShadowError(f"duplicate manifest game_id: {game_id}")
        seen.add(game_id)
        manifests.append(manifest)
    return slate,manifests


def _player_positions()->dict[str,str]:
    players=nfl.load_players()
    players=players.to_pandas() if hasattr(players,"to_pandas") else players.copy()
    id_col=next((c for c in ("gsis_id","player_id") if c in players.columns),None)
    pos_col=next((c for c in ("position","position_group") if c in players.columns),None)
    if id_col is None or pos_col is None:
        raise FootballShadowError("players source missing stable ID/position")
    work=players[[id_col,pos_col]].copy()
    work[id_col]=work[id_col].astype("string").fillna("").str.strip()
    work[pos_col]=work[pos_col].astype("string").fillna("").str.upper().str.strip()
    work=work[
        work[id_col].ne("")
        & work[pos_col].isin({"QB","RB","WR","TE"})
    ].drop_duplicates(id_col,keep="last")
    return dict(zip(work[id_col].astype(str),work[pos_col].astype(str)))


def _event_frame(
    pbp: pd.DataFrame,
    event_type: str,
    positions: Mapping[str,str],
)->pd.DataFrame:
    if "defteam" not in pbp.columns:
        raise FootballShadowError("PBP missing defteam")
    if event_type=="rushing":
        mask=pd.to_numeric(pbp.get("rush_attempt",0),errors="coerce").fillna(0).eq(1)
        yards_col="rushing_yards" if "rushing_yards" in pbp.columns else "yards_gained"
        id_col=next((c for c in ("rusher_player_id","rusher_id") if c in pbp.columns),None)
    elif event_type=="receiving":
        mask=pd.to_numeric(pbp.get("complete_pass",0),errors="coerce").fillna(0).eq(1)
        yards_col="receiving_yards" if "receiving_yards" in pbp.columns else "yards_gained"
        id_col=next((c for c in ("receiver_player_id","receiver_id") if c in pbp.columns),None)
    else:
        raise FootballShadowError(f"unsupported event_type {event_type}")
    if yards_col not in pbp.columns or id_col is None:
        raise FootballShadowError(f"PBP missing {event_type} yardage or stable player identity")
    yards=pd.to_numeric(pbp[yards_col],errors="coerce")
    player_id=pbp[id_col].astype("string").fillna("").str.strip()
    position=player_id.map(positions).astype("string").fillna("").str.upper().str.strip()
    eligible=position.isin({"QB","RB","WR","TE"})
    frame=pbp.loc[
        mask & yards.notna() & player_id.ne("") & eligible,
        [c for c in ("game_id","season","week","defteam") if c in pbp.columns],
    ].copy()
    frame["yards"]=yards.loc[frame.index].astype(float)
    frame["defteam"]=frame["defteam"].map(normalize_team_code)
    frame=frame[frame["defteam"].astype(str).ne("")].copy()
    frame["season"]=pd.to_numeric(frame["season"],errors="coerce")
    frame["week"]=pd.to_numeric(frame["week"],errors="coerce")
    return frame[frame["season"].notna() & frame["week"].notna()].copy()


def build_defense_state(
    pbp: pd.DataFrame,
    *,
    target_season: int,
    target_week: int,
    teams: set[str],
)->tuple[dict[str,dict[str,dict[str,float]]],dict[str,Any]]:
    normalized,norm_audit=normalize_nflverse_scramble_semantics(pbp)
    work=normalized.copy()
    if "season_type" in work.columns:
        work=work[work["season_type"].astype(str).str.upper().eq("REG")].copy()
    elif "game_type" in work.columns:
        work=work[work["game_type"].astype(str).str.upper().eq("REG")].copy()

    season=pd.to_numeric(work["season"],errors="coerce")
    week=pd.to_numeric(work["week"],errors="coerce")
    prior=(season<int(target_season)) | (
        season.eq(int(target_season)) & week.lt(int(target_week))
    )
    work=work[prior].copy()
    if work.empty:
        raise FootballShadowError("no strictly prior-week PBP available for defense state")

    positions=_player_positions()
    state={normalize_team_code(team):{} for team in teams}
    audit={"pbp_normalization":norm_audit,"target_season":int(target_season),"target_week":int(target_week),"events":{}}

    for event_type in ("rushing","receiving"):
        events=_event_frame(work,event_type,positions)
        if events.empty:
            raise FootballShadowError(f"no prior {event_type} events")
        league_mean=float(events["yards"].mean())
        grouped=(
            events.groupby(["season","week","game_id","defteam"],as_index=False,sort=True)
            .agg(event_yards=("yards","sum"),event_count=("yards","size"))
            .sort_values(["season","week","game_id"])
        )
        audit["events"][event_type]={
            "prior_events":int(len(events)),
            "league_yards_per_event":league_mean,
        }
        for team in sorted(state):
            team_games=grouped[grouped["defteam"].eq(team)].tail(DEFENSE_LOOKBACK_GAMES)
            if team_games.empty:
                raise FootballShadowError(f"no prior {event_type} defense games for {team}")
            yards=float(team_games["event_yards"].sum())
            count=int(team_games["event_count"].sum())
            shrunk=(yards+DEFENSE_PRIOR_EVENTS*league_mean)/(count+DEFENSE_PRIOR_EVENTS)
            delta=float(shrunk-league_mean)
            state[team][event_type]={
                "opponent_defense_yards_per_event":float(shrunk),
                "league_yards_per_event":league_mean,
                "opponent_defense_delta":delta,
                "prior_games":int(len(team_games)),
                "prior_events":count,
            }
    return state,audit


def adjusted_mean(base_mean: float, defense_delta: float, fit: Mapping[str,Any])->float:
    x_sd=max(float(fit["x_sd"]),1e-9)
    z=(float(defense_delta)-float(fit["x_mean"]))/x_sd
    correction=float(fit["intercept"])+float(fit["beta_standardized"])*z
    return float(max(MIN_ADJUSTED_MEAN,float(base_mean)+correction))


def apply_shadow_a(
    baseline,
    *,
    defense_state: Mapping[str,Mapping[str,Mapping[str,float]]],
    frozen: Mapping[str,Any],
):
    challenger=deepcopy(baseline)
    player_audit={}
    for player in baseline.players:
        stats=challenger.player_stats[player.player_id]
        opponent=normalize_team_code(str(player.opponent))
        if opponent not in defense_state:
            raise FootballShadowError(f"missing defense state for {opponent}")

        original={key:np.asarray(baseline.player_stats[player.player_id][key]).copy()
                  for key in OPPORTUNITY_KEYS if key in baseline.player_stats[player.player_id]}

        rush_state=defense_state[opponent]["rushing"]
        rec_state=defense_state[opponent]["receiving"]
        rush_mean=adjusted_mean(
            float(player.rushing_yards_per_carry),
            float(rush_state["opponent_defense_delta"]),
            frozen["fits"]["rushing"],
        )
        rec_mean=adjusted_mean(
            float(player.receiving_yards_per_reception),
            float(rec_state["opponent_defense_delta"]),
            frozen["fits"]["receiving"],
        )

        rush_rng=np.random.default_rng(
            _stable_seed(RETROSPECTIVE_MECHANISM_VERSION,"rushing",baseline.game_id,player.player_id)
        )
        rec_rng=np.random.default_rng(
            _stable_seed(RETROSPECTIVE_MECHANISM_VERSION,"receiving",baseline.game_id,player.player_id)
        )
        stats["rushing_yards"]=_compound_yards(
            np.asarray(stats["carries"]),
            rush_mean,
            float(player.rushing_yards_shape_per_carry),
            rush_rng,
            event_sd=player.rushing_yards_per_carry_event_sd,
            mean_se=float(player.rushing_yards_per_carry_mean_se),
        )
        stats["receiving_yards"]=_compound_yards(
            np.asarray(stats["receptions"]),
            rec_mean,
            float(player.receiving_yards_shape_per_reception),
            rec_rng,
            event_sd=player.receiving_yards_per_reception_event_sd,
            mean_se=float(player.receiving_yards_per_reception_mean_se),
        )

        for key,expected in original.items():
            if not np.array_equal(expected,np.asarray(stats[key])):
                raise FootballShadowError(
                    f"Shadow A modified opportunity array {player.player_id}/{key}"
                )
        player_audit[player.player_id]={
            "opponent":opponent,
            "base_rushing_yards_per_carry":float(player.rushing_yards_per_carry),
            "shadow_rushing_yards_per_carry":rush_mean,
            "rushing_defense_state":dict(rush_state),
            "base_receiving_yards_per_reception":float(player.receiving_yards_per_reception),
            "shadow_receiving_yards_per_reception":rec_mean,
            "receiving_defense_state":dict(rec_state),
        }

    return replace(challenger,model_version=SHADOW_VERSION),player_audit


def _build_game_from_manifest(manifest: Mapping[str,Any]):
    return build_game_input_from_upstream(
        home_team=str(manifest["home_team"]),
        away_team=str(manifest["away_team"]),
        opportunity_projections=manifest["opportunity_projections"],
        efficiency_player_parameters=manifest["efficiency_player_parameters"],
        team_td_parameters=manifest["team_td_parameters"],
        residual_efficiency_by_team=manifest["residual_efficiency_by_team"],
        model_version=str(manifest.get("model_version") or "levline-props-simulation-v0.1.0"),
        shared_pace_correlation=float(manifest.get("shared_pace_correlation",0.0)),
        shared_scoring_log_sd=float(manifest.get("shared_scoring_log_sd",0.0)),
        pass_rate_game_script_sensitivity=float(
            manifest.get("pass_rate_game_script_sensitivity",0.0)
        ),
    )


def _forecast_index(artifact: Mapping[str,Any])->dict[tuple[str,str,str],dict[str,Any]]:
    rows=artifact.get("forecasts")
    if not isinstance(rows,list):
        raise FootballShadowError("source forecasts artifact lacks forecasts list")
    out={}
    for row in rows:
        if not isinstance(row,dict):
            continue
        key=(
            str(row.get("game_id") or ""),
            str(row.get("player_id") or ""),
            str(row.get("prop_type") or ""),
        )
        if key in out:
            raise FootballShadowError(f"duplicate source forecast key: {key}")
        out[key]=row
    return out


def _assert_replay_matches_source(replay: Mapping[str,Any], source: Mapping[str,Any])->None:
    replay_model=replay.get("model") if isinstance(replay.get("model"),Mapping) else {}
    source_model=source.get("model") if isinstance(source.get("model"),Mapping) else {}
    for field in ("fair_line","over_probability","under_probability"):
        a=_finite(replay_model.get(field))
        b=_finite(source_model.get(field))
        if a is None and b is None:
            continue
        if a is None or b is None or not math.isclose(a,b,rel_tol=0.0,abs_tol=1e-12):
            raise FootballShadowError(
                f"baseline replay drift for {source.get('forecast_id')}/{field}: {a} != {b}"
            )


def _shadow_id(source_forecast_id: str)->str:
    return "props_football_shadow_"+_sha({
        "source_forecast_id":source_forecast_id,
        "shadow_version":SHADOW_VERSION,
        "contract_version":CONTRACT_VERSION,
    })[:24]


def build_receipt(
    *,
    source: Mapping[str,Any],
    shadow: Mapping[str,Any],
    manifest: Mapping[str,Any],
    player_audit: Mapping[str,Any],
    frozen: Mapping[str,Any],
    recorded_utc: datetime,
    source_workflow_run: str,
    source_head_sha: str,
)->dict[str,Any]|None:
    source_id=str(source.get("forecast_id") or "").strip()
    prop_type=str(source.get("prop_type") or "").strip()
    if not source_id or prop_type not in SUPPORTED_PROPS:
        return None
    kickoff=_aware(source.get("kickoff_utc"),label="kickoff_utc")
    forecast_at=_aware(source.get("forecast_timestamp_utc"),label="forecast_timestamp_utc")
    source_market=source.get("market") if isinstance(source.get("market"),Mapping) else {}
    market_captured=source_market.get("captured_utc")
    market_line=_finite(source_market.get("line"))
    market_no_vig=_finite(source_market.get("no_vig_over_probability"))
    if market_captured is None or market_line is None or market_no_vig is None:
        # V1 publishes research rows even when no complete sportsbook market is available.
        # Those rows are valid source forecasts but are outside the paired market-backed
        # prospective shadow population and must be skipped rather than aborting the slate.
        return None
    market_at=_aware(market_captured,label="market captured_utc")
    recorded=recorded_utc.astimezone(timezone.utc)
    if not (forecast_at<kickoff and market_at<kickoff and recorded<kickoff):
        return None
    if forecast_at>recorded or market_at>recorded:
        return None

    source_model=source.get("model") if isinstance(source.get("model"),Mapping) else {}
    shadow_model=shadow.get("model") if isinstance(shadow.get("model"),Mapping) else {}
    pid=str(source.get("player_id") or "")
    event_type="rushing" if prop_type=="rushing_yards" else "receiving"
    audit=player_audit.get(pid)
    if not isinstance(audit,Mapping):
        raise FootballShadowError(f"missing player overlay audit for {pid}")

    receipt={
        "contract_version":CONTRACT_VERSION,
        "event_type":EVENT_TYPE,
        "shadow_id":_shadow_id(source_id),
        "shadow_version":SHADOW_VERSION,
        "recorded_utc":recorded.isoformat(),
        "source_workflow_run":str(source_workflow_run),
        "source_head_sha":str(source_head_sha),
        "source_forecast_id":source_id,
        "source_forecast_sha256":_sha(dict(source)),
        "source_manifest_sha256":str(manifest.get("manifest_sha256") or ""),
        "source_forecast_timestamp_utc":forecast_at.isoformat(),
        "source_market_captured_utc":market_at.isoformat(),
        "kickoff_utc":kickoff.isoformat(),
        "game_id":str(source.get("game_id") or ""),
        "player_id":pid,
        "player":str(source.get("player") or ""),
        "position":str(source.get("position") or ""),
        "team":str(source.get("team") or ""),
        "opponent":str(source.get("opponent") or ""),
        "prop_type":prop_type,
        "market":{
            "line":market_line,
            "no_vig_over_probability":market_no_vig,
            "over_price_american":_finite(source_market.get("over_price_american")),
            "under_price_american":_finite(source_market.get("under_price_american")),
        },
        "v1":{
            "model_version":source_model.get("version"),
            "fair_line":_finite(source_model.get("fair_line")),
            "over_probability":_finite(source_model.get("over_probability")),
            "under_probability":_finite(source_model.get("under_probability")),
            "standard_deviation":_finite(source_model.get("standard_deviation")),
            "prediction_interval":source_model.get("prediction_interval"),
        },
        "shadow_a":{
            "model_version":shadow_model.get("version"),
            "fair_line":_finite(shadow_model.get("fair_line")),
            "over_probability":_finite(shadow_model.get("over_probability")),
            "under_probability":_finite(shadow_model.get("under_probability")),
            "standard_deviation":_finite(shadow_model.get("standard_deviation")),
            "prediction_interval":shadow_model.get("prediction_interval"),
        },
        "defensive_efficiency":{
            "event_type":event_type,
            "base_mean":audit[f"base_{event_type}_yards_per_"+("carry" if event_type=="rushing" else "reception")],
            "shadow_mean":audit[f"shadow_{event_type}_yards_per_"+("carry" if event_type=="rushing" else "reception")],
            "state":audit[f"{event_type}_defense_state"],
            "fit":dict(frozen["fits"][event_type]),
            "coefficient_contract_version":frozen["contract_version"],
        },
        "governance":{
            "production_authorized":False,
            "published_v1_props_mutated":False,
            "winner_model_mutated":False,
            "target_week_outcomes_used":0,
            "completed_2026_outcomes_used_for_coefficient_fit":0,
            "opportunity_arrays_preserved":True,
        },
    }
    receipt["shadow_sha256"]=_sha(receipt)
    return receipt


def record_shadow_a(
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
    season=int(upstream.get("season"))
    week=int(upstream.get("week"))
    captured=_aware(upstream.get("captured_at_utc"),label="upstream captured_at_utc")
    recorded=(recorded_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if recorded<captured:
        raise FootballShadowError("shadow cannot be recorded before source upstream capture")

    slate,manifests=load_manifests(run_root)
    source_artifact=_load_object(run_root/"forecasts.json")
    source_index=_forecast_index(source_artifact)

    teams={
        str(manifest["home_team"]).upper() for manifest in manifests
    }|{
        str(manifest["away_team"]).upper() for manifest in manifests
    }
    bundle=load_core_data(range(HISTORY_START,season+1))
    pbp=bundle.pbp.to_pandas() if hasattr(bundle.pbp,"to_pandas") else bundle.pbp.copy()
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
        verify_manifest_fingerprint(manifest)
        kickoff=_aware(manifest["kickoff_utc"],label="manifest kickoff_utc")
        if recorded>=kickoff:
            skipped_started+=1
            continue

        game=_build_game_from_manifest(manifest)
        baseline=simulate_game(
            game,
            simulations=int(manifest.get("simulations",20000)),
            seed=int(manifest.get("seed",0)),
        )
        shadow,overlay_audit=apply_shadow_a(
            baseline,defense_state=defense_state,frozen=frozen
        )

        baseline_artifact=build_forecast_artifact(
            baseline,
            manifest["market_artifacts"],
            kickoff_utc=manifest["kickoff_utc"],
            forecast_timestamp_utc=manifest["forecast_timestamp_utc"],
            interval_level=float(manifest.get("prediction_interval_level",0.80)),
        )
        shadow_artifact=build_forecast_artifact(
            shadow,
            manifest["market_artifacts"],
            kickoff_utc=manifest["kickoff_utc"],
            forecast_timestamp_utc=manifest["forecast_timestamp_utc"],
            interval_level=float(manifest.get("prediction_interval_level",0.80)),
        )
        baseline_index=_forecast_index(baseline_artifact)
        shadow_index=_forecast_index(shadow_artifact)

        game_id=str(manifest["game_id"])
        game_receipts=0
        for key,replay in baseline_index.items():
            if key[0]!=game_id or key[2] not in SUPPORTED_PROPS:
                continue
            source=source_index.get(key)
            shadow_row=shadow_index.get(key)
            if source is None or shadow_row is None:
                raise FootballShadowError(f"missing paired source/shadow row: {key}")
            _assert_replay_matches_source(replay,source)
            eligible_source_rows+=1
            candidate_id=_shadow_id(str(source.get("forecast_id") or ""))
            if candidate_id in existing_ids:
                skipped_existing+=1
                continue
            receipt=build_receipt(
                source=source,
                shadow=shadow_row,
                manifest=manifest,
                player_audit=overlay_audit,
                frozen=frozen,
                recorded_utc=recorded,
                source_workflow_run=source_workflow_run,
                source_head_sha=source_head_sha,
            )
            if receipt is None:
                continue
            receipts.append(receipt)
            existing_ids.add(receipt["shadow_id"])
            game_receipts+=1
        game_audit[game_id]={
            "source_manifest_sha256":manifest.get("manifest_sha256"),
            "new_receipts":game_receipts,
            "opportunity_arrays_preserved":True,
        }

    ledger.parent.mkdir(parents=True,exist_ok=True)
    appended=append_jsonl_immutable(
        ledger,receipts,identity_key="shadow_id"
    ) if receipts else 0
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
        "skipped_existing":int(skipped_existing),
        "skipped_started_games":int(skipped_started),
        "ledger":str(ledger),
        "defense_state_audit":defense_audit,
        "game_audit":game_audit,
        "production_authorized":False,
        "winner_model_mutated":False,
        "published_v1_props_mutated":False,
        "outcomes_read":0,
    }


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--artifact-root",type=Path,required=True)
    parser.add_argument("--frozen-coefficients",type=Path,required=True)
    parser.add_argument("--ledger",type=Path,required=True)
    parser.add_argument("--source-workflow-run",required=True)
    parser.add_argument("--source-head-sha",required=True)
    args=parser.parse_args()
    result=record_shadow_a(
        args.artifact_root,
        args.frozen_coefficients,
        args.ledger,
        source_workflow_run=args.source_workflow_run,
        source_head_sha=args.source_head_sha,
    )
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
