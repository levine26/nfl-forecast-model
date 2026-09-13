from __future__ import annotations

import json
from pathlib import Path

from research.v09b_modern_constructed_game_day_url_v2 import (
    candidate_urls,
    classify_media,
    page_signals_pass,
    parse_game_id,
    team_hosts,
)


def contract() -> dict:
    return json.loads(Path("research/availability/v09b_modern_constructed_game_day_url_v2_contract.json").read_text())


def test_game_id_parser_preserves_historical_team_codes() -> None:
    assert parse_game_id("2017_01_OAK_TEN") == (2017, 1, "OAK", "TEN")
    assert parse_game_id("2021_10_TB_WAS") == (2021, 10, "TB", "WAS")


def test_ravens_observed_cms_url_is_first_candidate_shape() -> None:
    c = contract()
    urls = candidate_urls(team="BAL", season=2019, week=2, away="ARI", home="BAL", contract=c)
    assert urls[0] == "https://www.baltimoreravens.com/game-day/2019/reg-week2/cardinals-at-ravens/"
    assert "https://www.baltimoreravens.com/game-day/2019/week2/cardinals-at-ravens/" in urls


def test_historical_raiders_code_maps_to_raiders_slug_and_domain() -> None:
    c = contract()
    urls = candidate_urls(team="OAK", season=2017, week=1, away="OAK", home="TEN", contract=c)
    assert urls[0] == "https://www.raiders.com/game-day/2017/reg-week1/raiders-at-titans/"


def test_washington_variants_are_bounded_and_explicit() -> None:
    c = contract()
    urls = candidate_urls(team="WAS", season=2021, week=10, away="TB", home="WAS", contract=c)
    assert any("buccaneers-at-redskins" in u for u in urls)
    assert any("buccaneers-at-washington-football-team" in u for u in urls)
    assert all("example" not in u for u in urls)


def test_page_signal_requires_week_and_both_teams() -> None:
    c = contract()
    ok, detail = page_signals_pass(
        "Week 2: Arizona Cardinals at Baltimore Ravens",
        week=2,
        away="ARI",
        home="BAL",
        signals=c["team_visible_signals"],
    )
    assert ok is True
    assert detail == {"week": True, "away": True, "home": True}
    bad, _ = page_signals_pass("Week 2 Baltimore Ravens", week=2, away="ARI", home="BAL", signals=c["team_visible_signals"])
    assert bad is False


def test_media_classification_does_not_promote_generic_links() -> None:
    c = contract()
    assert classify_media("GAME RELEASE", c["media_classes"]) == ["game_release"]
    assert "depth_chart" in classify_media("DEPTH CHART", c["media_classes"])
    assert classify_media("News and Videos", c["media_classes"]) == []


def test_domain_allowlist_is_team_bounded() -> None:
    hosts = team_hosts(["baltimoreravens.com"])
    assert "baltimoreravens.com" in hosts
    assert "www.baltimoreravens.com" in hosts
    assert "ravenspr.com" not in hosts


def test_contract_freezes_no_coverage_threshold_or_authority() -> None:
    c = contract()
    assert c["expected_games_total"] == 1296
    assert c["expected_team_partitions_total"] == 2592
    assert c["cms_grammar"]["stage_variants_in_frozen_order"] == ["reg-week{week}", "week{week}"]
    assert c["explicit_non_gates"]["constructed_page_coverage_threshold"] is None
    assert c["authority"]["diagnostic_has_locator_qualification_authority"] is False
    assert c["authority"]["modern_game_day_roster_universe_qualified"] is False
    assert c["authority"]["v09b_model_fit_authorized"] is False
    assert c["governance"]["completed_2026_outcomes_used"] == 0
