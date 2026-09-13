from __future__ import annotations

import json
from pathlib import Path

from research.v09b_modern_media_subdomain_discovery_v2 import (
    candidate_rows_from_urls,
    candidate_target_allowed,
    extract_html_candidates,
    extract_xml_locs,
    host_in_team_family,
    signal_match,
    unresolved_pairs,
)


def test_team_domain_family_is_bounded() -> None:
    assert host_in_team_family("media.denverbroncos.com", "denverbroncos.com") is True
    assert host_in_team_family("www.denverbroncos.com", "denverbroncos.com") is True
    assert host_in_team_family("denverbroncos.com.evil.example", "denverbroncos.com") is False
    assert host_in_team_family("otherteam.com", "denverbroncos.com") is False


def test_candidate_target_allows_team_family_and_static_clubs_only() -> None:
    assert candidate_target_allowed("https://media.denverbroncos.com/foo", "denverbroncos.com") is True
    assert candidate_target_allowed("https://static.clubs.nfl.com/image/upload/broncos/x.pdf", "denverbroncos.com") is True
    assert candidate_target_allowed("http://media.denverbroncos.com/foo", "denverbroncos.com") is False
    assert candidate_target_allowed("https://example.com/foo", "denverbroncos.com") is False


def test_signal_match_requires_season_and_document_signal() -> None:
    terms = ["WEEKLY RELEASE", "ROSTER", "DEPTH CHART"]
    assert signal_match("2019 Denver Broncos Weekly Release", 2019, terms) is True
    assert signal_match("Denver Broncos Weekly Release", 2019, terms) is False
    assert signal_match("2019 Denver Broncos schedule", 2019, terms) is False


def test_html_candidate_extraction_is_first_party_and_season_scoped() -> None:
    html = """
    <a href='/2019/12/weekly-release-week-17'>2019 Weekly Release</a>
    <a href='https://static.clubs.nfl.com/image/upload/broncos/2019-roster.pdf'>2019 Roster</a>
    <a href='https://example.com/2019-depth-chart.pdf'>2019 Depth Chart</a>
    <a href='/2020/12/weekly-release'>2020 Weekly Release</a>
    """
    rows = extract_html_candidates(
        html,
        page_url="https://media.denverbroncos.com/",
        base_domain="denverbroncos.com",
        seasons=[2019],
        terms=["WEEKLY RELEASE", "ROSTER", "DEPTH CHART"],
    )
    assert len(rows) == 2
    assert all(row["season"] == 2019 for row in rows)
    assert not any("example.com" in row["url"] for row in rows)


def test_sitemap_parser_and_url_candidates() -> None:
    xml = """<?xml version='1.0'?>
    <urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>
      <url><loc>https://media.denverbroncos.com/2019/12/weekly-release-week-17/</loc></url>
      <url><loc>https://media.denverbroncos.com/2020/01/news/</loc></url>
    </urlset>
    """
    kind, urls = extract_xml_locs(xml)
    assert kind == "urlset"
    assert len(urls) == 2
    rows = candidate_rows_from_urls(
        urls,
        base_domain="denverbroncos.com",
        seasons=[2019],
        terms=["WEEKLY RELEASE", "ROSTER", "DEPTH CHART"],
        method="sitemap",
    )
    assert len(rows) == 1
    assert rows[0]["season"] == 2019


def test_contract_has_exact_153_unresolved_pairs() -> None:
    contract_path = Path("research/availability/v09b_modern_media_subdomain_discovery_v2_contract.json")
    contract = json.loads(contract_path.read_text())
    pairs = unresolved_pairs(contract)
    assert len(pairs) == 153
    keys = {f"{team}|{season}" for team, season in pairs}
    assert "NE|2017" not in keys
    assert "TB|2020" not in keys
    assert "TB|2019" in keys
    assert "DEN|2019" in keys


def test_authority_firewall_is_explicit_in_contract() -> None:
    contract = json.loads(Path("research/availability/v09b_modern_media_subdomain_discovery_v2_contract.json").read_text())
    assert contract["explicit_non_gates"]["discovery_rate_threshold"] is None
    assert contract["explicit_non_gates"]["all_2592_team_game_partitions_tested"] is False
    assert contract["authority"]["diagnostic_has_locator_qualification_authority"] is False
    assert contract["authority"]["modern_game_day_roster_universe_qualified"] is False
    assert contract["authority"]["v09b_model_fit_authorized"] is False
    assert contract["governance"]["weekly_roster_status_used"] is False
    assert contract["governance"]["absence_from_inactive_used_as_positive"] is False
