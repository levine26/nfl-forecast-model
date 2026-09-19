import pytest

from nfl_forecast.props21_xtd import (
    build_xtd_from_manifest, fit_xtd_context_model, project_context_xtd,
    td_debt_diagnostic,
)


def history():
    rows = []
    event = 0
    for yardline, touchdowns in ((3, 8), (15, 4), (40, 1), (80, 0)):
        for index in range(10):
            event += 1
            rows.append({"event_id": str(event), "season": 2025, "position": "RB",
                         "kind": "rush", "yardline_100": yardline,
                         "touchdown": int(index < touchdowns),
                         "available_at": "2026-02-01T00:00:00+00:00", "source": "nflverse"})
    return rows


def test_context_probabilities_are_shrunk_and_field_position_monotone():
    model = fit_xtd_context_model(history(), fit_timestamp="2026-03-01T00:00:00+00:00")
    cells = {(row["position"], row["zone"]): row for row in model["cells"] if row["kind"] == "rush"}
    probabilities = [cells[("RB", zone)]["probability"] for zone in range(5)]
    assert probabilities == sorted(probabilities, reverse=True)
    assert all(0 < value < 1 for value in probabilities)
    assert model["trained_through_season"] == 2025
    assert model["conversion_skill_multiplier"] == 1.0


def test_projected_opportunities_create_xtd_without_due_bonus():
    model = fit_xtd_context_model(history(), fit_timestamp="2026-03-01T00:00:00+00:00")
    base = {"projected": True, "source": "pregame-role-model", "available_at": "2026-09-19T18:00:00+00:00",
            "captured_at": "2026-09-19T19:00:00+00:00", "game_id": "g", "team": "ATL",
            "player_id": "p", "position": "RB", "kind": "rush"}
    result = project_context_xtd([
        {**base, "opportunity_id": "goal", "yardline_100": 3, "expected_opportunities": 1.5},
        {**base, "opportunity_id": "far", "yardline_100": 40, "expected_opportunities": 2.0},
    ], model, forecast_timestamp="2026-09-19T20:00:00+00:00",
       kickoff_timestamp="2026-09-20T17:00:00+00:00")
    player = result["players"][0]
    assert player["expected_td"] > 0
    assert player["goal_line_opportunity"] == 1.5
    assert player["td_debt_diagnostic"] is None
    assert player["conversion_skill_multiplier"] == 1.0


def test_current_game_outcomes_and_due_inputs_are_prohibited():
    model = fit_xtd_context_model(history(), fit_timestamp="2026-03-01T00:00:00+00:00")
    row = {"projected": True, "source": "pregame", "available_at": "2026-09-19T18:00:00+00:00",
           "captured_at": "2026-09-19T19:00:00+00:00", "game_id": "g", "team": "ATL",
           "player_id": "p", "position": "RB", "kind": "rush", "opportunity_id": "x",
           "yardline_100": 3, "expected_opportunities": 1.0, "due_bonus": 8}
    with pytest.raises(ValueError, match="postgame"):
        project_context_xtd([row], model, forecast_timestamp="2026-09-19T20:00:00+00:00",
                            kickoff_timestamp="2026-09-20T17:00:00+00:00")
    debt = td_debt_diagnostic(historical_xtd=5, historical_actual_td=2, through_season=2025,
                              available_at="2026-03-01T00:00:00+00:00",
                              forecast_timestamp="2026-09-19T20:00:00+00:00")
    assert debt["td_debt_diagnostic"] == 3
    assert debt["used_in_prediction"] is False


def _live_manifest(row_forecast="2026-09-19T19:00:00+00:00"):
    kickoff = "2026-09-20T17:00:00+00:00"
    common = {
        "game_id": "g",
        "team": "ATL",
        "prior_model_trained_through_season": 2025,
        "feature_data_horizon": "2026-09-19T18:00:00+00:00",
        "forecast_timestamp": row_forecast,
        "kickoff_timestamp": kickoff,
    }
    return {
        "game_id": "g",
        "forecast_timestamp_utc": "2026-09-19T20:00:00+00:00",
        "kickoff_utc": kickoff,
        "efficiency_player_parameters": [{
            **common,
            "player_id": "p",
            "position": "RB",
            "expected_passing_tds": 0.0,
            "expected_receiving_tds": 0.1,
            "expected_rushing_tds": 0.2,
            "expected_pass_attempts": 0.0,
            "expected_targets": 4.0,
            "expected_carries": 10.0,
            "expected_red_zone_targets": 1.0,
            "expected_goal_line_carries": 2.0,
        }],
        "team_td_parameters": [{
            **common,
            "expected_passing_td_opportunities": 0.1,
            "expected_rushing_td_opportunities": 0.2,
        }],
    }


def test_manifest_adapter_accepts_point_in_time_rows_older_than_manifest_forecast():
    result = build_xtd_from_manifest(_live_manifest())
    assert result["audit"]["player_count"] == 1
    assert result["players"][0]["player_id"] == "p"


def test_manifest_adapter_rejects_rows_newer_than_manifest_forecast():
    with pytest.raises(ValueError, match="row forecast after manifest forecast"):
        build_xtd_from_manifest(_live_manifest("2026-09-19T20:01:00+00:00"))
