from __future__ import annotations

"""Full 2017-2021 NFL transaction ledger capture over the qualified AMP transport.

This module captures source bytes and parsed rows only. It defines no roster-state
transition semantics and has no chronology, membership, label, or model authority.
"""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from research.v09b_nfl_transaction_ledger_source_probe_v1 import parse_transaction_rows

CONTRACT_ID = "V09B-NFL-TRANSACTION-FULL-LEDGER-CAPTURE-V5"
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


def _validate_final(url: str, expected_path: str, allowed_hosts: set[str]) -> None:
    p = urlparse(str(url))
    if p.scheme.lower() != "https" or (p.hostname or "").lower() not in allowed_hosts:
        raise ValueError(f"unexpected final host: {url}")
    if p.path.rstrip("/") != expected_path.rstrip("/"):
        raise ValueError(f"transaction path changed: {url}")


def _amp_cursor_url(endpoint_url: str, cursor: str) -> str:
    p = urlparse(endpoint_url)
    return f"https://amp.nfl.com{p.path}?after={quote(str(cursor), safe='')}"


def _next_after_values(html: str, base_url: str, expected_path: str) -> list[str]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    found: list[str] = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(base_url, str(a.get("href") or ""))
        p = urlparse(absolute)
        if p.scheme.lower() != "https" or p.path.rstrip("/") != expected_path.rstrip("/"):
            continue
        for value in parse_qs(p.query, keep_blank_values=True).get("after", []):
            if value and value not in found:
                found.append(value)
    return found


def _get(url: str, *, timeout: float, expected_path: str, allowed_hosts: set[str]) -> requests.Response:
    r = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-full-transaction-capture/5.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    r.raise_for_status()
    _validate_final(str(r.url), expected_path, allowed_hosts)
    return r


def _write_raw_gzip(raw: bytes, path: Path) -> dict[str, Any]:
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
    expected_path = urlparse(endpoint_url).path
    allowed_hosts = set(contract["pagination"]["allowed_final_hosts"])
    max_pages = int(contract["scope"]["maximum_pages_per_endpoint"])
    all_row_keys: set[tuple[str, ...]] = set()
    seen_page_urls: set[str] = set()
    seen_page_shas: set[str] = set()
    pages: list[dict[str, Any]] = []
    current_url = endpoint_url
    converged = False
    error: str | None = None

    try:
        for page_index in range(max_pages):
            if current_url in seen_page_urls:
                raise RuntimeError(f"page URL cycle: {current_url}")
            response = _get(
                current_url,
                timeout=timeout,
                expected_path=expected_path,
                allowed_hosts=allowed_hosts,
            )
            raw = bytes(response.content)
            html = raw.decode("utf-8", errors="replace")
            rows, header = parse_transaction_rows(html)
            raw_sha = _sha(raw)
            row_keys = {_row_key(row) for row in rows}
            novel_keys = row_keys - all_row_keys
            overlap_keys = row_keys & all_row_keys
            if not header:
                raise RuntimeError("required transaction table header missing")
            if page_index > 0:
                if raw_sha in seen_page_shas:
                    raise RuntimeError("cursor response repeated a prior page SHA")
                if not novel_keys:
                    raise RuntimeError("cursor response contained zero novel transaction rows")

            next_values = _next_after_values(html, str(response.url), expected_path)
            current_after = parse_qs(urlparse(current_url).query, keep_blank_values=True).get("after", [])
            current_after_value = current_after[0] if current_after else None
            next_values = [x for x in next_values if x != current_after_value]
            if len(next_values) > 1:
                raise RuntimeError(f"multiple forward after cursors found: {len(next_values)}")

            rel = Path("raw") / str(year) / f"{month:02d}" / category / f"page_{page_index:03d}.html.gz"
            stored = _write_raw_gzip(raw, output_root / rel)
            page_record = {
                "page_index": page_index,
                "requested_url": current_url,
                "final_url": str(response.url),
                "status_code": int(response.status_code),
                "literal_required_header_seen": bool(header),
                "novel_rows_vs_prior_union": len(novel_keys),
                "overlap_rows_vs_prior_union": len(overlap_keys),
                "rows": rows,
                "forward_after_cursor_count": len(next_values),
                "forward_after_cursor": next_values[0] if next_values else None,
                **stored,
            }
            pages.append(page_record)
            seen_page_urls.add(current_url)
            seen_page_shas.add(raw_sha)
            all_row_keys.update(row_keys)
            response.close()

            if not next_values:
                converged = True
                break
            current_url = _amp_cursor_url(endpoint_url, next_values[0])
        if not converged:
            raise RuntimeError("endpoint did not converge before maximum_pages_per_endpoint")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return {
        "year": int(year),
        "month": int(month),
        "category": category,
        "endpoint_url": endpoint_url,
        "pages_fetched": len(pages),
        "unique_page_urls": len(seen_page_urls),
        "unique_page_shas": len(seen_page_shas),
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
            for row in page["rows"]:
                if str(row.get("name", "")) != str(item["name"]):
                    continue
                if str(item["transaction_contains"]).casefold() in str(row.get("transaction", "")).casefold():
                    return True
    return False


def capture_year(
    contract_path: Path,
    *,
    year: int,
    timeout: float,
    output_root: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
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

    source_errors = [ep for ep in endpoints if ep["error"]]
    pages = [p for ep in endpoints for p in ep["pages"]]
    transitions = sum(max(0, ep["pages_fetched"] - 1) for ep in endpoints)
    month_rows = {
        str(month): sum(ep["unique_transaction_rows"] for ep in endpoints if ep["month"] == month)
        for month in contract["scope"]["months"]
    }
    category_rows = {
        category: sum(ep["unique_transaction_rows"] for ep in endpoints if ep["category"] == category)
        for category in contract["scope"]["categories"]
    }
    semantic = [
        {**item, "found": _evidence_found(endpoints, item)}
        for item in contract["known_semantic_evidence"]
        if int(item["year"]) == int(year)
    ]
    year_gate = bool(
        len(endpoints) == 72
        and not source_errors
        and all(ep["converged"] for ep in endpoints)
        and all(ep["unique_page_urls"] == ep["pages_fetched"] for ep in endpoints)
        and all(ep["unique_page_shas"] == ep["pages_fetched"] for ep in endpoints)
        and all(page["gzip_roundtrip_matches"] for page in pages)
        and all(page["literal_required_header_seen"] for page in pages)
        and all(page["page_index"] == 0 or page["novel_rows_vs_prior_union"] >= 1 for page in pages)
        and sum(ep["unique_transaction_rows"] for ep in endpoints) > 0
        and all(item["found"] for item in semantic)
    )
    result = {
        "capture_version": 5,
        "contract_id": CONTRACT_ID,
        "year": int(year),
        "endpoints_expected": 72,
        "endpoints_completed": len(endpoints),
        "source_errors": len(source_errors),
        "pages_fetched_total": len(pages),
        "cursor_transitions_total": transitions,
        "raw_source_bytes_total": sum(page["raw_bytes"] for page in pages),
        "gzip_bytes_total": sum(page["gzip_bytes"] for page in pages),
        "unique_transaction_rows_across_endpoint_sums": sum(ep["unique_transaction_rows"] for ep in endpoints),
        "month_unique_row_sums": month_rows,
        "category_unique_row_sums": category_rows,
        "known_semantic_evidence": semantic,
        "year_capture_gate_pass": year_gate,
        "endpoints": endpoints,
        "all_month_capture_complete": False,
        "durable_full_ledger_source_archive_qualified": False,
        "transaction_state_machine_defined": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }
    manifest_path = output_root / "capture.json"
    manifest_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: Iterable[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--output-root", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=60.0)
    args = p.parse_args(list(argv) if argv is not None else None)
    args.output_root.mkdir(parents=True, exist_ok=True)
    result = capture_year(
        args.contract,
        year=args.year,
        timeout=args.timeout,
        output_root=args.output_root,
    )
    print(json.dumps({k: v for k, v in result.items() if k != "endpoints"}, indent=2, sort_keys=True))
    if not result["year_capture_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
