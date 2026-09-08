from datetime import timezone
from scripts.pregame_due import kickoff_utc


def test_kickoff_uses_new_york_dst_not_fixed_utc_offset():
    sep=kickoff_utc("2026-09-13","13:00")
    nov=kickoff_utc("2026-11-15","13:00")
    assert sep.hour==17
    assert nov.hour==18
    assert sep.tzinfo==timezone.utc
    assert nov.tzinfo==timezone.utc
