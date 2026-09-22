from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from research.run_adaptive_candidate4_shadow_v1 import (
    due_candidate4_cohorts,
    run,
)


def _feed() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_03_LAC_BUF",
            "season": 2026,
            "week": 3,
            "gameday": "2026-09-27",
            "gametime": "13:00",
            "away_team": "LAC",
            "home_team": "BUF",
        }
    ])


def _depth() -> pd.DataFrame:
    return pd.DataFrame([
        {"dt": "2026-09-27T14:00:00Z", "team": "BUF", "player_name": "Josh Allen", "gsis_id": "00-0034857", "pos_abb": "QB", "pos_rank": 1},
        {"dt": "2026-09-27T14:00:00Z", "team": "LAC", "player_name": "Justin Herbert", "gsis_id": "00-0036355", "pos_abb": "QB", "pos_rank": 1},
    ])


def _write_archive(root: Path) -> None:
    html = (
        "<html><body>"
        "<h3>BILLS</h3><ul><li>WR Example Receiver</li></ul>"
        "<h3>CHARGERS</h3><ul><li>QB Justin Herbert</li></ul>"
        "</body></html>"
    ).encode()
    sha = hashlib.sha256(html).hexdigest()
    (root / "raw").mkdir(parents=True, exist_ok=True)
    with gzip.open(root / "raw" / f"{sha}.html.gz", "wb") as handle:
        handle.write(html)
    observation = {
        "archive_id": "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1",
        "captured_at_utc": "2026-09-27T15:50:00Z",
        "due_games": [
            {
                "game_id": "2026_03_LAC_BUF",
                "away_team": "LAC",
                "home_team": "BUF",
                "kickoff_utc": "2026-09-27T17:00:00+00:00",
                "minutes_to_kickoff": 70,
            }
        ],
        "sources": [
            {
                "source_kind": "nfl_inactives_news_article",
                "url": "https://www.nfl.com/news/week-3-inactives-test",
                "http_status": 200,
                "raw_body_sha256": sha,
                "raw_object_relpath": f"raw/{sha}.html.gz",
            }
        ],
    }
    (root / "observations.jsonl").write_text(json.dumps(observation) + "\n", encoding="utf-8")


def _market() -> pd.DataFrame:
    rows = []
    for horizon, target, request, probability, update in [
        ("T-120m", "2026-09-27T15:00:00Z", "2026-09-27T14:59:00Z", 0.40, "2026-09-27T14:57:00Z"),
        ("T-60m", "2026-09-27T16:00:00Z", "2026-09-27T15:59:00Z", 0.55, "2026-09-27T15:57:00Z"),
    ]:
        base = {
            "game_id": "2026_03_LAC_BUF",
            "market_provider": "propline",
            "event_id": "evt-lac-buf",
            "provider_commence_time_utc": "2026-09-27T17:00:00+00:00",
            "home_team": "BUF",
            "away_team": "LAC",
            "kickoff_timestamp_utc": "2026-09-27T17:00:00+00:00",
            "horizon": horizon,
            "target_timestamp_utc": target,
            "request_timestamp_utc": request,
            "timing_error_minutes": -1.0,
            "research_only": True,
            "production_authorized": False,
        }
        books = []
        for i in range(5):
            key = f"book-{i}"
            books.append(key)
            p = probability + (i - 2) * 0.002
            rows.append({
                **base,
                "row_type": "book",
                "sportsbook_key": key,
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
            "h2h_home_no_vig": probability,
            "source_count": 5,
            "source_names": "|".join(books),
            "max_freshness_minutes": 2.0,
            "probability_range": 0.008,
        })
    return pd.DataFrame(rows)


def _production() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "game_id": "2026_03_LAC_BUF",
            "season": 2026,
            "week": 3,
            "gameday": "2026-09-27",
            "home_team": "BUF",
            "away_team": "LAC",
            "final_home_prob": 0.46,
            "lock_status": "LOCKED",
            "lock_timestamp_utc": "2026-09-27T15:30:00Z",
            "kickoff_utc": "2026-09-27T17:00:00Z",
            "minutes_to_kickoff_at_lock": 90.0,
            "fst_artifact_id": "F-ST-01-FROZEN-2026",
            "final_probability_strategy": "F-ST-01-FROZEN-2026",
        }
    ])


def test_due_cohort_is_only_sunday_week3_after_t60_retry_window() -> None:
    due = due_candidate4_cohorts(
        _feed(),
        datetime(2026, 9, 27, 16, 10, tzinfo=timezone.utc),
    )
    assert len(due) == 1
    assert due[0][0]["game_id"] == "2026_03_LAC_BUF"

    too_late = due_candidate4_cohorts(
        _feed(),
        datetime(2026, 9, 27, 16, 41, tzinfo=timezone.utc),
    )
    assert too_late == []


def test_live_runner_locks_only_eligible_preoutcome_decision(tmp_path) -> None:
    feed_path = tmp_path / "feed.csv"
    production_path = tmp_path / "prediction_history.csv"
    market_path = tmp_path / "market.csv"
    archive = tmp_path / "inactive"
    output = tmp_path / "candidate4"
    _feed().to_csv(feed_path, index=False)
    _production().to_csv(production_path, index=False)
    _market().to_csv(market_path, index=False)
    _write_archive(archive)

    status = run(
        feed_path=feed_path,
        production_history_path=production_path,
        market_ledger_path=market_path,
        inactive_archive_dir=archive,
        output_dir=output,
        now_utc=datetime(2026, 9, 27, 16, 10, tzinfo=timezone.utc),
        depth_frame=_depth(),
    )
    assert status["eligible_decisions_added"] == 1
    locked = pd.read_csv(output / "candidate4_decisions.csv")
    assert len(locked) == 1
    row = locked.iloc[0]
    assert bool(row["eligible"]) is True
    assert bool(row["candidate_switch"]) is True
    assert row["candidate_pick"] == "BUF"
    assert row["qb_shock_direction"] == 1
    assert row["market_source_qualified"]
    assert row["completed_2026_outcomes_used"] == 0
