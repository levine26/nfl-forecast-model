from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from signed_rushing_pregame import (
    SignedRushingPregameError,
    apply_signed_rushing_overlay,
    fit_residual_pools,
    signed_rushing_samples,
)


def _events():
    rows=[]
    for season in (2021,2022,2023):
        for position,base in (("QB",5.0),("RB",4.5),("WR",6.0),("TE",3.0)):
            for i in range(350):
                rows.append({
                    "season":season,"week":1+(i%18),"game_id":f"{season}_{i}",
                    "player_id":f"{position}_{i%12}","position":position,
                    "yards":base + ((i%11)-5)*1.1,
                })
    return pd.DataFrame(rows)


def test_signed_samples_preserve_zero_carries_and_allow_negative_totals():
    pool=np.array([-8,-5,-3,0,2,4,8],dtype=float)
    carries=np.array([0,1,1,2,3,4]*100,dtype=int)
    samples=signed_rushing_samples(
        carries,mean_per_carry=1.0,mean_se=0.0,residual_pool=pool,seed=7
    )
    assert (samples[carries==0]==0).all()
    assert (samples<0).any()


def test_fit_residual_pools_uses_only_training_horizon():
    events=_events()
    pools,audit=fit_residual_pools(events,trained_through_season=2022)
    assert set(pools)=={"QB","RB","WR","TE"}
    assert audit["trained_through_season"]==2022
    mutated=events.copy()
    mutated.loc[mutated.season.eq(2023),"yards"]=999
    pools2,_=fit_residual_pools(mutated,trained_through_season=2022)
    for position in pools:
        assert np.array_equal(pools[position],pools2[position])


def test_overlay_changes_only_rushing_yards_not_carries():
    player=SimpleNamespace(
        player_id="P1",position="RB",
        rushing_yards_per_carry=4.2,
        rushing_yards_per_carry_mean_se=0.1,
    )
    game=SimpleNamespace(players=(player,))
    carries=np.array([0,1,2,3,4,5]*50,dtype=int)
    original_yards=np.full(len(carries),99,dtype=int)
    sim=SimpleNamespace(player_stats={"P1":{
        "carries":carries.copy(),
        "rushing_yards":original_yards.copy(),
    }})
    audit=apply_signed_rushing_overlay(
        sim,game,{"RB":np.array([-6,-3,0,2,5,10],dtype=float)},
        seed_namespace="G1",
    )
    assert np.array_equal(sim.player_stats["P1"]["carries"],carries)
    assert not np.array_equal(sim.player_stats["P1"]["rushing_yards"],original_yards)
    assert audit["carry_arrays_modified"]==0
    assert audit["target_game_carries_used_for_fit"]==0


def test_2026_training_is_rejected():
    with pytest.raises(SignedRushingPregameError,match="2026"):
        fit_residual_pools(_events(),trained_through_season=2026)
