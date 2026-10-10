from datetime import datetime, timedelta, timezone
import csv
import io

import pytest

from nfl_forecast.publish import CURRENT_COLUMNS, LOCK_META_COLUMNS
from scripts.fast_official_lock import build_new_receipts

NOW = datetime(2026, 10, 11, 11, 35, tzinfo=timezone.utc)
COLUMNS = list(dict.fromkeys(CURRENT_COLUMNS + LOCK_META_COLUMNS))


def csv_text(columns, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, columns, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in columns})
    return stream.getvalue()


def game(gid, *, prediction_minutes_ago=20, final_prob="0.68"):
    return {
        "game_id": gid,
        "season": "2026",
        "week": "5",
        "gameday": "2026-10-11",
        "gametime": "09:30",
        "away_team": "PHI",
        "home_team": "JAX",
        "pick": "JAX",
        "pure_home_prob": "0.61",
        "market_home_prob": "0.66",
        "final_home_prob": final_prob,
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "prediction_timestamp_utc": (NOW - timedelta(minutes=prediction_minutes_ago)).isoformat(),
        "expected_margin": "3.7",
        "spread_line": "2.5",
        "margin_sigma": "12.89",
        "expected_total": "43.5",
        "snapshot_type": "RUN",
    }


def original_history():
    past = game("2026_05_TB_DAL")
    past.update({
        "lock_status": "LOCKED",
        "lock_timestamp_utc": "2026-10-08T23:55:39.504985+00:00",
        "kickoff_utc": "2026-10-09T00:15:00+00:00",
        "minutes_to_kickoff_at_lock": "19.34158358",
    })
    return csv_text(COLUMNS, [past])


def status():
    return {"fst_artifact_id": "F-ST-01-FROZEN-2026", "locked_official_predictions": 1}


def test_append_at_real_t120_preserves_existing_lock_bytes_and_ats_policy():
    history = original_history()
    feed = csv_text(CURRENT_COLUMNS, [game("2026_05_TB_DAL"), game("2026_05_PHI_JAX")])
    text, state, locked = build_new_receipts(feed, history, status(), NOW)
    assert text.startswith(history)
    assert locked == ["2026_05_PHI_JAX"]
    assert state["locked_official_predictions"] == 2
    rows = list(csv.DictReader(io.StringIO(text)))
    assert len(rows) == 2
    assert rows[0]["lock_timestamp_utc"] == "2026-10-08T23:55:39.504985+00:00"
    fresh = rows[1]
    assert fresh["lock_timestamp_utc"] == NOW.isoformat()
    assert float(fresh["minutes_to_kickoff_at_lock"]) == pytest.approx(115)
    assert fresh["locked_ats_status"] == "VALUE"
    assert fresh["locked_ats_pick_team"] == "JAX"
    assert float(fresh["locked_ats_pick_market_spread"]) == pytest.approx(-2.5)
    again, _, none = build_new_receipts(feed, text, state, NOW + timedelta(minutes=1))
    assert none == []
    assert again == text


def test_never_locks_early_and_never_backdates_after_delayed_dispatch():
    feed = csv_text(CURRENT_COLUMNS, [game("fresh")])
    history = csv_text(COLUMNS, [])
    early, _, rows = build_new_receipts(feed, history, status(), NOW - timedelta(minutes=15))
    assert early == history and not rows
    late, _, ids = build_new_receipts(feed, history, status(), NOW + timedelta(minutes=85))
    assert ids == ["fresh"]
    row = list(csv.DictReader(io.StringIO(late)))[0]
    assert row["lock_timestamp_utc"] == (NOW + timedelta(minutes=85)).isoformat()


def test_rejects_stale_future_or_noncanonical_snapshots():
    history = csv_text(COLUMNS, [])
    for change in (
        {"prediction_timestamp_utc": (NOW - timedelta(minutes=100)).isoformat()},
        {"prediction_timestamp_utc": (NOW + timedelta(minutes=5)).isoformat()},
        {"final_probability_strategy": "unfrozen"},
        {"final_home_prob": "inf"},
        {"pick": "NE"},
    ):
        row = game("bad")
        row.update(change)
        with pytest.raises(ValueError):
            build_new_receipts(csv_text(CURRENT_COLUMNS, [row]), history, status(), NOW)


def test_fails_closed_for_duplicate_ids_and_malformed_history():
    history = csv_text(COLUMNS, [])
    with pytest.raises(ValueError, match="duplicat"):
        build_new_receipts(csv_text(CURRENT_COLUMNS, [game("same"), game("same")]), history, status(), NOW)
    corrupted = original_history() + csv_text(COLUMNS, [game("2026_05_TB_DAL")])
    with pytest.raises(ValueError):
        build_new_receipts(csv_text(CURRENT_COLUMNS, [game("next")]), corrupted, status(), NOW)
