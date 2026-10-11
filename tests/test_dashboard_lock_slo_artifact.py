from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.audit_official_lock_timeliness import audit_history

REPO = Path(__file__).resolve().parents[1]


def test_pages_build_publishes_read_only_timestamp_audit_before_history_compatibility():
    text = (REPO / ".github/workflows/dashboard.yml").read_text()
    assert "tests/test_dashboard_lock_slo_artifact.py" in text
    publish = text.index("      - name: Publish actual immutable-lock deadline audit (read-only)")
    normalize = text.index("      - name: Normalize immutable history for Sunday Signal")
    assert publish < normalize
    step = text[publish:normalize]
    assert "scripts/audit_official_lock_timeliness.py" in step
    assert "--history site/public/data/prediction_history.csv" in step
    assert "--output site/public/data/official_lock_timeliness.json" in step
    assert "sum(report[\"counts\"].values()) == report[\"locked_count\"]" in step
    assert "F-ST-01-FROZEN-2026" in step
    assert "git add outputs/" not in step
    assert "git push" not in step


def test_read_only_audit_does_not_erase_late_or_missed_history_and_preserves_actual_lead():
    kick = datetime(2026, 10, 9, 0, 15, tzinfo=timezone.utc)
    rows = [
        {"game_id": "2026_05_TB_DAL", "lock_status": "LOCKED",
         "season": "2026", "week": "5",
         "kickoff_utc": kick.isoformat(),
         "lock_timestamp_utc": (kick - timedelta(minutes=19.3416)).isoformat()},
        {"game_id": "2026_04_IND_WAS", "lock_status": "RECOVERED_MISSED_LOCK",
         "season": "2026", "week": "4",
         "kickoff_utc": kick.isoformat(), "lock_timestamp_utc": ""},
    ]
    snapshot = repr(rows)
    result = audit_history(rows, season=2026)
    assert repr(rows) == snapshot  # audit must not mutate source rows
    assert result["locked_count"] == 1
    assert result["counts"]["late"] == 1
    assert result["counts"]["on_time"] == 0
    assert result["games"][0]["game_id"] == "2026_05_TB_DAL"
    assert result["games"][0]["minutes_before_kickoff"] == 19.3416
    assert result["games"][0]["minutes_late_vs_t120"] == 100.6584
    assert result["all_locks_on_time"] is False


def test_audit_never_transforms_historic_late_lock_to_success():
    kick = datetime(2026, 10, 11, 20, tzinfo=timezone.utc)
    rows = [
        {"game_id": "2026_05_CIN_MIA", "lock_status": "LOCKED", "season": "2026", "week": "5",
         "kickoff_utc": kick.isoformat(),
         "lock_timestamp_utc": (kick - timedelta(minutes=113)).isoformat()},
        {"game_id": "2026_05_CHI_GB", "lock_status": "LOCKED", "season": "2026", "week": "5",
         "kickoff_utc": kick.isoformat(),
         "lock_timestamp_utc": (kick - timedelta(minutes=109.9)).isoformat()},
    ]
    out = audit_history(rows, season=2026, week=5)
    assert out["counts"]["on_time"] == 1
    assert out["counts"]["late"] == 1
    assert out["all_locks_on_time"] is False
    assert out["games"][1]["minutes_late_vs_t120"] == 10.1
