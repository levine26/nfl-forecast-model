"""Read-only first-LOCKED-row Git-history audit, NOT a timestamp authority.

Git author/committer clocks, workflow starts and later API reads do not attest
that a row was publicly accessible pre-kickoff. This function never returns the
live two-stage gateway's lock_verifier proof; an independently recorded,
auditable external first-seen witness is still required.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re

from research.post_week4_phase4.c_shadow import canonical_hash, iso_utc, number

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED = ("game_id", "season", "week", "away_team", "home_team",
            "kickoff_utc", "lock_timestamp_utc", "prediction_timestamp_utc",
            "market_home_prob", "final_home_prob", "final_probability_strategy",
            "fst_artifact_id", "lock_status")


def history_rows(csv_text: str) -> list[dict]:
    if not isinstance(csv_text, str) or not csv_text:
        raise ValueError("Missing original raw history blob")
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("Missing/duplicate CSV columns")
    if any(k not in reader.fieldnames for k in REQUIRED):
        raise ValueError("Original CSV lacks minimum lock fields")
    rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("Malformed CSV row")
    ids = [row["game_id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate game IDs in original history blob")
    return rows


def normalize_first_lock(row: dict) -> dict:
    """Normalize CSV text to the gateway's original official-lock schema.

    Missing timestamp/freshness is NOT fabricated from lock_timestamp_utc.
    """
    if row["lock_status"] != "LOCKED" or row["fst_artifact_id"] != "F-ST-01-FROZEN-2026" or row["final_probability_strategy"] != "F-ST-01-FROZEN-2026":
        raise ValueError("Not genuine official frozen F-ST LOCKED row")
    for field in ("season", "week"):
        if not row[field].isdigit():
            raise ValueError("Invalid season/week")
    original = {k: row[k] for k in ("game_id", "away_team", "home_team",
                "kickoff_utc", "lock_timestamp_utc", "prediction_timestamp_utc",
                "fst_artifact_id", "final_probability_strategy", "lock_status")}
    original["season"] = int(row["season"])
    original["week"] = int(row["week"])
    original["final_home_prob"] = number(float(row["final_home_prob"]), "F-ST original", prob=True)
    original["market_home_prob"] = number(float(row["market_home_prob"]), "original market", prob=True)
    for k in ("kickoff_utc", "lock_timestamp_utc", "prediction_timestamp_utc"):
        iso_utc(original[k], k)
    if iso_utc(original["prediction_timestamp_utc"], "prediction") > iso_utc(original["lock_timestamp_utc"], "lock"):
        raise ValueError("Prediction generated after lock")
    # Existing historic rows may not have these; that is an explicit blocker.
    if not row.get("market_snapshot_timestamp_utc") or not row.get("market_freshness_status"):
        raise ValueError("Original lock lacks market snapshot time/freshness proof")
    original["market_snapshot_timestamp_utc"] = row["market_snapshot_timestamp_utc"]
    original["market_freshness_status"] = row["market_freshness_status"]
    if iso_utc(original["market_snapshot_timestamp_utc"], "market") > iso_utc(original["lock_timestamp_utc"], "lock"):
        raise ValueError("Market observed after original lock")
    if original["market_freshness_status"] not in ("fresh", "refreshed_this_run"):
        raise ValueError("Original market freshness cannot be verified")
    return original


def audit_first_lock(game_id: str, *, versions: list[dict]) -> dict:
    """Oldest-first contiguous first-parent history of full original CSV blobs.

    Every version must be independently obtained from actual Git objects.
    Completeness of version traversal and external publication are STILL
    independently unproved. No stdout/return object is a capture receipt.
    """
    if not versions or not isinstance(versions, list):
        raise ValueError("No Git history traversal supplied")
    prior = None
    first = None
    for version in versions:
        sha, parent = version.get("commit_sha"), version.get("parent_sha")
        if not isinstance(sha, str) or not _SHA40.fullmatch(sha):
            raise ValueError("Invalid commit identity")
        if prior is not None and parent != prior:
            raise ValueError("Gap or branch transition in Git history")
        prior = sha
        data = version.get("history_csv")
        if not isinstance(data, str):
            raise ValueError("No original CSV blob for commit")
        found = [r for r in history_rows(data) if r["game_id"] == game_id]
        if found and found[0]["lock_status"] == "RECOVERED_MISSED_LOCK":
            raise ValueError("Recovered lock cannot substitute for original lock")
        if found and found[0]["lock_status"] == "LOCKED" and first is None:
            first = {"commit_sha": sha, "original_raw_csv_row": found[0],
                     "history_blob_sha256": hashlib.sha256(data.encode()).hexdigest(),
                     "source_commit_author_clock": version.get("author_time"),
                     "source_commit_committer_clock": version.get("committer_time")}
        if first is not None and found and found[0]["lock_status"] != "LOCKED":
            raise ValueError("Previously locked game was silently rewritten")
    if first is None:
        raise ValueError("No original LOCKED record in supplied history")
    # CSV bytes and fields are preserved even when the gateway cannot accept
    # missing original market provenance.
    first["original_csv_fields_sha256"] = canonical_hash(first["original_raw_csv_row"])
    try:
        normalized = normalize_first_lock(first["original_raw_csv_row"])
        first["normalized_official"] = normalized
        first["normalized_row_sha256"] = canonical_hash(normalized)
        first["lock_data_integrity"] = "PASS_WITH_UNPROVEN_HISTORY_COMPLETENESS"
    except (ValueError, KeyError, TypeError, OverflowError) as exc:
        first["lock_data_integrity"] = "BLOCKED"
        first["lock_data_blocker"] = str(exc)
    first["first_publication_independently_verified"] = False
    first["first_published_utc"] = None
    first["gateway_live_verifier_ready"] = False
    return first


def witness_contract() -> dict:
    """Minimum future-facing receipt; no attestations synthesized here."""
    return {"required": [
        "trusted_external_witness_identity", "observed_server_utc",
        "observed_commit_sha", "first_lock_history_blob_sha256",
        "original_csv_row_sha256", "independent_witness_receipt_sha256",
        "first_seen_before_kickoff", "continuous_publication_observation",
        "durable_append_only_seal_ref", "auditor_verification_result"],
        "git_author_time_is_publication_proof": False,
        "git_committer_time_is_publication_proof": False,
        "workflow_runtime_is_publication_proof": False,
        "later_github_api_fetch_is_first_publication_proof": False,
        "gateway_eligible": False}
