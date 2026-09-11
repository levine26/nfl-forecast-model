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


def test_locked_row_overrides_later_mutable_forecast():
    gid = "2026_01_AAA_BBB"
    current = pd.DataFrame(
        [
            _row(gid, "AAA", "BBB", 0.41, "AAA"),
            _row("2026_01_CCC_DDD", "CCC", "DDD", 0.62, "DDD"),
        ]
    )
    locked = _row(gid, "AAA", "BBB", 0.64, "BBB")
    locked.update(
        {
            "lock_status": "LOCKED",
            "lock_timestamp_utc": "2026-09-13T15:05:00+00:00",
            "kickoff_utc": "2026-09-13T17:00:00+00:00",
            "minutes_to_kickoff_at_lock": 115.0,
        }
    )
    official = pd.DataFrame([locked])

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


def test_refuses_post_kickoff_live_replacement_without_lock():
    current = pd.DataFrame([_row("2026_01_AAA_BBB", "AAA", "BBB", 0.61, "BBB")])
    official = pd.DataFrame(columns=["game_id", "lock_status"])

    with pytest.raises(PublicForecastError, match="kickoff has passed without an immutable pregame lock"):
        MODULE.build_canonical_editorial_predictions(
            current,
            official,
            now_utc=datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc),
        )
