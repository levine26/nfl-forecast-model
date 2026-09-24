from pathlib import Path
import importlib.util
import json

import pandas as pd

from nfl_forecast.context import (
    coordinator_tenure,
    current_starting_qbs,
    fetch_espn_injuries,
    personnel_evidence,
)


class _Response:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class _Session:
    def __init__(self, payload): self.payload = payload
    def get(self, *args, **kwargs): return _Response(self.payload)


def test_espn_injury_parser_is_team_scoped():
    payload = {
        "injuries": [
            {
                "team": {"id":"24","abbreviation":"LAC"},
                "injuries": [
                    {
                        "athlete": {"fullName":"Example Quarterback","position":{"abbreviation":"QB"}},
                        "status": "Questionable",
                    }
                ],
            }
        ]
    }
    injuries, status = fetch_espn_injuries(session=_Session(payload))
    assert status["status"] == "healthy"
    assert injuries["LAC"][0]["name"] == "Example Quarterback"
    assert injuries["LAC"][0]["position"] == "QB"
    assert injuries["LAC"][0]["status"] == "Questionable"


def test_current_starting_qb_uses_latest_rank_one_depth_row():
    depth = pd.DataFrame([
        {"dt":"2026-08-20T00:00:00Z","team":"LAC","player_name":"Old QB","gsis_id":"old","espn_id":"1","pos_abb":"QB","pos_rank":1},
        {"dt":"2026-09-01T00:00:00Z","team":"LAC","player_name":"Justin Herbert","gsis_id":"herbert","espn_id":"2","pos_abb":"QB","pos_rank":1},
        {"dt":"2026-09-01T00:00:00Z","team":"LAC","player_name":"Backup QB","gsis_id":"backup","espn_id":"3","pos_abb":"QB","pos_rank":2},
    ])
    starters = current_starting_qbs(depth)
    assert starters["LAC"]["name"] == "Justin Herbert"
    assert starters["LAC"]["gsis_id"] == "herbert"


def test_coordinator_tenure_stops_when_staff_changes():
    history = {
        "DEN": {
            2026:{"def_coach":"Coach A"},
            2025:{"def_coach":"Coach A"},
            2024:{"def_coach":"Coach A"},
            2023:{"def_coach":"Coach B"},
        }
    }
    name, years = coordinator_tenure(history,"DEN",2026,"def_coach")
    assert name == "Coach A"
    assert years == [2026,2025,2024]


def test_qb_questionable_creates_scenario_watch_without_point_penalty():
    game = pd.Series({"away_team":"LAC","home_team":"DEN"})
    injuries = {"LAC":[{"name":"Justin Herbert","position":"QB","status":"Questionable","source_url":"https://example.com"}]}
    starters = {"LAC":{"name":"Justin Herbert","gsis_id":"herbert"}}
    items = personnel_evidence(game, injuries, starters)
    assert any(x.category == "personnel" for x in items)
    scenario = [x for x in items if x.category == "scenario"][0]
    assert "does not invent a quarterback penalty" in scenario.summary
    assert scenario.promoted_to_model is False


def test_context_refresh_preserves_current_slate_provider_fallback(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_context.py"
    spec = importlib.util.spec_from_file_location("run_context_script", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    status = {
        "groq_provider_fallback": {
            "status": "degraded",
            "run_id": "prior",
            "games": {
                "2026_03_ATL_GB": {
                    "provider": "groq",
                    "provider_result": "failed",
                    "requires_chatgpt_refresh": True,
                },
                "2026_02_OLD_GAME": {
                    "provider": "groq",
                    "provider_result": "failed",
                    "requires_chatgpt_refresh": True,
                },
            },
            "failed_games": ["2026_03_ATL_GB", "2026_02_OLD_GAME"],
        }
    }
    (tmp_path / "context_source_status.json").write_text(json.dumps(status), encoding="utf-8")

    preserved = module._preserve_provider_fallback(tmp_path, {"2026_03_ATL_GB"})
    assert preserved is not None
    assert set(preserved["games"]) == {"2026_03_ATL_GB"}
    assert preserved["failed_games"] == ["2026_03_ATL_GB"]
    assert preserved["games"]["2026_03_ATL_GB"]["requires_chatgpt_refresh"] is True
    assert preserved["context_refresh_preserved"] is True
