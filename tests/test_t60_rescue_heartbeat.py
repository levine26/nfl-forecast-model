from __future__ import annotations

"""Regression for the secondary T-60 alarm; never changes immutable history."""

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

from scripts.pregame_due import due_games


ROOT = Path(__file__).resolve().parents[1]
KICKOFF = datetime(2026, 10, 11, 17, 0, tzinfo=timezone.utc)
GAME = "2026_05_CHI_GB"


def fixture(tmp_path):
    current = tmp_path / "this_week.csv"
    history = tmp_path / "prediction_history.csv"
    with current.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["game_id", "gameday", "gametime"])
        writer.writeheader()
        writer.writerow({"game_id": GAME, "gameday": "2026-10-11", "gametime": "13:00"})
    with history.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["game_id", "lock_status"])
        writer.writeheader()
    return current, history


def test_rescue_gate_acts_only_in_last_65_minutes_pre_kickoff(tmp_path):
    feed, history = fixture(tmp_path)
    assert due_games(feed, history, KICKOFF - timedelta(minutes=66),
                     min_minutes=0, max_minutes=65) == []
    assert [gid for gid, _ in due_games(
        feed, history, KICKOFF - timedelta(minutes=60), min_minutes=0, max_minutes=65
    )] == [GAME]
    assert due_games(feed, history, KICKOFF + timedelta(seconds=1),
                     min_minutes=0, max_minutes=65) == []


def test_existing_immutable_lock_never_triggers_rescue(tmp_path):
    feed, history = fixture(tmp_path)
    with history.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["game_id", "lock_status"])
        writer.writerow({"game_id": GAME, "lock_status": "LOCKED"})
    assert due_games(feed, history, KICKOFF - timedelta(minutes=60),
                     min_minutes=0, max_minutes=65) == []


def test_verified_recovered_lock_also_prevents_duplicate_dispatch(tmp_path):
    feed, history = fixture(tmp_path)
    with history.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["game_id", "lock_status"])
        writer.writerow({"game_id": GAME, "lock_status": "RECOVERED_MISSED_LOCK"})
    assert due_games(feed, history, KICKOFF - timedelta(minutes=60),
                     min_minutes=0, max_minutes=65) == []


def test_separate_rescue_dispatches_existing_lock_worker_only():
    text = (ROOT / ".github/workflows/official_lock_t60_rescue.yml").read_text()
    assert "workflow_dispatch:" in text
    assert "max-minutes 65" in text
    assert "min-minutes 0" in text
    assert "gh workflow run fast_official_lock.yml --ref main" in text
    assert "actions: write" in text
    assert "ref: main" in text
    assert "git reset --hard origin/main" in text
    assert "if: steps.due.outputs.due == 'true'" in text
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in text
    assert "scripts/refresh_market.py" not in text
    assert "scripts/run_week.py" not in text
    assert "git push" not in text
    assert "prediction_history.csv" in text
    assert text.count("cron:") >= 3
    worker = (ROOT / ".github/workflows/fast_official_lock.yml").read_text()
    assert "python -m scripts.fast_lock_prepare --output-dir outputs" in worker
    assert "python scripts/fast_official_lock.py --output-dir outputs" in worker
    assert "git add outputs/" in worker
    assert "cancel-in-progress: ${{ github.event_name == 'pull_request' }}" in worker
