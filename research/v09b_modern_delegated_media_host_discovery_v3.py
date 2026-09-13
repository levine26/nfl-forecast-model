from __future__ import annotations

"""Diagnostic-only audit of three observed official-club -> delegated media-host relationships."""

import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-MODERN-DELEGATED-MEDIA-HOST-DISCOVERY-V3"


def norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().upper()


def exact_https_host(url: str, host: str) -> bool:
    p = urlparse(str(url or ""))
    return p.scheme.lower() == "https" and (p.hostname or "").lower() == str(host).lower()


def signal_match(value: str, season: int, terms: list[str]) -> bool:
    n = norm(value).replace("-", " ").replace("_", " ")
    return str(int(season)) in n and any(norm(t) in n for t in terms)


def xml_locs(raw: str) -> tuple[str, list[str]]:
    try:
        root = ET.fromstring(str(raw or ""))
    except ET.ParseError:
        return "invalid_xml", []
    kind = root.tag.split("}")[-1].lower()
    urls = []
    for elem in root.iter():
        if elem.tag.split("}")[-1].lower() == "loc" and elem.text:
            urls.append(elem.text.strip())
    return kind, urls


def response_redirect_chain(response: Any) -> list[dict[str, Any]]:
    chain = []
    for item in list(getattr(response, "history", []) or []) + [response]:
        chain.append(
            {
                "status": int(getattr(item, "status_code", 0) or 0),
                "url": str(getattr(item, "url", "")),
                "host": (urlparse(str(getattr(item, "url", ""))).hostname or "").lower(),
            }
        )
    return chain


def get(url: str, timeout: float) -> Any:
    return requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-delegated-media-discovery/3.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml,text/xml,application/json,*/*",
        },
    )


def extract_html_candidates(html: str, *, page_url: str, delegated_host: str, seasons: list[int], terms: list[str]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    found: dict[tuple[int, str], dict[str, Any]] = {}
    for a in soup.find_all("a", href=True):
        label = " ".join(a.get_text(" ", strip=True).split())
        url = urljoin(page_url, str(a.get("href") or ""))
        if not exact_https_host(url, delegated_host):
            continue
        for season in seasons:
            if signal_match(f"{label} {url}", season, terms):
                found.setdefault((season, url), {"season": season, "url": url, "label": label[:500], "method": "html_anchor"})
    return sorted(found.values(), key=lambda x: (x["season"], x["url"]))


def candidates_from_urls(urls: list[str], *, delegated_host: str, seasons: list[int], terms: list[str], method: str) -> list[dict[str, Any]]:
    found: dict[tuple[int, str], dict[str, Any]] = {}
    for url in urls:
        if not exact_https_host(url, delegated_host):
            continue
        for season in seasons:
            if signal_match(url, season, terms):
                found.setdefault((season, url), {"season": season, "url": url, "label": "", "method": method})
    return sorted(found.values(), key=lambda x: (x["season"], x["url"]))


def probe_delegation(item: dict[str, Any], contract: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    origin = str(item["official_origin_url"])
    expected_host = str(item["expected_delegated_host"]).lower()
    result: dict[str, Any] = {
        "team": item["team"],
        "team_name": item["team_name"],
        "official_origin_url": origin,
        "expected_delegated_host": expected_host,
        "delegation_kind": item["delegation_kind"],
        "origin_fetch_error": None,
        "origin_http_status": None,
        "redirect_chain": [],
        "delegation_exact_terminal_host_pass": False,
        "delegated_root_attribution_signals_found": [],
        "endpoint_results": [],
        "candidate_rows": [],
    }
    try:
        response = get(origin, timeout)
        result["origin_http_status"] = int(response.status_code)
        result["redirect_chain"] = response_redirect_chain(response)
        result["delegation_exact_terminal_host_pass"] = bool(response.status_code < 400 and exact_https_host(str(response.url), expected_host))
    except Exception as exc:
        result["origin_fetch_error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        return result

    if not result["delegation_exact_terminal_host_pass"]:
        return result

    seasons = [int(x) for x in item["seasons"]]
    terms = list(contract["candidate_signal_terms"])
    attribution = [norm(x) for x in contract["attribution_signals"][item["team"]]]
    root_url = f"https://{expected_host}/"
    wp_json_ok = False
    child_sitemaps: list[str] = []
    candidates: list[dict[str, Any]] = []

    endpoints = list(contract["delegated_host_probe_endpoints"])
    for endpoint in endpoints:
        url = root_url if endpoint == "/" else f"https://{expected_host}{endpoint}"
        row: dict[str, Any] = {"endpoint": endpoint, "requested_url": url, "http_status": None, "final_url": None, "final_host_exact": False, "error": None}
        try:
            response = get(url, timeout)
            row["http_status"] = int(response.status_code)
            row["final_url"] = str(response.url)
            row["final_host_exact"] = exact_https_host(str(response.url), expected_host)
            row["content_type"] = str(response.headers.get("content-type", ""))
            if response.status_code >= 400:
                row["error"] = f"HTTP {response.status_code}"
            elif not row["final_host_exact"]:
                row["error"] = f"redirect escaped delegated host to {(urlparse(str(response.url)).hostname or '').lower()}"
            else:
                text = response.text
                if endpoint == "/":
                    page_norm = norm(BeautifulSoup(text, "html.parser").get_text(" ", strip=True))
                    result["delegated_root_attribution_signals_found"] = [sig for sig in attribution if sig in page_norm]
                    candidates.extend(extract_html_candidates(text, page_url=str(response.url), delegated_host=expected_host, seasons=seasons, terms=terms))
                elif endpoint == "/wp-json/":
                    wp_json_ok = True
                elif "sitemap" in endpoint:
                    kind, locs = xml_locs(text)
                    row["xml_kind"] = kind
                    row["loc_count"] = len(locs)
                    candidates.extend(candidates_from_urls(locs, delegated_host=expected_host, seasons=seasons, terms=terms, method=f"{endpoint}_url"))
                    if kind == "sitemapindex":
                        child_sitemaps.extend([u for u in locs if exact_https_host(u, expected_host)])
                else:
                    candidates.extend(extract_html_candidates(text, page_url=str(response.url), delegated_host=expected_host, seasons=seasons, terms=terms))
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        result["endpoint_results"].append(row)

    max_children = int(contract["discovery_logic"]["bounded_child_sitemaps_max"])
    for url in list(dict.fromkeys(child_sitemaps))[:max_children]:
        row = {"endpoint": "child_sitemap", "requested_url": url, "http_status": None, "final_url": None, "final_host_exact": False, "error": None}
        try:
            response = get(url, timeout)
            row["http_status"] = int(response.status_code)
            row["final_url"] = str(response.url)
            row["final_host_exact"] = exact_https_host(str(response.url), expected_host)
            if response.status_code >= 400:
                row["error"] = f"HTTP {response.status_code}"
            elif not row["final_host_exact"]:
                row["error"] = "child sitemap escaped delegated host"
            else:
                kind, locs = xml_locs(response.text)
                row["xml_kind"] = kind
                row["loc_count"] = len(locs)
                candidates.extend(candidates_from_urls(locs, delegated_host=expected_host, seasons=seasons, terms=terms, method="child_sitemap_url"))
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        result["endpoint_results"].append(row)

    if wp_json_ok:
        for season in seasons:
            for query in contract["wordpress_search_queries"]:
                url = f"https://{expected_host}/wp-json/wp/v2/search?search={quote_plus(str(season) + ' ' + query)}&per_page=100"
                row = {"endpoint": "wp_search", "season": season, "query": query, "requested_url": url, "http_status": None, "error": None, "result_count": 0}
                try:
                    response = get(url, timeout)
                    row["http_status"] = int(response.status_code)
                    if response.status_code >= 400 or not exact_https_host(str(response.url), expected_host):
                        row["error"] = f"HTTP/host failure: {response.status_code} {response.url}"
                    else:
                        payload = response.json()
                        if not isinstance(payload, list):
                            raise ValueError("WordPress search payload is not a list")
                        row["result_count"] = len(payload)
                        for hit in payload[:100]:
                            u = str(hit.get("url") or "")
                            title = str(hit.get("title") or "")
                            # Do not manufacture the signal from the query itself: candidate text/url must carry it.
                            if exact_https_host(u, expected_host) and signal_match(f"{title} {u}", season, terms):
                                candidates.append({"season": season, "url": u, "label": title[:500], "method": "wp_search"})
                except Exception as exc:
                    row["error"] = f"{type(exc).__name__}: {str(exc)[:500]}"
                result["endpoint_results"].append(row)

    dedup: dict[tuple[int, str], dict[str, Any]] = {}
    for c in candidates:
        dedup.setdefault((int(c["season"]), str(c["url"])), c)
    result["candidate_rows"] = sorted(dedup.values(), key=lambda x: (int(x["season"]), str(x["url"])))
    return result


def run(contract_path: Path, *, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    items = list(contract["fixed_delegations"])
    rows = [probe_delegation(item, contract, timeout=timeout) for item in items]
    pair_rows = []
    bound = int(contract["required_accounting"]["bounded_candidate_examples_per_pair"])
    for row in rows:
        by_season = {int(s): [] for s in next(x for x in items if x["team"] == row["team"])["seasons"]}
        for candidate in row["candidate_rows"]:
            by_season[int(candidate["season"])].append(candidate)
        for season, candidates in sorted(by_season.items()):
            pair_rows.append({
                "team": row["team"],
                "season": season,
                "delegation_provenance_pass": row["delegation_exact_terminal_host_pass"],
                "candidate_count": len(candidates),
                "candidate_examples": candidates[:bound],
            })
    accounting = len(rows) == 3 and len(pair_rows) == 15 and len({(x["team"], x["season"]) for x in pair_rows}) == 15
    return {
        "diagnostic_version": 3,
        "contract_id": CONTRACT_ID,
        "delegations_expected": 3,
        "delegations_reported": len(rows),
        "delegations_with_exact_terminal_host": sum(1 for x in rows if x["delegation_exact_terminal_host_pass"]),
        "team_season_pairs_expected": 15,
        "team_season_pairs_reported": len(pair_rows),
        "team_season_pairs_with_candidate_urls": sum(1 for x in pair_rows if x["candidate_count"] > 0),
        "accounting_integrity_pass": accounting,
        "delegation_results": rows,
        "team_season_results": pair_rows,
        "diagnostic_has_source_qualification_authority": False,
        "diagnostic_has_locator_qualification_authority": False,
        "diagnostic_has_membership_authority": False,
        "delegated_host_is_first_party_authority": False,
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
    p = argparse.ArgumentParser()
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=12.0)
    args = p.parse_args(list(argv) if argv is not None else None)
    result = run(args.contract, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k not in {"delegation_results", "team_season_results"}}, indent=2, sort_keys=True))
    if not result["accounting_integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
