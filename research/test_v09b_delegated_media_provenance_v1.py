from __future__ import annotations

from research.v09b_delegated_media_provenance_v1 import _delegated_links, _markers


def test_delegated_links_require_exact_frozen_host() -> None:
    html = '''
    <a href="https://eagles.1rmg.com/rosters/">Rosters</a>
    <a href="https://eagles.1rmg.com/season-archives/">Season Archives</a>
    <a href="https://other.1rmg.com/">Other club</a>
    '''
    assert _delegated_links(html, "https://media.philadelphiaeagles.com/", "eagles.1rmg.com") == [
        "https://eagles.1rmg.com/rosters/",
        "https://eagles.1rmg.com/season-archives/",
    ]


def test_required_markers_are_all_explicit() -> None:
    result = _markers(
        "Browns Media Center Rosters Depth Chart Season Archive",
        ["Browns Media Center", "Rosters", "Depth Chart", "Season Archive"],
    )
    assert all(result.values())
    assert _markers("Browns Media Center Rosters", ["Depth Chart"])["Depth Chart"] is False
