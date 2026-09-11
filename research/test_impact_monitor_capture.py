from __future__ import annotations

import pandas as pd

from research.impact_monitor_capture import normalize_name, resolve_availability_cards
from nfl_forecast.player_impact_monitor import build_impact_monitor_payload


def _schedule() -> pd.DataFrame:
    return pd.DataFrame([
        {"game_id": "2026_01_AWY_HME", "season": 2026, "week": 1, "away_team": "AWY", "home_team": "HME"}
    ])


def _injuries() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "team": "HME", "player": "D.J. Example", "position": "WR",
            "practice_status": "Limited Participation", "game_status": "Questionable",
            "report_date": "2026-09-10", "source_url": "https://example.com/injury",
        },
        {
            "team": "AWY", "player": "Unknown Player", "position": "LB",
            "practice_status": "Did Not Participate", "game_status": "Doubtful",
            "report_date": "2026-09-10", "source_url": "https://example.com/injury",
        },
    ])


def _rosters() -> pd.DataFrame:
    return pd.DataFrame([
        {"season": 2026, "team": "HME", "full_name": "DJ Example", "football_name": "DJ Example", "position": "WR", "gsis_id": "00-0000001"},
        {"season": 2026, "team": "AWY", "full_name": "Other Player", "football_name": "Other Player", "position": "LB", "gsis_id": "00-0000002"},
    ])


def test_name_normalization_handles_punctuation_without_fuzzy_guessing() -> None:
    assert normalize_name("D.J. Example") == normalize_name("DJ Example")
    assert normalize_name("D.J. Example") != normalize_name("D. Example")


def test_resolver_creates_availability_only_card_and_skips_unresolved() -> None:
    cards, audit = resolve_availability_cards(
        _injuries(), _rosters(), _schedule(), season=2026, week=1,
        retrieved_at_utc="2026-09-10T20:00:00Z",
    )
    assert len(cards) == 1
    card = cards[0]
    assert card["player_id"] == "00-0000001"
    assert card["observed_statistics"] == []
    assert card["levline_impacts"] == []
    assert card["availability"]["source_status"] == "prospective_unqualified"
    assert audit["resolved_cards"] == 1
    assert audit["unresolved_rows"] == 1
    assert audit["modeled_player_impacts_created"] == 0
    assert audit["probability_feature_authorized"] is False

    payload = build_impact_monitor_payload(cards, generated_utc="FIXED")
    assert payload["games"][0]["players"][0]["availability"]["probability_feature_authorized"] is False


def test_ambiguous_stable_ids_fail_closed_instead_of_guessing() -> None:
    roster = _rosters()
    duplicate = roster.iloc[[0]].copy()
    duplicate["gsis_id"] = "00-0000009"
    roster = pd.concat([roster, duplicate], ignore_index=True)
    cards, audit = resolve_availability_cards(
        _injuries().iloc[[0]], roster, _schedule(), season=2026, week=1,
        retrieved_at_utc="2026-09-10T20:00:00Z",
    )
    assert cards == []
    assert audit["ambiguous_rows"] == 1
