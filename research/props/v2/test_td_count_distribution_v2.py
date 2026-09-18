from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[3]
SCRIPT=ROOT/"research"/"props"/"v2"/"td_count_distribution_v2.py"


def _module():
    spec=importlib.util.spec_from_file_location("td_count_distribution_tested",SCRIPT)
    assert spec and spec.loader
    m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m
    spec.loader.exec_module(m)
    return m


def test_negative_binomial_collapses_to_poisson_when_no_overdispersion():
    m=_module()
    a=m._pmf(2.2,0.0,"poisson")
    b=m._pmf(2.2,0.0,"negative_binomial")
    assert np.allclose(a,b)


def test_chronological_count_study_uses_2024_2025_only_as_tests():
    m=_module()
    rows=[]
    for season in [2021,2022,2023,2024,2025]:
        for week in range(1,19):
            for team,offset in [("A",0),("B",1)]:
                rows.append({
                    "season":season,"game_id":f"{season}-{week}-{team}",
                    "team":team,"offensive_tds":(week+offset)%5,
                })
    out=m.evaluate_td_count_families(pd.DataFrame(rows))
    assert set(out["seasons"])=={"2024","2025"}
    assert out["aggregate"]["n"]==72
    assert out["completed_2026_outcomes_used"]==0


def test_overdispersed_training_produces_nonnegative_alpha():
    m=_module()
    train=pd.DataFrame({
        "team":["A"]*100,
        "offensive_tds":[0]*50+[6]*50,
    })
    means,league=m._team_means(train)
    alpha=m._fit_overdispersion(train,means,league)
    assert alpha>0
