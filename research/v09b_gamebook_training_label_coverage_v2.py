from __future__ import annotations

"""V2 fail-closed Game Book coverage audit across documented official NFL hosts.

V1 remains permanently BLOCKED for the frozen www.nfl.com-only source family. V2 asks
whether the missing coverage is recovered by the historically documented nflcdns.nfl.com
mirror while preserving the exact schedule universe and 100% coverage threshold.

Coverage qualification is still not target-semantic qualification and does not authorize
P(active) fitting.
"""

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd
import requests

from research.v09b_gamebook_training_label_coverage_v1 import (
    ArchiveSource,
    CDX_ENDPOINT,
    _load_schedule,
    _select_sample,
    _stable_schedule_hash,
    evaluate_sample_semantics,
    home_code_candidates,
    parse_cdx_json,
)

CONTRACT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_contract_v2.json"
)
V1_RECEIPT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_receipt_v1.json"
)
OUTPUT_DIR_DEFAULT = Path("research_outputs/v09b_gamebook_training_label_coverage_v2")
TRAINING_SEASONS = tuple(range(2012, 2022))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def source_host(source: ArchiveSource) -> str:
    return urlparse(source.original).netloc.casefold()


def fetch_cdx_family(
    *,
    prefix: str,
    family: str,
    session: Any = requests,
    timeout_seconds: int = 120,
) -> tuple[list[ArchiveSource], dict[str, Any]]:
    params: list[tuple[str, str]] = [
        ("url", prefix),
        ("matchType", "prefix"),
        ("output", "json"),
        ("fl", "timestamp,original,statuscode,digest,mimetype,length"),
        ("filter", "statuscode:200"),
        ("filter", r"original:.*_Gamebook\.pdf"),
        ("collapse", "urlkey"),
        ("limit", "150000"),
    ]
    response = session.get(
        CDX_ENDPOINT,
        params=params,
        timeout=timeout_seconds,
        headers={"User-Agent": "nfl-forecast-model research source audit/2.0"},
    )
    response.raise_for_status()
    raw = bytes(response.content)
    rows = parse_cdx_json(response.json())
    return rows, {
        "family": family,
        "prefix": prefix,
        "endpoint": str(getattr(response, "url", CDX_ENDPOINT)),
        "http_status": int(getattr(response, "status_code", 200)),
        "response_bytes": len(raw),
        "parsed_gamebook_urls": len(rows),
    }


def fetch_all_source_families(
    *,
    contract: dict[str, Any],
    session: Any = requests,
) -> tuple[list[ArchiveSource], list[dict[str, Any]], list[str]]:
    all_sources: list[ArchiveSource] = []
    metadata: list[dict[str, Any]] = []
    errors: list[str] = []
    for family in contract["official_source_families"]:
        try:
            rows, meta = fetch_cdx_family(
                prefix=str(family["prefix"]),
                family=str(family["family"]),
                session=session,
            )
            all_sources.extend(rows)
            metadata.append(meta)
        except Exception as exc:
            metadata.append(
                {
                    "family": str(family["family"]),
                    "prefix": str(family["prefix"]),
                    "http_status": None,
                    "response_bytes": 0,
                    "parsed_gamebook_urls": 0,
                    "error": str(exc)[:1000],
                }
            )
            errors.append(f"CDX source family fetch failed: {family['family']}: {str(exc)[:500]}")
    return all_sources, metadata, errors


def index_sources(
    sources: Iterable[ArchiveSource],
) -> dict[tuple[str, str], list[ArchiveSource]]:
    out: dict[tuple[str, str], list[ArchiveSource]] = defaultdict(list)
    for source in sources:
        out[(source.gsis, source.team_code)].append(source)
    for key in out:
        out[key] = sorted(
            out[key], key=lambda item: (source_host(item), item.timestamp, item.original)
        )
    return dict(out)


def resolve_game_source_v2(
    *,
    gsis: str,
    home_team: str,
    source_index: dict[tuple[str, str], list[ArchiveSource]],
    contract: dict[str, Any],
) -> tuple[ArchiveSource | None, dict[str, Any]]:
    codes = home_code_candidates(home_team, contract)
    host_priority = {
        host.casefold(): index
        for index, host in enumerate(contract["mirror_policy"]["preferred_host_order"])
    }
    by_code: dict[str, list[ArchiveSource]] = {}
    for code in codes:
        rows = source_index.get((gsis, code), [])
        if rows:
            by_code[code] = rows

    alias_conflict = len(by_code) > 1
    chosen_code = next((code for code in codes if code in by_code), "")
    mirror_rows = by_code.get(chosen_code, [])
    ordered = sorted(
        mirror_rows,
        key=lambda item: (
            host_priority.get(source_host(item), 999),
            item.timestamp,
            item.original,
        ),
    )
    chosen = ordered[0] if ordered else None
    return chosen, {
        "resolved_team_codes": sorted(by_code),
        "alias_conflict": alias_conflict,
        "mirror_count": len(ordered),
        "mirror_hosts": sorted({source_host(row) for row in ordered}),
        "chosen_team_code": chosen_code,
    }


def build_source_map_v2(
    schedule: pd.DataFrame,
    sources: list[ArchiveSource],
    contract: dict[str, Any],
) -> pd.DataFrame:
    source_index = index_sources(sources)
    rows: list[dict[str, Any]] = []
    for record in schedule.to_dict(orient="records"):
        gsis = str(record["gsis_normalized"])
        chosen, diagnostic = resolve_game_source_v2(
            gsis=gsis,
            home_team=str(record["home_team"]),
            source_index=source_index,
            contract=contract,
        )
        rows.append(
            {
                "season": int(record["season"]),
                "week": int(record["week"]),
                "game_id": str(record["game_id"]),
                "gsis": gsis,
                "away_team": str(record["away_team"]),
                "home_team": str(record["home_team"]),
                "home_code_candidates": "|".join(
                    home_code_candidates(str(record["home_team"]), contract)
                ),
                "archive_found": chosen is not None,
                "alias_conflict": bool(diagnostic["alias_conflict"]),
                "resolved_team_codes": "|".join(diagnostic["resolved_team_codes"]),
                "mirror_count": int(diagnostic["mirror_count"]),
                "mirror_hosts": "|".join(diagnostic["mirror_hosts"]),
                "archive_host": source_host(chosen) if chosen else "",
                "archive_timestamp": chosen.timestamp if chosen else "",
                "archive_original": chosen.original if chosen else "",
                "archive_digest": chosen.digest if chosen else "",
                "archive_mimetype": chosen.mimetype if chosen else "",
                "archive_length": chosen.length if chosen else "",
            }
        )
    return pd.DataFrame(rows)


def summarize_v2(
    *,
    schedule: pd.DataFrame,
    source_map: pd.DataFrame,
    sample_results: list[dict[str, Any]],
    family_metadata: list[dict[str, Any]],
    family_errors: list[str],
    contract: dict[str, Any],
    v1_receipt: dict[str, Any],
) -> dict[str, Any]:
    expected = {
        int(k): int(v)
        for k, v in contract["source_universe"]["expected_regular_season_games_by_season"].items()
    }
    blockers = list(family_errors)
    metrics_by_season: dict[str, Any] = {}

    if v1_receipt.get("technical_status") != "BLOCKED":
        blockers.append("V1 predecessor receipt is not preserved as BLOCKED")
    if v1_receipt.get("historical_gamebook_coverage_qualified") is not False:
        blockers.append("V1 predecessor receipt unexpectedly qualifies coverage")

    for season in TRAINING_SEASONS:
        sched = schedule.loc[schedule["season"] == season]
        mapped = source_map.loc[source_map["season"] == season]
        expected_games = expected[season]
        found = int(mapped["archive_found"].sum()) if len(mapped) else 0
        conflicts = int(mapped["alias_conflict"].sum()) if len(mapped) else 0
        missing_gsis = int((sched["gsis_normalized"] == "").sum()) if len(sched) else expected_games
        coverage = found / len(mapped) if len(mapped) else 0.0
        host_counts = {
            str(host): int(count)
            for host, count in mapped.loc[mapped["archive_found"], "archive_host"].value_counts().items()
        }
        metrics_by_season[str(season)] = {
            "expected_games_contract": expected_games,
            "schedule_games": int(len(sched)),
            "missing_gsis": missing_gsis,
            "archive_games_found": found,
            "archive_games_missing": int(len(mapped) - found),
            "combined_archive_coverage_rate": coverage,
            "alias_conflict_games": conflicts,
            "chosen_host_counts": host_counts,
        }
        if len(sched) != expected_games:
            blockers.append(
                f"schedule expected-game-count gate failed: {season} expected {expected_games} got {len(sched)}"
            )
        if missing_gsis:
            blockers.append(f"schedule GSIS gate failed: {season} missing {missing_gsis}")
        if coverage != 1.0:
            blockers.append(
                f"combined archive coverage gate failed: {season} {found}/{len(mapped)} = {coverage:.6f}"
            )
        if conflicts:
            blockers.append(f"alias conflict gate failed: {season} {conflicts}")

    matched = source_map.loc[source_map["archive_found"]]
    missing_timestamp = int((matched["archive_timestamp"].astype(str).str.len() == 0).sum())
    missing_digest = int((matched["archive_digest"].astype(str).str.len() == 0).sum())
    if missing_timestamp:
        blockers.append(f"archive provenance timestamp gate failed: {missing_timestamp}")
    if missing_digest:
        blockers.append(f"archive provenance digest gate failed: {missing_digest}")

    required_sample = int(contract["frozen_qualification_gates"]["sample_games_per_season"]) * len(
        TRAINING_SEASONS
    )
    sample_count = len(sample_results)
    downloads = sum(bool(row.get("download_ok")) for row in sample_results)
    not_active = sum(bool(row.get("not_active_structure")) for row in sample_results)
    did_not_play = sum(bool(row.get("did_not_play_structure")) for row in sample_results)
    if sample_count != required_sample:
        blockers.append(f"sample cardinality gate failed: required {required_sample} got {sample_count}")
    if sample_count == 0 or downloads != sample_count:
        blockers.append(f"sample PDF download gate failed: {downloads}/{sample_count}")
    if sample_count == 0 or not_active != sample_count:
        blockers.append(f"sample Not Active structure gate failed: {not_active}/{sample_count}")
    if sample_count == 0 or did_not_play != sample_count:
        blockers.append(f"sample Did Not Play structure gate failed: {did_not_play}/{sample_count}")

    expected_total = int(contract["source_universe"]["expected_regular_season_games_total"])
    total_schedule = len(schedule)
    total_found = int(source_map["archive_found"].sum()) if len(source_map) else 0
    total_coverage = total_found / len(source_map) if len(source_map) else 0.0
    total_conflicts = int(source_map["alias_conflict"].sum()) if len(source_map) else 0
    if total_schedule != expected_total:
        blockers.append(
            f"total schedule expected-game-count gate failed: expected {expected_total} got {total_schedule}"
        )
    if total_coverage != 1.0:
        blockers.append(
            f"total combined archive coverage gate failed: {total_found}/{len(source_map)} = {total_coverage:.6f}"
        )
    if total_conflicts:
        blockers.append(f"total alias conflict gate failed: {total_conflicts}")

    coverage_qualified = not blockers
    host_counts_total = {
        str(host): int(count)
        for host, count in matched["archive_host"].value_counts().items()
    }
    return {
        "contract_id": contract["contract_id"],
        "technical_status": "QUALIFIED" if coverage_qualified else "BLOCKED",
        "historical_gamebook_coverage_qualified": coverage_qualified,
        "v1_failure_preserved": True,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "schedule_subset_sha256": _stable_schedule_hash(schedule),
        "source_family_indexes": family_metadata,
        "metrics": {
            "expected_games_contract": expected_total,
            "schedule_games": total_schedule,
            "archive_games_found": total_found,
            "archive_games_missing": int(len(source_map) - total_found),
            "combined_archive_coverage_rate": total_coverage,
            "alias_conflict_games": total_conflicts,
            "matched_rows_missing_timestamp": missing_timestamp,
            "matched_rows_missing_digest": missing_digest,
            "chosen_host_counts": host_counts_total,
            "sample_games": sample_count,
            "sample_pdf_downloads_ok": downloads,
            "sample_not_active_structure_ok": not_active,
            "sample_did_not_play_structure_ok": did_not_play,
        },
        "metrics_by_season": metrics_by_season,
        "hard_blockers": blockers,
        "interpretation": {
            "v1_www_only_result_remains_blocked": True,
            "v2_scope": "combined official-host source addressability, archive provenance, and sampled document structure only",
            "coverage_pass_does_not_qualify_target_semantics": True,
            "independent_contemporaneous_inactive_crosschecks_required": True,
            "full_player_identity_audit_required_before_labels": True,
        },
        "governance": {
            "source_only_audit": True,
            "labels_constructed": False,
            "model_fit_performed": False,
            "game_outcomes_used": 0,
            "completed_2026_outcomes_used": 0,
            "production_dependency_authorized": False,
            "candidate_promotion_authorized": False,
        },
    }


def execute(
    *,
    output_dir: Path,
    session: Any = requests,
    run_sample_downloads: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = _load_json(CONTRACT_PATH)
    v1_receipt = _load_json(V1_RECEIPT_PATH)
    schedule = _load_schedule()
    sources, family_metadata, family_errors = fetch_all_source_families(
        contract=contract, session=session
    )
    source_map = build_source_map_v2(schedule, sources, contract)
    sample_per_season = int(contract["frozen_qualification_gates"]["sample_games_per_season"])
    sample = _select_sample(source_map, sample_per_season)
    sample_results = (
        evaluate_sample_semantics(sample, session=session) if run_sample_downloads else []
    )
    report = summarize_v2(
        schedule=schedule,
        source_map=source_map,
        sample_results=sample_results,
        family_metadata=family_metadata,
        family_errors=family_errors,
        contract=contract,
        v1_receipt=v1_receipt,
    )
    source_map.to_csv(output_dir / "game_source_map.csv", index=False)
    (output_dir / "sample_semantics.json").write_text(
        json.dumps(sample_results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "qualification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR_DEFAULT)
    parser.add_argument("--skip-sample-downloads", action="store_true")
    args = parser.parse_args()
    report = execute(
        output_dir=args.output_dir,
        run_sample_downloads=not args.skip_sample_downloads,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
