"""Offline-only adversarial schedule/receipt integration tests."""
import json
import pytest

from research.post_week4_phase4.phase4b_integrity_audit import audit_local_denominator
from research.post_week4_phase4.test_two_stage_gateway import (
    stage, seal, data, at
)
from research.post_week4_phase4.two_stage_gateway import capture_raw
from research.post_week4_phase4.nflverse_epa_adapter import live_source_verifier_unavailable


def schedule():
    return [{"game_id":"2026_05_BUF_KC","season":2026,"week":5,
             "kickoff_utc":"2026-10-11T20:30:00+00:00"}]


def test_unwitnessed_source_cannot_create_stage_or_eligible_sample(tmp_path):
    with pytest.raises(RuntimeError,match="not configured"):
        capture_raw(data(),tmp_path,source_verifier=live_source_verifier_unavailable,
                    clock=at("2026-10-11T18:50:00Z"))
    a=audit_local_denominator(tmp_path,schedule())
    assert a["scheduled_games"]==1 and a["stage_count"]==0
    assert a["failure_ledger_count"]>=1
    assert a["independently_qualified_prospective_predictions"]==0


def test_two_stage_synthetic_seal_remains_unqualified(tmp_path):
    stage(tmp_path)
    seal(tmp_path)
    a=audit_local_denominator(tmp_path,schedule())
    assert a["errors"]==[] and a["stage_count"]==1 and a["sealed_count"]==1
    assert a["per_game"][0]["locally_consistent"]
    assert not a["per_game"][0]["prospective_qualified"]
    assert a["independently_qualified_non_tie_games"]==0
    assert a["live_activation_authorized"] is False


@pytest.mark.parametrize("mutation",["stage_revision","prediction_change",
              "corrupt_json","reschedule","missing_stage","outside_denominator"])
def test_detects_local_corruption_or_coverage_drift(tmp_path, mutation):
    s=stage(tmp_path)
    p=seal(tmp_path)
    sch=schedule()
    if mutation=="stage_revision":
        obj=json.loads((tmp_path/"staged"/"2026_05_BUF_KC.json").read_text())
        obj["football_input"]["team_states"]["home"]["team"]="XXX"
        (tmp_path/"staged"/"2026_05_BUF_KC.json").write_text(json.dumps(obj))
    elif mutation=="prediction_change":
        obj=json.loads((tmp_path/"predictions"/"2026_05_BUF_KC.json").read_text())
        obj["frozen_model_sha256"]="a"*64
        (tmp_path/"predictions"/"2026_05_BUF_KC.json").write_text(json.dumps(obj))
    elif mutation=="corrupt_json":
        (tmp_path/"staged"/"2026_05_BUF_KC.json").write_text("{")
    elif mutation=="reschedule":
        sch[0]["kickoff_utc"]="2026-10-12T20:30:00+00:00"
    elif mutation=="missing_stage":
        (tmp_path/"staged"/"2026_05_BUF_KC.json").unlink()
    elif mutation=="outside_denominator":
        (tmp_path/"predictions"/"2026_06_FAKE_GAME.json").write_text("{}")
    a=audit_local_denominator(tmp_path,sch)
    assert a["errors"]
    assert a["independently_qualified_non_tie_games"]==0


def test_denominator_rejects_duplicate_game_and_missing_kickoff(tmp_path):
    with pytest.raises(ValueError):
        audit_local_denominator(tmp_path,schedule()*2)
    sch=schedule()
    sch[0].pop("kickoff_utc")
    with pytest.raises(ValueError):
        audit_local_denominator(tmp_path,sch)
