from __future__ import annotations

from scripts.validate_copilot_media_reads import _extract_json


def test_extract_json_preserves_valid_payload():
    payload = _extract_json('{"games":{"g":{"headline":"A","read":"B","sources":[]}}}')
    assert payload["games"]["g"]["headline"] == "A"
    assert payload["games"]["g"]["read"] == "B"


def test_extract_json_repairs_llm_missing_comma():
    malformed = '{"games":{"g":{"headline":"A" "read":"B","sources":[]}}}'
    payload = _extract_json(malformed)
    assert payload["games"]["g"]["headline"] == "A"
    assert payload["games"]["g"]["read"] == "B"


def test_extract_json_repairs_trailing_comma_inside_fence():
    malformed = '```json\n{"games":{"g":{"headline":"A","read":"B","sources":[],},}}\n```'
    payload = _extract_json(malformed)
    assert payload["games"]["g"]["sources"] == []
