from datetime import timezone
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pregame_due.py"
SPEC = importlib.util.spec_from_file_location("pregame_due", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
pregame_due = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pregame_due)
kickoff_utc = pregame_due.kickoff_utc


def test_kickoff_uses_new_york_dst_not_fixed_utc_offset():
    sep = kickoff_utc("2026-09-13", "13:00")
    nov = kickoff_utc("2026-11-15", "13:00")
    assert sep.hour == 17
    assert nov.hour == 18
    assert sep.tzinfo == timezone.utc
    assert nov.tzinfo == timezone.utc


def _write_feed(tmp_path):
    feed = tmp_path / "this_week.csv"
    feed.write_text(
        "game_id,gameday,gametime,away_team,home_team\n"
        "2026_05_TB_DAL,2026-10-08,20:15,TB,DAL\n",
        encoding="utf-8",
    )
    return feed


def test_gate_recovers_a_late_but_pre_kickoff_lock(tmp_path):
    from datetime import datetime

    feed = _write_feed(tmp_path)
    # Dallas kickoff 20:15 ET == 00:15 UTC. Only 25 minutes remain.
    now = datetime(2026, 10, 8, 23, 50, tzinfo=timezone.utc)
    assert [gid for gid, _ in pregame_due.due_games(
        feed, tmp_path / "no_history.csv", now
    )] == ["2026_05_TB_DAL"]


def test_gate_skips_existing_immutable_official_lock(tmp_path):
    from datetime import datetime

    feed = _write_feed(tmp_path)
    history = tmp_path / "prediction_history.csv"
    history.write_text(
        "game_id,lock_status\n2026_05_TB_DAL,LOCKED\n",
        encoding="utf-8",
    )
    now = datetime(2026, 10, 8, 23, 50, tzinfo=timezone.utc)
    assert pregame_due.due_games(feed, history, now) == []


def test_gate_stops_after_kickoff_and_does_not_backdate(tmp_path):
    from datetime import datetime

    feed = _write_feed(tmp_path)
    after = datetime(2026, 10, 9, 0, 16, tzinfo=timezone.utc)
    assert pregame_due.due_games(feed, tmp_path / "no_history.csv", after) == []


def test_gate_raises_on_malformed_official_history(tmp_path):
    from datetime import datetime
    import pytest

    feed = _write_feed(tmp_path)
    history = tmp_path / "prediction_history.csv"
    history.write_text("wrong,columns\na,b\n", encoding="utf-8")
    now = datetime(2026, 10, 8, 23, 50, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Malformed official prediction history"):
        pregame_due.due_games(feed, history, now)
