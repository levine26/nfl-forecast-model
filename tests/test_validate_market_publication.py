from __future__ import annotations

import csv
from datetime import datetime, timezone
import json

import pytest

from scripts.validate_market_publication import (
    FROZEN_ID, FROZEN_TRAINING_SHA, FROZEN_IMPLEMENTATION_SHA, validate,
)

NOW = datetime(2026, 10, 30, 14, 0, tzinfo=timezone.utc)
HEADERS = [
    "game_id", "gameday", "gametime", "home_team", "away_team", "pick",
    "final_home_prob", "expected_margin", "spread_line", "prediction_timestamp_utc",
    "final_probability_strategy", "fst_artifact_id", "fst_artifact_training_data_sha256",
    "fst_artifact_freeze_implementation_sha", "fst_fallback", "market_available",
    "market_snapshot_timestamp_utc", "market_snapshot_source", "market_freshness_status",
]


def setup(tmp_path):
    locked = dict.fromkeys(HEADERS, "")
    locked.update(game_id="2026_08_CAR_GB", gameday="2026-10-29", gametime="20:15",
                  home_team="GB", away_team="CAR", pick="GB", final_home_prob="0.6065358419833728",
                  expected_margin="3.204", spread_line="3.5",
                  prediction_timestamp_utc="2026-10-29T23:12:59+00:00")
    live = dict(locked, game_id="2026_08_ARI_DAL", gameday="2026-11-01", gametime="13:00",
                home_team="DAL", away_team="ARI", pick="DAL", final_home_prob="0.713",
                market_snapshot_timestamp_utc="2026-10-30T13:59:00+00:00",
                market_snapshot_source="nflverse_games.csv_moneyline",
                market_freshness_status="refreshed_this_run")
    for row in (locked, live):
        row.update(final_probability_strategy=FROZEN_ID, fst_artifact_id=FROZEN_ID,
                   fst_artifact_training_data_sha256=FROZEN_TRAINING_SHA,
                   fst_artifact_freeze_implementation_sha=FROZEN_IMPLEMENTATION_SHA,
                   fst_fallback="False", market_available="True")
    history = dict(locked, lock_status="LOCKED")
    status = dict(generated_utc="2026-10-30T14:00:00+00:00", status="degraded",
                  slate_completeness_verified=True, expected_week_games=2, games=2,
                  missing_week_game_ids=[], final_probability_strategy=FROZEN_ID,
                  fst_artifact_id=FROZEN_ID, fst_artifact_training_data_sha256=FROZEN_TRAINING_SHA,
                  fst_fallback_count=0, market_available_games=2, market_missing_or_invalid_games=0,
                  locked_official_predictions=1, market_provenance_missing_games=1)
    return [locked, live], [history], status


def run(tmp_path, current, history, status):
    for filename, rows in (("this_week.csv", current), ("prediction_history.csv", history)):
        fields = HEADERS + (["lock_status"] if filename == "prediction_history.csv" else [])
        with (tmp_path / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    (tmp_path / "status.json").write_text(json.dumps(status), encoding="utf-8")
    return validate(tmp_path, now_utc=NOW)


def test_legacy_locked_missing_provenance_does_not_block_fresh_unlocked_games(tmp_path):
    a, h, s = setup(tmp_path)
    assert run(tmp_path, a, h, s) == {
        "slate": 2, "locked": 1, "unlocked": 1, "historical_locked_without_provenance": 1,
    }


@pytest.mark.parametrize("change,expected", [
    ("unlocked_missing", "unlocked forecast lacks fresh"),
    ("locked_drift", "drifted from immutable"),
    ("fallback", "F-ST fallback"),
    ("missing_game", "Unverified or incomplete"),
    ("false_healthy", "Status label contradicts"),
    ("stale_market", "stale/future market"),
    ("artifact", "changed frozen"),
    ("duplicate_id", "Missing/duplicate slate"),
])
def test_guard_fails_closed(tmp_path, change, expected):
    a, h, s = setup(tmp_path)
    if change == "unlocked_missing":
        a[1]["market_snapshot_timestamp_utc"] = ""
    elif change == "locked_drift":
        a[0]["final_home_prob"] = "0.8"
    elif change == "fallback":
        a[1]["fst_fallback"] = "True"
    elif change == "missing_game":
        s["expected_week_games"] = 3
    elif change == "false_healthy":
        s["status"] = "healthy"
    elif change == "stale_market":
        a[1]["market_snapshot_timestamp_utc"] = "2026-10-30T11:00:00+00:00"
    elif change == "artifact":
        a[1]["fst_artifact_id"] = "research-candidate"
    elif change == "duplicate_id":
        a.append(dict(a[1]))
    with pytest.raises(ValueError, match=expected):
        run(tmp_path, a, h, s)
