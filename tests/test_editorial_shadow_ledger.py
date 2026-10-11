from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from nfl_forecast import editorial_shadow_ledger as ledger


def _entry(game_id="2026_05_BAL_ATL", *, minute=0, provider="groq"):
    p1 = (
        "Baltimore has to protect its quarterback long enough to attack the Atlanta "
        "secondary downfield, but the Falcons can force a shorter passing rhythm "
        "by moving pressure toward the interior protection. Atlanta's offense can "
        "attack the Ravens' linebackers with backfield motion and quick throws. "
        "Baltimore's defensive response is to disguise coverage while keeping "
        "second-level defenders in position against the run. Both play callers "
        "must adapt if the first approach fails."
    )
    assert 55 <= len(p1.split()) <= 100
    now = datetime.now(timezone.utc) - timedelta(hours=3) + timedelta(minutes=minute)
    return {
        "game_id": game_id,
        "forecast_path_identity": ledger.MODEL,
        "provider": provider,
        "generated_utc": now.isoformat(),
        "headline": "Baltimore protection meets Atlanta interior pressure and motion",
        "paragraph1": p1,
        "model_rationale": "Pressure and protection determine whether Baltimore can reach its receivers before Atlanta counters with coverage, and Atlanta's backs stress Baltimore's linebackers.",
        "sources": [
            {"url": "https://www.nfl.com/news/sample-one", "title": "Baltimore report",
             "publisher_family": "nfl.com", "content_sha256": "a" * 64,
             "retrieved_utc": now.isoformat(), "verified_claim_support": True},
            {"url": "https://www.espn.com/nfl/story/_/id/1111111/sample-two", "title": "Atlanta report",
             "publisher_family": "espn.com", "content_sha256": "b" * 64,
             "retrieved_utc": now.isoformat(), "verified_claim_support": True},
        ],
        "acceptance_receipt": {
            "game_id": game_id,
            "status": "accepted",
            "validator_version": "editorial-e2e-test-1",
            "article_resolution_verified": True,
            "claim_support_verified": True,
        },
    }


def test_accepted_prose_survives_refresh_and_rejected_new_content(tmp_path):
    store = ledger.EditorialShadowLedger(tmp_path / "shadow")
    first = _entry()
    revision = store.accept(first, expected_revision=None)
    assert store.read_revision(first["game_id"], revision)["paragraph1"] == first["paragraph1"]
    store.mark_freshness(first["game_id"], expected_revision=revision,
                         state="review_required", reason="new injury status")
    assert store.pointer(first["game_id"])["accepted_revision"] == revision
    assert store.pointer(first["game_id"])["freshness_reason"] == "new injury status"
    invalid = _entry(minute=10)
    invalid["acceptance_receipt"]["claim_support_verified"] = False
    with pytest.raises(ledger.EditorialLedgerError):
        store.accept(invalid, expected_revision=revision)
    assert store.read_revision(first["game_id"], revision) == first
    assert store.pointer(first["game_id"])["accepted_revision"] == revision


def test_idempotency_stale_writes_and_preserved_immutable_revision(tmp_path):
    store = ledger.EditorialShadowLedger(tmp_path)
    first = _entry()
    old = store.accept(first, expected_revision=None)
    assert store.accept(first, expected_revision="wrong") == old
    new = _entry(minute=5, provider="chatgpt")
    new["headline"] = "Falcons motion forces a Ravens second-level adjustment"
    newer = store.accept(new, expected_revision=old)
    assert newer != old
    with pytest.raises(ledger.EditorialLedgerConflict):
        store.accept(_entry(minute=10), expected_revision=old)
    with pytest.raises(ledger.EditorialLedgerConflict):
        store.accept(_entry(minute=1), expected_revision=newer)
    assert store.read_revision(first["game_id"], old)["provider"] == "groq"
    assert store.read_revision(first["game_id"], newer)["provider"] == "chatgpt"


def test_rollback_requires_live_head_and_marks_review(tmp_path):
    store = ledger.EditorialShadowLedger(tmp_path)
    old = store.accept(_entry(), expected_revision=None)
    newer = store.accept(_entry(minute=5, provider="chatgpt"), expected_revision=old)
    with pytest.raises(ledger.EditorialLedgerConflict):
        store.rollback("2026_05_BAL_ATL", expected_revision=old, target_revision=old, reason="bad")
    store.rollback("2026_05_BAL_ATL", expected_revision=newer, target_revision=old, reason="later contradiction")
    current = store.pointer("2026_05_BAL_ATL")
    assert current["accepted_revision"] == old
    assert current["freshness"] == "review_required"
    assert "later contradiction" in current["freshness_reason"]


def test_crash_after_writing_immutable_revision_preserves_previous_pointer(tmp_path, monkeypatch):
    store = ledger.EditorialShadowLedger(tmp_path)
    old = store.accept(_entry(), expected_revision=None)
    original_write = ledger._write_atomic

    def crash_on_pointer(path, raw):
        if path.name == "current.json":
            raise OSError("simulated crash before pointer swap")
        return original_write(path, raw)

    monkeypatch.setattr(ledger, "_write_atomic", crash_on_pointer)
    with pytest.raises(OSError):
        store.accept(_entry(minute=5, provider="chatgpt"), expected_revision=old)
    assert store.pointer("2026_05_BAL_ATL")["accepted_revision"] == old
    assert store.read_revision("2026_05_BAL_ATL", old)["provider"] == "groq"


def test_unverified_source_receipts_are_not_promoted(tmp_path):
    store = ledger.EditorialShadowLedger(tmp_path)
    bad = _entry()
    bad["sources"][1]["publisher_family"] = bad["sources"][0]["publisher_family"]
    with pytest.raises(ledger.EditorialLedgerError, match="not independent"):
        store.accept(bad, expected_revision=None)
    bad = _entry()
    bad["sources"][0]["content_sha256"] = ""
    with pytest.raises(ledger.EditorialLedgerError, match="content hash"):
        store.accept(bad, expected_revision=None)
    bad = _entry()
    bad["acceptance_receipt"]["status"] = "rejected"
    with pytest.raises(ledger.EditorialLedgerError, match="not independently accepted"):
        store.accept(bad, expected_revision=None)


def test_release_fails_closed_when_game_missing_or_needs_review(tmp_path):
    store = ledger.EditorialShadowLedger(tmp_path)
    a = _entry()
    rev_a = store.accept(a, expected_revision=None)
    b = _entry(game_id="2026_05_CHI_GB")
    rev_b = store.accept(b, expected_revision=None)
    games = [a["game_id"], b["game_id"]]
    snap = hashlib.sha256(b"synthetic canonical Week 5").hexdigest()
    release = store.prepare_shadow_release(games, canonical_sha256=snap)
    assert release["status"] == "shadow_only"
    assert release["game_revisions"] == {a["game_id"]: rev_a, b["game_id"]: rev_b}
    with pytest.raises(ledger.EditorialLedgerError, match="missing accepted"):
        store.prepare_shadow_release(games + ["2026_05_CIN_MIA"], canonical_sha256=snap)
    store.mark_freshness(b["game_id"], expected_revision=rev_b,
                         state="withheld", reason="credible reporting contradicts preview")
    with pytest.raises(ledger.EditorialLedgerError, match="unresolved freshness"):
        store.prepare_shadow_release(games, canonical_sha256=snap)


def test_immutable_revision_integrity_is_checked_on_read(tmp_path):
    store = ledger.EditorialShadowLedger(tmp_path)
    entry = _entry()
    rev = store.accept(entry, expected_revision=None)
    _, directory = store._paths(entry["game_id"])
    (directory / f"{rev}.json").write_text("{}\n")
    with pytest.raises(ledger.EditorialLedgerError, match="content hash mismatch"):
        store.read_revision(entry["game_id"], rev)
