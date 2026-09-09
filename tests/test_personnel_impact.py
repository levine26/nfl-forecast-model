import pandas as pd

from nfl_forecast.personnel_impact import enrich_personnel_usage


def test_official_injury_evidence_gets_prior_usage_context_from_abbreviated_pbp_name():
    pbp_rows = []
    for i in range(100):
        pbp_rows.append({
            "season": 2025,
            "posteam": "NE",
            "receiver_player_name": "A.Receiver" if i < 30 else "O.Receiver",
            "rusher_player_name": None,
            "passer_player_name": "N.Quarterback",
        })
    predictions = pd.DataFrame([{
        "game_id": "2026_01_NE_SEA",
        "away_team": "NE",
        "home_team": "SEA",
    }])
    injuries = {
        "NE": [{
            "name": "Alpha Receiver",
            "position": "WR",
            "status": "Questionable",
            "source_url": "https://www.nfl.com/injuries/league/2026/reg1",
        }]
    }
    evidence = {
        "2026_01_NE_SEA": [{
            "category": "personnel",
            "title": "NE: Alpha Receiver — Questionable",
            "summary": "The official NFL injury report lists Alpha Receiver (WR) as Questionable.",
            "strength": "Moderate",
            "source_name": "NFL.com official injury report",
            "source_url": "https://www.nfl.com/injuries/league/2026/reg1",
        }]
    }

    enriched, status = enrich_personnel_usage(
        predictions=predictions,
        evidence=evidence,
        injuries=injuries,
        pbp=pd.DataFrame(pbp_rows),
        season=2026,
    )

    item = enriched["2026_01_NE_SEA"][0]
    assert status["status"] == "healthy"
    assert status["eligible_skill_injuries"] == 1
    assert status["evidence_items_enriched"] == 1
    assert "30%" in item["summary"]
    assert "not an automatic forecast adjustment" in item["summary"]
    assert "nflverse" in item["source_name"].lower()
    assert item["metadata"]["person_key"] == "areceiver"
    assert item["metadata"]["usage_context"]["targets"] == 30
    assert item["metadata"]["usage_context"]["target_share"] == 0.3


def test_ambiguous_abbreviated_player_keys_are_discarded():
    pbp = pd.DataFrame([
        {"season": 2025, "posteam": "NE", "receiver_player_name": "A.Brown", "rusher_player_name": None, "passer_player_name": "N.Qb"},
        {"season": 2025, "posteam": "NE", "receiver_player_name": "Adam Brown", "rusher_player_name": None, "passer_player_name": "N.Qb"},
        {"season": 2025, "posteam": "NE", "receiver_player_name": "Alex Brown", "rusher_player_name": None, "passer_player_name": "N.Qb"},
    ])
    predictions = pd.DataFrame([{"game_id":"g","away_team":"NE","home_team":"SEA"}])
    evidence = {"g":[{"category":"personnel","title":"NE: Adam Brown — Questionable","summary":"Official report.","source_name":"NFL.com"}]}
    injuries = {"NE":[{"name":"Adam Brown","position":"WR"}]}

    enriched, status = enrich_personnel_usage(predictions, evidence, injuries, pbp, 2026)

    assert status["ambiguous_player_keys_discarded"] >= 1
    assert status["evidence_items_enriched"] == 0
    assert "usage_context" not in enriched["g"][0].get("metadata", {})
