from __future__ import annotations

"""Held-out cohort/time-state qualification for the official NFL inactive article parser."""

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
from typing import Any

from research.inactive_article_player_parser_v1 import (
    ParsedInactiveArticle,
    parse_inactive_article_html,
)

SCHEMA_VERSION = "levline-inactive-article-cohort-parser-v2"


def qualify_cohort(
    parsed: ParsedInactiveArticle,
    contract: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cohort_teams = {
        str(game[side])
        for game in contract["due_game_cohort"]
        for side in ("away_team", "home_team")
    }
    expected = contract["frozen_expected_cohort_truth"]
    artifact = contract["validation_artifact"]
    cohort_rows = [row for row in parsed.rows if str(row["team"]) in cohort_teams]

    counts = Counter(str(row["team"]) for row in cohort_rows)
    emergency = sum(int(bool(row["emergency_third_qb"])) for row in cohort_rows)
    observed_pairs = {
        (str(row["team"]), str(row["player_name_rendered"])) for row in cohort_rows
    }
    observed_emergency = {
        (str(row["team"]), str(row["player_name_rendered"]))
        for row in cohort_rows
        if row["emergency_third_qb"]
    }
    expected_pairs = {tuple(pair) for pair in expected["sentinel_player_team_pairs"]}
    expected_emergency = {tuple(pair) for pair in expected["sentinel_emergency_third_qbs"]}
    observed_teams = set(counts)

    gates = {
        "raw_sha256_exact": parsed.audit["raw_html_sha256"] == artifact["raw_html_sha256"],
        "all_due_teams_present": cohort_teams.issubset(observed_teams),
        "cohort_team_section_count_exact": len(observed_teams) == expected["team_sections"],
        "cohort_inactive_entry_count_exact": len(cohort_rows) == expected["inactive_entries"],
        "cohort_emergency_annotation_count_exact": emergency
        == expected["emergency_third_qb_annotations"],
        "cohort_team_entry_counts_exact": dict(sorted(counts.items()))
        == dict(sorted(expected["team_entry_counts"].items())),
        "all_cohort_sentinel_player_team_pairs_present": expected_pairs.issubset(observed_pairs),
        "all_cohort_sentinel_emergency_qbs_present": expected_emergency.issubset(observed_emergency),
        "full_parser_zero_unparseable_entries": bool(parsed.audit["zero_unparseable_entries"]),
        "full_parser_zero_duplicate_team_sections": bool(parsed.audit["zero_duplicate_team_sections"]),
        "full_parser_zero_duplicate_players_within_team": bool(
            parsed.audit["zero_duplicate_players_within_team"]
        ),
    }
    passed = all(gates.values())
    receipt = {
        "contract_id": contract["contract_id"],
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if passed else "FAIL",
        "qualification_passed": passed,
        "gates": gates,
        "observed": {
            "raw_html_sha256": parsed.audit["raw_html_sha256"],
            "full_article_team_sections": parsed.audit["team_sections"],
            "full_article_inactive_entries": parsed.audit["inactive_entries"],
            "cohort_teams": sorted(observed_teams),
            "cohort_team_sections": len(observed_teams),
            "cohort_inactive_entries": len(cohort_rows),
            "cohort_emergency_third_qb_annotations": emergency,
            "cohort_team_entry_counts": dict(sorted(counts.items())),
        },
        "authority": {
            "player_level_parser_qualified_for_due_cohort_filtering": passed,
            "full_day_article_completeness_assumed": False,
            "absence_of_team_section_means_active_or_healthy": False,
            "player_identity_to_gsis_qualified": False,
            "availability_probability_feature_authorized": False,
            "player_value_join_authorized": False,
            "forecast_probability_effect_authorized": False,
            "production_authorized": False,
        },
        "completed_2026_outcomes_used": 0,
    }
    return receipt, cohort_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--archive-gzip", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--rows", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    artifact = contract["validation_artifact"]
    with gzip.open(args.archive_gzip, "rb") as handle:
        raw_html = handle.read()
    parsed = parse_inactive_article_html(
        raw_html,
        source_url=artifact["article_url"],
        captured_at_utc=artifact["captured_at_utc"],
        raw_html_sha256=artifact["raw_html_sha256"],
    )
    receipt, cohort_rows = qualify_cohort(parsed, contract)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.rows.parent.mkdir(parents=True, exist_ok=True)
    with args.rows.open("w", encoding="utf-8") as handle:
        for row in cohort_rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if not receipt["qualification_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
