from __future__ import annotations

import json
from pathlib import Path

from research import levline4_2026_official_club_roster_parser_v2 as mod


class FakeResponse:
    def __init__(self, url: str, html: str, status_code: int = 200):
        self.status_code = status_code
        self.url = url
        self.headers = {"Content-Type": "text/html"}
        self.content = html.encode("utf-8")


def roster_html(rows: int = 70, *, empty_jersey_at: int | None = None, duplicate: bool = False, bad_position_at: int | None = None) -> str:
    body = []
    for i in range(rows):
        slug_index = 0 if duplicate and i == rows - 1 else i
        jersey = "" if empty_jersey_at == i else str((i % 99) + 1)
        position = "" if bad_position_at == i else "WR"
        body.append(
            f"""
            <tr>
              <td><span class='nfl-o-roster__player-name' data-name='player{i},test'>
                <a href='/team/players-roster/test-player-{slug_index}/'>Test Player {i}</a>
              </span></td>
              <td>{jersey}</td><td>{position}</td><td>6-0</td><td>200</td><td>25</td><td>2</td><td>College</td>
            </tr>
            """
        )
    return f"""
    <html><body>
      <a href='/team/players-roster/promotional-player/'>Promotional Player</a>
      <h2>Practice Squad</h2>
      <table><thead><tr>
        <th>Player</th><th>#</th><th>Pos</th><th>HT</th><th>WT</th><th>Age</th><th>Exp</th><th>College</th>
      </tr></thead><tbody>{''.join(body)}</tbody></table>
    </body></html>
    """


def parse(html: str):
    return mod.parse_team_html(
        team="ARI",
        source_url="https://www.azcardinals.com/team/players-roster/",
        final_url="https://www.azcardinals.com/team/players-roster/",
        captured_at_utc="2026-09-16T18:00:00Z",
        raw_html=html.encode("utf-8"),
    )


def test_contract_freezes_narrow_authority():
    contract = mod.load_contract()
    assert contract["discovery_evidence"]["discovery_only_not_validation"] is True
    assert contract["frozen_parser"]["minimum_parsed_rows_per_team"] == 70
    assert contract["forbidden_semantics"]["roster_section_name_interpreted"] is False
    assert contract["authority_if_gate_passes"]["official_club_roster_metadata_parser_qualified"] is True
    assert contract["authority_if_gate_passes"]["official_club_roster_source_is_independent_gsis_ground_truth"] is False
    assert contract["authority_if_gate_passes"]["player_identity_to_gsis_qualified"] is False
    assert contract["authority_if_gate_passes"]["production_authorized"] is False
    assert contract["governance"]["completed_2026_outcomes_used_for_design_or_selection"] == 0


def test_parser_uses_only_exact_roster_table_rows_and_discards_status_semantics():
    rows, diagnostics = parse(roster_html(70, empty_jersey_at=3))
    assert diagnostics["parser_team_gate_pass"] is True
    assert diagnostics["parsed_row_count"] == 70
    assert diagnostics["empty_jersey_row_count"] == 1
    assert len(rows) == 70
    assert all("Promotional Player" not in row["visible_name"] for row in rows)
    assert rows[0]["profile_path"] == "/team/players-roster/test-player-0/"
    assert rows[0]["position"] == "WR"
    assert set(rows[0]) == {
        "team",
        "visible_name",
        "canonical_data_name",
        "jersey_number",
        "position",
        "profile_path",
        "source_url",
        "final_url",
        "captured_at_utc",
        "raw_html_sha256",
    }
    forbidden = {"status", "section", "injury", "starter", "depth_role", "height", "weight", "age", "experience", "college"}
    assert not forbidden.intersection(rows[0])


def test_duplicate_profile_path_fails_team_gate_without_manual_rescue():
    rows, diagnostics = parse(roster_html(70, duplicate=True))
    assert len(rows) == 70
    assert diagnostics["duplicate_profile_path_count"] == 1
    assert diagnostics["parser_team_gate_pass"] is False


def test_missing_position_is_error_and_cannot_pass():
    rows, diagnostics = parse(roster_html(70, bad_position_at=4))
    assert len(rows) == 69
    assert diagnostics["parse_error_count"] == 1
    assert diagnostics["parse_errors"][0]["error"] == "empty_position"
    assert diagnostics["parser_team_gate_pass"] is False


def test_wrong_row_shape_is_preserved_as_error():
    html = """
    <table><tr><th>Player</th><th>#</th><th>Pos</th><th>HT</th><th>WT</th><th>Age</th><th>Exp</th><th>College</th></tr>
    <tr><td><span class='nfl-o-roster__player-name' data-name='doe,jane'><a href='/team/players-roster/jane-doe/'>Jane Doe</a></span></td><td>1</td><td>QB</td></tr></table>
    """
    rows, diagnostics = parse(html)
    assert rows == []
    assert diagnostics["parse_error_count"] == 1
    assert diagnostics["parse_errors"][0]["error"] == "row_cell_count_not_8"
    assert diagnostics["parser_team_gate_pass"] is False


def test_nonexact_header_table_is_not_parsed():
    html = roster_html(70).replace("<th>College</th>", "<th>School</th>")
    rows, diagnostics = parse(html)
    assert rows == []
    assert diagnostics["exact_roster_table_count"] == 0
    assert diagnostics["parser_team_gate_pass"] is False


def test_full_synthetic_32_team_gate_passes_and_never_grants_gsis_authority(tmp_path: Path):
    html = roster_html(70)

    def fake_get(url: str, **kwargs):
        return FakeResponse(url, html)

    receipt = mod.run_held_out_capture(tmp_path / "out", get=fake_get)
    assert receipt["status"] == "PASS"
    assert receipt["captured_team_count"] == 32
    assert receipt["parser_gate_pass_team_count"] == 32
    assert receipt["parsed_row_count"] == 32 * 70
    assert receipt["minimum_parsed_rows_observed"] == 70
    assert receipt["held_out_parser_gate_pass"] is True
    assert receipt["official_club_roster_metadata_parser_qualified"] is True
    assert receipt["official_club_roster_source_is_independent_gsis_ground_truth"] is False
    assert receipt["player_identity_to_gsis_qualified"] is False
    assert receipt["week2_sunday_due_inactive_player_identity_to_gsis_qualified"] is False
    assert receipt["availability_state_authorized"] is False
    assert receipt["forecast_probability_effect_authorized"] is False
    assert receipt["production_authorized"] is False
    assert receipt["completed_2026_outcomes_used_for_design_or_selection"] == 0
    projected = (tmp_path / "out" / "roster_metadata.jsonl").read_text().splitlines()
    assert len(projected) == 32 * 70
    assert all("Practice Squad" not in line for line in projected)


def test_one_team_below_frozen_minimum_fails_full_gate(tmp_path: Path):
    normal = roster_html(70)
    short = roster_html(69)

    def fake_get(url: str, **kwargs):
        html = short if "azcardinals.com" in url else normal
        return FakeResponse(url, html)

    receipt = mod.run_held_out_capture(tmp_path / "out", get=fake_get)
    assert receipt["status"] == "FAIL"
    assert receipt["parser_gate_pass_team_count"] == 31
    assert receipt["minimum_parsed_rows_observed"] == 69
    assert receipt["official_club_roster_metadata_parser_qualified"] is False
    assert receipt["player_identity_to_gsis_qualified"] is False
    assert receipt["production_authorized"] is False
