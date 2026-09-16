from __future__ import annotations

import hashlib
import io
import json

import polars as pl
import pytest

from research.levline4_2026_identity_source_v1 import (
    ALLOWED_FIELDS,
    capture,
    load_contract,
    project_status_free_identity,
    verify_raw_source,
)


def _frame() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "season": [2026, 2026, 2026, 2025],
            "game_type": ["REG", "REG", "PRE", "REG"],
            "week": [2, 2, 3, 18],
            "team": ["ARI", "SEA", "ARI", "ARI"],
            "gsis_id": ["00-0000001", "00-0000002", "00-0000003", "00-0000004"],
            "jersey_number": ["1", "2", "3", "4"],
            "first_name": ["Alpha", "Beta", "Gamma", "Delta"],
            "football_name": ["Alpha", "Beta", "Gamma", "Delta"],
            "last_name": ["One", "Two", "Three", "Four"],
            "status": ["ACT", "INA", "ACT", "ACT"],
            "status_description_abbr": ["A01", "I01", "A01", "A01"],
            "status_short_description": ["Active", "Inactive", "Active", "Active"],
        }
    )


def _parquet_bytes(frame: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    frame.write_parquet(buf)
    return buf.getvalue()


def _contract(raw: bytes) -> dict:
    return {
        "contract_id": "LEVLINE-2026-STATUS-FREE-IDENTITY-SOURCE-CAPTURE-V1",
        "season": 2026,
        "source": {
            "asset_id": 567939096,
            "expected_sha256": hashlib.sha256(raw).hexdigest(),
            "expected_size_bytes": len(raw),
        },
        "prospective_time_firewall": {
            "source_known_by_utc": "2026-09-16T12:35:57Z",
        },
        "identity_projection": {
            "allowed_fields": list(ALLOWED_FIELDS),
            "forbidden_fields": [
                "status",
                "status_description_abbr",
                "status_short_description",
            ],
        },
    }


def test_projection_selects_allowlist_before_row_use_and_filters_reg_2026() -> None:
    projected = project_status_free_identity(_frame())
    assert tuple(projected.columns) == ALLOWED_FIELDS
    assert projected.height == 2
    assert set(projected["team"].to_list()) == {"ARI", "SEA"}
    assert "status" not in projected.columns
    assert "status_description_abbr" not in projected.columns
    assert "status_short_description" not in projected.columns


def test_missing_identity_field_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="missing required identity fields"):
        project_status_free_identity(_frame().drop("football_name"))


def test_raw_source_sha_and_size_are_exact_gates() -> None:
    raw = _parquet_bytes(_frame())
    contract = _contract(raw)
    verify_raw_source(raw, contract)

    bad = dict(contract)
    bad["source"] = dict(contract["source"])
    bad["source"]["expected_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="sha256 mismatch"):
        verify_raw_source(raw, bad)

    bad = dict(contract)
    bad["source"] = dict(contract["source"])
    bad["source"]["expected_size_bytes"] = len(raw) + 1
    with pytest.raises(RuntimeError, match="byte-size mismatch"):
        verify_raw_source(raw, bad)


def test_contract_refuses_status_or_allowlist_drift(tmp_path) -> None:
    raw = _parquet_bytes(_frame())
    contract = _contract(raw)
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    load_contract(path)

    contract["identity_projection"]["allowed_fields"].append("status")
    path.write_text(json.dumps(contract), encoding="utf-8")
    with pytest.raises(ValueError, match="allowed_fields drifted"):
        load_contract(path)


def test_capture_grants_source_only_and_blocks_week1_retro_join(tmp_path) -> None:
    raw = _parquet_bytes(_frame())
    source = tmp_path / "source.parquet"
    source.write_bytes(raw)
    contract = _contract(raw)
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    out = capture(
        raw_source_path=source,
        contract_path=contract_path,
        output_root=tmp_path / "out",
    )
    assert out["status"] == "PASS"
    assert out["exact_2026_status_free_identity_source_captured"] is True
    assert out["projection_contains_status_fields"] is False
    assert out["status_fields_selected"] is False
    assert out["status_fields_read"] is False
    assert out["week_1_retroactive_identity_join_authorized"] is False
    assert out["player_identity_resolution_qualified"] is False
    assert out["game_day_membership_qualified"] is False
    assert out["availability_state_qualified"] is False
    assert out["player_value_join_authorized"] is False
    assert out["forecast_probability_effect_authorized"] is False
    assert out["model_fit_authorized"] is False
    assert out["production_authorized"] is False
    assert out["identity_resolution_performed"] is False
    assert out["completed_2026_outcomes_used"] == 0


def test_empty_reg_2026_projection_is_not_silently_accepted(tmp_path) -> None:
    frame = _frame().filter(pl.col("season") == 2025)
    raw = _parquet_bytes(frame)
    source = tmp_path / "source.parquet"
    source.write_bytes(raw)
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(_contract(raw)), encoding="utf-8")
    with pytest.raises(RuntimeError, match="projection is empty"):
        capture(
            raw_source_path=source,
            contract_path=contract_path,
            output_root=tmp_path / "out",
        )
