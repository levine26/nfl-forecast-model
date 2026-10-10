from datetime import datetime, timedelta, timezone

import pytest

from scripts.groq_dispatch_due import assess_due

NOW = datetime(2026, 10, 10, 15, 30, tzinfo=timezone.utc)
IDS = ["2026_05_BUF_LA", "2026_05_TB_DAL"]
STATUS = {"generated_utc": NOW.isoformat(), "copilot_media": {"advisories": {}}}


def provider(ids=IDS, hours=1):
    ts = (NOW - timedelta(hours=hours)).isoformat()
    return {"generated_utc": ts, "games": {
        gid: {"headline": f"Distinct headline for {gid}",
              "paragraph1": f"Verified matchup analysis for {gid}"} for gid in ids
    }}


def test_missing_week_five_games_triggers_provider():
    due, reason = assess_due(IDS, provider(["2026_04_BUF_LA"]), STATUS, now_utc=NOW)
    assert due and reason.startswith("missing_current_game_ids:")


def test_complete_recent_provider_artifact_does_not_cause_redundant_calls():
    due, reason = assess_due(IDS, provider(), STATUS, now_utc=NOW)
    assert not due
    assert reason.endswith(":2")


def test_source_freshness_advisory_triggers_replacement_attempt():
    status = {"generated_utc": NOW.isoformat(), "copilot_media": {
        "advisories": {"2026_05_BUF_LA": "new_injury_report"}
    }}
    due, reason = assess_due(IDS, provider(), status, now_utc=NOW)
    assert due and reason == "source_freshness_advisory"


def test_old_or_missing_provider_data_is_due_not_promoted():
    assert assess_due(IDS, provider(hours=40), STATUS, now_utc=NOW)[0]
    artifact = provider()
    del artifact["games"][IDS[1]]["paragraph1"]
    assert assess_due(IDS, artifact, STATUS, now_utc=NOW)[0]


def test_fail_closed_on_duplicate_slate_or_invalid_context_status():
    with pytest.raises(ValueError):
        assess_due([IDS[0], IDS[0]], provider(), STATUS, now_utc=NOW)
    with pytest.raises(ValueError):
        assess_due(IDS, provider(), {}, now_utc=NOW)
    with pytest.raises(ValueError):
        assess_due(IDS, provider(hours=-1), STATUS, now_utc=NOW)
