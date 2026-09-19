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
WORKFLOW = ROOT / ".github" / "workflows" / "research_props_v2_prospective_shadow.yml"
NOW = datetime(2026, 9, 18, 17, 30, tzinfo=timezone.utc)
SOURCE_RUN = "12345"
SOURCE_SHA = "a" * 40
SOURCE_TRIGGER_SHA = "b" * 40
SOURCE_PROVIDER = "the_odds_api"
SOURCE_CREDENTIAL_MODE = "configured"
SOURCE_PROVENANCE_SHA = "c" * 64


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
    receipt = module.build_shadow_receipt(
        row,
        config,
        recorded_utc=NOW,
        source_workflow_run=SOURCE_RUN,
        source_head_sha=SOURCE_SHA,
        source_trigger_head_sha=SOURCE_TRIGGER_SHA,
        source_market_provider=SOURCE_PROVIDER,
        source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
        source_provenance_sha256=SOURCE_PROVENANCE_SHA,
    )
    assert receipt is not None
    assert row == before
    assert receipt["source_forecast_id"] == row["forecast_id"]
    assert receipt["source_workflow_run"] == SOURCE_RUN
    assert receipt["source_head_sha"] == SOURCE_SHA
    assert receipt["source_trigger_head_sha"] == SOURCE_TRIGGER_SHA
    assert receipt["source_market_provider"] == SOURCE_PROVIDER
    assert receipt["source_market_credential_mode"] == SOURCE_CREDENTIAL_MODE
    assert receipt["source_provenance_sha256"] == SOURCE_PROVENANCE_SHA
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
    assert module.build_shadow_receipt(
        row,
        config,
        recorded_utc=NOW,
        source_workflow_run=SOURCE_RUN,
        source_head_sha=SOURCE_SHA,
        source_trigger_head_sha=SOURCE_TRIGGER_SHA,
        source_market_provider=SOURCE_PROVIDER,
        source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
        source_provenance_sha256=SOURCE_PROVENANCE_SHA,
    ) is None


def test_started_game_fails_closed():
    module = _module()
    config = module.load_config(CONFIG)
    row = _artifact()["forecasts"][0]
    after = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    assert module.build_shadow_receipt(
        row,
        config,
        recorded_utc=after,
        source_workflow_run=SOURCE_RUN,
        source_head_sha=SOURCE_SHA,
        source_trigger_head_sha=SOURCE_TRIGGER_SHA,
        source_market_provider=SOURCE_PROVIDER,
        source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
        source_provenance_sha256=SOURCE_PROVENANCE_SHA,
    ) is None


def test_shadow_ledger_is_idempotent(tmp_path):
    module = _module()
    config = module.load_config(CONFIG)
    ledger = tmp_path / "challenger_originals.jsonl"
    first = module.record_shadow_receipts(
        _artifact(),
        config,
        ledger,
        source_workflow_run=SOURCE_RUN,
        source_head_sha=SOURCE_SHA,
        source_trigger_head_sha=SOURCE_TRIGGER_SHA,
        source_market_provider=SOURCE_PROVIDER,
        source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
        source_provenance_sha256=SOURCE_PROVENANCE_SHA,
        recorded_utc=NOW,
    )
    second = module.record_shadow_receipts(
        _artifact(),
        config,
        ledger,
        source_workflow_run=SOURCE_RUN,
        source_head_sha=SOURCE_SHA,
        source_trigger_head_sha=SOURCE_TRIGGER_SHA,
        source_market_provider=SOURCE_PROVIDER,
        source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
        source_provenance_sha256=SOURCE_PROVENANCE_SHA,
        recorded_utc=NOW,
    )
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
    a = module.build_shadow_receipt(
        row,
        config,
        recorded_utc=NOW,
        source_workflow_run=SOURCE_RUN,
        source_head_sha=SOURCE_SHA,
        source_trigger_head_sha=SOURCE_TRIGGER_SHA,
        source_market_provider=SOURCE_PROVIDER,
        source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
        source_provenance_sha256=SOURCE_PROVENANCE_SHA,
    )
    b = module.build_shadow_receipt(
        row,
        config,
        recorded_utc=datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc),
        source_workflow_run=SOURCE_RUN,
        source_head_sha=SOURCE_SHA,
        source_trigger_head_sha=SOURCE_TRIGGER_SHA,
        source_market_provider=SOURCE_PROVIDER,
        source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
        source_provenance_sha256=SOURCE_PROVENANCE_SHA,
    )
    assert a is not None and b is not None
    assert a["shadow_id"] == b["shadow_id"]
    assert a["recorded_utc"] != b["recorded_utc"]


def test_exact_source_listener_has_versioned_no_backfill_gate():
    text = WORKFLOW.read_text(encoding="utf-8")
    exact_marker = "EXACT_SOURCE_RUN_LISTENER_VERSION: levline-props-v2-market-shadow-exact-source-v0.1.0"
    provenance_marker = "LIVE_SOURCE_PROVENANCE_REQUIRED_VERSION: levline-props-live-source-provenance-v0.1.0"
    assert exact_marker in text
    assert provenance_marker in text
    assert "source_provenance.json" in text
    assert '--repo "${{ github.repository }}"' in text
    assert "live source provenance trigger SHA mismatch" in text
    assert "live source market snapshot provenance mismatch" in text
    assert "source SHA predates the live-source-provenance market shadow listener" in text


def test_missing_live_source_provenance_fails_closed():
    module = _module()
    config = module.load_config(CONFIG)
    row = deepcopy(_artifact()["forecasts"][0])
    with pytest.raises(module.ShadowError, match="source_market_provider"):
        module.build_shadow_receipt(
            row,
            config,
            recorded_utc=NOW,
            source_workflow_run=SOURCE_RUN,
            source_head_sha=SOURCE_SHA,
            source_trigger_head_sha=SOURCE_TRIGGER_SHA,
            source_market_provider="",
            source_market_credential_mode=SOURCE_CREDENTIAL_MODE,
            source_provenance_sha256=SOURCE_PROVENANCE_SHA,
        )


def test_market_shadow_workflow_legacy_enforcement_is_provenance_aware():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'partial live-source provenance is invalid' in text
    assert 'if any(present):' in text
    assert 'for row in current:' in text
    assert 'row["source_provenance_sha256"]==status["source_provenance_sha256"]' in text
