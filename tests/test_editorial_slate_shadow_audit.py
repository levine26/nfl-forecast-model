from __future__ import annotations

import csv
from hashlib import sha256
import json
from pathlib import Path

from scripts.audit_editorial_slate_shadow import audit_slate


IDS = ("2026_05_TB_DAL", "2026_05_BAL_ATL")


def fixture(tmp_path):
    canonical = tmp_path / "this_week.csv"
    with canonical.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["game_id"])
        writer.writeheader()
        for gid in IDS:
            writer.writerow({"game_id": gid})
    sha = sha256(canonical.read_bytes()).hexdigest()
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"editorial_acceptance": {
        "games_expected": 2, "status": "degraded",
        "article_resolution_verified": False,
        "claim_support_verified": False,
        "issues": {gid: ["no_accepted_provider_human_read"] for gid in IDS},
    }}))
    candidates = tmp_path / "candidates"
    candidates.mkdir()
    for gid in IDS:
        (candidates / f"{gid}.json").write_text("{}")
    draft_hashes = {gid: sha256((candidates / f"{gid}.json").read_bytes()).hexdigest() for gid in IDS}
    sources = tmp_path / "sources.json"
    src = {
        "canonical_slate_sha256": sha, "games_expected": 2,
        "games": {gid: {"status": "provenance_ready_semantics_pending", "candidate_sha256": draft_hashes[gid],
                        "sources": [{"url": "https://a.example"}, {"url": "https://b.example"}]}
                  for gid in IDS},
    }
    sources.write_text(json.dumps(src))
    queue = tmp_path / "queue.json"
    queued = {
        "canonical_slate_sha256": sha, "games_expected": 2, "games_queued": 2,
        "games": {gid: {"status": "pending_independent_clause_and_claim_review", "candidate_file_sha256": draft_hashes[gid],
                        "sentences": [{"text": "This statement is not yet verified."}],
                        "issues": []} for gid in IDS}
    }
    queue.write_text(json.dumps(queued))
    return canonical, status, sources, queue, candidates


def audit(inputs):
    return audit_slate(*inputs)


def test_two_drafts_and_sources_are_unverified_not_success(tmp_path):
    v = audit(fixture(tmp_path))
    assert v["games_expected"] == v["games_audited"] == 2
    assert v["games_with_resolved_source_receipts"] == 2
    assert v["games_with_independently_verified_human_reads"] == 0
    assert v["editorial_publication_authorized"] is False
    for item in v["games"].values():
        assert item["state"] == "draft_available_but_unverified"
        assert item["accepted_human_read"] is False
        assert "independent_semantic_claim_verification_missing" in item["issues"]
        assert item["sentence_count_pending_clause_review"] == 1


def test_one_broken_source_does_not_hide_other_games(tmp_path):
    inputs = fixture(tmp_path)
    path = inputs[2]
    data = json.loads(path.read_text())
    data["games"][IDS[0]]["status"] = "source_blocked"
    data["games"][IDS[0]]["sources"] = []
    path.write_text(json.dumps(data))
    v = audit(inputs)
    assert v["games_audited"] == 2
    assert v["games_with_resolved_source_receipts"] == 1
    assert v["games"][IDS[0]]["state"] == "research_incomplete"
    assert v["games"][IDS[1]]["state"] == "draft_available_but_unverified"


def test_mixed_snapshot_never_launders_stale_articles(tmp_path):
    inputs = fixture(tmp_path)
    sources = inputs[2]
    data = json.loads(sources.read_text())
    data["canonical_slate_sha256"] = "0" * 64
    sources.write_text(json.dumps(data))
    v = audit(inputs)
    assert not v["source_snapshot_compatible"]
    assert v["games_with_resolved_source_receipts"] == 0
    assert all("source_receipt_snapshot_mismatch" in x["issues"] for x in v["games"].values())
    assert all(x["state"] == "stale_or_mismatched_snapshot" for x in v["games"].values())


def test_missing_candidate_does_not_cancel_scan(tmp_path):
    inputs = fixture(tmp_path)
    (inputs[4] / f"{IDS[0]}.json").unlink()
    v = audit(inputs)
    assert v["games_audited"] == 2
    assert v["games"][IDS[0]]["state"] == "missing_content"
    assert v["games"][IDS[1]]["state"] == "draft_available_but_unverified"


def test_one_rejected_review_queue_stays_separate(tmp_path):
    inputs = fixture(tmp_path)
    queue = inputs[3]
    data = json.loads(queue.read_text())
    data["games"][IDS[0]]["issues"] = ["missing_sentence"]
    queue.write_text(json.dumps(data))
    v = audit(inputs)
    assert v["games"][IDS[0]]["state"] == "draft_available_but_review_queue_rejected"
    assert v["games"][IDS[1]]["state"] == "draft_available_but_unverified"


def test_duplicate_canonical_game_cannot_be_audited_as_complete(tmp_path):
    inputs = fixture(tmp_path)
    canonical = inputs[0]
    content = canonical.read_text()
    canonical.write_text(content + f"{IDS[0]}\n")
    import pytest
    with pytest.raises(ValueError, match="unique"):
        audit(inputs)


def test_changed_candidate_rejects_old_source_and_claim_evidence(tmp_path):
    inputs = fixture(tmp_path)
    target = inputs[4] / f"{IDS[0]}.json"
    target.write_text('{"games": {"revised": true}}')
    v = audit(inputs)
    assert v["games"][IDS[0]]["state"] == "stale_or_mismatched_snapshot"
    assert "candidate_provenance_version_mismatch" in v["games"][IDS[0]]["issues"]
    assert v["games"][IDS[1]]["state"] == "draft_available_but_unverified"


def test_rejected_but_fetched_sources_are_not_counted_as_valid(tmp_path):
    inputs = fixture(tmp_path)
    sources = inputs[2]
    data = json.loads(sources.read_text())
    data["games"][IDS[0]]["status"] = "source_blocked"
    # A failed independence/claim-context check might still have two URLs.
    assert len(data["games"][IDS[0]]["sources"]) == 2
    sources.write_text(json.dumps(data))
    result = audit(inputs)
    assert result["games_with_resolved_source_receipts"] == 1
    assert result["games"][IDS[0]]["state"] == "research_incomplete"


def test_stale_candidate_source_fingerprint_not_counted(tmp_path):
    inputs = fixture(tmp_path)
    sources = inputs[2]
    data = json.loads(sources.read_text())
    data["games"][IDS[0]]["candidate_sha256"] = "a" * 64
    sources.write_text(json.dumps(data))
    result = audit(inputs)
    assert result["games_with_resolved_source_receipts"] == 1
    assert result["games"][IDS[0]]["state"] == "stale_or_mismatched_snapshot"
