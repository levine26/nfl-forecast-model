from __future__ import annotations

"""Shadow-only, point-in-time, direct-article evidence receipts.

The trusted acquisition worker supplies actual resolved HTTP metadata and
extracted article body. This verifier checks URL/title identity, direct-report
policy, real content fingerprints, team relevance and verbatim supporting
excerpts. Quote presence is NOT semantic entailment: do not use these receipts
as article_claims_verified=True without a separate trusted factual reviewer.
No production writer imports this module.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import html
import json
import re
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

from nfl_forecast.source_policy import is_direct_media_report_url, media_domain_family


class EvidenceInsufficient(ValueError):
    pass


WORD = re.compile(r"[a-z0-9]+")
GAME_ID = re.compile(r"^20\d{2}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$")
GENERIC = re.compile(
    r"\b(?:how to watch|listen and follow|live stream|odds and picks|betting picks|"
    r"dfs plays|fantasy rankings|power rankings|nfl schedule|week \d+ roundup|"
    r"where to watch|tv schedule)\b", re.IGNORECASE,
)


def _normalized(value: object) -> str:
    return " ".join(WORD.findall(html.unescape(str(value or "")).lower()))


def _date(value: object, *, allow_missing: bool = False) -> datetime | None:
    if value in (None, "") and allow_missing:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise EvidenceInsufficient("article timestamps need ISO-8601 timezone") from exc
    if stamp.tzinfo is None:
        raise EvidenceInsufficient("article timestamp must be timezone-aware")
    return stamp.astimezone(timezone.utc)


def _canonical(url: str) -> str:
    try:
        p = urlparse(str(url).strip())
    except (TypeError, ValueError) as exc:
        raise EvidenceInsufficient("invalid article URL") from exc
    if p.scheme != "https" or not p.hostname or p.username or p.password:
        raise EvidenceInsufficient("article must use HTTPS without embedded credentials")
    try:
        if p.port not in (None, 443):
            raise EvidenceInsufficient("unexpected article port")
    except ValueError as exc:
        raise EvidenceInsufficient("invalid article port") from exc
    params = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
              if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    host = p.hostname.lower().rstrip(".")
    if not host:
        raise EvidenceInsufficient("missing verified host")
    path = p.path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", urlencode(params), ""))


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_retrieved_article(
    *,
    game_id: str,
    candidate_url: str,
    candidate_title: str,
    fetched: dict[str, Any],
    claims: list[dict[str, str]],
    team_aliases: dict[str, list[str]],
) -> dict[str, Any]:
    """Verify a trusted HTTP acquisition result, never an LLM-supplied fetch claim.

    Trusted caller guarantees fetched.status_code, fetched.final_url,
    fetched.title and fetched.article_text originated from an actual network
    retrieval, not the generative model. No network calls happen here.
    """
    if not GAME_ID.fullmatch(game_id) or len(team_aliases) != 2:
        raise EvidenceInsufficient("canonical game and two opponent identities are mandatory")
    canonical = _canonical(candidate_url)
    final = _canonical(str(fetched.get("final_url") or ""))
    if canonical != final or not is_direct_media_report_url(canonical):
        raise EvidenceInsufficient("fabricated, redirected, or non-report article URL")
    if fetched.get("status_code") != 200:
        raise EvidenceInsufficient("article did not resolve successfully")
    article_title = str(fetched.get("title") or "").strip()
    if not article_title or _normalized(article_title) != _normalized(candidate_title):
        raise EvidenceInsufficient("displayed article title does not match retrieved title")
    if GENERIC.search(article_title) or GENERIC.search(urlparse(canonical).path.replace("-", " ")):
        raise EvidenceInsufficient("generic viewing/betting/schedule content is not direct reporting")

    body = str(fetched.get("article_text") or "").strip()
    norm_body = _normalized(body)
    if len(norm_body.split()) < 100:
        raise EvidenceInsufficient("retrieved article body too short for source verification")
    retrieved = _date(fetched.get("retrieved_utc"))
    published = _date(fetched.get("published_utc"), allow_missing=True)
    assert retrieved is not None
    if retrieved > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise EvidenceInsufficient("article retrieval timestamp lies in the future")
    if published and published > retrieved + timedelta(minutes=5):
        raise EvidenceInsufficient("publication timestamp postdates retrieval")

    # Headlines alone cannot establish matchup relevance; require team identity in reported body.
    joined = " " + _normalized(body) + " "
    relevant: list[str] = []
    for team, aliases in team_aliases.items():
        if not re.fullmatch(r"[A-Z]{2,3}", team) or not isinstance(aliases, list):
            raise EvidenceInsufficient("team aliases must originate from canonical roster")
        if any(len(_normalized(alias).split()) and
               " " + _normalized(alias) + " " in joined
               for alias in aliases):
            relevant.append(team)
    if not relevant:
        raise EvidenceInsufficient("wrong-team or unrelated article")
    if not isinstance(claims, list) or not claims:
        raise EvidenceInsufficient("article has no claimed evidence linkage")

    proofs: list[dict[str, str]] = []
    padded_body = " " + norm_body + " "
    for claim in claims:
        if not isinstance(claim, dict):
            raise EvidenceInsufficient("claim evidence must be an object")
        statement = str(claim.get("statement") or "").strip()
        excerpt = str(claim.get("supporting_excerpt") or "").strip()
        normalized = _normalized(excerpt)
        if not statement or len(normalized.split()) < 8:
            raise EvidenceInsufficient("claim needs a substantive quoted supporting passage")
        if " " + normalized + " " not in padded_body:
            raise EvidenceInsufficient("claimed supporting excerpt does not appear in article body")
        proofs.append({
            "statement": statement,
            "supporting_excerpt": excerpt,
            "excerpt_sha256": _sha_text(normalized),
        })

    return {
        "game_id": game_id,
        "canonical_url": canonical,
        "publisher_family": media_domain_family(canonical),
        "article_title": article_title,
        "published_utc": published.isoformat() if published else None,
        "retrieved_utc": retrieved.isoformat(),
        "article_content_sha256": _sha_text(body),
        "relevant_teams": sorted(relevant),
        "claim_evidence": proofs,
        "url_title_and_quote_presence_verified": True,
        "semantic_claim_entailment_verified": False,
        "verification_status": "quote_present_semantic_review_required",
    }


def audit_matchup_receipts(
    receipts: list[dict[str, Any]], *, game_id: str, teams: list[str],
) -> dict[str, Any]:
    """Require independent sourced coverage of BOTH opponents, without promoting truth."""
    if len(teams) != 2 or teams[0] == teams[1]:
        raise EvidenceInsufficient("invalid opposing teams")
    if len(receipts) < 2:
        raise EvidenceInsufficient("two independent direct-report sources required")
    families: set[str] = set()
    coverage: set[str] = set()
    for r in receipts:
        if r.get("game_id") != game_id or r.get("verification_status") != "quote_present_semantic_review_required":
            raise EvidenceInsufficient("mismatched game or unverified source packet")
        family = str(r.get("publisher_family") or "").strip()
        if not family or family in families:
            raise EvidenceInsufficient("sources must use independent publisher families")
        families.add(family)
        coverage.update(r.get("relevant_teams") or [])
    if not set(teams).issubset(coverage):
        raise EvidenceInsufficient("direct reporting does not cover both matchup teams")
    return {
        "game_id": game_id,
        "independent_source_count": len(families),
        "teams_covered": sorted(coverage & set(teams)),
        "status": "quote_verified_semantics_pending",
        "editorial_publication_authorized": False,
    }
