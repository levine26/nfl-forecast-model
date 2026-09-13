from __future__ import annotations

from datetime import date

import pytest

from research.v09b_modern_game_release_roster_source_probe_v1 import (
    choose_pregame_roster_date,
    marker_lines,
    pdf_magic_valid,
    roster_as_of_candidates,
    validate_source_url,
)


def test_first_party_url_guard() -> None:
    validate_source_url("https://static.clubs.nfl.com/image/upload/team/example.pdf")
    with pytest.raises(ValueError):
        validate_source_url("http://static.clubs.nfl.com/image/upload/team/example.pdf")
    with pytest.raises(ValueError):
        validate_source_url("https://example.com/example.pdf")


def test_marker_detection_is_case_and_spacing_tolerant() -> None:
    lines = [
        " NEW ENGLAND PATRIOTS   GAME RELEASE ",
        " 2021 PATRIOTS NUMERICAL ROSTER ",
        " PRACTICE   SQUAD ",
        " RESERVE/INJURED ",
    ]
    assert len(marker_lines(lines, ("GAME RELEASE",))) == 1
    assert len(marker_lines(lines, ("NUMERICAL ROSTER",))) == 1
    assert len(marker_lines(lines, ("PRACTICE SQUAD", "RESERVE/INJURED"))) == 2


def test_roster_as_of_date_is_bounded_to_roster_marker_window() -> None:
    lines = ["old history AS OF JANUARY 1, 2010"] + [""] * 20
    lines += ["2021 TEAM NUMERICAL ROSTER", "AS OF NOVEMBER 9, 2021", "PRACTICE SQUAD"]
    roster_markers = marker_lines(lines, ("NUMERICAL ROSTER",))
    candidates = roster_as_of_candidates(lines, roster_markers, window_lines=4)
    assert [row["date"] for row in candidates] == ["2021-11-09"]


def test_numeric_as_of_date_is_supported_and_must_be_pregame() -> None:
    lines = ["2021 TEAM NUMERICAL ROSTER", "(as of 11/9/21)"]
    roster_markers = marker_lines(lines, ("NUMERICAL ROSTER",))
    candidates = roster_as_of_candidates(lines, roster_markers, window_lines=2)
    chosen = choose_pregame_roster_date(
        candidates,
        game_date=date(2021, 11, 14),
        maximum_age_days=7,
    )
    assert chosen is not None
    assert chosen["date"] == "2021-11-09"
    assert chosen["snapshot_age_days"] == 5


def test_snapshot_older_than_seven_days_is_not_viable() -> None:
    candidates = [
        {
            "date": "2021-11-01",
            "line_index": 10,
            "distance_from_roster_marker_lines": 1,
            "line": "AS OF NOVEMBER 1, 2021",
            "roster_marker": "NUMERICAL ROSTER",
            "roster_marker_line_index": 9,
        }
    ]
    assert choose_pregame_roster_date(
        candidates,
        game_date=date(2021, 11, 14),
        maximum_age_days=7,
    ) is None


def test_postgame_snapshot_is_never_accepted() -> None:
    candidates = [
        {
            "date": "2021-11-15",
            "line_index": 10,
            "distance_from_roster_marker_lines": 1,
            "line": "AS OF NOVEMBER 15, 2021",
            "roster_marker": "NUMERICAL ROSTER",
            "roster_marker_line_index": 9,
        }
    ]
    assert choose_pregame_roster_date(
        candidates,
        game_date=date(2021, 11, 14),
        maximum_age_days=7,
    ) is None


def test_pdf_magic() -> None:
    assert pdf_magic_valid(b"%PDF-1.7\n...") is True
    assert pdf_magic_valid(b"not a pdf") is False
