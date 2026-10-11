from __future__ import annotations

"""Fail-closed, independently signed HUMAN-claim publication prerequisite.

This is an *approval verifier*, NOT a fact-checker. A separately trusted human
reviewer must inspect the original captured articles and every factual clause,
then sign the complete provenance-bound dossier using a secret never given to
Groq, ChatGPT, candidate-generation jobs, or submitted candidate files.

Absent trusted review, receipts, or key -> no HUMAN publication. This module
never modifies official forecasts, historical locks, or published artifacts.
"""

import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo


class ClaimAcceptanceBlocked(ValueError):
    """A verified external claim review is missing, stale, or inconsistent."""


_SHA = re.compile(r"^[0-9a-f]{64}$")
_GAME = re.compile(r"^20\d{2}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$")


def _canonical(item: Any) -> bytes:
    return json.dumps(item, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(item: Any) -> str:
    return sha256(_canonical(item)).hexdigest()


def _date(value: Any, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise ClaimAcceptanceBlocked(f"{label}: timezone-aware timestamp required") from exc


def verify_signed_claim_receipts(
    *, forecast: Path, previews: Path, dossier: Path, review_key: str,
) -> dict[str, Any]:
    """Validate a separate trusted attestation against exact canonical bytes.

    The reviewer, not this deterministic checker, is responsible for semantic
    entailment, source authenticity, all factual-clause enumeration and article
    preservation. A valid signature authenticates that reviewer's *attestation*;
    it does not prove the underlying football facts independently.
    """
    if not isinstance(review_key, str) or len(review_key.encode("utf-8")) < 32:
        raise ClaimAcceptanceBlocked("independent review signing key unavailable or too weak")
    try:
        signed = json.loads(dossier.read_text(encoding="utf-8"))
        if not isinstance(signed, dict) or set(signed) != {"payload", "signature"}:
            raise ClaimAcceptanceBlocked("signed dossier must contain only payload/signature")
        payload, signature = signed["payload"], signed["signature"]
        if not isinstance(payload, dict) or not isinstance(signature, str) or not _SHA.fullmatch(signature):
            raise ClaimAcceptanceBlocked("invalid signed dossier structure")
        expected = hmac.new(review_key.encode("utf-8"), _canonical(payload), "sha256").hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise ClaimAcceptanceBlocked("claim dossier has no valid independent reviewer signature")
        raw_forecast = forecast.read_bytes()
        with forecast.open(encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        public_previews = json.loads(previews.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, csv.Error) as exc:
        raise ClaimAcceptanceBlocked(f"claim verification inputs missing or malformed: {type(exc).__name__}") from exc

    ids = [str(row.get("game_id") or "") for row in rows]
    if not ids or len(ids) != len(set(ids)) or any(not _GAME.fullmatch(gid) for gid in ids):
        raise ClaimAcceptanceBlocked("canonical forecast slate contains missing/duplicate game identities")
    if payload.get("schema_version") != 1 or payload.get("canonical_slate_sha256") != sha256(raw_forecast).hexdigest():
        raise ClaimAcceptanceBlocked("signed claim review does not match current canonical forecast bytes")
    attestations = payload.get("games")
    if not isinstance(attestations, dict) or set(attestations) != set(ids):
        raise ClaimAcceptanceBlocked("signed claim review missing or adding canonical games")
    if not isinstance(public_previews, dict) or set(ids) != set(public_previews):
        raise ClaimAcceptanceBlocked("published preview identities do not match the canonical slate")

    failures: dict[str, list[str]] = {}
    for row in rows:
        gid = row["game_id"]
        try:
            rec = attestations[gid]
            if not isinstance(rec, dict):
                raise ClaimAcceptanceBlocked("missing signed game record")
            if rec.get("official_forecast_sha256") != _digest(row):
                raise ClaimAcceptanceBlocked("stale official forecast snapshot")
            paragraphs = public_previews[gid]["paragraphs"]
            if not isinstance(paragraphs, list) or not paragraphs or not isinstance(paragraphs[0], str):
                raise ClaimAcceptanceBlocked("missing published HUMAN paragraph")
            human_sha = sha256(paragraphs[0].encode("utf-8")).hexdigest()
            if rec.get("human_paragraph_sha256") != human_sha:
                raise ClaimAcceptanceBlocked("stale or replaced HUMAN paragraph")
            if (rec.get("all_material_factual_clauses_reviewed") is not True
                    or rec.get("independent_semantic_review_complete") is not True
                    or rec.get("point_in_time_evidence_review_complete") is not True):
                raise ClaimAcceptanceBlocked("independent clause/semantic/time review not completed")
            reviewer = str(rec.get("reviewer_id") or "").strip()
            if not reviewer or reviewer.lower() in {"groq", "chatgpt", "provider", "llm"}:
                raise ClaimAcceptanceBlocked("independent human reviewer identity missing")
            _date(rec.get("reviewed_utc"), "reviewed_utc")
            try:
                kickoff = datetime.fromisoformat(
                    f"{row['gameday']}T{row['gametime']}"
                ).replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)
            except (ValueError, KeyError) as exc:
                raise ClaimAcceptanceBlocked("canonical kickoff unavailable") from exc

            sources = rec.get("sources")
            if not isinstance(sources, list) or len(sources) < 2:
                raise ClaimAcceptanceBlocked("two independently reviewed source receipts required")
            families: set[str] = set()
            source_hashes: set[str] = set()
            for source in sources:
                if not isinstance(source, dict):
                    raise ClaimAcceptanceBlocked("malformed signed source receipt")
                family = str(source.get("publisher_family") or "").lower().strip()
                fingerprint = str(source.get("article_content_sha256") or "")
                url = str(source.get("canonical_url") or "")
                if (not family or family in families or not _SHA.fullmatch(fingerprint)
                        or not url.startswith("https://")):
                    raise ClaimAcceptanceBlocked("source identity, fingerprint or publisher independence invalid")
                published = _date(source.get("published_utc"), "source publication")
                captured = _date(source.get("captured_utc"), "source archive capture")
                if published >= kickoff or captured >= kickoff or captured < published - timedelta(minutes=5):
                    raise ClaimAcceptanceBlocked("article not demonstrably captured before kickoff")
                if source.get("original_article_content_reviewed") is not True:
                    raise ClaimAcceptanceBlocked("source article body not independently reviewed")
                families.add(family)
                source_hashes.add(fingerprint)
            claims = rec.get("claims")
            if not isinstance(claims, list) or not claims:
                raise ClaimAcceptanceBlocked("no independently verified factual claim inventory")
            for claim in claims:
                if not isinstance(claim, dict):
                    raise ClaimAcceptanceBlocked("malformed factual claim")
                if claim.get("judgment") != "verified" or not str(claim.get("statement") or "").strip():
                    raise ClaimAcceptanceBlocked("unsupported, contradicted or unreviewed factual claim")
                excerpt = str(claim.get("exact_supporting_excerpt") or "").strip()
                if len(excerpt.split()) < 8:
                    raise ClaimAcceptanceBlocked("missing substantive exact cited excerpt")
                if claim.get("article_content_sha256") not in source_hashes:
                    raise ClaimAcceptanceBlocked("claim support is detached from archived source bytes")
                if claim.get("independently_entails_claim") is not True:
                    raise ClaimAcceptanceBlocked("reviewer did not attest semantic entailment")
        except (KeyError, TypeError, AttributeError, ClaimAcceptanceBlocked) as exc:
            failures.setdefault(gid, []).append(str(exc))
    if failures:
        raise ClaimAcceptanceBlocked("independent HUMAN claim acceptance refused: "
                                     + json.dumps(failures, sort_keys=True))
    return {"games_verified_by_signed_independent_review": len(ids),
            "canonical_slate_sha256": sha256(raw_forecast).hexdigest(),
            "review_basis": "HMAC-authenticated independent HUMAN semantic attestation"}


def require_signed_claim_receipts(
    *, forecast: Path = Path("outputs/this_week.csv"),
    previews: Path = Path("outputs/game_previews.json"),
    dossier: Path = Path("inputs/sunday_signal/independent_claim_approvals.json"),
) -> dict[str, Any]:
    """Production gate: no secret or no independent signed dossier means BLOCK."""
    return verify_signed_claim_receipts(
        forecast=forecast, previews=previews, dossier=dossier,
        review_key=os.environ.get("SUNDAY_SIGNAL_REVIEW_KEY", ""),
    )
