from __future__ import annotations

"""Audit actual HUMAN-Read readiness separately from deterministic context health.

Passing source-URL shape checks is NOT evidence that an article resolves or
supports a claim. This layer is an observable, non-model acceptance prerequisite;
verified source content and roster/injury attribution require a separate receipt.
"""

from collections import Counter
import re
from urllib.parse import urlparse
from typing import Any

from nfl_forecast.context import TEAM_META
from nfl_forecast.source_policy import is_direct_media_report_url, media_domain_family

_WORD = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*")
_FALLBACK_SHAPES = (
    re.compile(r"\bcenters on\s+[A-Z]{2,4}\s*:", re.I),
    re.compile(r"\bthe official NFL injury report lists\b.*\bLevLine does not make up\b", re.I),
    re.compile(r"\b(?:coverage|pressure|history) note\s*:", re.I),
    re.compile(r"\b(?:PURE has|market gap:)\b", re.I),
)


def _words(value: object) -> list[str]:
    return _WORD.findall(str(value or ""))


def _mentions_team(value: object, code: str) -> bool:
    full = str((TEAM_META.get(code) or {}).get("name") or code)
    aliases = (code.lower(), full.lower(), full.split()[-1].lower())
    text = str(value or "").lower()
    return any(re.search(r"\b" + re.escape(alias) + r"\b", text) for alias in aliases)


def _substantive_seven_grams(value: object) -> set[str]:
    """Exclude standard practice-status vocabulary, not tactical copy."""
    words = [token.lower() for token in _words(value)]
    out = set()
    for i in range(max(0, len(words) - 6)):
        phrase = " ".join(words[i:i + 7])
        if any(status in phrase for status in (
            "did not participate in practice",
            "limited participant in practice",
            "was limited in practice",
            "placed on injured reserve",
            "listed as questionable",
        )):
            continue
        out.add(phrase)
    return out


def audit_editorial_acceptance(predictions, previews: dict[str, Any]) -> dict[str, Any]:
    """Classify each canonical game; never equate template output to HUMAN success.

    A structurally eligible Read is NOT fact-checked merely because its URLs
    look plausible. This report explicitly leaves article/claim verification open.
    """
    rows = [row for _, row in predictions.iterrows()]
    ids = [str(row.get("game_id") or "") for row in rows]
    issues: dict[str, list[str]] = {}
    human_ready = []
    seen_phrases: dict[str, str] = {}
    headlines: Counter[str] = Counter()

    for row in rows:
        gid = str(row.get("game_id") or "")
        errors = []
        preview = previews.get(gid) if isinstance(previews, dict) else None
        if not isinstance(preview, dict):
            issues[gid] = ["missing_matchup_preview"]
            continue
        headline = str(preview.get("headline") or "").strip()
        paragraphs = preview.get("paragraphs")
        if not headline:
            errors.append("missing_headline")
        if not isinstance(paragraphs, list) or len(paragraphs) != 2 or not all(
            isinstance(p, str) and p.strip() for p in paragraphs
        ):
            errors.append("invalid_two_paragraph_contract")
            first = ""
        else:
            first = paragraphs[0]
        voice = preview.get("editorial_voice") or {}
        if not bool(voice.get("copilot_researched")):
            errors.append("no_accepted_provider_human_read")
        word_count = len(_words(first))
        if not 55 <= word_count <= 100:
            errors.append("human_paragraph_outside_55_100_words")
        away, home = str(row.get("away_team") or ""), str(row.get("home_team") or "")
        if not (_mentions_team(first, away) and _mentions_team(first, home)):
            errors.append("human_paragraph_does_not_discuss_both_teams")
        if any(pattern.search(f"{headline} {first}") for pattern in _FALLBACK_SHAPES):
            errors.append("mechanical_injury_or_stock_template")
        if re.search(r"\b(?:LevLine|F-ST|PURE|market gap|moneyline|\d+(?:\.\d+)?\s*%)\b", first, re.I):
            errors.append("numerical_model_language_in_human_paragraph")

        sources = preview.get("reported_sources") or []
        family_set = set()
        direct = 0
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, dict):
                    continue
                url = str(source.get("source_url") or source.get("url") or "").strip()
                if is_direct_media_report_url(url) and urlparse(url).scheme == "https":
                    direct += 1
                    family_set.add(media_domain_family(url))
        if direct < 2 or len(family_set) < 2:
            errors.append("fewer_than_two_independent_direct_report_url_candidates")

        normalized = " ".join(_words(headline.lower()))
        if normalized:
            headlines[normalized] += 1
        for gram in _substantive_seven_grams(f"{headline} {first}"):
            if gram in seen_phrases and seen_phrases[gram] != gid:
                errors.append("repeated_substantive_seven_word_phrase")
                break
            seen_phrases[gram] = gid

        if errors:
            issues[gid] = sorted(set(errors))
        else:
            human_ready.append(gid)

    if len(ids) != len(set(ids)) or not all(ids):
        issues["__slate__"] = ["missing_or_duplicate_canonical_game_ids"]
    if not isinstance(previews, dict) or set(previews) != set(ids):
        issues.setdefault("__slate__", []).append("preview_game_ids_differ_from_canonical_slate")
    if any(count > 1 for count in headlines.values()):
        issues.setdefault("__slate__", []).append("duplicate_human_headlines")

    expected = len(ids)
    eligible = len(human_ready) if not issues else 0
    return {
        "status": "structurally_eligible" if expected and eligible == expected else "degraded",
        "games_expected": expected,
        "games_with_structurally_eligible_human_reads": len(human_ready),
        "games_rejected": sum(1 for gid in issues if gid != "__slate__"),
        "issues": issues,
        "provider_requirement": "validated game-scoped human Read, not deterministic fallback",
        "direct_source_requirement": "two independent HTTPS direct-report URL candidates per game",
        "article_resolution_verified": False,
        "claim_support_verified": False,
        "fact_check_requirement": "Direct-report URL classification alone cannot establish current article content, roster accuracy or claim support; separate source-content receipts are required before claiming full editorial acceptance.",
    }
