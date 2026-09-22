from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from research.run_adaptive_candidate4_shadow_v1 import (
    PROCESSING_GRACE_MINUTES,
    _ready_game_ids,
    run,
)


def _production() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_03_A_B",
            "season": 2026,
            "week": 3,
            "gameday": "2026-09-27",
            "home_team": "B",
            "away_team": "A",
            "final_home_prob": 0.46,
            "lock_status": "LOCKED",
            "lock_timestamp_utc": "2026-09-27T15:30:00Z",
            "kickoff_utc": "2026-09-27T17:00:00Z",
            "minutes_to_kickoff_at_lock": 90.0,
            "fst_artifact_id": "F-ST-01-FROZEN-2026",
            "final_probability_strategy": "F-ST-01-FROZEN-2026",
        }
    ])


def _market() -> pd.DataFrame:
    rows: list[dict] = []
    books = [f"book-{i}" for i in range(5)]
    for horizon, target, request, home_prob, update in [
        ("T-120m", "2026-09-27T15:00:00Z", "2026-09-27T14:59:00Z", 0.40, "2026-09-27T14:57:00Z"),
        ("T-60m", "2026-09-27T16:00:00Z", "2026-09-27T15:59:00Z", 0.55, "2026-09-27T15:57:00Z"),
    ]:
        base = {
            "game_id": "2026_03_A_B",
            "market_provider": "propline",
            "event_id": "evt-a-b",
            "provider_commence_time_utc": "2026-09-27T17:00:00+00:00",
            "home_team": "B",
            "away_team": "A",
            "kickoff_timestamp_utc": "2026-09-27T17:00:00+00:00",
            "horizon": horizon,
            "target_timestamp_utc": target,
            "request_timestamp_utc": request,
            "timing_error_minutes": -1.0,
            "research_only": True,
            "production_authorized": False,
        }
        for i, book in enumerate(books):
            p = home_prob + (i - 2) * 0.002
            rows.append({
                **base,
                "row_type": "book",
                "sportsbook_key": book,
                "h2h_home_no_vig": p,
                "home_moneyline": -110 if p >= 0.5 else 120,
                "away_moneyline": 100 if p >= 0.5 else -130,
                "sportsbook_last_update_utc": update,
                "freshness_minutes": 2.0,
            })
        rows.append({
            **base,
            "row_type": "consensus",
            "sportsbook_key": "sportsbook_consensus",
            "h2h_home_no_vig": home_prob,
            "source_count": 5,
            "source_names": "|".join(books),
            "max_freshness_minutes": 2.0,
            "probability_range": 0.008,
        })
    return pd.DataFrame(rows)


def _qb() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_03_A_B",
            "qb_state_complete": True,
            "source_qualified": True,
            "research_only": True,
            "production_authorized": False,
            "qb_shock_direction": 1,
            "qb_shock_known_by_utc": "2026-09-27T15:50:00Z",
            "home_t120_qb1_player_name": "Home Quarterback",
            "home_t120_qb1_gsis_id": "00-0000002",
            "home_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "away_t120_qb1_player_name": "Away Quarterback",
            "away_t120_qb1_gsis_id": "00-0000001",
            "away_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "inactive_raw_sha256": "a" * 64,
            "inactive_capture_timestamp_utc": "2026-09-27T15:50:00Z",
        }
    ])


def test_ready_gate_waits_for_processing_grace() -> None:
    before = _ready_game_ids(
        _production(),
        _market(),
        _qb(),
        now_utc=datetime(2026, 9, 27, 16, 14, tzinfo=timezone.utc),
    )
    ready = _ready_game_ids(
        _production(),
        _market(),
        _qb(),
        now_utc=datetime(2026, 9, 27, 16, PROCESSING_GRACE_MINUTES, tzinfo=timezone.utc),
    )
    assert before == set()
    assert ready == {"2026_03_A_B"}


def test_ready_gate_requires_both_primary_market_horizons() -> None:
    market = _market()
    market = market[~market["horizon"].eq("T-60m")]
    ready = _ready_game_ids(
        _production(),
        market,
        _qb(),
        now_utc=datetime(2026, 9, 27, 16, 20, tzinfo=timezone.utc),
    )
    assert ready == set()


def test_runner_locks_one_replay_stable_candidate4_row(tmp_path) -> None:
    production_path = tmp_path / "production.csv"
    market_path = tmp_path / "market.csv"
    qb_path = tmp_path / "qb.csv"
    output_path = tmp_path / "candidate4" / "decision_ledger.csv"
    _production().to_csv(production_path, index=False)
    _market().to_csv(market_path, index=False)
    _qb().to_csv(qb_path, index=False)

    first = run(
        production_history_path=production_path,
        market_ledger_path=market_path,
        qb_state_path=qb_path,
        output_path=output_path,
        now_utc=datetime(2026, 9, 27, 16, 15, tzinfo=timezone.utc),
    )
    assert first["rows_added"] == 1
    assert first["eligible_rows_total"] == 1
    assert first["switches_total"] == 1

    locked = pd.read_csv(output_path)
    assert len(locked) == 1
    assert bool(locked.iloc[0]["eligible"]) is True
    assert locked.iloc[0]["candidate_pick"] == "B"

    second = run(
        production_history_path=production_path,
        market_ledger_path=market_path,
        qb_state_path=qb_path,
        output_path=output_path,
        now_utc=datetime(2026, 9, 27, 16, 20, tzinfo=timezone.utc),
    )
    assert second["rows_added"] == 0
    assert len(pd.read_csv(output_path)) == 1
