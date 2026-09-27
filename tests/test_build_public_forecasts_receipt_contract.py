from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nfl_forecast.public_forecast import PublicForecastError, build_public_forecasts
from scripts.build_public_forecasts import _assert_locked_public_contract, _prepare_locked_receipts


def _row(**overrides):
    row = {
        "game_id": "2026_03_A_B",
        "season": "2026",
        "week": "3",
        "gameday": "2026-09-27",
        "gametime": "16:25",
        "away_team": "A",
        "home_team": "B",
        "final_home_prob": "0.60",
        "margin_sigma": "12.0",
        "expected_margin": "99",
        "expected_total": "45",
        "spread_line": "99",
        "lock_status": "LOCKED",
        "lock_timestamp_utc": "2026-09-27T18:00:00+00:00",
        "locked_ats_status": "VALUE",
        "locked_ats_pick_team": "B",
        "locked_ats_pick_market_spread": "-3.5",
        "locked_ats_model_margin_home": "7.5",
        "locked_ats_market_margin_home": "3.5",
        "locked_ats_home_edge_points": "4.0",
    }
    row.update(overrides)
    return row


def test_locked_public_artifact_uses_same_selected_side_and_market_number_as_receipt():
    official = _prepare_locked_receipts([_row()])
    payload = build_public_forecasts(
        [_row(lock_status="")],
        official,
        now_utc=datetime(2026, 9, 27, 18, 30, tzinfo=timezone.utc),
    )
    _assert_locked_public_contract(payload, official)
    game = payload["games"][0]

    assert game["source_snapshot"] == "LOCKED"
    assert game["ats_model_margin_home"] == pytest.approx(7.5)
    assert game["ats_market_margin_home"] == pytest.approx(3.5)
    assert game["ats_pick_team"] == "B"
    assert game["ats_pick_market_spread"] == pytest.approx(-3.5)


def test_locked_public_artifact_rejects_selected_side_that_diverges_from_receipt():
    official = _prepare_locked_receipts([_row(locked_ats_pick_team="A", locked_ats_pick_market_spread="3.5")])
    payload = build_public_forecasts(
        [_row(lock_status="")],
        official,
        now_utc=datetime(2026, 9, 27, 18, 30, tzinfo=timezone.utc),
    )
    with pytest.raises(PublicForecastError, match="public ATS side diverges"):
        _assert_locked_public_contract(payload, official)


def test_policy_era_locked_public_artifact_fails_closed_without_dedicated_receipt():
    with pytest.raises(PublicForecastError, match="missing its dedicated ATS receipt"):
        _prepare_locked_receipts([
            _row(
                locked_ats_status="",
                locked_ats_pick_team="",
                locked_ats_pick_market_spread="",
                locked_ats_model_margin_home="",
                locked_ats_market_margin_home="",
                locked_ats_home_edge_points="",
            )
        ])
