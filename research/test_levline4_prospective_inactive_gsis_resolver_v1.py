from __future__ import annotations

import hashlib
import json
from pathlib import Path

import polars as pl
import pytest

from research.levline4_prospective_inactive_gsis_resolver_v1 import (
    SOURCE_FIELDS,
    build_identity_index,
    load_contract,
    normalize_name,
    resolve_observation,
    resolve_observations,
)

RAW_SHA = "a" * 64


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2026, 2026, 2026, 2026],
            "game_type": ["REG", "REG", "REG", "REG"],
            "week": [2, 2, 2, 2],
            "team": ["ARI", "ARI", "ARI", "SEA"],
            "gsis_id": ["00-1", "00-2", "00-3", "00-4"],
            "jersey_number": ["1", "2", "3", "4"],
            "first_name": ["Dee", "John", "John", "Other"],
            "football_name": ["Dee", "Johnny", "John", "Other"],
            "last_name": ["Example Jr.", "Smith", "Smith", "Player"],
        }
    ).select(list(SOURCE_FIELDS))


def _row(name: str = "Dee Example Jr.", *, week: int = 2, team: str = "ARI") -> dict:
    return {
        "observation_id": f"obs-{week}-{team}-{name}",
        "week": week,
        "team": team,
        "player_name_rendered": name,
        "source_known_by_utc": "2026-09-16T13:00:00Z",
        "raw_evidence_sha256": RAW_SHA,
    }


def test_normalization_is_fixed_and_suffix_bounded() -> None:
    assert normalize_name("Dee Example Jr.") == "dee example"
    assert normalize_name("DEE—EXAMPLE JR") == "dee example"
    assert normalize_name("O’Connell") == "o connell"
    assert normalize_name("Name III Jr") == "name iii"


def test_exact_unique_resolution_uses_only_week_team_and_name() -> None:
    idx = build_identity_index(_frame())
    out = resolve_observation(_row(), identity_index=idx)
    assert out["resolution_state"] == "RESOLVED_EXACT_UNIQUE"
    assert out["resolved_gsis_id"] == "00-1"
    assert out["position_used"] is False
    assert out["jersey_number_used"] is False
    assert out["status_used"] is False
    assert out["fuzzy_matching_used"] is False
    assert out["manual_override_used"] is False
    assert out["player_identity_to_gsis_qualified"] is False
    assert out["player_value_join_authorized"] is False


def test_collision_is_ambiguous_not_tiebroken() -> None:
    idx = build_identity_index(_frame())
    out = resolve_observation(_row("John Smith"), identity_index=idx)
    assert out["resolution_state"] == "AMBIGUOUS"
    assert out["resolved_gsis_id"] is None
    assert out["candidate_gsis_ids"] == ["00-2", "00-3"]


def test_zero_match_remains_unresolved() -> None:
    idx = build_identity_index(_frame())
    out = resolve_observation(_row("Nobody Here"), identity_index=idx)
    assert out["resolution_state"] == "UNRESOLVED"
    assert out["candidate_gsis_ids"] == []


def test_week1_and_pre_source_observations_fail_closed() -> None:
    idx = build_identity_index(_frame())
    with pytest.raises(ValueError, match="Week 1"):
        resolve_observation(_row(week=1), identity_index=idx)
    row = _row()
    row["source_known_by_utc"] = "2026-09-16T12:35:56Z"
    with pytest.raises(ValueError, match="predates"):
        resolve_observation(row, identity_index=idx)


def test_projection_hash_is_mandatory(tmp_path: Path) -> None:
    projection = tmp_path / "projection.parquet"
    _frame().write_parquet(projection)
    digest = hashlib.sha256(projection.read_bytes()).hexdigest()
    rows, receipt = resolve_observations(
        [_row()], projection_path=projection, expected_projection_sha256=digest
    )
    assert rows[0]["resolved_gsis_id"] == "00-1"
    assert receipt["real_execution_is_self_qualifying"] is False
    assert receipt["player_identity_to_gsis_qualified"] is False
    assert receipt["production_authorized"] is False

    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        resolve_observations(
            [_row()], projection_path=projection, expected_projection_sha256="0" * 64
        )


def test_source_schema_drift_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="fields"):
        build_identity_index(_frame().drop("football_name"))


def test_contract_freezes_no_status_and_no_self_qualification(tmp_path: Path) -> None:
    contract = {
        "contract_id": "LEVLINE-2026-PROSPECTIVE-INACTIVE-GSIS-RESOLVER-V1",
        "dependency": {
            "source_projection_sha256": "fc993e0543950222cd20e0c29e457980da572d100bebff6a5d4bf5f7b72b051f",
            "source_fields": list(SOURCE_FIELDS),
            "status_fields_available_to_resolver": False,
        },
    }
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    load_contract(path)
    contract["dependency"]["status_fields_available_to_resolver"] = True
    path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(ValueError, match="status fields"):
        load_contract(path)
