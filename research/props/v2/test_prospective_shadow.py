from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "research" / "props" / "v2" / "record_prospective_shadow.py"
FIXTURE = ROOT / "research" / "props" / "fixtures" / "props_forecasts.json"
CONFIG = ROOT / "research" / "props" / "v2" / "prospective_shadow_v0_1.json"
NOW = datetime(2026, 9, 18, 17, 30, tzinfo=timezone.utc)


def _module():
    spec = importlib.util.spec_from_file_location("props_shadow_tested", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _artifact():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_frozen_config_is_research_only_and_pre2026_fit():
    module = _module()
    config = module.load_config(CONFIG)
    assert config["production_authorized"] is False
    assert config["completed_2026_outcomes_used_for_selection_or_fit"] is False
    assert config["market_v1_residual"]["intercept"] == pytest.approx(-0.0718941364380648)
    assert config["market_v1_residual"]["residual_beta"] == pytest.approx(0.043750664468122)


def test_build_shadow_records_market_and_residual_without_mutating_v1():
    module = _module()
    config = module.load_config(CONFIG)
    row = deepcopy(_artifact()["forecasts"][0])
    before = deepcopy(row)
    receipt = module.build_shadow_receipt(row, config, recorded_utc=NOW)
    assert receipt is not None
    assert row == before
    assert receipt["source_forecast_id"] == row["forecast_id"]
    assert receipt["market_only"]["p_over"] == pytest.approx(0.5)
    assert receipt["market_only"]["direction"] is None
    assert 0.0 < receipt["market_v1_residual"]["p_over"] < 1.0
    assert receipt["governance"]["production_authorized"] is False
    assert receipt["governance"]["winner_model_mutated"] is False


def test_binary_td_is_outside_frozen_shadow_population():
    module = _module()
    config = module.load_config(CONFIG)
    row = _artifact()["forecasts"][2]
    assert row["prop_type"] == "anytime_td"
    assert module.build_shadow_receipt(row, config, recorded_utc=NOW) is None


def test_started_game_fails_closed():
    module = _module()
    config = module.load_config(CONFIG)
    row = _artifact()["forecasts"][0]
    after = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    assert module.build_shadow_receipt(row, config, recorded_utc=after) is None


def test_shadow_ledger_is_idempotent(tmp_path):
    module = _module()
    config = module.load_config(CONFIG)
    ledger = tmp_path / "challenger_originals.jsonl"
    first = module.record_shadow_receipts(_artifact(), config, ledger, recorded_utc=NOW)
    second = module.record_shadow_receipts(_artifact(), config, ledger, recorded_utc=NOW)
    assert first["appended"] == 3
    assert second["appended"] == 0
    assert second["skipped_existing"] == 3
    rows = module.read_jsonl(ledger)
    assert len(rows) == 3
    assert len({row["shadow_id"] for row in rows}) == 3


def test_same_source_forecast_has_stable_shadow_identity():
    module = _module()
    config = module.load_config(CONFIG)
    row = _artifact()["forecasts"][1]
    a = module.build_shadow_receipt(row, config, recorded_utc=NOW)
    b = module.build_shadow_receipt(
        row, config, recorded_utc=datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc)
    )
    assert a is not None and b is not None
    assert a["shadow_id"] == b["shadow_id"]
    assert a["recorded_utc"] != b["recorded_utc"]
