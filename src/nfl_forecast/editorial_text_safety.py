from __future__ import annotations

"""Small publication-boundary text repairs for mechanically assembled evidence.

This module does not rewrite analysis or facts. It only repairs punctuation artifacts
that arise when a source-provided injury/body-part description is concatenated with a
standardized editorial guardrail. Source/status language itself is preserved.
"""

from copy import deepcopy
import re
from typing import Any

_INJURY_GUARDRAIL = "LevLine does not make up an injury point value for it."


def sanitize_public_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    # Example upstream assembly before this guard:
    #   "... listed Garrett Williams (CB) as Out. Achilles LevLine does not ..."
    # Keep "Achilles" exactly as sourced, but make it a complete evidence fragment.
    text = re.sub(
        rf"(?<![.!?])\s+(?={re.escape(_INJURY_GUARDRAIL)})",
        ". ",
        text,
    )
    text = re.sub(r"(?<=[.!?])\.{1,}(?=\s|$)", "", text)
    return text


def sanitize_public_evidence(evidence: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, list[dict[str, Any]]], int]:
    cleaned = deepcopy(evidence)
    changed = 0
    for items in cleaned.values():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            before = str(item.get("summary") or "")
            after = sanitize_public_text(before)
            if after != before:
                item["summary"] = after
                changed += 1
    return cleaned, changed


def sanitize_preview_text(previews: dict[str, dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    cleaned = deepcopy(previews)
    changed = 0
    for preview in cleaned.values():
        if not isinstance(preview, dict):
            continue
        paragraphs = preview.get("paragraphs")
        if isinstance(paragraphs, list):
            new_paragraphs = []
            for paragraph in paragraphs:
                before = str(paragraph or "")
                after = sanitize_public_text(before)
                changed += int(after != before)
                new_paragraphs.append(after)
            preview["paragraphs"] = new_paragraphs
        for key in ("case_for_pick", "case_for_opponent", "what_could_make_us_wrong"):
            if key in preview:
                before = str(preview.get(key) or "")
                after = sanitize_public_text(before)
                changed += int(after != before)
                preview[key] = after
        for collection in ("key_factors", "matchup_meter", "notebook"):
            rows = preview.get(collection)
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict) or "summary" not in row:
                    continue
                before = str(row.get("summary") or "")
                after = sanitize_public_text(before)
                changed += int(after != before)
                row["summary"] = after
    return cleaned, changed
