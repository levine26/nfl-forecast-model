from __future__ import annotations

import json
from pathlib import Path

from research.v09b_modern_delegated_media_host_discovery_v3 import (
    candidates_from_urls,
    exact_https_host,
    extract_html_candidates,
    signal_match,
    xml_locs,
)


def test_exact_delegated_host_is_strict() -> None:
    assert exact_https_host("https://browns.1rmg.com/foo", "browns.1rmg.com") is True
    assert exact_https_host("http://browns.1rmg.com/foo", "browns.1rmg.com") is False
    assert exact_https_host("https://evil.browns.1rmg.com/foo", "browns.1rmg.com") is False
    assert exact_https_host("https://1rmg.com/foo", "browns.1rmg.com") is False


def test_signal_match_requires_real_candidate_text_not_query_context() -> None:
    terms = ["WEEKLY RELEASE", "GAME RELEASE", "ROSTER", "DEPTH CHART"]
    assert signal_match("2019 Week 4 Game Release", 2019, terms) is True
    assert signal_match("2019 Draft Notes", 2019, terms) is False
    assert signal_match("Week 4 Game Release", 2019, terms) is False


def test_html_candidate_extraction_stays_on_exact_delegated_host() -> None:
    html = """
    <a href='/2019/week-4-game-release'>2019 Week 4 Game Release</a>
    <a href='https://other.1rmg.com/2019/week-4-game-release'>2019 Week 4 Game Release</a>
    <a href='/2019/draft-notes'>2019 Draft Notes</a>
    """
    rows = extract_html_candidates(
        html,
        page_url="https://browns.1rmg.com/",
        delegated_host="browns.1rmg.com",
        seasons=[2019],
        terms=["WEEKLY RELEASE", "GAME RELEASE", "ROSTER", "DEPTH CHART"],
    )
    assert len(rows) == 1
    assert rows[0]["url"] == "https://browns.1rmg.com/2019/week-4-game-release"


def test_sitemap_candidates_require_exact_host_season_and_signal() -> None:
    xml = """<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://eagles.1rmg.com/2020/week-2-roster/</loc></url>
      <url><loc>https://eagles.1rmg.com/2020/draft-notes/</loc></url>
      <url><loc>https://other.1rmg.com/2020/week-2-roster/</loc></url>
    </urlset>"""
    kind, urls = xml_locs(xml)
    assert kind == "urlset"
    rows = candidates_from_urls(
        urls,
        delegated_host="eagles.1rmg.com",
        seasons=[2020],
        terms=["ROSTER", "DEPTH CHART", "GAME RELEASE"],
        method="sitemap",
    )
    assert len(rows) == 1
    assert rows[0]["url"] == "https://eagles.1rmg.com/2020/week-2-roster/"


def test_contract_freezes_exact_three_observed_delegations_and_no_authority() -> None:
    c = json.loads(Path("research/availability/v09b_modern_delegated_media_host_discovery_v3_contract.json").read_text())
    assert len(c["fixed_delegations"]) == 3
    assert [x["team"] for x in c["fixed_delegations"]] == ["CLE", "DEN", "PHI"]
    assert [x["expected_delegated_host"] for x in c["fixed_delegations"]] == ["browns.1rmg.com", "nfl.omgsports.com", "eagles.1rmg.com"]
    assert c["delegation_requirements"]["unobserved_vendor_hosts_forbidden"] is True
    assert c["delegation_requirements"]["delegation_does_not_create_source_authority"] is True
    assert c["explicit_non_gates"]["delegated_host_is_first_party_authority"] is False
    assert c["authority"]["diagnostic_has_source_qualification_authority"] is False
    assert c["authority"]["modern_game_day_roster_universe_qualified"] is False
    assert c["authority"]["v09b_model_fit_authorized"] is False
