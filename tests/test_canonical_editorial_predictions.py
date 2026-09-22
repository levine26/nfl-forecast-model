from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from nfl_forecast.public_forecast import PublicForecastError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_canonical_editorial_predictions.py"
SPEC = importlib.util.spec_from_file_location("canonical_editorial_predictions", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row(game_id: str, away: str, home: str, probability: float, pick: str) -> dict:
    return {
        "game_id": game_id,
        "season": 2026,
        "week": 1,
        "gameday": "2026-09-13",
        "gametime": "13:00",
        "away_team": away,
        "home_team": home,
        "final_home_prob": probability,
        "pick": pick,
        "margin_sigma": 13.0,
        "expected_margin": 2.0 if probability > 0.5 else -2.0,
        "expected_total": 44.0,
        "spread_line": -1.5 if probability > 0.5 else 1.5,
        "total_line": 44.5,
        "prediction_timestamp_utc": "2026-09-13T14:00:00+00:00",
    }


def _locked(row: dict, *, kickoff: str = "2026-09-13T17:00:00+00:00") -> dict:
    locked = dict(row)
    locked.update(
        {
            "lock_status": "LOCKED",
            "lock_timestamp_utc": "2026-09-13T15:05:00+00:00",
            "kickoff_utc": kickoff,
            "minutes_to_kickoff_at_lock": 115.0,
        }
    )
    return locked


def test_locked_row_overrides_later_mutable_forecast():
    gid = "2026_01_AAA_BBB"
    current = pd.DataFrame(
        [
            _row(gid, "AAA", "BBB", 0.41, "AAA"),
            _row("2026_01_CCC_DDD", "CCC", "DDD", 0.62, "DDD"),
        ]
    )
    official = pd.DataFrame([_locked(_row(gid, "AAA", "BBB", 0.64, "BBB"))])

    selected = MODULE.build_canonical_editorial_predictions(
        current,
        official,
        now_utc=datetime(2026, 9, 13, 16, 0, tzinfo=timezone.utc),
    ).set_index("game_id")

    assert float(selected.loc[gid, "final_home_prob"]) == pytest.approx(0.64)
    assert selected.loc[gid, "pick"] == "BBB"
    assert selected.loc[gid, "lock_status"] == "LOCKED"
    assert float(selected.loc["2026_01_CCC_DDD", "final_home_prob"]) == pytest.approx(0.62)
    assert selected.loc["2026_01_CCC_DDD", "pick"] == "DDD"


def test_restores_locked_games_dropped_from_contracting_current_slate():
    live = _row("2026_02_NYG_LA", "NYG", "LA", 0.71, "LA")
    live.update({"week": 2, "gameday": "2026-09-21", "gametime": "20:15"})
    extra_live = _row("2026_02_DET_BUF", "DET", "BUF", 0.61, "BUF")
    extra_live.update({"week": 2, "gameday": "2026-09-17", "gametime": "20:15"})

    locked_a = _locked(_row("2026_02_CAR_ATL", "CAR", "ATL", 0.63, "ATL"))
    locked_a.update({"week": 2, "gameday": "2026-09-20", "gametime": "13:00"})

    locked_b = _locked(_row("2026_02_IND_KC", "IND", "KC", 0.66, "KC"))
    locked_b.update({"week": 2, "gameday": "2026-09-20", "gametime": "16:25"})

    excluded_same_week = _locked(_row("2026_02_DET_BUF", "DET", "BUF", 0.61, "BUF"))
    excluded_same_week.update({"week": 2, "gameday": "2026-09-17", "gametime": "20:15"})
    prior_week = _locked(_row("2026_01_AAA_BBB", "AAA", "BBB", 0.61, "BBB"))

    selected = MODULE.build_canonical_editorial_predictions(
        pd.DataFrame([live, extra_live]),
        pd.DataFrame([locked_a, locked_b, excluded_same_week, prior_week]),
        now_utc=datetime(2026, 9, 21, 23, 0, tzinfo=timezone.utc),
        editorial_game_ids={"2026_02_NYG_LA", "2026_02_CAR_ATL", "2026_02_IND_KC"},
    )

    assert selected["game_id"].tolist() == [
        "2026_02_NYG_LA",
        "2026_02_CAR_ATL",
        "2026_02_IND_KC",
    ]
    restored = selected.set_index("game_id")
    assert restored.loc["2026_02_CAR_ATL", "lock_status"] == "LOCKED"
    assert restored.loc["2026_02_IND_KC", "lock_status"] == "LOCKED"
    assert "2026_02_DET_BUF" not in restored.index
    assert "2026_01_AAA_BBB" not in restored.index



def test_loads_top_level_game_preview_roster(tmp_path):
    roster = tmp_path / "game_previews.json"
    roster.write_text(
        """{
  "2026_02_CAR_ATL": {"game_id": "2026_02_CAR_ATL"},
  "2026_02_NYG_LA": {"game_id": "2026_02_NYG_LA"}
}
""",
        encoding="utf-8",
    )

    assert MODULE._load_editorial_game_ids(roster) == {
        "2026_02_CAR_ATL",
        "2026_02_NYG_LA",
    }


def test_refuses_authorized_roster_game_without_live_or_locked_source():
    live = _row("2026_02_NYG_LA", "NYG", "LA", 0.71, "LA")
    live.update({"week": 2, "gameday": "2026-09-21", "gametime": "20:15"})

    with pytest.raises(RuntimeError, match="does not exactly match the authorized roster"):
        MODULE.build_canonical_editorial_predictions(
            pd.DataFrame([live]),
            pd.DataFrame(columns=["game_id", "lock_status"]),
            now_utc=datetime(2026, 9, 21, 23, 0, tzinfo=timezone.utc),
            editorial_game_ids={"2026_02_NYG_LA", "2026_02_CAR_ATL"},
        )


def test_refuses_post_kickoff_live_replacement_without_lock():
    current = pd.DataFrame([_row("2026_01_AAA_BBB", "AAA", "BBB", 0.61, "BBB")])
    official = pd.DataFrame(columns=["game_id", "lock_status"])

    with pytest.raises(PublicForecastError, match="kickoff has passed without an immutable pregame lock"):
        MODULE.build_canonical_editorial_predictions(
            current,
            official,
            now_utc=datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc),
        )
