from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import pandas as pd
from nfl_forecast.publish import write_outputs


def test_forecast_and_lock_writer_does_not_require_editorial_artifact(tmp_path):
    row = dict(
        game_id="2026_06_CHI_GB", season=2026, week=6,
        gameday="2026-10-18", gametime="13:00", home_team="GB", away_team="CHI",
        final_home_prob=0.63, market_home_prob=0.61, pick="GB",
        model_version="0.9.0-fst", final_probability_strategy="F-ST-01-FROZEN-2026",
        fst_artifact_id="F-ST-01-FROZEN-2026",
    )
    games = pd.DataFrame([{"game_id": row["game_id"], "home_team": "GB", "away_team": "CHI"}])
    write_outputs(
        SimpleNamespace(predictions=pd.DataFrame([row]), games=games),
        output_dir=tmp_path,
        now_utc=datetime(2026, 10, 18, 16, 30, tzinfo=timezone.utc),
    )
    assert (tmp_path / "this_week.csv").is_file()
    assert (tmp_path / "status.json").is_file()
    locks = pd.read_csv(tmp_path / "prediction_history.csv")
    assert len(locks) == 1 and locks.iloc[0]["lock_status"] == "LOCKED"
    assert not (tmp_path / "game_previews.json").exists()


def test_no_production_read_gate_and_no_autonomous_editorial_workflows():
    root = Path(__file__).resolve().parents[1]
    for name in ("weekly.yml", "market_refresh.yml", "pregame.yml", "fast_official_lock.yml", "dashboard.yml"):
        content = (root / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "sync_market_reads --output-dir" not in content
    dashboard = (root / ".github" / "workflows" / "dashboard.yml").read_text(encoding="utf-8")
    assert "game_previews.json" not in dashboard
    assert "context_source_status.json" not in dashboard
    for name in ("context.yml", "groq_after_context.yml", "groq_media_writer.yml",
                 "chatgpt_media_ingest.yml", "chatgpt_failed_game_ingest.yml",
                 "editorial_source_receipts_shadow.yml"):
        workflow = (root / ".github" / "workflows" / name).read_text(encoding="utf-8")
        triggers = workflow.split("\non:", 1)[1].split("\npermissions:", 1)[0]
        assert "workflow_dispatch:" in triggers
        for forbidden in ("push:", "schedule:", "workflow_run:", "pull_request:"):
            assert forbidden not in triggers
