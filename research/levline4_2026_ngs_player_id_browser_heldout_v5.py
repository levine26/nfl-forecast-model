#!/usr/bin/env python3
"""LevLine 4 NGS browser-context held-out resolver V5 (research only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

GSIS_RE = re.compile(r"^00-[0-9]{7}$")
PLAYER_SEARCH_HOST = "api.ngs.nfl.com"
PLAYER_SEARCH_PATH = "/league/player/search"
SUFFIX_RE = re.compile(r"\s+(?:jr\.?|sr\.?|ii|iii|iv|v)\s*$", re.I)
EDGE_PUNCT_RE = re.compile(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def clean(value: Any) -> str:
    return str(value or "").strip()


def int_or_none(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    text = clean(value)
    return int(text) if re.fullmatch(r"[0-9]+", text) else None


def base_normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def name_key(value: Any) -> str:
    text = base_normalize(value)
    tokens = text.split()
    if tokens and tokens[-1] in {"jr", "sr", "ii", "iii", "iv", "v"}:
        tokens = tokens[:-1]
    n = 0
    while n < len(tokens) and len(tokens[n]) == 1 and tokens[n].isalpha():
        n += 1
    if n >= 2:
        tokens = ["".join(tokens[:n])] + tokens[n:]
    return " ".join(tokens)


def strip_terminal_suffix(value: Any) -> str:
    return SUFFIX_RE.sub("", clean(value)).strip()


def surname_only(value: Any) -> str | None:
    base = strip_terminal_suffix(value)
    if not base:
        return None
    token = EDGE_PUNCT_RE.sub("", base.split()[-1])
    alnum = re.sub(r"[^A-Za-z0-9]", "", token)
    return token if len(alnum) >= 3 else None


def query_plan(visible_name: str) -> list[tuple[str, str]]:
    exact = clean(visible_name)
    plan: list[tuple[str, str]] = [("exact_visible_name", exact)]
    stripped = strip_terminal_suffix(exact)
    if stripped and stripped != exact:
        plan.append(("terminal_suffix_stripped", stripped))
    surname = surname_only(exact)
    if surname and surname not in {query for _, query in plan}:
        plan.append(("surname_only", surname))
    return plan[:3]


def row_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return clean(row.get("team")), clean(row.get("visible_name")), clean(row.get("profile_path"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{line_no}: non-object")
        rows.append(obj)
    return rows


def selection_key(row: dict[str, Any], contract: dict[str, Any]) -> str:
    cfg = contract["target_selection"]
    fields = [
        clean(row.get("team")),
        clean(row.get("visible_name")),
        clean(row.get("position")),
        clean(row.get("jersey_number")),
        clean(row.get("profile_path")),
    ]
    payload = cfg["selection_salt"] + "\x1e" + "\x1f".join(fields)
    return sha256_bytes(payload.encode("utf-8"))


def canonical_sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(raw)


def select_targets(
    rows: Iterable[dict[str, Any]], contract: dict[str, Any], v3_selection: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = contract["target_selection"]
    sentinels = {base_normalize(x) for x in cfg["exclusions"]["normalized_v1_sentinel_visible_names"]}
    prior = {row_identity(x) for x in v3_selection["targets"]}
    eligible = [
        dict(row)
        for row in rows
        if clean(row.get("team"))
        and clean(row.get("visible_name"))
        and clean(row.get("position"))
        and base_normalize(row.get("visible_name")) not in sentinels
        and row_identity(row) not in prior
    ]
    assert len(eligible) == cfg["expected_eligible_row_count"]

    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        by_team[clean(row["team"])].append(row)

    def order(row: dict[str, Any]):
        return selection_key(row, contract), clean(row.get("visible_name")), clean(row.get("profile_path"))

    coverage: list[dict[str, Any]] = []
    for team in sorted(by_team):
        coverage.extend(sorted(by_team[team], key=order)[: cfg["coverage_stratum"]["per_team_count"]])
    alias = sorted(by_team[cfg["team_alias_ari_stratum"]["team"]], key=order)[: cfg["team_alias_ari_stratum"]["expected_target_count"]]
    regexes = [re.compile(x, re.I if "Jr" in x else 0) for x in cfg["source_name_variant_stratum"]["source_only_regexes"]]
    variants = [row for row in eligible if any(rx.search(clean(row["visible_name"])) for rx in regexes)]
    assert len(variants) == cfg["source_name_variant_stratum"]["expected_eligible_count"]
    variants = sorted(
        variants,
        key=lambda row: (
            selection_key(row, contract),
            clean(row["team"]),
            clean(row["visible_name"]),
            clean(row.get("profile_path")),
        ),
    )[: cfg["source_name_variant_stratum"]["expected_target_count"]]

    strata: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    target_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for name, subset in (("coverage", coverage), ("team_alias_ari", alias), ("source_name_variant", variants)):
        for row in subset:
            rid = row_identity(row)
            target_map[rid] = row
            strata[rid].append(name)

    targets: list[dict[str, Any]] = []
    for rid in sorted(target_map):
        row = dict(target_map[rid])
        row["_strata"] = [s for s in ("coverage", "team_alias_ari", "source_name_variant") if s in strata[rid]]
        row["_selection_key_sha256"] = selection_key(row, contract)
        targets.append(row)

    sets = {
        key: {row_identity(row) for row in subset}
        for key, subset in (("coverage", coverage), ("team_alias_ari", alias), ("source_name_variant", variants))
    }
    identities = [[clean(r["team"]), clean(r["visible_name"]), clean(r.get("profile_path"))] for r in targets]
    projection = [
        {
            "team": clean(r["team"]),
            "visible_name": clean(r["visible_name"]),
            "position": clean(r.get("position")),
            "jersey_number": clean(r.get("jersey_number")),
            "profile_path": clean(r.get("profile_path")),
            "strata": r["_strata"],
            "selection_key_sha256": r["_selection_key_sha256"],
        }
        for r in targets
    ]
    diagnostics = {
        "eligible_row_count": len(eligible),
        "team_count": len(by_team),
        "coverage_target_count": len(coverage),
        "team_alias_ari_target_count": len(alias),
        "source_name_variant_target_count": len(variants),
        "total_target_count": len(targets),
        "overlap_counts": {
            "coverage_and_team_alias_ari": len(sets["coverage"] & sets["team_alias_ari"]),
            "coverage_and_source_name_variant": len(sets["coverage"] & sets["source_name_variant"]),
            "team_alias_ari_and_source_name_variant": len(sets["team_alias_ari"] & sets["source_name_variant"]),
            "all_three": len(sets["coverage"] & sets["team_alias_ari"] & sets["source_name_variant"]),
        },
        "sorted_row_identity_sha256": canonical_sha(identities),
        "target_projection_sha256": canonical_sha(projection),
    }
    assert diagnostics["team_count"] == cfg["coverage_stratum"]["expected_team_count"]
    assert diagnostics["coverage_target_count"] == cfg["coverage_stratum"]["expected_target_count"]
    assert diagnostics["overlap_counts"] == cfg["expected_overlap_counts"]
    assert diagnostics["total_target_count"] == cfg["expected_total_target_count"]
    assert diagnostics["sorted_row_identity_sha256"] == cfg["expected_sorted_row_identity_sha256"]
    assert diagnostics["target_projection_sha256"] == cfg["expected_target_projection_sha256"]
    return targets, diagnostics


def matches_player_search_response(url: str, query: str) -> bool:
    parsed = urllib.parse.urlparse(str(url or ""))
    terms = urllib.parse.parse_qs(parsed.query, keep_blank_values=True).get("term", [])
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() == PLAYER_SEARCH_HOST
        and parsed.path == PLAYER_SEARCH_PATH
        and len(terms) == 1
        and terms[0] == query
    )


def parse_players_body(status: int | None, body: bytes) -> tuple[dict[str, Any] | None, bool, str | None]:
    if status != 200:
        return None, False, f"http_status_{status}" if status is not None else "no_matching_browser_response"
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return None, False, f"json_parse_error:{type(exc).__name__}"
    if not isinstance(obj, dict) or not isinstance(obj.get("players"), list):
        return obj if isinstance(obj, dict) else None, False, "http_200_without_object_players_array"
    if not all(isinstance(player, dict) for player in obj["players"]):
        return obj, False, "players_array_contains_non_object"
    return obj, True, None


def candidate_projection(player: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "displayName", "teamAbbr", "position", "positionGroup", "uniformNumber", "jerseyNumber",
        "gsisId", "nflId", "esbId", "smartId", "status", "statusShortDescription",
    )
    return {key: player.get(key) for key in keys}


def team_matches(official: str, ngs: str) -> bool:
    official = clean(official).upper()
    ngs = clean(ngs).upper()
    return ngs in ({"ARI", "AZ"} if official == "ARI" else {official})


def resolve_target(target: dict[str, Any], payload: dict[str, Any] | None) -> dict[str, Any]:
    players = payload.get("players", []) if isinstance(payload, dict) else []
    target_key = name_key(target.get("visible_name"))
    target_team = clean(target.get("team")).upper()
    primary = [
        player
        for player in players
        if isinstance(player, dict)
        and name_key(player.get("displayName")) == target_key
        and team_matches(target_team, player.get("teamAbbr"))
    ]
    tiebreak_applied = len(primary) > 1
    narrowed = primary
    if tiebreak_applied:
        target_position = clean(target.get("position")).upper()
        target_jersey = int_or_none(target.get("jersey_number"))
        narrowed = []
        if target_position and target_jersey is not None:
            for player in primary:
                positions = {clean(player.get("position")).upper(), clean(player.get("positionGroup")).upper()}
                jersey = int_or_none(player.get("uniformNumber"))
                if jersey is None:
                    jersey = int_or_none(player.get("jerseyNumber"))
                if target_position in positions and jersey == target_jersey:
                    narrowed.append(player)

    candidate = narrowed[0] if len(narrowed) == 1 else None
    gsis = clean(candidate.get("gsisId")) if candidate else ""
    gsis_valid = bool(candidate and GSIS_RE.fullmatch(gsis))
    resolved = bool(candidate and gsis_valid)
    official_jersey = int_or_none(target.get("jersey_number"))
    ngs_jersey = None
    if candidate:
        ngs_jersey = int_or_none(candidate.get("uniformNumber"))
        if ngs_jersey is None:
            ngs_jersey = int_or_none(candidate.get("jerseyNumber"))
    comparable = resolved and official_jersey is not None and ngs_jersey is not None
    return {
        "target_name_key": target_key,
        "target_team": target_team,
        "response_player_count": len(players),
        "primary_candidate_count": len(primary),
        "primary_candidates": [candidate_projection(player) for player in primary],
        "tiebreak_applied": tiebreak_applied,
        "tiebreak_candidate_count": len(narrowed) if tiebreak_applied else None,
        "tiebreak_succeeded": bool(tiebreak_applied and resolved),
        "selected_candidate": candidate_projection(candidate) if candidate else None,
        "selected_candidate_gsis_raw": gsis if candidate else None,
        "selected_candidate_gsis_valid": gsis_valid,
        "selected_gsis_id": gsis if resolved else None,
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
        return [by_id[row_identity(target)] for target in targets if name in target["_strata"]]

    coverage = stratum("coverage")
    alias = stratum("team_alias_ari")
    variants = stratum("source_name_variant")
    resolved = lambda rows: [row for row in rows if row["resolved"]]
    coverage_resolved = resolved(coverage)
    alias_resolved = resolved(alias)
    variant_resolved = resolved(variants)
    all_attempts = [attempt for result in results for attempt in result["query_attempts"]]
    all_parseable = bool(all_attempts) and all(
        attempt["http_status"] == 200 and attempt["parseable_players_array"] for attempt in all_attempts
    )
    invalid = [
        result for result in results
        if result["selected_candidate"] is not None and not result["selected_candidate_gsis_valid"]
    ]
    gsis_rows: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for result in results:
        if result["resolved"]:
            gsis_rows[result["selected_gsis_id"]].append(tuple(result["target_row_identity"]))
    duplicates = {gsis: identities for gsis, identities in gsis_rows.items() if len(set(identities)) > 1}

    independent_coverage = [result for result in coverage_resolved if not result["tiebreak_applied"]]
    comparable = [result for result in independent_coverage if result["jersey_comparable"]]
    agreements = [result for result in comparable if result["jersey_agrees"]]
    fallback = [result for result in results if len(result["query_attempts"]) > 1]
    fallback_success = [result for result in fallback if result["resolved"]]
    tiebreak = [result for result in results if result["tiebreak_applied"]]
    tiebreak_success = [result for result in tiebreak if result["tiebreak_succeeded"]]
    alias_az_exercised = [
        result for result in alias_resolved
        if clean((result.get("selected_candidate") or {}).get("teamAbbr")).upper() == "AZ"
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
            gsis: [list(identity) for identity in identities] for gsis, identities in sorted(duplicates.items())
        },
    }
    gates = {
        "page_loaded_and_unique_query_input": page_loaded and query_input_count == 1,
        "every_executed_query_attempt_http_200_parseable_players_array": all_parseable,
        "coverage_unique_resolution_minimum": (
            len(coverage_resolved) >= cfg["coverage_stratum_unique_resolution_minimum_count"]
            and fraction(len(coverage_resolved), len(coverage)) >= cfg["coverage_stratum_unique_resolution_minimum_fraction"]
        ),
        "team_alias_ari_unique_resolution_required": (
            len(alias_resolved) == cfg["team_alias_ari_stratum_unique_resolution_required_count"]
            and fraction(len(alias_resolved), len(alias)) == cfg["team_alias_ari_stratum_unique_resolution_required_fraction"]
        ),
        "source_name_variant_unique_resolution_minimum": (
            len(variant_resolved) >= cfg["source_name_variant_stratum_unique_resolution_minimum_count"]
            and fraction(len(variant_resolved), len(variants)) >= cfg["source_name_variant_stratum_unique_resolution_minimum_fraction"]
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
        "query_fallback_semantics_qualified": passed and len(fallback_success) > 0,
        "multiple_candidate_tiebreak_qualified": passed and len(tiebreak_success) > 0,
    }
    return metrics, gates, passed, conditional


def run_probe(contract_path: Path, roster_path: Path, v3_selection_path: Path, output_dir: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    response_dir = output_dir / "responses"
    response_dir.mkdir(parents=True, exist_ok=True)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract["schema_version"] != "levline4-2026-ngs-player-id-browser-heldout-v5-contract":
        raise ValueError("unexpected contract schema")
    rows = load_jsonl(roster_path)
    v3_selection = json.loads(v3_selection_path.read_text(encoding="utf-8"))
    roster_cfg = contract["frozen_upstream_evidence"]["official_club_roster_v2"]
    if sha256_file(roster_path) != roster_cfg["roster_metadata_sha256"] or len(rows) != roster_cfg["row_count"]:
        raise ValueError("roster source mismatch")
    v3_cfg = contract["frozen_upstream_evidence"]["ngs_browser_heldout_v3"]
    if sha256_file(v3_selection_path) != v3_cfg["target_selection_sha256"]:
        raise ValueError("V3 selection mismatch")

    targets, diagnostics = select_targets(rows, contract, v3_selection)
    (output_dir / "target_selection.json").write_text(
        json.dumps(
            {
                "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v5-target-selection",
                "contract_id": contract["contract_id"],
                "source_roster_metadata_sha256": sha256_file(roster_path),
                "v3_target_selection_sha256": sha256_file(v3_selection_path),
                "selection_diagnostics": diagnostics,
                "targets": targets,
            },
            indent=2,
            sort_keys=True,
        ) + "\n",
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
            locator = page.get_by_placeholder(browser_cfg["query_input_placeholder_exact"], exact=True)
            query_input_count = locator.count()
        except Exception as exc:
            browser_error = f"{type(exc).__name__}: {exc}"

        for target_index, target in enumerate(targets, 1):
            attempts: list[dict[str, Any]] = []
            chosen_payload: dict[str, Any] | None = None
            action_error = browser_error
            if browser_error is None and locator is not None and query_input_count == 1:
                for attempt_index, (query_kind, query) in enumerate(query_plan(clean(target["visible_name"])), 1):
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
                            lambda response, expected=query: matches_player_search_response(response.url, expected),
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

                    relpath = f"responses/target_{target_index:03d}_attempt_{attempt_index}.json"
                    (output_dir / relpath).write_bytes(body)
                    parsed, parseable, semantic_error = parse_players_body(status, body)
                    player_count = len(parsed.get("players", [])) if parseable and isinstance(parsed, dict) else 0
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
                            "response_sha256": sha256_bytes(body),
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
                    "target_row_identity": list(row_identity(target)),
                    "target_visible_name": clean(target["visible_name"]),
                    "target_team": clean(target["team"]),
                    "target_position": clean(target["position"]),
                    "target_jersey_number": clean(target.get("jersey_number")),
                    "target_profile_path": clean(target.get("profile_path")),
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
        authority = dict(contract["authority_if_and_only_if_all_v5_gates_pass"])
        authority["ari_az_team_alias_qualified_for_frozen_v5_population"] = conditional["ari_az_team_alias_qualified"]
        authority["query_fallback_semantics_qualified_for_frozen_v5_population"] = conditional["query_fallback_semantics_qualified"]
        authority["multiple_candidate_tiebreak_qualified_for_frozen_v5_population"] = conditional["multiple_candidate_tiebreak_qualified"]
    else:
        authority = dict(contract["authority_if_any_v5_gate_fails"])

    receipt = {
        "schema_version": "levline4-2026-ngs-player-id-browser-heldout-v5-receipt",
        "contract_id": contract["contract_id"],
        "captured_at_utc": utc_now(),
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
            "manual_headers_or_credentials_used": False,
            "browser_storage_state_persisted": False,
            "direct_http_fallback_used": False,
            "explicit_retry_used": False,
        },
        "metrics": metrics,
        "gates": gates,
        "conditional_capability_evidence": conditional,
        "authority": authority,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "week2_inactive_execution_evidence_used_for_design": False,
        "f_st_01_frozen_2026_unchanged": True,
        "research_only": True,
        "production_paths_changed": False,
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
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    receipt = run_probe(args.contract, args.roster_metadata, args.v3_target_selection, args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
