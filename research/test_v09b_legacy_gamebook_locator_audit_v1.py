from __future__ import annotations

import pytest

from research.v09b_legacy_gamebook_locator_audit_v1 import (
    _canonical_team,
    _crosswalk_games,
    legacy_gamebook_url,
)


def test_legacy_gamebook_url_is_frozen() -> None:
    assert legacy_gamebook_url(2012, 1, "55504") == (
        "https://www.nflgsis.com/2012/Reg/01/55504/Gamebook.pdf"
    )


def test_week_is_zero_padded() -> None:
    assert legacy_gamebook_url(2016, 9, "56789").endswith("/2016/Reg/09/56789/Gamebook.pdf")


def test_double_digit_week_is_preserved() -> None:
    assert legacy_gamebook_url(2015, 14, "12345").endswith("/2015/Reg/14/12345/Gamebook.pdf")


def test_current_archived_schedule_object_shape_is_supported() -> None:
    games = [["2012090550", {"year": 2012, "week": 1}]]
    assert _crosswalk_games({"games": games}) == games


def test_direct_games_array_shape_remains_supported() -> None:
    games = [["2012090550", {"year": 2012, "week": 1}]]
    assert _crosswalk_games(games) == games


def test_unknown_crosswalk_shape_fails_closed() -> None:
    with pytest.raises(ValueError, match="missing list-valued 'games'"):
        _crosswalk_games({"events": []})


def test_historical_team_aliases_map_only_identity() -> None:
    assert _canonical_team("JAC") == "JAX"
    assert _canonical_team("SD") == "LAC"
    assert _canonical_team("STL") == "LA"
    assert _canonical_team("OAK") == "LV"
    assert _canonical_team("NE") == "NE"
