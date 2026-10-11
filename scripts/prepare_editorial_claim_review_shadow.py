from __future__ import annotations

"""Generate a deterministic, shadow-only HUMAN sentence review queue.

This is a review *request*, not a factual verification or a complete clause
extraction. A qualified independent reviewer must enumerate every factual
assertion (including subclauses), evaluate real article text and point-in-time
eligibility, and issue a separate provenance-bound approval. Nothing here may
authorize publication or write forecasts, locks, sheets, or published Reads.
"""

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\u201c\"'])")
_GAME_ID = re.compile(r"^20\d{2}_\d{2}_[A-Z]{2,3}_[A-Z]{2,3}$")


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def review_queue(slate_file: Path, candidate_dir: Path) -> dict[str, Any]:
    """Return every game and each sentence, without inferring semantic support."""
    slate_bytes = slate_file.read_bytes()
    rows = list(csv.DictReader(slate_bytes.decode("utf-8-sig").splitlines()))
    ids = [str(row.get("game_id") or "") for row in rows]
    if not ids or len(ids) != len(set(ids)) or not all(_GAME_ID.fullmatch(g) for g in ids):
        raise ValueError("canonical slate must have unique valid game IDs")

    games: dict[str, Any] = {}
    sentences_total = 0
    for gid in ids:
        issues: list[str] = []
        reviewed: list[dict[str, Any]] = []
        source_candidates: list[dict[str, str]] = []
        candidate_sha: str | None = None
        paragraph_sha: str | None = None
        file = candidate_dir / f"{gid}.json"
        try:
            data_bytes = file.read_bytes()
            candidate_sha = _sha(data_bytes)
            data = json.loads(data_bytes)
            entry = data["games"][gid]
            if not isinstance(entry, dict):
                raise ValueError("candidate is not an object")
            paragraph = entry.get("paragraph1")
            if not isinstance(paragraph, str) or not paragraph.strip():
                raise ValueError("paragraph1 missing")
            paragraph_sha = _sha(paragraph.encode("utf-8"))
            parts = [sentence.strip() for sentence in _SENTENCE_BREAK.split(paragraph.strip())
                     if sentence.strip()]
            if not parts:
                raise ValueError("no sentences to review")
            for n, sentence in enumerate(parts, start=1):
                reviewed.append({
                    "sentence_id": f"{gid}:p1:s{n}",
                    "sentence_index": n,
                    "text": sentence,
                    "sha256": _sha(sentence.encode("utf-8")),
                    "review_state": "unreviewed",
                    "all_factual_clauses_enumerated": False,
                    "point_in_time_evidence_verified": False,
                    "semantic_claim_entailment_verified": False,
                    "supporting_article_receipts": [],
                    "independent_reviewer_attestation": None,
                })
            source_entries = entry.get("sources")
            if not isinstance(source_entries, list) or len(source_entries) < 2:
                issues.append("fewer_than_two_candidate_sources")
            else:
                for source in source_entries:
                    if not isinstance(source, dict):
                        issues.append("malformed_candidate_source")
                        continue
                    url, title = source.get("url"), source.get("title")
                    if not isinstance(url, str) or not isinstance(title, str) or not url or not title:
                        issues.append("candidate_source_missing_title_or_url")
                        continue
                    source_candidates.append({"url": url, "title": title})
        except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            issues.append(f"candidate_unavailable:{type(exc).__name__}")
        sentences_total += len(reviewed)
        games[gid] = {
            "candidate_file_sha256": candidate_sha,
            "human_paragraph_sha256": paragraph_sha,
            "candidate_sources_unverified": source_candidates,
            "sentences": reviewed,
            "issues": issues,
            "status": "pending_independent_clause_and_claim_review" if not issues else "candidate_blocked",
            "editorial_publication_authorized": False,
        }

    return {
        "schema_version": 1,
        "kind": "human_editorial_claim_review_queue_shadow",
        "canonical_slate_sha256": _sha(slate_bytes),
        "games_expected": len(ids),
        "games_queued": len(games),
        "sentences_queued": sentences_total,
        "semantic_claim_entailment_verified": False,
        "article_point_in_time_verified": False,
        "editorial_publication_authorized": False,
        "warnings": [
            "Sentence boundaries are not a complete factual-clause inventory.",
            "Listed source links are unverified candidate references, not evidence receipts.",
            "All factual subclauses must be extracted and checked by an independent approved reviewer.",
            "Only provenance-bound approvals linked to exact candidate/article hashes may ever establish acceptance.",
        ],
        "games": games,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slate", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--candidate-dir", type=Path, default=Path("inputs/chatgpt_media/fallback"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    queue = review_queue(args.slate, args.candidate_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(queue, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    blocked = sorted(gid for gid, item in queue["games"].items() if item["issues"])
    print(json.dumps({
        "games_queued": queue["games_queued"], "sentences_queued": queue["sentences_queued"],
        "candidate_blocked_games": blocked,
        "verified_claims": 0, "editorial_publication_authorized": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
