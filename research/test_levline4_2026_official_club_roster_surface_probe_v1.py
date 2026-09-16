from pathlib import Path

import pytest

from research.levline4_2026_official_club_roster_surface_probe_v1 import (
    diagnose_html,
    host_allowed,
    request_with_frozen_redirects,
    run_capture,
)


class FakeResponse:
    def __init__(self, url: str, *, status: int = 200, content: bytes = b"", headers=None):
        self.url = url
        self.status_code = status
        self.content = content
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}


HTML = b"""
<html><head>
<script id="__NEXT_DATA__" type="application/json">{}</script>
<script type="application/ld+json">{}</script>
</head><body>
<table><thead><tr><th>Player</th><th>#</th><th>Pos</th></tr></thead></table>
<a href="/team/players-roster/jane-doe/">Jane Doe</a>
<a href="/team/players-roster/john-smith">John Smith</a>
<a href="/news/not-a-player">Ignore</a>
</body></html>
"""


def test_host_allowlist_accepts_only_https_www_variant():
    assert host_allowed("https://www.example.com/team/players-roster/", "www.example.com")
    assert host_allowed("https://example.com/team/players-roster/", "www.example.com")
    assert not host_allowed("http://www.example.com/team/players-roster/", "www.example.com")
    assert not host_allowed("https://evil.example.net/team/players-roster/", "www.example.com")


def test_redirects_fail_closed_when_host_changes():
    def fake_get(url, **kwargs):
        return FakeResponse(url, status=302, headers={"Location": "https://evil.example.net/pwn"})

    with pytest.raises(RuntimeError, match="disallowed_redirect_host"):
        request_with_frozen_redirects(
            "https://www.example.com/team/players-roster/",
            "www.example.com",
            get=fake_get,
        )


def test_same_host_redirect_is_allowed():
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(url, status=301, headers={"Location": "https://example.com/team/players-roster/"})
        return FakeResponse(url, content=HTML)

    result = request_with_frozen_redirects(
        "https://www.example.com/team/players-roster/",
        "www.example.com",
        get=fake_get,
    )
    assert result.status_code == 200
    assert result.url == "https://example.com/team/players-roster/"
    assert result.content == HTML


def test_diagnostics_are_structural_only():
    diagnostic = diagnose_html(
        "ARI",
        "https://www.azcardinals.com/team/players-roster/",
        "https://www.azcardinals.com/team/players-roster/",
        "2026-09-16T00:00:00Z",
        HTML,
    )
    assert diagnostic["unique_profile_url_count"] == 2
    assert diagnostic["surface_presence"] is True
    assert diagnostic["tables_with_player_number_position_headers"] == 1
    assert diagnostic["next_data_script_present"] is True
    assert diagnostic["json_ld_script_count"] == 1
    assert {row["anchor_text"] for row in diagnostic["profile_links"]} == {"Jane Doe", "John Smith"}
    assert all(set(row) == {
        "team", "profile_url", "anchor_text", "source_url", "final_url", "captured_at_utc", "raw_html_sha256"
    } for row in diagnostic["profile_links"])


def test_full_fake_capture_requires_all_32_and_preserves_authority_firewall(tmp_path: Path):
    def fake_get(url, **kwargs):
        return FakeResponse(url, content=HTML)

    receipt = run_capture(tmp_path, get=fake_get)
    assert receipt["status"] == "PASS"
    assert receipt["expected_team_count"] == 32
    assert receipt["captured_team_count"] == 32
    assert receipt["http_success_team_count"] == 32
    assert receipt["surface_presence_team_count"] == 32
    assert receipt["profile_link_rows"] == 64
    assert len(list((tmp_path / "raw").glob("*.html"))) == 32
    assert (tmp_path / "team_diagnostics.json").is_file()
    assert (tmp_path / "profile_links.jsonl").is_file()
    assert (tmp_path / "receipt.json").is_file()
    for key in (
        "name_jersey_position_parser_qualified",
        "official_club_roster_identity_parser_qualified",
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified",
        "general_2026_player_identity_to_gsis_qualified",
        "game_day_membership_qualified",
        "availability_state_authorized",
        "player_value_join_authorized",
        "forecast_probability_effect_authorized",
        "model_fit_authorized",
        "production_authorized",
    ):
        assert receipt[key] is False
    assert receipt["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert receipt["postgame_participation_used"] is False
    assert receipt["f_st_01_frozen_2026_unchanged"] is True


def test_failure_is_recorded_instead_of_silently_dropping_team(tmp_path: Path):
    def fake_get(url, **kwargs):
        if "azcardinals.com" in url:
            raise OSError("synthetic network failure")
        return FakeResponse(url, content=HTML)

    receipt = run_capture(tmp_path, get=fake_get)
    assert receipt["status"] == "FAIL"
    assert receipt["captured_team_count"] == 31
    assert receipt["capture_complete"] is False
    assert receipt["official_club_roster_surface_capture_qualified"] is False
    assert receipt["errors"][0]["team"] == "ARI"
    assert (tmp_path / "receipt.json").is_file()
