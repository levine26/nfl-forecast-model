"""Synthetic only: two-stage research capture, independent-verifier boundary, failure ledger."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pytest

from research.post_week4_phase4.c_shadow import canonical_hash
from research.post_week4_phase4.c_shadow_eval import evaluate
from research.post_week4_phase4.test_c_shadow import example_snapshot


def frozen_model():
    return json.loads(Path('research/post_week4_phase4/artifacts/C_SHADOW_FROZEN_2026.json').read_text())
from research.post_week4_phase4.two_stage_gateway import capture_raw, seal_against_lock


def at(value):
    return lambda: datetime.fromisoformat(value.replace("Z", "+00:00"))


def source_verified(_raw):
    return {"complete_asof_capture": True, "storage_rights_verified": True,
            "verification_ref": "synthetic-independent-source-verifier-NOT-LIVE",
            "football_input_sha256": canonical_hash(_raw)}


def data():
    snapshot = example_snapshot()
    for k in ("snapshot_captured_utc", "fst_lock_timestamp_utc",
              "fst_lock_status", "fst_candidate_id", "fst_home_prob", "market_home_prob"):
        snapshot.pop(k)
    return snapshot


def official():
    s = example_snapshot()
    return {
        "game_id": s["game_id"], "season": s["season"], "week": s["week"],
        "home_team": s["home_team"], "away_team": s["away_team"],
        "kickoff_utc": s["kickoff_utc"],
        "lock_timestamp_utc": s["fst_lock_timestamp_utc"],
        "lock_status": "LOCKED",
        "fst_artifact_id": "F-ST-01-FROZEN-2026",
        "final_probability_strategy": "F-ST-01-FROZEN-2026",
        "prediction_timestamp_utc": "2026-10-11T18:54:00+00:00",
        "market_snapshot_timestamp_utc": "2026-10-11T18:53:00+00:00",
        "market_freshness_status": "refreshed_this_run",
        "final_home_prob": s["fst_home_prob"],
        "market_home_prob": s["market_home_prob"],
    }


def first_published(row):
    return {"commit_sha": "a" * 40, "row_sha256": canonical_hash(row),
            "first_published_utc": "2026-10-11T18:56:00+00:00"}


def stage(tmp_path: Path, verified=True):
    return capture_raw(data(), tmp_path,
        source_verifier=source_verified if verified else None,
        clock=at("2026-10-11T18:50:00+00:00"))


def seal(tmp_path: Path, **kw):
    return seal_against_lock(tmp_path, "2026_05_BUF_KC", official(), frozen_model(),
        lock_verifier=first_published, clock=at("2026-10-11T18:57:00+00:00"), **kw)


def test_qualified_synthetic_two_stage_and_tie_grade(tmp_path):
    a = stage(tmp_path)
    assert a["created"]
    assert a["stage"]["prospective_qualified"] is False
    b = seal(tmp_path)
    assert b["created"] and b["record"]["gateway_pit_checks_passed"] is True
    assert b["record"]["official_lock_commit_sha"] == "a" * 40
    assert b["record"]["candidate_id"] == frozen_model()["candidate_id"]
    pending = evaluate([b["record"]], [])
    assert pending["pending_games"] == 1 and pending["graded_non_tie_games"] == 0
    tie = {"game_id": b["record"]["game_id"], "season": 2026, "week": 5,
           "home_score": 21, "away_score": 21,
           "source_type": "verified_official_game_result", "source_sha256": "b" * 64,
           "result_observed_utc": "2026-10-12T01:00:00Z"}
    assert evaluate([b["record"]], [tie])["ties_excluded"] == 1
    assert len(list((tmp_path / "predictions").glob("*.json"))) == 1


def test_idempotent_stage_and_prediction_do_not_change_seal(tmp_path):
    first = stage(tmp_path)
    second = stage(tmp_path)
    assert first["stage_sha256"] == second["stage_sha256"] and not second["created"]
    a = seal(tmp_path)
    b = seal(tmp_path)
    assert not b["created"] and a["prediction_sha256"] == b["prediction_sha256"]
    altered = data()
    altered["team_states"]["home"]["current_season_completed"][0]["off_epa"] = -9.0
    with pytest.raises(FileExistsError, match="Conflicting"):
        capture_raw(altered, tmp_path, source_verifier=source_verified,
                    clock=at("2026-10-11T18:51:00Z"))
    assert len(list((tmp_path / "failures").glob("*.json"))) >= 1


@pytest.mark.parametrize("action", ["missing_stage","no_lock_verifier",
    "wrong_team","wrong_week","wrong_kickoff","wrong_model","recovered_lock",
    "no_market_age","stale_market","generated_after_lock","published_after_kickoff",
    "published_before_lock","published_in_future","lock_row_hash_changed","no_artifact",
    "after_kickoff","wrong_fst_probability"])
def test_seal_fail_closed(tmp_path, action):
    if action != "missing_stage":
        stage(tmp_path)
    o = official()
    m = frozen_model()
    verify = first_published
    now = at("2026-10-11T18:57:00+00:00")
    if action == "wrong_team":
        o["home_team"] = "DAL"
    elif action == "wrong_week":
        o["week"] = 6
    elif action == "wrong_kickoff":
        o["kickoff_utc"] = "2026-10-11T21:00:00Z"
    elif action == "wrong_model":
        o["fst_artifact_id"] = "CHALLENGER"
    elif action == "recovered_lock":
        o["lock_status"] = "RECOVERED_MISSED_LOCK"
    elif action == "no_market_age":
        o.pop("market_snapshot_timestamp_utc")
    elif action == "stale_market":
        o["market_freshness_status"] = "unknown"
    elif action == "generated_after_lock":
        o["prediction_timestamp_utc"] = "2026-10-11T18:58:00+00:00"
    elif action == "published_after_kickoff":
        verify = lambda row: dict(first_published(row), first_published_utc="2026-10-11T21:00:00Z")
    elif action == "published_before_lock":
        verify = lambda row: dict(first_published(row), first_published_utc="2026-10-11T18:52:00Z")
    elif action == "published_in_future":
        verify = lambda row: dict(first_published(row), first_published_utc="2026-10-11T19:20:00Z")
    elif action == "lock_row_hash_changed":
        verify = lambda row: dict(first_published(row), row_sha256="a" * 64)
    elif action == "no_artifact":
        m["theta"] = []
    elif action == "after_kickoff":
        now = at("2026-10-11T21:00:00Z")
    elif action == "wrong_fst_probability":
        o["final_home_prob"] = 1.0
    if action == "no_lock_verifier":
        verify = None
    with pytest.raises((ValueError, KeyError)):
        seal_against_lock(tmp_path, "2026_05_BUF_KC", o, m,
                          lock_verifier=verify, clock=now)
    assert not list((tmp_path / "predictions").glob("*.json"))
    assert list((tmp_path / "failures").glob("*.json"))


@pytest.mark.parametrize("action", ["post_kickoff","future_source","missing_coverage",
    "outcome_contamination","forecast_contamination","missing_history","changed_team",
    "stale_age","future_previous_stats","wrong_game","short_prior_history","wrong_completed_count"])
def test_stage_fail_closed_and_records_missingness(tmp_path, action):
    raw = data()
    now = at("2026-10-11T18:50:00Z")
    if action == "post_kickoff":
        now = at("2026-10-11T21:00:00Z")
    elif action == "future_source":
        raw["features_observed_at_utc"] = "2026-10-11T19:00:00Z"
    elif action == "missing_coverage":
        raw["upstream_completion_audit_passed"] = False
    elif action == "outcome_contamination":
        raw["outcome"] = "HOME"
    elif action == "forecast_contamination":
        raw["fst_home_prob"] = 0.7
    elif action == "missing_history":
        raw["team_states"]["away"]["current_season_completed"] = None
    elif action == "changed_team":
        raw["team_states"]["home"]["team"] = "BUF"
    elif action == "stale_age":
        raw["feature_source_asof_utc"] = "2026-10-11T15:00:00Z"
    elif action == "future_previous_stats":
        raw["team_states"]["home"]["current_season_completed"][0]["stats_observed_utc"] = "2026-10-12T10:00:00Z"
    elif action == "wrong_game":
        raw["game_id"] = "2026_05_BUF_BUF"
    elif action == "short_prior_history":
        raw["team_states"]["home"]["last_eight_previous_season"].pop()
    elif action == "wrong_completed_count":
        raw["team_states"]["away"]["expected_completed_current_season_games"] = 5
    with pytest.raises((ValueError, TypeError)):
        capture_raw(raw, tmp_path, source_verifier=source_verified, clock=now)
    assert not list((tmp_path / "staged").glob("*.json"))
    assert list((tmp_path / "failures").glob("*.json"))


def test_missing_independent_source_verification_prevents_raw_retention(tmp_path):
    with pytest.raises(ValueError, match="source/rights verification required"):
        stage(tmp_path, verified=False)
    assert not list((tmp_path / "staged").glob("*.json"))
    assert list((tmp_path / "failures").glob("*.json"))


def test_failed_retroactive_stage_is_never_rescued(tmp_path):
    with pytest.raises(ValueError):
        capture_raw(data(), tmp_path, source_verifier=source_verified,
                    clock=at("2026-10-12T03:00:00Z"))
    assert not list((tmp_path / "staged").glob("*.json"))
