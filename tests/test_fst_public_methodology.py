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
    assert "LEVLINE F-ST" in adapter
    assert "Legacy confidence" in adapter
    assert "exact legacy 75/25 rule" in adapter


def test_public_methodology_does_not_claim_legacy_formula_is_current_after_adapter():
    adapter = Path('site/src/fst-production-presentation.js').read_text(encoding='utf-8')
    assert "replaceExactText(root, '75% PURE + 25% MARKET'" in adapter
    assert "LevLine blends 75% PURE with 25% market signal" in adapter
