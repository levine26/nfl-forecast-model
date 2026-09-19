from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from game_environment_residual import (
    evaluate_environment_season,
    fit_environment_residuals,
    prepare_environment_rows,
)


def _rows():
    diagnostics=[]
    market=[]
    for season in (2021,2022,2023):
        for week in range(1,18):
            game=f"{season}_{week:02d}_A_B"
            total=40.0+(week%7)
            spread=-3.0 if week%2 else 3.0
            # Deliberately generate context-linked residuals only for test mechanics.
            for team,ts in (("A",spread),("B",-spread)):
                base_plays=63.0
                actual_plays=base_plays+0.20*(total-43.0)+0.05*abs(ts)
                base_drop=.60
                actual_drop=base_drop+(-0.006*ts)
                diagnostics.append({
                    "game_id":game,"season":season,"week":week,"team":team,
                    "pred_team_plays_mean":base_plays,
                    "actual_team_plays":actual_plays,
                    "pred_dropback_rate_mean":base_drop,
                    "actual_dropback_rate":actual_drop,
                })
                market.append({
                    "game_id":game,"team":team,"team_spread":ts,"game_total":total
                })
    return pd.DataFrame(diagnostics),pd.DataFrame(market)


def test_prepare_environment_joins_opponent_without_future_fields():
    d,m=_rows()
    rows=prepare_environment_rows(d,m)
    assert len(rows)==len(d)
    assert rows["opponent_base_plays"].notna().all()
    assert "actual_team_plays" in rows
    assert "game_total" in rows


def test_fit_is_invariant_to_evaluation_season_outcomes():
    d,m=_rows()
    rows=prepare_environment_rows(d,m)
    a=fit_environment_residuals(rows,trained_through_season=2022)
    mutated=rows.copy()
    mutated.loc[mutated.season.eq(2023),"actual_team_plays"]=200
    mutated.loc[mutated.season.eq(2023),"actual_dropback_rate"]=0.1
    # Residual columns are evaluation-period data too; mutate them as well.
    mutated.loc[mutated.season.eq(2023),"play_residual"]=137
    mutated.loc[mutated.season.eq(2023),"dropback_logit_residual"]=-5
    b=fit_environment_residuals(mutated,trained_through_season=2022)
    assert a["plays"].intercept==pytest.approx(b["plays"].intercept)
    assert a["dropback"].intercept==pytest.approx(b["dropback"].intercept)


def test_season_forward_challenger_improves_synthetic_context_signal():
    d,m=_rows()
    rows=prepare_environment_rows(d,m)
    scored,summary=evaluate_environment_season(rows,evaluation_season=2023)
    assert len(scored)>0
    assert summary["trained_through_season"]==2022
    assert summary["challenger_team_plays_mae"] < summary["baseline_team_plays_mae"]
    assert summary["challenger_dropback_rate_mae"] < summary["baseline_dropback_rate_mae"]
    assert summary["prop_outcomes_used"]==0
    assert summary["completed_2026_outcomes_used"]==0
