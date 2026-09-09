import pandas as pd

from nfl_forecast.career_qb_context import add_career_qb_ledgers


def _evidence():
    return {"g": [{
        "category":"history",
        "title":"Jacoby Brissett vs LAC: player history",
        "side":"away",
        "metadata":{
            "family":"qb_opponent_history",
            "meetings":[
                {"game_id":"2024_17_LAC_NE","season":2024,"dropbacks":2},
                {"game_id":"2022_05_LAC_CLE","season":2022,"dropbacks":34},
            ],
        },
    }]}


def test_career_ledger_excludes_relief_cameo_and_cross_checks_recent_game():
    stats = pd.DataFrame([
        {"player_display_name":"Jacoby Brissett","opponent_team":"LAC","attempts":40,"game_id":"2019_03_LAC_IND","season":2019,"season_type":"REG","passing_yards":300,"passing_tds":2,"passing_interceptions":0},
        {"player_display_name":"Jacoby Brissett","opponent_team":"LAC","attempts":34,"game_id":"2022_05_LAC_CLE","season":2022,"season_type":"REG","passing_yards":230,"passing_tds":1,"passing_interceptions":1},
        {"player_display_name":"Jacoby Brissett","opponent_team":"LAC","attempts":2,"game_id":"2024_17_LAC_NE","season":2024,"season_type":"REG","passing_yards":12,"passing_tds":0,"passing_interceptions":0},
    ])
    players = pd.DataFrame([{"display_name":"Jacoby Brissett","draft_year":2016}])
    evidence, audit, status = add_career_qb_ledgers(_evidence(), 2026, player_stats=stats, players=players)
    item = [x for x in evidence["g"] if (x.get("metadata") or {}).get("family") == "career_qb_opponent_ledger"][0]
    assert status["status"] == "healthy"
    assert item["metadata"]["meaningful_games"] == 2
    assert item["metadata"]["recent_overlap_verified"] is True
    assert "2 meaningful passing games" in item["summary"]
    assert "brief relief cameos are excluded" in item["summary"]
    assert audit[0]["provenance_grade"] == "B"


def test_career_ledger_fails_closed_when_recent_pbp_game_is_missing():
    stats = pd.DataFrame([
        {"player_display_name":"Jacoby Brissett","opponent_team":"LAC","attempts":40,"game_id":"2019_03_LAC_IND","season":2019,"season_type":"REG"},
    ])
    players = pd.DataFrame([{"display_name":"Jacoby Brissett","draft_year":2016}])
    evidence, audit, status = add_career_qb_ledgers(_evidence(), 2026, player_stats=stats, players=players)
    assert status["status"] == "degraded"
    assert status["conflicts"] == 1
    assert audit[0]["provenance_grade"] == "HOLD"
    assert not [x for x in evidence["g"] if (x.get("metadata") or {}).get("family") == "career_qb_opponent_ledger"]
