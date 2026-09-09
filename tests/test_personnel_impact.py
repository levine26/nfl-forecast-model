import pandas as pd

from nfl_forecast.personnel_impact import enrich_personnel_usage


def test_official_injury_evidence_gets_prior_usage_context():
    pbp_rows = []
    for i in range(100):
        pbp_rows.append({
            "season": 2025,
            "posteam": "NE",
            "receiver_player_name": "Alpha Receiver" if i < 30 else "Other Receiver",
            "rusher_player_name": None,
            "passer_player_name": "NE Quarterback",
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
    assert status["evidence_items_enriched"] == 1
    assert "30%" in item["summary"]
    assert "not an automatic forecast adjustment" in item["summary"]
    assert "nflverse" in item["source_name"].lower()
    assert item["metadata"]["usage_context"]["targets"] == 30
    assert item["metadata"]["usage_context"]["target_share"] == 0.3
