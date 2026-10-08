"""Read-only Git objects prove earliest seen CSV content, never publication UTC.

Run only when full Git history is available (research Actions checkout fetch-depth:0).
"""
import subprocess
import pytest

from research.post_week4_phase4.original_lock_audit import audit_first_lock

PARENT="8f16596ce1ffdce1a2d13e4ad327380161c63061"
FIRST="fc88ef398a310b75eea2bf189ab21d2296237d4e"


def git_show(commit):
    p=subprocess.run(["git","show",f"{commit}:outputs/prediction_history.csv"],
                     stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode:
        pytest.skip("Full historic Git objects not available; research CI requires fetch-depth 0")
    return p.stdout.decode("utf-8")


def test_actual_legacy_first_lock_diff_does_not_create_publication_proof():
    original=git_show(FIRST)
    previous=git_show(PARENT)
    assert "2026_01_NE_SEA," not in previous
    assert "2026_01_NE_SEA," in original
    result=audit_first_lock("2026_01_NE_SEA",versions=[
      {"commit_sha":PARENT,"parent_sha":None,"history_csv":previous},
      {"commit_sha":FIRST,"parent_sha":PARENT,"history_csv":original}
    ])
    assert result["commit_sha"]==FIRST
    assert result["first_publication_independently_verified"] is False
    assert result["gateway_live_verifier_ready"] is False
    assert result["lock_data_integrity"]=="BLOCKED"
