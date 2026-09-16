from __future__ import annotations

import hashlib

from research.inactive_article_player_parser_v1 import parse_inactive_article_html
from research.qualify_inactive_article_cohort_parser_v2 import qualify_cohort


def _html(include_lac: bool = True) -> str:
    lac = "<h3>CHARGERS</h3><ul><li>OL Logan Taylor</li><li>OL Alex Harkey</li></ul>" if include_lac else ""
    return f"""
    <html><body>
      <h3>FALCONS</h3><ul><li>QB Tua Tagovailoa</li></ul>
      <h3>CARDINALS</h3>
      <ul><li>QB Carson Beck (emergency third QB)</li><li>CB Garrett Williams</li></ul>
      {lac}
      <h2>Related Content</h2>
    </body></html>
    """


def _contract(raw_sha: str) -> dict:
    return {
        "contract_id": "TEST-V2",
        "validation_artifact": {"raw_html_sha256": raw_sha},
        "due_game_cohort": [
            {"game_id": "g", "away_team": "ARI", "home_team": "LAC"}
        ],
        "frozen_expected_cohort_truth": {
            "team_sections": 2,
            "inactive_entries": 4,
            "emergency_third_qb_annotations": 1,
            "team_entry_counts": {"ARI": 2, "LAC": 2},
            "sentinel_player_team_pairs": [["ARI", "Garrett Williams"]],
            "sentinel_emergency_third_qbs": [["ARI", "Carson Beck"]],
        },
    }


def test_cohort_filter_ignores_valid_noncohort_sections() -> None:
    html = _html()
    raw_sha = hashlib.sha256(html.encode()).hexdigest()
    parsed = parse_inactive_article_html(
        html,
        source_url="https://www.nfl.com/news/example",
        captured_at_utc="2026-09-13T19:32:16Z",
        raw_html_sha256=raw_sha,
    )
    receipt, rows = qualify_cohort(parsed, _contract(raw_sha))
    assert receipt["qualification_passed"] is True
    assert receipt["observed"]["full_article_team_sections"] == 3
    assert receipt["observed"]["cohort_team_sections"] == 2
    assert receipt["observed"]["cohort_inactive_entries"] == 4
    assert {row["team"] for row in rows} == {"ARI", "LAC"}
    assert receipt["authority"]["full_day_article_completeness_assumed"] is False
    assert receipt["authority"]["forecast_probability_effect_authorized"] is False
    assert receipt["authority"]["production_authorized"] is False


def test_missing_due_team_fails_closed() -> None:
    html = _html(include_lac=False)
    raw_sha = hashlib.sha256(html.encode()).hexdigest()
    parsed = parse_inactive_article_html(
        html,
        source_url="https://www.nfl.com/news/example",
        captured_at_utc="2026-09-13T19:32:16Z",
        raw_html_sha256=raw_sha,
    )
    receipt, _ = qualify_cohort(parsed, _contract(raw_sha))
    assert receipt["qualification_passed"] is False
    assert receipt["gates"]["all_due_teams_present"] is False
    assert receipt["authority"]["player_level_parser_qualified_for_due_cohort_filtering"] is False


def test_wrong_raw_sha_gate_fails_even_when_cohort_content_matches() -> None:
    html = _html()
    actual_sha = hashlib.sha256(html.encode()).hexdigest()
    parsed = parse_inactive_article_html(
        html,
        source_url="https://www.nfl.com/news/example",
        captured_at_utc="2026-09-13T19:32:16Z",
        raw_html_sha256=actual_sha,
    )
    contract = _contract("0" * 64)
    receipt, _ = qualify_cohort(parsed, contract)
    assert receipt["qualification_passed"] is False
    assert receipt["gates"]["raw_sha256_exact"] is False


def test_cohort_pass_never_grants_probability_or_identity_authority() -> None:
    html = _html()
    raw_sha = hashlib.sha256(html.encode()).hexdigest()
    parsed = parse_inactive_article_html(
        html,
        source_url="https://www.nfl.com/news/example",
        captured_at_utc="2026-09-13T19:32:16Z",
        raw_html_sha256=raw_sha,
    )
    receipt, _ = qualify_cohort(parsed, _contract(raw_sha))
    authority = receipt["authority"]
    assert authority["player_identity_to_gsis_qualified"] is False
    assert authority["availability_probability_feature_authorized"] is False
    assert authority["player_value_join_authorized"] is False
    assert authority["forecast_probability_effect_authorized"] is False
    assert authority["production_authorized"] is False
    assert receipt["completed_2026_outcomes_used"] == 0
