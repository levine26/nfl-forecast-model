from __future__ import annotations

import polars as pl

from research.v09b_roster_universe_audit_v2 import (
    duplicate_shape_diagnostics,
    normalize_team_v2,
)


def test_observed_data_exchange_team_aliases_are_identity_only() -> None:
    assert normalize_team_v2("ARZ") == "ARI"
    assert normalize_team_v2("BLT") == "BAL"
    assert normalize_team_v2("CLV") == "CLE"
    assert normalize_team_v2("HST") == "HOU"
    assert normalize_team_v2("SL") == "LA"
    assert normalize_team_v2("JAC") == "JAX"
    assert normalize_team_v2("SD") == "LAC"
    assert normalize_team_v2("OAK") == "LV"
    assert normalize_team_v2("NE") == "NE"


def _frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "season": 2012,
                "game_type": "REG",
                "week": 1,
                "team": "ARZ",
                "gsis_id": "00-0000001",
                "status_description_abbr": "A01",
                "status_short_description": "Active",
                **row,
            }
            for row in rows
        ]
    )


def test_duplicate_diagnostics_distinguish_identical_from_conflicting_rows() -> None:
    frame = _frame(
        [
            {},
            {},
            {
                "gsis_id": "00-0000002",
                "status_description_abbr": "A01",
                "status_short_description": "Active",
            },
            {
                "gsis_id": "00-0000002",
                "status_description_abbr": "R01",
                "status_short_description": "Reserve/Injured",
            },
        ]
    )
    result = duplicate_shape_diagnostics(season=2012, frame=frame)
    assert result["legacy_team_alias_row_counts"] == {"ARZ->ARI": 4}
    assert result["duplicate_identity_keys_total"] == 2
    assert result["duplicate_identity_keys_single_status_variant"] == 1
    assert result["duplicate_identity_keys_conflicting_status_variants"] == 1
    assert result["exact_duplicate_normalized_excess_rows"] == 1
    variants = result["duplicate_identity_status_variant_examples"]["2012-W1-ARI-00-0000002"]
    assert {row["status_description_abbr"] for row in variants} == {"A01", "R01"}


def test_diagnostics_do_not_interpret_status_semantics() -> None:
    result = duplicate_shape_diagnostics(season=2012, frame=_frame([{}]))
    assert "eligible" not in result
    assert "active_label" not in result
    assert result["duplicate_identity_keys_total"] == 0
