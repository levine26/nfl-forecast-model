from pathlib import Path


def test_active_site_installs_fst_production_presentation_adapter():
    main = Path('site/src/main.jsx').read_text(encoding='utf-8')
    assert "./fst-production-presentation.js" in main
    assert "installFstProductionPresentationAdapter()" in main


def test_public_fst_presentation_replaces_legacy_formula_and_labels_diagnostics():
    adapter = Path('site/src/fst-production-presentation.js').read_text(encoding='utf-8')
    assert "Frozen F-ST-01 market + nested-PURE logit stack" in adapter
    assert "1.19391 × logit(MARKET)" in adapter
    assert "0.19343 × logit(F-ST NESTED PURE)" in adapter
    assert "LEGACY PURE" in adapter
    assert '<small>LEVLINE</small>' in adapter
    assert '<small>LEVLINE F-ST</small>' not in adapter
    assert "Legacy confidence" not in adapter
    assert "Legacy model disagreement" not in adapter
    assert "exact legacy 75/25 rule" in adapter


def test_public_methodology_does_not_claim_legacy_formula_is_current_after_adapter():
    adapter = Path('site/src/fst-production-presentation.js').read_text(encoding='utf-8')
    assert "replaceExactText(root, '75% PURE + 25% MARKET'" in adapter
    assert "LevLine blends 75% PURE with 25% market signal" in adapter


def test_public_presentation_separates_probability_from_conflicting_margin_model():
    adapter = Path('site/src/fst-production-presentation.js').read_text(encoding='utf-8')
    assert "scoreWinnerFromText" in adapter
    assert "Official pick ${pick} · separate margin model favors ${marginWinner}" in adapter
    assert "Separate margin model favors ${marginWinner}" in adapter
    assert "Margin-model score" in adapter
    assert "Margin-model spread" in adapter
    assert "The official Sunday Signal pick is the LevLine win probability shown above." in adapter
