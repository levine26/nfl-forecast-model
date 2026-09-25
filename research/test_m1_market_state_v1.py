from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from research.m1_market_contract_v1 import (
    DIAGNOSTIC_ONLY_PREFIXES,
    PREDICTOR_FEATURE_COLUMNS,
    due_fixed_horizons,
    latest_prekick_due,
)
from research.m1_market_state_v1 import build_diagnostic_row, build_predictor_row

KICKOFF = datetime(2026, 10, 4, 20, 0, tzinfo=timezone.utc)


def _row(
    horizon: str,
    minutes: int,
    book: str,
    *,
    home_spread: float,
    spread_prob: float,
    ml_prob: float,
    total: float = 47.5,
    freshness: float = 5.0,
    request_offset_minutes: float = -2.0,
) -> dict:
    target = KICKOFF - timedelta(minutes=minutes)
    request = target + timedelta(minutes=request_offset_minutes)
    return {
        "row_type": "book",
        "game_id": "2026_04_TEST",
        "market_provider": "fixture",
        "event_id": "evt-1",
        "provider_commence_time_utc": KICKOFF.isoformat(),
        "provider_kickoff_delta_minutes": 0.0,
        "home_team": "HOME",
        "away_team": "AWAY",
        "kickoff_timestamp_utc": KICKOFF.isoformat(),
        "horizon": horizon,
        "target_timestamp_utc": target.isoformat(),
        "request_timestamp_utc": request.isoformat(),
        "timing_error_minutes": request_offset_minutes,
        "sportsbook_key": book,
        "sportsbook_title": book,
        "sportsbook_last_update_utc": (request - timedelta(minutes=freshness)).isoformat(),
        "freshness_minutes": freshness,
        "home_spread": home_spread,
        "spread_home_cover_no_vig": spread_prob,
        "h2h_home_no_vig": ml_prob,
        "total_points": total,
        "research_only": True,
        "production_authorized": False,
    }


def _fixture() -> list[dict]:
    rows: list[dict] = []
    for horizon, minutes in (("T-2160m", 2160), ("T-720m", 720)):
        rows += [
            _row(horizon, minutes, "book_a", home_spread=-2.5, spread_prob=0.50, ml_prob=0.58),
            _row(horizon, minutes, "book_b", home_spread=-3.0, spread_prob=0.51, ml_prob=0.59),
        ]
    rows += [
        _row("T-360m", 360, "book_a", home_spread=-2.5, spread_prob=0.50, ml_prob=0.58),
        _row("T-360m", 360, "book_b", home_spread=-3.0, spread_prob=0.51, ml_prob=0.59, freshness=20.0),
        _row("T-120m", 120, "book_a", home_spread=-3.5, spread_prob=0.52, ml_prob=0.61),
        _row("T-120m", 120, "book_b", home_spread=-3.0, spread_prob=0.53, ml_prob=0.62, freshness=20.0),
        _row("T-60m", 60, "book_a", home_spread=-4.0, spread_prob=0.54, ml_prob=0.63),
        _row("T-60m", 60, "book_b", home_spread=-4.0, spread_prob=0.55, ml_prob=0.64),
        _row("T-30m", 30, "book_a", home_spread=-4.5, spread_prob=0.56, ml_prob=0.65),
        _row("T-30m", 30, "book_b", home_spread=-4.5, spread_prob=0.57, ml_prob=0.66),
    ]
    return rows


def test_fixed_due_horizons_are_strictly_at_or_before_cutoff() -> None:
    target = KICKOFF - timedelta(minutes=120)
    early = due_fixed_horizons(KICKOFF, target - timedelta(minutes=2))
    assert any(row["horizon"] == "T-120m" for row in early)
    late = due_fixed_horizons(KICKOFF, target + timedelta(seconds=1))
    assert not any(row["horizon"] == "T-120m" for row in late)


def test_latest_prekick_is_strict_and_bounded() -> None:
    assert latest_prekick_due(KICKOFF, KICKOFF - timedelta(minutes=5))
    assert not latest_prekick_due(KICKOFF, KICKOFF - timedelta(seconds=30))
    assert not latest_prekick_due(KICKOFF, KICKOFF - timedelta(minutes=11))
    assert not latest_prekick_due(KICKOFF, KICKOFF)


def test_predictor_materializes_frozen_feature_registry_without_diagnostics() -> None:
    row, audit = build_predictor_row(_fixture(), "2026_04_TEST")
    assert audit["eligible"] is True
    assert row is not None
    assert set(PREDICTOR_FEATURE_COLUMNS).issubset(row)
    assert row["active_book_count_t120"] == 2
    assert row["key_number_crossing_3_or_7_t360_to_t120"] == 1
    assert row["movement_breadth_t360_to_t120"] == pytest.approx(1.0)
    assert row["spread_price_move_unchanged_number_t360_to_t120"] == pytest.approx(0.02)
    assert audit["available_predictor_horizons"] == ["T-2160m", "T-720m", "T-360m", "T-120m"]
    assert all(not key.startswith(DIAGNOSTIC_ONLY_PREFIXES) for key in row)


def test_post_t120_quote_cannot_change_predictor() -> None:
    rows = _fixture()
    baseline, _ = build_predictor_row(rows, "2026_04_TEST")
    late = _row(
        "T-120m",
        120,
        "book_c",
        home_spread=-20.0,
        spread_prob=0.99,
        ml_prob=0.99,
        request_offset_minutes=1.0,
    )
    rows.append(late)
    changed, _ = build_predictor_row(rows, "2026_04_TEST")
    assert changed == baseline


def test_diagnostic_market_state_is_separate_from_predictor() -> None:
    rows = _fixture()
    predictor, _ = build_predictor_row(rows, "2026_04_TEST")
    diagnostics = build_diagnostic_row(rows, "2026_04_TEST")
    assert predictor is not None
    assert diagnostics["t60_consensus_spread"] == -4.0
    assert diagnostics["t30_consensus_spread"] == -4.5
    assert "t60_consensus_spread" not in predictor
    assert "t30_consensus_spread" not in predictor


def test_completed_outcome_rows_are_rejected_and_cannot_influence_features() -> None:
    rows = _fixture()
    baseline, _ = build_predictor_row(rows, "2026_04_TEST")
    contaminated = deepcopy(rows[4])
    contaminated["sportsbook_key"] = "book_outcome"
    contaminated["home_score"] = 99
    contaminated["away_score"] = 0
    contaminated["home_spread"] = -30.0
    rows.append(contaminated)
    changed, _ = build_predictor_row(rows, "2026_04_TEST")
    assert changed == baseline


def test_kickoff_revision_or_event_identity_mismatch_fails_closed() -> None:
    rows = _fixture()
    bad = deepcopy(rows[0])
    bad["horizon"] = "T-120m"
    bad["target_timestamp_utc"] = (KICKOFF - timedelta(minutes=120)).isoformat()
    bad["request_timestamp_utc"] = (KICKOFF - timedelta(minutes=122)).isoformat()
    bad["timing_error_minutes"] = -2.0
    bad["kickoff_timestamp_utc"] = (KICKOFF + timedelta(hours=1)).isoformat()
    rows.append(bad)
    with pytest.raises(ValueError, match="cross-horizon"):
        build_predictor_row(rows, "2026_04_TEST")
