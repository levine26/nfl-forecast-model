from __future__ import annotations

"""Non-production, game-scoped accepted-human editorial ledger (shadow v1).

This module never calculates, modifies, imports, or persists numerical forecasts.
A trusted caller MUST complete live source/claim checks and the existing focused
editorial validator before furnishing an acceptance receipt. This store verifies
receipt-to-payload integrity, not the external article's truth.
"""

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Callable
from urllib.parse import urlparse

import fcntl


SCHEMA_VERSION = 1
_SHA_RE = re.compile(r"^[a-f0-9]{64}$")
_GAME_ID_RE = re.compile(r"^20\d\d_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$")
_FORBIDDEN = {
    "pick", "probability", "probabilities", "final_home_prob", "pure_home_prob",
    "market_home_prob", "win_probability", "coherent_score", "fair_line",
    "score", "spread", "moneyline", "official_lock", "grading",
}


class LedgerConflict(ValueError):
    """Optimistic revision, audit-contract, or file-write conflict."""


def canonical_bytes(data: Any) -> bytes:
    return json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(data: Any) -> str:
    return sha256(canonical_bytes(data)).hexdigest()


def _time(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
    except (TypeError, AttributeError, ValueError) as exc:
        raise LedgerConflict("timestamps must be timezone-aware ISO 8601") from exc


def _payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LedgerConflict("human candidate must be an object")
    forbidden = set(payload) & _FORBIDDEN
    if forbidden:
        raise LedgerConflict(f"LLM human candidate contains protected numerical fields: {sorted(forbidden)}")
    expected = {"game_id", "provider", "headline", "paragraph1", "model_rationale", "sources", "evidence_digest"}
    if set(payload) != expected:
        raise LedgerConflict(f"unexpected/missing candidate fields: {sorted(set(payload) ^ expected)}")
    if not _GAME_ID_RE.fullmatch(str(payload["game_id"])):
        raise LedgerConflict("invalid canonical game id")
    for key in ("provider", "headline", "paragraph1", "model_rationale"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            raise LedgerConflict(f"missing {key}")
    if not _SHA_RE.fullmatch(str(payload["evidence_digest"])):
        raise LedgerConflict("missing evidence content fingerprint")
    sources = payload["sources"]
    if not isinstance(sources, list) or len(sources) < 2:
        raise LedgerConflict("two source receipts required")
    hosts: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise LedgerConflict("source receipt must be an object")
        required = {"url", "publisher", "title", "retrieved_utc", "content_sha256", "supported_claims"}
        if not required.issubset(source):
            raise LedgerConflict("source receipt missing URL, content hash, or claim support")
        url = str(source["url"])
        parts = urlparse(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            raise LedgerConflict("source receipt URL must be canonical HTTPS")
        if not str(source["publisher"]).strip() or not str(source["title"]).strip():
            raise LedgerConflict("source receipt title/publisher missing")
        _time(str(source["retrieved_utc"]))
        if not _SHA_RE.fullmatch(str(source["content_sha256"])):
            raise LedgerConflict("source receipt lacks fetched-content digest")
        if not isinstance(source["supported_claims"], list) or not source["supported_claims"]:
            raise LedgerConflict("source receipt must identify supported claims")
        # A publisher family is an independent verifier-supplied property, NOT a
        # guarantee that the underlying article has been fact-checked.
        family = str(source.get("publisher_family") or "").strip().lower()
        if not family:
            raise LedgerConflict("source receipt missing publisher-family identity")
        hosts.add(family)
    if len(hosts) < 2:
        raise LedgerConflict("source receipts must represent two publisher families")
    return deepcopy(payload)


def _blank(game_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "accepted_revision": 0,
        "revisions": [],
        "freshness": {"state": "current", "reason": ""},
    }


def verify_state(state: dict[str, Any]) -> None:
    """Reject tampered or structurally incomplete accepted revisions."""
    if not isinstance(state, dict) or state.get("schema_version") != SCHEMA_VERSION:
        raise LedgerConflict("invalid ledger schema")
    gid = str(state.get("game_id") or "")
    revisions = state.get("revisions")
    if not _GAME_ID_RE.fullmatch(gid) or not isinstance(revisions, list):
        raise LedgerConflict("invalid ledger game/revision history")
    if not isinstance(state.get("accepted_revision"), int) or state["accepted_revision"] != len(revisions):
        raise LedgerConflict("accepted revision count mismatch")
    for index, version in enumerate(revisions, 1):
        if not isinstance(version, dict) or version.get("revision") != index:
            raise LedgerConflict("nonconsecutive accepted revision history")
        data = _payload(version.get("candidate"))
        if data["game_id"] != gid or version.get("candidate_sha256") != digest(data):
            raise LedgerConflict("accepted editorial bytes fail checksum")
        receipt = version.get("validation_receipt")
        if not isinstance(receipt, dict) or receipt.get("passed") is not True or receipt.get("article_claims_verified") is not True:
            raise LedgerConflict("accepted entry lacks authoritative validation receipt")
        if receipt.get("candidate_sha256") != version["candidate_sha256"]:
            raise LedgerConflict("accepted entry validation receipt hash mismatch")
    freshness = state.get("freshness")
    if not isinstance(freshness, dict) or freshness.get("state") not in {
        "current", "review_required", "withheld_factual_contradiction"
    }:
        raise LedgerConflict("unrecognized freshness status")
    if freshness["state"] != "current" and not str(freshness.get("reason") or "").strip():
        raise LedgerConflict("freshness rejection missing reason")


def accept_candidate(
    current: dict[str, Any] | None,
    candidate: dict[str, Any],
    *,
    validation_receipt: dict[str, Any],
    expected_revision: int,
) -> dict[str, Any]:
    """Append only a separately validator-approved candidate; never mutate prior revisions.

    `validation_receipt` MUST originate from trusted validation code after actual
    article fetch/claim verification. Supplying a boolean from LLM JSON is not
    sufficient. Production caller wiring is intentionally disabled in shadow v1.
    """
    record = _payload(candidate)
    game_id = record["game_id"]
    state = deepcopy(current) if current is not None else _blank(game_id)
    verify_state(state)
    if state.get("game_id") != game_id:
        raise LedgerConflict("ledger game ownership mismatch")
    revision = state["accepted_revision"]
    fingerprint = digest(record)
    latest = state["revisions"][-1] if state["revisions"] else None
    if latest and latest.get("candidate_sha256") == fingerprint:
        return state  # identical retries never create duplicates
    if expected_revision != revision:
        raise LedgerConflict(f"stale game revision: wanted {expected_revision}, actual {revision}")

    if not isinstance(validation_receipt, dict):
        raise LedgerConflict("separate validator receipt required")
    required = {"passed", "candidate_sha256", "validator_version", "article_claims_verified", "validated_utc"}
    if not required.issubset(validation_receipt):
        raise LedgerConflict("validator receipt missing required proof")
    if validation_receipt["passed"] is not True or validation_receipt["article_claims_verified"] is not True:
        raise LedgerConflict("unverified or rejected human candidate")
    if validation_receipt["candidate_sha256"] != fingerprint:
        raise LedgerConflict("validator receipt references different candidate bytes")
    if not str(validation_receipt["validator_version"]).strip():
        raise LedgerConflict("unknown validator version")
    _time(str(validation_receipt["validated_utc"]))

    state["revisions"].append({
        "revision": revision + 1,
        "candidate_sha256": fingerprint,
        "candidate": record,
        "validation_receipt": deepcopy(validation_receipt),
    })
    state["accepted_revision"] = revision + 1
    state["freshness"] = {"state": "current", "reason": ""}
    return state


def flag_freshness(current: dict[str, Any], *, status: str, reason: str) -> dict[str, Any]:
    """Context/injury updates change freshness only, never accepted paragraph bytes."""
    if status not in {"current", "review_required", "withheld_factual_contradiction"}:
        raise LedgerConflict("invalid freshness state")
    if status != "current" and not str(reason).strip():
        raise LedgerConflict("factual invalidation/review must record reason")
    state = deepcopy(current)
    if not state.get("accepted_revision"):
        raise LedgerConflict("no accepted revision to retain")
    state["freshness"] = {"state": status, "reason": str(reason)}
    verify_state(state)
    return state


def release_index(
    ledger_states: dict[str, dict[str, Any]],
    *,
    expected_game_ids: list[str],
    canonical_forecast_sha256: str,
    slate_validation_receipt: dict[str, Any],
) -> dict[str, Any]:
    """Prepare only a shadow publication index. Never writes protected forecasts."""
    expected = list(map(str, expected_game_ids))
    if not expected or len(expected) != len(set(expected)) or set(ledger_states) != set(expected):
        raise LedgerConflict("partial or duplicate slate cannot be published")
    if not _SHA_RE.fullmatch(str(canonical_forecast_sha256)):
        raise LedgerConflict("missing canonical forecast fingerprint")
    if not isinstance(slate_validation_receipt, dict) or slate_validation_receipt.get("passed") is not True:
        raise LedgerConflict("full-slate validator has not approved publication")
    refs = {}
    for gid in sorted(expected):
        state = ledger_states[gid]
        verify_state(state)
        if state.get("game_id") != gid or not state.get("accepted_revision"):
            raise LedgerConflict(f"{gid}: missing accepted human revision")
        if state.get("freshness", {}).get("state") == "withheld_factual_contradiction":
            raise LedgerConflict(f"{gid}: unresolved factual contradiction")
        current_revision = state["revisions"][-1]
        refs[gid] = {
            "revision": state["accepted_revision"],
            "candidate_sha256": current_revision["candidate_sha256"],
            "freshness": state["freshness"]["state"],
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "editorial_shadow_release",
        "canonical_forecast_sha256": canonical_forecast_sha256,
        "games": refs,
        "slate_validation_sha256": digest(slate_validation_receipt),
    }


def modify_json_atomically(
    path: Path,
    transform: Callable[[dict[str, Any] | None], dict[str, Any]],
    *,
    expected_file_digest: str | None,
) -> dict[str, Any]:
    """Crash-safe local compare-and-swap with a per-file Linux advisory lease.

    Cross-run GitHub publication still needs remote ref CAS and a single publisher.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        raw = path.read_bytes() if path.exists() else None
        actual_digest = sha256(raw).hexdigest() if raw is not None else None
        if actual_digest != expected_file_digest:
            raise LedgerConflict("ledger file advanced after the caller's read")
        current = json.loads(raw) if raw is not None else None
        if current is not None:
            verify_state(current)
        updated = transform(deepcopy(current))
        verify_state(updated)
        if current == updated:
            return updated
        staged = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as f:
                staged = Path(f.name)
                f.write(json.dumps(updated, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(staged, path)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
        return updated
