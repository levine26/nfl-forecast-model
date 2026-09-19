from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from defensive_efficiency_residual import (
    DefensiveEfficiencyError,
    build_component_rows,
    fit_residual,
    score_season,
)


def _events():
    rows=[]
    for season in (2018,2019,2020,2021,2022,2023):
        for week in range(1,19):
            for game_suffix,(offense,defense) in enumerate((("A","B"),("B","A"))):
                game=f"{season}_{week}_{game_suffix}"
                # Player p has stable skill; defense B allows more yards than A.
                for event_type,position,count,base in (
                    ("rushing","RB",8,4.5),
                    ("receiving","WR",5,11.0),
                ):
                    player=f"{offense}_{event_type}"
                    def_effect=0.8 if defense=="B" else -0.8
                    for j in range(count):
                        rows.append({
                            "game_id":game,"season":season,"week":week,
                            "posteam":offense,"defteam":defense,"player_id":player,
                            "position":position,"event_type":event_type,
                            "yards":base+def_effect+(j%3-1)*0.2,
                        })
    return pd.DataFrame(rows)


def test_component_rows_use_only_prior_weeks_for_player_and_defense_state():
    rows=build_component_rows(_events())
    target=rows[(rows.season==2023)&(rows.week==2)&(rows.event_type=="rushing")]
    assert len(target)>0
    assert (target["same_week_outcomes_used"]==0).all()
    assert (target["player_prior_event_count"]>0).all()
    assert (target["opponent_prior_games"]>0).all()


def test_fixed_residual_model_improves_synthetic_defense_signal():
    rows=build_component_rows(_events())
    scored,summary=score_season(rows,event_type="rushing",evaluation_season=2023)
    assert len(scored)>0
    assert summary["challenger_conditional_total_mae"] < summary["baseline_conditional_total_mae"]
    assert summary["completed_2026_outcomes_used"]==0
    assert summary["prop_lines_used"]==0


def test_future_outcomes_do_not_change_prior_season_fit():
    rows=build_component_rows(_events())
    a=fit_residual(rows,event_type="receiving",trained_through_season=2022)
    mutated=rows.copy()
    mutated.loc[mutated.season.eq(2023),"actual_yards_per_event"]=999
    b=fit_residual(mutated,event_type="receiving",trained_through_season=2022)
    assert a.intercept==pytest.approx(b.intercept)
    assert a.beta_standardized==pytest.approx(b.beta_standardized)


def test_2026_fit_is_prohibited():
    rows=build_component_rows(_events())
    with pytest.raises(DefensiveEfficiencyError,match="2026"):
        fit_residual(rows,event_type="rushing",trained_through_season=2026)
