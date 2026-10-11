from __future__ import annotations

from copy import deepcopy
from hashlib import sha256

import pytest

from nfl_forecast.editorial_ledger_shadow import (
    LedgerConflict,
    accept_candidate,
    digest,
    flag_freshness,
    modify_json_atomically,
    release_index,
    verify_state,
)


def candidate(gid="2026_05_BAL_ATL", *, headline="Distinct Ravens and Falcons film note"):
    return {
        "game_id": gid,
        "provider": "groq",
        "headline": headline,
        "paragraph1": (
            "Baltimore must protect the middle of its pocket because Atlanta is likely to mug the "
            "linebackers and force a hot throw. The Ravens can counter with a quick tight-end "
            "release, but the Falcons can rotate their safety down to erase that window. "
            "Atlanta also needs to manage second down so Baltimore cannot disguise coverage "
            "behind a predictable passing situation."
        ),
        "model_rationale": "Baltimore's protection versus Atlanta's interior rotation determines how efficiently the offense creates short throws.",
        "sources": [
            {
                "url": "https://example-one.com/reports/game",
                "title": "Verified direct report on Baltimore",
                "publisher": "Publisher One",
                "publisher_family": "one.com",
                "retrieved_utc": "2026-10-10T22:00:00Z",
                "content_sha256": "a" * 64,
                "supported_claims": ["C1"],
            },
            {
                "url": "https://example-two.com/reports/game",
                "title": "Verified direct report on Atlanta",
                "publisher": "Publisher Two",
                "publisher_family": "two.com",
                "retrieved_utc": "2026-10-10T22:00:00Z",
                "content_sha256": "b" * 64,
                "supported_claims": ["C2"],
            },
        ],
        "evidence_digest": "c" * 64,
    }


def receipt(payload):
    return {
        "passed": True,
        "article_claims_verified": True,
        "candidate_sha256": digest(payload),
        "validator_version": "human-read-focused-v2",
        "validated_utc": "2026-10-10T22:10:00Z",
    }


def accepted(gid="2026_05_BAL_ATL"):
    payload = candidate(gid)
    return accept_candidate(None, payload, validation_receipt=receipt(payload), expected_revision=0)


def test_acceptance_is_game_scoped_idempotent_and_revisioned():
    first = accepted()
    assert first["accepted_revision"] == 1
    replay = accept_candidate(first, candidate(), validation_receipt=receipt(candidate()), expected_revision=0)
    assert replay == first
    second = candidate(headline="New independently validated matchup title")
    next_state = accept_candidate(first, second, validation_receipt=receipt(second), expected_revision=1)
    assert next_state["accepted_revision"] == 2
    assert next_state["revisions"][0] == first["revisions"][0]
    assert next_state["revisions"][1]["candidate"]["headline"] == second["headline"]
    assert len(first["revisions"]) == 1


def test_stale_writer_cannot_replace_newer_revision():
    previous = accepted()
    newer = candidate(headline="A new accepted Ravens-Falcons title")
    with pytest.raises(LedgerConflict, match="stale game revision"):
        accept_candidate(previous, newer, validation_receipt=receipt(newer), expected_revision=0)


def test_unverified_sources_and_provider_numerical_fields_rejected():
    payload = candidate()
    payload["market_home_prob"] = 0.65
    with pytest.raises(LedgerConflict, match="protected numerical fields"):
        accept_candidate(None, payload, validation_receipt=receipt(payload), expected_revision=0)

    payload = candidate()
    payload["sources"][1]["publisher_family"] = "one.com"
    with pytest.raises(LedgerConflict, match="two publisher families"):
        accept_candidate(None, payload, validation_receipt=receipt(payload), expected_revision=0)

    payload = candidate()
    payload["sources"][0].pop("content_sha256")
    with pytest.raises(LedgerConflict, match="source receipt missing"):
        accept_candidate(None, payload, validation_receipt=receipt(payload), expected_revision=0)


def test_receipt_cannot_approve_different_or_unverified_payload():
    payload = candidate()
    invalid = receipt(payload)
    invalid["candidate_sha256"] = "f" * 64
    with pytest.raises(LedgerConflict, match="different candidate bytes"):
        accept_candidate(None, payload, validation_receipt=invalid, expected_revision=0)

    invalid = receipt(payload)
    invalid["article_claims_verified"] = False
    with pytest.raises(LedgerConflict, match="unverified or rejected"):
        accept_candidate(None, payload, validation_receipt=invalid, expected_revision=0)


def test_injury_freshness_review_preserves_accepted_prose():
    current = accepted()
    reviewed = flag_freshness(
        current, status="review_required", reason="New official injury report requires editorial recheck"
    )
    assert reviewed["revisions"] == current["revisions"]
    assert reviewed["accepted_revision"] == 1
    assert current["freshness"]["state"] == "current"
    blocked = flag_freshness(
        reviewed, status="withheld_factual_contradiction", reason="Named starter moved to inactive"
    )
    assert blocked["revisions"][0] == current["revisions"][0]
    with pytest.raises(LedgerConflict, match="factual invalidation"):
        flag_freshness(current, status="withheld_factual_contradiction", reason="")


def test_partial_slate_and_withheld_contradiction_fail_closed():
    state = accepted()
    valid = {"passed": True, "full_slate_digest": "b" * 64}
    with pytest.raises(LedgerConflict, match="partial or duplicate"):
        release_index(
            {state["game_id"]: state},
            expected_game_ids=[state["game_id"], "2026_05_BUF_LA"],
            canonical_forecast_sha256="d" * 64,
            slate_validation_receipt=valid,
        )
    blocked = flag_freshness(state, status="withheld_factual_contradiction", reason="Direct report contradiction")
    with pytest.raises(LedgerConflict, match="unresolved factual contradiction"):
        release_index(
            {blocked["game_id"]: blocked},
            expected_game_ids=[blocked["game_id"]],
            canonical_forecast_sha256="d" * 64,
            slate_validation_receipt=valid,
        )
    with pytest.raises(LedgerConflict, match="full-slate validator"):
        release_index(
            {state["game_id"]: state},
            expected_game_ids=[state["game_id"]],
            canonical_forecast_sha256="d" * 64,
            slate_validation_receipt={"passed": False},
        )


def test_release_references_only_accepted_editorial_and_forecast_fingerprint():
    left = accepted()
    right = accepted("2026_05_BUF_LA")
    obj = release_index(
        {left["game_id"]: left, right["game_id"]: right},
        expected_game_ids=[left["game_id"], right["game_id"]],
        canonical_forecast_sha256="e" * 64,
        slate_validation_receipt={"passed": True, "validator_version": "whole-slate-v2"},
    )
    assert obj["kind"] == "editorial_shadow_release"
    assert set(obj["games"]) == set([left["game_id"], right["game_id"]])
    assert not any(key in obj for key in ("pick", "probability", "scores", "moneyline"))
    assert obj["canonical_forecast_sha256"] == "e" * 64


def test_atomic_cas_prevents_stale_writes_and_survives_crash(tmp_path):
    path = tmp_path / "editorial" / "game.json"
    first = modify_json_atomically(path, lambda _: accepted(), expected_file_digest=None)
    assert first["accepted_revision"] == 1
    original_bytes = path.read_bytes()
    checksum = sha256(original_bytes).hexdigest()
    with pytest.raises(LedgerConflict, match="advanced"):
        modify_json_atomically(path, lambda _: {"destroyed": True}, expected_file_digest=None)
    assert path.read_bytes() == original_bytes

    def crash(_):
        raise RuntimeError("interrupted before atomic swap")

    with pytest.raises(RuntimeError, match="interrupted"):
        modify_json_atomically(path, crash, expected_file_digest=checksum)
    assert path.read_bytes() == original_bytes
    updated = modify_json_atomically(
        path,
        lambda current: flag_freshness(current, status="review_required", reason="New roster update"),
        expected_file_digest=checksum,
    )
    assert updated["revisions"] == first["revisions"]
    assert updated["freshness"]["state"] == "review_required"
    assert not list(path.parent.glob("*.tmp"))


def test_tampered_human_prose_or_verifier_receipt_is_rejected():
    original = accepted()
    tampered = deepcopy(original)
    tampered["revisions"][0]["candidate"]["paragraph1"] = "Unverified edited text"
    with pytest.raises(LedgerConflict, match="checksum"):
        verify_state(tampered)
    forged = deepcopy(original)
    forged["revisions"][0]["validation_receipt"]["validator_version"] = "changed-without-receipt"
    with pytest.raises(LedgerConflict, match="receipt integrity"):
        verify_state(forged)
