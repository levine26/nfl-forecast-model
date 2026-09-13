from __future__ import annotations

from research.v09b_modern_club_archive_surface_discovery_v1 import (
    allowed_team_hosts,
    build_tasks,
    inspect_archive_html,
    valid_roster_depth_anchor,
)


def test_allowed_team_hosts_adds_www_variant() -> None:
    assert allowed_team_hosts(["patriots.com"]) == {"patriots.com", "www.patriots.com"}
    assert allowed_team_hosts(["www.buccaneers.com"]) == {"buccaneers.com", "www.buccaneers.com"}


def test_static_clubs_roster_depth_anchor_is_accepted() -> None:
    row = valid_roster_depth_anchor(
        text="Rosters & Depth",
        href="https://static.clubs.nfl.com/image/upload/patriots/example.pdf",
        page_url="https://www.patriots.com/press-room/mediasite/game-packages-2020",
        team_hosts={"patriots.com", "www.patriots.com"},
    )
    assert row is not None
    assert row["host"] == "static.clubs.nfl.com"


def test_same_team_https_roster_depth_anchor_is_accepted() -> None:
    row = valid_roster_depth_anchor(
        text="Roster and Depth Chart",
        href="/media/roster-depth.pdf",
        page_url="https://www.buccaneers.com/media/weekly-information-2021",
        team_hosts={"buccaneers.com", "www.buccaneers.com"},
    )
    assert row is not None
    assert row["url"] == "https://www.buccaneers.com/media/roster-depth.pdf"


def test_third_party_or_incomplete_visible_text_is_rejected() -> None:
    hosts = {"patriots.com", "www.patriots.com"}
    assert valid_roster_depth_anchor(
        text="Rosters & Depth",
        href="https://example.com/roster.pdf",
        page_url="https://www.patriots.com/press-room/mediasite/game-packages-2020",
        team_hosts=hosts,
    ) is None
    assert valid_roster_depth_anchor(
        text="Rosters",
        href="https://static.clubs.nfl.com/image/upload/patriots/example.pdf",
        page_url="https://www.patriots.com/press-room/mediasite/game-packages-2020",
        team_hosts=hosts,
    ) is None


def test_archive_hit_requires_season_text_and_roster_depth_anchor() -> None:
    page = "https://www.patriots.com/press-room/mediasite/game-packages-2020"
    hosts = {"patriots.com", "www.patriots.com"}
    html = '<html><body><h1>2020 Game Packages</h1><a href="https://static.clubs.nfl.com/image/upload/patriots/example.pdf">Rosters &amp; Depth</a></body></html>'
    result = inspect_archive_html(html, page_url=page, season=2020, team_hosts=hosts)
    assert result["season_text_present"] is True
    assert result["roster_depth_anchor_count"] == 1
    assert result["archive_surface_hit"] is True

    missing_season = inspect_archive_html(
        '<a href="https://static.clubs.nfl.com/image/upload/patriots/example.pdf">Rosters &amp; Depth</a>',
        page_url=page,
        season=2020,
        team_hosts=hosts,
    )
    assert missing_season["season_text_present"] is False
    assert missing_season["roster_depth_anchor_count"] == 1
    assert missing_season["archive_surface_hit"] is False


def test_build_tasks_is_deterministic_for_synthetic_contract() -> None:
    contract = {
        "teams": {
            "NE": ["patriots.com"],
            "WAS": ["commanders.com", "washingtonfootball.com"],
        },
        "seasons": [2020, 2021],
        "standardized_path_candidates": [
            "/media/weekly-information-{season}",
            "/press-room/game-packages-{season}",
        ],
    }
    tasks = build_tasks(contract)
    assert len(tasks) == 12
    assert tasks[0] == {
        "team": "NE",
        "season": 2020,
        "team_domains": ["patriots.com"],
        "base_domain": "patriots.com",
        "path_template": "/media/weekly-information-{season}",
        "url": "https://www.patriots.com/media/weekly-information-2020",
    }
    assert tasks[-1]["team"] == "WAS"
    assert tasks[-1]["season"] == 2021
    assert tasks[-1]["url"] == "https://www.washingtonfootball.com/press-room/game-packages-2021"
