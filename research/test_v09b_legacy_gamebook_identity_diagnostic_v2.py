from __future__ import annotations

import polars as pl

from research.v09b_legacy_gamebook_identity_diagnostic_v2 import (
    build_same_week_team_jersey_index,
)


def _row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "season": 2012,
        "game_type": "REG",
        "week": 1,
        "team": "BLT",
        "gsis_id": "00-0023456",
        "jersey_number": 31,
        "first_name": "Antonio",
        "football_name": "Antonio",
        "last_name": "Cromartie",
        "status": "ACT",
        "status_description_abbr": "ACT",
        "status_short_description": "Active",
    }
    row.update(overrides)
    return row


def test_transaction_status_variants_collapse_to_one_same_jersey_candidate() -> None:
    frame = pl.DataFrame([
        _row(status="ACT"),
        _row(status="RES"),
    ])
    result = build_same_week_team_jersey_index(season=2012, frame=frame)
    assert result["source_identity_conflicts"] == 0
    assert result["index"][(1, "BAL", "31")] == {"00-0023456"}


def test_multiple_distinct_gsis_ids_on_same_week_team_jersey_remain_visible() -> None:
    frame = pl.DataFrame([
        _row(gsis_id="00-0023456"),
        _row(gsis_id="00-0099999", first_name="Other", football_name="Other", last_name="Player"),
    ])
    result = build_same_week_team_jersey_index(season=2012, frame=frame)
    assert result["source_identity_conflicts"] == 0
    assert result["index"][(1, "BAL", "31")] == {"00-0023456", "00-0099999"}


def test_inconsistent_identity_signature_for_same_gsis_is_excluded_as_conflict() -> None:
    frame = pl.DataFrame([
        _row(),
        _row(jersey_number=32),
    ])
    result = build_same_week_team_jersey_index(season=2012, frame=frame)
    assert result["source_identity_conflicts"] == 1
    assert not result["index"]


def test_postseason_rows_are_not_identity_candidates() -> None:
    frame = pl.DataFrame([
        _row(),
        _row(game_type="POST", gsis_id="00-0099999"),
    ])
    result = build_same_week_team_jersey_index(season=2012, frame=frame)
    assert result["source_rows_selected"] == 1
    assert result["index"][(1, "BAL", "31")] == {"00-0023456"}


def test_missing_gsis_rows_are_counted_but_never_candidates() -> None:
    frame = pl.DataFrame([
        _row(gsis_id=None),
        _row(gsis_id="00-0023456"),
    ])
    result = build_same_week_team_jersey_index(season=2012, frame=frame)
    assert result["missing_gsis_rows"] == 1
    assert result["index"][(1, "BAL", "31")] == {"00-0023456"}
