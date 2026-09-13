from __future__ import annotations

"""Research-only source-class probe for the official NFL transaction ledger.

The module verifies first-party source/pagination semantics only. It does not apply any
transaction to a roster state and has no chronology, membership, label, or model authority.
"""

import argparse
import hashlib
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

CONTRACT_ID = "V09B-NFL-TRANSACTION-LEDGER-SOURCE-PROBE-V1"
DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}$")
EXPECTED_HEADER = ["FROM", "TO", "DATE", "NAME", "POSITION", "TRANSACTION"]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_text(value: str) -> str:
    return " ".join(str(value or "").split())


def canonical_url(url: str) -> str:
    parsed = urlparse(str(url))
    path = parsed.path.rstrip("/") or "/"
    query = parsed.query
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", query, ""))


def validate_url(url: str, *, allowed_hosts: set[str]) -> None:
    parsed = urlparse(str(url))
    if parsed.scheme.lower() != "https":
        raise ValueError("transaction source URL must use https")
    host = (parsed.hostname or "").lower()
    if host not in allowed_hosts:
        raise ValueError(f"transaction source host not allowlisted: {host}")


def endpoint_path(season: int, month: int, category: str) -> str:
    return f"/transactions/league/{category}/{season}/{month}"


def validate_endpoint_identity(url: str, *, season: int, month: int, category: str, allowed_hosts: set[str]) -> None:
    validate_url(url, allowed_hosts=allowed_hosts)
    parsed = urlparse(url)
    if parsed.path.rstrip("/") != endpoint_path(season, month, category):
        raise ValueError(f"pagination escaped endpoint identity: {url}")
    query = parse_qs(parsed.query, keep_blank_values=True)
    unexpected = sorted(set(query) - {"after"})
    if unexpected:
        raise ValueError(f"unexpected transaction pagination query keys: {unexpected}")


def fetch_page(session: Any, url: str, *, timeout: float, allowed_hosts: set[str]) -> tuple[bytes, str, str]:
    validate_url(url, allowed_hosts=allowed_hosts)
    response = session.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-transaction-ledger-probe/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    response.raise_for_status()
    final_url = str(response.url)
    validate_url(final_url, allowed_hosts=allowed_hosts)
    raw = response.content
    return raw, final_url, str(response.headers.get("content-type", ""))


def _cell_text(cell: Any) -> str:
    # NFL team cells can contain an icon/alt label plus visible label. Preserve source text,
    # but collapse whitespace so exact HTML layout cannot affect the audit.
    return normalize_text(cell.get_text(" ", strip=True))


def parse_transaction_rows(html: str) -> tuple[list[dict[str, str]], bool]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, str]] = []
    required_header_seen = False

    for table in soup.find_all("table"):
        headers = [_cell_text(x).upper() for x in table.find_all("th")]
        if headers[:6] == EXPECTED_HEADER or all(item in headers for item in EXPECTED_HEADER):
            required_header_seen = True
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 6:
                continue
            values = [_cell_text(cell) for cell in cells[:6]]
            if not DATE_RE.fullmatch(values[2]):
                continue
            rows.append(
                {
                    "from": values[0],
                    "to": values[1],
                    "date": values[2],
                    "name": values[3],
                    "position": values[4],
                    "transaction": values[5],
                }
            )

    # Some NFL templates omit explicit <th> markup but still render the transaction rows.
    # A parsed row is acceptable evidence of the six-column semantic layout; the boolean is
    # retained diagnostically so later work can see whether headers were literal.
    return rows, required_header_seen


def page_identity_markers(html: str, *, season: int, month: int, category: str) -> dict[str, bool]:
    text = normalize_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True)).casefold()
    category_label = category.replace("-", " ").casefold()
    month_names = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
    ]
    return {
        "season_marker": f"{season} nfl transactions" in text,
        "category_marker": category_label in text,
        "month_marker": month_names[month - 1] in text,
    }


def discover_pagination_links(
    html: str,
    *,
    base_url: str,
    season: int,
    month: int,
    category: str,
    allowed_hosts: set[str],
) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        absolute = urljoin(base_url, str(anchor.get("href") or ""))
        try:
            validate_endpoint_identity(
                absolute,
                season=season,
                month=month,
                category=category,
                allowed_hosts=allowed_hosts,
            )
        except ValueError:
            continue
        query = parse_qs(urlparse(absolute).query, keep_blank_values=True)
        if "after" not in query:
            continue
        found.add(canonical_url(absolute))
    return sorted(found)


def row_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row.get(key, "") for key in ("from", "to", "date", "name", "position", "transaction"))


def probe_endpoint(
    *,
    season: int,
    month: int,
    category: str,
    url_template: str,
    allowed_hosts: set[str],
    maximum_pages: int,
    timeout: float,
    session: Any = requests,
) -> dict[str, Any]:
    initial_url = url_template.format(category=category, season=season, month=month)
    validate_endpoint_identity(
        initial_url,
        season=season,
        month=month,
        category=category,
        allowed_hosts=allowed_hosts,
    )

    pending: deque[str] = deque([canonical_url(initial_url)])
    visited: set[str] = set()
    source_pages: list[dict[str, Any]] = []
    all_rows: list[dict[str, str]] = []
    exact_row_keys: set[tuple[str, ...]] = set()
    duplicate_rows = 0
    initial_markers: dict[str, bool] | None = None

    while pending:
        if len(visited) >= maximum_pages:
            raise RuntimeError(f"pagination exceeded maximum_pages={maximum_pages}")
        requested_url = pending.popleft()
        if requested_url in visited:
            continue
        raw, final_url, content_type = fetch_page(
            session,
            requested_url,
            timeout=timeout,
            allowed_hosts=allowed_hosts,
        )
        validate_endpoint_identity(
            final_url,
            season=season,
            month=month,
            category=category,
            allowed_hosts=allowed_hosts,
        )
        final_canonical = canonical_url(final_url)
        if final_canonical in visited:
            continue
        visited.add(final_canonical)
        html = raw.decode("utf-8", errors="replace")
        rows, literal_header = parse_transaction_rows(html)
        markers = page_identity_markers(html, season=season, month=month, category=category)
        if initial_markers is None:
            initial_markers = markers
        next_links = discover_pagination_links(
            html,
            base_url=final_url,
            season=season,
            month=month,
            category=category,
            allowed_hosts=allowed_hosts,
        )
        for link in next_links:
            if link not in visited:
                pending.append(link)

        for row in rows:
            key = row_key(row)
            if key in exact_row_keys:
                duplicate_rows += 1
            else:
                exact_row_keys.add(key)
                all_rows.append(row)

        source_pages.append(
            {
                "requested_url": requested_url,
                "final_url": final_url,
                "content_type": content_type,
                "raw_bytes": len(raw),
                "raw_sha256": sha256_bytes(raw),
                "literal_required_header_seen": literal_header,
                "rows_parsed": len(rows),
                "pagination_links_discovered": len(next_links),
            }
        )

    return {
        "season": season,
        "month": month,
        "category": category,
        "initial_url": initial_url,
        "pages_fetched": len(source_pages),
        "source_pages": source_pages,
        "initial_identity_markers": initial_markers or {},
        "unique_rows_parsed": len(all_rows),
        "duplicate_rows_across_pages": duplicate_rows,
        "rows": all_rows,
        "pagination_converged": True,
    }


def evidence_found(rows: list[dict[str, str]], evidence: dict[str, Any]) -> bool:
    expected_name = normalize_text(str(evidence["name"])).casefold()
    transaction_fragment = normalize_text(str(evidence["transaction_contains"])).casefold()
    return any(
        normalize_text(row.get("name", "")).casefold() == expected_name
        and transaction_fragment in normalize_text(row.get("transaction", "")).casefold()
        for row in rows
    )


def run_probe(contract_path: Path, *, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")

    fixed = contract["fixed_cross_era_probe"]
    seasons = [int(x) for x in fixed["seasons"]]
    month = int(fixed["month"])
    categories = [str(x) for x in fixed["categories"]]
    url_template = str(fixed["url_template"])
    allowed_hosts = {str(x).lower() for x in contract["source_requirements"]["allowed_hosts"]}
    maximum_pages = int(contract["source_requirements"]["maximum_pages_per_endpoint"])

    endpoints: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for season in seasons:
        for category in categories:
            try:
                endpoints.append(
                    probe_endpoint(
                        season=season,
                        month=month,
                        category=category,
                        url_template=url_template,
                        allowed_hosts=allowed_hosts,
                        maximum_pages=maximum_pages,
                        timeout=timeout,
                    )
                )
            except Exception as exc:
                errors.append(
                    {
                        "season": str(season),
                        "month": str(month),
                        "category": category,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

    by_key = {(x["season"], x["category"]): x for x in endpoints}
    season_row_totals = {
        str(season): sum(by_key.get((season, cat), {}).get("unique_rows_parsed", 0) for cat in categories)
        for season in seasons
    }
    category_row_totals = {
        cat: sum(by_key.get((season, cat), {}).get("unique_rows_parsed", 0) for season in seasons)
        for cat in categories
    }

    evidence_results: list[dict[str, Any]] = []
    for item in contract["known_semantic_evidence"]:
        key = (int(item["season"]), str(item["category"]))
        endpoint = by_key.get(key)
        found = bool(endpoint and evidence_found(endpoint["rows"], item))
        evidence_results.append({**item, "found": found})

    initial_endpoint_count = len(seasons) * len(categories)
    all_initial_markers = all(
        all(bool(endpoint["initial_identity_markers"].get(k)) for k in ("season_marker", "category_marker", "month_marker"))
        for endpoint in endpoints
    ) if endpoints else False
    all_page_hashes = all(
        len(str(page.get("raw_sha256", ""))) == 64
        for endpoint in endpoints
        for page in endpoint["source_pages"]
    )
    gate_pass = bool(
        not errors
        and len(endpoints) == initial_endpoint_count
        and all_initial_markers
        and all(endpoint["pagination_converged"] for endpoint in endpoints)
        and all_page_hashes
        and all(value > 0 for value in season_row_totals.values())
        and all(value > 0 for value in category_row_totals.values())
        and all(item["found"] for item in evidence_results)
    )

    compact_endpoints = []
    for endpoint in endpoints:
        compact_endpoints.append(
            {
                "season": endpoint["season"],
                "month": endpoint["month"],
                "category": endpoint["category"],
                "initial_url": endpoint["initial_url"],
                "pages_fetched": endpoint["pages_fetched"],
                "unique_rows_parsed": endpoint["unique_rows_parsed"],
                "duplicate_rows_across_pages": endpoint["duplicate_rows_across_pages"],
                "initial_identity_markers": endpoint["initial_identity_markers"],
                "page_hashes": [
                    {
                        "final_url": page["final_url"],
                        "raw_sha256": page["raw_sha256"],
                        "raw_bytes": page["raw_bytes"],
                        "rows_parsed": page["rows_parsed"],
                    }
                    for page in endpoint["source_pages"]
                ],
            }
        )

    return {
        "probe_version": 1,
        "contract_id": CONTRACT_ID,
        "initial_endpoint_count_expected": initial_endpoint_count,
        "initial_endpoint_count_completed": len(endpoints),
        "source_errors": errors,
        "season_row_totals": season_row_totals,
        "category_row_totals": category_row_totals,
        "known_semantic_evidence": evidence_results,
        "endpoints": compact_endpoints,
        "source_class_semantic_viability_probe_pass": gate_pass,
        "full_2017_2021_all_month_ledger_captured": False,
        "transaction_state_machine_defined": False,
        "same_day_transaction_order_resolved": False,
        "week_specific_roster_snapshot_coverage_proven": False,
        "game_day_roster_membership_constructed": False,
        "inactive_lists_reconciled": False,
        "probe_has_chronology_authority": False,
        "probe_has_membership_authority": False,
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
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_probe(args.contract, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "endpoints"}, indent=2, sort_keys=True))
    if result["source_class_semantic_viability_probe_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
