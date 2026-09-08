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
