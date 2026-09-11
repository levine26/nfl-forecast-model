from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_copilot_media_prompt.py"
spec = importlib.util.spec_from_file_location("build_groq_media_prompt", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
_packet = module._packet


def test_groq_packet_contains_pick_and_context_but_no_model_numerics():
    row = pd.Series({
        "game_id": "2026_01_DEN_KC",
        "season": 2026,
        "week": 1,
        "gameday": "2026-09-13",
        "gametime": "16:25",
        "away_team": "DEN",
        "home_team": "KC",
        "pick": "KC",
        "confidence": "Lean",
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        # These values deliberately exist on the production row but must never be
        # handed to Groq. Deterministic code owns every numerical model statement.
        "final_home_prob": 0.605,
        "fst_pure_home_prob": 0.316,
        "pure_home_prob": 0.318,
        "market_home_prob": 0.572,
        "expected_margin": -5.5,
        "spread_line": 2.5,
        "expected_total": 45.0,
        "projected_score": "DEN 25 – KC 20",
    })
    previews = {
        "2026_01_DEN_KC": {
            "reported_sources": [{
                "source_name": "NFL.com",
                "title": "Chiefs Week 1 availability update",
                "source_url": "https://www.nfl.com/news/should-not-be-passed-through",
                "as_of": "2026-09-11T20:00:00Z",
            }]
        }
    }
    evidence = {
        "2026_01_DEN_KC": [{
            "strength": "Strong",
            "category": "personnel",
            "title": "KC protection availability",
            "summary": "Kansas City has a current protection availability question.",
            "source_name": "NFL.com",
        }]
    }

    packet = _packet(row, previews, evidence)

    assert packet["levline_pick"] == "KC"
    assert packet["production_strategy"] == "F-ST-01-FROZEN-2026"
    assert packet["production_artifact"] == "F-ST-01-FROZEN-2026"
    assert packet["provider_scope"] == "editorial_research_only_no_model_numerics"
    assert packet["discovered_reporting"][0]["title"] == "Chiefs Week 1 availability update"
    assert "url" not in packet["discovered_reporting"][0]
    assert packet["verified_football_context"][0]["title"] == "KC protection availability"

    forbidden_keys = {
        "levline_pick_probability",
        "pure_pick_probability",
        "fst_pick_probability",
        "market_pick_probability",
        "expected_margin_home",
        "market_spread_home",
        "projected_score",
        "production_blend",
    }
    assert forbidden_keys.isdisjoint(packet)

    serialized = json.dumps(packet).lower()
    assert "75% pure" not in serialized
    assert "0.605" not in serialized
    assert "0.316" not in serialized
    assert "0.572" not in serialized
    assert "-5.5" not in serialized
