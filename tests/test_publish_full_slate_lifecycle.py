from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd

from nfl_forecast.publish import write_outputs


def _row(game_id: str, away: str, home: str, p_home: float, ts: str) -> dict:
    return {
        "game_id": game_id,
        "season": 2026,
        "week": 1,
        "gameday": "2026-09-13",
        "gametime": "20:20",
        "away_team": away,
        "home_team": home,
        "market_home_prob": 0.55,
        "final_home_prob": p_home,
        "pick": home if p_home >= 0.5 else away,
        "expected_margin": 2.0,
        "margin_sigma": 13.0,
        "expected_total": 45.0,
        "confidence": "Solid",
        "market_available": True,
        "snapshot_type": "MARKET",
        "model_version": "0.9.0-fst",
        "prediction_timestamp_utc": ts,
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "fst_fallback": False,
        "data_state": "test",
    }


def _locked_dal() -> dict:
    locked = _row("2026_01_DAL_NYG", "DAL", "NYG", 0.37, "2026-09-13T22:40:00+00:00")
    locked.update(
        {
            "lock_status": "LOCKED",
            "kickoff_utc": "2026-09-14T00:20:00+00:00",
            "lock_timestamp_utc": "2026-09-13T22:40:00+00:00",
            "minutes_to_kickoff_at_lock": 100.0,
        }
    )
    return locked


def _legacy_lock() -> dict:
    locked = _row("2026_01_NE_SEA", "NE", "SEA", 0.60, "2026-09-09T22:43:57+00:00")
    locked.update(
        {
            "final_probability_strategy": pd.NA,
            "fst_artifact_id": pd.NA,
            "model_version": "0.4.0-accountability",
            "lock_status": "LOCKED",
            "kickoff_utc": "2026-09-10T00:20:00+00:00",
            "lock_timestamp_utc": "2026-09-09T22:43:57+00:00",
            "minutes_to_kickoff_at_lock": 96.0,
        }
    )
    return locked


def _games(*ids: str) -> pd.DataFrame:
    return pd.DataFrame(
        [{"game_id": gid, "home_score": pd.NA, "away_score": pd.NA} for gid in ids]
    )


def test_write_outputs_preserves_locked_same_week_rows_and_prefers_lock(tmp_path):
    pd.DataFrame([_locked_dal()]).to_csv(tmp_path / "prediction_history.csv", index=False)

    # A later mutable row for the already-locked game must not replace the lock.
    mutated = _row("2026_01_DAL_NYG", "DAL", "NYG", 0.45, "2026-09-14T01:00:00+00:00")
    live = _row("2026_01_DEN_KC", "DEN", "KC", 0.58, "2026-09-14T01:00:00+00:00")
    artifacts = SimpleNamespace(
        predictions=pd.DataFrame([mutated, live]),
        games=_games("2026_01_DAL_NYG", "2026_01_DEN_KC"),
    )

    write_outputs(
        artifacts,
        tmp_path,
        now_utc=datetime(2026, 9, 14, 1, 5, tzinfo=timezone.utc),
        lock_window_minutes=0,
    )

    current = pd.read_csv(tmp_path / "this_week.csv").set_index("game_id")
    status = pd.read_json(tmp_path / "status.json", typ="series")

    assert set(current.index) == {"2026_01_DAL_NYG", "2026_01_DEN_KC"}
    assert current.loc["2026_01_DAL_NYG", "final_home_prob"] == 0.37
    assert current.loc["2026_01_DAL_NYG", "prediction_timestamp_utc"] == "2026-09-13T22:40:00+00:00"
    assert current.loc["2026_01_DEN_KC", "final_home_prob"] == 0.58
    assert int(status["games"]) == 2


def test_write_outputs_carries_locked_game_missing_from_live_predictions(tmp_path):
    pd.DataFrame([_locked_dal()]).to_csv(tmp_path / "prediction_history.csv", index=False)

    # This is the real production shrink case: completed DAL-NYG has disappeared from
    # the newly generated live frame, but its immutable same-week lock must stay public.
    live = _row("2026_01_DEN_KC", "DEN", "KC", 0.58, "2026-09-14T01:00:00+00:00")
    artifacts = SimpleNamespace(
        predictions=pd.DataFrame([live]),
        games=_games("2026_01_DAL_NYG", "2026_01_DEN_KC"),
    )

    write_outputs(
        artifacts,
        tmp_path,
        now_utc=datetime(2026, 9, 14, 1, 5, tzinfo=timezone.utc),
        lock_window_minutes=0,
    )

    current = pd.read_csv(tmp_path / "this_week.csv").set_index("game_id")
    status = pd.read_json(tmp_path / "status.json", typ="series")

    assert set(current.index) == {"2026_01_DAL_NYG", "2026_01_DEN_KC"}
    assert current.loc["2026_01_DAL_NYG", "final_home_prob"] == 0.37
    assert current.loc["2026_01_DEN_KC", "final_home_prob"] == 0.58
    assert int(status["games"]) == 2


def test_write_outputs_does_not_republish_legacy_same_week_locks(tmp_path):
    pd.DataFrame([_legacy_lock(), _locked_dal()]).to_csv(
        tmp_path / "prediction_history.csv", index=False
    )

    live = _row("2026_01_DEN_KC", "DEN", "KC", 0.58, "2026-09-14T01:00:00+00:00")
    artifacts = SimpleNamespace(
        predictions=pd.DataFrame([live]),
        games=_games("2026_01_NE_SEA", "2026_01_DAL_NYG", "2026_01_DEN_KC"),
    )

    write_outputs(
        artifacts,
        tmp_path,
        now_utc=datetime(2026, 9, 14, 1, 5, tzinfo=timezone.utc),
        lock_window_minutes=0,
    )

    current = pd.read_csv(tmp_path / "this_week.csv").set_index("game_id")
    assert set(current.index) == {"2026_01_DAL_NYG", "2026_01_DEN_KC"}
    assert "2026_01_NE_SEA" not in current.index
