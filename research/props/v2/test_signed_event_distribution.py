from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from signed_event_distribution import (
    empirical_crps,
    evaluate_component_season,
    gamma_aggregate_samples,
    signed_empirical_aggregate_samples,
)


def test_signed_empirical_sampler_can_generate_negative_total():
    training=np.asarray([-5,-2,0,3,8,15],dtype=float)
    samples=signed_empirical_aggregate_samples(
        1,3.0,training,simulations=5000,seed=7
    )
    assert np.min(samples)<0


def test_gamma_baseline_is_nonnegative():
    samples=gamma_aggregate_samples(
        2,4.0,6.0,simulations=5000,seed=7
    )
    assert np.min(samples)>=0


def test_empirical_crps_degenerate_matches_absolute_error():
    assert empirical_crps(np.asarray([5.0,5.0]),2.0)==pytest.approx(3.0)


def test_season_forward_component_ignores_future_season_fit():
    rows=[]
    for season in (2021,2022,2023):
        for week in range(1,5):
            for player,pos,event,vals in [
                ("rb","RB","rushing",[-3,2,4,8]),
                ("wr","WR","receiving",[-2,5,11]),
            ]:
                for y in vals:
                    rows.append({
                        "game_id":f"{season}_{week}",
                        "season":season,"week":week,
                        "player_id":player,"position":pos,
                        "event_type":event,"yards":float(y),
                    })
    events=pd.DataFrame(rows)
    scored,summary=evaluate_component_season(
        events,evaluation_season=2023,simulations=1000
    )
    assert len(scored)>0
    assert summary["trained_through_season"]==2022
    assert summary["component_isolation_only"] is True
    assert summary["pregame_prop_forecast"] is False
    assert summary["completed_2026_outcomes_used"]==0
