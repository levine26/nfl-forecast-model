from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from research.m1_operational_qualification_v1 import (
    PHASE2_OPENED_AT_UTC,
    qualification_rows,
    qualification_summary,
)


def _write_slate(path: Path, *, gameday: str, gametime: str, include_outcomes: bool = False) -> None:
    fields = ["game_id", "gameday", "gametime", "away_team", "home_team"]
    if include_outcomes:
        fields += ["home_score", "away_score", "ats_result"]
    row = {
        "game_id": "2026_03_AAA_BBB",
        "gameday": gameday,
        "gametime": gametime,
        "away_team": "AAA",
        "home_team": "BBB",
        "home_score": "99",
        "away_score": "0",
        "ats_result": "HOME_COVER",
    }
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({key: row[key] for key in fields})


def _write_capture(path: Path, *, horizon: str) -> None:
    fields = ["game_id", "horizon", "row_type", "source_count", "m1_role"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow(
            {
                "game_id": "2026_03_AAA_BBB",
                "horizon": horizon,
                "row_type": "consensus",
                "source_count": "2",
                "m1_role": "predictor" if horizon.startswith("T-2") else "diagnostic_only",
            }
        )


def _state(rows: list[dict[str, object]], horizon: str) -> str:
    return str(next(row for row in rows if row["horizon"] == horizon)["state"])


def test_fixed_horizon_transitions_future_open_missed(tmp_path: Path) -> None:
    slate = tmp_path / "slate.csv"
    ledger = tmp_path / "ledger.csv"
    _write_slate(slate, gameday="2026-09-27", gametime="13:00")

    future = qualification_rows(
        slate_path=slate,
        ledger_path=ledger,
        now_utc=datetime(2026, 9, 25, 20, 0, tzinfo=timezone.utc),
    )
    assert _state(future, "T-2160m") == "future"

    open_window = qualification_rows(
        slate_path=slate,
        ledger_path=ledger,
        now_utc=datetime(2026, 9, 26, 4, 55, tzinfo=timezone.utc),
    )
    assert _state(open_window, "T-2160m") == "capture_window_open"

    missed = qualification_rows(
        slate_path=slate,
        ledger_path=ledger,
        now_utc=datetime(2026, 9, 26, 5, 1, tzinfo=timezone.utc),
    )
    assert _state(missed, "T-2160m") == "missed_no_valid_capture"


def test_qualified_consensus_closes_fixed_horizon(tmp_path: Path) -> None:
    slate = tmp_path / "slate.csv"
    ledger = tmp_path / "ledger.csv"
    _write_slate(slate, gameday="2026-09-27", gametime="13:00")
    _write_capture(ledger, horizon="T-2160m")

    rows = qualification_rows(
        slate_path=slate,
        ledger_path=ledger,
        now_utc=datetime(2026, 9, 26, 5, 1, tzinfo=timezone.utc),
    )
    assert _state(rows, "T-2160m") == "captured"


def test_pre_phase2_horizons_are_not_counted_as_misses(tmp_path: Path) -> None:
    slate = tmp_path / "slate.csv"
    ledger = tmp_path / "ledger.csv"
    _write_slate(slate, gameday="2026-09-24", gametime="20:15")

    rows = qualification_rows(
        slate_path=slate,
        ledger_path=ledger,
        now_utc=datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc),
    )
    assert all(row["state"] == "pre_phase2_boundary" for row in rows)
    summary = qualification_summary(rows)
    assert summary["missed_fixed_horizons"] == 0
    assert summary["phase2_eligible_fixed_horizons"] == 0


def test_outcome_columns_are_ignored_and_never_enter_artifact(tmp_path: Path) -> None:
    slate = tmp_path / "slate.csv"
    ledger = tmp_path / "ledger.csv"
    _write_slate(slate, gameday="2026-09-27", gametime="13:00", include_outcomes=True)

    rows = qualification_rows(
        slate_path=slate,
        ledger_path=ledger,
        now_utc=PHASE2_OPENED_AT_UTC,
    )
    assert rows
    assert all("home_score" not in row for row in rows)
    assert all("away_score" not in row for row in rows)
    assert all("ats_result" not in row for row in rows)
    assert all(row["completed_2026_outcomes_used"] == 0 for row in rows)
    summary = qualification_summary(rows)
    assert summary["historical_or_completed_game_outcomes_read"] is False
    assert summary["completed_2026_outcomes_used"] == 0


def test_latest_prekick_remains_diagnostic_only(tmp_path: Path) -> None:
    slate = tmp_path / "slate.csv"
    ledger = tmp_path / "ledger.csv"
    _write_slate(slate, gameday="2026-09-27", gametime="13:00")

    rows = qualification_rows(
        slate_path=slate,
        ledger_path=ledger,
        now_utc=datetime(2026, 9, 27, 16, 55, tzinfo=timezone.utc),
    )
    latest = next(row for row in rows if row["horizon"] == "LATEST_PREKICK")
    assert latest["state"] == "capture_window_open"
    assert latest["role"] == "diagnostic_only"
