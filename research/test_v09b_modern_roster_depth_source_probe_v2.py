from __future__ import annotations

from datetime import date

from research.v09b_modern_roster_depth_source_probe_v2 import (
    _parse_as_of_from_line,
    archive_link_evidence,
    choose_pregame_roster_date,
    marker_lines,
)


class _Response:
    def __init__(self, *, url: str, text: str = "", content: bytes = b"", status_code: int = 200):
        self.url = url
        self.text = text
        self.content = content
        self.status_code = status_code
        self.headers = {"content-type": "text/html"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    def __init__(self, response: _Response):
        self.response = response

    def get(self, *_args, **_kwargs):
        return self.response


def test_full_month_and_numeric_as_of_forms_are_accepted() -> None:
    assert _parse_as_of_from_line("AS OF NOVEMBER 9, 2017") == [date(2017, 11, 9)]
    assert _parse_as_of_from_line("(as of 9/3/21)") == [date(2021, 9, 3)]
    assert _parse_as_of_from_line("AS OF 11/17/2020") == [date(2020, 11, 17)]


def test_abbreviated_month_form_is_not_silently_added_to_v2_contract() -> None:
    assert _parse_as_of_from_line("As of Nov. 7, 2017") == []


def test_nearest_valid_pregame_snapshot_is_selected() -> None:
    candidates = [
        {"date": "2020-11-10", "distance_from_roster_marker_lines": 1},
        {"date": "2020-11-17", "distance_from_roster_marker_lines": 5},
        {"date": "2020-11-23", "distance_from_roster_marker_lines": 1},
    ]
    chosen = choose_pregame_roster_date(candidates, game_date=date(2020, 11, 22), maximum_age_days=7)
    assert chosen is not None
    assert chosen["date"] == "2020-11-17"
    assert chosen["snapshot_age_days"] == 5


def test_current_and_excluded_marker_taxonomy_is_structural() -> None:
    lines = [
        "2021 TAMPA BAY BUCCANEERS NUMERICAL ROSTER",
        "PRACTICE SQUAD",
        "INJURED RESERVE",
        "2021 TAMPA BAY BUCCANEERS ROSTER BY POSITION",
    ]
    assert len(marker_lines(lines, ("NUMERICAL ROSTER", "ALPHABETICAL ROSTER", "ROSTER BY POSITION"))) == 2
    assert len(marker_lines(lines, ("PRACTICE SQUAD",))) == 1
    assert len(marker_lines(lines, ("RESERVE/INJURED", "INJURED RESERVE"))) == 1


def test_archive_page_must_link_exact_frozen_pdf_with_frozen_label() -> None:
    archive_url = "https://www.patriots.com/press-room/mediasite/game-packages-2020"
    source_url = "https://static.clubs.nfl.com/image/upload/patriots/example.pdf"
    html = f'<a href="{source_url}">Rosters &amp; Depth</a><a href="https://static.clubs.nfl.com/image/upload/patriots/other.pdf">Rosters &amp; Depth</a>'
    result = archive_link_evidence(
        {
            "archive_url": archive_url,
            "archive_link_text": "Rosters & Depth",
            "source_url": source_url,
        },
        timeout=1.0,
        archive_hosts={"www.patriots.com"},
        pdf_hosts={"static.clubs.nfl.com"},
        session=_Session(_Response(url=archive_url, text=html)),
    )
    assert result["matching_archive_link_count"] == 2
    assert result["exact_source_link_count"] == 1
    assert result["exact_source_link_present"] is True
