from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from availability_workload_mixture import (
    build_workload_examples,
    evaluate_season_forward,
    fit_workload_mixtures,
    normalize_injury_designations,
    normalize_snap_history,
)


def _snap_rows():
    rows=[]
    # Stable WR gets 80% baseline, then limited on Q designation and normal on D designation.
    for season in (2021,2022,2023):
        for week in range(1,7):
            share=0.80
            if season==2023 and week==5:
                share=0.40
            if season==2023 and week==6:
                share=0.80
            rows.append({
                "season":season,"week":week,"team":"ARI","player_id":"p1",
                "offense_pct":share,"offense_snaps":int(70*share)
            })
            # Full-snap player establishes team denominator.
            rows.append({
                "season":season,"week":week,"team":"ARI","player_id":"full",
                "offense_pct":1.0,"offense_snaps":70
            })
    # Add enough historical examples across players for fit stability.
    for j in range(50):
        player=f"q{j}"
        for week in (1,2,3):
            share=0.6 if week<3 else (0.3 if j%2==0 else 0.6)
            rows.append({
                "season":2022,"week":week,"team":"BUF","player_id":player,
                "offense_pct":share,"offense_snaps":int(70*share)
            })
        rows.append({
            "season":2022,"week":3,"team":"BUF","player_id":"buf_full",
            "offense_pct":1.0,"offense_snaps":70
        })
    return pd.DataFrame(rows)


def _injuries():
    rows=[
        {"season":2023,"week":5,"team":"ARI","gsis_id":"p1","position":"WR","report_status":"Questionable"},
        {"season":2023,"week":6,"team":"ARI","gsis_id":"p1","position":"WR","report_status":"Doubtful"},
    ]
    for j in range(50):
        rows.append({
            "season":2022,"week":3,"team":"BUF","gsis_id":f"q{j}",
            "position":"WR","report_status":"Questionable",
        })
    return pd.DataFrame(rows)


def test_examples_use_strictly_prior_baseline_and_classify_limited():
    snaps,_=normalize_snap_history(_snap_rows(),max_season=2023)
    injuries,_=normalize_injury_designations(_injuries(),max_season=2023)
    examples,audit=build_workload_examples(injuries,snaps)
    row=examples[(examples.player_id=="p1") & (examples.week==5)].iloc[0]
    assert row.baseline_snap_share == pytest.approx(0.80)
    assert row.actual_snap_share == pytest.approx(0.40)
    assert row.workload_ratio == pytest.approx(0.50)
    assert row.workload_state == "ACTIVE_LIMITED"
    assert audit["prop_outcomes_used"] == 0


def test_missing_player_row_is_out_only_with_team_week_coverage():
    snaps,_=normalize_snap_history(_snap_rows(),max_season=2023)
    injuries=pd.DataFrame([
        {"season":2023,"week":5,"team":"ARI","gsis_id":"ghost","position":"WR","report_status":"Questionable"}
    ])
    # Create prior history for ghost but no current row.
    extra=pd.DataFrame([
        {"season":2022,"week":1,"team":"ARI","player_id":"ghost","snap_share":0.5,"offense_snaps":35},
        {"season":2022,"week":2,"team":"ARI","player_id":"ghost","snap_share":0.5,"offense_snaps":35},
    ])
    snaps=pd.concat([snaps,extra],ignore_index=True)
    inj,_=normalize_injury_designations(injuries,max_season=2023)
    examples,_=build_workload_examples(inj,snaps)
    assert len(examples)==1
    assert examples.iloc[0].workload_state=="OUT"
    assert examples.iloc[0].actual_snap_share==0.0


def test_fit_uses_only_prior_seasons():
    snaps,_=normalize_snap_history(_snap_rows(),max_season=2023)
    injuries,_=normalize_injury_designations(_injuries(),max_season=2023)
    examples,_=build_workload_examples(injuries,snaps)
    a=fit_workload_mixtures(examples,trained_through_season=2022)
    mutated=examples.copy()
    mutated.loc[mutated.season.eq(2023),"workload_ratio"]=2.0
    mutated.loc[mutated.season.eq(2023),"workload_state"]="ACTIVE_ELEVATED"
    b=fit_workload_mixtures(mutated,trained_through_season=2022)
    assert a[("QUESTIONABLE","WR")].expected_workload_ratio == pytest.approx(
        b[("QUESTIONABLE","WR")].expected_workload_ratio
    )


def test_season_forward_evaluation_never_consumes_prop_outcomes():
    snaps,_=normalize_snap_history(_snap_rows(),max_season=2023)
    injuries,_=normalize_injury_designations(_injuries(),max_season=2023)
    examples,_=build_workload_examples(injuries,snaps)
    scored,summary=evaluate_season_forward(examples,evaluation_season=2023)
    assert len(scored)>=1
    assert summary["trained_through_season"]==2022
    assert summary["prop_outcomes_used_for_fit_or_evaluation"]==0
    assert summary["completed_2026_outcomes_used"]==0
    assert summary["production_authorized"] is False
