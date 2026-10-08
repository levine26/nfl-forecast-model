"""Synthetic Git ancestry and original-lock provenance auditor tests."""
import csv
import io
import pytest

from research.post_week4_phase4.original_lock_audit import (
    audit_first_lock, history_rows, normalize_first_lock, witness_contract,
)

FIELDS = ("game_id","season","week","away_team","home_team","kickoff_utc",
          "lock_timestamp_utc","prediction_timestamp_utc","market_home_prob",
          "final_home_prob","final_probability_strategy","fst_artifact_id",
          "lock_status","market_snapshot_timestamp_utc","market_freshness_status")


def row(status="LOCKED"):
    return {"game_id":"2026_05_BUF_KC","season":"2026","week":"5",
      "away_team":"BUF","home_team":"KC",
      "kickoff_utc":"2026-10-11T20:30:00+00:00",
      "lock_timestamp_utc":"2026-10-11T18:55:00+00:00",
      "prediction_timestamp_utc":"2026-10-11T18:54:00+00:00",
      "market_home_prob":"0.57","final_home_prob":"0.56",
      "final_probability_strategy":"F-ST-01-FROZEN-2026",
      "fst_artifact_id":"F-ST-01-FROZEN-2026",
      "lock_status":status,
      "market_snapshot_timestamp_utc":"2026-10-11T18:53:00+00:00",
      "market_freshness_status":"refreshed_this_run"}


def csv_blob(rows):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=FIELDS,lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def history(blobs):
    return [{"commit_sha":format(i+1,"040x"),
             "parent_sha":format(i,"040x") if i else None,
             "history_csv":b,"author_time":"2026-10-11T18:00:00Z",
             "committer_time":"2026-10-11T18:00:00Z"}
            for i,b in enumerate(blobs)]


def test_first_lock_is_original_even_after_graded_revisions():
    newer=row();newer["final_home_prob"]="0.89"
    result=audit_first_lock("2026_05_BUF_KC",versions=history([
         csv_blob([]),csv_blob([row()]),csv_blob([newer])]))
    assert result["commit_sha"] == format(2,"040x")
    assert result["normalized_official"]["final_home_prob"] == 0.56
    assert result["lock_data_integrity"] == "PASS_WITH_UNPROVEN_HISTORY_COMPLETENESS"
    assert result["first_publication_independently_verified"] is False
    assert result["first_published_utc"] is None
    assert result["gateway_live_verifier_ready"] is False


def test_missing_market_metadata_stays_blocked():
    r=row();r["market_snapshot_timestamp_utc"]=""
    audit=audit_first_lock("2026_05_BUF_KC",versions=history([csv_blob([r])]))
    assert audit["lock_data_integrity"] == "BLOCKED"
    assert "market" in audit["lock_data_blocker"]


@pytest.mark.parametrize("bad", ["wrong_fst","recovered","duplicate_game","gap",
                                 "after_lock_market","late_prediction","wrong_csv"])
def test_fail_closed_original_lock_audit(bad):
    r=row()
    if bad=="wrong_fst": r["fst_artifact_id"]="other"
    if bad=="recovered": r["lock_status"]="RECOVERED_MISSED_LOCK"
    if bad=="after_lock_market": r["market_snapshot_timestamp_utc"]="2026-10-11T19:00:00Z"
    if bad=="late_prediction": r["prediction_timestamp_utc"]="2026-10-11T19:00:00Z"
    if bad=="duplicate_game": v=history([csv_blob([r,r])])
    elif bad=="gap":
        v=history([csv_blob([]),csv_blob([r])])
        v[1]["parent_sha"]="f"*40
    elif bad=="wrong_csv":
        v=history(["not,a,valid,header\n"])
    else: v=history([csv_blob([r])])
    if bad in ("recovered","duplicate_game","gap","wrong_csv"):
        with pytest.raises(ValueError):
            audit_first_lock("2026_05_BUF_KC",versions=v)
    else:
        audit=audit_first_lock("2026_05_BUF_KC",versions=v)
        assert audit["lock_data_integrity"]=="BLOCKED"


def test_witness_contract_explicitly_excludes_git_clock_and_self_attestation():
    w=witness_contract()
    assert "continuous_publication_observation" in w["required"]
    assert "trusted_external_witness_identity" in w["required"]
    assert w["git_committer_time_is_publication_proof"] is False
    assert w["gateway_eligible"] is False
