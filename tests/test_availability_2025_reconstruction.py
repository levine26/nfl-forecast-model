from __future__ import annotations

import pandas as pd
import pytest

import nfl_forecast.availability_2025_reconstruction as recon
from nfl_forecast.availability_2025_reconstruction import (
    attach_stable_identity,
    build_canonical_reconstruction,
    git_blob_sha1,
    load_regular_mirror,
    normalize_game_status,
    normalize_name_token,
    normalize_practice_status,
    parse_nfl_postseason_page,
    validate_nflverse_payload,
)


POST_HTML = """
<html><body>
<a class="nfl-c-matchup-strip__team-fullname">Cardinals</a>
<table class="d3-o-table">
<thead><tr><th>Player</th><th>Position</th><th>Injuries</th><th>Practice Status</th><th>Game Status</th></tr></thead>
<tbody><tr><td>Will Hernandez</td><td>G</td><td>Knee</td><td>Limited Participation in Practice</td><td>Out</td></tr></tbody>
</table>
</body></html>
"""

MATCHUP_HTML = """
<html><body>
<section class="nfl-o-injury-report__unit">
<div class="nfl-c-matchup-strip__game">
<a class="nfl-c-matchup-strip__team-fullname">Cowboys</a>
<a class="nfl-c-matchup-strip__team-fullname">Eagles</a>
</div>
<div class="nfl-t-stats__title">Cowboys</div>
<table class="d3-o-table"><tbody>
<tr><td>Trevon Diggs</td><td>CB</td><td>Knee</td><td>Full Participation in Practice</td><td>Questionable</td></tr>
</tbody></table>
<div class="nfl-t-stats__title">Eagles</div>
<table class="d3-o-table"><tbody>
<tr><td>Jalen Carter</td><td>DT</td><td>Shoulder</td><td>Limited Participation in Practice</td><td>Questionable</td></tr>
</tbody></table>
</section>
</body></html>
"""


def _nflverse_row(*, week: int = 1) -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2025,
        "season_type": "REG" if week <= 18 else "POST",
        "game_type": "REG" if week <= 18 else "WC",
        "team": "ARI",
        "week": week,
        "gsis_id": "00-0034346",
        "position": "G",
        "full_name": "Will Hernandez",
        "first_name": "Will",
        "last_name": "Hernandez",
        "report_primary_injury": "Knee",
        "report_secondary_injury": None,
        "report_status": "Out",
        "practice_primary_injury": "Knee",
        "practice_secondary_injury": None,
        "practice_status": "Limited Participation in Practice",
    }])


def _external(*, week: int = 1) -> pd.DataFrame:
    return pd.DataFrame([{
        "season": 2025,
        "week": week,
        "team": "ARI",
        "external_player": "Will Hernandez",
        "external_position": "G",
        "external_injury": "Knee",
        "external_practice_status": "LP",
        "external_game_status": "OUT",
        "external_source": "fixture",
        "source_url": "https://example.test/source",
    }])


def test_git_blob_sha1_matches_git_object_identity():
    payload = b"hello\n"
    assert git_blob_sha1(payload) == "ce013625030ba8dba906f756967f9e9ca394464a"


def test_regular_mirror_loader_accepts_pinned_partial_supplemental_coverage(monkeypatch):
    rows = []
    for week in range(1, 13):
        rows.append({
            "season": 2025, "week": week, "team": "Arizona Cardinals", "player": "Will Hernandez",
            "position": "G", "injury": "Knee", "day_1_date": "Wed 09/03", "day_1_status": "LP",
            "day_2_date": "Thu 09/04", "day_2_status": "LP", "day_3_date": "Fri 09/05",
            "day_3_status": "LP", "game_status": "OUT",
        })
    payload = pd.DataFrame(rows).to_csv(index=False).encode()
    monkeypatch.setattr(recon, "REGULAR_MIRROR_EXPECTED_GIT_BLOB_SHA1", git_blob_sha1(payload))
    frame = load_regular_mirror(payload, source_url="https://example.test/mirror.csv")
    assert len(frame) == 12
    assert set(frame.week) == set(range(1, 13))
    assert set(frame.team) == {"ARI"}
    assert set(frame.external_practice_status) == {"LP"}
    assert set(frame.external_source) == {"footballdb_regular_github_mirror"}


def test_summary_schema_names_official_regular_coverage_not_supplemental_mirror():
    summary = recon.ReconstructionSummary(
        6068, 6068, 18, 4, 1.0, 1.0, 1.0, 1.0, 1.0, True, ()
    ).as_dict()
    assert summary["nfl_regular_weeks_crosschecked"] == 18
    assert "regular_mirror_weeks" not in summary


def test_nfl_postseason_parser_preserves_official_status_table():
    frame = parse_nfl_postseason_page(POST_HTML, nfl_week=19, source_url="https://www.nfl.com/injuries/league/2025/post1")
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row.team == "ARI"
    assert row.external_player == "Will Hernandez"
    assert row.external_practice_status == "Limited Participation in Practice"
    assert row.external_game_status == "Out"
    assert row.external_source == "nfl_com_official_injury_page"


def test_official_parser_uses_nearest_table_team_title_not_matchup_strip_order():
    frame = parse_nfl_postseason_page(
        MATCHUP_HTML,
        nfl_week=1,
        source_url="https://www.nfl.com/injuries/league/2025/reg1",
    )
    assert frame[["external_player", "team"]].to_dict("records") == [
        {"external_player": "Trevon Diggs", "team": "DAL"},
        {"external_player": "Jalen Carter", "team": "PHI"},
    ]


def test_initialism_normalization_preserves_full_name_identity():
    assert normalize_name_token("B.J. Hill") == "bj hill"
    assert normalize_name_token("BJ Hill") == "bj hill"
    assert normalize_name_token("C.J. Gardner-Johnson") == "cj gardner johnson"


def test_exact_full_name_crosswalk_attaches_gsis_and_ambiguous_fallback_does_not_guess():
    matched = attach_stable_identity(_external(), _nflverse_row())
    assert matched.iloc[0].gsis_id == "00-0034346"
    assert matched.iloc[0].identity_match_state == "unique"
    assert matched.iloc[0].identity_match_method == "exact_full_name"

    abbreviated = _external().assign(external_player="W. Hernandez")
    unique_fallback = attach_stable_identity(abbreviated, _nflverse_row())
    assert unique_fallback.iloc[0].gsis_id == "00-0034346"
    assert unique_fallback.iloc[0].identity_match_method == "unique_initial_surname"

    ambiguous = pd.concat([_nflverse_row(), _nflverse_row().assign(gsis_id="00-0099999")], ignore_index=True)
    blocked = attach_stable_identity(abbreviated, ambiguous)
    assert blocked.iloc[0].gsis_id == ""
    assert blocked.iloc[0].identity_match_state == "ambiguous"


def test_failed_full_name_match_does_not_fall_back_to_different_same_initial_surname():
    nflverse = _nflverse_row(week=7).assign(
        team="SEA",
        gsis_id="00-0032387",
        full_name="Jarran Reed",
        first_name="Jarran",
        last_name="Reed",
        position="DT",
    )
    external = _external(week=7).assign(
        team="SEA",
        external_player="Jaylen Reed",
        external_position="S",
    )
    blocked = attach_stable_identity(external, nflverse)
    assert blocked.iloc[0].gsis_id == ""
    assert blocked.iloc[0].identity_match_state == "unmatched"
    assert blocked.iloc[0].identity_match_method == "exact_full_name"


def test_canonical_practice_state_is_known_before_t120_without_postgame_information():
    schedules = pd.DataFrame([{
        "game_id": "2025_01_ARI_NO",
        "season": 2025,
        "week": 1,
        "home_team": "NO",
        "away_team": "ARI",
        "gameday": "2025-09-07",
        "gametime": "13:00",
    }])
    result = build_canonical_reconstruction(_nflverse_row(), _external(), schedules)
    row = result.iloc[0]
    assert bool(row.identity_matched)
    assert bool(row.practice_status_agrees)
    assert bool(row.game_status_agrees)
    assert bool(row.known_by_t120)
    assert bool(row.fully_qualified_practice_state)
    assert not bool(row.postgame_information_used)
    assert not bool(row.historical_game_status_feature_authorized)


def test_status_normalization_handles_both_vocabularies():
    assert normalize_practice_status("Limited Participation in Practice") == "limited"
    assert normalize_practice_status("LP") == "limited"
    assert normalize_practice_status("FP") == "full"
    assert normalize_practice_status("DNP") == "dnp"
    assert normalize_game_status("Questionable") == "questionable"
    assert normalize_game_status("(-)") == ""
    assert normalize_game_status("UNSPECIFIED") == ""


def test_nflverse_payload_drift_fails_closed_before_parsing():
    with pytest.raises(ValueError, match="digest changed"):
        validate_nflverse_payload(b"season,week,gsis_id\n2025,1,00-0000001\n")
