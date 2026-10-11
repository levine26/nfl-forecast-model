from __future__ import annotations

"""Read-only, exact-snapshot diagnostic for each canonical Sunday Signal game.

A successfully fetched source is NOT semantic support. A draft, published
preview, reviewer queue or provider-success state is NEVER an accepted HUMAN
Read without a separate independently verified production acceptance record.
This tool never publishes or edits official forecast/lock/history data.
"""

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.name}: unreadable JSON: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: expected a JSON object")
    return data


def audit_slate(
    canonical: Path,
    acceptance_status: Path,
    source_receipts: Path,
    review_queue: Path,
    candidate_dir: Path,
) -> dict[str, Any]:
    raw = canonical.read_bytes()
    with canonical.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    ids = [str(x.get("game_id") or "") for x in rows]
    if not ids or len(ids) != len(set(ids)) or any(not x for x in ids):
        raise ValueError("nonempty unique canonical game identifiers required")
    fingerprint = sha256(raw).hexdigest()
    status = _load(acceptance_status)
    receipt = _load(source_receipts)
    queue = _load(review_queue)
    accepted = status.get("editorial_acceptance") or {}
    if not isinstance(accepted, dict):
        accepted = {}
    accepted_issues = accepted.get("issues") or {}
    if not isinstance(accepted_issues, dict):
        accepted_issues = {}
    source_games = receipt.get("games") or {}
    if not isinstance(source_games, dict):
        source_games = {}
    queue_games = queue.get("games") or {}
    if not isinstance(queue_games, dict):
        queue_games = {}

    source_snapshot_ok = (
        receipt.get("canonical_slate_sha256") == fingerprint
        and receipt.get("games_expected") == len(ids)
        and set(source_games) == set(ids)
    )
    queue_snapshot_ok = (
        queue.get("canonical_slate_sha256") == fingerprint
        and queue.get("games_expected") == len(ids)
        and queue.get("games_queued") == len(ids)
        and set(queue_games) == set(ids)
    )
    # These are *shadow* proof stages; never infer accepted claim verification.
    # A later trusted ledger-specific production audit must independently
    # validate signed claim receipts against exact published bytes.
    games: dict[str, Any] = {}
    for gid in ids:
        faults: list[str] = []
        draft_file = candidate_dir / f"{gid}.json"
        draft_exists = draft_file.is_file()
        draft_sha = sha256(draft_file.read_bytes()).hexdigest() if draft_exists else None
        if not draft_exists:
            faults.append("missing_candidate_draft")
        if not source_snapshot_ok:
            faults.append("source_receipt_snapshot_mismatch")
        if not queue_snapshot_ok:
            faults.append("claim_queue_snapshot_mismatch")
        sg = source_games.get(gid)
        qg = queue_games.get(gid)
        if draft_exists and isinstance(sg, dict) and isinstance(qg, dict):
            if (sg.get("candidate_sha256") != draft_sha
                    or qg.get("candidate_file_sha256") != draft_sha):
                faults.append("candidate_provenance_version_mismatch")
        if source_snapshot_ok:
            if not isinstance(sg, dict) or sg.get("status") != "provenance_ready_semantics_pending":
                faults.append("source_retrieval_or_independence_incomplete")
            elif not isinstance(sg.get("sources"), list) or len(sg["sources"]) < 2:
                faults.append("fewer_than_two_resolved_articles")
        if queue_snapshot_ok:
            if not isinstance(qg, dict) or qg.get("issues"):
                faults.append("claim_review_queue_incomplete")
            elif not isinstance(qg.get("sentences"), list) or not qg["sentences"]:
                faults.append("no_factual_sentences_queued")
        for issue in accepted_issues.get(gid) or []:
            if isinstance(issue, str) and issue:
                faults.append(f"published_acceptance:{issue}")
        if accepted.get("article_resolution_verified") is not True:
            faults.append("published_article_verification_missing")
        if accepted.get("claim_support_verified") is not True:
            faults.append("independent_semantic_claim_verification_missing")
        if not draft_exists:
            state = "missing_content"
        elif not (source_snapshot_ok and queue_snapshot_ok) or "candidate_provenance_version_mismatch" in faults:
            state = "stale_or_mismatched_snapshot"
        elif not isinstance(sg, dict) or sg.get("status") != "provenance_ready_semantics_pending":
            state = "research_incomplete"
        elif not isinstance(qg, dict) or qg.get("issues"):
            state = "draft_available_but_review_queue_rejected"
        else:
            state = "draft_available_but_unverified"
        games[gid] = {
            "state": state,
            "draft_present": draft_exists,
            "resolved_source_receipts": len(sg.get("sources") or []) if isinstance(sg, dict) else 0,
            "sentence_count_pending_clause_review": len(qg.get("sentences") or []) if isinstance(qg, dict) else 0,
            "independently_verified_material_claims": 0,
            "accepted_human_read": False,
            "editorial_publication_authorized": False,
            "issues": sorted(set(faults)),
        }
    return {
        "schema_version": 1,
        "kind": "sunday_signal_full_slate_diagnostic_no_release_authority",
        "canonical_slate_sha256": fingerprint,
        "games_expected": len(ids),
        "games_audited": len(games),
        "games_with_resolved_source_receipts": sum(
            source_snapshot_ok and g["resolved_source_receipts"] >= 2 for g in games.values()
        ),
        "games_with_independently_verified_human_reads": 0,
        "source_snapshot_compatible": source_snapshot_ok,
        "claim_queue_snapshot_compatible": queue_snapshot_ok,
        "editorial_launch_status": "blocked",
        "editorial_publication_authorized": False,
        "warning": "This shadow diagnostic cannot certify independent semantic support, acceptance or publication; zero approvals is an intentionally conservative status.",
        "games": games,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--canonical", type=Path, default=Path("outputs/this_week.csv"))
    p.add_argument("--status", type=Path, default=Path("outputs/context_source_status.json"))
    p.add_argument("--source-receipts", type=Path, required=True)
    p.add_argument("--claim-queue", type=Path, required=True)
    p.add_argument("--candidate-dir", type=Path, default=Path("inputs/chatgpt_media/fallback"))
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = audit_slate(args.canonical, args.status, args.source_receipts, args.claim_queue, args.candidate_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    for gid, game in sorted(report["games"].items()):
        print(json.dumps({"game_id": gid, "state": game["state"], "issues": game["issues"]}, sort_keys=True))
    print(f"Full-slate diagnostic: {report['games_audited']}/{report['games_expected']} games checked, "
          "zero independent HUMAN approvals, publication prohibited.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
