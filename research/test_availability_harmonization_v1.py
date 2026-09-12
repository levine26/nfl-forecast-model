from __future__ import annotations

import copy

import pandas as pd

from research.availability_harmonization_v1 import (
    EXPECTED_V09B,
    SeasonAudit,
    evaluate_harmonization,
    harmonize_season,
    normalize_practice_status,
    validate_v09b_preregistry,
)


def _injury_frame(season: int = 2022) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "season": season,
                "week": 1,
                "team": "BUF",
                "gsis_id": "00-0034857",
                "position": "QB",
                "full_name": "Example Player",
                "practice_primary_injury": "Ankle",
                "practice_secondary_injury": "",
                "practice_status": "Limited Participation in Practice",
                "report_primary_injury": "Ankle",
                "report_secondary_injury": "",
                "report_status": "Questionable",
            }
        ]
    )


def _schedule(season: int = 2022) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "season": season,
                "week": 1,
                "home_team": "LA",
                "away_team": "BUF",
                "gameday": f"{season}-09-08",
                "gametime": "20:20",
                "game_id": f"{season}_01_BUF_LA",
            }
        ]
    )


def _contract(*, pinned: bool) -> dict:
    return {
        "target_seasons": [2022],
        "source": {
            "expected_sha256": {"2022": "abc" if pinned else None},
            "expected_full_asset_rows": {"2022": 1},
        },
        "qualification_gates": {
            "stable_identity_missing_rate": 0.0,
            "duplicate_player_team_week_rows": 0,
            "schedule_join_missing_rate": 0.0,
            "known_by_t120_rate": 1.0,
            "practice_status_normalization_unknown_rate_max": 0.01,
        },
    }


def _receipt() -> dict:
    return {
        "research_source_qualified": True,
        "supports_2025_reconstruction": True,
        "probability_feature_authorized": False,
    }


def _audit(source_sha256: str = "abc") -> SeasonAudit:
    return SeasonAudit(
        season=2022,
        source_sha256=source_sha256,
        full_asset_rows=1,
        regular_rows=1,
        missing_id_rate=0.0,
        duplicate_player_team_week_rows=0,
        schedule_join_missing_rate=0.0,
        known_by_t120_rate=1.0,
        unknown_practice_status_rate=0.0,
    )


def test_practice_status_normalization_is_compact_and_fail_closed():
    assert normalize_practice_status("Full Participation in Practice") == "full"
    assert normalize_practice_status("Limited Participation in Practice") == "limited"
    assert normalize_practice_status("Did Not Participate In Practice") == "dnp"
    assert normalize_practice_status(None) == "unknown"
    assert normalize_practice_status("surprise vendor value") == "unknown"


def test_harmonizer_excludes_game_status_and_proves_t120_chronology():
    canonical, audit = harmonize_season(
        _injury_frame(),
        _schedule(),
        season=2022,
        source_sha256="abc",
    )
    assert list(canonical["practice_status_normalized"]) == ["limited"]
    assert list(canonical["listed_on_injury_report"]) == [True]
    assert list(canonical["known_by_t120"]) == [True]
    assert "report_status" not in canonical.columns
    assert "actual_snaps" not in canonical.columns
    assert audit.schedule_join_missing_rate == 0.0
    assert audit.known_by_t120_rate == 1.0


def test_duplicate_player_team_week_rows_fail_closed():
    injuries = pd.concat([_injury_frame(), _injury_frame()], ignore_index=True)
    try:
        harmonize_season(injuries, _schedule(), season=2022, source_sha256="abc")
    except ValueError as exc:
        assert "duplicate player-team-week" in str(exc)
    else:
        raise AssertionError("duplicate stable player-week rows must fail closed")


def test_unpinned_hashes_cannot_authorize_v09b():
    result = evaluate_harmonization(
        [_audit()],
        _contract(pinned=False),
        v09b_prereg_ok=True,
        qualified_2025_receipt=_receipt(),
    )
    assert result["technical_status"] == "VERIFIED"
    assert result["research_classification"] == "AUDIT_ONLY_UNPINNED_SOURCE_HASHES"
    assert result["v09b_execution_authorized"] is False
    assert result["probability_model_built"] is False


def test_pinned_hash_and_all_gates_can_qualify_research_only_contract():
    result = evaluate_harmonization(
        [_audit()],
        _contract(pinned=True),
        v09b_prereg_ok=True,
        qualified_2025_receipt=_receipt(),
    )
    assert result["research_classification"] == "QUALIFIED_RESEARCH_2022_2025"
    assert result["v09b_execution_authorized"] is True
    assert result["probability_feature_authorized"] is False
    assert result["production_dependency_authorized"] is False


def test_v09b_preregistration_drift_is_detected():
    target = {
        "experiment_id": "V09B-AVAILABILITY-001",
        **copy.deepcopy(EXPECTED_V09B),
        "prohibited_inputs": [
            "2026 outcomes",
            "actual current-game snaps",
            "final starter identity",
            "retrospective inactive status",
            "later injury designation",
            "postgame participation",
        ],
    }
    ok, reasons = validate_v09b_preregistry({"experiments": [target]})
    assert ok is True
    assert reasons == []

    target["model_family"] = "post-hoc rescue model"
    ok, reasons = validate_v09b_preregistry({"experiments": [target]})
    assert ok is False
    assert any("model_family" in reason for reason in reasons)
