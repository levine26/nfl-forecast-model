from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pandas as pd
import pytest

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from defensive_efficiency_pregame import (
    PregameDefensiveEfficiencyError,
    adjusted_mean,
    apply_defensive_efficiency_overlay,
    build_defense_delta_lookup,
)


def _fit():
    return {
        "x_mean":0.0,
        "x_sd":0.5,
        "intercept":-0.1,
        "beta_standardized":0.2,
    }


def test_adjusted_mean_moves_with_defense_state():
    assert adjusted_mean(4.5,0.5,_fit()) > adjusted_mean(4.5,-0.5,_fit())


def test_lookup_requires_strict_prior_week_source():
    frame=pd.DataFrame([{
        "game_id":"G","defteam":"D","event_type":"rushing",
        "opponent_defense_delta":0.2,"same_week_outcomes_used":1,
    }])
    with pytest.raises(PregameDefensiveEfficiencyError,match="strict"):
        build_defense_delta_lookup(frame)


def test_overlay_changes_only_target_yardage_distribution():
    player=SimpleNamespace(
        player_id="P",opponent="D",
        rushing_yards_per_carry=4.5,
        rushing_yards_shape_per_carry=2.0,
        rushing_yards_per_carry_event_sd=3.0,
        rushing_yards_per_carry_mean_se=0.1,
        receiving_yards_per_reception=10.0,
        receiving_yards_shape_per_reception=2.0,
        receiving_yards_per_reception_event_sd=6.0,
        receiving_yards_per_reception_mean_se=0.1,
    )
    game=SimpleNamespace(players=(player,))
    carries=np.array([0,1,2,3,4]*100,dtype=int)
    receptions=np.array([0,1,2,3,4]*100,dtype=int)
    original_receiving=np.full(len(carries),77,dtype=int)
    sim=SimpleNamespace(player_stats={"P":{
        "carries":carries.copy(),
        "receptions":receptions.copy(),
        "rushing_yards":np.full(len(carries),99,dtype=int),
        "receiving_yards":original_receiving.copy(),
    }})
    audit=apply_defensive_efficiency_overlay(
        sim,game,game_id="G",mode="rushing",fit=_fit(),
        defense_delta_lookup={("G","D","rushing"):0.4},
    )
    assert np.array_equal(sim.player_stats["P"]["carries"],carries)
    assert np.array_equal(sim.player_stats["P"]["receptions"],receptions)
    assert np.array_equal(sim.player_stats["P"]["receiving_yards"],original_receiving)
    assert audit["opportunity_arrays_modified"]==0
    assert audit["players_adjusted"]==1
