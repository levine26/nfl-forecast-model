from __future__ import annotations

import pandas as pd
import pytest

from research.run_availability_harmonization_repaired_v1 import (
    collapse_exact_official_duplicates,
    reverse_identity_audit,
)


def _official_row(*, player: str = "Brock Wright", practice: str = "Full Participation in Practice") -> dict:
    return {
        "season": 2022,
        "week": 9,
        "team": "DET",
        "external_player": player,
        "external_position": "TE",
        "external_injury": "Concussion",
        "external_practice_status": practice,
        "external_game_status": "Questionable",
        "external_source": "nfl_com_official_injury_page",
        "source_url": "https://www.nfl.com/injuries/league/2022/reg9",
    }


def _nflverse_rows(*, include_date_modified: bool = True, season: int = 2022) -> pd.DataFrame:
    row = {
        "season": season,
        "week": 9,
        "team": "DET",
        "gsis_id": "00-0035869",
        "position": "TE",
        "full_name": "Brock Wright",
        "first_name": "Brock",
        "last_name": "Wright",
        "practice_status": "Full Participation in Practice",
        "report_status": "Questionable",
    }
    if include_date_modified:
        row["date_modified"] = "2022-11-04 16:00:00"
    return pd.DataFrame([row])


def test_identical_official_html_duplicate_collapses_without_changing_semantics() -> None:
    frame = pd.DataFrame([_official_row(), _official_row()])
    deduped, duplicates = collapse_exact_official_duplicates(frame)
    assert len(frame) == 2
    assert len(deduped) == 1
    assert len(duplicates) == 2
    assert deduped.iloc[0].external_player == "Brock Wright"


def test_conflicting_duplicate_is_not_collapsed() -> None:
    frame = pd.DataFrame([
        _official_row(practice="Full Participation in Practice"),
        _official_row(practice="Limited Participation in Practice"),
    ])
    deduped, duplicates = collapse_exact_official_duplicates(frame)
    assert len(deduped) == 2
    assert duplicates.empty


def test_reverse_identity_audit_accounts_for_every_distinct_official_row() -> None:
    metrics, unresolved = reverse_identity_audit(
        pd.DataFrame([_official_row()]), _nflverse_rows(), season=2022
    )
    assert metrics["official_distinct_rows"] == 1
    assert metrics["official_unique_stable_identity_rows"] == 1
    assert metrics["official_unresolved_identity_rows"] == 0
    assert metrics["official_identity_resolution_rate"] == 1.0
    assert unresolved.empty


def test_reverse_identity_audit_surfaces_official_row_missing_from_nflverse() -> None:
    official = pd.DataFrame([_official_row(), _official_row(player="Ghost Player")])
    metrics, unresolved = reverse_identity_audit(official, _nflverse_rows(), season=2022)
    assert metrics["official_distinct_rows"] == 2
    assert metrics["official_unique_stable_identity_rows"] == 1
    assert metrics["official_unresolved_identity_rows"] == 1
    assert metrics["official_identity_resolution_rate"] == 0.5
    assert unresolved.iloc[0].external_player == "Ghost Player"
    assert unresolved.iloc[0].identity_match_state == "unmatched"


def test_reverse_identity_2025_does_not_require_legacy_date_modified_field() -> None:
    official = pd.DataFrame([_official_row()]).assign(season=2025)
    nflverse = _nflverse_rows(include_date_modified=False, season=2025)
    metrics, unresolved = reverse_identity_audit(official, nflverse, season=2025)
    assert metrics["official_identity_resolution_rate"] == 1.0
    assert unresolved.empty


def test_reverse_identity_still_requires_stable_identity_fields() -> None:
    official = pd.DataFrame([_official_row()])
    bad = _nflverse_rows().drop(columns=["gsis_id"])
    with pytest.raises(ValueError, match="identity audit missing fields"):
        reverse_identity_audit(official, bad, season=2022)


def test_exact_duplicate_contract_requires_all_semantic_fields() -> None:
    incomplete = pd.DataFrame([{"season": 2022, "week": 9, "team": "DET"}])
    with pytest.raises(ValueError, match="duplicate-reconciliation fields"):
        collapse_exact_official_duplicates(incomplete)
