from __future__ import annotations

import polars as pl

from research.v09b_legacy_gamebook_identity_audit_v1 import (
    build_identity_index,
    compact_name,
    normalize_team,
    roster_display_keys,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season": 2012,
        "game_type": "REG",
        "week": 1,
        "team": "ARZ",
        "gsis_id": "00-0023456",
        "jersey_number": 31,
        "first_name": "Antonio",
        "football_name": "Antonio",
        "last_name": "Cromartie",
        # Forbidden membership/transaction field deliberately present in the frame.
        "status": "ACT",
    }
    row.update(overrides)
    return row


def test_compact_gamebook_name_and_legacy_team_aliases() -> None:
    assert compact_name("A.Cromartie") == "ACROMARTIE"
    assert compact_name("D’Brickashaw-Ferguson") == "DBRICKASHAWFERGUSON"
    assert normalize_team("ARZ") == "ARI"
    assert normalize_team("BLT") == "BAL"
    assert normalize_team("CLV") == "CLE"
    assert normalize_team("HST") == "HOU"
    assert normalize_team("SL") == "LA"


def test_roster_display_keys_use_first_initial_plus_last_name() -> None:
    keys = roster_display_keys(
        first_name="Antonio",
        football_name="Antonio",
        last_name="Cromartie",
    )
    assert keys == {"ACROMARTIE"}


def test_transaction_status_variants_do_not_change_identity_index() -> None:
    frame = pl.DataFrame(
        [
            _row(status="ACT"),
            _row(status="DEV"),
        ]
    )
    result = build_identity_index(season=2012, frame=frame)
    index = result["index"]
    assert result["source_rows_selected"] == 2
    assert result["source_identity_conflicts"] == 0
    assert result["collapsed_player_team_week_gsis_keys"] == 1
    assert index[(1, "ARI", "31", "ACROMARTIE")] == {"00-0023456"}


def test_inconsistent_identity_signature_for_same_gsis_is_hard_conflict() -> None:
    frame = pl.DataFrame(
        [
            _row(),
            _row(jersey_number=32),
        ]
    )
    result = build_identity_index(season=2012, frame=frame)
    assert result["source_identity_conflicts"] == 1
    assert result["collapsed_player_team_week_gsis_keys"] == 0
    assert not result["index"]


def test_two_distinct_gsis_ids_with_same_exact_key_remain_ambiguous() -> None:
    frame = pl.DataFrame(
        [
            _row(gsis_id="00-0023456"),
            _row(gsis_id="00-0099999"),
        ]
    )
    result = build_identity_index(season=2012, frame=frame)
    assert result["source_identity_conflicts"] == 0
    assert result["index"][(1, "ARI", "31", "ACROMARTIE")] == {
        "00-0023456",
        "00-0099999",
    }


def test_non_regular_rows_are_excluded_before_resolution() -> None:
    frame = pl.DataFrame(
        [
            _row(game_type="REG"),
            _row(game_type="POST", gsis_id="00-0088888"),
        ]
    )
    result = build_identity_index(season=2012, frame=frame)
    assert result["source_rows_selected"] == 1
    assert result["index"][(1, "ARI", "31", "ACROMARTIE")] == {"00-0023456"}
