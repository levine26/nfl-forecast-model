from __future__ import annotations

"""Immutable accountability regression for 2026 Week 5 PHI–JAX.

This was NOT an on-time T−120 lock. The source was committed hours before
kickoff and is explicitly recorded as a recovered missed-lock snapshot.
Never infer a lock timestamp from prediction time or recovery time.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from nfl_forecast.public_forecast import build_public_forecasts
from nfl_forecast.read_publication import synchronize_file


ROOT = Path(__file__).resolve().parents[1]
GAME = "2026_05_PHI_JAX"
SOURCE_COMMIT = "5f611ab21ab16db51c3e432740fba79c40d647fb"
SOURCE_PROB = "0.7729426227299359"
SOURCE_PREDICTION_AT = "2026-10-11T07:47:30.494936+00:00"


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_phi_jax_recovery_is_evidenced_not_a_fabricated_lock():
    history = _rows(ROOT / "outputs" / "prediction_history.csv")
    matching = [row for row in history if row.get("game_id") == GAME]
    assert len(matching) == 1
    status = json.loads((ROOT / "outputs" / "status.json").read_text(encoding="utf-8"))
    assert status["locked_official_predictions"] == len(history)
    row = matching[0]
    assert row["lock_status"] == "RECOVERED_MISSED_LOCK"
    assert row["lock_timestamp_utc"] == ""
    assert row["minutes_to_kickoff_at_lock"] == ""
    assert row["recovery_source_commit_sha"] == SOURCE_COMMIT
    assert row["prediction_timestamp_utc"] == SOURCE_PREDICTION_AT
    assert row["recovery_source_prediction_timestamp_utc"] == SOURCE_PREDICTION_AT
    assert row["final_home_prob"] == SOURCE_PROB
    assert row["pick"] == "JAX"
    assert row["final_probability_strategy"] == "F-ST-01-FROZEN-2026"
    assert row["fst_artifact_id"] == "F-ST-01-FROZEN-2026"
    assert row["locked_ats_status"] == "VALUE"
    assert row["locked_ats_pick_team"] == "JAX"
    assert float(row["locked_ats_pick_market_spread"]) == -8.5
    assert abs(float(row["locked_ats_home_edge_points"]) - (
        float(row["locked_ats_model_margin_home"]) -
        float(row["locked_ats_market_margin_home"])
    )) < 1e-10
    kickoff = datetime.fromisoformat(row["kickoff_utc"])
    assert datetime.fromisoformat(SOURCE_PREDICTION_AT) < kickoff
    assert datetime.fromisoformat(row["recovery_recorded_utc"].replace("Z", "+00:00")) > kickoff
    assert "NOT an on-time lock" in row["recovery_reason"]


def test_phi_jax_public_contract_exposes_provenance_without_laundering_recovery():
    history = _rows(ROOT / "outputs" / "prediction_history.csv")
    recovered = next(x for x in history if x["game_id"] == GAME)
    current = _rows(ROOT / "outputs" / "this_week.csv")
    live = next(x for x in current if x["game_id"] == GAME)
    public = build_public_forecasts(
        [live], [recovered],
        now_utc=datetime(2026, 10, 11, 17, 0, tzinfo=timezone.utc),
    )
    game = public["games"][0]
    assert game["source_snapshot"] == "RECOVERED_MISSED_LOCK"
    assert game["immutable"] is True
    assert game["lock_timestamp_utc"] is None
    assert game["recovery"]["source_commit_sha"] == SOURCE_COMMIT
    assert game["official_home_win_probability"] == float(SOURCE_PROB)


def test_recovered_publication_is_full_slate_and_reads_are_synchronized():
    current = _rows(ROOT / "outputs" / "this_week.csv")
    history = _rows(ROOT / "outputs" / "prediction_history.csv")
    matching = next(row for row in current if row.get("game_id") == GAME)
    official = next(row for row in history if row.get("game_id") == GAME)
    assert matching["final_home_prob"] == official["final_home_prob"] == SOURCE_PROB
    assert matching["prediction_timestamp_utc"] == SOURCE_PREDICTION_AT
    assert matching["market_home_prob"] == official["market_home_prob"]
    assert len(current) == len({row["game_id"] for row in current})
    assert synchronize_file(ROOT / "outputs", check=True) == 0
