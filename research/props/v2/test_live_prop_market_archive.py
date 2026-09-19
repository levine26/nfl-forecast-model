from __future__ import annotations

from datetime import datetime, timedelta, timezone
import gzip
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "research" / "props" / "v2" / "archive_live_prop_market.py"
WORKFLOW = ROOT / ".github" / "workflows" / "research_props_v2_market_archive.yml"
SOURCE_SHA = "a" * 40


def _module():
    spec = importlib.util.spec_from_file_location("props_market_archive_tested", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot(captured: datetime, kickoff: datetime) -> dict:
    artifact = {
        "schema_version": "levline.props.market.v1",
        "research_only": True,
        "production_authorized": False,
        "as_of_utc": captured.isoformat(),
        "game_id": "g1",
        "player_id": "p1",
        "player": "Player One",
        "prop_type": "receiving_yards",
        "consensus_line": 64.5,
        "consensus_no_vig_p_over": 0.51,
        "sportsbook_count": 2,
        "sportsbooks": ["book_a", "book_b"],
        "line_min": 63.5,
        "line_max": 64.5,
        "line_range": 1.0,
        "line_stddev": 0.5,
        "individual_books": [
            {"sportsbook_key": "book_a", "line": 64.5, "over_american": -110, "under_american": -110},
            {"sportsbook_key": "book_b", "line": 63.5, "over_american": -105, "under_american": -115},
        ],
    }
    return {
        "contract_version": "levline-props-market-live-v0.1",
        "research_only": True,
        "production_authorized": False,
        "provider": "the_odds_api",
        "captured_at_utc": captured.isoformat(),
        "market_artifacts": [artifact],
        "audit": {
            "matched_events": [
                {"provider_event_id": "evt1", "game_id": "g1", "kickoff_utc": kickoff.isoformat()}
            ]
        },
    }


def _write_capture(root: Path, snapshot: dict):
    run = root / "artifact" / "20260918T170000Z"
    run.mkdir(parents=True)
    (run / "market.json").write_text(json.dumps(snapshot), encoding="utf-8")
    (run / "market.raw.json").write_text(
        json.dumps({"payload_sha256": "abc123"}),
        encoding="utf-8",
    )
    return run / "market.json"


def test_archives_full_normalized_multi_book_state_and_pit_distance(tmp_path):
    module = _module()
    captured = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    kickoff = captured + timedelta(hours=4)
    market = _write_capture(tmp_path / "download", _snapshot(captured, kickoff))
    out = tmp_path / "archive"
    manifest = out / "manifest.jsonl"

    result = module.archive_snapshot(
        market,
        output_dir=out,
        manifest_path=manifest,
        source_workflow_run="123",
        source_head_sha=SOURCE_SHA,
    )
    assert result["status"] == "archived"
    assert result["artifact_count"] == 1
    assert result["raw_provider_payload_sha256"] == "abc123"
    assert result["source_head_sha"] == SOURCE_SHA

    rows = [json.loads(line) for line in manifest.read_text().splitlines()]
    assert len(rows) == 1
    capture = out / rows[0]["archive_file"]
    with gzip.open(capture, "rt", encoding="utf-8") as handle:
        record = json.loads(handle.readline())
    assert record["minutes_to_kickoff"] == pytest.approx(240.0)
    assert record["source_head_sha"] == SOURCE_SHA
    assert record["market_artifact"]["sportsbook_count"] == 2
    assert len(record["market_artifact"]["individual_books"]) == 2


def test_duplicate_snapshot_is_idempotent(tmp_path):
    module = _module()
    captured = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    kickoff = captured + timedelta(hours=2)
    market = _write_capture(tmp_path / "download", _snapshot(captured, kickoff))
    out = tmp_path / "archive"
    manifest = out / "manifest.jsonl"

    first = module.archive_snapshot(
        market, output_dir=out, manifest_path=manifest, source_workflow_run="123", source_head_sha=SOURCE_SHA
    )
    second = module.archive_snapshot(
        market, output_dir=out, manifest_path=manifest, source_workflow_run="123", source_head_sha=SOURCE_SHA
    )
    assert first["status"] == "archived"
    assert second["status"] == "existing"
    assert len(manifest.read_text().splitlines()) == 1


def test_post_kickoff_capture_fails_closed(tmp_path):
    module = _module()
    kickoff = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    captured = kickoff + timedelta(seconds=1)
    market = _write_capture(tmp_path / "download", _snapshot(captured, kickoff))
    with pytest.raises(module.MarketArchiveError, match="post-kickoff"):
        module.archive_snapshot(
            market,
            output_dir=tmp_path / "archive",
            manifest_path=tmp_path / "archive" / "manifest.jsonl",
            source_workflow_run="123",
        )


def test_production_authorized_snapshot_is_rejected(tmp_path):
    module = _module()
    captured = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    kickoff = captured + timedelta(hours=2)
    snapshot = _snapshot(captured, kickoff)
    snapshot["production_authorized"] = True
    market = _write_capture(tmp_path / "download", snapshot)
    with pytest.raises(module.MarketArchiveError, match="production-authorized"):
        module.archive_snapshot(
            market,
            output_dir=tmp_path / "archive",
            manifest_path=tmp_path / "archive" / "manifest.jsonl",
            source_workflow_run="123",
        )


def test_rejects_missing_or_invalid_source_head_sha(tmp_path):
    module = _module()
    captured = datetime(2026, 9, 18, 17, 0, tzinfo=timezone.utc)
    kickoff = captured + timedelta(hours=2)
    market = _write_capture(tmp_path / "download", _snapshot(captured, kickoff))
    for value in ("", "not-a-sha"):
        with pytest.raises(module.MarketArchiveError, match="source_head_sha"):
            module.archive_snapshot(
                market,
                output_dir=tmp_path / "archive",
                manifest_path=tmp_path / "archive" / "manifest.jsonl",
                source_workflow_run="123",
                source_head_sha=value,
            )


def test_market_archive_workflow_has_exact_source_no_backfill_gate():
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = "EXACT_SOURCE_RUN_LISTENER_VERSION: levline-props-v2-market-archive-exact-source-v0.1.0"
    assert marker in text
    assert "source run predates the exact-source market archive listener" in text
    assert "head_sha=$SHA" in text
    assert "--source-head-sha" in text
