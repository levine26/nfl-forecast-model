from __future__ import annotations

import pandas as pd

from nfl_forecast.availability_research import (
    PROHIBITED_AVAILABILITY_INPUTS,
    qualify_v09b_sources,
)


def test_v09b_is_blocked_when_2025_injury_reports_are_missing():
    injuries = pd.DataFrame(
        {
            "season": [2022, 2023, 2024],
            "gsis_id": ["00-1", "00-2", "00-3"],
        }
    )
    depth = pd.DataFrame(
        {
            "dt": ["2025-09-01T07:00:00Z"],
            "gsis_id": ["00-4"],
        }
    )
    report = qualify_v09b_sources(injuries, depth)
    assert report["status"] == "blocked"
    assert any("2025" in blocker for blocker in report["blockers"])
    assert report["p_active_model_built"] is False
    assert report["2026_outcomes_used"] == 0


def test_timestamped_depth_chart_does_not_override_missing_injury_season():
    injuries = pd.DataFrame(
        {
            "season": [2022, 2023, 2024],
            "gsis_id": ["00-1", "00-2", "00-3"],
        }
    )
    depth = pd.DataFrame(
        {
            "dt": ["2025-09-01T07:00:00Z", "2025-09-02T07:00:00Z"],
            "gsis_id": ["00-4", "00-5"],
        }
    )
    report = qualify_v09b_sources(injuries, depth)
    assert report["depth_2025"]["timestamp_field_present"] is True
    assert report["status"] == "blocked"


def test_complete_synthetic_target_coverage_can_reach_research_qualification():
    injuries = pd.DataFrame(
        {
            "season": [2022, 2023, 2024, 2025],
            "gsis_id": ["00-1", "00-2", "00-3", "00-4"],
        }
    )
    depth = pd.DataFrame(
        {
            "dt": ["2025-09-01T07:00:00Z"],
            "gsis_id": ["00-4"],
        }
    )
    report = qualify_v09b_sources(injuries, depth)
    assert report["status"] == "qualified_for_model_research"


def test_hindsight_inputs_are_explicitly_prohibited():
    prohibited = set(PROHIBITED_AVAILABILITY_INPUTS)
    assert "postgame_snap_share" in prohibited
    assert "final_starter_identity" in prohibited
    assert "later_injury_designation" in prohibited
