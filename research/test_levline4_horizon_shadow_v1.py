from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.fst_production import frozen_fst_probability, load_fst_artifact
from research.levline4_horizon_shadow_v1 import (
    FST_HORIZON_CANDIDATE_ID,
    MARKET_CANDIDATE_ID,
    build_shadow_ledger,
)


def _consensus(
    *,
    horizon: str = "T-45m",
    request: str = "2026-09-13T16:15:00Z",
    target: str = "2026-09-13T16:15:00Z",
    kickoff: str = "2026-09-13T17:00:00Z",
    probability: float = 0.62,
    source_count: int = 4,
    timing_error: float = 0.0,
) -> dict:
    return {
        "row_type": "consensus",
        "game_id": "2026_01_A_B",
        "event_id": "evt-1",
        "home_team": "B",
        "away_team": "A",
        "kickoff_timestamp_utc": kickoff,
        "horizon": horizon,
        "target_timestamp_utc": target,
        "request_timestamp_utc": request,
        "timing_error_minutes": timing_error,
        "sportsbook_key": "sportsbook_consensus",
        "h2h_home_no_vig": probability,
        "source_count": source_count,
        "source_names": "book1|book2|book3|book4",
        "max_freshness_minutes": 3.0,
        "probability_range": 0.025,
        "research_only": True,
        "production_authorized": False,
    }


def _lock(*, pure: float = 0.57, timestamp: str = "2026-09-13T15:01:00Z") -> dict:
    return {
        "game_id": "2026_01_A_B",
        "lock_status": "LOCKED",
        "lock_timestamp_utc": timestamp,
        "fst_pure_home_prob": pure,
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "model_version": "0.9.0-fst",
    }


def test_builds_market_and_fst_candidates_from_same_horizon() -> None:
    market = pd.DataFrame([_consensus()])
    history = pd.DataFrame([_lock()])
    ledger = build_shadow_ledger(
        market,
        history,
        generated_at_utc="2026-09-13T16:16:00Z",
    )
    assert set(ledger["candidate_id"]) == {
        MARKET_CANDIDATE_ID,
        FST_HORIZON_CANDIDATE_ID,
    }
    market_row = ledger.loc[ledger["candidate_id"].eq(MARKET_CANDIDATE_ID)].iloc[0]
    fst_row = ledger.loc[ledger["candidate_id"].eq(FST_HORIZON_CANDIDATE_ID)].iloc[0]
    assert market_row["final_home_prob"] == pytest.approx(0.62)
    expected = frozen_fst_probability(
        np.asarray([0.62]), np.asarray([0.57]), load_fst_artifact()
    )[0]
    assert fst_row["final_home_prob"] == pytest.approx(float(expected))
    assert fst_row["pure_home_prob"] == pytest.approx(0.57)
    assert fst_row["market_home_prob"] == pytest.approx(0.62)
    assert fst_row["completed_2026_outcomes_used"] == 0
    assert bool(fst_row["production_authorized"]) is False


def test_first_qualified_consensus_is_immutable_source() -> None:
    market = pd.DataFrame(
        [
            _consensus(
                request="2026-09-13T16:14:00Z",
                probability=0.61,
                timing_error=-1.0,
            ),
            _consensus(
                request="2026-09-13T16:16:00Z",
                probability=0.67,
                timing_error=1.0,
            ),
        ]
    )
    ledger = build_shadow_ledger(
        market,
        pd.DataFrame([_lock()]),
        generated_at_utc="2026-09-13T16:17:00Z",
    )
    assert set(ledger["market_home_prob"].round(8)) == {0.61}
    assert set(ledger["market_snapshot_request_timestamp_utc"]) == {
        "2026-09-13T16:14:00+00:00"
    }


def test_fst_candidate_waits_for_official_locked_pure() -> None:
    market = pd.DataFrame([_consensus()])
    without_lock = build_shadow_ledger(
        market,
        pd.DataFrame(),
        generated_at_utc="2026-09-13T16:16:00Z",
    )
    assert list(without_lock["candidate_id"]) == [MARKET_CANDIDATE_ID]

    with_lock = build_shadow_ledger(
        market,
        pd.DataFrame([_lock()]),
        existing_ledger=without_lock,
        generated_at_utc="2026-09-13T16:20:00Z",
    )
    assert set(with_lock["candidate_id"]) == {
        MARKET_CANDIDATE_ID,
        FST_HORIZON_CANDIDATE_ID,
    }


def test_fst_never_replays_a_later_lock_into_an_earlier_horizon() -> None:
    # The production lock is the first valid refresh *inside* T-120. A lock at T-119
    # cannot be used as if its PURE state had existed at the exact T-120 research target.
    t120_market = pd.DataFrame(
        [
            _consensus(
                horizon="T-120m",
                request="2026-09-13T15:00:00Z",
                target="2026-09-13T15:00:00Z",
            )
        ]
    )
    t120 = build_shadow_ledger(
        t120_market,
        pd.DataFrame([_lock(timestamp="2026-09-13T15:01:00Z")]),
        generated_at_utc="2026-09-13T16:00:00Z",
    )
    assert list(t120["candidate_id"]) == [MARKET_CANDIDATE_ID]

    # The same already-frozen lock is valid evidence for a later T-60 horizon.
    t60_market = pd.DataFrame(
        [
            _consensus(
                horizon="T-60m",
                request="2026-09-13T16:00:00Z",
                target="2026-09-13T16:00:00Z",
            )
        ]
    )
    t60 = build_shadow_ledger(
        t60_market,
        pd.DataFrame([_lock(timestamp="2026-09-13T15:01:00Z")]),
        generated_at_utc="2026-09-13T16:01:00Z",
    )
    assert set(t60["candidate_id"]) == {
        MARKET_CANDIDATE_ID,
        FST_HORIZON_CANDIDATE_ID,
    }


def test_never_backfills_missing_forecast_after_kickoff() -> None:
    ledger = build_shadow_ledger(
        pd.DataFrame([_consensus()]),
        pd.DataFrame([_lock()]),
        generated_at_utc="2026-09-13T17:01:00Z",
    )
    assert ledger.empty


def test_existing_identity_is_never_rewritten() -> None:
    original = build_shadow_ledger(
        pd.DataFrame([_consensus(probability=0.60)]),
        pd.DataFrame([_lock(pure=0.55)]),
        generated_at_utc="2026-09-13T16:16:00Z",
    )
    changed_inputs = pd.DataFrame(
        [
            _consensus(
                request="2026-09-13T16:14:00Z",
                probability=0.72,
                timing_error=-1.0,
            )
        ]
    )
    replay = build_shadow_ledger(
        changed_inputs,
        pd.DataFrame([_lock(pure=0.80)]),
        existing_ledger=original,
        generated_at_utc="2026-09-13T16:25:00Z",
    )
    pd.testing.assert_frame_equal(
        replay.reset_index(drop=True), original.reset_index(drop=True)
    )


def test_unqualified_market_rows_fail_closed() -> None:
    market = pd.DataFrame(
        [
            _consensus(source_count=1),
            _consensus(
                request="2026-09-13T16:30:00Z",
                timing_error=15.0,
                probability=0.63,
            ),
        ]
    )
    ledger = build_shadow_ledger(
        market,
        pd.DataFrame([_lock()]),
        generated_at_utc="2026-09-13T16:31:00Z",
    )
    assert ledger.empty


def test_duplicate_existing_identity_is_rejected() -> None:
    base = build_shadow_ledger(
        pd.DataFrame([_consensus()]),
        pd.DataFrame([_lock()]),
        generated_at_utc=datetime(2026, 9, 13, 16, 16, tzinfo=timezone.utc),
    )
    duplicated = pd.concat([base, base.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate identities"):
        build_shadow_ledger(
            pd.DataFrame([_consensus()]),
            pd.DataFrame([_lock()]),
            existing_ledger=duplicated,
            generated_at_utc="2026-09-13T16:20:00Z",
        )
