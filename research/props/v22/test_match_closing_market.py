from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "match_closing_market.py"
SPEC = importlib.util.spec_from_file_location("match_closing_market", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

FORECAST = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
KICKOFF = datetime(2026, 9, 27, 20, 0, tzinfo=timezone.utc)


def _receipt(
    *,
    source_sha: str = "a" * 64,
    game_id: str = "2026_03_A_B",
    player_id: str = "p1",
    prop_type: str = "receiving_yards",
    market_line: float | None = 64.5,
    market_probability: float | None = 0.52,
    model_probability: float | None = 0.61,
    forecast: datetime = FORECAST,
    kickoff: datetime = KICKOFF,
    outcome=None,
):
    return {
        "contract_version": "levline-props-2.2-prereg-v0.2",
        "challenger_id": "P21_BASE",
        "source_props21_forecast_id": "p21_f1",
        "source_props21_forecast_sha256": source_sha,
        "game_id": game_id,
        "player_id": player_id,
        "prop_type": prop_type,
        "kickoff_utc": kickoff.isoformat(),
        "forecast_timestamp_utc": forecast.isoformat(),
        "chronology": {
            "market_capture_utc": (forecast - timedelta(minutes=1)).isoformat(),
        },
        "line": {
            "market_line": market_line,
            "model_fair_line": 68.0,
        },
        "probability": {
            "kind": "over" if prop_type not in MODULE.BINARY_TD_MARKETS else "td",
            "market_probability": market_probability,
            "model_probability": model_probability,
        },
        "research_only": True,
        "production_authorized": False,
        "outcome": outcome,
    }


def _archive(
    captured: datetime,
    *,
    snapshot_id: str,
    game_id: str = "2026_03_A_B",
    player_id: str = "p1",
    prop_type: str = "receiving_yards",
    consensus_line: float | None = 64.5,
    p_over: float | None = 0.52,
    books=None,
    kickoff: datetime = KICKOFF,
):
    artifact = {
        "consensus_line": consensus_line,
        "consensus_no_vig_p_over": p_over,
        "consensus_no_vig_p_under": None if p_over is None else 1.0 - p_over,
        "sportsbook_count": 2,
        "line_range": 1.0,
        "line_stddev": 0.5,
        "individual_books": books
        if books is not None
        else [
            {
                "sportsbook_key": "book_a",
                "line": consensus_line,
                "over_american": -110,
                "under_american": -110,
            },
            {
                "sportsbook_key": "book_b",
                "line": consensus_line,
                "over_american": -105,
                "under_american": -115,
            },
        ],
    }
    return {
        "contract_version": MODULE.ARCHIVE_CONTRACT_VERSION,
        "snapshot_id": snapshot_id,
        "source_workflow_run": "123",
        "source_head_sha": "b" * 40,
        "source_trigger_head_sha": "c" * 40,
        "source_market_provider": "the_odds_api",
        "source_market_credential_mode": "configured",
        "source_provenance_sha256": "d" * 64,
        "captured_at_utc": captured.isoformat(),
        "kickoff_utc": kickoff.isoformat(),
        "minutes_to_kickoff": (kickoff - captured).total_seconds() / 60.0,
        "game_id": game_id,
        "player_id": player_id,
        "prop_type": prop_type,
        "market_artifact_sha256": f"hash-{snapshot_id}",
        "market_artifact": artifact,
        "research_only": True,
        "production_authorized": False,
    }


def test_selects_latest_valid_capture_after_forecast_before_kickoff():
    source = MODULE.collapse_source_forecasts([_receipt()])[0]
    rows = [
        _archive(FORECAST - timedelta(minutes=1), snapshot_id="original"),
        _archive(FORECAST + timedelta(hours=1), snapshot_id="middle", consensus_line=65.5),
        _archive(KICKOFF - timedelta(minutes=3), snapshot_id="close", consensus_line=66.5),
    ]
    selected = MODULE.select_closing_row(source, rows)
    assert selected is not None
    assert selected["snapshot_id"] == "close"


def test_deterministic_tie_breaker_uses_snapshot_then_artifact_sha():
    source = MODULE.collapse_source_forecasts([_receipt()])[0]
    stamp = KICKOFF - timedelta(minutes=5)
    rows = [
        _archive(stamp, snapshot_id="aaa", consensus_line=65.5),
        _archive(stamp, snapshot_id="bbb", consensus_line=66.5),
    ]
    selected = MODULE.select_closing_row(source, rows)
    assert selected is not None
    assert selected["snapshot_id"] == "bbb"


def test_post_kickoff_archive_row_fails_closed():
    rows = [_archive(KICKOFF + timedelta(seconds=1), snapshot_id="late")]
    with pytest.raises(MODULE.ClosingMarketError, match="non-pregame"):
        MODULE.build_events(
            [_receipt()],
            rows,
            as_of=KICKOFF + timedelta(hours=2),
        )


def test_wrong_identity_does_not_match():
    rows = [
        _archive(
            KICKOFF - timedelta(minutes=3),
            snapshot_id="wrong",
            player_id="other-player",
        )
    ]
    events, counts = MODULE.build_events(
        [_receipt()],
        rows,
        as_of=KICKOFF + timedelta(hours=2),
    )
    assert events == []
    assert counts["unmatched_after_settlement"] == 1


def test_kickoff_mismatch_for_exact_identity_fails_closed():
    rows = [
        _archive(
            KICKOFF - timedelta(minutes=3),
            snapshot_id="bad-kickoff",
            kickoff=KICKOFF + timedelta(hours=1),
        )
    ]
    with pytest.raises(MODULE.ClosingMarketError, match="kickoff mismatch"):
        MODULE.build_events(
            [_receipt()],
            rows,
            as_of=KICKOFF + timedelta(hours=2),
        )


def test_builds_positive_over_line_clv_and_same_threshold_price_clv():
    original_books = [
        {
            "sportsbook_key": "book_a",
            "line": 64.5,
            "over_american": -105,
            "under_american": -115,
        },
        {
            "sportsbook_key": "book_b",
            "line": 64.5,
            "over_american": -110,
            "under_american": -110,
        },
    ]
    close_books = [
        {
            "sportsbook_key": "book_a",
            "line": 64.5,
            "over_american": -125,
            "under_american": 105,
        },
        {
            "sportsbook_key": "book_b",
            "line": 66.5,
            "over_american": -110,
            "under_american": -110,
        },
    ]
    rows = [
        _archive(
            FORECAST - timedelta(minutes=1),
            snapshot_id="original",
            consensus_line=64.5,
            p_over=0.52,
            books=original_books,
        ),
        _archive(
            KICKOFF - timedelta(minutes=2),
            snapshot_id="close",
            consensus_line=66.5,
            p_over=0.58,
            books=close_books,
        ),
    ]
    events, counts = MODULE.build_events(
        [_receipt()],
        rows,
        as_of=KICKOFF + timedelta(hours=2),
    )
    assert counts["matched_closing_events"] == 1
    event = events[0]
    assert event["frozen_model_side"] == "over"
    assert event["line_clv"]["side_oriented_line_clv"] == pytest.approx(2.0)
    price = event["same_threshold_price_clv"]
    assert price["available"] is True
    assert price["threshold"] == pytest.approx(64.5)
    assert price["original_best_price"]["american"] == pytest.approx(-105)
    assert price["closing_best_price"]["american"] == pytest.approx(-125)
    assert price["decimal_odds_clv_original_minus_close"] > 0
    assert price["implied_probability_clv_pp_close_minus_original"] > 0


def test_same_threshold_price_clv_unavailable_when_close_drops_original_threshold():
    rows = [
        _archive(
            FORECAST - timedelta(minutes=1),
            snapshot_id="original",
            consensus_line=64.5,
            p_over=0.52,
        ),
        _archive(
            KICKOFF - timedelta(minutes=2),
            snapshot_id="close",
            consensus_line=66.5,
            p_over=0.58,
            books=[
                {
                    "sportsbook_key": "book_a",
                    "line": 66.5,
                    "over_american": -110,
                    "under_american": -110,
                }
            ],
        ),
    ]
    events, _ = MODULE.build_events(
        [_receipt()],
        rows,
        as_of=KICKOFF + timedelta(hours=2),
    )
    assert events[0]["line_clv"]["available"] is True
    assert events[0]["same_threshold_price_clv"]["available"] is False


def test_under_side_orients_line_clv_correctly():
    rows = [
        _archive(FORECAST - timedelta(minutes=1), snapshot_id="original"),
        _archive(
            KICKOFF - timedelta(minutes=2),
            snapshot_id="close",
            consensus_line=62.5,
            p_over=0.45,
        ),
    ]
    events, _ = MODULE.build_events(
        [_receipt(model_probability=0.40)],
        rows,
        as_of=KICKOFF + timedelta(hours=2),
    )
    assert events[0]["frozen_model_side"] == "under"
    assert events[0]["line_clv"]["side_oriented_line_clv"] == pytest.approx(2.0)


def test_td_market_has_price_clv_but_no_continuous_line_clv():
    receipt = _receipt(
        prop_type="anytime_td",
        market_line=None,
        market_probability=0.42,
        model_probability=0.58,
    )
    original = _archive(
        FORECAST - timedelta(minutes=1),
        snapshot_id="original",
        prop_type="anytime_td",
        consensus_line=None,
        p_over=0.42,
        books=[
            {"sportsbook_key": "book_a", "yes_american": 140, "no_american": -160}
        ],
    )
    close = _archive(
        KICKOFF - timedelta(minutes=2),
        snapshot_id="close",
        prop_type="anytime_td",
        consensus_line=None,
        p_over=0.50,
        books=[
            {"sportsbook_key": "book_a", "yes_american": 110, "no_american": -130}
        ],
    )
    events, _ = MODULE.build_events(
        [receipt],
        [original, close],
        as_of=KICKOFF + timedelta(hours=2),
    )
    event = events[0]
    assert event["frozen_model_side"] == "yes"
    assert event["line_clv"]["available"] is False
    assert event["same_threshold_price_clv"]["available"] is True


def test_settlement_grace_prevents_premature_immutable_close():
    rows = [
        _archive(FORECAST - timedelta(minutes=1), snapshot_id="original"),
        _archive(KICKOFF - timedelta(minutes=2), snapshot_id="close"),
    ]
    events, counts = MODULE.build_events(
        [_receipt()],
        rows,
        as_of=KICKOFF + timedelta(minutes=30),
    )
    assert events == []
    assert counts["pending_archive_settlement_grace"] == 1


def test_week2_backfill_is_rejected():
    old_forecast = MODULE.CAPTURE_NOT_BEFORE_UTC - timedelta(seconds=1)
    old_kickoff = old_forecast + timedelta(hours=3)
    with pytest.raises(MODULE.ClosingMarketError, match="predates Props 2.2"):
        MODULE.build_events(
            [_receipt(forecast=old_forecast, kickoff=old_kickoff)],
            [],
            as_of=old_kickoff + timedelta(hours=2),
        )


def test_outcome_bearing_receipt_is_rejected():
    with pytest.raises(MODULE.ClosingMarketError, match="outcome-bearing"):
        MODULE.collapse_source_forecasts([_receipt(outcome=123.0)])


def test_conflicting_source_receipt_identity_fails_closed():
    first = _receipt()
    second = _receipt()
    second["challenger_id"] = "P22_COMBINED_25"
    second["line"]["market_line"] = 65.5
    with pytest.raises(MODULE.ClosingMarketError, match="conflicting Props 2.2 source identity"):
        MODULE.collapse_source_forecasts([first, second])


def test_immutable_closing_event_conflict_fails_closed(tmp_path):
    output = tmp_path / "closing.jsonl"
    row = {
        "source_props21_forecast_sha256": "a" * 64,
        "closing_event_sha256": "1" * 64,
    }
    assert MODULE.append_immutable(output, [row])["appended"] == 1
    assert MODULE.append_immutable(output, [row])["replayed"] == 1
    conflict = dict(row)
    conflict["closing_event_sha256"] = "2" * 64
    with pytest.raises(MODULE.ClosingMarketError, match="immutable closing event conflict"):
        MODULE.append_immutable(output, [conflict])
