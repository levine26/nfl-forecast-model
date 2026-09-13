from __future__ import annotations

from research.v09b_modern_game_day_media_surface_discovery_v1 import (
    canonical_regular_game_base,
    classify_media_anchor,
    extract_first_party_media_links,
    extract_schedule_game_bases,
    team_hosts,
)


def test_team_hosts_adds_www_variants() -> None:
    assert team_hosts(["azcardinals.com"]) == {"azcardinals.com", "www.azcardinals.com"}


def test_regular_game_base_accepts_reg_week_and_week_shapes() -> None:
    hosts = {"azcardinals.com", "www.azcardinals.com"}
    assert canonical_regular_game_base(
        "/game-day/2021/week1/cardinals-at-titans/scoring-summary",
        page_url="https://www.azcardinals.com/schedule/2021/",
        season=2021,
        allowed_hosts=hosts,
    ) == "https://www.azcardinals.com/game-day/2021/week1/cardinals-at-titans/"
    assert canonical_regular_game_base(
        "/game-day/2021/reg-week17/rams-at-ravens/media",
        page_url="https://www.azcardinals.com/schedule/2021/",
        season=2021,
        allowed_hosts=hosts,
    ) == "https://www.azcardinals.com/game-day/2021/reg-week17/rams-at-ravens/"


def test_nonregular_or_wrong_host_game_links_are_rejected() -> None:
    hosts = {"baltimoreravens.com", "www.baltimoreravens.com"}
    assert canonical_regular_game_base(
        "/game-day/2021/pre-week1/saints-at-ravens/",
        page_url="https://www.baltimoreravens.com/schedule/2021/",
        season=2021,
        allowed_hosts=hosts,
    ) is None
    assert canonical_regular_game_base(
        "https://example.com/game-day/2021/reg-week1/ravens-at-raiders/",
        page_url="https://www.baltimoreravens.com/schedule/2021/",
        season=2021,
        allowed_hosts=hosts,
    ) is None


def test_schedule_game_bases_deduplicate_subpages() -> None:
    html = """
    <a href='/game-day/2021/reg-week1/ravens-at-raiders/'>Game</a>
    <a href='/game-day/2021/reg-week1/ravens-at-raiders/scoring-summary'>Score</a>
    <a href='/game-day/2021/reg-week2/chiefs-at-ravens/'>Game 2</a>
    <a href='/game-day/2021/pre-week1/saints-at-ravens/'>Preseason</a>
    """
    values = extract_schedule_game_bases(
        html,
        page_url="https://www.baltimoreravens.com/schedule/2021/",
        season=2021,
        allowed_hosts={"baltimoreravens.com", "www.baltimoreravens.com"},
    )
    assert values == [
        "https://www.baltimoreravens.com/game-day/2021/reg-week1/ravens-at-raiders/",
        "https://www.baltimoreravens.com/game-day/2021/reg-week2/chiefs-at-ravens/",
    ]


def test_media_anchor_classification_can_report_roster_and_depth_together() -> None:
    assert classify_media_anchor("GAME RELEASE") == ["game_release"]
    assert classify_media_anchor("ROSTER AND DEPTH CHART") == ["roster", "depth_chart"]
    assert classify_media_anchor("FLIP CARD") == ["flip_card"]
    assert classify_media_anchor("Unrelated") == []


def test_media_links_require_first_party_https_targets() -> None:
    html = """
    <a href='https://static.clubs.nfl.com/image/upload/cardinals/release.pdf'>GAME RELEASE</a>
    <a href='/team/players-roster.pdf'>ROSTER</a>
    <a href='https://example.com/depth.pdf'>DEPTH CHART</a>
    <a href='http://static.clubs.nfl.com/card.pdf'>FLIP CARD</a>
    """
    result = extract_first_party_media_links(
        html,
        page_url="https://www.azcardinals.com/game-day/2021/week1/cardinals-at-titans/",
        allowed_hosts={"azcardinals.com", "www.azcardinals.com"},
    )
    assert len(result["game_release"]) == 1
    assert len(result["roster"]) == 1
    assert result["depth_chart"] == []
    assert result["flip_card"] == []
