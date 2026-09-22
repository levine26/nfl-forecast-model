from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRID = ROOT / 'research' / 'props' / 'v22' / 'CHALLENGER_GRID.json'

def test_props22_grid_is_fixed_research_only_and_non_outcome_fitted():
    payload = json.loads(GRID.read_text(encoding='utf-8'))
    assert payload['status'] == 'FROZEN_BEFORE_FUTURE_HOLDOUT'
    assert payload['research_only'] is True
    assert payload['production_authorized'] is False
    assert payload['outcome_fit_allowed'] is False
    assert payload['baseline_model'] == 'levline-props-2.1-sunday-v0.1'
    ids = [row['id'] for row in payload['challengers']]
    assert ids == ['P21_BASE','P22_RESIDUAL_25','P22_RESIDUAL_50','P22_CAL_50','P22_RESIDUAL50_CAL50']
    for row in payload['challengers']:
        market = float(row['line_market_weight'])
        model = float(row['line_model_weight'])
        shrink = float(row['probability_shrink_to_half'])
        assert 0.0 <= market <= 1.0
        assert 0.0 <= model <= 1.0
        assert abs((market + model) - 1.0) < 1e-12
        assert shrink in {0.0, 0.5}
    minimum = payload['minimum_promotion_evidence']
    assert minimum['future_weeks'] >= 3
    assert minimum['finalized_games'] >= 30
    assert minimum['market_matched_observations'] >= 1000
    assert minimum['prop_family_observations'] >= 250
    forbidden = set(payload['forbidden'])
    assert 'week2_parameter_fit' in forbidden
    assert 'retrospective_signal_relabel' in forbidden
    assert 'postkickoff_market_use' in forbidden
    assert 'production_winner_model_mutation' in forbidden