from __future__ import annotations

"""Full 2017-2021 NFL transaction ledger capture using only V7-qualified empty semantics."""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, quote, urlparse

import requests
from bs4 import BeautifulSoup

from research.v09b_nfl_transaction_ledger_source_probe_v1 import parse_transaction_rows
from research.v09b_nfl_transaction_no_header_source_shape_v6 import _title_and_headings

CONTRACT_ID = "V09B-NFL-TRANSACTION-FULL-LEDGER-CAPTURE-V8"
ROW_FIELDS = ("from", "to", "date", "name", "position", "transaction")
SAFE_COMPONENT = re.compile(r"^[a-z0-9-]+$")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _row_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(k, "")) for k in ROW_FIELDS)


def _endpoint_url(contract: dict[str, Any], *, year: int, month: int, category: str) -> str:
    if not SAFE_COMPONENT.fullmatch(category):
        raise ValueError(f"unsafe category: {category}")
    return str(contract["scope"]["url_template"]).format(
        category=category,
        year=int(year),
        month=int(month),
    )


def _amp_cursor_url(endpoint_url: str, cursor: str) -> str:
    p = urlparse(endpoint_url)
    return f"https://amp.nfl.com{p.path}?after={quote(str(cursor), safe='')}"


def _validate_final(requested_url: str, final_url: str, allowed_hosts: set[str]) -> None:
    req = urlparse(requested_url)
    final = urlparse(final_url)
    if final.scheme.lower() != "https":
        raise ValueError(f"non-https final URL: {final_url}")
    if (final.hostname or "").lower() not in allowed_hosts:
        raise ValueError(f"unexpected final host: {final_url}")
    if final.path.rstrip("/") != req.path.rstrip("/"):
        raise ValueError(f"transaction path changed: requested={requested_url} final={final_url}")


def _distinct_after_values(html: str, base_url: str, requested_url: str) -> list[str]:
    from urllib.parse import urljoin

    soup = BeautifulSoup(str(html or ""), "html.parser")
    expected_path = urlparse(requested_url).path
    current_values = parse_qs(urlparse(requested_url).query, keep_blank_values=True).get("after", [])
    current = current_values[0] if current_values else None
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(base_url, str(a.get("href") or ""))
        p = urlparse(absolute)
        if p.scheme.lower() != "https" or p.path.rstrip("/") != expected_path.rstrip("/"):
            continue
        for value in parse_qs(p.query, keep_blank_values=True).get("after", []):
            if value and value != current and value not in found:
                found.append(value)
    return found


def _write_raw(raw: bytes, path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    path.write_bytes(packed)
    restored = gzip.decompress(path.read_bytes())
    if restored != raw:
        raise RuntimeError(f"gzip round-trip mismatch: {path}")
    return {
        "raw_relpath": path.as_posix(),
        "raw_bytes": len(raw),
        "raw_sha256": _sha(raw),
        "gzip_bytes": len(packed),
        "gzip_roundtrip_matches": True,
    }


def _qualified_empty_shape(
    *,
    headings: list[str],
    header: bool,
    rows: list[dict[str, str]],
    table_count: int,
    distinct_after_values: list[str],
    contract: dict[str, Any],
) -> bool:
    rule = contract["qualified_explicit_empty_rule"]
    return bool(
        str(rule["exact_heading"]) in headings
        and bool(header) is bool(rule["standard_transaction_header_seen"])
        and len(rows) == int(rule["standard_transaction_row_count"])
        and int(table_count) == int(rule["html_table_count"])
        and len(distinct_after_values) == int(rule["distinct_forward_after_cursor_count"])
    )


def _get(url: str, *, timeout: float) -> requests.Response:
    response = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-full-transaction-capture/8.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    return response


def _expected_empty_urls(v6_contract: dict[str, Any], year: int | None = None) -> set[str]:
    rows = list(v6_contract["scope"]["fixed_requests"])
    if year is not None:
        rows = [x for x in rows if int(x["year"]) == int(year)]
    return {str(x["requested_url"]) for x in rows}


def crawl_endpoint(
    contract: dict[str, Any],
    *,
    year: int,
    month: int,
    category: str,
    timeout: float,
    output_root: Path,
) -> dict[str, Any]:
    endpoint_url = _endpoint_url(contract, year=year, month=month, category=category)
    allowed_hosts = set(contract["transport_and_pagination"]["allowed_final_hosts"])
    max_pages = int(contract["scope"]["maximum_pages_per_endpoint"])
    seen_page_urls: set[str] = set()
    seen_transaction_shas: set[str] = set()
    all_row_keys: set[tuple[str, ...]] = set()
    pages: list[dict[str, Any]] = []
    current_url = endpoint_url
    converged = False
    error: str | None = None

    try:
        for page_index in range(max_pages):
            if current_url in seen_page_urls:
                raise RuntimeError(f"page URL cycle: {current_url}")

            response = _get(current_url, timeout=timeout)
            try:
                raw = bytes(response.content)
                rel = Path("raw") / str(year) / f"{month:02d}" / category / f"page_{page_index:03d}.html.gz"
                stored = _write_raw(raw, output_root / rel)
                record: dict[str, Any] = {
                    "page_index": page_index,
                    "requested_url": current_url,
                    "final_url": str(response.url),
                    "status_code": int(response.status_code),
                    **stored,
                }
                pages.append(record)

                response.raise_for_status()
                _validate_final(current_url, str(response.url), allowed_hosts)
                html = raw.decode("utf-8", errors="replace")
                rows, header = parse_transaction_rows(html)
                _, headings = _title_and_headings(html)
                table_count = len(BeautifulSoup(html, "html.parser").find_all("table"))
                distinct_after = _distinct_after_values(html, str(response.url), current_url)
                if len(distinct_after) > 1:
                    raise RuntimeError(f"multiple distinct forward after cursors found: {len(distinct_after)}")

                row_keys = {_row_key(row) for row in rows}
                novel_keys = row_keys - all_row_keys
                overlap_keys = row_keys & all_row_keys
                explicit_empty = _qualified_empty_shape(
                    headings=headings,
                    header=bool(header),
                    rows=rows,
                    table_count=table_count,
                    distinct_after_values=distinct_after,
                    contract=contract,
                )
                record.update(
                    {
                        "headings": headings,
                        "table_count": table_count,
                        "standard_transaction_header_seen": bool(header),
                        "rows": rows,
                        "transaction_row_count": len(rows),
                        "novel_rows_vs_prior_union": len(novel_keys),
                        "overlap_rows_vs_prior_union": len(overlap_keys),
                        "distinct_forward_after_cursor_count": len(distinct_after),
                        "distinct_forward_after_cursor": distinct_after[0] if distinct_after else None,
                        "qualified_explicit_empty_shape": explicit_empty,
                    }
                )

                if explicit_empty:
                    record["page_classification"] = (
                        "qualified_explicit_empty_initial"
                        if page_index == 0
                        else "qualified_explicit_empty_terminal"
                    )
                    converged = True
                    seen_page_urls.add(current_url)
                    break

                if str(contract["qualified_explicit_empty_rule"]["exact_heading"]) in headings:
                    raise RuntimeError("qualified empty heading present but exact V7 shape did not match")
                if not header:
                    raise RuntimeError("ordinary transaction page missing required transaction header")
                if len(rows) < int(contract["ordinary_transaction_page_rule"]["standard_transaction_rows_min"]):
                    raise RuntimeError("ordinary transaction page has zero transaction rows")

                raw_sha = str(record["raw_sha256"])
                if page_index > 0:
                    if raw_sha in seen_transaction_shas:
                        raise RuntimeError("transaction cursor response repeated a prior transaction-page SHA")
                    if len(novel_keys) < int(
                        contract["transport_and_pagination"]["transaction_cursor_page_novel_rows_vs_prior_union_min"]
                    ):
                        raise RuntimeError("transaction cursor response contained zero novel transaction rows")

                record["page_classification"] = "ordinary_transaction_page"
                seen_page_urls.add(current_url)
                seen_transaction_shas.add(raw_sha)
                all_row_keys.update(row_keys)

                if not distinct_after:
                    converged = True
                    break
                current_url = _amp_cursor_url(endpoint_url, distinct_after[0])
            finally:
                response.close()

        if not converged:
            raise RuntimeError("endpoint did not converge before maximum_pages_per_endpoint")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        if pages and "page_classification" not in pages[-1]:
            pages[-1]["page_classification"] = "unclassified_error"
            pages[-1]["classification_error"] = error

    return {
        "year": int(year),
        "month": int(month),
        "category": str(category),
        "endpoint_url": endpoint_url,
        "pages_fetched": len(pages),
        "unique_transaction_rows": len(all_row_keys),
        "converged": converged,
        "error": error,
        "pages": pages,
    }


def _evidence_found(endpoints: list[dict[str, Any]], item: dict[str, Any]) -> bool:
    for ep in endpoints:
        if ep["year"] != int(item["year"]) or ep["month"] != int(item["month"]) or ep["category"] != str(item["category"]):
            continue
        for page in ep["pages"]:
            for row in page.get("rows", []):
                if str(row.get("name", "")) != str(item["name"]):
                    continue
                if str(item["transaction_contains"]).casefold() in str(row.get("transaction", "")).casefold():
                    return True
    return False


def capture_year(
    contract_path: Path,
    v6_contract_path: Path,
    *,
    year: int,
    timeout: float,
    output_root: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    v6_contract = json.loads(v6_contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    if int(year) not in contract["scope"]["years"]:
        raise ValueError("year outside frozen scope")

    endpoints: list[dict[str, Any]] = []
    for month in contract["scope"]["months"]:
        for category in contract["scope"]["categories"]:
            endpoints.append(
                crawl_endpoint(
                    contract,
                    year=int(year),
                    month=int(month),
                    category=str(category),
                    timeout=timeout,
                    output_root=output_root,
                )
            )

    pages = [page for ep in endpoints for page in ep["pages"]]
    source_errors = [ep for ep in endpoints if ep["error"]]
    observed_empty_urls = {
        str(page["requested_url"])
        for page in pages
        if str(page.get("page_classification", "")).startswith("qualified_explicit_empty_")
    }
    expected_empty_urls = _expected_empty_urls(v6_contract, int(year))
    semantic = [
        {**item, "found": _evidence_found(endpoints, item)}
        for item in contract["known_semantic_evidence"]
        if int(item["year"]) == int(year)
    ]
    month_rows = {
        str(month): sum(ep["unique_transaction_rows"] for ep in endpoints if ep["month"] == month)
        for month in contract["scope"]["months"]
    }
    category_rows = {
        category: sum(ep["unique_transaction_rows"] for ep in endpoints if ep["category"] == category)
        for category in contract["scope"]["categories"]
    }
    unclassified = [p for p in pages if p.get("page_classification") == "unclassified_error"]
    raw_failures = [p for p in pages if not p.get("raw_sha256") or not p.get("gzip_roundtrip_matches")]
    year_gate = bool(
        len(endpoints) == int(contract["scope"]["expected_endpoints_per_year"])
        and not source_errors
        and all(ep["converged"] for ep in endpoints)
        and not unclassified
        and not raw_failures
        and observed_empty_urls == expected_empty_urls
        and sum(ep["unique_transaction_rows"] for ep in endpoints) > 0
        and all(item["found"] for item in semantic)
    )

    result = {
        "capture_version": 8,
        "contract_id": CONTRACT_ID,
        "year": int(year),
        "endpoints_expected": int(contract["scope"]["expected_endpoints_per_year"]),
        "endpoints_accounted_for": len(endpoints),
        "source_errors": len(source_errors),
        "pages_fetched_total": len(pages),
        "ordinary_transaction_pages": sum(p.get("page_classification") == "ordinary_transaction_page" for p in pages),
        "qualified_explicit_empty_initial_pages": sum(p.get("page_classification") == "qualified_explicit_empty_initial" for p in pages),
        "qualified_explicit_empty_terminal_pages": sum(p.get("page_classification") == "qualified_explicit_empty_terminal" for p in pages),
        "unclassified_pages": len(unclassified),
        "raw_preservation_failures": len(raw_failures),
        "raw_source_bytes_total": sum(int(p.get("raw_bytes") or 0) for p in pages),
        "gzip_bytes_total": sum(int(p.get("gzip_bytes") or 0) for p in pages),
        "unique_transaction_rows_across_endpoint_sums": sum(ep["unique_transaction_rows"] for ep in endpoints),
        "month_unique_row_sums": month_rows,
        "category_unique_row_sums": category_rows,
        "observed_explicit_empty_request_urls": sorted(observed_empty_urls),
        "expected_explicit_empty_request_urls": sorted(expected_empty_urls),
        "explicit_empty_request_set_exact_match": observed_empty_urls == expected_empty_urls,
        "known_semantic_evidence": semantic,
        "year_capture_gate_pass": year_gate,
        "endpoints": endpoints,
        "all_month_full_ledger_capture_qualified": False,
        "full_ledger_source_capture_complete": False,
        "durable_full_ledger_source_archive_qualified": False,
        "transaction_state_machine_defined": False,
        "transaction_semantic_taxonomy_qualified": False,
        "same_day_transaction_order_resolved": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }
    (output_root / "capture.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--v6-contract", type=Path, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    args.output_root.mkdir(parents=True, exist_ok=True)
    result = capture_year(
        args.contract,
        args.v6_contract,
        year=args.year,
        timeout=args.timeout,
        output_root=args.output_root,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "endpoints"}, indent=2, sort_keys=True))
    if not result["year_capture_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
