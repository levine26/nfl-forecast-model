from datetime import datetime, timezone
import json

from nfl_forecast.coaching import load_coaching_history


def _staff(team="NE", season=2026):
    return {
        "team": team,
        "season": season,
        "head_coach": "Head Coach",
        "off_coach": "Offensive Coach",
        "def_coach": "Defensive Coach",
    }


def test_stale_negative_cache_is_retried_and_can_recover(tmp_path):
    cache = tmp_path / "coaching.json"
    cache.write_text(json.dumps({
        "NE:2026": {"fetched_at": "2026-09-08T20:00:00+00:00", "data": None}
    }))
    calls = []

    def fetcher(team, year, session=None):
        calls.append((team, year))
        return _staff(team, year), f"https://example.test/{team}/{year}"

    history, status = load_coaching_history(
        ["NE"], 2026, cache, lookback=0, fetcher=fetcher,
        negative_cache_ttl_seconds=60, request_interval_seconds=0,
        current_retry_delay_seconds=0,
    )

    assert calls == [("NE", 2026)]
    assert history["NE"][2026]["head_coach"] == "Head Coach"
    assert status["negative_entries_retried"] == 1
    assert status["refresh_attempts"] == 1


def test_fresh_negative_cache_is_not_hammered(tmp_path):
    cache = tmp_path / "coaching.json"
    cache.write_text(json.dumps({
        "NE:2026": {"fetched_at": datetime.now(timezone.utc).isoformat(), "data": None}
    }))

    def should_not_fetch(*args, **kwargs):
        raise AssertionError("fresh negative cache should not be retried")

    history, status = load_coaching_history(
        ["NE"], 2026, cache, lookback=0, fetcher=should_not_fetch,
        negative_cache_ttl_seconds=3600, request_interval_seconds=0,
        current_retry_delay_seconds=0,
    )

    assert history["NE"] == {}
    assert status["refresh_attempts"] == 0
    assert status["pages_missing"] == 1


def test_current_season_miss_gets_one_paced_retry(tmp_path):
    calls = []

    def flaky_fetch(team, year, session=None):
        calls.append((team, year))
        if len(calls) == 1:
            return None, f"https://example.test/{team}/{year}"
        return _staff(team, year), f"https://example.test/{team}/{year}"

    history, status = load_coaching_history(
        ["BAL"], 2026, tmp_path / "coaching.json", lookback=0,
        fetcher=flaky_fetch, request_interval_seconds=0,
        current_retry_delay_seconds=0,
    )

    assert calls == [("BAL", 2026), ("BAL", 2026)]
    assert history["BAL"][2026]["head_coach"] == "Head Coach"
    assert status["current_retry_recoveries"] == 1
    assert status["refresh_attempts"] == 2
