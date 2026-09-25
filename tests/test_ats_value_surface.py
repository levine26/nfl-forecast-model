from pathlib import Path


def test_ats_value_layer_is_mounted_on_canonical_surface():
    coherent = Path('site/src/AppCoherent.jsx').read_text(encoding='utf-8')
    assert "import AtsValueLayer from './AtsValueLayer.jsx'" in coherent
    assert '<AtsValueLayer/>' in coherent
    assert 'Winner and ATS spread value are separate forecasts.' in coherent


def test_ats_value_layer_uses_canonical_public_contract_fields():
    source = Path('site/src/AtsValueLayer.jsx').read_text(encoding='utf-8')
    for field in (
        'ats_pick_team',
        'ats_pick_market_spread',
        'ats_model_margin_home',
        'ats_market_margin_home',
        'ats_edge_points',
        'ats_status',
        'official_winner',
        'official_winner_probability',
    ):
        assert field in source
    assert 'ATS VALUE' in source
    assert 'OUTRIGHT FORECAST' in source
    assert 'ATS SIDE' in source
    assert 'LEVLINE MODEL LINE' in source
    assert 'MARKET LINE' in source
    assert 'Winner / ATS split' in source
    assert "pick!==game.official_winner" in source


def test_ats_surface_does_not_claim_historical_profitability():
    source = Path('site/src/AtsValueLayer.jsx').read_text(encoding='utf-8').lower()
    forbidden = ('profitable', 'guaranteed', 'beat the market', 'winning system', 'roi')
    assert all(term not in source for term in forbidden)
