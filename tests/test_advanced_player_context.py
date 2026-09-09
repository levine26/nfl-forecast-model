import pandas as pd

from nfl_forecast.advanced_player_context import build_ngs_qb_evidence


def test_ngs_qb_context_uses_current_starter_from_verified_history_evidence():
    evidence = {"g": [{
        "category":"history",
        "title":"Matthew Stafford vs SF: player history",
        "side":"home",
        "metadata":{"family":"qb_opponent_history"},
    }]}
    ngs = pd.DataFrame([{
        "season":2025,"season_type":"REG","week":0,"player_display_name":"Matthew Stafford",
        "attempts":510,"avg_time_to_throw":2.78,"completion_percentage_above_expectation":1.6,
        "avg_intended_air_yards":8.1,"aggressiveness":15.2,
    }])
    out, status = build_ngs_qb_evidence(evidence, 2026, frame=ngs)
    items = [item for item in out["g"] if (item.get("metadata") or {}).get("family") == "ngs_qb_profile"]
    assert status["status"] == "healthy"
    assert status["evidence_items_added"] == 1
    assert len(items) == 1
    assert "2.78s average time to throw" in items[0]["summary"]
    assert items[0]["promoted_to_model"] is False


def test_ngs_qb_context_does_not_publish_tiny_sample():
    evidence = {"g": [{
        "category":"history","title":"Backup QB vs SF: player history","side":"away",
        "metadata":{"family":"qb_opponent_history"},
    }]}
    ngs = pd.DataFrame([{
        "season":2025,"season_type":"REG","week":0,"player_display_name":"Backup QB",
        "attempts":12,"avg_time_to_throw":2.4,"completion_percentage_above_expectation":2.0,
        "avg_intended_air_yards":7.0,"aggressiveness":10.0,
    }])
    out, status = build_ngs_qb_evidence(evidence, 2026, frame=ngs)
    assert not [item for item in out["g"] if (item.get("metadata") or {}).get("family") == "ngs_qb_profile"]
    assert status["evidence_items_added"] == 0
