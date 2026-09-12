from __future__ import annotations

"""Source-only residual path diagnostic after blocked V09B Game Book coverage V2.

V3 does not add a source host or change any qualification threshold. It reproduces V2,
then asks whether the 70 residual scheduled games have archived files under the same two
official NFL GSIS directories that V2 missed solely because its CDX query filtered on the
canonical `_Gamebook.pdf` spelling.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlparse

import pandas as pd
import requests

from research.v09b_gamebook_training_label_coverage_v1 import CDX_ENDPOINT, _load_schedule
from research.v09b_gamebook_training_label_coverage_v2 import (
    build_source_map_v2,
    fetch_all_source_families,
)

CONTRACT_PATH = Path("research/availability/v09b_gamebook_residual_path_audit_v3.json")
V2_CONTRACT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_contract_v2.json"
)
V2_RECEIPT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_receipt_v2.json"
)
OUTPUT_DIR_DEFAULT = Path("research_outputs/v09b_gamebook_residual_path_audit_v3")
GAMEBOOK_PDF_RE = re.compile(r"gamebook.*\.pdf$", re.IGNORECASE)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _host(url: str) -> str:
    return (urlparse(str(url)).hostname or "").casefold()


def _path_gsis(url: str) -> str:
    match = re.search(r"/liveupdate/gamecenter/(\d+)/", urlparse(str(url)).path, re.IGNORECASE)
    return match.group(1) if match else ""


def _basename(url: str) -> str:
    path = unquote(urlparse(str(url)).path)
    return path.rsplit("/", 1)[-1]


def _is_pdf(url: str) -> bool:
    return _basename(url).casefold().endswith(".pdf")


def _is_gamebook_pdf(url: str) -> bool:
    return bool(GAMEBOOK_PDF_RE.search(_basename(url)))


def parse_cdx_directory_payload(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, list) or not payload:
        return []
    header = payload[0]
    if not isinstance(header, list):
        raise ValueError("CDX directory response header is not a list")
    required = ["timestamp", "original", "statuscode", "digest", "mimetype", "length"]
    missing = [field for field in required if field not in header]
    if missing:
        raise ValueError(f"CDX directory response missing fields: {missing}")
    indexes = {name: header.index(name) for name in required}
    rows: list[dict[str, str]] = []
    for row in payload[1:]:
        if not isinstance(row, list) or len(row) < len(header):
            continue
        rows.append({name: str(row[indexes[name]] or "") for name in required})
    return rows


def query_directory(
    *,
    prefix: str,
    gsis: str,
    session: Any = requests,
    timeout_seconds: int = 30,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    url_prefix = f"{prefix}{gsis}/"
    params: list[tuple[str, str]] = [
        ("url", url_prefix),
        ("matchType", "prefix"),
        ("output", "json"),
        ("fl", "timestamp,original,statuscode,digest,mimetype,length"),
        ("filter", "statuscode:200"),
        ("collapse", "urlkey"),
        ("limit", "500"),
    ]
    response = session.get(
        CDX_ENDPOINT,
        params=params,
        timeout=timeout_seconds,
        headers={"User-Agent": "nfl-forecast-model residual source audit/3.0"},
    )
    response.raise_for_status()
    rows = parse_cdx_directory_payload(response.json())
    return rows, {
        "query_prefix": url_prefix,
        "http_status": int(getattr(response, "status_code", 200)),
        "rows": len(rows),
    }


def audit_game_directories(
    games: pd.DataFrame,
    *,
    contract: dict[str, Any],
    session: Any = requests,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    authorized_hosts = {str(x).casefold() for x in contract["authorized_hosts_exact"]}
    source_families = list(contract["source_families"])
    candidate_rows: list[dict[str, Any]] = []
    query_rows: list[dict[str, Any]] = []

    for game in games.to_dict(orient="records"):
        gsis = str(game["gsis"])
        for family in source_families:
            family_name = str(family["family"])
            prefix = str(family["prefix"])
            query_record: dict[str, Any] = {
                "season": int(game["season"]),
                "week": int(game["week"]),
                "game_id": str(game["game_id"]),
                "gsis": gsis,
                "away_team": str(game["away_team"]),
                "home_team": str(game["home_team"]),
                "family": family_name,
                "prefix": prefix,
                "query_ok": False,
                "http_status": None,
                "rows": 0,
                "pdf_rows": 0,
                "gamebook_candidate_rows": 0,
                "error": "",
            }
            try:
                rows, metadata = query_directory(
                    prefix=prefix,
                    gsis=gsis,
                    session=session,
                )
                query_record["query_ok"] = True
                query_record["http_status"] = metadata["http_status"]
                query_record["rows"] = metadata["rows"]
                for row in rows:
                    original = row["original"]
                    host = _host(original)
                    path_gsis = _path_gsis(original)
                    pdf = _is_pdf(original)
                    gamebook = _is_gamebook_pdf(original)
                    if pdf:
                        query_record["pdf_rows"] += 1
                    if gamebook:
                        query_record["gamebook_candidate_rows"] += 1
                    if not pdf:
                        continue
                    candidate_rows.append(
                        {
                            "season": int(game["season"]),
                            "week": int(game["week"]),
                            "game_id": str(game["game_id"]),
                            "scheduled_gsis": gsis,
                            "away_team": str(game["away_team"]),
                            "home_team": str(game["home_team"]),
                            "family": family_name,
                            "timestamp": row["timestamp"],
                            "original": original,
                            "host": host,
                            "path_gsis": path_gsis,
                            "basename": _basename(original),
                            "digest": row["digest"],
                            "mimetype": row["mimetype"],
                            "length": row["length"],
                            "is_gamebook_candidate": gamebook,
                            "authorized_host": host in authorized_hosts,
                            "gsis_matches": path_gsis == gsis,
                        }
                    )
            except Exception as exc:
                query_record["error"] = str(exc)[:1000]
            query_rows.append(query_record)

    return pd.DataFrame(candidate_rows), query_rows


def execute(
    *,
    output_dir: Path,
    session: Any = requests,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = _load_json(CONTRACT_PATH)
    v2_contract = _load_json(V2_CONTRACT_PATH)
    v2_receipt = _load_json(V2_RECEIPT_PATH)

    schedule = _load_schedule()
    sources, family_metadata, family_errors = fetch_all_source_families(
        contract=v2_contract,
        session=session,
    )
    source_map = build_source_map_v2(schedule, sources, v2_contract)
    residual = source_map.loc[~source_map["archive_found"]].copy()
    conflicts = source_map.loc[source_map["alias_conflict"]].copy()

    expected_missing = int(contract["residual_universe"]["expected_v2_missing_games"])
    expected_covered = int(contract["residual_universe"]["expected_v2_coverage_games"])
    expected_total = int(contract["residual_universe"]["expected_total_games"])

    reproduction_blockers: list[str] = list(family_errors)
    if len(schedule) != expected_total:
        reproduction_blockers.append(
            f"V2 schedule reproduction mismatch: expected {expected_total} got {len(schedule)}"
        )
    covered = int(source_map["archive_found"].sum())
    if covered != expected_covered:
        reproduction_blockers.append(
            f"V2 coverage reproduction mismatch: expected {expected_covered} got {covered}"
        )
    if len(residual) != expected_missing:
        reproduction_blockers.append(
            f"V2 residual reproduction mismatch: expected {expected_missing} got {len(residual)}"
        )
    expected_conflicts = int(contract["alias_conflict_diagnostic"]["v2_alias_conflict_games_expected"])
    if len(conflicts) != expected_conflicts:
        reproduction_blockers.append(
            f"V2 alias-conflict reproduction mismatch: expected {expected_conflicts} got {len(conflicts)}"
        )
    if v2_receipt.get("technical_status") != "BLOCKED":
        reproduction_blockers.append("V2 predecessor receipt is not preserved as BLOCKED")

    residual_candidates, residual_queries = audit_game_directories(
        residual,
        contract=contract,
        session=session,
    )
    conflict_candidates, conflict_queries = audit_game_directories(
        conflicts,
        contract=contract,
        session=session,
    )

    all_candidates = pd.concat(
        [residual_candidates, conflict_candidates],
        ignore_index=True,
    ) if (len(residual_candidates) or len(conflict_candidates)) else pd.DataFrame()
    all_queries = residual_queries + conflict_queries

    residual_gamebook = (
        residual_candidates.loc[
            residual_candidates["is_gamebook_candidate"]
            & residual_candidates["authorized_host"]
            & residual_candidates["gsis_matches"]
        ].copy()
        if len(residual_candidates)
        else pd.DataFrame()
    )
    candidate_games = sorted(set(residual_gamebook["game_id"])) if len(residual_gamebook) else []
    query_errors = [row for row in all_queries if not row["query_ok"]]
    successful_queries = sum(bool(row["query_ok"]) for row in all_queries)
    expected_queries = (len(residual) + len(conflicts)) * len(contract["source_families"])

    if reproduction_blockers:
        status = "BLOCKED_REPRODUCTION_MISMATCH"
    elif query_errors:
        status = "INCONCLUSIVE_NETWORK_OR_CDX_ERRORS"
    elif candidate_games:
        status = "ADDITIONAL_KNOWN_HOST_PATH_CANDIDATES_FOUND"
    else:
        status = "NO_ADDITIONAL_KNOWN_HOST_PATHS_FOUND"

    basename_counts = Counter(
        str(x) for x in residual_gamebook["basename"].tolist()
    ) if len(residual_gamebook) else Counter()
    family_counts = Counter(
        str(x) for x in residual_gamebook["family"].tolist()
    ) if len(residual_gamebook) else Counter()

    report = {
        "contract_id": contract["contract_id"],
        "technical_status": status,
        "v2_failure_preserved": True,
        "v2_reproduction": {
            "schedule_games": int(len(schedule)),
            "covered_games": covered,
            "residual_games": int(len(residual)),
            "alias_conflict_games": int(len(conflicts)),
            "source_family_indexes": family_metadata,
            "blockers": reproduction_blockers,
        },
        "directory_queries": {
            "expected": expected_queries,
            "attempted": len(all_queries),
            "successful": successful_queries,
            "errors": len(query_errors),
        },
        "residual_path_findings": {
            "residual_games": int(len(residual)),
            "games_with_additional_gamebook_candidate": len(candidate_games),
            "games_without_additional_gamebook_candidate": int(len(residual) - len(candidate_games)),
            "candidate_game_ids": candidate_games,
            "candidate_rows": int(len(residual_gamebook)),
            "candidate_family_counts": dict(sorted(family_counts.items())),
            "candidate_basename_counts": dict(sorted(basename_counts.items())),
            "all_pdf_rows_in_residual_directories": int(len(residual_candidates)),
        },
        "alias_conflict_diagnostic": {
            "games": int(len(conflicts)),
            "pdf_rows": int(len(conflict_candidates)),
            "gamebook_rows": int(
                conflict_candidates["is_gamebook_candidate"].sum()
                if len(conflict_candidates) else 0
            ),
        },
        "interpretation": {
            "known_host_path_audit_only": True,
            "new_host_family_tested": False,
            "candidate_found_does_not_reclassify_v2": True,
            "candidate_found_does_not_qualify_coverage": True,
            "no_candidate_found_does_not_prove_no_other_official_host_exists": True,
            "network_errors_are_inconclusive": True,
        },
        "authorization": {
            "training_label_semantics_qualified": False,
            "training_source_chronology_qualified": False,
            "v09b_model_fit_authorized": False,
            "production_authorized": False,
        },
        "governance": {
            "source_only_audit": True,
            "labels_constructed": False,
            "model_fit_performed": False,
            "game_outcomes_used": 0,
            "completed_2026_outcomes_used": 0,
        },
    }

    residual.to_csv(output_dir / "v2_residual_games.csv", index=False)
    conflicts.to_csv(output_dir / "v2_alias_conflict_games.csv", index=False)
    pd.DataFrame(all_queries).to_csv(output_dir / "directory_queries.csv", index=False)
    if len(all_candidates):
        all_candidates.to_csv(output_dir / "directory_pdf_candidates.csv", index=False)
    else:
        pd.DataFrame(
            columns=[
                "season", "week", "game_id", "scheduled_gsis", "away_team", "home_team",
                "family", "timestamp", "original", "host", "path_gsis", "basename", "digest",
                "mimetype", "length", "is_gamebook_candidate", "authorized_host", "gsis_matches",
            ]
        ).to_csv(output_dir / "directory_pdf_candidates.csv", index=False)
    (output_dir / "qualification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR_DEFAULT)
    args = parser.parse_args()
    report = execute(output_dir=args.output_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
