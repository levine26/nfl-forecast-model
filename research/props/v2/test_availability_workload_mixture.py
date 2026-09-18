from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"availability_workload_mixture.py"


def _module():
    spec=importlib.util.spec_from_file_location("availability_workload_mixture_tested",SCRIPT)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module


def test_latest_pregame_report_and_strict_prior_baseline():
    m=_module()
    schedules=pd.DataFrame([{
        "season":2024,"week":3,"game_type":"REG","home_team":"ARI","away_team":"LAR",
        "kickoff":"2024-09-22T20:00:00Z",
    }])
    injuries=pd.DataFrame([
        {"season":2024,"week":3,"season_type":"REG","team":"ARI","gsis_id":"p",
         "position":"WR","report_status":"Questionable","date_modified":"2024-09-20T16:00:00Z"},
        {"season":2024,"week":3,"season_type":"REG","team":"ARI","gsis_id":"p",
         "position":"WR","report_status":"Questionable","date_modified":"2024-09-22T19:00:00Z"},
        {"season":2024,"week":3,"season_type":"REG","team":"ARI","gsis_id":"p",
         "position":"WR","report_status":"Out","date_modified":"2024-09-22T21:00:00Z"},
    ])
    snaps=pd.DataFrame([
        {"season":2024,"week":1,"team":"ARI","player_id":"p","offense_snaps":40},
        {"season":2024,"week":1,"team":"ARI","player_id":"other","offense_snaps":60},
        {"season":2024,"week":2,"team":"ARI","player_id":"p","offense_snaps":42},
        {"season":2024,"week":2,"team":"ARI","player_id":"other","offense_snaps":60},
        {"season":2024,"week":3,"team":"ARI","player_id":"p","offense_snaps":20},
        {"season":2024,"week":3,"team":"ARI","player_id":"other","offense_snaps":60},
    ])
    obs,audit=m.build_workload_observations(injuries,snaps,schedules,trained_through_season=2024)
    assert len(obs)==1
    row=obs.iloc[0]
    assert row["report_status"]=="QUESTIONABLE"
    assert row["prior_baseline_snap_share"]==pytest.approx(np.median([40/60,42/60]))
    assert row["offense_snap_share"]==pytest.approx(20/60)
    assert audit["injury_source"]["post_kickoff_rows_dropped"]==1
    assert audit["completed_2026_outcomes_used"]==0


def test_mixture_recovers_ordered_active_states_without_prop_outcomes():
    m=_module()
    rng=np.random.default_rng(123)
    rows=[]
    for idx,(state,mu) in enumerate([
        ("limited",-0.8),("normal",0.0),("elevated",0.45)
    ]):
        for j in range(120):
            ratio=float(np.exp(rng.normal(mu,0.08)))
            rows.append({
                "season":2024,"week":1,"team":"A","player_id":f"{idx}-{j}",
                "position":"WR","report_status":"QUESTIONABLE",
                "report_timestamp_utc":"2024-09-01T00:00:00+00:00",
                "kickoff_utc":"2024-09-02T00:00:00+00:00",
                "offense_snap_share":min(ratio*0.7,1.0),
                "prior_baseline_snap_share":0.7,
                "workload_ratio":ratio,"active":True,
            })
    fit=m.fit_workload_mixture(pd.DataFrame(rows))
    med=[fit["active_state_parameters"][s]["median_workload_ratio"] for s in m.STATE_NAMES]
    assert med[0] < med[1] < med[2]
    assert fit["diagnostic_gate"]["enough_active_rows"] is True
    assert fit["prop_outcomes_used"]==0


def test_2026_training_horizon_rejected():
    m=_module()
    with pytest.raises(m.AvailabilityMixtureError,match="2026 outcomes"):
        m.build_workload_observations(pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),trained_through_season=2026)
