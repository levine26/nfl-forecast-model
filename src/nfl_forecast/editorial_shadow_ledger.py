from __future__ import annotations

"""Research-only, crash-safe game-scoped editorial acceptance ledger.

NOT a production publisher, source-verification engine, or forecasting model.
Only already independently validated HUMAN records may be stored. The caller
must attach the actual validation receipt, which this ledger checks for shape
and binds to the submitted content hash. Existing production publication gates
remain authoritative until a separately approved cutover.
"""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from datetime import datetime, timezone
from urllib.parse import urlparse


GAME_ID = re.compile(r"^[0-9]{4}_[0-9]{2}_[A-Z]{2,3}_[A-Z]{2,3}$")
DIGEST = re.compile(r"^[a-f0-9]{64}$")
MODEL = "F-ST-01-FROZEN-2026"


class EditorialLedgerError(ValueError):
    pass


class EditorialLedgerConflict(EditorialLedgerError):
    pass


def _utc(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise EditorialLedgerError("timestamp must be ISO 8601 UTC-aware") from exc
    if parsed.tzinfo is None:
        raise EditorialLedgerError("timestamps must carry timezone")
    return parsed.astimezone(timezone.utc)


def _encoded(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".editorial-stage-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        fd_dir = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd_dir)
        finally:
            os.close(fd_dir)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EditorialLedgerError(f"non-object ledger artifact: {path}")
    return value


def _validate_game_id(gid: object) -> str:
    gid = str(gid)
    if not GAME_ID.fullmatch(gid):
        raise EditorialLedgerError("invalid canonical game ID")
    return gid


def _validate_record(entry: dict[str, Any]) -> None:
    gid = _validate_game_id(entry.get("game_id"))
    if entry.get("forecast_path_identity") != MODEL:
        raise EditorialLedgerError(f"{gid}: frozen forecast identity mismatch")
    if str(entry.get("provider") or "") not in {"groq", "chatgpt", "approved_fallback"}:
        raise EditorialLedgerError(f"{gid}: unsupported provider")
    for field in ("headline", "paragraph1", "model_rationale"):
        if not isinstance(entry.get(field), str) or not entry[field].strip():
            raise EditorialLedgerError(f"{gid}: missing {field}")
    count = len(re.findall(r"\b[\w’-]+\b", entry["paragraph1"]))
    if count < 55 or count > 100:
        raise EditorialLedgerError(f"{gid}: human paragraph must be 55–100 words")
    stamp = _utc(entry.get("generated_utc"))
    if stamp > datetime.now(timezone.utc).replace(microsecond=999999):
        raise EditorialLedgerError(f"{gid}: future-dated provider record")
    receipt = entry.get("acceptance_receipt")
    if not isinstance(receipt, dict):
        raise EditorialLedgerError(f"{gid}: missing independent validation receipt")
    if receipt.get("game_id") != gid or receipt.get("status") != "accepted":
        raise EditorialLedgerError(f"{gid}: not independently accepted")
    if not isinstance(receipt.get("validator_version"), str) or not receipt["validator_version"]:
        raise EditorialLedgerError(f"{gid}: missing validator version")
    if receipt.get("article_resolution_verified") is not True or receipt.get("claim_support_verified") is not True:
        raise EditorialLedgerError(f"{gid}: source/claim verification not certified")
    sources = entry.get("sources")
    if not isinstance(sources, list) or len(sources) < 2:
        raise EditorialLedgerError(f"{gid}: fewer than two sources")
    families: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise EditorialLedgerError(f"{gid}: invalid source receipt")
        url = str(source.get("url") or "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or not source.get("title"):
            raise EditorialLedgerError(f"{gid}: source needs an HTTPS article URL and title")
        family = str(source.get("publisher_family") or "").strip()
        content_sha = str(source.get("content_sha256") or "")
        if not family or not DIGEST.fullmatch(content_sha):
            raise EditorialLedgerError(f"{gid}: source missing publisher identity/content hash")
        _utc(source.get("retrieved_utc"))
        if source.get("verified_claim_support") is not True:
            raise EditorialLedgerError(f"{gid}: source claim support not verified")
        families.add(family)
    if len(families) < 2:
        raise EditorialLedgerError(f"{gid}: sources not independent")


class EditorialShadowLedger:
    """File-based immutable revisions and atomic current pointers under a shadow path."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _paths(self, gid: str) -> tuple[Path, Path]:
        _validate_game_id(gid)
        base = self.root / "games" / gid
        return base / "current.json", base / "revisions"

    def _lock(self):
        """Single-writer lock held across revision-write and pointer CAS."""
        self.root.mkdir(parents=True, exist_ok=True)
        handle = (self.root / ".writer.lock").open("a+b")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return handle

    def pointer(self, game_id: str) -> dict[str, Any] | None:
        current_path, _ = self._paths(game_id)
        return _read_json(current_path)

    def read_revision(self, game_id: str, revision: str) -> dict[str, Any]:
        _, directory = self._paths(game_id)
        if not DIGEST.fullmatch(str(revision)):
            raise EditorialLedgerError("invalid revision checksum")
        path = directory / f"{revision}.json"
        if not path.is_file():
            raise EditorialLedgerError(f"{game_id}: accepted revision not found")
        raw = path.read_bytes()
        if _sha(raw) != revision:
            raise EditorialLedgerError(f"{game_id}: immutable revision content hash mismatch")
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("game_id") != game_id:
            raise EditorialLedgerError(f"{game_id}: invalid revision identity")
        return payload

    def accept(self, entry: dict[str, Any], *, expected_revision: str | None) -> str:
        _validate_record(entry)
        gid = str(entry["game_id"])
        encoded = _encoded(entry)
        revision = _sha(encoded)
        current_path, revisions = self._paths(gid)
        with self._lock():
            current = _read_json(current_path)
            actual = current.get("accepted_revision") if current else None
            if actual == revision:
                self.read_revision(gid, revision)
                return revision  # Idempotent retry; no pointer update.
            if actual != expected_revision:
                raise EditorialLedgerConflict(f"{gid}: expected {expected_revision}, found {actual}")
            if current:
                previous = self.read_revision(gid, actual)
                if _utc(entry["generated_utc"]) <= _utc(previous["generated_utc"]):
                    raise EditorialLedgerConflict(f"{gid}: older/equal provider output cannot replace accepted prose")
            revisions.mkdir(parents=True, exist_ok=True)
            immutable_path = revisions / f"{revision}.json"
            if immutable_path.is_file():
                self.read_revision(gid, revision)
            else:
                _write_atomic(immutable_path, encoded)
            next_pointer = {
                "game_id": gid,
                "accepted_revision": revision,
                "previous_revision": actual,
                "freshness": "current",
                "freshness_reason": None,
                "forecast_path_identity": MODEL,
            }
            _write_atomic(current_path, _encoded(next_pointer))
        return revision

    def mark_freshness(self, game_id: str, *, expected_revision: str,
                       state: str, reason: str) -> None:
        if state not in {"review_required", "withheld", "current"} or not reason.strip():
            raise EditorialLedgerError("freshness transition needs state and reason")
        current_path, _ = self._paths(game_id)
        with self._lock():
            pointer = _read_json(current_path)
            if not pointer or pointer.get("accepted_revision") != expected_revision:
                raise EditorialLedgerConflict(f"{game_id}: stale freshness mutation")
            updated = dict(pointer)
            updated["freshness"] = state
            updated["freshness_reason"] = reason
            _write_atomic(current_path, _encoded(updated))
        # The accepted article revision is untouched.

    def rollback(self, game_id: str, *, expected_revision: str, target_revision: str,
                 reason: str) -> None:
        if not reason.strip() or target_revision == expected_revision:
            raise EditorialLedgerError("rollback needs a distinct validated target and reason")
        current_path, _ = self._paths(game_id)
        with self._lock():
            pointer = _read_json(current_path)
            if not pointer or pointer.get("accepted_revision") != expected_revision:
                raise EditorialLedgerConflict(f"{game_id}: current revision changed before rollback")
            self.read_revision(game_id, target_revision)
            updated = dict(pointer)
            updated.update(
                accepted_revision=target_revision,
                previous_revision=expected_revision,
                freshness="review_required",
                freshness_reason=f"rollback: {reason}",
            )
            _write_atomic(current_path, _encoded(updated))

    def prepare_shadow_release(self, game_ids: list[str], *, canonical_sha256: str,
                               allow_freshness_review: bool = False) -> dict[str, Any]:
        """Prepare only: this does not publish or change the official website."""
        if not DIGEST.fullmatch(canonical_sha256) or not game_ids or len(set(game_ids)) != len(game_ids):
            raise EditorialLedgerError("invalid canonical snapshot fingerprint or slate IDs")
        entries: dict[str, str] = {}
        for gid in game_ids:
            pointer = self.pointer(gid)
            if not pointer:
                raise EditorialLedgerError(f"{gid}: missing accepted HUMAN article")
            if not allow_freshness_review and pointer.get("freshness") != "current":
                raise EditorialLedgerError(f"{gid}: unresolved freshness review")
            revision = str(pointer["accepted_revision"])
            self.read_revision(gid, revision)
            entries[gid] = revision
        return {
            "status": "shadow_only",
            "forecast_path_identity": MODEL,
            "canonical_sha256": canonical_sha256,
            "game_revisions": entries,
        }
