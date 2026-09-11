from datetime import datetime, timezone

import pytest

from nfl_forecast.public_forecast import (
    PublicForecastError,
    build_public_forecasts,
    probability_implied_margin,
    validate_public_forecast,
)


def row(**overrides):
    base = {
        "game_id": "2026_01_DEN_KC",
        "season": "2026",
        "week": "1",
        "gameday": "2026-09-13",
        "gametime": "16:25",
        "away_team": "DEN",
        "home_team": "KC",
        "final_home_prob": "0.605",
        "fst_pure_home_prob": "0.54",
        "pure_home_prob": "0.57",
        "market_home_prob": "0.572",
        "margin_sigma": "12.9",
        "expected_margin": "-1.7",
        "expected_total": "45.2",
        "spread_line": "2.5",
        "total_line": "44.5",
        "prediction_timestamp_utc": "2026-09-10T20:12:00+00:00",
        "market_snapshot_timestamp_utc": "2026-09-10T20:08:00+00:00",
        "market_snapshot_source": "test-market",
        "model_version": "0.9.0-fst",
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "fst_fallback": "False",
    }
    base.update(overrides)
    return base


def test_probability_bridge_has_correct_direction_and_is_monotonic():
    sigma = 12.9
    assert probability_implied_margin(0.50, sigma) == pytest.approx(0.0)
    assert probability_implied_margin(0.60, sigma) > 0
    assert probability_implied_margin(0.70, sigma) > probability_implied_margin(0.60, sigma)
    assert probability_implied_margin(0.40, sigma) < 0


def test_canonical_contract_reconciles_public_margin_without_rewriting_diagnostic():
    payload = build_public_forecasts([row()], [], now_utc=datetime(2026, 9, 10, 21, tzinfo=timezone.utc))
    game = payload["games"][0]

    assert game["official_winner"] == "KC"
    assert game["official_winner_probability"] == pytest.approx(0.605)
    assert game["football_only_home_win_probability"] == pytest.approx(0.54)
    assert game["market_home_win_probability"] == pytest.approx(0.572)
    assert game["coherent_fair_margin_home"] > 0
    assert game["coherent_fair_spread_home"] < 0
    assert game["projected_home_score"] > game["projected_away_score"]
    assert game["diagnostics"]["independent_margin_home"] == pytest.approx(-1.7)
    assert game["levline_vs_market_winner_probability_pp"] == pytest.approx(3.3)
    assert game["lifecycle_status"] == "LIVE_FORECAST"


def test_locked_game_uses_immutable_lock_row_not_newer_current_row():
    current = row(
        final_home_prob="0.71",
        prediction_timestamp_utc="2026-09-13T20:30:00+00:00",
    )
    locked = row(
        final_home_prob="0.605",
        fst_pure_home_prob="",
        pure_home_prob="0.55",
        prediction_timestamp_utc="2026-09-13T18:20:00+00:00",
        lock_timestamp_utc="2026-09-13T18:21:00+00:00",
        lock_status="LOCKED",
    )
    payload = build_public_forecasts(
        [current],
        [locked],
        now_utc=datetime(2026, 9, 13, 19, tzinfo=timezone.utc),
    )
    game = payload["games"][0]

    assert game["official_home_win_probability"] == pytest.approx(0.605)
    assert game["forecast_timestamp_utc"] == "2026-09-13T18:20:00+00:00"
    assert game["source_snapshot"] == "LOCKED"
    assert game["immutable"] is True
    assert game["signals"]["football"]["kind"] == "LEGACY_FOOTBALL"
    assert game["lifecycle_status"] == "FINAL_PREGAME"


def test_after_kickoff_live_row_without_lock_is_rejected():
    with pytest.raises(PublicForecastError, match="without an immutable pregame lock"):
        build_public_forecasts(
            [row(gameday="2026-09-10", gametime="20:35")],
            [],
            now_utc=datetime(2026, 9, 11, 1, tzinfo=timezone.utc),
        )


def test_validation_rejects_contradictory_public_score():
    game = build_public_forecasts([row()], [], now_utc=datetime(2026, 9, 10, 21, tzinfo=timezone.utc))["games"][0]
    game["projected_home_score"] = 20
    game["projected_away_score"] = 24
    with pytest.raises(PublicForecastError, match="contradictory"):
        validate_public_forecast(game)
