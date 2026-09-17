#!/usr/bin/env python3
"""LevLine 4 NGS browser-context held-out resolver V7 (research only).

V7 extends the frozen V6/V5 resolver with exactly one preregistered source-native
identity representation: official-club roster ``canonical_data_name``.  It does
not use fuzzy matching, manual aliases, status, participation, outcomes, or
availability evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from research import levline4_2026_ngs_player_id_browser_heldout_v6_frozen_base as base

_SUFFIX_TOKEN_RE = re.compile(r"^(?:jr\.?|sr\.?|ii|iii|iv|v)$", re.I)


def canonical_query_name(value: Any) -> str | None:
    """Convert the source-native ``family,given [suffix]`` field deterministically.

    Empty comma components are discarded to tolerate source markup such as
    ``murray,,kenneth jr.`` without inventing any token.  Exactly two nonempty
    components must remain.  A terminal suffix on the given-name side is moved
    to the end, preserving its source spelling.
    """
    parts = [base.clean(part) for part in base.clean(value).split(",") if base.clean(part)]
    if len(parts) != 2:
        return None
    family, given = parts
    tokens = given.split()
    if not family or not tokens:
        return None
    suffix: str | None = None
    if _SUFFIX_TOKEN_RE.fullmatch(tokens[-1]):
        suffix = tokens.pop()
    given_core = " ".join(tokens).strip()
    if not given_core:
        return None
    return " ".join([given_core, family] + ([suffix] if suffix else []))


def source_name_keys(target: dict[str, Any]) -> tuple[str, str | None, set[str]]:
    visible_key = base.name_key(target.get("visible_name"))
    canonical = canonical_query_name(target.get("canonical_data_name"))
    canonical_key = base.name_key(canonical) if canonical else ""
    keys = {visible_key}
    if canonical_key:
        keys.add(canonical_key)
    return visible_key, canonical if canonical else None, keys


def query_plan(target: dict[str, Any]) -> list[tuple[str, str]]:
    visible = base.clean(target.get("visible_name"))
    plan: list[tuple[str, str]] = [("exact_visible_name", visible)]

    stripped = base.strip_terminal_suffix(visible)
    if stripped and stripped != visible:
        plan.append(("terminal_suffix_stripped", stripped))

    canonical = canonical_query_name(target.get("canonical_data_name"))
    if (
        canonical
        and base.name_key(canonical) != base.name_key(visible)
        and canonical not in {query for _, query in plan}
    ):
        plan.append(("source_canonical_name", canonical))

    surname = base.surname_only(visible)
    if surname and surname not in {query for _, query in plan}:
        plan.append(("surname_only", surname))
    return plan[:4]


def select_targets(
    rows: Iterable[dict[str, Any]],
    contract: dict[str, Any],
    v3_selection: dict[str, Any],
    v5_selection: dict[str, Any],
    v6_selection: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = contract["target_selection"]
    v3_targets = list(v3_selection.get("targets", []))
    v5_targets = list(v5_selection.get("targets", []))
    v6_targets = list(v6_selection.get("targets", []))
    assert len(v3_targets) == 70
    assert len(v5_targets) == 74
    assert len(v6_targets) == 78

    prior_sets = [
        {base.row_identity(row) for row in v3_targets},
        {base.row_identity(row) for row in v5_targets},
        {base.row_identity(row) for row in v6_targets},
    ]
    assert not (prior_sets[0] & prior_sets[1])
    assert not (prior_sets[0] & prior_sets[2])
    assert not (prior_sets[1] & prior_sets[2])
    prior = set().union(*prior_sets)

    sentinels = {
        base.base_normalize(name)
        for name in cfg["exclusions"]["normalized_v1_sentinel_visible_names"]
    }
    eligible = [
        dict(row)
        for row in rows
        if base.clean(row.get("team"))
        and base.clean(row.get("visible_name"))
        and base.clean(row.get("position"))
        and base.base_normalize(row.get("visible_name")) not in sentinels
        and base.row_identity(row) not in prior
    ]
    assert len(eligible) == cfg["expected_eligible_row_count"]

    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_team[base.clean(row["team"])].append(row)

    def order(row: dict[str, Any]):
        return (
            base.selection_key(row, contract),
            base.clean(row.get("visible_name")),
            base.clean(row.get("profile_path")),
        )

    coverage: list[dict[str, Any]] = []
    for team in sorted(by_team):
        coverage.extend(
            sorted(by_team[team], key=order)[: cfg["coverage_stratum"]["per_team_count"]]
        )
    alias = sorted(
        by_team[cfg["team_alias_ari_stratum"]["team"]], key=order
    )[: cfg["team_alias_ari_stratum"]["expected_target_count"]]

    regexes = [
        re.compile(expr, re.I if "Jr" in expr else 0)
        for expr in cfg["source_name_variant_stratum"]["source_only_regexes"]
    ]
    variants = [
        row
        for row in eligible
        if any(rx.search(base.clean(row["visible_name"])) for rx in regexes)
    ]
    assert len(variants) == cfg["source_name_variant_stratum"]["expected_eligible_count"]
    variants = sorted(
        variants,
        key=lambda row: (
            base.selection_key(row, contract),
            base.clean(row["team"]),
            base.clean(row["visible_name"]),
            base.clean(row.get("profile_path")),
        ),
    )[: cfg["source_name_variant_stratum"]["expected_target_count"]]

    canonical_variants = []
    for row in eligible:
        canonical = canonical_query_name(row.get("canonical_data_name"))
        if canonical and base.name_key(canonical) != base.name_key(row.get("visible_name")):
            canonical_variants.append(row)
    assert (
        len(canonical_variants)
        == cfg["canonical_name_variant_stratum"]["expected_eligible_count"]
    )
    canonical_variants = sorted(
        canonical_variants,
        key=lambda row: (
            base.selection_key(row, contract),
            base.clean(row["team"]),
            base.clean(row["visible_name"]),
            base.clean(row.get("profile_path")),
        ),
    )[: cfg["canonical_name_variant_stratum"]["expected_target_count"]]

    ordered_strata = (
        "coverage",
        "team_alias_ari",
        "source_name_variant",
        "canonical_name_variant",
    )
    subsets = (
        ("coverage", coverage),
        ("team_alias_ari", alias),
        ("source_name_variant", variants),
        ("canonical_name_variant", canonical_variants),
    )
    strata: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    target_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for name, subset in subsets:
        for row in subset:
            rid = base.row_identity(row)
            target_map[rid] = row
            strata[rid].append(name)

    targets: list[dict[str, Any]] = []
    for rid in sorted(target_map):
        row = dict(target_map[rid])
        row["_strata"] = [name for name in ordered_strata if name in strata[rid]]
        row["_selection_key_sha256"] = base.selection_key(row, contract)
        row["_canonical_query_name"] = canonical_query_name(row.get("canonical_data_name"))
        targets.append(row)

    sets = {
        name: {base.row_identity(row) for row in subset}
        for name, subset in subsets
    }
    overlap_counts = {
        "coverage_and_team_alias_ari": len(sets["coverage"] & sets["team_alias_ari"]),
        "coverage_and_source_name_variant": len(
            sets["coverage"] & sets["source_name_variant"]
        ),
        "coverage_and_canonical_name_variant": len(
            sets["coverage"] & sets["canonical_name_variant"]
        ),
        "team_alias_and_source_name_variant": len(
            sets["team_alias_ari"] & sets["source_name_variant"]
        ),
        "team_alias_and_canonical_name_variant": len(
            sets["team_alias_ari"] & sets["canonical_name_variant"]
        ),
        "source_name_variant_and_canonical_name_variant": len(
            sets["source_name_variant"] & sets["canonical_name_variant"]
        ),
        "coverage_team_alias_source_name_variant": len(
            sets["coverage"] & sets["team_alias_ari"] & sets["source_name_variant"]
        ),
        "coverage_team_alias_canonical_name_variant": len(
            sets["coverage"] & sets["team_alias_ari"] & sets["canonical_name_variant"]
        ),
        "coverage_source_name_variant_canonical_name_variant": len(
            sets["coverage"] & sets["source_name_variant"] & sets["canonical_name_variant"]
        ),
        "team_alias_source_name_variant_canonical_name_variant": len(
            sets["team_alias_ari"]
            & sets["source_name_variant"]
            & sets["canonical_name_variant"]
        ),
        "all_four": len(
            sets["coverage"]
            & sets["team_alias_ari"]
            & sets["source_name_variant"]
            & sets["canonical_name_variant"]
        ),
    }

    identities = [
        [
            base.clean(row["team"]),
            base.clean(row["visible_name"]),
            base.clean(row.get("profile_path")),
        ]
        for row in targets
    ]
    projection = [
        {
            "team": base.clean(row["team"]),
            "visible_name": base.clean(row["visible_name"]),
            "canonical_data_name": base.clean(row.get("canonical_data_name")),
            "canonical_query_name": base.clean(row.get("_canonical_query_name")),
            "position": base.clean(row.get("position")),
            "jersey_number": base.clean(row.get("jersey_number")),
            "profile_path": base.clean(row.get("profile_path")),
            "strata": row["_strata"],
            "selection_key_sha256": row["_selection_key_sha256"],
        }
        for row in targets
    ]
    diagnostics = {
        "eligible_row_count": len(eligible),
        "team_count": len(by_team),
        "coverage_target_count": len(coverage),
        "team_alias_ari_target_count": len(alias),
        "source_name_variant_target_count": len(variants),
        "canonical_name_variant_target_count": len(canonical_variants),
        "canonical_name_variant_eligible_count": sum(
            1
            for row in eligible
            if (canonical_query_name(row.get("canonical_data_name")))
            and base.name_key(canonical_query_name(row.get("canonical_data_name")))
            != base.name_key(row.get("visible_name"))
        ),
        "total_target_count": len(targets),
        "overlap_counts": overlap_counts,
        "sorted_row_identity_sha256": base.canonical_sha(identities),
        "target_projection_sha256": base.canonical_sha(projection),
    }
    assert diagnostics["team_count"] == cfg["coverage_stratum"]["expected_team_count"]
    assert diagnostics["coverage_target_count"] == cfg["coverage_stratum"]["expected_target_count"]
    assert diagnostics["team_alias_ari_target_count"] == cfg["team_alias_ari_stratum"]["expected_target_count"]
    assert diagnostics["source_name_variant_target_count"] == cfg["source_name_variant_stratum"]["expected_target_count"]
    assert diagnostics["canonical_name_variant_target_count"] == cfg["canonical_name_variant_stratum"]["expected_target_count"]
    assert diagnostics["canonical_name_variant_eligible_count"] == cfg["canonical_name_variant_stratum"]["expected_eligible_count"]
    assert diagnostics["overlap_counts"] == cfg["expected_overlap_counts"]
    assert diagnostics["total_target_count"] == cfg["expected_total_target_count"]
    assert diagnostics["sorted_row_identity_sha256"] == cfg["expected_sorted_row_identity_sha256"]
    assert diagnostics["target_projection_sha256"] == cfg["expected_target_projection_sha256"]

    selected = {base.row_identity(row) for row in targets}
    assert not (selected & prior)
    return targets, diagnostics


def resolve_target(target: dict[str, Any], payload: dict[str, Any] | None) -> dict[str, Any]:
    players = payload.get("players", []) if isinstance(payload, dict) else []
    visible_key, canonical, allowed_keys = source_name_keys(target)
    canonical_key = base.name_key(canonical) if canonical else ""
    target_team = base.clean(target.get("team")).upper()

    primary = [
        player
        for player in players
        if isinstance(player, dict)
        and base.name_key(player.get("displayName")) in allowed_keys
        and base.team_matches(target_team, player.get("teamAbbr"))
    ]
    tiebreak_applied = len(primary) > 1
    narrowed = primary
    if tiebreak_applied:
        target_position = base.clean(target.get("position")).upper()
        target_jersey = base.int_or_none(target.get("jersey_number"))
        narrowed = []
        if target_position and target_jersey is not None:
            for player in primary:
                positions = {
                    base.clean(player.get("position")).upper(),
                    base.clean(player.get("positionGroup")).upper(),
                }
                jersey = base.int_or_none(player.get("uniformNumber"))
                if jersey is None:
                    jersey = base.int_or_none(player.get("jerseyNumber"))
                if target_position in positions and jersey == target_jersey:
                    narrowed.append(player)

    candidate = narrowed[0] if len(narrowed) == 1 else None
    gsis = base.clean(candidate.get("gsisId")) if candidate else ""
    gsis_valid = bool(candidate and base.GSIS_RE.fullmatch(gsis))
    resolved = bool(candidate and gsis_valid)

    official_jersey = base.int_or_none(target.get("jersey_number"))
    ngs_jersey = None
    if candidate:
        ngs_jersey = base.int_or_none(candidate.get("uniformNumber"))
        if ngs_jersey is None:
            ngs_jersey = base.int_or_none(candidate.get("jerseyNumber"))
    comparable = resolved and official_jersey is not None and ngs_jersey is not None

    selected_key = base.name_key(candidate.get("displayName")) if candidate else ""
    if candidate and canonical_key and canonical_key != visible_key and selected_key == canonical_key:
        selected_representation = "source_canonical"
    elif candidate and selected_key == visible_key:
        selected_representation = "visible"
    else:
        selected_representation = None

    return {
        "target_visible_name_key": visible_key,
        "target_source_canonical_query_name": canonical,
        "target_source_canonical_name_key": canonical_key or None,
        "target_allowed_name_keys": sorted(allowed_keys),
        "target_team": target_team,
        "response_player_count": len(players),
        "primary_candidate_count": len(primary),
        "primary_candidates": [base.candidate_projection(player) for player in primary],
        "tiebreak_applied": tiebreak_applied,
        "tiebreak_candidate_count": len(narrowed) if tiebreak_applied else None,
        "tiebreak_succeeded": bool(tiebreak_applied and resolved),
        "selected_candidate": base.candidate_projection(candidate) if candidate else None,
        "selected_candidate_gsis_raw": gsis if candidate else None,
        "selected_candidate_gsis_valid": gsis_valid,
        "selected_gsis_id": gsis if resolved else None,
        "selected_name_representation": selected_representation,
        "resolved": resolved,
        "official_jersey_int": official_jersey,
        "ngs_jersey_int": ngs_jersey,
        "jersey_comparable": comparable,
        "jersey_agrees": (official_jersey == ngs_jersey) if comparable else None,
    }


def evaluate_gates(
    targets: list[dict[str, Any]],
    results: list[dict[str, Any]],
    contract: dict[str, Any],
    page_loaded: bool,
    query_input_count: int,
) -> tuple[dict[str, Any], dict[str, bool], bool, dict[str, bool]]:
    cfg = contract["frozen_pass_gates"]
    by_id = {tuple(result["target_row_identity"]): result for result in results}

    def stratum(name: str) -> list[dict[str, Any]]:
        return [by_id[base.row_identity(target)] for target in targets if name in target["_strata"]]

    coverage = stratum("coverage")
    alias = stratum("team_alias_ari")
    variants = stratum("source_name_variant")
    canonical_variants = stratum("canonical_name_variant")

    def resolved(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [row for row in rows if row["resolved"]]

    coverage_resolved = resolved(coverage)
    alias_resolved = resolved(alias)
    variant_resolved = resolved(variants)
    canonical_resolved = resolved(canonical_variants)
    all_attempts = [attempt for result in results for attempt in result["query_attempts"]]
    all_parseable = bool(all_attempts) and all(
        attempt["http_status"] == 200 and attempt["parseable_players_array"]
        for attempt in all_attempts
    )
    invalid = [
        result
        for result in results
        if result["selected_candidate"] is not None
        and not result["selected_candidate_gsis_valid"]
    ]
    gsis_rows: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for result in results:
        if result["resolved"]:
            gsis_rows[result["selected_gsis_id"]].append(tuple(result["target_row_identity"]))
    duplicates = {
        gsis: identities
        for gsis, identities in gsis_rows.items()
        if len(set(identities)) > 1
    }

    independent_coverage = [
        result for result in coverage_resolved if not result["tiebreak_applied"]
    ]
    comparable = [
        result for result in independent_coverage if result["jersey_comparable"]
    ]
    agreements = [result for result in comparable if result["jersey_agrees"]]
    fallback = [result for result in results if len(result["query_attempts"]) > 1]
    fallback_success = [result for result in fallback if result["resolved"]]
    tiebreak = [result for result in results if result["tiebreak_applied"]]
    tiebreak_success = [result for result in tiebreak if result["tiebreak_succeeded"]]
    alias_az_exercised = [
        result
        for result in alias_resolved
        if base.clean((result.get("selected_candidate") or {}).get("teamAbbr")).upper()
        == "AZ"
    ]
    canonical_attempted = [
        result
        for result in results
        if any(a["query_kind"] == "source_canonical_name" for a in result["query_attempts"])
    ]
    canonical_success = [
        result
        for result in canonical_attempted
        if result["resolved"] and result["selected_name_representation"] == "source_canonical"
    ]

    def fraction(num: int, den: int) -> float:
        return num / den if den else 0.0

    metrics = {
        "target_count": len(results),
        "executed_query_attempt_count": len(all_attempts),
        "all_executed_query_attempts_http_200_parseable_players_array": all_parseable,
        "coverage_target_count": len(coverage),
        "coverage_unique_resolution_count": len(coverage_resolved),
        "coverage_unique_resolution_fraction": fraction(len(coverage_resolved), len(coverage)),
        "team_alias_ari_target_count": len(alias),
        "team_alias_ari_unique_resolution_count": len(alias_resolved),
        "team_alias_ari_unique_resolution_fraction": fraction(len(alias_resolved), len(alias)),
        "team_alias_ari_selected_ngs_az_count": len(alias_az_exercised),
        "source_name_variant_target_count": len(variants),
        "source_name_variant_unique_resolution_count": len(variant_resolved),
        "source_name_variant_unique_resolution_fraction": fraction(len(variant_resolved), len(variants)),
        "canonical_name_variant_target_count": len(canonical_variants),
        "canonical_name_variant_unique_resolution_count": len(canonical_resolved),
        "canonical_name_variant_unique_resolution_fraction": fraction(len(canonical_resolved), len(canonical_variants)),
        "source_canonical_query_exercised_count": len(canonical_attempted),
        "source_canonical_query_success_count": len(canonical_success),
        "invalid_selected_gsis_count": len(invalid),
        "duplicate_selected_gsis_across_distinct_target_rows_count": len(duplicates),
        "independent_resolved_coverage_count": len(independent_coverage),
        "independent_resolved_coverage_jersey_comparable_count": len(comparable),
        "independent_resolved_coverage_jersey_comparable_fraction": fraction(len(comparable), len(independent_coverage)),
        "independent_resolved_coverage_jersey_agreement_count": len(agreements),
        "independent_resolved_coverage_jersey_agreement_fraction": fraction(len(agreements), len(comparable)),
        "fallback_exercised_count": len(fallback),
        "fallback_success_count": len(fallback_success),
        "tiebreak_exercised_count": len(tiebreak),
        "tiebreak_success_count": len(tiebreak_success),
        "duplicate_selected_gsis_assignments": {
            gsis: [list(identity) for identity in identities]
            for gsis, identities in sorted(duplicates.items())
        },
    }
    gates = {
        "page_loaded_and_unique_query_input": page_loaded and query_input_count == 1,
        "every_executed_query_attempt_http_200_parseable_players_array": all_parseable,
        "coverage_unique_resolution_minimum": (
            len(coverage_resolved) >= cfg["coverage_stratum_unique_resolution_minimum_count"]
            and fraction(len(coverage_resolved), len(coverage))
            >= cfg["coverage_stratum_unique_resolution_minimum_fraction"]
        ),
        "team_alias_ari_unique_resolution_required": (
            len(alias_resolved) == cfg["team_alias_ari_stratum_unique_resolution_required_count"]
            and fraction(len(alias_resolved), len(alias))
            == cfg["team_alias_ari_stratum_unique_resolution_required_fraction"]
        ),
        "source_name_variant_unique_resolution_minimum": (
            len(variant_resolved) >= cfg["source_name_variant_stratum_unique_resolution_minimum_count"]
            and fraction(len(variant_resolved), len(variants))
            >= cfg["source_name_variant_stratum_unique_resolution_minimum_fraction"]
        ),
        "canonical_name_variant_unique_resolution_minimum": (
            len(canonical_resolved) >= cfg["canonical_name_variant_stratum_unique_resolution_minimum_count"]
            and fraction(len(canonical_resolved), len(canonical_variants))
            >= cfg["canonical_name_variant_stratum_unique_resolution_minimum_fraction"]
        ),
        "invalid_selected_gsis_zero": len(invalid) <= cfg["invalid_selected_gsis_count_allowed"],
        "duplicate_selected_gsis_zero": len(duplicates) <= cfg["duplicate_selected_gsis_across_distinct_target_rows_allowed"],
        "independent_resolved_coverage_jersey_comparable_minimum": (
            fraction(len(comparable), len(independent_coverage))
            >= cfg["independent_resolved_coverage_jersey_comparable_minimum_fraction"]
        ),
        "independent_resolved_coverage_jersey_agreement_minimum": (
            fraction(len(agreements), len(comparable))
            >= cfg["independent_resolved_coverage_jersey_agreement_minimum_fraction"]
        ),
    }
    passed = all(gates.values())
    conditional = {
        "ari_az_team_alias_qualified": passed and len(alias_az_exercised) > 0,
        "source_canonical_name_representation_qualified": passed and len(canonical_success) > 0,
        "query_fallback_semantics_qualified": passed and len(fallback_success) > 0,
        "multiple_candidate_tiebreak_qualified": passed and len(tiebreak_success) > 0,
    }
    return metrics, gates, passed, conditional


def run_probe(
    contract_path: Path,
    roster_path: Path,
    v3_selection_path: Path,
    v5_selection_path: Path,
    v6_selection_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    response_dir = output_dir / "responses"
    response_dir.mkdir(parents=True, exist_ok=True)

    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["schema_version"] != "levline4-2026-ngs-player-id-browser-heldout-v7-contract":
        raise ValueError("unexpected V7 contract schema")
    rows = base.load_jsonl(roster_path)
    v3_selection = json.loads(v3_selection_path.read_text(encoding="utf-8"))
    v5_selection = json.loads(v5_selection_path.read_text(encoding="utf-8"))
    v6_selection = json.loads(v6_selection_path.read_text(encoding="utf-8"))

    roster_cfg = contract["frozen_upstream_evidence"]["official_club_roster_v2"]
    if base.sha256_file(roster_path) != roster_cfg["roster_metadata_sha256"] or len(rows) != roster_cfg["row_count"]:
        raise ValueError("roster source mismatch")
    for path, key in (
        (v3_selection_path, "ngs_browser_heldout_v3"),
        (v5_selection_path, "ngs_browser_heldout_v5_empirical_exposure_only"),
        (v6_selection_path, "ngs_browser_heldout_v6"),
    ):
        if base.sha256_file(path) != contract["frozen_upstream_evidence"][key]["target_selection_sha256"]:
            raise ValueError(f"{key} selection mismatch")

    targets, diagnostics = select_targets(
        rows, contract, v3_selection, v5_selection, v6_selection
    )
    (output_dir / "target_selection.json").write_text(
        json.dumps(
            {
                "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v7-target-selection",
                "contract_id": contract["contract_id"],
                "source_roster_metadata_sha256": base.sha256_file(roster_path),
                "v3_target_selection_sha256": base.sha256_file(v3_selection_path),
                "v5_target_selection_sha256": base.sha256_file(v5_selection_path),
                "v6_target_selection_sha256": base.sha256_file(v6_selection_path),
                "selection_diagnostics": diagnostics,
                "targets": targets,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    browser_cfg = contract["browser_transport"]
    page_loaded = False
    query_input_count = 0
    browser_error: str | None = None
    results: list[dict[str, Any]] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=browser_cfg["context_user_agent"],
            locale=browser_cfg["context_locale"],
        )
        page = context.new_page()
        locator = None
        try:
            page.goto(
                browser_cfg["page_url"],
                wait_until=browser_cfg["page_load_wait_until"],
                timeout=browser_cfg["page_load_timeout_ms"],
            )
            page.wait_for_timeout(browser_cfg["post_load_settle_ms"])
            page_loaded = True
            locator = page.get_by_placeholder(
                browser_cfg["query_input_placeholder_exact"], exact=True
            )
            query_input_count = locator.count()
        except Exception as exc:
            browser_error = f"{type(exc).__name__}: {exc}"

        for target_index, target in enumerate(targets, 1):
            attempts: list[dict[str, Any]] = []
            chosen_payload: dict[str, Any] | None = None
            action_error = browser_error
            if browser_error is None and locator is not None and query_input_count == 1:
                for attempt_index, (query_kind, query) in enumerate(query_plan(target), 1):
                    if attempt_index > 1:
                        previous = attempts[-1]
                        if not (
                            previous["http_status"] == 200
                            and previous["parseable_players_array"]
                            and previous["player_count"] == 0
                        ):
                            break
                    body = b""
                    status = None
                    response_url = None
                    content_type = None
                    attempt_error = None
                    try:
                        with page.expect_response(
                            lambda response, expected=query: base.matches_player_search_response(
                                response.url, expected
                            ),
                            timeout=browser_cfg["response_timeout_ms"],
                        ) as response_info:
                            locator.fill(query)
                            locator.press("Enter")
                        response = response_info.value
                        response_url = response.url
                        status = int(response.status)
                        content_type = str(response.headers.get("content-type", ""))
                        body = response.body()
                    except Exception as exc:
                        attempt_error = f"{type(exc).__name__}: {exc}"
                        action_error = attempt_error

                    relpath = (
                        f"responses/target_{target_index:03d}_attempt_{attempt_index}.json"
                    )
                    (output_dir / relpath).write_bytes(body)
                    parsed, parseable, semantic_error = base.parse_players_body(
                        status, body
                    )
                    player_count = (
                        len(parsed.get("players", []))
                        if parseable and isinstance(parsed, dict)
                        else 0
                    )
                    attempts.append(
                        {
                            "attempt_index": attempt_index,
                            "query_kind": query_kind,
                            "query": query,
                            "response_url": response_url,
                            "http_status": status,
                            "content_type": content_type,
                            "parseable_players_array": parseable,
                            "player_count": player_count,
                            "semantic_error": semantic_error,
                            "browser_action_error": attempt_error,
                            "response_relpath": relpath,
                            "response_bytes": len(body),
                            "response_sha256": base.sha256_bytes(body),
                        }
                    )
                    if attempt_error or not parseable:
                        break
                    if player_count > 0:
                        chosen_payload = parsed
                        break

            resolution = resolve_target(target, chosen_payload)
            results.append(
                {
                    "target_index": target_index,
                    "target_row_identity": list(base.row_identity(target)),
                    "target_visible_name": base.clean(target["visible_name"]),
                    "target_canonical_data_name": base.clean(
                        target.get("canonical_data_name")
                    ),
                    "target_source_canonical_query_name": canonical_query_name(
                        target.get("canonical_data_name")
                    ),
                    "target_team": base.clean(target["team"]),
                    "target_position": base.clean(target["position"]),
                    "target_jersey_number": base.clean(target.get("jersey_number")),
                    "target_profile_path": base.clean(target.get("profile_path")),
                    "target_strata": target["_strata"],
                    "selection_key_sha256": target["_selection_key_sha256"],
                    "browser_action_error": action_error,
                    "query_attempts": attempts,
                    "fallback_used": len(attempts) > 1,
                    **resolution,
                }
            )
        browser.close()

    with (output_dir / "target_results.jsonl").open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, sort_keys=True) + "\n")

    metrics, gates, passed, conditional = evaluate_gates(
        targets, results, contract, page_loaded, query_input_count
    )
    if passed:
        authority = dict(contract["authority_if_and_only_if_all_v7_gates_pass"])
        authority["ari_az_team_alias_qualified_for_frozen_v7_population"] = conditional[
            "ari_az_team_alias_qualified"
        ]
        authority[
            "source_canonical_name_representation_qualified_for_frozen_v7_population"
        ] = conditional["source_canonical_name_representation_qualified"]
        authority[
            "query_fallback_semantics_qualified_for_frozen_v7_population"
        ] = conditional["query_fallback_semantics_qualified"]
        authority[
            "multiple_candidate_tiebreak_qualified_for_frozen_v7_population"
        ] = conditional["multiple_candidate_tiebreak_qualified"]
    else:
        authority = dict(contract["authority_if_any_v7_gate_fails"])

    receipt = {
        "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v7-receipt",
        "contract_id": contract["contract_id"],
        "captured_at_utc": base.utc_now(),
        "status": "PASS" if passed else "FAIL",
        "target_selection": diagnostics,
        "browser_transport": {
            "page_url": browser_cfg["page_url"],
            "page_loaded": page_loaded,
            "query_input_count": query_input_count,
            "browser_error": browser_error,
            "context_locale": browser_cfg["context_locale"],
            "context_user_agent": browser_cfg["context_user_agent"],
            "post_load_settle_ms": browser_cfg["post_load_settle_ms"],
            "manual_headers_or_credentials_used": false,
            "browser_storage_state_persisted": false,
            "direct_http_fallback_used": false,
            "explicit_retry_used": false
        },
        "metrics": metrics,
        "gates": gates,
        "conditional_capability_evidence": conditional,
        "authority": authority,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": false,
        "week2_inactive_execution_evidence_used_for_design": false,
        "future_information_used_to_repair_point_in_time_state": false,
        "f_st_01_frozen_2026_unchanged": true,
        "research_only": true,
        "production_paths_changed": false
    }
    (output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--roster-metadata", required=True, type=Path)
    parser.add_argument("--v3-target-selection", required=True, type=Path)
    parser.add_argument("--v5-target-selection", required=True, type=Path)
    parser.add_argument("--v6-target-selection", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    receipt = run_probe(
        args.contract,
        args.roster_metadata,
        args.v3_target_selection,
        args.v5_target_selection,
        args.v6_target_selection,
        args.output_dir,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
