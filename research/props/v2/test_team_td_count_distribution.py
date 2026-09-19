from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from team_td_count_distribution import (
    TeamTDCountError,
    build_strict_prior_means,
    fit_dispersion,
    negative_binomial_pmf,
    poisson_pmf,
    score_season,
)


def _team_games():
    rows=[]
    for season in range(2018,2024):
        for week in range(1,19):
            for game_index in range(8):
                game=f"{season}_{week}_{game_index}"
                for side,team in enumerate((f"A{game_index}",f"B{game_index}")):
                    base=2.5 + (0.4 if team.startswith("A") else -0.3)
                    # Deterministic overdispersion around a stable mean.
                    value=max(0,int(round(base + ((week+game_index+side)%5-2)*0.9)))
                    rows.append({
                        "game_id":game,"season":season,"week":week,
                        "team":team,"offensive_tds":value,
                    })
    return pd.DataFrame(rows)


def test_strict_prior_means_do_not_use_same_week_outcomes():
    rows=build_strict_prior_means(_team_games())
    assert len(rows)>0
    assert (rows["same_week_outcomes_used"]==0).all()
    target=rows[(rows.season==2023)&(rows.week==2)]
    assert (target["prior_team_games"]>0).all()
    assert (target["prior_league_games"]>0).all()


def test_distribution_pmfs_are_valid_and_share_mean_parameterization():
    poi=poisson_pmf(2.7)
    nb=negative_binomial_pmf(2.7,0.25)
    assert poi.sum()==pytest.approx(1.0)
    assert nb.sum()==pytest.approx(1.0)
    assert (poi>=0).all()
    assert (nb>=0).all()


def test_season_forward_scores_without_prop_or_market_inputs():
    rows=build_strict_prior_means(_team_games())
    scored,summary=score_season(rows,evaluation_season=2023)
    assert len(scored)>0
    assert summary["trained_through_season"]==2022
    assert summary["same_expected_mean_for_both_models"] is True
    assert summary["player_prop_outcomes_used"]==0
    assert summary["sportsbook_data_used"]==0


def test_future_season_does_not_change_prior_dispersion_fit():
    rows=build_strict_prior_means(_team_games())
    a=fit_dispersion(rows,trained_through_season=2022)
    mutated=rows.copy()
    mutated.loc[mutated.season.eq(2023),"actual_offensive_tds"]=99
    b=fit_dispersion(mutated,trained_through_season=2022)
    assert a.alpha==pytest.approx(b.alpha)


def test_2026_fit_is_rejected():
    rows=build_strict_prior_means(_team_games())
    with pytest.raises(TeamTDCountError,match="2026"):
        fit_dispersion(rows,trained_through_season=2026)
