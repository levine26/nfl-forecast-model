from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from research.point_in_time_store import (
    SCHEMA_VERSION,
    SnapshotValidationError,
    append_snapshot_jsonl,
    build_snapshot,
    target_timestamp,
    validate_snapshot,
)


def _snapshot(**overrides):
    kwargs = {
        "game_id": "2026_01_CHI_CAR",
        "kickoff_timestamp_utc": "2026-09-13T17:00:00Z",
        "horizon": "T-120m",
        "retrieval_timestamp_utc": "2026-09-13T14:59:30Z",
        "schedule_state": "scheduled",
        "inputs": {
            "schedule": {"kickoff_timestamp_utc": "2026-09-13T17:00:00Z"},
            "market": {"status": "available", "books": 4},
            "personnel": {"status": "available"},
            "weather": {"status": "available"},
            "football": {"status": "available"},
            "context": {"status": "available"},
        },
        "source_state": [
            {
                "source_id": "nflverse_schedule",
                "retrieved_at_utc": "2026-09-13T14:59:20Z",
                "available_at_utc": "2026-09-13T14:59:00Z",
                "status": "ok",
                "quality": "qualified",
            },
            {
                "source_id": "nws_api",
                "retrieved_at_utc": "2026-09-13T14:59:25Z",
                "available_at_utc": "2026-09-13T14:55:00Z",
                "status": "ok",
                "quality": "prospective_only",
            },
        ],
    }
    kwargs.update(overrides)
    return build_snapshot(**kwargs)


def test_target_timestamp_is_deterministic() -> None:
    assert target_timestamp("2026-09-13T17:00:00Z", "T-120m") == "2026-09-13T15:00:00Z"
    assert target_timestamp("2026-09-13T17:00:00Z", "T-7d") == "2026-09-06T17:00:00Z"


def test_snapshot_has_content_addressed_receipt() -> None:
    snapshot = _snapshot()
    assert snapshot["schema_version"] == SCHEMA_VERSION
    assert snapshot["receipt"]["snapshot_id"].startswith("2026_01_CHI_CAR__T-120m__")
    assert len(snapshot["receipt"]["content_sha256"]) == 64
    validate_snapshot(snapshot)


def test_research_only_horizons_are_explicit() -> None:
    snapshot = _snapshot(horizon="T-30m", retrieval_timestamp_utc="2026-09-13T16:29:30Z")
    assert snapshot["research_only"] is True
    official = _snapshot()
    assert official["research_only"] is False


def test_future_source_availability_fails_closed() -> None:
    sources = copy.deepcopy(_snapshot()["source_state"])
    sources[0]["available_at_utc"] = "2026-09-13T15:01:00Z"
    with pytest.raises(SnapshotValidationError, match="future-information leakage"):
        _snapshot(source_state=sources)


def test_post_kickoff_snapshot_is_rejected() -> None:
    with pytest.raises(SnapshotValidationError, match="must precede kickoff"):
        _snapshot(retrieval_timestamp_utc="2026-09-13T17:00:01Z")


def test_missing_input_family_is_rejected() -> None:
    inputs = copy.deepcopy(_snapshot()["inputs"])
    inputs.pop("weather")
    with pytest.raises(SnapshotValidationError, match="missing input families"):
        _snapshot(inputs=inputs)


def test_tampering_breaks_receipt() -> None:
    snapshot = _snapshot()
    snapshot["inputs"]["market"]["books"] = 99
    with pytest.raises(SnapshotValidationError, match="content hash mismatch"):
        validate_snapshot(snapshot)


def test_append_only_store_rejects_duplicate_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "snapshots.jsonl"
    snapshot = _snapshot()
    receipt = append_snapshot_jsonl(path, snapshot)
    assert receipt.snapshot_id == snapshot["receipt"]["snapshot_id"]
    with pytest.raises(SnapshotValidationError, match="duplicate snapshot_id"):
        append_snapshot_jsonl(path, snapshot)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [snapshot]


def test_store_detects_corruption_before_append(tmp_path: Path) -> None:
    path = tmp_path / "snapshots.jsonl"
    path.write_text("not-json\n", encoding="utf-8")
    with pytest.raises(SnapshotValidationError, match="corrupt append-only store"):
        append_snapshot_jsonl(path, _snapshot())
