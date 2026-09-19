from __future__ import annotations

import pandas as pd

from nfl_forecast.props_contextual_intelligence import (
    fetch_live_qb_starter_reports,
    resolve_primary_qbs_from_levline_media,
    resolve_primary_qbs_from_live_reports,
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


def test_live_reporting_resolves_cooper_rush_over_doubtful_depth_qb():
    game_id = "2026_02_CAR_ATL"
    state = pd.DataFrame(
        [
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
                "player_id": "ATL-RUSH",
                "player_name": "Cooper Rush",
                "position": "QB",
                "team": "ATL",
                "expected_active_state": "AVAILABLE",
            },
            {
                "game_id": game_id,
                "player_id": "ATL-PENIX",
                "player_name": "Michael Penix Jr.",
                "position": "QB",
                "team": "ATL",
                "expected_active_state": "OUT",
            },
            {
                "game_id": game_id,
                "player_id": "CAR-YOUNG",
                "player_name": "Bryce Young",
                "position": "QB",
                "team": "CAR",
                "expected_active_state": "AVAILABLE",
            },
        ]
    )
    reports = {
        "captured_at_utc": "2026-09-18T22:00:00Z",
        "games": {
            game_id: [
                {
                    "title": "Cooper Rush named starting QB for Falcons vs. Panthers",
                    "summary": (
                        "Head coach Kevin Stefanski announced Friday that Cooper Rush "
                        "will start against Carolina."
                    ),
                    "source_name": "Atlanta Falcons",
                    "source_url": (
                        "https://www.atlantafalcons.com/news/"
                        "cooper-rush-starting-qb-falcons-vs-panthers"
                    ),
                    "publisher_url": "https://www.atlantafalcons.com",
                    "published_utc": "2026-09-18T18:26:00Z",
                    "source_priority": 72,
                    "official_source": True,
                }
            ]
        },
    }

    resolved, audit = resolve_primary_qbs_from_live_reports(
        reports,
        state,
        game_id=game_id,
        forecast_timestamp=FORECAST,
    )

    assert resolved["ATL"]["player_id"] == "ATL-RUSH"
    assert resolved["ATL"]["provenance"].startswith("levline_live_reporting:")
    accepted = [row for row in audit["claims"] if row.get("accepted")]
    assert [row["player_id"] for row in accepted] == ["ATL-RUSH"]


def test_live_reporting_ignores_old_conflicting_starter_article():
    game_id = "2026_02_CAR_ATL"
    state = pd.DataFrame(
        [
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
                "player_id": "ATL-RUSH",
                "player_name": "Cooper Rush",
                "position": "QB",
                "team": "ATL",
                "expected_active_state": "AVAILABLE",
            },
            {
                "game_id": game_id,
                "player_id": "CAR-YOUNG",
                "player_name": "Bryce Young",
                "position": "QB",
                "team": "CAR",
                "expected_active_state": "AVAILABLE",
            },
        ]
    )
    reports = {
        "games": {
            game_id: [
                {
                    "title": "Atlanta names Tua Tagovailoa starting quarterback for Week 1",
                    "summary": "Tua Tagovailoa will start the opener.",
                    "published_utc": "2026-09-07T12:00:00Z",
                    "source_priority": 95,
                    "official_source": True,
                    "source_url": "https://www.atlantafalcons.com/news/tua-week-1-starter",
                },
                {
                    "title": "Cooper Rush named starting QB for Falcons vs. Panthers",
                    "summary": "Cooper Rush will start Sunday against Carolina.",
                    "published_utc": "2026-09-18T18:26:00Z",
                    "source_priority": 95,
                    "official_source": True,
                    "source_url": "https://www.atlantafalcons.com/news/cooper-rush-week-2-starter",
                },
            ]
        }
    }

    resolved, _ = resolve_primary_qbs_from_live_reports(
        reports,
        state,
        game_id=game_id,
        forecast_timestamp=FORECAST,
    )

    assert resolved["ATL"]["player_id"] == "ATL-RUSH"


def test_live_starter_fetch_uses_levline_news_stack_and_official_team_source():
    class Response:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            return None

    class Session:
        def get(self, url, **kwargs):
            if "google.com" in url:
                return Response(
                    """
                    <rss><channel><item>
                      <title>Cooper Rush named starting QB for Falcons vs. Panthers</title>
                      <link>https://www.atlantafalcons.com/news/cooper-rush-starting-qb-falcons-vs-panthers</link>
                      <source url="https://www.atlantafalcons.com">Atlanta Falcons</source>
                      <pubDate>Fri, 18 Sep 2026 18:26:00 GMT</pubDate>
                      <description>Cooper Rush will start Sunday against the Carolina Panthers.</description>
                    </item></channel></rss>
                    """
                )
            return Response("<rss><channel></channel></rss>")

    schedules = pd.DataFrame(
        [
            {
                "game_id": "2026_02_CAR_ATL",
                "season": 2026,
                "week": 2,
                "away_team": "CAR",
                "home_team": "ATL",
            }
        ]
    )

    payload, audit = fetch_live_qb_starter_reports(
        schedules,
        season=2026,
        week=2,
        session=Session(),
    )

    reports = payload["games"]["2026_02_CAR_ATL"]
    assert reports[0]["title"].startswith("Cooper Rush named starting QB")
    assert reports[0]["official_source"] is True
    assert audit["source_stack"].startswith("Sunday Signal Google News RSS")
