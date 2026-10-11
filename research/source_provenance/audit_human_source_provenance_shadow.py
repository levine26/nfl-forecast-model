from __future__ import annotations

"""Shadow-only live article audit for one complete editorial candidate slate.

This tool diagnoses source availability and provenance; it is NEVER an
editorial publication writer or a semantic factual-claim verifier. It does
not modify forecasts, editorial drafts, accepted ledger entries or output
release artifacts, and it does not store copyrighted article bodies.
"""

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable

from nfl_forecast.editorial_article_capture import (
    capture_report,
    require_independent_publishers,
)

NICKNAMES = {
    "ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens",
    "BUF": "Bills", "CAR": "Panthers", "CHI": "Bears",
    "CIN": "Bengals", "CLE": "Browns", "DAL": "Cowboys",
    "DEN": "Broncos", "DET": "Lions", "GB": "Packers",
    "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars",
    "KC": "Chiefs", "LA": "Rams", "LAC": "Chargers",
    "LV": "Raiders", "MIA": "Dolphins", "MIN": "Vikings",
    "NE": "Patriots", "NO": "Saints", "NYG": "Giants",
    "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers",
    "SEA": "Seahawks", "SF": "49ers", "TB": "Buccaneers",
    "TEN": "Titans", "WAS": "Commanders",
}


class SlateProvenanceError(ValueError):
    pass


def validate_active_slate(
    manifest: dict[str, Any], *,
    current_csv: Path,
    historical_roster: Path,
    allow_partial: bool = False,
) -> dict[str, Any]:
    """Check a candidate against current canonical forecasts, not an older freeze.

    The frozen editorial roster is only authoritative when its season/week
    matches the active forecasts. Never rewrite or thaw an earlier week's
    immutable roster to make a research audit pass.
    """
    ids = manifest.get("game_ids")
    if (not isinstance(ids, list) or not ids
            or not all(isinstance(g, str) and g for g in ids)
            or len(ids) != len(set(ids))):
        raise SlateProvenanceError("manifest needs unique canonical game IDs")
    try:
        with current_csv.open("r", newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
    except OSError as exc:
        raise SlateProvenanceError("active canonical forecast CSV unavailable") from exc
    if not rows:
        raise SlateProvenanceError("active canonical forecast CSV is empty")
    try:
        seasons_weeks = {(int(r["season"]), int(r["week"])) for r in rows}
        if len(seasons_weeks) != 1:
            raise SlateProvenanceError("active forecast CSV mixes seasons or weeks")
        season, week = next(iter(seasons_weeks))
        current_ids = [str(r["game_id"]) for r in rows]
        for row in rows:
            expected = f"{season}_{week:02d}_{row['away_team']}_{row['home_team']}"
            if row["game_id"] != expected:
                raise SlateProvenanceError("active forecast CSV game identity mismatch")
    except (KeyError, ValueError, TypeError) as exc:
        raise SlateProvenanceError("active forecast CSV lacks valid game identity") from exc
    if len(current_ids) != len(set(current_ids)):
        raise SlateProvenanceError("duplicate games in active canonical forecast")
    if (not set(ids).issubset(set(current_ids))
            or (not allow_partial and (set(ids) != set(current_ids) or len(ids) != len(current_ids)))):
        missing = sorted(set(current_ids) - set(ids))
        extra = sorted(set(ids) - set(current_ids))
        raise SlateProvenanceError(
            f"candidate manifest differs from ACTIVE canonical forecast: "
            f"missing={missing}; extra={extra}"
        )
    roster_status = "absent"
    if historical_roster.is_file():
        try:
            historic = json.loads(historical_roster.read_text(encoding="utf-8"))
            roster_season, roster_week = int(historic["season"]), int(historic["week"])
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise SlateProvenanceError("historical editorial roster has invalid identity") from exc
        if (roster_season, roster_week) == (season, week):
            frozen_ids = historic.get("game_ids")
            if (not isinstance(frozen_ids, list)
                    or len(frozen_ids) != len(set(frozen_ids))
                    or set(frozen_ids) != set(current_ids)):
                raise SlateProvenanceError("same-week frozen roster differs from active slate")
            roster_status = "same_week_validated"
        else:
            roster_status = "different_week_historical_not_authoritative"
    return {
        "season": season, "week": week, "games_expected": len(current_ids),
        "canonical_game_ids": sorted(current_ids),
        "candidate_games_audited": len(ids),
        "candidate_is_partial": len(ids) != len(current_ids),
        "unaudited_canonical_game_ids": sorted(set(current_ids) - set(ids)),
        "historical_roster_status": roster_status,
        "publication_authorized": False,
    }



def audit_game(
    game_id: str,
    *,
    input_dir: Path,
    fetch: Callable[..., dict[str, Any]] = capture_report,
) -> dict[str, Any]:
    """One isolated case. Return all source errors instead of aborting slate."""
    codes = game_id.split("_")
    result: dict[str, Any] = {
        "game_id": game_id, "article_resolution_verified": False,
        "claim_support_verified": False, "publication_authorized": False,
        "sources": [], "issues": [],
    }
    if len(codes) != 4 or codes[2] not in NICKNAMES or codes[3] not in NICKNAMES:
        result["issues"].append("invalid_canonical_game_identity")
        return result
    path = input_dir / f"{game_id}.json"
    try:
        raw = path.read_bytes()
        packet = json.loads(raw)
        if not isinstance(packet, dict) or set(packet.get("games", {})) != {game_id}:
            raise SlateProvenanceError("source packet must contain exactly the canonical game")
        data = packet["games"][game_id]
        sources = data.get("sources")
        if not isinstance(sources, list) or len(sources) < 2:
            raise SlateProvenanceError("candidate needs two independently retrieved sources")
        result["candidate_sha256"] = sha256(raw).hexdigest()
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result["issues"].append(f"missing_or_invalid_candidate: {type(exc).__name__}: {exc}")
        return result

    verified = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            result["issues"].append(f"source_{index + 1}: invalid source object")
            continue
        url = str(source.get("url") or "")
        title = str(source.get("title") or "")
        try:
            report = fetch(
                url, expected_title=title,
                away_name=NICKNAMES[codes[2]],
                home_name=NICKNAMES[codes[3]],
            )
            verified.append(report)
            result["sources"].append({
                "candidate_url": url,
                "publisher_family": report["publisher_family"],
                "resolved_title": report["article_title"],
                "retrieved_utc": report["retrieved_utc"],
                "published_or_updated_raw": report.get("published_or_updated_raw"),
                "content_sha256": report["content_sha256"],
                "extracted_body_sha256": report["extracted_body_sha256"],
                "reported_teams": report["reported_teams"],
                "article_resolution_verified": True,
                "quote_location_verified": False,
                "claim_entailment_verified": False,
            })
        except Exception as exc:
            # Diagnostic-only: never let one missing article conceal other
            # sources, and never publish on the basis of partial retrieval.
            result["issues"].append(f"source_{index + 1}: {type(exc).__name__}: {exc}")
            result["sources"].append({
                "candidate_url": url,
                "article_resolution_verified": False,
            })
    try:
        require_independent_publishers(
            verified, expected_teams=[NICKNAMES[codes[2]], NICKNAMES[codes[3]]],
        )
        result["article_resolution_verified"] = len(verified) == len(sources)
    except Exception as exc:
        result["issues"].append(f"independent_two_team_coverage: {type(exc).__name__}: {exc}")
    # Citation resolution, quoted-text presence, and claim entailment are
    # independent stages. The candidate has no verified per-claim excerpts;
    # this collector MUST NEVER certify factual support or authorize a Read.
    result["issues"].append("semantic_claim_support_not_verified")
    return result


def audit_slate(
    manifest: dict[str, Any],
    *,
    input_dir: Path,
    fetch: Callable[..., dict[str, Any]] = capture_report,
    max_workers: int = 4,
) -> dict[str, Any]:
    ids = manifest.get("game_ids")
    if (not isinstance(ids, list) or not ids
            or not all(isinstance(g, str) for g in ids) or len(set(ids)) != len(ids)):
        raise SlateProvenanceError("manifest must contain distinct canonical game IDs")
    games: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, 6))) as executor:
        futures = {executor.submit(audit_game, game_id, input_dir=input_dir, fetch=fetch): game_id
                   for game_id in ids}
        for future in as_completed(futures):
            gid = futures[future]
            try:
                games[gid] = future.result()
            except Exception as exc:
                games[gid] = {
                    "game_id": gid, "article_resolution_verified": False,
                    "claim_support_verified": False,
                    "publication_authorized": False,
                    "sources": [],
                    "issues": [f"unexpected_audit_error: {type(exc).__name__}: {exc}"],
                }
    verified = sum(v["article_resolution_verified"] is True for v in games.values())
    return {
        "schema_version": 1,
        "mode": "shadow_only_not_a_publication_authority",
        "audited_utc": datetime.now(timezone.utc).isoformat(),
        "games_expected": len(ids),
        "games_with_verified_article_resolutions": verified,
        "games_with_verified_claim_support": 0,
        "full_slate_article_resolution_verified": verified == len(ids),
        "full_slate_claim_support_verified": False,
        "publication_authorized": False,
        "games": {gid: games[gid] for gid in ids},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("inputs/chatgpt_media/fallback/manifest.json"))
    parser.add_argument("--input-dir", type=Path, default=Path("inputs/chatgpt_media/fallback"))
    parser.add_argument("--current", type=Path, default=Path("outputs/this_week.csv"))
    parser.add_argument("--output", type=Path, default=Path("/tmp/sunday_signal_article_provenance_shadow.json"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--allow-partial", action="store_true",
                        help="Audit an exact authorized recovery subset without claiming whole-slate coverage")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    canonical = validate_active_slate(
        manifest, current_csv=args.current,
        historical_roster=Path("inputs/sunday_signal/editorial_slate_roster.json"),
        allow_partial=args.allow_partial,
    )
    result = audit_slate(manifest, input_dir=args.input_dir, max_workers=args.workers)
    result["canonical_slate_reference"] = canonical
    result["active_slate_games_expected"] = canonical["games_expected"]
    result["audited_subset_only"] = canonical["candidate_is_partial"]
    result["unaudited_canonical_game_ids"] = canonical["unaudited_canonical_game_ids"]
    if canonical["candidate_is_partial"]:
        # A 13/13 recovery batch is NOT a verified 15/15 active slate.
        result["full_slate_article_resolution_verified"] = False
        result["full_slate_claim_support_verified"] = False
        result["publication_authorized"] = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Shadow article verification: {result['games_with_verified_article_resolutions']}/"
          f"{result['games_expected']}; claim verification 0;"
          f" PUBLICATION NOT AUTHORIZED. Diagnostics: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
