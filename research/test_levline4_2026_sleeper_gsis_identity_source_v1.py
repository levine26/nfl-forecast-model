from __future__ import annotations

import json
from pathlib import Path

from research import levline4_2026_sleeper_gsis_identity_source_v1 as mod


class FakeResponse:
    def __init__(self, payload: bytes, status_code: int = 200):
        self.content = payload
        self.status_code = status_code
        self.headers = {"Content-Type": "application/json"}


def player(i: int, *, gsis: str | None = None, name: str | None = None) -> dict:
    return {
        "player_id": str(i),
        "gsis_id": gsis if gsis is not None else f"00-{i:07d}",
        "full_name": name or f"Player {i}",
        "first_name": "Player",
        "last_name": str(i),
        "position": "WR",
        "number": i % 100,
        "birth_date": "2000-01-01",
        "espn_id": 100000 + i,
        "sportradar_id": f"sr-{i}",
        "team": "ARI",
        "active": True,
        "status": "Active",
        "injury_status": "Questionable",
        "practice_participation": "Limited",
        "depth_chart_order": 1,
    }


def test_contract_is_source_capture_only_and_excludes_state_fields():
    c = mod.load_contract()
    assert c["source"]["endpoint"] == "https://api.sleeper.app/v1/players/nfl"
    assert c["source"]["single_first_capture_is_canonical"] is True
    assert c["source"]["later_same_version_capture_may_replace_first_capture"] is False
    assert c["projection"]["source_team_or_status_used_for_identity"] is False
    forbidden = set(c["projection"]["forbidden_fields"])
    assert {"team", "active", "status", "injury_status", "practice_participation", "depth_chart_order"}.issubset(forbidden)
    assert c["authority_if_capture_gate_passes"]["player_identity_to_gsis_qualified"] is False
    assert c["authority_if_capture_gate_passes"]["production_authorized"] is False
    assert c["governance"]["completed_2026_outcomes_used_for_design_or_selection"] == 0


def test_projection_physically_excludes_team_status_injury_practice_and_depth_fields():
    c = mod.load_contract()
    payload = {"123": player(123)}
    rows, d = mod.project_identity_catalog(json.dumps(payload).encode(), c)
    assert len(rows) == 1
    row = rows[0]
    assert row["sleeper_player_id"] == "123"
    assert row["gsis_id"] == "00-0000123"
    assert tuple(row) == tuple(c["projection"]["allowed_fields"])
    assert not set(c["projection"]["forbidden_fields"]).intersection(row)
    assert d["projection_contains_forbidden_fields"] is False


def test_missing_and_noncanonical_gsis_rows_are_excluded_and_counted():
    c = mod.load_contract()
    payload = {
        "1": player(1, gsis=""),
        "2": player(2, gsis="12345"),
        "3": player(3, gsis="00-0000003"),
    }
    rows, d = mod.project_identity_catalog(json.dumps(payload).encode(), c)
    assert [r["sleeper_player_id"] for r in rows] == ["3"]
    assert d["missing_gsis_row_count"] == 1
    assert d["invalid_gsis_row_count"] == 1
    assert d["projection_row_count"] == 1


def test_conflicting_names_for_same_gsis_are_detected():
    c = mod.load_contract()
    payload = {
        "1": player(1, gsis="00-0000001", name="Alpha One"),
        "2": player(2, gsis="00-0000001", name="Beta Two"),
    }
    rows, d = mod.project_identity_catalog(json.dumps(payload).encode(), c)
    assert len(rows) == 2
    assert d["duplicate_gsis_group_count"] == 1
    assert d["duplicate_gsis_conflicting_name_count"] == 1


def test_source_sanity_gate_passes_without_granting_identity_authority(tmp_path: Path):
    payload = {str(i): player(i) for i in range(1, 5001)}
    raw = json.dumps(payload, sort_keys=True).encode()

    def fake_get(url: str, **kwargs):
        return FakeResponse(raw)

    receipt = mod.run_capture(tmp_path / "out", get=fake_get)
    assert receipt["status"] == "PASS"
    assert receipt["total_player_objects"] == 5000
    assert receipt["projection_row_count"] == 5000
    assert receipt["capture_gate_pass"] is True
    assert receipt["sleeper_external_identity_source_capture_qualified"] is True
    assert receipt["statistical_independence_of_underlying_provider_data_proven"] is False
    assert receipt["player_identity_to_gsis_qualified"] is False
    assert receipt["availability_state_authorized"] is False
    assert receipt["forecast_probability_effect_authorized"] is False
    assert receipt["production_authorized"] is False
    assert receipt["completed_2026_outcomes_used_for_design_or_selection"] == 0
    line = json.loads((tmp_path / "out" / "identity_projection.jsonl").read_text().splitlines()[0])
    assert not {"team", "active", "status", "injury_status"}.intersection(line)


def test_conflicting_gsis_identity_fails_capture_gate(tmp_path: Path):
    payload = {str(i): player(i) for i in range(1, 5001)}
    payload["5001"] = player(5001, gsis="00-0000001", name="Different Person")
    raw = json.dumps(payload, sort_keys=True).encode()

    def fake_get(url: str, **kwargs):
        return FakeResponse(raw)

    receipt = mod.run_capture(tmp_path / "out", get=fake_get)
    assert receipt["status"] == "FAIL"
    assert receipt["duplicate_gsis_conflicting_name_count"] == 1
    assert receipt["sleeper_external_identity_source_capture_qualified"] is False
    assert receipt["player_identity_to_gsis_qualified"] is False


def test_non_200_raw_body_is_preserved_before_failure(tmp_path: Path):
    raw = b'{"error":"temporary"}'

    def fake_get(url: str, **kwargs):
        return FakeResponse(raw, status_code=503)

    receipt = mod.run_capture(tmp_path / "out", get=fake_get)
    assert receipt["status"] == "FAIL"
    assert receipt["http_status"] == 503
    assert receipt["raw_source_bytes"] == len(raw)
    assert (tmp_path / "out" / f"raw-{receipt['raw_source_sha256']}.json").read_bytes() == raw
    assert receipt["projection_row_count"] == 0
    assert receipt["player_identity_to_gsis_qualified"] is False
    assert receipt["production_authorized"] is False
