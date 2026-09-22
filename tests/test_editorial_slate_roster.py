from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh_editorial_slate_roster.py"
SPEC = importlib.util.spec_from_file_location("refresh_editorial_slate_roster", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _row(game_id: str, gameday: str, gametime: str = "13:00", *, locked: bool = False) -> dict:
    return {
        "game_id": game_id,
        "season": 2026,
        "week": 2,
        "gameday": gameday,
        "gametime": gametime,
        "lock_status": "LOCKED" if locked else "",
    }


def test_derives_weekend_roster_from_live_and_locked_rows() -> None:
    current = pd.DataFrame([
        _row("2026_02_NYG_LA", "2026-09-21", "20:15"),
    ])
    official = pd.DataFrame([
        _row("2026_02_DET_BUF", "2026-09-17", "20:15", locked=True),
        _row("2026_02_CAR_ATL", "2026-09-20", "13:00", locked=True),
        _row("2026_02_IND_KC", "2026-09-20", "20:20", locked=True),
    ])

    roster = MODULE.build_roster(
        current,
        official,
        {},
        now_utc=datetime(2026, 9, 21, 23, 0, tzinfo=timezone.utc),
    )

    assert roster["frozen"] is True
    assert roster["game_ids"] == [
        "2026_02_CAR_ATL",
        "2026_02_IND_KC",
        "2026_02_NYG_LA",
    ]
    assert "2026_02_DET_BUF" not in roster["game_ids"]


def test_includes_saturday_games_in_weekend_roster() -> None:
    current = pd.DataFrame([
        _row("2026_02_SAT_GAME", "2026-09-19", "16:30"),
        _row("2026_02_SUN_GAME", "2026-09-20", "13:00"),
        _row("2026_02_MON_GAME", "2026-09-21", "20:15"),
        _row("2026_02_THU_GAME", "2026-09-17", "20:15"),
    ])

    roster = MODULE.build_roster(
        current,
        pd.DataFrame(columns=current.columns),
        {},
        now_utc=datetime(2026, 9, 18, 18, 0, tzinfo=timezone.utc),
    )

    assert roster["frozen"] is False
    assert roster["game_ids"] == [
        "2026_02_SAT_GAME",
        "2026_02_SUN_GAME",
        "2026_02_MON_GAME",
    ]


def test_frozen_roster_survives_complete_current_contraction() -> None:
    existing = {
        "schema_version": 1,
        "season": 2026,
        "week": 2,
        "timezone": "America/Los_Angeles",
        "weekend_start_local": "2026-09-19T00:00:00-07:00",
        "frozen": True,
        "generated_utc": "2026-09-19T07:00:00+00:00",
        "game_ids": ["2026_02_CAR_ATL", "2026_02_NYG_LA"],
        "policy": "test",
    }

    roster = MODULE.build_roster(
        pd.DataFrame(),
        pd.DataFrame(),
        existing,
        now_utc=datetime(2026, 9, 22, 4, 0, tzinfo=timezone.utc),
    )

    assert roster == existing


def test_bootstraps_latest_locked_week_when_current_is_empty() -> None:
    official = pd.DataFrame([
        {
            **_row("2026_01_OLD_GAME", "2026-09-13", locked=True),
            "week": 1,
        },
        _row("2026_02_DET_BUF", "2026-09-17", "20:15", locked=True),
        _row("2026_02_CAR_ATL", "2026-09-20", "13:00", locked=True),
        _row("2026_02_NYG_LA", "2026-09-21", "20:15", locked=True),
    ])

    roster = MODULE.build_roster(
        pd.DataFrame(),
        official,
        {},
        now_utc=datetime(2026, 9, 22, 4, 0, tzinfo=timezone.utc),
    )

    assert roster["season"] == 2026
    assert roster["week"] == 2
    assert roster["game_ids"] == ["2026_02_CAR_ATL", "2026_02_NYG_LA"]
