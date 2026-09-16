#!/usr/bin/env python3
"""LevLine 4 NGS browser-context held-out resolver V4 (research only)."""
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
    toks = text.split()
    if toks and toks[-1] in {"jr", "sr", "ii", "iii", "iv", "v"}:
        toks = toks[:-1]
    n = 0
    while n < len(toks) and len(toks[n]) == 1 and toks[n].isalpha():
        n += 1
    if n >= 2:
        toks = ["".join(toks[:n])] + toks[n:]
    return " ".join(toks)


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
    if surname and surname not in {q for _, q in plan}:
        plan.append(("surname_only", surname))
    return plan[:3]


def row_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    return clean(row.get("team")), clean(row.get("visible_name")), clean(row.get("profile_path"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    out = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"{path}:{i}: non-object")
        out.append(obj)
    return out


def selection_key(row: dict[str, Any], contract: dict[str, Any]) -> str:
    cfg = contract["target_selection"]
    fields = [clean(row.get("team")), clean(row.get("visible_name")), clean(row.get("position")), clean(row.get("jersey_number")), clean(row.get("profile_path"))]
    payload = cfg["selection_salt"] + "\x1e" + "\x1f".join(fields)
    return sha256_bytes(payload.encode("utf-8"))


def canonical_sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(raw)


def select_targets(rows: Iterable[dict[str, Any]], contract: dict[str, Any], v3_selection: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cfg = contract["target_selection"]
    sentinels = {base_normalize(x) for x in cfg["exclusions"]["normalized_v1_sentinel_visible_names"]}
    prior = {row_identity(x) for x in v3_selection["targets"]}
    eligible = [dict(r) for r in rows if clean(r.get("team")) and clean(r.get("visible_name")) and clean(r.get("position")) and base_normalize(r.get("visible_name")) not in sentinels and row_identity(r) not in prior]
    assert len(eligible) == cfg["expected_eligible_row_count"]
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in eligible:
        by_team[clean(r["team"])].append(r)

    def order(r: dict[str, Any]):
        return selection_key(r, contract), clean(r.get("visible_name")), clean(r.get("profile_path"))

    coverage = []
    for team in sorted(by_team):
        coverage.extend(sorted(by_team[team], key=order)[: cfg["coverage_stratum"]["per_team_count"]])
    alias = sorted(by_team[cfg["team_alias_ari_stratum"]["team"]], key=order)[: cfg["team_alias_ari_stratum"]["expected_target_count"]]
    regexes = [re.compile(x, re.I if "Jr" in x else 0) for x in cfg["source_name_variant_stratum"]["source_only_regexes"]]
    variants = [r for r in eligible if any(rx.search(clean(r["visible_name"])) for rx in regexes)]
    assert len(variants) == cfg["source_name_variant_stratum"]["expected_eligible_count"]
    variants = sorted(variants, key=lambda r: (selection_key(r, contract), clean(r["team"]), clean(r["visible_name"]), clean(r.get("profile_path"))))[: cfg["source_name_variant_stratum"]["expected_target_count"]]

    strata: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    target_map = {}
    for name, subset in (("coverage", coverage), ("team_alias_ari", alias), ("source_name_variant", variants)):
        for r in subset:
            rid = row_identity(r)
            target_map[rid] = r
            strata[rid].append(name)
    targets = []
    for rid in sorted(target_map):
        r = dict(target_map[rid])
        r["_strata"] = [s for s in ("coverage", "team_alias_ari", "source_name_variant") if s in strata[rid]]
        r["_selection_key_sha256"] = selection_key(r, contract)
        targets.append(r)
    ids = [[clean(r["team"]), clean(r["visible_name"]), clean(r.get("profile_path"))] for r in targets]
    proj = [{"team": clean(r["team"]), "visible_name": clean(r["visible_name"]), "position": clean(r.get("position")), "jersey_number": clean(r.get("jersey_number")), "profile_path": clean(r.get("profile_path")), "strata": r["_strata"], "selection_key_sha256": r["_selection_key_sha256"]} for r in targets]
    sets = {k: {row_identity(r) for r in subset} for k, subset in (("coverage", coverage), ("team_alias_ari", alias), ("source_name_variant", variants))}
    diag = {
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
        "sorted_row_identity_sha256": canonical_sha(ids),
        "target_projection_sha256": canonical_sha(proj),
    }
    assert diag["team_count"] == cfg["coverage_stratum"]["expected_team_count"]
    assert diag["coverage_target_count"] == cfg["coverage_stratum"]["expected_target_count"]
    assert diag["overlap_counts"] == cfg["expected_overlap_counts"]
    assert diag["total_target_count"] == cfg["expected_total_target_count"]
    assert diag["sorted_row_identity_sha256"] == cfg["expected_sorted_row_identity_sha256"]
    assert diag["target_projection_sha256"] == cfg["expected_target_projection_sha256"]
    return targets, diag


def matches_player_search_response(url: str, query: str) -> bool:
    p = urllib.parse.urlparse(str(url or ""))
    terms = urllib.parse.parse_qs(p.query, keep_blank_values=True).get("term", [])
    return p.scheme == "https" and (p.hostname or "").lower() == PLAYER_SEARCH_HOST and p.path == PLAYER_SEARCH_PATH and len(terms) == 1 and terms[0] == query


def parse_players_body(status: int | None, body: bytes) -> tuple[dict[str, Any] | None, bool, str | None]:
    if status != 200:
        return None, False, f"http_status_{status}" if status is not None else "no_matching_browser_response"
    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as exc:
        return None, False, f"json_parse_error:{type(exc).__name__}"
    if not isinstance(obj, dict) or not isinstance(obj.get("players"), list):
        return obj if isinstance(obj, dict) else None, False, "http_200_without_object_players_array"
    if not all(isinstance(x, dict) for x in obj["players"]):
        return obj, False, "players_array_contains_non_object"
    return obj, True, None


def candidate_projection(p: dict[str, Any]) -> dict[str, Any]:
    return {k: p.get(k) for k in ("displayName", "teamAbbr", "position", "positionGroup", "uniformNumber", "jerseyNumber", "gsisId", "nflId", "esbId", "smartId", "status", "statusShortDescription")}


def team_matches(official: str, ngs: str) -> bool:
    o = clean(official).upper()
    n = clean(ngs).upper()
    return n in ({"ARI", "AZ"} if o == "ARI" else {o})


def resolve_target(target: dict[str, Any], payload: dict[str, Any] | None) -> dict[str, Any]:
    players = payload.get("players", []) if isinstance(payload, dict) else []
    tkey = name_key(target.get("visible_name"))
    team = clean(target.get("team")).upper()
    primary = [p for p in players if isinstance(p, dict) and name_key(p.get("displayName")) == tkey and team_matches(team, p.get("teamAbbr"))]
    tiebreak_applied = len(primary) > 1
    narrowed = primary
    if tiebreak_applied:
        pos = clean(target.get("position")).upper()
        jersey = int_or_none(target.get("jersey_number"))
        narrowed = []
        if pos and jersey is not None:
            for p in primary:
                npos = {clean(p.get("position")).upper(), clean(p.get("positionGroup")).upper()}
                nj = int_or_none(p.get("uniformNumber"))
                nj = nj if nj is not None else int_or_none(p.get("jerseyNumber"))
                if pos in npos and nj == jersey:
                    narrowed.append(p)
    candidate = narrowed[0] if len(narrowed) == 1 else None
    gsis = clean(candidate.get("gsisId")) if candidate else ""
    valid = bool(candidate and GSIS_RE.fullmatch(gsis))
    resolved = bool(candidate and valid)
    offj = int_or_none(target.get("jersey_number"))
    ngsj = None
    if candidate:
        ngsj = int_or_none(candidate.get("uniformNumber"))
        ngsj = ngsj if ngsj is not None else int_or_none(candidate.get("jerseyNumber"))
    comparable = resolved and offj is not None and ngsj is not None
    return {
        "target_name_key": tkey,
        "target_team": team,
        "response_player_count": len(players),
        "primary_candidate_count": len(primary),
        "primary_candidates": [candidate_projection(p) for p in primary],
        "tiebreak_applied": tiebreak_applied,
        "tiebreak_candidate_count": len(narrowed) if tiebreak_applied else None,
        "tiebreak_succeeded": bool(tiebreak_applied and resolved),
        "selected_candidate": candidate_projection(candidate) if candidate else None,
        "selected_candidate_gsis_raw": gsis if candidate else None,
        "selected_candidate_gsis_valid": valid,
        "selected_gsis_id": gsis if resolved else None,
        "resolved": resolved,
        "official_jersey_int": offj,
        "ngs_jersey_int": ngsj,
        "jersey_comparable": comparable,
        "jersey_agrees": offj == ngsj if comparable else None,
    }


def evaluate_gates(targets: list[dict[str, Any]], results: list[dict[str, Any]], contract: dict[str, Any], page_loaded: bool, query_input_count: int) -> tuple[dict[str, Any], dict[str, bool], bool, dict[str, bool]]:
    cfg = contract["frozen_pass_gates"]
    byid = {tuple(r["target_row_identity"]): r for r in results}

    def stratum(name: str):
        return [byid[row_identity(t)] for t in targets if name in t["_strata"]]

    cov, alias, var = stratum("coverage"), stratum("team_alias_ari"), stratum("source_name_variant")
    resolved = lambda xs: [r for r in xs if r["resolved"]]
    covr, aliasr, varr = map(resolved, (cov, alias, var))
    all_attempts = [a for r in results for a in r["query_attempts"]]
    all_parseable = bool(all_attempts) and all(a["http_status"] == 200 and a["parseable_players_array"] for a in all_attempts)
    invalid = [r for r in results if r["selected_candidate"] is not None and not r["selected_candidate_gsis_valid"]]
    gs = defaultdict(list)
    for r in results:
        if r["resolved"]:
            gs[r["selected_gsis_id"]].append(tuple(r["target_row_identity"]))
    dup = {k: v for k, v in gs.items() if len(set(v)) > 1}
    comparable = [r for r in covr if r["jersey_comparable"]]
    agree = [r for r in comparable if r["jersey_agrees"]]
    frac = lambda a, b: (a / b if b else 0.0)
    fallback = [r for r in results if len(r["query_attempts"]) > 1]
    fallback_success = [r for r in fallback if r["resolved"]]
    ties = [r for r in results if r["tiebreak_applied"]]
    ties_success = [r for r in ties if r["tiebreak_succeeded"]]
    metrics = {
        "target_count": len(results),
        "executed_query_attempt_count": len(all_attempts),
        "all_executed_query_attempts_http_200_parseable_players_array": all_parseable,
        "coverage_target_count": len(cov),
        "coverage_unique_resolution_count": len(covr),
        "coverage_unique_resolution_fraction": frac(len(covr), len(cov)),
        "team_alias_ari_target_count": len(alias),
        "team_alias_ari_unique_resolution_count": len(aliasr),
        "team_alias_ari_unique_resolution_fraction": frac(len(aliasr), len(alias)),
        "source_name_variant_target_count": len(var),
        "source_name_variant_unique_resolution_count": len(varr),
        "source_name_variant_unique_resolution_fraction": frac(len(varr), len(var)),
        "invalid_selected_gsis_count": len(invalid),
        "duplicate_selected_gsis_across_distinct_target_rows_count": len(dup),
        "resolved_coverage_jersey_comparable_fraction": frac(len(comparable), len(covr)),
        "resolved_coverage_jersey_agreement_fraction": frac(len(agree), len(comparable)),
        "fallback_exercised_count": len(fallback),
        "fallback_success_count": len(fallback_success),
        "tiebreak_exercised_count": len(ties),
        "tiebreak_success_count": len(ties_success),
        "duplicate_selected_gsis_assignments": {k: [list(x) for x in v] for k, v in sorted(dup.items())},
    }
    gates = {
        "page_loaded_and_unique_query_input": page_loaded and query_input_count == 1,
        "every_executed_query_attempt_http_200_parseable_players_array": all_parseable,
        "coverage_unique_resolution_minimum": len(covr) >= cfg["coverage_stratum_unique_resolution_minimum_count"] and frac(len(covr), len(cov)) >= cfg["coverage_stratum_unique_resolution_minimum_fraction"],
        "team_alias_ari_unique_resolution_required": len(aliasr) == cfg["team_alias_ari_stratum_unique_resolution_required_count"] and frac(len(aliasr), len(alias)) == cfg["team_alias_ari_stratum_unique_resolution_required_fraction"],
        "source_name_variant_unique_resolution_minimum": len(varr) >= cfg["source_name_variant_stratum_unique_resolution_minimum_count"] and frac(len(varr), len(var)) >= cfg["source_name_variant_stratum_unique_resolution_minimum_fraction"],
        "invalid_selected_gsis_zero": len(invalid) <= cfg["invalid_selected_gsis_count_allowed"],
        "duplicate_selected_gsis_zero": len(dup) <= cfg["duplicate_selected_gsis_across_distinct_target_rows_allowed"],
        "resolved_coverage_jersey_comparable_minimum": frac(len(comparable), len(covr)) >= cfg["resolved_coverage_jersey_comparable_minimum_fraction"],
        "resolved_coverage_jersey_agreement_minimum": frac(len(agree), len(comparable)) >= cfg["resolved_coverage_jersey_agreement_minimum_fraction"],
    }
    passed = all(gates.values())
    conditional = {
        "ari_az_team_alias_qualified": passed and gates["team_alias_ari_unique_resolution_required"],
        "query_fallback_semantics_qualified": passed and len(fallback_success) > 0,
        "multiple_candidate_tiebreak_qualified": passed and len(ties_success) > 0,
    }
    return metrics, gates, passed, conditional


def run_probe(contract_path: Path, roster_path: Path, v3_selection_path: Path, output_dir: Path) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "responses").mkdir(parents=True, exist_ok=True)
    contract = json.loads(contract_path.read_text())
    rows = load_jsonl(roster_path)
    v3sel = json.loads(v3_selection_path.read_text())
    up = contract["frozen_upstream_evidence"]["official_club_roster_v2"]
    if sha256_file(roster_path) != up["roster_metadata_sha256"] or len(rows) != up["row_count"]:
        raise ValueError("roster source mismatch")
    v3up = contract["frozen_upstream_evidence"]["ngs_browser_heldout_v3"]
    if sha256_file(v3_selection_path) != v3up["target_selection_sha256"]:
        raise ValueError("V3 selection mismatch")
    targets, diag = select_targets(rows, contract, v3sel)
    (output_dir / "target_selection.json").write_text(json.dumps({"schema_version": "levline4-2026-ngs-player-id-browser-heldout-v4-target-selection", "contract_id": contract["contract_id"], "source_roster_metadata_sha256": sha256_file(roster_path), "v3_target_selection_sha256": sha256_file(v3_selection_path), "selection_diagnostics": diag, "targets": targets}, indent=2, sort_keys=True) + "\n")
    (output_dir / "contract.json").write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    page_loaded = False
    qcount = 0
    browser_error = None
    results = []
    bcfg = contract["browser_transport"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale=bcfg["context_locale"])
        page = context.new_page()
        locator = None
        try:
            page.goto(bcfg["page_url"], wait_until="domcontentloaded", timeout=bcfg["page_load_timeout_ms"])
            page.wait_for_timeout(1500)
            page_loaded = True
            locator = page.get_by_placeholder(bcfg["query_input_placeholder_exact"], exact=True)
            qcount = locator.count()
        except Exception as exc:
            browser_error = f"{type(exc).__name__}: {exc}"
        for idx, target in enumerate(targets, 1):
            attempts = []
            chosen = None
            action_error = browser_error
            if browser_error is None and locator is not None and qcount == 1:
                for attempt_idx, (kind, query) in enumerate(query_plan(clean(target["visible_name"])), 1):
                    if attempt_idx > 1:
                        prev = attempts[-1]
                        if not (prev["http_status"] == 200 and prev["parseable_players_array"] and prev["player_count"] == 0):
                            break
                    body = b""
                    status = None
                    url = None
                    ctype = None
                    err = None
                    try:
                        with page.expect_response(lambda r, q=query: matches_player_search_response(r.url, q), timeout=bcfg["response_timeout_ms"]) as info:
                            locator.fill(query)
                            locator.press("Enter")
                        resp = info.value
                        url = resp.url
                        status = int(resp.status)
                        ctype = str(resp.headers.get("content-type", ""))
                        body = resp.body()
                    except Exception as exc:
                        err = f"{type(exc).__name__}: {exc}"
                        action_error = err
                    rel = f"responses/target_{idx:03d}_attempt_{attempt_idx}.json"
                    (output_dir / rel).write_bytes(body)
                    parsed, ok, semantic = parse_players_body(status, body)
                    pc = len(parsed.get("players", [])) if ok and isinstance(parsed, dict) else 0
                    attempts.append({"attempt_index": attempt_idx, "query_kind": kind, "query": query, "response_url": url, "http_status": status, "content_type": ctype, "parseable_players_array": ok, "player_count": pc, "semantic_error": semantic, "browser_action_error": err, "response_relpath": rel, "response_bytes": len(body), "response_sha256": sha256_bytes(body)})
                    if err or not ok:
                        break
                    if pc > 0:
                        chosen = parsed
                        break
            resolution = resolve_target(target, chosen)
            results.append({"target_index": idx, "target_row_identity": list(row_identity(target)), "target_visible_name": clean(target["visible_name"]), "target_team": clean(target["team"]), "target_position": clean(target["position"]), "target_jersey_number": clean(target.get("jersey_number")), "target_profile_path": clean(target.get("profile_path")), "target_strata": target["_strata"], "selection_key_sha256": target["_selection_key_sha256"], "browser_action_error": action_error, "query_attempts": attempts, "fallback_used": len(attempts) > 1, **resolution})
        browser.close()
    with (output_dir / "target_results.jsonl").open("w") as h:
        for r in results:
            h.write(json.dumps(r, sort_keys=True) + "\n")
    metrics, gates, passed, conditional = evaluate_gates(targets, results, contract, page_loaded, qcount)
    if passed:
        authority = dict(contract["authority_if_and_only_if_all_v4_gates_pass"])
        authority["ari_az_team_alias_qualified_for_frozen_v4_population"] = conditional["ari_az_team_alias_qualified"]
        authority["query_fallback_semantics_qualified_for_frozen_v4_population"] = conditional["query_fallback_semantics_qualified"]
        authority["multiple_candidate_tiebreak_qualified_for_frozen_v4_population"] = conditional["multiple_candidate_tiebreak_qualified"]
    else:
        authority = dict(contract["authority_if_any_v4_gate_fails"])
    receipt = {"schema_version": "levline4-2026-ngs-player-id-browser-heldout-v4-receipt", "contract_id": contract["contract_id"], "captured_at_utc": utc_now(), "status": "PASS" if passed else "FAIL", "target_selection": diag, "browser_transport": {"page_loaded": page_loaded, "query_input_count": qcount, "browser_error": browser_error, "manual_headers_or_credentials_used": False, "browser_storage_state_persisted": False, "direct_http_fallback_used": False, "explicit_retry_used": False}, "metrics": metrics, "gates": gates, "conditional_capability_evidence": conditional, "authority": authority, "completed_2026_outcomes_used_for_design_or_selection": 0, "postgame_participation_used": False, "week2_inactive_execution_evidence_used_for_design": False, "f_st_01_frozen_2026_unchanged": True, "research_only": True, "production_paths_changed": False}
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True, type=Path)
    ap.add_argument("--roster-metadata", required=True, type=Path)
    ap.add_argument("--v3-target-selection", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    a = ap.parse_args()
    print(json.dumps(run_probe(a.contract, a.roster_metadata, a.v3_target_selection, a.output_dir), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
