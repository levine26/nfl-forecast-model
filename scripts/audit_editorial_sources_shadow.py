from __future__ import annotations

"""All-game, read-only publisher-article capture; no semantic or release authority."""

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable

from nfl_forecast.editorial_article_capture import (
    ArticleCaptureError, capture_report, require_independent_publishers,
)

TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LA": "Los Angeles Rams",
    "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings", "NE": "New England Patriots",
    "NO": "New Orleans Saints", "NYG": "New York Giants", "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks", "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}


def audit_candidates(
    slate: list[dict[str, str]],
    fallback_dir: Path,
    *,
    fetcher: Callable[..., dict[str, Any]] = capture_report,
) -> dict[str, Any]:
    """Audit all source URLs, retaining per-game failures without publishing."""
    ids = [str(row.get("game_id") or "") for row in slate]
    if not ids or not all(ids) or len(set(ids)) != len(ids):
        raise ValueError("canonical slate missing or duplicate game IDs")
    games: dict[str, Any] = {}
    for row in slate:
        gid = row["game_id"]
        away, home = row.get("away_team"), row.get("home_team")
        if away not in TEAM_NAMES or home not in TEAM_NAMES or away == home:
            raise ValueError(f"{gid}: unrecognized canonical team identifiers")
        errors: list[str] = []
        reports: list[dict[str, Any]] = []
        sources_out: list[dict[str, Any]] = []
        try:
            data = json.loads((fallback_dir / f"{gid}.json").read_text(encoding="utf-8"))
            sources = data["games"][gid]["sources"]
            if not isinstance(sources, list) or not 2 <= len(sources) <= 4:
                raise ValueError("two to four sources required")
        except (KeyError, TypeError, ValueError, OSError) as exc:
            errors.append(f"candidate_unavailable:{type(exc).__name__}")
            sources = []
        for idx, source in enumerate(sources, 1):
            try:
                if not isinstance(source, dict) or not source.get("url") or not source.get("title"):
                    raise ValueError("source URL/title missing")
                report = fetcher(
                    source["url"], expected_title=source["title"],
                    away_name=TEAM_NAMES[away], home_name=TEAM_NAMES[home],
                )
                if report.get("article_resolution_verified") is not True:
                    raise ValueError("article resolution not verified")
                reports.append(report)
                sources_out.append({
                    "url": report["url"],
                    "publisher_family": report["publisher_family"],
                    "article_title": report["article_title"],
                    "published_or_updated_raw": report.get("published_or_updated_raw"),
                    "retrieved_utc": report["retrieved_utc"],
                    "http_content_sha256": report["content_sha256"],
                    "extracted_body_sha256": report["extracted_body_sha256"],
                    "reported_teams": report["reported_teams"],
                    "article_resolution_verified": True,
                    "semantic_claim_entailment_verified": False,
                })
            except (ArticleCaptureError, KeyError, TypeError, ValueError) as exc:
                errors.append(f"source_{idx}:{type(exc).__name__}:{str(exc)[:160]}")
        try:
            require_independent_publishers(
                reports, expected_teams=[TEAM_NAMES[away], TEAM_NAMES[home]],
            )
        except ArticleCaptureError as exc:
            errors.append(f"publisher_or_team_coverage:{exc}")
        games[gid] = {
            "sources": sources_out,
            "errors": errors,
            "status": "provenance_ready_semantics_pending" if not errors else "source_blocked",
            "semantic_claim_entailment_verified": False,
            "editorial_publication_authorized": False,
        }
    ready = sum(x["status"] == "provenance_ready_semantics_pending" for x in games.values())
    return {
        "schema_version": 1,
        "kind": "editorial_source_batch_shadow_only",
        "games_expected": len(ids),
        "games_with_verified_article_provenance": ready,
        "games_with_verified_semantic_claims": 0,
        "article_provenance_status": "complete" if ready == len(ids) else "incomplete",
        "semantic_claim_entailment_verified": False,
        "editorial_publication_authorized": False,
        "games": games,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slate", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--fallback-dir", type=Path, default=Path("inputs/chatgpt_media/fallback"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = args.slate.read_bytes()
    with args.slate.open(newline="", encoding="utf-8") as fh:
        slate = list(csv.DictReader(fh))
    result = audit_candidates(slate, args.fallback_dir)
    result["canonical_slate_sha256"] = sha256(raw).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"ARTICLE SHADOW: {result['games_with_verified_article_provenance']}/"
          f"{result['games_expected']} article-ready; zero claims verified; publication prohibited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
