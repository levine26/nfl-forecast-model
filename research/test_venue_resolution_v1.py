from __future__ import annotations

import pytest

from research.venue_resolution_v1 import (
    VenueResolutionError,
    choose_exact_candidate,
    extract_coordinate,
    normalize_name,
    resolve_game_venue,
    unresolved_game_venue,
)


def _entity(qid="Q123", rank="normal"):
    return {
        "id": qid,
        "labels": {"en": {"language": "en", "value": "Example Stadium"}},
        "claims": {
            "P625": [{
                "rank": rank,
                "mainsnak": {
                    "datavalue": {
                        "value": {
                            "latitude": 33.5,
                            "longitude": -112.1,
                            "globe": "http://www.wikidata.org/entity/Q2",
                        }
                    }
                },
            }]
        },
    }


def test_normalization_is_exact_but_punctuation_insensitive() -> None:
    assert normalize_name("Levi's Stadium") == normalize_name("LEVI’S STADIUM")
    assert normalize_name("AT&T Stadium") == "at and t stadium"


def test_search_requires_single_exact_label_or_returned_alias() -> None:
    candidate = choose_exact_candidate("Example Stadium", [
        {"id": "Q123", "label": "Example Stadium", "match": {"type": "label", "text": "Example Stadium"}},
        {"id": "Q999", "label": "Example Stadium Annex", "match": {"type": "label", "text": "Example Stadium Annex"}},
    ])
    assert candidate.qid == "Q123"

    alias = choose_exact_candidate("Old Sponsor Field", [
        {"id": "Q123", "label": "Current Sponsor Field", "match": {"type": "alias", "text": "Old Sponsor Field"}},
    ])
    assert alias.qid == "Q123"
    assert alias.match_type == "alias"


def test_fuzzy_or_ambiguous_search_results_fail_closed() -> None:
    with pytest.raises(VenueResolutionError, match="no exact"):
        choose_exact_candidate("Example Stadium", [
            {"id": "Q123", "label": "Example Stadium Annex", "match": {"type": "label", "text": "Example Stadium Annex"}},
        ])
    with pytest.raises(VenueResolutionError, match="ambiguous"):
        choose_exact_candidate("Example Stadium", [
            {"id": "Q123", "label": "Example Stadium", "match": {"type": "label", "text": "Example Stadium"}},
            {"id": "Q124", "label": "Example Stadium", "match": {"type": "label", "text": "Example Stadium"}},
        ])


def test_coordinate_requires_one_non_deprecated_earth_statement() -> None:
    assert extract_coordinate(_entity()) == (33.5, -112.1, "normal")
    entity = _entity()
    entity["claims"]["P625"].append(entity["claims"]["P625"][0].copy())
    with pytest.raises(VenueResolutionError, match="ambiguous"):
        extract_coordinate(entity)


def test_game_receipt_uses_schedule_stadium_not_home_team_inference() -> None:
    schedule = {
        "game_id": "2026_01_ARI_LAC",
        "gameday": "2026-09-13",
        "away_team": "ARI",
        "home_team": "LAC",
        "stadium": "Example Stadium",
        "location": "Neutral",
        "roof": "outdoors",
    }
    row = resolve_game_venue(
        schedule_row=schedule,
        search_rows=[{"id": "Q123", "label": "Example Stadium", "match": {"type": "label", "text": "Example Stadium"}}],
        entity=_entity(),
        schedule_retrieved_at_utc="2026-09-11T05:00:00Z",
        wikidata_retrieved_at_utc="2026-09-11T05:00:01Z",
    )
    assert row["game_id"] == schedule["game_id"]
    assert row["stadium_name"] == "Example Stadium"
    assert row["schedule_location"] == "Neutral"
    assert row["wikidata_qid"] == "Q123"
    assert row["research_only"] is True
    assert row["production_authorized"] is False


def test_unresolved_receipt_is_explicit_and_nonproduction() -> None:
    row = unresolved_game_venue(
        schedule_row={"game_id": "g", "stadium": "Mystery Field", "location": "Neutral"},
        reason="no exact Wikidata stadium label/alias match",
        schedule_retrieved_at_utc="2026-09-11T05:00:00Z",
        attempted_at_utc="2026-09-11T05:00:01Z",
    )
    assert row["status"] == "unresolved"
    assert row["reason"].startswith("no exact")
    assert row["production_authorized"] is False
