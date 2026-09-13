from __future__ import annotations

import pandas as pd

from research.v09b_modern_dnp_weekly_roster_diagnostic_v1 import (
    DnpToken,
    gamebook_name_parts,
    name_compatible,
    normalize_jersey,
    parse_dnp_tokens_from_text,
    resolve_dnp_token,
    validate_weekly_roster_frame,
)


def _row(**kwargs):
    row = {
        "season": 2021,
        "week": 10,
        "team": "KC",
        "jersey_number": 99,
        "status": "INA",
        "status_description_abbr": "INA",
        "full_name": "Khalen Saunders",
        "first_name": "Khalen",
        "last_name": "Saunders",
        "football_name": "Khalen Saunders",
        "display_name": "Khalen Saunders",
        "gsis_id": "00-0035678",
    }
    row.update(kwargs)
    return row


def test_name_parts_and_exact_prefix_rule():
    assert gamebook_name_parts("K.Saunders") == ("k", "saunders")
    assert gamebook_name_parts("Da.Williams") == ("da", "williams")
    assert name_compatible("K.Saunders", _row()) is True
    assert name_compatible("X.Saunders", _row()) is False
    assert name_compatible("K.Smith", _row()) is False


def test_jersey_normalization_is_exact_not_fuzzy():
    assert normalize_jersey("09") == "9"
    assert normalize_jersey(99.0) == "99"
    assert normalize_jersey(None) == ""


def test_unique_resolution_preserves_source_status():
    weekly = validate_weekly_roster_frame(pd.DataFrame([_row()]), 2021)
    token = DnpToken(2021, 10, "2021_10_KC_LV", "KC", "left", "99", "K.Saunders")
    result = resolve_dnp_token(token, weekly)
    assert result["identity_state"] == "unique"
    assert result["gsis_id"] == "00-0035678"
    assert result["weekly_statuses"] == "INA"


def test_same_jersey_different_name_does_not_match():
    weekly = validate_weekly_roster_frame(pd.DataFrame([_row()]), 2021)
    token = DnpToken(2021, 10, "2021_10_KC_LV", "KC", "left", "99", "A.Brown")
    result = resolve_dnp_token(token, weekly)
    assert result["identity_state"] == "unresolved"
    assert result["weekly_statuses"] == ""


def test_source_absence_never_becomes_active():
    weekly = validate_weekly_roster_frame(pd.DataFrame([_row()]), 2021)
    token = DnpToken(2021, 10, "2021_10_KC_LV", "KC", "left", "80", "M.Missing")
    result = resolve_dnp_token(token, weekly)
    assert result["identity_state"] == "unresolved"
    assert result["weekly_statuses"] == ""


def test_parser_extracts_both_team_dnp_columns_without_promoting_semantics():
    text = """
Lineups                                               Lineups
10 A.Alpha                                            12 B.Beta
Substitutions                                         Substitutions
20 C.Charlie                                          22 D.Delta
Did Not Play                                          Did Not Play
99 K.Saunders                                         81 A.Brown
Not Active                                            Not Active
1 X.One                                               2 Y.Two
"""
    tokens = parse_dnp_tokens_from_text(
        text,
        season=2021,
        week=10,
        game_id="2021_10_KC_TB",
        away_team="KC",
        home_team="TB",
    )
    observed = {(t.team, t.jersey_number, t.gamebook_name) for t in tokens}
    assert ("KC", "99", "K.Saunders") in observed
    assert ("TB", "81", "A.Brown") in observed
    assert all("X.One" != t.gamebook_name for t in tokens)
    assert all("Y.Two" != t.gamebook_name for t in tokens)


def test_required_weekly_roster_schema_is_fail_closed():
    frame = pd.DataFrame([_row()]).drop(columns=["gsis_id"])
    try:
        validate_weekly_roster_frame(frame, 2021)
    except ValueError as exc:
        assert "missing fields" in str(exc)
    else:
        raise AssertionError("missing stable identity must fail closed")
