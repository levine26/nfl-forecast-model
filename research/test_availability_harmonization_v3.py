from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import research.run_availability_harmonization_v3 as v3


CONTRACT = json.loads(Path("research/availability/2022_2025_harmonization_contract_v3.json").read_text())


def _canonical_row(*, timestamp: str = "2024-01-18T18:00:00Z", t120: str = "2024-01-20T21:30:00Z") -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2023,
        "week": 20,
        "team": "BAL",
        "gsis_id": "00-0034753",
        "position": "TE",
        "full_name": "Mark Andrews",
        "first_name": "Mark",
        "last_name": "Andrews",
        "practice_status": "Full Participation in Practice",
        "report_status": "Questionable",
        "date_modified": timestamp,
        "external_player": pd.NA,
        "external_position": pd.NA,
        "external_injury": pd.NA,
        "external_practice_status": pd.NA,
        "external_game_status": pd.NA,
        "external_source": pd.NA,
        "source_url": pd.NA,
        "identity_match_method": pd.NA,
        "identity_matched": False,
        "nflverse_practice_normalized": "full",
        "external_practice_normalized": "",
        "nflverse_game_normalized": "questionable",
        "external_game_normalized": "",
        "recognized_practice_state": True,
        "practice_status_agrees": False,
        "game_status_agrees": False,
        "date_modified_utc": pd.Timestamp(timestamp),
        "game_id": "2023_20_HOU_BAL",
        "kickoff_utc": pd.Timestamp("2024-01-20T23:30:00Z"),
        "report_deadline_eod_utc": pd.Timestamp("2024-01-19T04:59:59Z"),
        "schedule_matched": True,
        "t120_utc": pd.Timestamp(t120),
        "known_by_t120": False,
        "fully_qualified_practice_state": False,
        "canonical_practice_state": "unknown",
        "availability_source": "nflverse+official_nfl_historical_report_crosscheck",
        "chronology_policy": "official_game_status_report_day_eod_eastern_before_t120",
        "historical_game_status_feature_authorized": False,
        "postgame_information_used": False,
        "unresolved_reason": "identity_unresolved",
    }])


def _week20_evidence(*, published_at: str = "2024-01-18T19:51:00Z") -> dict:
    return {
        "source_presence_gate_passed": True,
        "sources": [{"url": "https://example.test/report", "published_at_utc": published_at}],
    }


def test_v3_contract_does_not_relax_v1_v2_thresholds() -> None:
    assert CONTRACT["unchanged_v1_v2_gates"]["canonical_to_official_identity_min"] == 0.995
    assert CONTRACT["unchanged_v1_v2_gates"]["official_to_nflverse_identity_min"] == 0.995
    assert CONTRACT["unchanged_v1_v2_gates"]["normal_row_practice_status_agreement_min"] == 0.985
    assert CONTRACT["fallback_rule"]["fallback_fully_qualified_rate_required"] == 1.0
    assert CONTRACT["fallback_rule"]["fallback_date_modified_by_t120_rate_required"] == 1.0
    assert CONTRACT["fallback_rule"]["fallback_official_source_by_t120_rate_required"] == 1.0
    assert CONTRACT["firewall"]["game_outcomes_allowed"] is False
    assert CONTRACT["firewall"]["completed_2026_outcomes_allowed"] is False


def test_v3_pre_execution_repair_did_not_observe_v3_source_metrics() -> None:
    history = CONTRACT["v3_execution_history"]
    assert history["first_ci_attempt_reached_live_source_audit"] is False
    assert history["v3_source_metrics_observed_before_repair"] is False
    assert history["numeric_threshold_relaxation"] is False


def test_all_preregistered_defective_weeks_have_timestamped_matchup_evidence() -> None:
    defects = {(item["season"], item["nfl_week"]) for item in CONTRACT["known_archive_defects_fixed_before_v3_execution"]}
    evidence = {tuple(map(int, key.split("-"))) for key in CONTRACT["registered_matchup_evidence"]}
    assert defects == evidence
    for season, week in defects:
        rows = CONTRACT["registered_matchup_evidence"][f"{season}-{week}"]
        assert rows
        assert all(row["published_at_utc"].endswith("Z") for row in rows)


def test_fallback_qualifies_only_timestamp_and_official_source_safe_row(monkeypatch) -> None:
    monkeypatch.setattr(v3, "_ORIGINAL_BUILD", lambda *args, **kwargs: _canonical_row())
    monkeypatch.setattr(v3, "_DEFECTIVE", {(2023, 20)})
    v3._FALLBACK_EVIDENCE.clear()
    v3._FALLBACK_EVIDENCE[(2023, 20)] = _week20_evidence()
    out = v3._build_season_v3(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), season=2023)
    row = out.iloc[0]
    assert bool(row.fallback_archive_defect)
    assert bool(row.fallback_official_source_presence)
    assert bool(row.fallback_official_source_by_t120)
    assert bool(row.fully_qualified_practice_state)
    assert row.canonical_practice_state == "full"
    assert not bool(row.independent_practice_crosscheck)
    assert not bool(row.practice_status_agrees)
    assert row.identity_match_method == "intrinsic_gsis_archive_defect_fallback"


def test_fallback_late_row_remains_in_denominator_and_unqualified(monkeypatch) -> None:
    monkeypatch.setattr(v3, "_ORIGINAL_BUILD", lambda *args, **kwargs: _canonical_row(timestamp="2024-01-20T22:00:00Z"))
    monkeypatch.setattr(v3, "_DEFECTIVE", {(2023, 20)})
    v3._FALLBACK_EVIDENCE.clear()
    v3._FALLBACK_EVIDENCE[(2023, 20)] = _week20_evidence()
    out = v3._build_season_v3(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), season=2023)
    row = out.iloc[0]
    assert bool(row.fallback_archive_defect)
    assert not bool(row.fully_qualified_practice_state)
    assert row.canonical_practice_state == "unknown"
    assert v3._FALLBACK_EVIDENCE[(2023, -1)]["fallback_rows"] == 1
    assert v3._FALLBACK_EVIDENCE[(2023, -1)]["fallback_unqualified_rows"] == 1
    assert v3._FALLBACK_EVIDENCE[(2023, -1)]["fallback_fully_qualified_rate"] == 0.0


def test_fallback_official_source_after_t120_fails_row_closed(monkeypatch) -> None:
    monkeypatch.setattr(v3, "_ORIGINAL_BUILD", lambda *args, **kwargs: _canonical_row())
    monkeypatch.setattr(v3, "_DEFECTIVE", {(2023, 20)})
    v3._FALLBACK_EVIDENCE.clear()
    v3._FALLBACK_EVIDENCE[(2023, 20)] = _week20_evidence(published_at="2024-01-20T22:00:00Z")
    out = v3._build_season_v3(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), season=2023)
    row = out.iloc[0]
    assert not bool(row.fallback_official_source_by_t120)
    assert not bool(row.fully_qualified_practice_state)
    assert row.canonical_practice_state == "unknown"
    assert "fallback_official_source_not_by_t120" in row.unresolved_reason


def test_unregistered_zero_row_archive_defect_stays_fail_closed() -> None:
    assert (2022, 20) not in v3._DEFECTIVE
    assert (2024, 21) not in v3._DEFECTIVE
