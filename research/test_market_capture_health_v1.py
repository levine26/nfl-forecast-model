from __future__ import annotations

from datetime import datetime, timezone

from research.market_capture_health_v1 import build_capture_health


def _slate() -> list[dict]:
    return [
        {
            "game_id": "2026_02_DET_BUF",
            "gameday": "2026-09-17",
            "gametime": "20:15",
            "away_team": "DET",
            "home_team": "BUF",
        }
    ]


def _consensus(*, horizon: str, target: str, request: str, timing: float, sources: int = 3) -> dict:
    return {
        "row_type": "consensus",
        "game_id": "2026_02_DET_BUF",
        "horizon": horizon,
        "target_timestamp_utc": target,
        "request_timestamp_utc": request,
        "timing_error_minutes": timing,
        "source_count": sources,
        "source_names": "a|b|c",
        "h2h_home_no_vig": 0.61,
    }


def _row(receipt: dict, horizon: str) -> dict:
    return next(row for row in receipt["rows"] if row["horizon"] == horizon)


def test_not_yet_open_and_window_open_are_distinct() -> None:
    early = build_capture_health(
        _slate(), [], now_utc=datetime(2026, 9, 17, 21, 0, tzinfo=timezone.utc)
    )
    assert _row(early, "T-120m")["status"] == "not_yet_open"

    open_window = build_capture_health(
        _slate(), [], now_utc=datetime(2026, 9, 17, 22, 10, tzinfo=timezone.utc)
    )
    assert _row(open_window, "T-120m")["status"] == "window_open"
    assert open_window["strict_window_minutes"] == [-7.5, 0.0]


def test_uncaptured_state_becomes_missed_immediately_after_cutoff() -> None:
    receipt = build_capture_health(
        _slate(), [], now_utc=datetime(2026, 9, 17, 22, 15, 1, tzinfo=timezone.utc)
    )
    row = _row(receipt, "T-120m")
    assert row["status"] == "missed_window"
    assert row["late_backfill_authorized"] is False
    assert "2026_02_DET_BUF:T-120m" in receipt["missed_horizon_ids"]


def test_strict_pre_cutoff_consensus_counts_as_captured() -> None:
    ledger = [
        _consensus(
            horizon="T-120m",
            target="2026-09-17T22:15:00+00:00",
            request="2026-09-17T22:10:00+00:00",
            timing=-5.0,
        )
    ]
    receipt = build_capture_health(
        _slate(), ledger, now_utc=datetime(2026, 9, 17, 22, 20, tzinfo=timezone.utc)
    )
    assert _row(receipt, "T-120m")["status"] == "captured_qualified"
    assert receipt["counts"]["captured_qualified"] == 1
    assert receipt["counts"]["missed_window"] == 0
    assert receipt["closed_window_capture_success_rate"] == 1.0


def test_post_cutoff_consensus_is_preserved_as_invalid_and_does_not_repair_missingness() -> None:
    ledger = [
        _consensus(
            horizon="T-120m",
            target="2026-09-17T22:15:00+00:00",
            request="2026-09-17T22:15:01+00:00",
            timing=1.0 / 60.0,
        )
    ]
    receipt = build_capture_health(
        _slate(), ledger, now_utc=datetime(2026, 9, 17, 22, 20, tzinfo=timezone.utc)
    )
    assert _row(receipt, "T-120m")["status"] == "missed_window"
    assert receipt["closed_window_capture_success_rate"] == 0.0


def test_insufficient_book_consensus_does_not_close_horizon() -> None:
    ledger = [
        _consensus(
            horizon="T-120m",
            target="2026-09-17T22:15:00+00:00",
            request="2026-09-17T22:10:00+00:00",
            timing=-5.0,
            sources=1,
        )
    ]
    receipt = build_capture_health(
        _slate(), ledger, now_utc=datetime(2026, 9, 17, 22, 20, tzinfo=timezone.utc)
    )
    assert _row(receipt, "T-120m")["status"] == "missed_window"


def test_target_identity_and_recorded_timing_must_agree() -> None:
    wrong_target = [
        _consensus(
            horizon="T-120m",
            target="2026-09-17T22:16:00+00:00",
            request="2026-09-17T22:10:00+00:00",
            timing=-6.0,
        )
    ]
    receipt = build_capture_health(
        _slate(), wrong_target, now_utc=datetime(2026, 9, 17, 22, 20, tzinfo=timezone.utc)
    )
    assert _row(receipt, "T-120m")["status"] == "missed_window"

    wrong_recorded_error = [
        _consensus(
            horizon="T-120m",
            target="2026-09-17T22:15:00+00:00",
            request="2026-09-17T22:10:00+00:00",
            timing=-4.0,
        )
    ]
    receipt = build_capture_health(
        _slate(), wrong_recorded_error, now_utc=datetime(2026, 9, 17, 22, 20, tzinfo=timezone.utc)
    )
    assert _row(receipt, "T-120m")["status"] == "missed_window"


def test_receipt_is_outcome_blind_and_nonproduction() -> None:
    receipt = build_capture_health(
        _slate(), [], now_utc=datetime(2026, 9, 17, 21, 0, tzinfo=timezone.utc)
    )
    assert receipt["outcome_blind"] is True
    assert receipt["game_outcomes_used"] == 0
    assert receipt["completed_2026_outcomes_used"] == 0
    assert receipt["production_authorized"] is False
    assert receipt["promotion_authorized"] is False
    assert receipt["missingness_policy"] == "missed_horizon_remains_missing_no_late_backfill"
