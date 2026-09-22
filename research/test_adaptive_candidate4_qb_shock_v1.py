from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pandas as pd

from research.adaptive_candidate4_qb_shock_v1 import (
    build_qb_shock_rows,
    build_qb_shock_rows_from_snapshots,
    normalize_name,
)


GAMES = [
    {
        "game_id": "2026_03_LAC_BUF",
        "away_team": "LAC",
        "home_team": "BUF",
        "kickoff_utc": "2026-09-27T17:00:00Z",
    }
]


def _depth(*, buf_dt: str = "2026-09-27T14:00:00Z", lac_dt: str = "2026-09-27T14:00:00Z") -> pd.DataFrame:
    return pd.DataFrame([
        {"dt": buf_dt, "team": "BUF", "player_name": "Josh Allen", "gsis_id": "00-0034857", "pos_abb": "QB", "pos_rank": 1},
        {"dt": buf_dt, "team": "BUF", "player_name": "Backup Buffalo", "gsis_id": "00-0099998", "pos_abb": "QB", "pos_rank": 2},
        {"dt": lac_dt, "team": "LAC", "player_name": "Justin Herbert", "gsis_id": "00-0036355", "pos_abb": "QB", "pos_rank": 1},
        {"dt": lac_dt, "team": "LAC", "player_name": "Backup Charger", "gsis_id": "00-0099999", "pos_abb": "QB", "pos_rank": 2},
    ])


def _qb1_snapshots(*, captured: str = "2026-09-27T14:59:00Z") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "schema_version": "adaptive-candidate4-qb1-t120-snapshot-v1",
            "candidate_id": "ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1",
            "preregistration_sha": "74ecd303545c09f57593546472d27438e3d8a204",
            "game_id": "2026_03_LAC_BUF",
            "season": 2026,
            "week": 3,
            "gameday": "2026-09-27",
            "home_team": "BUF",
            "away_team": "LAC",
            "kickoff_utc": "2026-09-27T17:00:00Z",
            "t120_target_utc": "2026-09-27T15:00:00Z",
            "captured_at_utc": captured,
            "capture_timing_error_minutes": -1.0,
            "home_t120_qb1_player_name": "Josh Allen",
            "home_t120_qb1_gsis_id": "00-0034857",
            "home_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "away_t120_qb1_player_name": "Justin Herbert",
            "away_t120_qb1_gsis_id": "00-0036355",
            "away_t120_depth_timestamp_utc": "2026-09-27T14:00:00Z",
            "qb1_snapshot_complete": True,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
            "qb1_snapshot_sha256": "c" * 64,
        }
    ])


def _write_archive(
    root: Path,
    *,
    captured: str = "2026-09-27T15:50:00Z",
    bills_entries: list[str] | None = None,
    chargers_entries: list[str] | None = None,
) -> None:
    bills_entries = bills_entries if bills_entries is not None else ["WR Example Receiver"]
    chargers_entries = chargers_entries if chargers_entries is not None else ["TE Example Tightend"]
    html = (
        "<html><body>"
        "<h3>BILLS</h3><ul>"
        + "".join(f"<li>{x}</li>" for x in bills_entries)
        + "</ul><h3>CHARGERS</h3><ul>"
        + "".join(f"<li>{x}</li>" for x in chargers_entries)
        + "</ul></body></html>"
    ).encode()
    sha = hashlib.sha256(html).hexdigest()
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(raw_dir / f"{sha}.html.gz", "wb") as handle:
        handle.write(html)
    obs = {
        "archive_id": "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1",
        "captured_at_utc": captured,
        "due_games": GAMES,
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
    (root / "observations.jsonl").write_text(json.dumps(obs) + "\n", encoding="utf-8")


def test_normalize_name_is_exact_but_suffix_and_punctuation_tolerant() -> None:
    assert normalize_name("Josh Allen Jr.") == "josh allen"
    assert normalize_name("JOSH-ALLEN, JR") == "josh allen"


def test_home_qb_inactive_creates_negative_home_direction(tmp_path) -> None:
    _write_archive(tmp_path, bills_entries=["QB Josh Allen"], chargers_entries=["TE Example Tightend"])
    out = build_qb_shock_rows(_depth(), archive_dir=tmp_path, games=GAMES)
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is True
    assert bool(row["source_qualified"]) is True
    assert row["qb_shock_direction"] == -1
    assert bool(row["home_t120_qb1_inactive"]) is True
    assert bool(row["away_t120_qb1_inactive"]) is False
    assert row["home_t120_qb1_player_name"] == "Josh Allen"
    assert row["away_t120_qb1_player_name"] == "Justin Herbert"
    assert row["completed_2026_outcomes_used"] == 0


def test_away_qb_inactive_creates_positive_home_direction(tmp_path) -> None:
    _write_archive(tmp_path, bills_entries=["WR Example Receiver"], chargers_entries=["QB Justin Herbert"])
    out = build_qb_shock_rows(_depth(), archive_dir=tmp_path, games=GAMES)
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is True
    assert row["qb_shock_direction"] == 1
    assert bool(row["away_t120_qb1_inactive"]) is True


def test_complete_article_with_neither_qb_inactive_is_zero_shock(tmp_path) -> None:
    _write_archive(tmp_path)
    out = build_qb_shock_rows(_depth(), archive_dir=tmp_path, games=GAMES)
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is True
    assert row["qb_shock_direction"] == 0
    assert row["incomplete_reasons"] == ""


def test_article_captured_after_t60_is_not_used(tmp_path) -> None:
    _write_archive(
        tmp_path,
        captured="2026-09-27T16:01:00Z",
        bills_entries=["QB Josh Allen"],
    )
    out = build_qb_shock_rows(_depth(), archive_dir=tmp_path, games=GAMES)
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is False
    assert "no_qualified_inactive_article_by_t60" in row["incomplete_reasons"]
    assert pd.isna(row["qb_shock_direction"])


def test_depth_state_after_t120_fails_closed(tmp_path) -> None:
    _write_archive(tmp_path)
    out = build_qb_shock_rows(
        _depth(buf_dt="2026-09-27T15:01:00Z"),
        archive_dir=tmp_path,
        games=GAMES,
    )
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is False
    assert "home_missing_depth_state_by_t120" in row["incomplete_reasons"]


def test_both_t120_qbs_inactive_is_ambiguous_not_zero(tmp_path) -> None:
    _write_archive(
        tmp_path,
        bills_entries=["QB Josh Allen"],
        chargers_entries=["QB Justin Herbert"],
    )
    out = build_qb_shock_rows(_depth(), archive_dir=tmp_path, games=GAMES)
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is False
    assert "both_t120_qbs_inactive_direction_ambiguous" in row["incomplete_reasons"]
    assert pd.isna(row["qb_shock_direction"])


def test_live_snapshot_path_uses_frozen_t120_identity(tmp_path) -> None:
    _write_archive(
        tmp_path,
        bills_entries=["WR Example Receiver"],
        chargers_entries=["QB Justin Herbert"],
    )
    out = build_qb_shock_rows_from_snapshots(
        _qb1_snapshots(),
        archive_dir=tmp_path,
        games=GAMES,
    )
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is True
    assert bool(row["source_qualified"]) is True
    assert row["depth_source"] == "immutable_candidate4_t120_qb1_snapshot"
    assert row["qb1_snapshot_sha256"] == "c" * 64
    assert row["qb_shock_direction"] == 1
    assert row["away_t120_qb1_player_name"] == "Justin Herbert"


def test_live_snapshot_path_fails_closed_when_snapshot_missing(tmp_path) -> None:
    _write_archive(tmp_path)
    out = build_qb_shock_rows_from_snapshots(
        pd.DataFrame(),
        archive_dir=tmp_path,
        games=GAMES,
    )
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is False
    assert "missing_t120_qb1_snapshot" in row["incomplete_reasons"]
    assert pd.isna(row["qb_shock_direction"])


def test_live_snapshot_path_rejects_post_t120_capture(tmp_path) -> None:
    _write_archive(tmp_path)
    out = build_qb_shock_rows_from_snapshots(
        _qb1_snapshots(captured="2026-09-27T15:00:01Z"),
        archive_dir=tmp_path,
        games=GAMES,
    )
    row = out.iloc[0]
    assert bool(row["qb_state_complete"]) is False
    assert "qb1_snapshot_capture_outside_t120_window" in row["incomplete_reasons"]
