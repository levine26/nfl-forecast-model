from nfl_forecast.props21_qa import check_accounting, evaluate_forecast_qa


def forecast(mean=50.0):
    return {"player_id": "p", "prop_type": "receiving_yards", "player_identity_resolved": True,
            "forecast_timestamp_utc": "2026-09-19T20:00:00+00:00",
            "kickoff_utc": "2026-09-20T17:00:00+00:00",
            "model": {"mean": mean, "fair_line": mean, "over_probability": .60,
                      "simulation_count": 20000, "simulation_accounting_ok": True},
            "market": {"captured_utc": "2026-09-19T19:50:00+00:00", "line": 45.5,
                       "no_vig_over_probability": .50},
            "data_quality": {"critical_ok": True}, "provenance": {"market": {}}}


def role(**changes):
    value = {"player_id": "p", "identity_resolved": True, "role_state": "STARTER_CONFIRMED",
             "availability_state": "AVAILABLE", "current_news_coverage": True}
    value.update(changes)
    return value


def test_clean_disagreement_is_radar_but_never_betting_eligible():
    qa = evaluate_forecast_qa(forecast(), role_state=role(),
                              market_state={"status": "MARKET_DISTRIBUTION_SUPPORTED", "book_count": 3},
                              opportunity={"targets": 7})
    assert qa["signal_state"] == "RADAR"
    assert qa["classification"] == "MODEL DISAGREEMENT"
    assert qa["betting_eligible"] is False
    assert qa["uncertainty"]["calibrated"] is False


def test_out_player_and_market_with_zero_output_are_blocked():
    out = evaluate_forecast_qa(forecast(), role_state=role(role_state="OUT", availability_state="OUT"),
                               market_state={"status": "MARKET_DISTRIBUTION_SUPPORTED", "book_count": 3},
                               opportunity={"targets": 7})
    codes = {flag["code"] for flag in out["flags"]}
    assert "OUT_PLAYER_WITH_OPPORTUNITY" in codes
    assert out["signal_state"] == "NO SIGNAL"
    zero = evaluate_forecast_qa(forecast(0), role_state=role(),
                                market_state={"status": "MARKET_DISTRIBUTION_SUPPORTED", "book_count": 3},
                                opportunity={"targets": 0})
    assert {"MARKET_WITH_ZERO_MODEL_OPPORTUNITY", "MARKET_WITH_ZERO_MODEL_OUTPUT"} <= {f["code"] for f in zero["flags"]}
    assert zero["publication_eligible"] is False


def test_accounting_checks_expectations_and_skips_medians():
    accounting = {"relationships": [
        {"name": "qb_yards", "source": "model", "statistic": "expectation", "complete": True,
         "aggregate_mean": 250, "component_means": [100, 90], "residual_mean": 30},
        {"name": "market_medians", "source": "market", "statistic": "median", "complete": True,
         "aggregate_mean": 250, "component_means": [100, 90], "residual_mean": 60},
    ]}
    result = check_accounting(accounting)
    assert result["flags"][0]["code"] == "PLAYER_TEAM_ACCOUNTING_INCONSISTENCY"
    assert result["skipped"][0]["name"] == "market_medians"


def test_depth_chart_expected_starter_cannot_be_radar_without_news_and_availability():
    depth_role = role(
        role_state="STARTER_EXPECTED",
        availability_state="UNKNOWN",
        current_news_coverage=False,
    )
    qa = evaluate_forecast_qa(
        forecast(),
        role_state=depth_role,
        market_state={"status": "MARKET_DISTRIBUTION_SUPPORTED", "book_count": 3},
        opportunity={"targets": 7},
    )
    assert qa["signal_state"] == "WATCH"
    assert qa["betting_eligible"] is False
    codes = {flag["code"] for flag in qa["flags"]}
    assert {"UNKNOWN_AVAILABILITY", "ROLE_UNCERTAINTY", "MISSING_CURRENT_NEWS_COVERAGE"} <= codes
