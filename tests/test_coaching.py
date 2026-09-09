from datetime import datetime, timezone
import json

from nfl_forecast.coaching import COACHING_CACHE_VERSION, fetch_coaching_staff, load_coaching_history


def _staff(team="NE", season=2026):
    return {
        "team": team,
        "season": season,
        "head_coach": "Head Coach",
        "off_coach": "Offensive Coach",
        "def_coach": "Defensive Coach",
    }


class _Response:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class _Session:
    def __init__(self, html):
        self.html = html
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return _Response(self.html)


def test_rendered_infobox_extracts_current_staff():
    html = """
    <html><table class="infobox">
      <tr><th>Coach</th><td><a>Mike Vrabel</a></td></tr>
      <tr><th>Off. coach</th><td>Josh McDaniels <sup>[1]</sup></td></tr>
      <tr><th>Def. coach</th><td>Zak Kuhr</td></tr>
    </table></html>
    """
    session = _Session(html)
    data, source = fetch_coaching_staff("NE", 2026, session=session)

    assert data["head_coach"] == "Mike Vrabel"
    assert data["off_coach"] == "Josh McDaniels"
    assert data["def_coach"] == "Zak Kuhr"
    assert data["source_url"] == source
    assert "2026_New_England_Patriots_season" in source
    assert session.urls == [source]


def test_rendered_staff_table_fills_historical_coordinators_missing_from_infobox():
    html = """
    <html>
      <table class="infobox"><tr><th>Coach</th><td>Robert Saleh</td></tr></table>
      <table class="wikitable">
        <caption>2023 New York Jets staff</caption>
        <tr><td><ul>
          <li>Head coach – Robert Saleh</li>
          <li>Offensive coordinator – Nathaniel Hackett</li>
          <li>Defensive coordinator – Jeff Ulbrich</li>
        </ul></td></tr>
      </table>
    </html>
    """
    data, _ = fetch_coaching_staff("NYJ", 2023, session=_Session(html))
    assert data["head_coach"] == "Robert Saleh"
    assert data["off_coach"] == "Nathaniel Hackett"
    assert data["def_coach"] == "Jeff Ulbrich"


def test_malformed_infobox_role_is_replaced_by_explicit_staff_table():
    html = """
    <html>
      <table class="infobox">
        <tr><th>Coach</th><td>Todd Bowles</td></tr>
        <tr><th>Def. coach</th><td>general_manager = Jason Licht</td></tr>
      </table>
      <table><tr><td><li>Defensive coordinator – Kacy Rodgers</li></td></tr></table>
    </html>
    """
    data, _ = fetch_coaching_staff("TB", 2023, session=_Session(html))
    assert data["def_coach"] == "Kacy Rodgers"


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


def test_successful_old_parser_cache_refreshes_once(tmp_path):
    cache = tmp_path / "coaching.json"
    cache.write_text(json.dumps({
        "NYJ:2023": {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "data": {"team":"NYJ","season":2023,"head_coach":"Robert Saleh","off_coach":None,"def_coach":None},
        }
    }))
    calls = []

    def fetcher(team, year, session=None):
        calls.append((team, year))
        return {
            "team":team,"season":year,"head_coach":"Robert Saleh",
            "off_coach":"Nathaniel Hackett","def_coach":"Jeff Ulbrich",
        }, "https://example.test"

    history, status = load_coaching_history(
        ["NYJ"], 2023, cache, lookback=0, fetcher=fetcher,
        request_interval_seconds=0, current_retry_delay_seconds=0,
    )

    assert calls == [("NYJ", 2023)]
    assert history["NYJ"][2023]["off_coach"] == "Nathaniel Hackett"
    assert status["parser_version"] == COACHING_CACHE_VERSION
    assert status["parser_version_refreshes"] == 1
