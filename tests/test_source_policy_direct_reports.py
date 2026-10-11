from nfl_forecast.source_policy import (
    is_direct_media_report_url,
    is_substantive_report_candidate,
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


def test_substantive_gate_rejects_real_but_nonsubstantive_news_urls():
    cases = [
        ("NFL Week 5 picks: predictions for every game",
         "https://www.nfl.com/news/nfl-picks-week-5-2026-nfl-season"),
        ("Where to watch Cowboys vs. Buccaneers: Prediction, pick, odds, streaming for TNF",
         "https://www.cbssports.com/nfl/news/cowboys-vs-buccaneers-prediction-where-to-watch-tnf/"),
        ("Lions at Cardinals: How to watch, listen and follow",
         "https://www.detroitlions.com/news/lions-at-cardinals-how-to-watch-listen-and-follow-2026"),
        ("Jaguars vs. Eagles: odds, injuries, key matchup in Jags' first London game",
         "https://sports.yahoo.com/articles/jaguars-vs-eagles-odds-injuries-201049659.html"),
        ("NFL Week 5 Schedule: How to Watch, TV Channels, Streaming, Game Previews",
         "https://www.foxsports.com/stories/nfl/nfl-week-5-schedule-how-watch-tv-channels-streaming-game-previews"),
    ]
    assert all(
        is_direct_media_report_url(url) and
        not is_substantive_report_candidate(title=title, url=url)
        for title, url in cases
    )


def test_substantive_gate_keeps_two_independent_direct_matchup_reporters():
    cases = [
        ("Week 5 opponent: What the Cardinals are saying",
         "https://www.detroitlions.com/news/week-5-opponent-what-the-cardinals-are-saying-lafleur-brissett"),
        ("Vikings at Saints Week 5 Game Preview",
         "https://www.vikings.com/news/saints-week-5-game-preview-2026"),
        ("Jaguars Media Give Final Analysis Before Week 5 Against Eagles in London",
         "https://www.jaguars.com/news/jaguars-media-give-final-analysis-before-week-5-against-eagles-in-london"),
        ("Everything You Need to Know: Ravens vs. Falcons | Game Preview",
         "https://www.baltimoreravens.com/news/ravens-falcons-game-preview-week-5-2026-lamar-jackson-ankle-tyler-huntley-bijan-robinson"),
        ("Week 5 Blog: Enjoying every minute of it",
         "https://www.steelers.com/news/week-5-blog-being-more-efficient"),
    ]
    assert all(is_substantive_report_candidate(title=title, url=url) for title, url in cases)


def test_substantive_gate_does_not_claim_accepted_source_is_fact_verified():
    # A true result merely states report-candidate suitability, not URL
    # resolution, timestamp accuracy or claim/roster entailment.
    assert is_substantive_report_candidate(
        title="Week 5 opponent: What the Cardinals are saying",
        url="https://www.detroitlions.com/news/week-5-opponent-what-the-cardinals-are-saying-lafleur-brissett",
    )
