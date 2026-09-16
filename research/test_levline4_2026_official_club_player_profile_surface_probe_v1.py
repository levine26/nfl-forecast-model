from __future__ import annotations

from dataclasses import dataclass

import pytest

from research import levline4_2026_official_club_player_profile_surface_probe_v1 as probe


def _contract() -> dict:
    return {
        "diagnostics_only": {
            "literal_token_patterns": [
                "gsis",
                "playerid",
                "player_id",
                "player-id",
                "nflid",
                "nfl_id",
                "nfl-id",
                "personid",
                "person_id",
                "person-id",
                "athleteid",
                "athlete_id",
                "athlete-id",
                "sportradar",
                "espn",
            ],
            "maximum_attribute_samples_per_name": 10,
        }
    }


def _row(team: str, slug: str, name: str | None = None) -> dict:
    return {
        "team": team,
        "visible_name": name or slug.replace("-", " ").title(),
        "profile_path": f"/team/players-roster/{slug}/",
        "final_url": f"https://{team.lower()}.example.com/team/players-roster/",
        "raw_html_sha256": "a" * 64,
    }


def test_select_profiles_uses_frozen_lexicographic_rule_for_all_32_teams() -> None:
    rows = []
    for i in range(32):
        team = f"T{i:02d}"
        rows.extend([_row(team, "z-player"), _row(team, "a-player")])
    selected = probe.select_profiles(rows)
    assert len(selected) == 32
    assert [row["team"] for row in selected] == sorted(row["team"] for row in selected)
    assert all(row["profile_path"] == "/team/players-roster/a-player/" for row in selected)
    assert all(row["profile_url"].endswith("/team/players-roster/a-player/") for row in selected)


def test_select_profiles_fails_closed_on_nonunique_minimum_profile_path() -> None:
    rows = []
    for i in range(32):
        team = f"T{i:02d}"
        rows.append(_row(team, "a-player"))
    rows.append(_row("T00", "a-player", "Duplicate"))
    with pytest.raises(RuntimeError, match="nonunique_minimum_profile_path:T00"):
        probe.select_profiles(rows)


def test_diagnostics_record_identifier_candidates_without_qualifying_them() -> None:
    raw = b"""
    <html><head>
      <link rel="canonical" href="https://club.example.com/team/players-roster/example/">
      <script id="__NEXT_DATA__" type="application/json">{"gsis":"00-1234567","espn_id":"42"}</script>
      <script type="application/ld+json">{"name":"Example"}</script>
    </head><body>
      <div data-player-id="abc123" data-person_id="person-9" id="bio">Example</div>
    </body></html>
    """
    result = probe.diagnose_profile_html(raw, contract=_contract())
    assert result["gsis_like_values"] == ["00-1234567"]
    assert result["literal_token_counts"]["gsis"] == 1
    assert result["literal_token_counts"]["espn"] == 1
    assert result["id_like_attribute_name_counts"]["data-player-id"] == 1
    assert result["id_like_attribute_name_counts"]["data-person_id"] == 1
    assert result["next_data_script_present"] is True
    assert result["json_ld_script_count"] == 1
    assert result["canonical_links"] == ["https://club.example.com/team/players-roster/example/"]
    assert "official_stable_player_identifier_exposed_qualified" not in result
    assert "player_identity_to_gsis_qualified" not in result


@dataclass
class _FakeResponse:
    status_code: int
    url: str
    content: bytes
    headers: dict[str, str]


def test_capture_profile_accepts_only_same_frozen_host() -> None:
    selected = {
        "team": "T00",
        "visible_name": "A Player",
        "profile_path": "/team/players-roster/a-player/",
        "profile_url": "https://t00.example.com/team/players-roster/a-player/",
        "host": "t00.example.com",
        "roster_page_final_url": "https://t00.example.com/team/players-roster/",
        "roster_page_raw_html_sha256": "a" * 64,
    }

    def good_get(url: str, **_: object) -> _FakeResponse:
        return _FakeResponse(200, url, b"<html><body>profile</body></html>", {"Content-Type": "text/html"})

    diagnostic, raw = probe.capture_profile(selected, contract=_contract(), get=good_get)
    assert raw.startswith(b"<html>")
    assert diagnostic["http_success"] is True
    assert diagnostic["final_url"] == selected["profile_url"]

    def bad_redirect_get(url: str, **_: object) -> _FakeResponse:
        return _FakeResponse(302, url, b"", {"Location": "https://evil.example.net/player"})

    with pytest.raises(RuntimeError, match="disallowed_redirect_host"):
        probe.capture_profile(selected, contract=_contract(), get=bad_redirect_get)
