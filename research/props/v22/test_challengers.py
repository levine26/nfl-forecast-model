from __future__ import annotations

import pytest

from research.props.v22.challengers import Props22Error, build_challenger_set


def _source(**overrides):
    row = {
        'forecast_id': 'p21_test',
        'player_id': '00-1',
        'player_name': 'Test Player',
        'team': 'ARI',
        'opponent': 'SEA',
        'position': 'WR',
        'game_id': '2026_03_ARI_SEA',
        'prop_type': 'receiving_yards',
        'kickoff_utc': '2026-09-27T20:25:00+00:00',
        'forecast_timestamp_utc': '2026-09-27T16:00:00+00:00',
        'model_mean': 82.0,
        'model_median': 80.0,
        'probability_over': 0.70,
        'probability_td': None,
        'market_line': 70.0,
        'market_probability_over': 0.55,
        'market_probability_td': None,
        'role_state': {'state': 'STARTER_EXPECTED'},
        'market_state': {'book_count': 6},
        'qa': {'research_eligible': True},
        'provenance': {
            'challenger_model_version': 'levline-props-2.1-sunday-v0.1',
            'source_data_horizon_utc': '2026-09-27T15:55:00+00:00',
        },
    }
    row.update(overrides)
    return row


def _by_id(rows):
    return {row['challenger_id']: row for row in rows}


def test_fixed_grid_applies_expected_line_and_probability_math():
    rows = _by_id(build_challenger_set(_source()))
    assert rows['P21_BASE']['line']['challenger_line'] == pytest.approx(80.0)
    assert rows['P22_RESIDUAL_25']['line']['challenger_line'] == pytest.approx(72.5)
    assert rows['P22_RESIDUAL_50']['line']['challenger_line'] == pytest.approx(75.0)
    assert rows['P22_CAL_50']['probability']['challenger_probability'] == pytest.approx(0.60)
    combo = rows['P22_RESIDUAL50_CAL50']
    assert combo['line']['challenger_line'] == pytest.approx(75.0)
    assert combo['probability']['challenger_probability'] == pytest.approx(0.60)
    assert combo['line']['model_residual_vs_market'] == pytest.approx(10.0)
    assert combo['probability']['model_residual_vs_market'] == pytest.approx(0.15)
    assert combo['research_only'] is True
    assert combo['production_authorized'] is False
    assert combo['outcome'] is None
    assert len(combo['receipt_sha256']) == 64


def test_missing_market_line_only_disables_market_anchored_line_candidates():
    rows = _by_id(build_challenger_set(_source(market_line=None)))
    assert rows['P21_BASE']['line']['line_available'] is True
    assert rows['P22_CAL_50']['line']['line_available'] is True
    for cid in ['P22_RESIDUAL_25','P22_RESIDUAL_50','P22_RESIDUAL50_CAL50']:
        assert rows[cid]['line']['line_available'] is False
        assert rows[cid]['line']['unavailable_reason'] == 'missing_market_line_for_residual_challenger'


def test_binary_td_keeps_probability_challengers_without_inventing_a_line():
    rows = _by_id(build_challenger_set(_source(
        prop_type='anytime_td',
        model_median=None,
        market_line=None,
        probability_over=None,
        probability_td=0.40,
        market_probability_over=None,
        market_probability_td=0.30,
    )))
    for row in rows.values():
        assert row['line']['line_available'] is False
        assert row['line']['unavailable_reason'] == 'binary_td_market_has_no_continuous_line'
        assert row['probability']['probability_available'] is True
    assert rows['P22_CAL_50']['probability']['challenger_probability'] == pytest.approx(0.45)
    assert rows['P22_CAL_50']['probability']['model_residual_vs_market'] == pytest.approx(0.10)


def test_outcome_contamination_is_rejected():
    source = _source(outcome={'actual': 88.0})
    with pytest.raises(Props22Error, match='outcome-contaminated'):
        build_challenger_set(source)