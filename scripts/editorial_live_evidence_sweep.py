from __future__ import annotations

"""Non-production, complete-slate ORIGINAL article provenance audit.

The existing source-verification layer checks article content, quotes and
semantic review separately. This sweep merely retrieves real publisher content
and records URL/title/coverage reliability. It never authorizes a HUMAN Read,
freezes any number, or writes an official forecast.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from nfl_forecast.context import TEAM_META
from nfl_forecast.editorial_article_capture import (
    ArticleCaptureError, capture_report, require_independent_publishers,
)


def audit_slate(
    prediction_rows: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    *,
    capture: Callable[..., dict[str, Any]] = capture_report,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Audit every game and EVERY cited report without aborting on first failure."""
    ts = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    ids = [str(row.get("game_id") or "") for row in prediction_rows]
    if not ids or len(set(ids)) != len(ids) or not all(ids):
        raise ValueError("missing/duplicate canonical game IDs")

    result: dict[str, Any] = {}
    for row in prediction_rows:
        gid = str(row["game_id"])
        away = str(row.get("away_team") or "")
        home = str(row.get("home_team") or "")
        entry = candidates.get(gid)
        details: list[dict[str, Any]] = []
        verified: list[dict[str, Any]] = []
        problems: list[str] = []

        if away not in TEAM_META or home not in TEAM_META or away == home:
            problems.append("canonical_team_identity_missing")
        elif not isinstance(entry, dict):
            problems.append("game_has_no_human_candidate")
        else:
            sources = entry.get("sources")
            if not isinstance(sources, list) or len(sources) < 2:
                problems.append("fewer_than_two_source_candidates")
                sources = sources if isinstance(sources, list) else []
            for index, source in enumerate(sources[:8]):
                item: dict[str, Any] = {"index": index, "status": "rejected"}
                if not isinstance(source, dict):
                    item["reason"] = "source_is_not_an_object"
                    details.append(item)
                    continue
                url = str(source.get("url") or "")
                title = str(source.get("title") or "")
                item.update(url=url, claimed_title=title)
                if not url or not title:
                    item["reason"] = "missing_url_or_title"
                    details.append(item)
                    continue
                try:
                    packet = capture(
                        url,
                        expected_title=title,
                        away_name=str(TEAM_META[away]["name"]),
                        home_name=str(TEAM_META[home]["name"]),
                        now=now,
                    )
                    verified.append(packet)
                    item.update({
                        "status": "article_resolved",
                        "article_title": packet["article_title"],
                        "publisher_family": packet["publisher_family"],
                        "content_sha256": packet["content_sha256"],
                        "article_text_sha256": packet["extracted_body_sha256"],
                        "retrieved_utc": packet["retrieved_utc"],
                        "reported_teams": packet.get("reported_teams") or [],
                        "quote_location_verified": False,
                        "semantic_claim_entailment_verified": False,
                    })
                except (ArticleCaptureError, KeyError, OSError, ValueError) as exc:
                    item["reason"] = str(exc)[:360]
                details.append(item)

        if len(verified) >= 2:
            try:
                require_independent_publishers(
                    verified,
                    expected_teams=[str(TEAM_META[away]["name"]), str(TEAM_META[home]["name"])],
                )
            except (ArticleCaptureError, KeyError, ValueError) as exc:
                problems.append("independence_or_combined_coverage: " + str(exc)[:280])
        else:
            problems.append("fewer_than_two_resolved_independent_sources")
        result[gid] = {
            "status": "provenance_candidates_resolved" if not problems else "provenance_incomplete",
            "errors": problems,
            "source_checks": details,
            "article_resolution_verified": not problems,
            "semantic_claim_entailment_verified": False,
            "editorial_publication_authorized": False,
        }

    if set(candidates) != set(ids):
        result["__slate__"] = {
            "missing_candidates": sorted(set(ids)-set(candidates)),
            "extra_candidates": sorted(set(candidates)-set(ids)),
        }
    resolved = sum(item["status"] == "provenance_candidates_resolved"
                   for gid, item in result.items() if gid != "__slate__")
    return {
        "schema_version": 1,
        "status": "shadow_provenance_complete" if resolved == len(ids) and "__slate__" not in result
                  else "shadow_provenance_incomplete",
        "source_type": "original_publisher_article_acquisition",
        "generated_utc": ts,
        "games_expected": len(ids),
        "games_with_two_resolved_independent_reporters": resolved,
        "games": result,
        "fact_checking_complete": False,
        "editorial_publication_authorized": False,
        "limitation": (
            "This report records original article access, title, content fingerprints, "
            "publisher independence and matchup relevance; it does NOT attest "
            "truth of generated football assertions or independently verified roster facts."
        ),
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    """Atomic report replaces only this shadow audit artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".editorial-evidence-", suffix=".tmp", delete=False) as temp:
        temporary = Path(temp.name)
        json.dump(report, temp, ensure_ascii=False, indent=2, sort_keys=True)
        temp.write("\n")
        temp.flush()
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--input-dir", type=Path, default=Path("inputs/chatgpt_media/fallback"))
    parser.add_argument("--output", type=Path, default=Path("research_outputs/editorial/article_provenance_sweep.json"))
    args = parser.parse_args()

    with args.predictions.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    candidates: dict[str, dict[str, Any]] = {}
    for row in rows:
        gid = str(row.get("game_id"))
        file = args.input_dir / f"{gid}.json"
        if file.exists():
            try:
                content = json.loads(file.read_text(encoding="utf-8"))
                candidate = (content.get("games") or {}).get(gid)
                if isinstance(candidate, dict):
                    candidates[gid] = candidate
            except (ValueError, OSError, AttributeError):
                pass
    report = audit_slate(rows, candidates)
    report["canonical_prediction_sha256"] = hashlib.sha256(args.predictions.read_bytes()).hexdigest()
    write_report(args.output, report)
    print(
        f"Shadow article provenance: {report['games_with_two_resolved_independent_reporters']}"
        f"/{report['games_expected']} resolved; complete factual verification: NO; "
        f"publication authorized: NO. Report: {args.output}"
    )


if __name__ == "__main__":
    main()
