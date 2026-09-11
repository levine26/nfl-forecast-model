from pathlib import Path


def _active_app() -> str:
    return Path("site/src/AppCoherent.jsx").read_text(encoding="utf-8")


def test_active_site_uses_canonical_consumer_surface_without_dom_patchers():
    main = Path("site/src/main.jsx").read_text(encoding="utf-8")
    assert "./AppCoherent.jsx" in main
    assert "fst-production-presentation" not in main
    assert "installFstProductionPresentationAdapter" not in main
    assert "calibration-presentation" not in main


def test_consumer_surface_reads_canonical_public_forecast_contract():
    app = _active_app()
    assert "public_forecasts.json" in app
    assert "LEVLINE FORECAST" in app
    assert "FOOTBALL SIGNAL" in app
    assert "MARKET SIGNAL" in app
    assert "coherent_fair_margin_home" in app
    assert "official_winner_probability" in app
    assert "FINAL PREGAME" in app
    assert "LIVE FORECAST" in app
    assert "IN PROGRESS" in app
    assert "GRADED" in app


def test_consumer_surface_retires_ambiguous_confidence_and_legacy_pure_labels():
    app = _active_app()
    assert "Confidence" not in app
    assert "Coin Flip" not in app
    assert "Solid" not in app
    assert "High" not in app
    assert "Legacy PURE" not in app
    assert "LEVLINE F-ST" not in app
    assert "F-ST LevLine" not in app


def test_methodology_contains_current_frozen_architecture_only_in_technical_context():
    app = _active_app()
    assert "1.19391 × logit(P_market)" in app
    assert "0.19343 × logit(P_nested_football)" in app
    assert "F-ST-01-FROZEN-2026" in app
    assert "75% PURE + 25% MARKET" not in app
    assert "2026 outcomes" in app
    assert "cannot select, tune or refit" in app
    assert "presentation_margin = margin_sigma × Φ⁻¹(P_home)" in app
    assert "Probability-implied line" in app
    assert "not expected margin" in app


def test_forecast_movement_has_market_lock_and_context_markers():
    app = _active_app()
    assert 'name="LevLine"' in app
    assert 'name="Market"' in app
    assert "lock_timestamp_utc" in app
    assert "CONTEXT ALONGSIDE MOVEMENT" in app
    assert "not claimed as the cause" in app
    assert "ReferenceLine" in app


def test_model_consensus_is_progressively_disclosed_and_diagnostic():
    app = _active_app()
    assert "Model Consensus" in app
    assert "component diagnostics" in app
    assert "Component diagnostics are supporting views, not competing official forecasts." in app
    assert "<details><summary>Model Consensus" in app
