from __future__ import annotations

import pandas as pd

from nfl_forecast.props_contextual_intelligence import (
    resolve_primary_qbs_from_current_reporting,
    resolve_primary_qbs_from_levline_media,
)


GAME_ID = "2026_02_SEA_ARI"
FORECAST = "2026-09-18T23:00:00Z"


def _player_state():
    return pd.DataFrame(
        [
            {
                "game_id": GAME_ID,
                "player_id": "SEA-DARNOLD",
                "player_name": "Sam Darnold",
                "position": "QB",
                "team": "SEA",
                "expected_active_state": "OUT",
            },
            {
                "game_id": GAME_ID,
                "player_id": "SEA-LOCK",
                "player_name": "Drew Lock",
                "position": "QB",
                "team": "SEA",
                "expected_active_state": "UNKNOWN",
            },
            {
                "game_id": GAME_ID,
                "player_id": "ARI-QB1",
                "player_name": "Kyler Murray",
                "position": "QB",
                "team": "ARI",
                "expected_active_state": "AVAILABLE",
            },
        ]
    )


def _media(*, generated="2026-09-18T21:00:00Z", paragraph=None):
    return {
        "generated_utc": generated,
        "games": {
            GAME_ID: {
                "generated_utc": generated,
                "paragraph1": paragraph
                or (
                    "Seattle heads to Arizona with Drew Lock expected to start after "
                    "Sam Darnold was ruled out. Arizona prepares for the replacement "
                    "quarterback while Seattle adjusts its passing-game plan."
                ),
                "sources": [
                    {
                        "name": "Seattle Seahawks",
                        "title": "Sam Darnold ruled out; Drew Lock will start",
                        "url": "https://www.seahawks.com/news/darnold-out-drew-lock-start",
                    },
                    {
                        "name": "NFL",
                        "title": "Seahawks turn to Drew Lock at quarterback",
                        "url": "https://www.nfl.com/news/seahawks-drew-lock-week-2",
                    },
                ],
            }
        },
    }


def test_shared_media_expected_starter_overrides_when_competing_qb_is_out():
    resolved, audit = resolve_primary_qbs_from_levline_media(
        _media(),
        _player_state(),
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved["SEA"]["player_id"] == "SEA-LOCK"
    assert resolved["SEA"]["provenance"].startswith("levline_shared_media:")
    assert audit["status"] == "qualified"
    assert audit["teams_resolved"] == 1
    assert audit["claims"][0]["accepted"] is True


def test_stale_shared_media_is_not_used_for_props_qb_identity():
    resolved, audit = resolve_primary_qbs_from_levline_media(
        _media(generated="2026-09-17T12:00:00Z"),
        _player_state(),
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved == {}
    assert audit["status"] == "stale"


def test_uncertain_starter_reporting_fails_closed():
    media = _media(
        paragraph=(
            "Seattle has not yet named its starting quarterback, and Drew Lock could "
            "start if Sam Darnold cannot go. Arizona is preparing for multiple options."
        )
    )
    resolved, audit = resolve_primary_qbs_from_levline_media(
        media,
        _player_state(),
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved == {}
    assert audit["status"] == "no_qualified_starter_claim"


def test_out_player_cannot_be_promoted_by_media_claim():
    state = _player_state()
    state.loc[state["player_id"].eq("SEA-LOCK"), "expected_active_state"] = "OUT"
    resolved, audit = resolve_primary_qbs_from_levline_media(
        _media(),
        state,
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved == {}
    assert audit["status"] == "no_qualified_starter_claim"


def test_confirmed_starter_with_source_title_support_overrides_without_competing_injury():
    game_id = "2026_02_CAR_ATL"
    state = pd.DataFrame(
        [
            {
                "game_id": game_id,
                "player_id": "ATL-RUSH",
                "player_name": "Cooper Rush",
                "position": "QB",
                "team": "ATL",
                "expected_active_state": "AVAILABLE",
            },
            {
                "game_id": game_id,
                "player_id": "ATL-QB2",
                "player_name": "Taylor Heinicke",
                "position": "QB",
                "team": "ATL",
                "expected_active_state": "AVAILABLE",
            },
            {
                "game_id": game_id,
                "player_id": "CAR-QB1",
                "player_name": "Bryce Young",
                "position": "QB",
                "team": "CAR",
                "expected_active_state": "AVAILABLE",
            },
        ]
    )
    media = {
        "generated_utc": "2026-09-18T21:00:00Z",
        "games": {
            game_id: {
                "generated_utc": "2026-09-18T21:00:00Z",
                "paragraph1": (
                    "Atlanta confirmed Cooper Rush will start against Carolina. "
                    "The Falcons are adjusting the passing plan around Rush while the "
                    "Panthers prepare for the newly named starter."
                ),
                "sources": [
                    {
                        "name": "Atlanta Falcons",
                        "title": "Cooper Rush will start at quarterback against Carolina",
                        "url": "https://www.atlantafalcons.com/news/cooper-rush-start-quarterback-carolina",
                    },
                    {
                        "name": "NFL",
                        "title": "Falcons name Cooper Rush starter for Week 2",
                        "url": "https://www.nfl.com/news/falcons-cooper-rush-starter-week-2",
                    },
                ],
            }
        },
    }

    resolved, audit = resolve_primary_qbs_from_levline_media(
        media,
        state,
        game_id=game_id,
        forecast_timestamp=FORECAST,
    )

    assert resolved["ATL"]["player_id"] == "ATL-RUSH"
    assert audit["status"] == "qualified"
    accepted = [row for row in audit["claims"] if row.get("accepted")]
    assert accepted[0]["strength"] == "confirmed"


def test_replacement_sentence_does_not_misclassify_displaced_qb_as_starter():
    state = _player_state()
    state.loc[state["player_id"].eq("SEA-DARNOLD"), "expected_active_state"] = "QUESTIONABLE"

    resolved, audit = resolve_primary_qbs_from_levline_media(
        _media(),
        state,
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved["SEA"]["player_id"] == "SEA-LOCK"
    accepted = [row for row in audit["claims"] if row.get("accepted")]
    assert [row["player_id"] for row in accepted] == ["SEA-LOCK"]



def test_current_reporting_resolves_drew_lock_from_fresh_starter_headline():
    previews = {
        GAME_ID: {
            "current_reported_sources": [
                {
                    "source_name": "Yahoo Sports",
                    "source_url": "https://sports.yahoo.com/articles/drew-lock-start-cardinals.html",
                    "title": "Seahawks’ Drew Lock Auditioning for QB-Needy NFL Teams With Start at Cardinals",
                    "as_of": "2026-09-18T17:00:00Z",
                }
            ]
        }
    }

    resolved, audit = resolve_primary_qbs_from_current_reporting(
        previews,
        _player_state(),
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved["SEA"]["player_id"] == "SEA-LOCK"
    assert resolved["SEA"]["provenance"].startswith("levline_current_reporting:")
    assert audit["status"] == "qualified"
    assert audit["teams_resolved"] == 1


def test_current_reporting_resolves_cooper_rush_from_named_starter_headline():
    game_id = "2026_02_CAR_ATL"
    state = pd.DataFrame(
        [
            {
                "game_id": game_id,
                "player_id": "ATL-RUSH",
                "player_name": "Cooper Rush",
                "position": "QB",
                "team": "ATL",
                "expected_active_state": "AVAILABLE",
            },
            {
                "game_id": game_id,
                "player_id": "ATL-TUA",
                "player_name": "Tua Tagovailoa",
                "position": "QB",
                "team": "ATL",
                "expected_active_state": "DOUBTFUL",
            },
            {
                "game_id": game_id,
                "player_id": "CAR-QB1",
                "player_name": "Bryce Young",
                "position": "QB",
                "team": "CAR",
                "expected_active_state": "AVAILABLE",
            },
        ]
    )
    previews = {
        game_id: {
            "current_reported_sources": [
                {
                    "source_name": "Atlanta Falcons",
                    "source_url": "https://www.atlantafalcons.com/news/cooper-rush-starting-quarterback",
                    "title": "Falcons name Cooper Rush starting quarterback for Sunday vs. Panthers",
                    "as_of": "2026-09-18T21:30:00Z",
                }
            ]
        }
    }

    resolved, audit = resolve_primary_qbs_from_current_reporting(
        previews,
        state,
        game_id=game_id,
        forecast_timestamp=FORECAST,
    )

    assert resolved["ATL"]["player_id"] == "ATL-RUSH"
    assert audit["status"] == "qualified"


def test_stale_current_reporting_fails_closed():
    previews = {
        GAME_ID: {
            "current_reported_sources": [
                {
                    "source_name": "Seattle Seahawks",
                    "source_url": "https://www.seahawks.com/news/old-drew-lock-story",
                    "title": "Drew Lock to start at quarterback",
                    "as_of": "2026-09-15T18:00:00Z",
                }
            ]
        }
    }

    resolved, audit = resolve_primary_qbs_from_current_reporting(
        previews,
        _player_state(),
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved == {}
    assert audit["sources_stale_discarded"] == 1
    assert audit["status"] == "no_qualified_current_reporting"


def test_same_timestamp_conflicting_current_starter_claims_fail_closed():
    state = _player_state()
    state.loc[state["player_id"].eq("SEA-DARNOLD"), "expected_active_state"] = "AVAILABLE"
    previews = {
        GAME_ID: {
            "current_reported_sources": [
                {
                    "source_name": "Outlet A",
                    "source_url": "https://example.com/lock",
                    "title": "Drew Lock to start at quarterback for Seattle",
                    "as_of": "2026-09-18T22:00:00Z",
                },
                {
                    "source_name": "Outlet B",
                    "source_url": "https://example.org/darnold",
                    "title": "Sam Darnold will start at quarterback for Seattle",
                    "as_of": "2026-09-18T22:00:00Z",
                },
            ]
        }
    }

    resolved, audit = resolve_primary_qbs_from_current_reporting(
        previews,
        state,
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert "SEA" not in resolved
    assert audit["teams_ambiguous"][0]["team"] == "SEA"


def test_newer_current_starter_report_supersedes_older_conflicting_report():
    state = _player_state()
    state.loc[state["player_id"].eq("SEA-DARNOLD"), "expected_active_state"] = "AVAILABLE"
    previews = {
        GAME_ID: {
            "current_reported_sources": [
                {
                    "source_name": "Earlier report",
                    "source_url": "https://example.com/darnold-earlier",
                    "title": "Sam Darnold will start at quarterback for Seattle",
                    "as_of": "2026-09-18T19:00:00Z",
                },
                {
                    "source_name": "Seattle Seahawks",
                    "source_url": "https://www.seahawks.com/news/drew-lock-late-update",
                    "title": "Drew Lock to start at quarterback for Seattle",
                    "as_of": "2026-09-18T22:00:00Z",
                },
            ]
        }
    }

    resolved, audit = resolve_primary_qbs_from_current_reporting(
        previews,
        state,
        game_id=GAME_ID,
        forecast_timestamp=FORECAST,
    )

    assert resolved["SEA"]["player_id"] == "SEA-LOCK"
    assert audit["status"] == "qualified"
