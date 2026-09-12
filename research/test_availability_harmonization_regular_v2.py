from __future__ import annotations

import pandas as pd

from research.availability_harmonization_regular_v2 import (
    OFFICIAL_SEMANTIC_COLUMNS,
    StrictSeasonAudit,
    collapse_exact_official_duplicates,
    evaluate_strict_harmonization,
    filter_model_eligible_schedule,
    official_semantic_sha256,
    parse_date_modified_utc,
    remove_model_universe_exceptions,
)


EXCEPTIONS = [
    {
        "season": 2022,
        "week": 17,
        "teams": ["BUF", "CIN"],
    }
]


def _official_row(player: str, team: str = "BUF", week: int = 1) -> dict:
    return {
        "season": 2022,
        "week": week,
        "team": team,
        "external_player": player,
        "external_position": "WR",
        "external_injury": "ankle",
        "external_practice_status": "Limited Participation",
        "external_game_status": "Questionable",
        "external_source": "nfl_com_official_injury_page",
        "source_url": f"https://example.test/2022/reg{week}",
    }


def _audit(season: int, injury_hash: str, official_hash: str) -> StrictSeasonAudit:
    return StrictSeasonAudit(
        season=season,
        injury_source_sha256=injury_hash,
        full_asset_rows=100,
        model_eligible_rows=90,
        exception_rows_removed=0,
        official_pages_collected=18,
        official_rows=90,
        official_semantic_sha256=official_hash,
        stable_gsis_missing_rate=0.0,
        canonical_to_official_identity_rate=1.0,
        official_to_canonical_identity_rate=1.0,
        practice_status_agreement_rate=1.0,
        diagnostic_game_status_agreement_rate=1.0,
        known_by_t120_rate_among_identity_matched_rows=1.0,
        fully_qualified_practice_state_rate=1.0,
        date_modified_parse_rate=1.0 if season < 2025 else None,
        schedule_match_rate=1.0,
        non_exception_schedule_unmatched_rows=0,
        duplicate_canonical_identity_rows=0,
        identical_duplicate_rows_collapsed=0,
    )


def _contract(*, official_pinned: bool, schedule_pinned: bool) -> dict:
    injury_hashes = {str(season): f"inj-{season}" for season in (2022, 2023, 2024, 2025)}
    official_hashes = {
        str(season): (f"off-{season}" if official_pinned else None)
        for season in (2022, 2023, 2024, 2025)
    }
    return {
        "primary_state_source": {
            "expected_sha256": injury_hashes,
            "expected_full_asset_rows": {str(season): 100 for season in (2022, 2023, 2024, 2025)},
        },
        "independent_crosscheck": {
            "expected_semantic_bundle_sha256": official_hashes,
        },
        "schedule_source": {
            "expected_derived_subset_sha256": "sched" if schedule_pinned else None,
        },
        "frozen_qualification_gates": {
            "required_seasons_exact": [2022, 2023, 2024, 2025],
            "official_nfl_pages_required_per_season": 18,
            "stable_gsis_missing_rate_max": 0.0,
            "canonical_to_official_unique_identity_match_rate_min": 0.995,
            "official_to_canonical_identity_resolution_rate_min": 0.995,
            "practice_status_agreement_rate_min": 0.985,
            "diagnostic_game_status_agreement_rate_min": 0.985,
            "known_by_t120_rate_required_among_identity_matched_rows": 1.0,
            "fully_qualified_practice_state_rate_min": 0.99,
            "legacy_date_modified_parse_rate_min": 0.995,
            "schedule_match_rate_required_among_model_eligible_rows": 1.0,
            "non_exception_schedule_unmatched_rows_allowed": 0,
            "duplicate_canonical_identity_rows_allowed": 0,
        },
    }


def test_official_semantic_hash_is_order_invariant():
    frame = pd.DataFrame([_official_row("Alpha One"), _official_row("Beta Two")])
    reversed_frame = frame.iloc[::-1].reset_index(drop=True)
    assert official_semantic_sha256(frame) == official_semantic_sha256(reversed_frame)


def test_exact_official_duplicate_collapse_requires_complete_semantic_identity():
    row = _official_row("Alpha One")
    frame = pd.DataFrame([row, row, {**row, "external_game_status": "Out"}])
    deduped, collapsed = collapse_exact_official_duplicates(frame)
    assert collapsed == 1
    assert len(deduped) == 2
    assert list(deduped.columns) == OFFICIAL_SEMANTIC_COLUMNS


def test_cancelled_buf_cin_rows_are_explicit_exception_only():
    frame = pd.DataFrame(
        [
            {"season": 2022, "week": 17, "team": "BUF", "gsis_id": "1"},
            {"season": 2022, "week": 17, "team": "CIN", "gsis_id": "2"},
            {"season": 2022, "week": 17, "team": "NE", "gsis_id": "3"},
        ]
    )
    kept, removed = remove_model_universe_exceptions(frame, EXCEPTIONS)
    assert kept[["team", "gsis_id"]].to_dict("records") == [{"team": "NE", "gsis_id": "3"}]
    assert set(removed["team"]) == {"BUF", "CIN"}


def test_schedule_filter_removes_only_preregistered_cancelled_matchup():
    schedules = pd.DataFrame(
        [
            {
                "season": 2022,
                "week": 17,
                "game_id": "2022_17_BUF_CIN",
                "gameday": "2023-01-02",
                "gametime": "20:30",
                "home_team": "CIN",
                "away_team": "BUF",
                "game_type": "REG",
            },
            {
                "season": 2022,
                "week": 17,
                "game_id": "2022_17_MIA_NE",
                "gameday": "2023-01-01",
                "gametime": "13:00",
                "home_team": "NE",
                "away_team": "MIA",
                "game_type": "REG",
            },
            {
                "season": 2022,
                "week": 19,
                "game_id": "2022_19_WC",
                "gameday": "2023-01-15",
                "gametime": "13:00",
                "home_team": "BUF",
                "away_team": "MIA",
                "game_type": "WC",
            },
        ]
    )
    kept, removed = filter_model_eligible_schedule(schedules, EXCEPTIONS)
    assert kept["game_id"].tolist() == ["2022_17_MIA_NE"]
    assert removed["game_id"].tolist() == ["2022_17_BUF_CIN"]


def test_date_modified_naive_values_use_nflverse_timezone():
    parsed = parse_date_modified_utc(pd.Series(["2022-09-10 12:00:00", None]))
    assert str(parsed.iloc[0].tzinfo) == "UTC"
    assert parsed.iloc[0].hour == 16
    assert pd.isna(parsed.iloc[1])


def test_unpinned_strict_hashes_are_audit_only_not_authorization():
    contract = _contract(official_pinned=False, schedule_pinned=False)
    audits = [
        _audit(season, f"inj-{season}", f"off-{season}")
        for season in (2022, 2023, 2024, 2025)
    ]
    report = evaluate_strict_harmonization(
        audits,
        contract,
        schedule_sha256="sched",
        v09b_prereg_ok=True,
        qualified_2025_receipt_ok=True,
    )
    assert report["technical_status"] == "VERIFIED"
    assert report["research_classification"] == "AUDIT_ONLY_UNPINNED_STRICT_SOURCE_HASHES"
    assert report["hard_blockers"] == []
    assert len(report["pin_blockers"]) == 5
    assert report["v09b_execution_authorized"] is False
    assert report["probability_model_built"] is False


def test_all_frozen_gates_and_pins_authorize_research_execution_only():
    contract = _contract(official_pinned=True, schedule_pinned=True)
    audits = [
        _audit(season, f"inj-{season}", f"off-{season}")
        for season in (2022, 2023, 2024, 2025)
    ]
    report = evaluate_strict_harmonization(
        audits,
        contract,
        schedule_sha256="sched",
        v09b_prereg_ok=True,
        qualified_2025_receipt_ok=True,
    )
    assert report["research_classification"] == "QUALIFIED_REGULAR_SEASON_SOURCE_2022_2025"
    assert report["v09b_execution_authorized"] is True
    assert report["probability_feature_authorized"] is False
    assert report["production_dependency_authorized"] is False


def test_any_frozen_gate_failure_blocks_even_if_hashes_are_pinned():
    contract = _contract(official_pinned=True, schedule_pinned=True)
    audits = [
        _audit(season, f"inj-{season}", f"off-{season}")
        for season in (2022, 2023, 2024, 2025)
    ]
    audits[0] = StrictSeasonAudit(**{
        **audits[0].as_dict(),
        "practice_status_agreement_rate": 0.98,
    })
    report = evaluate_strict_harmonization(
        audits,
        contract,
        schedule_sha256="sched",
        v09b_prereg_ok=True,
        qualified_2025_receipt_ok=True,
    )
    assert report["technical_status"] == "BLOCKED"
    assert "practice-state agreement gate failed: 2022" in report["hard_blockers"]
    assert report["v09b_execution_authorized"] is False
