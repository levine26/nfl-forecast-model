import pandas as pd
import pytest

from nfl_forecast.ats_fair_line_policy import (
    REFERENCE_BREAK_EVEN,
    bootstrap_hit_rate,
    classification,
    grade_oof,
    record,
    season_records,
)


def _frame(rows):
    return pd.DataFrame(rows)


def test_grade_oof_uses_model_line_minus_market_line_not_winner_identity():
    graded = grade_oof(_frame([
        {"season": 2022, "week": 1, "margin": 3.0, "spread_line": 6.0, "expected_margin": 2.0},
        {"season": 2022, "week": 2, "margin": 8.0, "spread_line": 6.0, "expected_margin": 9.0},
        {"season": 2022, "week": 3, "margin": -1.0, "spread_line": 2.5, "expected_margin": 0.0},
    ]))
    # Row 1: model says home by 2 while market asks home by 6 -> away ATS; away covers.
    assert graded.loc[0, "edge_home"] == pytest.approx(-4.0)
    assert bool(graded.loc[0, "pick_home"]) is False
    assert bool(graded.loc[0, "win"]) is True
    # Row 2: model says home by 9 versus market home by 6 -> home ATS; home covers.
    assert graded.loc[1, "edge_home"] == pytest.approx(3.0)
    assert bool(graded.loc[1, "pick_home"]) is True
    assert bool(graded.loc[1, "win"]) is True
    # Row 3: home is a market favorite in canonical margin representation, but model edge is away.
    assert graded.loc[2, "edge_home"] < 0
    assert bool(graded.loc[2, "win"]) is True


def test_push_and_exact_no_edge_are_not_losses():
    graded = grade_oof(_frame([
        {"season": 2023, "week": 1, "margin": 3.0, "spread_line": 3.0, "expected_margin": 5.0},
        {"season": 2023, "week": 2, "margin": 7.0, "spread_line": 3.0, "expected_margin": 3.0},
    ]))
    assert bool(graded.loc[0, "push"]) is True
    assert bool(graded.loc[0, "loss"]) is False
    assert bool(graded.loc[1, "decision"]) is False
    rec = record(graded)
    assert rec.decisions == 1
    assert rec.pushes == 1
    assert rec.no_edge == 1


def test_completed_2026_rows_fail_closed():
    with pytest.raises(RuntimeError, match="2026"):
        grade_oof(_frame([
            {"season": 2026, "week": 1, "margin": 1.0, "spread_line": 0.0, "expected_margin": 2.0},
        ]))


def test_bootstrap_is_frozen_and_classification_gate_is_mechanical():
    rows = []
    for season in (2022, 2023, 2024, 2025):
        for week in (1, 2, 3, 4):
            # Three wins and one loss per season: 75% hit rate, safely above the frozen gate.
            win = week != 4
            rows.append({
                "season": season,
                "week": week,
                "margin": 2.0 if win else -2.0,
                "spread_line": 0.0,
                "expected_margin": 1.0,
            })
    graded = grade_oof(_frame(rows))
    agg = record(graded)
    by_season = season_records(graded)
    boot = bootstrap_hit_rate(graded)
    assert agg.hit_rate_ex_push > REFERENCE_BREAK_EVEN
    assert boot["samples"] == 10_000
    assert boot["seed"] == 20260925
    assert classification(agg, by_season, boot) == "HISTORICALLY_INTERESTING"
