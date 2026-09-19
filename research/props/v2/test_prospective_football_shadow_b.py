from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.props_opportunity import (
    DEFAULT_ALLOCATION_PSEUDOCOUNT,
    _availability_adjusted_allocation,
    _route_redistribution,
)

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"record_prospective_football_shadow_b.py"


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
