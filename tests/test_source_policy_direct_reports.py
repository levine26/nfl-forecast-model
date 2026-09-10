from nfl_forecast.source_policy import (
    is_direct_media_report_url,
    media_domain_family,
)


def test_direct_report_policy_rejects_generic_navigation_pages():
    urls = [
        "https://www.nfl.com/teams/los-angeles-chargers/",
        "https://www.chargers.com/schedule/",
        "https://www.nfl.com/games/bills-at-texans-2026-reg-1",
        "https://www.espn.com/nfl/team/_/name/nyg/new-york-giants",
        "https://nextgenstats.nfl.com/stats/quarterbacks/2025/REG/all",
        "https://www.cbssports.com/nfl/standings/",
    ]
    assert not any(is_direct_media_report_url(url) for url in urls)


def test_direct_report_policy_accepts_known_report_shapes():
    urls = [
        "https://www.nfl.com/news/example-report",
        "https://www.espn.com/nfl/story/_/id/123/example-report",
        "https://www.cbssports.com/nfl/news/example-report/",
        "https://www.colts.com/news/example-report",
        "https://apnews.com/article/example-report",
        "https://sports.yahoo.com/articles/example-report.html",
    ]
    assert all(is_direct_media_report_url(url) for url in urls)


def test_x_and_twitter_share_one_publisher_family():
    assert media_domain_family("https://x.com/reporter/status/123") == "x.com"
    assert media_domain_family("https://twitter.com/reporter/status/456") == "x.com"
