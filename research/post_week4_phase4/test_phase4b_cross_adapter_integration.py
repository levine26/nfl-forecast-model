"""Cross-adapter PIT-gateway integration QA. Synthetic-only, never enrollment.

Real NFLverse payload and first-lock proof are deliberately NOT substituted
by test fixtures. These tests exercise the wiring and its fail-closed boundary,
not prospective statistical evidence or real clock/storage attestations.
"""
from __future__ import annotations

import csv
from io import StringIO
import json
from pathlib import Path

import pytest

from research.post_week4_phase4.nflverse_epa_adapter import (
    team_game_epa, build_team_states, live_source_verifier_unavailable,
)
from research.post_week4_phase4.original_lock_audit import (
    audit_first_lock, witness_contract,
)
from research.post_week4_phase4.test_nflverse_epa_adapter import fixture as pbp_fixture
from research.post_week4_phase4.test_two_stage_gateway import (
    at, data, official, first_published, source_verified, frozen_model,
)
from research.post_week4_phase4.two_stage_gateway import capture_raw, seal_against_lock


def stitched_raw():
    games, plays, counts, target = pbp_fixture()
    states = build_team_states(
        target=target, historical_games=games,
        per_team_epa=team_game_epa(plays, games, counts),
        stats_observed_utc="2026-10-11T18:49:00Z",
        capture_cutoff_utc="2026-10-11T18:50:00Z",
    )
    raw = data()
    raw["team_states"] = states
    return raw


def test_epa_to_stage_to_frozen_c_shadow_is_deterministic_synthetic(tmp_path):
    raw = stitched_raw()
    staged = capture_raw(
        raw, tmp_path, source_verifier=source_verified,
        clock=at("2026-10-11T18:50:00Z"))
    assert staged["created"] is True
    assert staged["stage"]["prospective_qualified"] is False
    assert staged["stage"]["football_input"]["team_states"]["home"]["expected_completed_current_season_games"] == 2
    sealed = seal_against_lock(
        tmp_path, raw["game_id"], official(), frozen_model(),
        lock_verifier=first_published, clock=at("2026-10-11T18:57:00Z"))
    assert sealed["record"]["candidate_id"] == frozen_model()["candidate_id"]
    assert sealed["record"]["frozen_model_sha256"] == "6af9358922321c3a03f9285df384e96cbe2d59f6d9780d2cd1ddf7d39c1ccdd5"
    assert sealed["created"] is True
    assert sealed["record"]["gateway_schema"] == "c_shadow_two_stage_gateway_v1"
    again = seal_against_lock(
        tmp_path, raw["game_id"], official(), frozen_model(),
        lock_verifier=first_published, clock=at("2026-10-11T18:58:00Z"))
    assert again["created"] is False
    assert again["prediction_sha256"] == sealed["prediction_sha256"]


def test_unqualified_real_adapter_cannot_stage_or_publish(tmp_path):
    with pytest.raises(RuntimeError, match="not configured"):
        capture_raw(stitched_raw(), tmp_path,
                    source_verifier=live_source_verifier_unavailable,
                    clock=at("2026-10-11T18:50:00Z"))
    assert not list((tmp_path / "staged").glob("*.json"))
    assert list((tmp_path / "failures").glob("*.json"))
    assert not list((tmp_path / "predictions").glob("*.json"))


def test_source_revision_after_stage_cannot_rewrite_original(tmp_path):
    raw = stitched_raw()
    staged = capture_raw(raw, tmp_path, source_verifier=source_verified,
                         clock=at("2026-10-11T18:50:00Z"))
    original_sha = staged["stage_sha256"]
    changed = stitched_raw()
    changed["team_states"]["home"]["current_season_completed"][0]["off_epa"] += 0.1
    with pytest.raises(FileExistsError, match="Conflicting"):
        capture_raw(changed, tmp_path, source_verifier=source_verified,
                    clock=at("2026-10-11T18:51:00Z"))
    assert staged["path"] and original_sha == __import__("hashlib").sha256(
        Path(staged["path"]).read_bytes()).hexdigest()


def test_git_first_occurrence_alone_cannot_seal_shadow(tmp_path):
    raw = stitched_raw()
    capture_raw(raw, tmp_path, source_verifier=source_verified,
                clock=at("2026-10-11T18:50:00Z"))
    row = {
        **{k: str(v) for k, v in official().items()},
    }
    # All necessary fields can exist in a Git blob without independently
    # establishing the first externally observed published time.
    names = list(row)
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=names, lineterminator=chr(10))
    writer.writeheader()
    writer.writerow(row)
    git = [{"commit_sha":"a"*40, "parent_sha":None,
            "history_csv":stream.getvalue(),
            "author_time":"2026-10-11T18:56:00Z",
            "committer_time":"2026-10-11T18:56:00Z"}]
    proof = audit_first_lock(raw["game_id"], versions=git)
    assert proof["first_published_utc"] is None
    assert proof["gateway_live_verifier_ready"] is False
    assert witness_contract()["gateway_eligible"] is False
    with pytest.raises(ValueError, match="Official source SHA"):
        seal_against_lock(tmp_path, raw["game_id"], official(), frozen_model(),
            lock_verifier=lambda _: proof,
            clock=at("2026-10-11T18:57:00Z"))
    assert not list((tmp_path / "predictions").glob("*.json"))
    assert list((tmp_path / "failures").glob("*.json"))


@pytest.mark.parametrize("mutation", ["late_source", "after_kickoff",
                                       "missing_prior_game", "changed_kickoff"])
def test_adapters_reject_chronology_or_incomplete_games(tmp_path, mutation):
    raw = stitched_raw()
    if mutation == "late_source":
        raw["features_observed_at_utc"] = "2026-10-11T18:51:00Z"
    elif mutation == "after_kickoff":
        raw["kickoff_utc"] = "2026-10-11T18:49:00Z"
    elif mutation == "missing_prior_game":
        raw["team_states"]["away"]["last_eight_previous_season"].pop()
    else:
        raw["kickoff_utc"] = "2026-10-11T18:53:00Z"
    with pytest.raises(ValueError):
        capture_raw(raw, tmp_path, source_verifier=source_verified,
                    clock=at("2026-10-11T18:50:00Z"))
    assert not list((tmp_path / "staged").glob("*.json"))
    assert list((tmp_path / "failures").glob("*.json"))
