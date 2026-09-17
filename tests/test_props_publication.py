from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from nfl_forecast.props_publication import (
    PropsPublicationError,
    append_jsonl_immutable,
    build_history_view,
    build_public_props,
    grade_forecast_receipt,
    make_closing_event,
    make_forecast_receipt,
    normalize_public_forecast,
    read_jsonl,
)

FIXTURE = Path(__file__).resolve().parents[1] / "research" / "props" / "fixtures" / "props_forecasts.json"
NOW = datetime(2026, 9, 17, 21, 0, tzinfo=timezone.utc)


def artifact():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_builds_research_beta_and_preserves_signal_counts():
    payload = build_public_props(artifact(), now_utc=NOW)
    assert payload["research_label"] == "LEVLINE PROPS — RESEARCH BETA"
    assert payload["profitability_claim"] is False
    assert payload["summary"] == {"total": 4, "model_edge": 2, "watch": 1, "no_signal": 1}


def test_fair_line_probability_edge_and_fair_odds_are_public():
    row = normalize_public_forecast(artifact()["forecasts"][0], now_utc=NOW)
    assert row["signal_state"] == "MODEL EDGE"
    assert row["model"]["fair_line"] == 83.5
    assert row["model"]["line_difference"] == 7.0
    assert row["model"]["over_probability"] == 0.618
    assert row["model"]["probability_edge"] == pytest.approx(0.118)
    assert row["model"]["fair_odds_american"] == -162


def test_binary_td_card_does_not_require_fair_line():
    row = normalize_public_forecast(artifact()["forecasts"][2], now_utc=NOW)
    assert row["market_kind"] == "BINARY_TD"
    assert row["signal_state"] == "MODEL EDGE"
    assert row["model"]["fair_line"] is None
    assert row["model"]["td_probability"] == 0.64
    assert row["model"]["fair_odds_american"] == -178
    assert row["model"]["probability_edge"] == pytest.approx(0.12)


def test_low_quality_can_never_render_model_edge():
    row = normalize_public_forecast(artifact()["forecasts"][3], now_utc=NOW)
    assert row["signal_state"] == "NO SIGNAL"
    assert "critical_data_quality_below_minimum" in row["unavailable_reasons"]


def test_unresolved_identity_fails_closed():
    raw = deepcopy(artifact()["forecasts"][0])
    raw["player_identity_resolved"] = False
    row = normalize_public_forecast(raw, now_utc=NOW)
    assert row["signal_state"] == "NO SIGNAL"
    assert "player_identity_unresolved" in row["unavailable_reasons"]


def test_invalid_probability_accounting_fails_closed():
    raw = deepcopy(artifact()["forecasts"][0])
    raw["model"]["over_probability"] = 0.8
    raw["model"]["under_probability"] = 0.4
    row = normalize_public_forecast(raw, now_utc=NOW)
    assert row["signal_state"] == "NO SIGNAL"
    assert "probability_accounting_failed" in row["unavailable_reasons"]


def test_started_game_fails_closed_even_when_numbers_are_valid():
    raw = deepcopy(artifact()["forecasts"][0])
    after_kickoff = datetime(2026, 9, 20, 18, 0, tzinfo=timezone.utc)
    row = normalize_public_forecast(raw, now_utc=after_kickoff)
    assert row["signal_state"] == "NO SIGNAL"
    assert "game_started" in row["unavailable_reasons"]


def test_forecast_receipts_are_idempotent_but_conflicts_are_rejected(tmp_path):
    raw = artifact()["forecasts"][0]
    receipt = make_forecast_receipt(raw, recorded_utc=NOW)
    ledger = tmp_path / "forecast_originals.jsonl"
    assert append_jsonl_immutable(ledger, [receipt], identity_key="forecast_id") == 1
    assert append_jsonl_immutable(ledger, [receipt], identity_key="forecast_id") == 0
    conflicting = deepcopy(receipt)
    conflicting["original_forecast"]["market"]["line"] = 99.5
    with pytest.raises(PropsPublicationError, match="immutable history collision"):
        append_jsonl_immutable(ledger, [conflicting], identity_key="forecast_id")
    assert read_jsonl(ledger)[0]["original_forecast"]["market"]["line"] == 76.5


def test_closing_and_grading_overlay_never_mutates_original():
    raw = artifact()["forecasts"][0]
    receipt = make_forecast_receipt(raw, recorded_utc=NOW)
    before = deepcopy(receipt["original_forecast"])
    close = make_closing_event(receipt["forecast_id"], captured_utc="2026-09-20T16:55:00+00:00", source="consensus", line=82.5, over_price_american=-112, under_price_american=-108)
    grade = grade_forecast_receipt(receipt, actual_result=101, graded_utc="2026-09-20T21:00:00+00:00")
    view = build_history_view([receipt], [close], [grade])[0]
    assert receipt["original_forecast"] == before
    assert view["original_forecast"]["market"]["line"] == 76.5
    assert view["original_forecast"]["model"]["fair_line"] == 83.5
    assert view["closing_market"]["line"] == 82.5
    assert view["grade"]["actual_result"] == 101
    assert view["grade"]["grading_result"] == "WIN"


def test_reception_push_is_graded_without_rewriting_forecast():
    raw = artifact()["forecasts"][3]
    receipt = make_forecast_receipt(raw, recorded_utc=NOW)
    grade = grade_forecast_receipt(receipt, actual_result=5, graded_utc="2026-09-20T23:00:00+00:00")
    assert grade["market_outcome"] == "PUSH"
    assert grade["grading_result"] == "PUSH"
    assert receipt["original_forecast"]["market"]["line"] == 5.0


def test_rejects_wrong_upstream_contract_version():
    payload = artifact(); payload["contract_version"] = "wrong-version"
    with pytest.raises(PropsPublicationError, match="unsupported upstream Props contract"):
        build_public_props(payload, now_utc=NOW)


def test_missing_data_horizon_market_timestamp_source_and_model_version_fail_closed():
    row = deepcopy(artifact()["forecasts"][0])
    row.pop("data_horizon_utc", None); row["market"].pop("captured_utc", None); row["market"].pop("source", None); row["model"].pop("version", None)
    public = normalize_public_forecast(row, now_utc=NOW)
    assert public["signal_state"] == "NO SIGNAL"
    assert {"data_horizon_timestamp_invalid", "market_timestamp_invalid", "market_source_missing", "model_version_missing"}.issubset(set(public["unavailable_reasons"]))


def test_missing_prices_or_no_vig_market_probability_fail_closed():
    row = deepcopy(artifact()["forecasts"][0]); row["market"].pop("over_price_american", None); row["market"].pop("no_vig_over_probability", None)
    public = normalize_public_forecast(row, now_utc=NOW)
    assert public["signal_state"] == "NO SIGNAL"
    assert "market_price_invalid" in public["unavailable_reasons"]
    assert "market_no_vig_probability_invalid" in public["unavailable_reasons"]


def test_upstream_artifact_requires_timezone_aware_generated_timestamp():
    payload = artifact(); payload["generated_utc"] = "2026-09-17T21:00:00"
    with pytest.raises(PropsPublicationError, match="timezone-aware generated_utc"):
        build_public_props(payload, now_utc=NOW)


def test_original_receipt_cannot_be_created_retrospectively():
    with pytest.raises(PropsPublicationError, match="retrospective Props forecast receipt"):
        make_forecast_receipt(artifact()["forecasts"][0], recorded_utc=datetime(2026, 9, 20, 17, 1, tzinfo=timezone.utc))


def test_grade_timestamp_must_be_after_kickoff():
    receipt = make_forecast_receipt(artifact()["forecasts"][0], recorded_utc=NOW)
    with pytest.raises(PropsPublicationError, match="after the original forecast kickoff"):
        grade_forecast_receipt(receipt, actual_result=101, graded_utc="2026-09-20T16:59:00+00:00")
