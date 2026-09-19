from __future__ import annotations

import pandas as pd

from nfl_forecast.props_contextual_intelligence import (
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
