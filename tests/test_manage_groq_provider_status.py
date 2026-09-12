from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "manage_groq_provider_status.py"
spec = importlib.util.spec_from_file_location("manage_groq_provider_status", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_init_clears_stale_failed_game_flags(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    status.write_text(json.dumps({
        "evidence": {"status": "healthy"},
        "groq_provider_fallback": {
            "run_id": "old-run",
            "status": "degraded",
            "games": {"g1": {"requires_chatgpt_refresh": True}},
            "failed_games": ["g1"],
        },
    }))

    section = module.initialize(
        status,
        run_id="new-run",
        now=datetime(2026, 9, 12, 17, 0, tzinfo=timezone.utc),
    )

    payload = json.loads(status.read_text())
    assert payload["evidence"] == {"status": "healthy"}
    assert section["run_id"] == "new-run"
    assert section["status"] == "healthy"
    assert section["games"] == {}
    assert section["failed_games"] == []
    assert payload["groq_provider_fallback"] == section


def test_snapshot_and_restore_survive_latest_main_reset(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    snapshot = tmp_path / "provider.json"
    module.initialize(
        status,
        run_id="run-93",
        now=datetime(2026, 9, 12, 17, 0, tzinfo=timezone.utc),
    )
    payload = json.loads(status.read_text())
    payload["groq_provider_fallback"]["status"] = "degraded"
    payload["groq_provider_fallback"]["games"] = {
        "2026_01_ARI_LAC": {
            "provider_result": "failed",
            "fallback_source": "last_validated_editorial",
            "requires_chatgpt_refresh": True,
        }
    }
    payload["groq_provider_fallback"]["failed_games"] = ["2026_01_ARI_LAC"]
    status.write_text(json.dumps(payload))

    module.snapshot(status, snapshot, run_id="run-93")

    # Simulate `git reset --hard origin/main`: latest main has fresher contextual
    # sections but no current-run provider ledger.
    status.write_text(json.dumps({
        "generated_utc": "2026-09-12T17:05:00+00:00",
        "evidence": {"status": "healthy", "signals": 200},
    }))
    restored = module.restore(status, snapshot, run_id="run-93")

    latest = json.loads(status.read_text())
    assert latest["generated_utc"] == "2026-09-12T17:05:00+00:00"
    assert latest["evidence"]["signals"] == 200
    assert restored["games"]["2026_01_ARI_LAC"]["requires_chatgpt_refresh"] is True
    assert latest["groq_provider_fallback"] == restored


def test_snapshot_fails_closed_for_wrong_or_missing_run(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    module.initialize(status, run_id="run-a")
    try:
        module.snapshot(status, tmp_path / "snapshot.json", run_id="run-b")
    except ValueError as exc:
        assert "run-b" in str(exc)
    else:
        raise AssertionError("wrong-run provider status must fail closed")


def test_restore_fails_closed_for_wrong_run(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    snapshot = tmp_path / "provider.json"
    module.initialize(status, run_id="run-a")
    module.snapshot(status, snapshot, run_id="run-a")
    try:
        module.restore(status, snapshot, run_id="run-b")
    except ValueError as exc:
        assert "run-b" in str(exc)
    else:
        raise AssertionError("wrong-run provider snapshot must fail closed")
