from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_copilot_media_reads.py"
spec = importlib.util.spec_from_file_location("validate_copilot_media_reads", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_extract_json = module._extract_json


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
