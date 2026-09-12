from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_copilot_media_reads.py"
spec = importlib.util.spec_from_file_location("validate_copilot_media_reads", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_extract_json = module._extract_json
_contains_labeled_line = module._contains_labeled_line
_ngrams = module._ngrams
_unique_ngrams = module._unique_ngrams


def test_extract_json_preserves_valid_payload():
    payload = _extract_json('{"games":{"g":{"headline":"A","paragraph1":"B","paragraph2":"C","sources":[]}}}')
    assert payload["games"]["g"]["headline"] == "A"


def test_extract_json_repairs_llm_missing_comma():
    malformed = '{"games":{"g":{"headline":"A" "paragraph1":"B","paragraph2":"C","sources":[]}}}'
    payload = _extract_json(malformed)
    assert payload["games"]["g"]["paragraph1"] == "B"


def test_extract_json_repairs_trailing_comma_inside_fence():
    malformed = '```json\n{"games":{"g":{"headline":"A","paragraph1":"B","paragraph2":"C","sources":[],},}}\n```'
    payload = _extract_json(malformed)
    assert payload["games"]["g"]["sources"] == []


def test_model_line_validation_requires_correct_team_value_and_label():
    text = "LevLine projects the Denver Broncos -6.5 on its model line."
    labels = ("levline", "model", "project", "margin")
    assert _contains_labeled_line(text, -6.5, "KC", "DEN", labels)
    assert not _contains_labeled_line(
        "LevLine projects the Kansas City Chiefs -6.5 on its model line.",
        -6.5,
        "KC",
        "DEN",
        labels,
    )


def test_market_line_validation_rejects_wrong_number():
    labels = ("market", "spread", "consensus")
    assert _contains_labeled_line("The market spread is Kansas City Chiefs -3.5.", 3.5, "KC", "DEN", labels)
    assert not _contains_labeled_line("The market spread is Kansas City Chiefs -4.5.", 3.5, "KC", "DEN", labels)


def test_official_status_boilerplate_is_not_a_uniqueness_failure():
    text = (
        "The Falcons listed as questionable after Friday practice while the defense "
        "disguises pressure by rotating safeties late."
    )
    raw = _ngrams(text)
    filtered = _unique_ngrams(text)
    standardized = {gram for gram in raw if "listed as questionable" in gram}

    assert standardized
    assert standardized.isdisjoint(filtered)


def test_substantive_editorial_prose_near_status_language_remains_unique_checked():
    text = (
        "The Falcons ruled out a reserve corner, but the defense disguises pressure "
        "by rotating safeties after the snap."
    )
    filtered = _unique_ngrams(text)

    assert "the defense disguises pressure by rotating safeties" in filtered
