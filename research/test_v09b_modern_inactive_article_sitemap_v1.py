from __future__ import annotations

from datetime import date

from research import v09b_modern_inactive_article_sitemap_v1 as m


def test_extract_sitemap_entries_keeps_date_title_and_first_party_url():
    html = """
    <ul>
      <li><span>2021-11-14</span> | <a href="/news/week-10-inactives-chiefs-vs-raiders">Week 10 Inactives | Chiefs vs. Raiders</a></li>
      <li><span>2021-11-14</span> | <a href="https://example.com/not-first-party">Inactives mirror</a></li>
      <li><span>2021-11-15</span> | <a href="/news/postgame">Postgame recap</a></li>
    </ul>
    """
    rows = m.extract_sitemap_entries(
        html,
        sitemap_url="https://www.chiefs.com/sitemap/html/articles/2021/11",
        domains=["chiefs.com"],
    )
    assert rows == [
        {
            "date": "2021-11-14",
            "title": "Week 10 Inactives | Chiefs vs. Raiders",
            "url": "https://www.chiefs.com/news/week-10-inactives-chiefs-vs-raiders",
        },
        {
            "date": "2021-11-15",
            "title": "Postgame recap",
            "url": "https://www.chiefs.com/news/postgame",
        },
    ]


def test_title_taxonomy_is_case_and_apostrophe_normalized():
    markers = ["inactive", "will/won't play"]
    assert m._title_matches("Steelers INACTIVES for Week 16", markers)
    assert m._title_matches("Who Will/Won’t Play Sunday?", markers)
    assert not m._title_matches("Friday Injury Report", markers)


def test_host_allowlist_requires_https_and_exact_team_domain_family():
    assert m._host_allowed("https://www.raiders.com/news/foo", ["raiders.com"])
    assert m._host_allowed("https://raiders.com/news/foo", ["raiders.com"])
    assert not m._host_allowed("http://www.raiders.com/news/foo", ["raiders.com"])
    assert not m._host_allowed("https://example.com/news/foo", ["raiders.com"])
    assert not m._host_allowed("https://evil.raiders.com/news/foo", ["raiders.com"])


def test_game_date_accepts_iso_string_and_date_object():
    assert m._game_date({"game_id": "2021_10_KC_LV", "gameday": "2021-11-14"}) == "2021-11-14"
    assert m._game_date({"game_id": "2021_10_KC_LV", "gameday": date(2021, 11, 14)}) == "2021-11-14"


def test_game_id_parser_preserves_historical_team_codes():
    assert m._parse_game_id("2018_16_DEN_OAK") == (2018, 16, "DEN", "OAK")
    assert m._parse_game_id("2020_13_NO_ATL") == (2020, 13, "NO", "ATL")
