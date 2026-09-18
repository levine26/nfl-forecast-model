from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"distribution_v2_event_study.py"


def _module():
    spec=importlib.util.spec_from_file_location("distribution_v2_tested",SCRIPT)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m


def test_empirical_candidate_preserves_negative_support():
    m=_module()
    train=np.array([-4,-2,-1,0,1,2,3,4,5,8,12,20]*20,dtype=float)
    test=np.array([-3,-1,0,4,15],dtype=float)
    result=m.evaluate_distribution_pair(train,train,test,kind="rushing",seed=7)
    assert result["negative_rate"]>0
    assert result["empirical_mixture"]["forecast_quantiles"]["q05"]<0
    assert result["nonnegative_gamma"]["forecast_quantiles"]["q05"]>=0
    assert result["empirical_mixture"]["bin_probabilities"][0]>0
    assert result["nonnegative_gamma"]["bin_probabilities"][0]==0


def test_rolling_evaluation_is_chronological():
    m=_module()
    rows=[]
    for season in [2021,2022,2023,2024,2025]:
        for i in range(80):
            rows.append({
                "season":season,
                "event_kind":"rushing",
                "position":"RB",
                "yards":float((i%12)-2),
            })
            rows.append({
                "season":season,
                "event_kind":"receiving",
                "position":"WR",
                "yards":float((i%24)-1),
            })
    result=m.evaluate_rolling_event_distributions(pd.DataFrame(rows))
    assert "2024|rushing|RB" in result["cells"]
    assert "2025|receiving|WR" in result["cells"]
    assert result["completed_2026_outcomes_used"]==0
    assert result["aggregate"]["n_test"]>0
