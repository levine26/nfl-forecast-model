from __future__ import annotations

import polars as pl

from research import levline4_2026_official_club_nflverse_metadata_consistency_v1 as m
from research.levline4_prospective_inactive_gsis_resolver_v1 import SOURCE_FIELDS


def _frame(rows: list[dict]) -> pl.DataFrame:
    data = {field: [row.get(field) for row in rows] for field in SOURCE_FIELDS}
    return pl.DataFrame(data)


def _contract_for_small_fixture() -> dict:
    c = m.load_contract()
    c = {**c, "qualification_gate": dict(c["qualification_gate"])}
    c["qualification_gate"].update(
        {
            "official_row_count_must_equal": 2,
            "official_team_count_must_equal": 2,
            "exact_unique_resolution_rate_min": 1.0,
            "jersey_comparable_fraction_of_exact_unique_min": 1.0,
        }
    )
    return c


def test_normalize_jersey_is_deterministic_and_missing_stays_missing():
    assert m.normalize_jersey(None) == (None, False)
    assert m.normalize_jersey(0) == ("0", False)
    assert m.normalize_jersey("07") == ("7", False)
    assert m.normalize_jersey(97.0) == ("97", False)
    assert m.normalize_jersey("7.5") == (None, True)
    assert m.normalize_jersey("QB") == (None, True)
    assert m.normalize_jersey(100) == (None, True)


def test_exact_name_team_resolution_and_jersey_audit_pass_small_fixture():
    identity = _frame(
        [
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "ARI",
                "gsis_id": "00-0000001",
                "jersey_number": 7,
                "first_name": "A.J.",
                "football_name": "AJ",
                "last_name": "Example",
            },
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "ATL",
                "gsis_id": "00-0000002",
                "jersey_number": 22,
                "first_name": "John",
                "football_name": "Johnny",
                "last_name": "Sample",
            },
        ]
    )
    official = [
        {"team": "ARI", "visible_name": "A.J. Example Jr.", "jersey_number": "7", "position": "WR", "profile_path": "/team/players-roster/a-j-example/"},
        {"team": "ATL", "visible_name": "Johnny Sample", "jersey_number": "22", "position": "CB", "profile_path": "/team/players-roster/johnny-sample/"},
    ]
    rows, summary, dup = m.evaluate(official, identity, _contract_for_small_fixture())
    assert [row["resolution_state"] for row in rows] == ["RESOLVED_EXACT_UNIQUE", "RESOLVED_EXACT_UNIQUE"]
    assert all(row["jersey_used_for_resolution"] is False for row in rows)
    assert all(row["position_comparison_performed"] is False for row in rows)
    assert summary["jersey_agreement_rate"] == 1.0
    assert summary["gate_pass"] is True
    assert dup == []


def test_jersey_disagreement_does_not_change_exact_name_resolution():
    identity = _frame(
        [
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "ARI",
                "gsis_id": "00-0000001",
                "jersey_number": 8,
                "first_name": "Alice",
                "football_name": "Alice",
                "last_name": "Example",
            },
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "ATL",
                "gsis_id": "00-0000002",
                "jersey_number": 22,
                "first_name": "John",
                "football_name": "Johnny",
                "last_name": "Sample",
            },
        ]
    )
    official = [
        {"team": "ARI", "visible_name": "Alice Example", "jersey_number": "7", "position": "WR", "profile_path": "/a/"},
        {"team": "ATL", "visible_name": "Johnny Sample", "jersey_number": "22", "position": "CB", "profile_path": "/b/"},
    ]
    rows, summary, _ = m.evaluate(official, identity, _contract_for_small_fixture())
    assert rows[0]["resolution_state"] == "RESOLVED_EXACT_UNIQUE"
    assert rows[0]["jersey_agrees"] is False
    assert summary["jersey_disagreement_count"] == 1
    assert summary["gate_pass"] is False


def test_ambiguous_name_never_uses_jersey_as_tiebreaker():
    identity = _frame(
        [
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "ARI",
                "gsis_id": "00-0000001",
                "jersey_number": 7,
                "first_name": "Chris",
                "football_name": "Chris",
                "last_name": "Smith",
            },
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "ARI",
                "gsis_id": "00-0000002",
                "jersey_number": 8,
                "first_name": "Chris",
                "football_name": "Chris",
                "last_name": "Smith",
            },
        ]
    )
    official = [{"team": "ARI", "visible_name": "Chris Smith", "jersey_number": "7", "position": "WR", "profile_path": "/x/"}]
    c = _contract_for_small_fixture()
    c["qualification_gate"]["official_row_count_must_equal"] = 1
    c["qualification_gate"]["official_team_count_must_equal"] = 1
    rows, summary, _ = m.evaluate(official, identity, c)
    assert rows[0]["resolution_state"] == "AMBIGUOUS"
    assert rows[0]["resolved_candidate_gsis_id"] is None
    assert rows[0]["jersey_used_for_resolution"] is False
    assert summary["ambiguous_count"] == 1
    assert summary["gate_pass"] is False


def test_contract_keeps_strong_authority_closed():
    c = m.load_contract()
    assert c["frozen_sources"]["statistical_or_upstream_data_independence_proven"] is False
    assert c["post_resolution_metadata_audit"]["position_comparison_performed"] is False
    assert c["qualification_gate"]["post_result_threshold_relaxation_allowed"] is False
    assert c["qualification_gate"]["unresolved_rows_may_be_repaired_after_observation"] is False
    assert c["authority_if_gate_passes"]["player_identity_to_gsis_qualified"] is False
    assert c["authority_if_gate_passes"]["forecast_probability_effect_authorized"] is False
    assert c["authority_if_gate_passes"]["production_authorized"] is False
