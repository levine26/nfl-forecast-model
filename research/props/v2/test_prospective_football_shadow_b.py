from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.props_opportunity import (
    DEFAULT_ALLOCATION_PSEUDOCOUNT,
    ForecastContext,
    _availability_adjusted_allocation,
    _route_redistribution,
    build_opportunity_projection,
)

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"record_prospective_football_shadow_b.py"
FROZEN=ROOT/"research"/"props"/"v2"/"DEFENSIVE_EFFICIENCY_SHADOW_FROZEN.json"


def _module():
    spec=importlib.util.spec_from_file_location("shadow_b_tested",SCRIPT)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _projection():
    rows=[
        {
            "player_id":"RB1","player_name":"RB One","position":"RB",
            "availability_probability":0.95,"availability_uncertainty":0.04,
            "carry_history_effective_opportunities":34.0,
            "target_history_effective_opportunities":8.0,
            "route_history_effective_dropbacks":16.0,
        },
        {
            "player_id":"RB2","player_name":"RB Two","position":"RB",
            "availability_probability":0.85,"availability_uncertainty":0.06,
            "carry_history_effective_opportunities":20.0,
            "target_history_effective_opportunities":5.0,
            "route_history_effective_dropbacks":11.0,
        },
        {
            "player_id":"WR1","player_name":"WR One","position":"WR",
            "availability_probability":0.98,"availability_uncertainty":0.03,
            "carry_history_effective_opportunities":2.0,
            "target_history_effective_opportunities":31.0,
            "route_history_effective_dropbacks":62.0,
        },
        {
            "player_id":"WR2","player_name":"WR Two","position":"WR",
            "availability_probability":0.92,"availability_uncertainty":0.05,
            "carry_history_effective_opportunities":1.0,
            "target_history_effective_opportunities":24.0,
            "route_history_effective_dropbacks":55.0,
        },
    ]
    players=pd.DataFrame(rows)
    for col in ("role_multiplier","carry_role_multiplier","target_role_multiplier","route_role_multiplier"):
        players[col]=1.0

    carry_ids=["RB1","RB2","WR1","WR2"]
    target_ids=["RB1","RB2","WR1","WR2"]
    carry=players.set_index("player_id").loc[carry_ids].reset_index()
    target=players.set_index("player_id").loc[target_ids].reset_index()

    carry_alpha=carry["carry_history_effective_opportunities"].to_numpy(dtype=float)+DEFAULT_ALLOCATION_PSEUDOCOUNT
    target_alpha=target["target_history_effective_opportunities"].to_numpy(dtype=float)+DEFAULT_ALLOCATION_PSEUDOCOUNT
    carry_dist,carry_redist,_=_availability_adjusted_allocation(
        carry,carry_alpha,label="designed_carry_share",multiplier_column="carry_role_multiplier"
    )
    target_dist,target_redist,_=_availability_adjusted_allocation(
        target,target_alpha,label="target_share",multiplier_column="target_role_multiplier"
    )

    base_route=np.array([0.55,0.42,0.91,0.84],dtype=float)
    route_strength=target["route_history_effective_dropbacks"].to_numpy(dtype=float)+24.0
    route_dists,route_redist,_=_route_redistribution(target,base_route,route_strength)

    projection={
        "metadata":{"team":"ARI","opponent":"LAR","season":2026,"week":3,"game_id":"G1"},
        "players":rows,
        "hierarchy":{
            "designed_carry_share_given_designed_rush":carry_dist,
            "target_share_given_team_target":target_dist,
            "route_participation_given_dropback":{
                pid:dist for pid,dist in zip(target_ids,route_dists)
            },
        },
        "redistribution":{
            "designed_carries":carry_redist,
            "targets":target_redist,
            "routes":route_redist,
        },
    }
    return projection


def test_shadow_b_reconstructs_v1_before_applying_role_adjustments():
    module=_module()
    projection=_projection()
    adjusted,audit=module.transform_opportunity_projection(
        projection,
        {
            "RB1":{"carry_role_multiplier":1.20,"target_role_multiplier":1.10,"route_role_multiplier":1.15},
            "WR1":{"target_role_multiplier":1.12,"route_role_multiplier":1.08},
        },
    )
    assert audit["baseline_reconstruction_verified"] is True
    base_carry=projection["hierarchy"]["designed_carry_share_given_designed_rush"]["mean_share"]["RB1"]
    new_carry=adjusted["hierarchy"]["designed_carry_share_given_designed_rush"]["mean_share"]["RB1"]
    assert new_carry > base_carry
    base_target=projection["hierarchy"]["target_share_given_team_target"]["mean_share"]["WR1"]
    new_target=adjusted["hierarchy"]["target_share_given_team_target"]["mean_share"]["WR1"]
    assert new_target > base_target
    base_route=projection["hierarchy"]["route_participation_given_dropback"]["WR1"]["mean"]
    new_route=adjusted["hierarchy"]["route_participation_given_dropback"]["WR1"]["mean"]
    assert new_route > base_route


def test_shadow_b_fails_closed_when_captured_v1_distribution_does_not_reconstruct():
    module=_module()
    projection=_projection()
    projection["hierarchy"]["target_share_given_team_target"]["concentration"]["WR1"] += 0.25
    with pytest.raises(module.FootballShadowBError,match="captured V1 opportunity drift"):
        module.transform_opportunity_projection(
            projection,
            {"WR1":{"target_role_multiplier":1.1}},
        )


def test_shadow_b_rejects_unknown_role_player():
    module=_module()
    with pytest.raises(module.FootballShadowBError,match="unknown players"):
        module.transform_opportunity_projection(
            _projection(),
            {"NOT_A_PLAYER":{"carry_role_multiplier":1.2}},
        )


def test_shadow_b_transform_matches_canonical_opportunity_engine():
    module=_module()
    team_rows=[]
    player_rows=[]
    for week in range(1,7):
        gid=f"2025_{week:02d}_ARI_LAR"
        team_rows.append({
            "game_id":gid,"season":2025,"week":week,"team":"ARI",
            "offensive_plays":64.0,"dropbacks":39.0,"pass_attempts":36.0,
            "sacks":2.0,"qb_scrambles":1.0,"designed_rush_attempts":25.0,
            "team_targets":34.0,
        })
        player_rows.extend([
            {"game_id":gid,"season":2025,"week":week,"team":"ARI","player_id":"QB1","position":"QB","designed_carries":3.0,"routes":0.0,"targets":0.0,"receptions":0.0},
            {"game_id":gid,"season":2025,"week":week,"team":"ARI","player_id":"RB1","position":"RB","designed_carries":16.0,"routes":21.0,"targets":5.0,"receptions":4.0},
            {"game_id":gid,"season":2025,"week":week,"team":"ARI","player_id":"RB2","position":"RB","designed_carries":6.0,"routes":10.0,"targets":2.0,"receptions":1.0},
            {"game_id":gid,"season":2025,"week":week,"team":"ARI","player_id":"WR1","position":"WR","designed_carries":0.0,"routes":36.0,"targets":11.0,"receptions":7.0},
            {"game_id":gid,"season":2025,"week":week,"team":"ARI","player_id":"TE1","position":"TE","designed_carries":0.0,"routes":27.0,"targets":7.0,"receptions":5.0},
        ])
    team_history=pd.DataFrame(team_rows)
    player_history=pd.DataFrame(player_rows)
    players=pd.DataFrame([
        {"player_id":"QB1","player_name":"QB","position":"QB","availability_probability":1.0,"availability_uncertainty":0.0,"is_primary_qb":True},
        {"player_id":"RB1","player_name":"RB One","position":"RB","availability_probability":0.95,"availability_uncertainty":0.04,"is_primary_qb":False},
        {"player_id":"RB2","player_name":"RB Two","position":"RB","availability_probability":0.90,"availability_uncertainty":0.05,"is_primary_qb":False},
        {"player_id":"WR1","player_name":"WR One","position":"WR","availability_probability":0.98,"availability_uncertainty":0.02,"is_primary_qb":False},
        {"player_id":"TE1","player_name":"TE One","position":"TE","availability_probability":0.97,"availability_uncertainty":0.03,"is_primary_qb":False},
    ])
    context=ForecastContext(
        game_id="2026_03_LAR_ARI",
        season=2026,
        week=3,
        team="ARI",
        opponent="LAR",
        forecast_timestamp="2026-09-19T18:00:00+00:00",
        data_horizon="2026-09-19T18:00:00+00:00",
    )
    adjustments={
        "RB1":{
            "carry_role_multiplier":1.20,
            "target_role_multiplier":1.10,
            "route_role_multiplier":1.15,
        },
        "WR1":{
            "target_role_multiplier":1.12,
            "route_role_multiplier":1.08,
        },
    }
    baseline=build_opportunity_projection(
        team_history,player_history,players,context
    ).to_dict()
    transformed,audit=module.transform_opportunity_projection(
        baseline,adjustments
    )
    assert audit["baseline_reconstruction_verified"] is True

    dynamic_players=players.copy()
    for col in (
        "role_multiplier",
        "carry_role_multiplier",
        "target_role_multiplier",
        "route_role_multiplier",
    ):
        dynamic_players[col]=1.0
    for pid,fields in adjustments.items():
        for field,value in fields.items():
            dynamic_players.loc[
                dynamic_players["player_id"].eq(pid),field
            ]=float(value)
    canonical=build_opportunity_projection(
        team_history,player_history,dynamic_players,context
    ).to_dict()

    for channel in (
        "designed_carry_share_given_designed_rush",
        "target_share_given_team_target",
    ):
        left=transformed["hierarchy"][channel]
        right=canonical["hierarchy"][channel]
        assert left["player_ids"]==right["player_ids"]
        assert left["concentration_total"]==pytest.approx(right["concentration_total"])
        for field in ("concentration","mean_share","variance"):
            assert set(left[field])==set(right[field])
            for pid in left[field]:
                assert left[field][pid]==pytest.approx(right[field][pid],abs=1e-12)

    left_routes=transformed["hierarchy"]["route_participation_given_dropback"]
    right_routes=canonical["hierarchy"]["route_participation_given_dropback"]
    assert set(left_routes)==set(right_routes)
    for pid in left_routes:
        for field in ("mean","alpha","beta","effective_sample_size"):
            if field in left_routes[pid] or field in right_routes[pid]:
                assert left_routes[pid].get(field)==pytest.approx(
                    right_routes[pid].get(field),abs=1e-12
                )


def test_shadow_b_receipt_uses_explicit_capture_timestamps():
    module=_module()
    frozen=module.load_frozen_coefficients(FROZEN)
    source={
        "forecast_id":"f-b",
        "game_id":"G1",
        "player_id":"P1",
        "player":"Player",
        "position":"RB",
        "team":"ARI",
        "opponent":"LAR",
        "prop_type":"rushing_yards",
        "kickoff_utc":"2026-09-20T20:00:00+00:00",
        "forecast_timestamp_utc":"2026-09-20T18:00:00+00:00",
        "market":{
            "captured_utc":"2026-09-20T18:05:00+00:00",
            "line":60.5,
            "no_vig_over_probability":0.51,
            "over_price_american":-110,
            "under_price_american":-110,
        },
        "model":{
            "version":"V1",
            "fair_line":62.0,
            "over_probability":0.54,
            "under_probability":0.46,
            "standard_deviation":20.0,
            "prediction_interval":{"low":30.0,"high":90.0,"coverage":0.8},
        },
    }
    shadow={
        **source,
        "model":{
            **source["model"],
            "version":module.SHADOW_VERSION,
            "fair_line":63.0,
        },
    }
    defense={
        "P1":{
            "base_rushing_yards_per_carry":4.2,
            "shadow_rushing_yards_per_carry":4.4,
            "rushing_defense_state":{"opponent_defense_delta":0.2},
            "base_receiving_yards_per_reception":10.0,
            "shadow_receiving_yards_per_reception":10.1,
            "receiving_defense_state":{"opponent_defense_delta":0.1},
        }
    }
    started=datetime(2026,9,20,18,30,tzinfo=timezone.utc)
    recorded=datetime(2026,9,20,19,0,tzinfo=timezone.utc)
    receipt=module.build_receipt(
        source=source,
        shadow=shadow,
        manifest={"manifest_sha256":"a"*64},
        defense_player_audit=defense,
        role_player_audit={},
        frozen=frozen,
        capture_started_utc=started,
        recorded_utc=recorded,
        source_workflow_run="1",
        source_head_sha="b"*40,
        source_season=2026,
        source_week=2,
        v1_samples=np.array([40,50,60,70],dtype=float),
        shadow_samples=np.array([42,52,62,72],dtype=float),
    )
    assert receipt is not None
    assert receipt["capture_started_utc"]==started.isoformat()
    assert receipt["capture_completed_utc"]==recorded.isoformat()
    assert receipt["recorded_utc"]==recorded.isoformat()
    assert receipt["source_season"]==2026
    assert receipt["source_week"]==2
    assert receipt["governance"]["production_authorized"] is False


def test_role_player_audit_preserves_unit_fallback_provenance():
    module=_module()
    audit={
        "ARI":{
            "dynamic_role":{
                "engine_version":"levline-props-dynamic-role-v0.1.0",
                "mode":"full",
                "history":{"status":"available"},
                "fallback_player_ids":["P_FALLBACK"],
                "estimates":[
                    {"player_id":"P_ADJ","history_games":4}
                ],
            },
            "transform":{
                "adjustments":{
                    "P_ADJ":{"target_role_multiplier":1.1}
                }
            },
        }
    }
    players=module._role_player_audit(audit)
    assert players["P_FALLBACK"]["fallback_to_unit_role"] is True
    assert players["P_FALLBACK"]["adjustment"]=={}
    assert players["P_FALLBACK"]["estimate"] is None
    assert players["P_ADJ"]["fallback_to_unit_role"] is False


def test_shadow_b_fails_closed_when_strictly_lagged_snap_history_is_unavailable(monkeypatch):
    module=_module()
    projection=_projection()

    def unavailable_history(*args, **kwargs):
        return {}, {
            "engine_version":"levline-props-dynamic-role-v0.1.0",
            "mode":"full",
            "history":{
                "status":"unavailable",
                "reason":"no_strictly_lagged_snap_rows",
            },
            "fallback_player_ids":[],
            "estimates":[],
        }

    monkeypatch.setattr(module,"build_dynamic_role_adjustments",unavailable_history)
    manifest={"opportunity_projections":[projection,projection]}
    with pytest.raises(
        module.FootballShadowBError,
        match="strictly lagged snap history unavailable",
    ):
        module.role_adjustments_for_manifest(
            manifest,
            pd.DataFrame([{"player_id":"RB1"}]),
        )
