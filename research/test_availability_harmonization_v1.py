from __future__ import annotations

import pandas as pd

from research.availability_harmonization_v1 import (
    build_season_reconstruction,
    kickoff_index,
    missingness_report,
    parse_date_modified_utc,
    standardize_canonical,
    summarize_season,
)


def _nflverse(*, season: int = 2022, practice_status: str = "Limited Participation in Practice") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "season": season,
            "week": 1,
            "team": "ARI",
            "gsis_id": "00-0034346",
            "position": "G",
            "full_name": "Will Hernandez",
            "first_name": "Will",
            "last_name": "Hernandez",
            "practice_status": practice_status,
            "report_status": "Questionable",
            "date_modified": f"{season}-09-09 16:15:00",
        }
    ])


def _official(*, season: int = 2022, practice_status: str = "Limited Participation in Practice") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "season": season,
            "week": 1,
            "team": "ARI",
            "external_player": "Will Hernandez",
            "external_position": "G",
            "external_injury": "Knee",
            "external_practice_status": practice_status,
            "external_game_status": "Questionable",
            "external_source": "nfl_com_official_injury_page",
            "source_url": f"https://www.nfl.com/injuries/league/{season}/reg1",
        }
    ])


def _schedules(*, season: int = 2022) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": f"{season}_01_KC_ARI",
            "season": season,
            "week": 1,
            "game_type": "REG",
            "home_team": "ARI",
            "away_team": "KC",
            "gameday": f"{season}-09-11",
            "gametime": "16:25",
        }
    ])


def _gates() -> dict:
    return {
        "official_nfl_pages_required_per_season": 22,
        "stable_gsis_missing_rate_max": 0.0,
        "schedule_match_rate_min": 1.0,
        "unique_identity_match_rate_min": 0.995,
        "practice_status_agreement_rate_min": 0.985,
        "diagnostic_game_status_agreement_rate_min": 0.985,
        "known_by_t120_rate_required_among_matched_rows": 1.0,
        "fully_qualified_practice_state_rate_min": 0.99,
        "legacy_date_modified_parse_rate_min": 0.995,
        "duplicate_identity_rows_allowed": 0,
    }


def test_date_modified_uses_documented_nflverse_timezone_but_is_diagnostic_only() -> None:
    values = pd.Series(["2022-09-09 16:15:00", "not-a-time"])
    parsed = parse_date_modified_utc(values)
    assert str(parsed.iloc[0]) == "2022-09-09 20:15:00+00:00"
    assert pd.isna(parsed.iloc[1])


def test_uniform_official_filing_day_is_before_t120_for_sunday_game() -> None:
    index = kickoff_index(_schedules(), season=2022)
    ari = index[index.team.eq("ARI")].iloc[0]
    assert str(ari.kickoff_utc) == "2022-09-11 20:25:00+00:00"
    assert str(ari.report_deadline_eod_utc) == "2022-09-10 03:59:59+00:00"
    assert ari.report_deadline_eod_utc <= ari.kickoff_utc - pd.Timedelta(minutes=120)


def test_canonical_state_requires_identity_crosscheck_chronology_and_practice_agreement() -> None:
    result = build_season_reconstruction(
        _nflverse(),
        _official(),
        _schedules(),
        season=2022,
    )
    row = result.iloc[0]
    assert bool(row.identity_matched)
    assert bool(row.schedule_matched)
    assert bool(row.practice_status_agrees)
    assert bool(row.game_status_agrees)
    assert bool(row.known_by_t120)
    assert bool(row.fully_qualified_practice_state)
    assert row.canonical_practice_state == "limited"
    assert row.unresolved_reason == ""
    assert not bool(row.historical_game_status_feature_authorized)
    assert not bool(row.postgame_information_used)


def test_practice_disagreement_fails_closed_to_unknown() -> None:
    result = build_season_reconstruction(
        _nflverse(practice_status="Limited Participation in Practice"),
        _official(practice_status="Full Participation in Practice"),
        _schedules(),
        season=2022,
    )
    row = result.iloc[0]
    assert bool(row.identity_matched)
    assert not bool(row.practice_status_agrees)
    assert not bool(row.fully_qualified_practice_state)
    assert row.canonical_practice_state == "unknown"
    assert "practice_state_crosscheck_mismatch" in row.unresolved_reason


def test_unrecognized_practice_state_is_never_interpreted_as_healthy() -> None:
    result = build_season_reconstruction(
        _nflverse(practice_status="Not Reported"),
        _official(practice_status="Not Reported"),
        _schedules(),
        season=2022,
    )
    row = result.iloc[0]
    assert not bool(row.recognized_practice_state)
    assert not bool(row.fully_qualified_practice_state)
    assert row.canonical_practice_state == "unknown"
    assert "practice_state_unrecognized" in row.unresolved_reason


def test_summary_passes_only_when_all_preregistered_gates_pass() -> None:
    result = build_season_reconstruction(
        _nflverse(),
        _official(),
        _schedules(),
        season=2022,
    )
    summary = summarize_season(
        result,
        season=2022,
        official_crosscheck_rows=1,
        official_pages_collected=22,
        gates=_gates(),
    )
    assert summary.qualified
    assert summary.reasons == ()
    assert summary.unique_identity_match_rate == 1.0
    assert summary.known_by_t120_rate_among_matched_rows == 1.0
    assert summary.date_modified_parse_rate == 1.0


def test_summary_does_not_relax_failed_crosscheck_gate() -> None:
    result = build_season_reconstruction(
        _nflverse(),
        _official(practice_status="Full Participation in Practice"),
        _schedules(),
        season=2022,
    )
    summary = summarize_season(
        result,
        season=2022,
        official_crosscheck_rows=1,
        official_pages_collected=22,
        gates=_gates(),
    )
    assert not summary.qualified
    assert "practice_status_agreement_rate_below_gate" in summary.reasons
    assert "fully_qualified_practice_state_rate_below_gate" in summary.reasons


def test_standardized_output_and_missingness_preserve_unknown_reason() -> None:
    result = build_season_reconstruction(
        _nflverse(practice_status="Not Reported"),
        _official(practice_status="Not Reported"),
        _schedules(),
        season=2022,
    )
    standardized = standardize_canonical(result)
    report = missingness_report(standardized)
    assert standardized.iloc[0].canonical_practice_state == "unknown"
    assert report.iloc[0].unknown_rows == 1
    assert report.iloc[0].unknown_rate == 1.0
