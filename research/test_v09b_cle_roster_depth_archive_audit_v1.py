from __future__ import annotations

from bs4 import BeautifulSoup

from research.v09b_cle_roster_depth_archive_audit_v1 import discover_week_viewers, full_document_link


def test_discover_regular_season_week_and_game_date() -> None:
    html = '''
    <div class="game"><div>Sunday 9/8 Week 1 vs Titans</div>
      <a href="/season/2019/regular-season/week-1/rosters-depth/">Rosters &amp; Depth</a>
    </div>
    <div class="game"><div>BYE WEEK</div><span>Rosters &amp; Depth</span></div>
    <div class="pre"><div>Thursday 8/8 Week 1 vs Redskins</div>
      <a href="/season/2019/preseason/week-1/rosters-depth/">Rosters &amp; Depth</a>
    </div>
    '''
    rows, duplicates = discover_week_viewers(
        html,
        archive_url="https://browns.1rmg.com/season/2019/",
        season=2019,
    )
    assert duplicates == 0
    assert rows == [{
        "season": 2019,
        "week": 1,
        "game_date": "2019-09-08",
        "viewer_url": "https://browns.1rmg.com/season/2019/regular-season/week-1/rosters-depth/",
    }]


def test_january_regular_season_game_uses_following_calendar_year() -> None:
    html = '''<div>Sunday 1/3 Week 17 vs Steelers
    <a href="/season/2020/regular-season/week-17/rosters-depth/">Rosters &amp; Depth</a></div>'''
    rows, _ = discover_week_viewers(html, archive_url="https://browns.1rmg.com/season/2020/", season=2020)
    assert rows[0]["game_date"] == "2021-01-03"


def test_full_document_requires_exact_child_media_host() -> None:
    html = '''
    <a href="https://media.browns.1rmg.com/wp-content/uploads/a.pdf">Full Document</a>
    <a href="https://evil.example/a.pdf">Full Document</a>
    '''
    url, count = full_document_link(html, viewer_url="https://browns.1rmg.com/season/2019/regular-season/week-1/rosters-depth/")
    assert count == 1
    assert url == "https://media.browns.1rmg.com/wp-content/uploads/a.pdf"


def test_duplicate_week_links_are_diagnostic_failure_input() -> None:
    html = '''
    <div>Sunday 9/8 Week 1 vs Titans
      <a href="/season/2019/regular-season/week-1/rosters-depth/">Rosters &amp; Depth</a>
      <a href="/season/2019/regular-season/week-1/rosters-depth/">Rosters &amp; Depth</a>
    </div>
    '''
    rows, duplicates = discover_week_viewers(html, archive_url="https://browns.1rmg.com/season/2019/", season=2019)
    assert len(rows) == 2
    assert duplicates == 1
