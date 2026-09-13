from __future__ import annotations

"""Discovery-only inventory of first-party club media/press subdomains.

This module follows the standardized archive-surface V1 diagnostic. It probes only deterministic
child subdomains of each club's allowlisted historical domain, then inspects reachable first-party
WordPress/sitemap/root indexes for season-specific weekly-release/roster/depth candidate URLs.
Discovered URLs are candidate seeds only and have no locator, chronology, membership, or identity
authority.
"""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus, urljoin, urlparse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-MODERN-MEDIA-SUBDOMAIN-DISCOVERY-V2"
STATIC_CLUB_HOST = "static.clubs.nfl.com"


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def normalize_domain(value: str) -> str:
    return str(value or "").strip().lower().removeprefix("www.").rstrip(".")


def host_in_team_family(host: str | None, base_domain: str) -> bool:
    h = normalize_domain(host or "")
    base = normalize_domain(base_domain)
    return bool(h and base and (h == base or h.endswith("." + base)))


def candidate_target_allowed(url: str, base_domain: str) -> bool:
    parsed = urlparse(str(url or ""))
    if parsed.scheme.lower() != "https":
        return False
    host = (parsed.hostname or "").lower()
    return host == STATIC_CLUB_HOST or host_in_team_family(host, base_domain)


def signal_match(value: str, season: int, terms: list[str]) -> bool:
    normalized = normalize_text(value).replace("_", " ").replace("-", " ")
    if str(int(season)) not in normalized:
        return False
    return any(normalize_text(term) in normalized for term in terms)


def _response_record(url: str, response: Any, base_domain: str) -> dict[str, Any]:
    final_url = str(getattr(response, "url", url))
    parsed = urlparse(final_url)
    return {
        "requested_url": url,
        "final_url": final_url,
        "http_status": int(getattr(response, "status_code", 0) or 0),
        "content_type": str(getattr(response, "headers", {}).get("content-type", "")),
        "final_host": (parsed.hostname or "").lower(),
        "final_host_allowed": parsed.scheme.lower() == "https" and host_in_team_family(parsed.hostname, base_domain),
    }


def _get(url: str, *, timeout: float) -> Any:
    return requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-media-subdomain-discovery/2.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,application/json,*/*",
        },
    )


def extract_html_candidates(
    html: str,
    *,
    page_url: str,
    base_domain: str,
    seasons: list[int],
    terms: list[str],
) -> list[dict[str, Any]]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split())
        absolute = urljoin(page_url, str(anchor.get("href") or "").strip())
        if not candidate_target_allowed(absolute, base_domain):
            continue
        combined = f"{text} {absolute}"
        for season in seasons:
            if not signal_match(combined, season, terms):
                continue
            key = (int(season), absolute)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"season": int(season), "url": absolute, "label": text[:500], "discovery_method": "html_anchor"})
    return rows


def extract_xml_locs(raw: str) -> tuple[str, list[str]]:
    try:
        root = ET.fromstring(str(raw or ""))
    except ET.ParseError:
        return "invalid_xml", []
    tag = root.tag.split("}")[-1].lower()
    locs: list[str] = []
    for elem in root.iter():
        if elem.tag.split("}")[-1].lower() == "loc" and elem.text:
            locs.append(elem.text.strip())
    return tag, locs


def candidate_rows_from_urls(
    urls: list[str],
    *,
    base_domain: str,
    seasons: list[int],
    terms: list[str],
    method: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for url in urls:
        if not candidate_target_allowed(url, base_domain):
            continue
        for season in seasons:
            if not signal_match(url, season, terms):
                continue
            key = (int(season), url)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"season": int(season), "url": url, "label": "", "discovery_method": method})
    return rows


def _probe_subdomain(task: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    base_domain = normalize_domain(task["base_domain"])
    host = str(task["host"]).lower()
    root_url = f"https://{host}/"
    row: dict[str, Any] = {
        "team": str(task["team"]),
        "base_domain": base_domain,
        "prefix": str(task["prefix"]),
        "host": host,
        "root_url": root_url,
        "root_http_status": None,
        "root_final_url": None,
        "root_final_host_allowed": False,
        "root_error": None,
        "reachable_first_party_surface": False,
        "endpoint_results": [],
        "candidate_rows": [],
    }
    try:
        response = _get(root_url, timeout=timeout)
        rec = _response_record(root_url, response, base_domain)
        row["root_http_status"] = rec["http_status"]
        row["root_final_url"] = rec["final_url"]
        row["root_final_host_allowed"] = rec["final_host_allowed"]
        if not rec["final_host_allowed"]:
            row["root_error"] = f"redirect escaped team domain family: {rec['final_host']}"
            return row
        if rec["http_status"] >= 400:
            row["root_error"] = f"HTTP {rec['http_status']}"
            return row
        row["reachable_first_party_surface"] = True
        content_type = rec["content_type"].lower()
        if "html" in content_type or not content_type:
            row["candidate_rows"].extend(
                extract_html_candidates(
                    response.text,
                    page_url=rec["final_url"],
                    base_domain=base_domain,
                    seasons=list(task["seasons"]),
                    terms=list(task["terms"]),
                )
            )
    except Exception as exc:
        row["root_error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        return row

    # Probe bounded index surfaces only after the child subdomain itself is reachable.
    wp_json_reachable = False
    sitemap_children: list[str] = []
    for endpoint in task["index_endpoints"]:
        if endpoint == "/":
            continue
        url = f"https://{host}{endpoint}"
        endpoint_row: dict[str, Any] = {"endpoint": endpoint, "requested_url": url, "http_status": None, "final_url": None, "error": None}
        try:
            response = _get(url, timeout=timeout)
            rec = _response_record(url, response, base_domain)
            endpoint_row.update({"http_status": rec["http_status"], "final_url": rec["final_url"], "final_host_allowed": rec["final_host_allowed"], "content_type": rec["content_type"]})
            if not rec["final_host_allowed"]:
                endpoint_row["error"] = f"redirect escaped team domain family: {rec['final_host']}"
            elif rec["http_status"] >= 400:
                endpoint_row["error"] = f"HTTP {rec['http_status']}"
            else:
                if endpoint == "/wp-json/":
                    wp_json_reachable = True
                if "sitemap" in endpoint:
                    kind, locs = extract_xml_locs(response.text)
                    endpoint_row["xml_kind"] = kind
                    endpoint_row["loc_count"] = len(locs)
                    row["candidate_rows"].extend(
                        candidate_rows_from_urls(
                            locs,
                            base_domain=base_domain,
                            seasons=list(task["seasons"]),
                            terms=list(task["terms"]),
                            method=f"{endpoint}_url",
                        )
                    )
                    if kind == "sitemapindex":
                        sitemap_children.extend([u for u in locs if candidate_target_allowed(u, base_domain)][:40])
                else:
                    row["candidate_rows"].extend(
                        extract_html_candidates(
                            response.text,
                            page_url=rec["final_url"],
                            base_domain=base_domain,
                            seasons=list(task["seasons"]),
                            terms=list(task["terms"]),
                        )
                    )
        except Exception as exc:
            endpoint_row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        row["endpoint_results"].append(endpoint_row)

    # Inspect a bounded number of child sitemaps exposed by a first-party sitemap index.
    for child_url in list(dict.fromkeys(sitemap_children))[:40]:
        child_row: dict[str, Any] = {"endpoint": "child_sitemap", "requested_url": child_url, "http_status": None, "final_url": None, "error": None}
        try:
            response = _get(child_url, timeout=timeout)
            rec = _response_record(child_url, response, base_domain)
            child_row.update({"http_status": rec["http_status"], "final_url": rec["final_url"], "final_host_allowed": rec["final_host_allowed"], "content_type": rec["content_type"]})
            if not rec["final_host_allowed"]:
                child_row["error"] = f"redirect escaped team domain family: {rec['final_host']}"
            elif rec["http_status"] >= 400:
                child_row["error"] = f"HTTP {rec['http_status']}"
            else:
                kind, locs = extract_xml_locs(response.text)
                child_row["xml_kind"] = kind
                child_row["loc_count"] = len(locs)
                row["candidate_rows"].extend(
                    candidate_rows_from_urls(
                        locs,
                        base_domain=base_domain,
                        seasons=list(task["seasons"]),
                        terms=list(task["terms"]),
                        method="child_sitemap_url",
                    )
                )
        except Exception as exc:
            child_row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        row["endpoint_results"].append(child_row)

    # WordPress search is used only when the subdomain explicitly exposes wp-json.
    if wp_json_reachable:
        for season in task["seasons"]:
            for query in task["wordpress_search_queries"]:
                search_term = f"{season} {query}"
                url = f"https://{host}/wp-json/wp/v2/search?search={quote_plus(search_term)}&per_page=100"
                search_row: dict[str, Any] = {"endpoint": "wp_search", "season": int(season), "query": query, "requested_url": url, "http_status": None, "error": None, "result_count": 0}
                try:
                    response = _get(url, timeout=timeout)
                    rec = _response_record(url, response, base_domain)
                    search_row.update({"http_status": rec["http_status"], "final_url": rec["final_url"], "final_host_allowed": rec["final_host_allowed"]})
                    if not rec["final_host_allowed"]:
                        search_row["error"] = f"redirect escaped team domain family: {rec['final_host']}"
                    elif rec["http_status"] >= 400:
                        search_row["error"] = f"HTTP {rec['http_status']}"
                    else:
                        payload = response.json()
                        if not isinstance(payload, list):
                            raise ValueError("WordPress search response is not a list")
                        search_row["result_count"] = len(payload)
                        for item in payload[:100]:
                            candidate_url = str(item.get("url") or "")
                            title = str(item.get("title") or "")
                            if not candidate_target_allowed(candidate_url, base_domain):
                                continue
                            combined = f"{season} {query} {title} {candidate_url}"
                            if not signal_match(combined, int(season), list(task["terms"])):
                                continue
                            row["candidate_rows"].append({"season": int(season), "url": candidate_url, "label": title[:500], "discovery_method": "wp_search"})
                except Exception as exc:
                    search_row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
                row["endpoint_results"].append(search_row)

    # Deterministic de-duplication.
    dedup: dict[tuple[int, str], dict[str, Any]] = {}
    for candidate in row["candidate_rows"]:
        key = (int(candidate["season"]), str(candidate["url"]))
        dedup.setdefault(key, candidate)
    row["candidate_rows"] = sorted(dedup.values(), key=lambda x: (int(x["season"]), str(x["url"])))
    return row


def unresolved_pairs(contract: dict[str, Any]) -> list[tuple[str, int]]:
    already = set(str(x) for x in contract["already_discovered_team_seasons"])
    pairs: list[tuple[str, int]] = []
    for team in sorted(contract["teams"]):
        for season in contract["seasons"]:
            key = f"{team}|{int(season)}"
            if key not in already:
                pairs.append((team, int(season)))
    return pairs


def build_subdomain_tasks(contract: dict[str, Any]) -> list[dict[str, Any]]:
    needed_by_team: dict[str, list[int]] = {}
    for team, season in unresolved_pairs(contract):
        needed_by_team.setdefault(team, []).append(int(season))
    tasks: list[dict[str, Any]] = []
    for team, seasons in sorted(needed_by_team.items()):
        for base_domain in contract["teams"][team]:
            base = normalize_domain(base_domain)
            for prefix in contract["candidate_subdomain_prefixes"]:
                tasks.append(
                    {
                        "team": team,
                        "seasons": sorted(seasons),
                        "base_domain": base,
                        "prefix": str(prefix),
                        "host": f"{prefix}.{base}",
                        "index_endpoints": list(contract["index_endpoints"]),
                        "wordpress_search_queries": list(contract["wordpress_search_queries"]),
                        "terms": list(contract["candidate_signal_terms"]),
                    }
                )
    return tasks


def run_discovery(contract_path: Path, *, timeout: float, workers: int) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    pairs = unresolved_pairs(contract)
    expected_pairs = int(contract["required_accounting"]["unresolved_team_season_pairs"])
    if len(pairs) != expected_pairs:
        raise ValueError(f"unresolved pair contract mismatch: {len(pairs)} != {expected_pairs}")
    tasks = build_subdomain_tasks(contract)
    subdomains: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        future_map = {pool.submit(_probe_subdomain, task, timeout=timeout): task for task in tasks}
        for future in as_completed(future_map):
            subdomains.append(future.result())
    subdomains.sort(key=lambda x: (x["team"], x["base_domain"], x["prefix"]))

    pair_rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for team, season in pairs:
        candidates: list[dict[str, Any]] = []
        reachable_hosts: list[str] = []
        for row in subdomains:
            if row["team"] != team:
                continue
            if row["reachable_first_party_surface"]:
                reachable_hosts.append(str(row["host"]))
            candidates.extend([c for c in row["candidate_rows"] if int(c["season"]) == int(season)])
        dedup: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            dedup.setdefault(str(candidate["url"]), candidate)
        selected = sorted(dedup.values(), key=lambda x: str(x["url"]))
        pair = {
            "team": team,
            "season": int(season),
            "reachable_first_party_media_hosts": sorted(set(reachable_hosts)),
            "candidate_url_count": len(selected),
            "candidate_examples": selected[: int(contract["required_accounting"]["bounded_candidate_examples_per_pair"])],
            "media_subdomain_candidate_discovered": bool(selected),
        }
        pair_rows.append(pair)
        if not selected:
            missing.append(f"{team}|{season}")

    hit_count = sum(1 for row in pair_rows if row["media_subdomain_candidate_discovered"])
    accounting_pass = bool(
        len(pair_rows) == expected_pairs
        and len({(row["team"], row["season"]) for row in pair_rows}) == expected_pairs
        and len(subdomains) == len(tasks)
    )
    return {
        "discovery_version": 2,
        "contract_id": CONTRACT_ID,
        "expected_unresolved_team_season_pairs": expected_pairs,
        "unresolved_team_season_pairs_reported": len(pair_rows),
        "derived_subdomain_probes_expected": len(tasks),
        "derived_subdomain_probes_reported": len(subdomains),
        "reachable_first_party_media_subdomains": sum(1 for row in subdomains if row["reachable_first_party_surface"]),
        "team_season_pairs_with_candidate_urls": hit_count,
        "team_season_pairs_without_candidate_urls": len(missing),
        "candidate_discovery_fraction_diagnostic_only": hit_count / expected_pairs if expected_pairs else 0.0,
        "missing_team_season_pairs": missing,
        "discovery_accounting_integrity_pass": accounting_pass,
        "team_season_results": pair_rows,
        "subdomain_results": subdomains,
        "diagnostic_has_locator_qualification_authority": False,
        "diagnostic_has_membership_authority": False,
        "modern_roster_depth_locator_coverage_qualified": False,
        "all_2592_team_game_partitions_tested": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "weekly_roster_membership_used": False,
        "weekly_roster_status_used": False,
        "postgame_participation_used_as_training_authority": False,
        "absence_from_inactive_used_as_positive": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_discovery(args.contract, timeout=args.timeout, workers=args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"team_season_results", "subdomain_results"}}, indent=2, sort_keys=True))
    if result["discovery_accounting_integrity_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
