from __future__ import annotations

import pandas as pd
import pytest

from nfl_forecast.availability_qualification import audit_availability_source


def _schedules() -> pd.DataFrame:
    rows = []
    for season in (2022, 2023, 2024, 2025):
        rows.append({
            "game_id": f"{season}_01_AWAY_HOME",
            "season": season,
            "week": 1,
            "home_team": "HOME",
            "away_team": "AWAY",
            "kickoff_utc": f"{season}-09-10T20:00:00+00:00",
        })
    return pd.DataFrame(rows)


def _injuries() -> pd.DataFrame:
    rows = []
    for season in (2022, 2023, 2024, 2025):
        rows.append({
            "season": season,
            "week": 1,
            "team": "HOME",
            "source_player_id": f"source-{season}",
            "status_date": f"{season}-09-09T00:00:00+00:00",
            "practice_status": "Limited Participation In Practice",
            "game_status": "Questionable",
        })
    return pd.DataFrame(rows)


def _crosswalk() -> pd.DataFrame:
    return pd.DataFrame([
        {"source_player_id": f"source-{season}", "player_id": f"gsis-{season}"}
        for season in (2022, 2023, 2024, 2025)
    ])


def test_complete_timestamped_crosswalk_still_fails_without_point_in_time_and_revision_proof():
    result, aligned = audit_availability_source(
        _injuries(),
        _schedules(),
        _crosswalk(),
        source_id="candidate",
        point_in_time_history_proven=False,
        later_revision_reconstruction_proven=False,
    )
    assert result.target_seasons_complete
    assert result.timestamp_parse_rate == 1.0
    assert result.known_by_t120_rate == 1.0
    assert result.crosswalk_missing_rate == 0.0
    assert result.historically_qualified is False
    assert "point_in_time_history_not_proven" in result.reasons
    assert "later_revision_reconstruction_not_proven" in result.reasons
    assert aligned.known_by_t120.all()


def test_source_can_only_qualify_when_all_strict_conditions_are_proven():
    result, _ = audit_availability_source(
        _injuries(),
        _schedules(),
        _crosswalk(),
        source_id="synthetic-qualified-source",
        point_in_time_history_proven=True,
        later_revision_reconstruction_proven=True,
    )
    assert result.historically_qualified is True
    assert result.reasons == ()
    assert result.seasons_present == (2022, 2023, 2024, 2025)


def test_post_t120_status_or_incomplete_2025_coverage_fails():
    injuries = _injuries()
    injuries.loc[injuries.season.eq(2025), "status_date"] = "2025-09-10T19:00:00+00:00"
    result, _ = audit_availability_source(
        injuries,
        _schedules(),
        _crosswalk(),
        source_id="late-source",
        point_in_time_history_proven=True,
        later_revision_reconstruction_proven=True,
    )
    assert result.historically_qualified is False
    assert result.known_by_t120_rate < 1.0
    assert "one_or_more_rows_not_proven_known_by_t120" in result.reasons

    injuries = _injuries().loc[lambda frame: frame.season.ne(2025)]
    result, _ = audit_availability_source(
        injuries,
        _schedules(),
        _crosswalk(),
        source_id="missing-2025",
        point_in_time_history_proven=True,
        later_revision_reconstruction_proven=True,
    )
    assert result.historically_qualified is False
    assert result.target_seasons_complete is False
    assert "target_seasons_incomplete" in result.reasons


def test_ambiguous_or_missing_crosswalk_fails_closed():
    crosswalk = pd.concat([
        _crosswalk(),
        pd.DataFrame([{"source_player_id": "source-2025", "player_id": "other-gsis"}]),
    ], ignore_index=True)
    result, _ = audit_availability_source(
        _injuries(),
        _schedules(),
        crosswalk,
        source_id="ambiguous",
        point_in_time_history_proven=True,
        later_revision_reconstruction_proven=True,
    )
    assert result.historically_qualified is False
    assert result.ambiguous_crosswalk_ids == 1
    assert "ambiguous_source_player_ids" in result.reasons


def test_actual_snaps_or_outcomes_are_never_accepted_as_availability_fields():
    injuries = _injuries()
    injuries["actual_snap_share"] = 0.5
    with pytest.raises(ValueError, match="refuses retrospective fields"):
        audit_availability_source(
            injuries,
            _schedules(),
            _crosswalk(),
            source_id="unsafe",
            point_in_time_history_proven=True,
            later_revision_reconstruction_proven=True,
        )

    injuries = _injuries()
    injuries["home_win"] = 1
    with pytest.raises(ValueError, match="refuses retrospective fields"):
        audit_availability_source(
            injuries,
            _schedules(),
            _crosswalk(),
            source_id="unsafe-outcome",
            point_in_time_history_proven=True,
            later_revision_reconstruction_proven=True,
        )
