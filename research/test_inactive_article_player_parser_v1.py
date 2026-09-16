from __future__ import annotations

import pytest

from research.inactive_article_player_parser_v1 import parse_inactive_article_html


def _html() -> str:
    return """
    <html><body>
      <h2>Article heading</h2>
      <h3>CARDINALS</h3>
      <ul>
        <li>QB Carson Beck (emergency third QB)</li>
        <li>CB Garrett Williams</li>
      </ul>
      <ul>
        <li>WHERE: Next Stadium</li>
        <li>WHEN: 4:25 p.m. ET | CBS</li>
      </ul>
      <h3>CHARGERS</h3>
      <ul>
        <li>OL Logan Taylor</li>
        <li>OL Alex Harkey</li>
      </ul>
      <h2>Related Content</h2>
      <ul><li>Not an inactive player</li></ul>
    </body></html>
    """


def test_extracts_team_player_position_and_emergency_annotation() -> None:
    parsed = parse_inactive_article_html(
        _html(),
        source_url="https://www.nfl.com/news/example",
        captured_at_utc="2026-09-13T15:49:38Z",
    )
    assert parsed.audit["team_sections"] == 2
    assert parsed.audit["inactive_entries"] == 4
    assert parsed.audit["emergency_third_qb_annotations"] == 1
    assert parsed.audit["team_entry_counts"] == {"ARI": 2, "LAC": 2}
    first = parsed.rows[0]
    assert first["team"] == "ARI"
    assert first["position_rendered"] == "QB"
    assert first["player_name_rendered"] == "Carson Beck"
    assert first["emergency_third_qb"] is True
    assert first["player_identity_to_gsis_qualified"] is False
    assert first["forecast_probability_effect_authorized"] is False


def test_game_metadata_list_after_inactive_list_is_not_player_data() -> None:
    parsed = parse_inactive_article_html(
        _html(),
        source_url="https://www.nfl.com/news/example",
        captured_at_utc="2026-09-13T15:49:38Z",
    )
    rendered = {(row["team"], row["player_name_rendered"]) for row in parsed.rows}
    assert ("ARI", "Next Stadium") not in rendered
    assert all(not str(row["position_rendered"]).startswith("WHERE") for row in parsed.rows)
    assert all(not str(row["position_rendered"]).startswith("WHEN") for row in parsed.rows)


def test_raw_sha_gate_fails_closed() -> None:
    with pytest.raises(ValueError, match="raw HTML SHA mismatch"):
        parse_inactive_article_html(
            _html(),
            source_url="https://www.nfl.com/news/example",
            captured_at_utc="2026-09-13T15:49:38Z",
            raw_html_sha256="0" * 64,
        )


def test_duplicate_player_within_team_fails_closed() -> None:
    html = """
    <h3>RAIDERS</h3>
    <ul><li>TE Brock Bowers</li><li>TE Brock Bowers</li></ul>
    <h2>Related Content</h2>
    """
    with pytest.raises(ValueError, match="duplicate player"):
        parse_inactive_article_html(
            html,
            source_url="https://www.nfl.com/news/example",
            captured_at_utc="2026-09-13T15:49:38Z",
        )


def test_duplicate_team_section_fails_closed() -> None:
    html = """
    <h3>PACKERS</h3><ul><li>LB Ty'Ron Hopper</li></ul>
    <h3>VIKINGS</h3><ul><li>QB J.J. McCarthy (emergency third QB)</li></ul>
    <h3>PACKERS</h3><ul><li>G Aaron Banks</li></ul>
    """
    with pytest.raises(ValueError, match="duplicate team sections"):
        parse_inactive_article_html(
            html,
            source_url="https://www.nfl.com/news/example",
            captured_at_utc="2026-09-13T15:49:38Z",
        )


def test_nonteam_navigation_and_related_content_are_ignored() -> None:
    html = """
    <h3>NEWS</h3><ul><li>Some nav item</li></ul>
    <h3>GIANTS</h3><ul><li>RB Najee Harris</li></ul>
    <h2>Related Content</h2><ul><li>Article Something Else</li></ul>
    """
    parsed = parse_inactive_article_html(
        html,
        source_url="https://www.nfl.com/news/example",
        captured_at_utc="2026-09-13T15:49:38Z",
    )
    assert parsed.audit["team_entry_counts"] == {"NYG": 1}
    assert parsed.rows[0]["player_name_rendered"] == "Najee Harris"
