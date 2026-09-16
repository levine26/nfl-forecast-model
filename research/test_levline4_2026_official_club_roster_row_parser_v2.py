from pathlib import Path

from research.levline4_2026_official_club_roster_row_parser_v2 import (
    EXPECTED_HEADERS,
    PROJECTION_FIELDS,
    parse_team_rows,
    run_capture,
)


class FakeResponse:
    def __init__(self, url: str, *, status: int = 200, content: bytes = b"", headers=None):
        self.url = url
        self.status_code = status
        self.content = content
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}


def _table(rows: list[str], headers=EXPECTED_HEADERS) -> bytes:
    head = "".join(f"<th>{value}</th>" for value in headers)
    return (
        "<html><body><table><thead><tr>"
        + head
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></body></html>"
    ).encode()


def _row(i: int, *, name=None, jersey=None, position="WR", href=None, extra_href=None) -> str:
    name = name if name is not None else f"Player {i}"
    jersey = str(i % 100) if jersey is None else jersey
    href = href or f"/team/players-roster/player-{i}/"
    links = f'<a href="{href}">{name}</a>'
    if extra_href:
        links += f'<a href="{extra_href}">{name}</a>'
    cells = [links, jersey, position, "6-1", "200", "25", "3", "College"]
    return "<tr>" + "".join(f"<td>{value}</td>" for value in cells) + "</tr>"


def _valid_html(n: int = 50) -> bytes:
    return _table([_row(i) for i in range(n)])


def _parse(raw: bytes):
    return parse_team_rows(
        team="ARI",
        host="www.azcardinals.com",
        source_url="https://www.azcardinals.com/team/players-roster/",
        final_url="https://www.azcardinals.com/team/players-roster/",
        captured_at_utc="2026-09-16T17:30:00Z",
        raw=raw,
    )


def test_exact_header_and_projection_are_status_free():
    rows, diagnostic = _parse(_valid_html())
    assert diagnostic["parser_pass"] is True
    assert diagnostic["exact_header_tables"] == 1
    assert diagnostic["parsed_identity_rows"] == 50
    assert diagnostic["row_parse_errors"] == 0
    assert diagnostic["roster_section_or_status_selected"] is False
    assert diagnostic["roster_section_or_status_interpreted"] is False
    assert all(tuple(row) == PROJECTION_FIELDS for row in rows)
    forbidden = {"status", "roster_status", "section", "section_heading", "table_index", "injury_status", "starter"}
    assert all(not forbidden.intersection(row) for row in rows)


def test_wrong_header_is_not_fuzzily_accepted():
    headers = ("Player", "Number", "Position", "HT", "WT", "Age", "Exp", "College")
    rows, diagnostic = _parse(_table([_row(i) for i in range(50)], headers=headers))
    assert rows == []
    assert diagnostic["exact_header_tables"] == 0
    assert diagnostic["parser_pass"] is False


def test_malformed_width_is_a_hard_team_error():
    good = [_row(i) for i in range(49)]
    bad = "<tr>" + "".join(f"<td>{x}</td>" for x in ["Bad Player", "1", "WR", "6-0", "190", "24", "2"]) + "</tr>"
    rows, diagnostic = _parse(_table(good + [bad]))
    assert len(rows) == 49
    assert diagnostic["row_parse_errors"] == 1
    assert diagnostic["error_examples"][0]["kind"] == "row_width"
    assert diagnostic["parser_pass"] is False


def test_empty_player_or_position_is_a_hard_team_error():
    raw = _table([_row(i) for i in range(48)] + [_row(98, name=""), _row(99, position="")])
    rows, diagnostic = _parse(raw)
    assert len(rows) == 48
    assert {e["kind"] for e in diagnostic["error_examples"]} == {"empty_player_name", "empty_position"}
    assert diagnostic["parser_pass"] is False


def test_blank_jersey_is_preserved_but_not_repaired():
    rows, diagnostic = _parse(_table([_row(i) for i in range(49)] + [_row(99, jersey="")]))
    assert diagnostic["parser_pass"] is True
    assert diagnostic["blank_jersey_rows"] == 1
    blank = [row for row in rows if row["jersey_number_rendered"] == ""]
    assert len(blank) == 1


def test_duplicate_anchors_to_same_profile_collapse_to_one_url():
    raw = _table([_row(i) for i in range(49)] + [_row(99, extra_href="/team/players-roster/player-99/")])
    rows, diagnostic = _parse(raw)
    assert diagnostic["parser_pass"] is True
    assert len(rows) == 50


def test_two_different_profile_urls_in_one_row_fail_closed():
    raw = _table([_row(i) for i in range(49)] + [_row(99, extra_href="/team/players-roster/different-99/")])
    rows, diagnostic = _parse(raw)
    assert len(rows) == 49
    assert diagnostic["error_examples"][0]["kind"] == "profile_url_cardinality"
    assert diagnostic["parser_pass"] is False


def test_off_host_profile_link_fails_closed():
    raw = _table([_row(i) for i in range(49)] + [_row(99, href="https://evil.example/team/players-roster/player-99/")])
    rows, diagnostic = _parse(raw)
    assert len(rows) == 49
    kinds = {e["kind"] for e in diagnostic["error_examples"]}
    assert "off_host_profile_url" in kinds
    assert "profile_url_cardinality" in kinds
    assert diagnostic["parser_pass"] is False


def test_duplicate_profile_url_within_team_is_a_hard_error():
    raw = _table([_row(i) for i in range(49)] + [_row(99, href="/team/players-roster/player-1/")])
    rows, diagnostic = _parse(raw)
    assert len(rows) == 49
    assert diagnostic["duplicate_profile_urls"] == 1
    assert diagnostic["parser_pass"] is False


def test_full_fake_32_team_capture_meets_frozen_mechanical_gate_but_grants_no_authority(tmp_path: Path):
    html = _valid_html()

    def fake_get(url, **kwargs):
        return FakeResponse(url, content=html)

    receipt = run_capture(tmp_path, get=fake_get)
    assert receipt["status"] == "PASS"
    assert receipt["http_success_team_count"] == 32
    assert receipt["team_parser_pass_count"] == 32
    assert receipt["parsed_identity_rows"] == 1600
    assert receipt["minimum_rows_observed_per_team"] == 50
    assert receipt["total_row_parse_errors"] == 0
    assert receipt["duplicate_profile_urls"] == 0
    assert receipt["parser_qualification_gate_pass"] is True
    assert receipt["real_execution_is_self_qualifying"] is False
    assert receipt["official_club_roster_identity_row_parser_qualified"] is False
    assert receipt["underlying_source_independence_from_nflverse_established"] is False
    for key in (
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified",
        "general_2026_player_identity_to_gsis_qualified",
        "game_day_membership_qualified",
        "availability_state_authorized",
        "availability_probability_authorized",
        "player_value_join_authorized",
        "forecast_probability_effect_authorized",
        "model_fit_authorized",
        "production_authorized",
    ):
        assert receipt[key] is False
    assert receipt["completed_2026_outcomes_used_for_design_or_selection"] == 0
    assert receipt["postgame_participation_used"] is False
    assert receipt["f_st_01_frozen_2026_unchanged"] is True


def test_one_team_failure_fails_full_capture_and_is_preserved(tmp_path: Path):
    html = _valid_html()

    def fake_get(url, **kwargs):
        if "azcardinals.com" in url:
            return FakeResponse(url, content=b"<html><body>no roster table</body></html>")
        return FakeResponse(url, content=html)

    receipt = run_capture(tmp_path, get=fake_get)
    assert receipt["status"] == "FAIL"
    assert receipt["http_success_team_count"] == 32
    assert receipt["team_parser_pass_count"] == 31
    assert receipt["parser_qualification_gate_pass"] is False
    assert (tmp_path / "receipt.json").is_file()
    assert (tmp_path / "team_parser_diagnostics.json").is_file()
    assert len(list((tmp_path / "raw").glob("*.html"))) == 32
