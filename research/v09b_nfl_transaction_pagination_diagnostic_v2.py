from __future__ import annotations

"""Post-V1 transport diagnostic for NFL.com transaction pagination.

This module deliberately has no source-qualification, chronology, membership, label, or
model authority. It tests whether transport/session/cache variants make a discovered
`after` cursor advance response bytes or transaction-row identity.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from research.v09b_nfl_transaction_ledger_source_probe_v1 import parse_transaction_rows

CONTRACT_ID = "V09B-NFL-TRANSACTION-PAGINATION-DIAGNOSTIC-V2"
ALLOWED_HOST = "www.nfl.com"
CACHE_HEADERS = ("cache-control", "age", "vary", "etag", "x-cache")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate(url: str) -> None:
    p = urlparse(str(url))
    if p.scheme.lower() != "https" or (p.hostname or "").lower() != ALLOWED_HOST:
        raise ValueError(f"non-first-party URL: {url}")


def _row_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row.get(k, "") for k in ("from", "to", "date", "name", "position", "transaction"))


def _headers(response: Any) -> dict[str, str]:
    lowered = {str(k).lower(): str(v) for k, v in response.headers.items()}
    return {k: lowered.get(k, "") for k in CACHE_HEADERS}


def _cursor_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    found: list[str] = []
    seen: set[str] = set()
    base = urlparse(base_url)
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, str(a.get("href") or ""))
        p = urlparse(href)
        if p.scheme.lower() != "https" or (p.hostname or "").lower() != ALLOWED_HOST:
            continue
        if p.path.rstrip("/") != base.path.rstrip("/"):
            continue
        if "after" not in parse_qs(p.query, keep_blank_values=True):
            continue
        if href not in seen:
            seen.add(href)
            found.append(href)
    return found


def _embedded_evidence(html: str, base_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    scripts: list[str] = []
    for s in soup.find_all("script", src=True):
        absolute = urljoin(base_url, str(s.get("src") or ""))
        if absolute not in scripts:
            scripts.append(absolute)
        if len(scripts) >= 40:
            break

    snippets: list[dict[str, str]] = []
    needles = ("after", "transaction", "next page")
    for s in soup.find_all("script"):
        if s.get("src"):
            continue
        text = str(s.string or s.get_text(" ", strip=True) or "")
        low = text.casefold()
        for needle in needles:
            idx = low.find(needle)
            if idx < 0:
                continue
            start = max(0, idx - 200)
            end = min(len(text), idx + 400)
            snippets.append({"needle": needle, "snippet": text[start:end]})
            break
        if len(snippets) >= 20:
            break
    return {"script_src_urls": scripts, "inline_script_snippets": snippets}


def _record_response(response: Any, initial_keys: set[tuple[str, ...]]) -> dict[str, Any]:
    raw = response.content
    html = raw.decode("utf-8", errors="replace")
    rows, literal_header = parse_transaction_rows(html)
    keys = {_row_key(r) for r in rows}
    return {
        "status_code": int(response.status_code),
        "final_url": str(response.url),
        "raw_bytes": len(raw),
        "raw_sha256": _sha(raw),
        "rows_parsed": len(rows),
        "literal_required_header_seen": bool(literal_header),
        "novel_row_count_vs_initial": len(keys - initial_keys),
        "cache_headers": _headers(response),
    }


def _get(session: Any, url: str, *, timeout: float, headers: dict[str, str] | None = None) -> Any:
    response = session.get(url, timeout=timeout, headers=headers or {})
    response.raise_for_status()
    _validate(str(response.url))
    return response


def diagnose_endpoint(item: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    url = str(item["url"])
    _validate(url)
    base_headers = {
        "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-transaction-pagination-diagnostic/2.0)",
        "Accept": "text/html,application/xhtml+xml",
    }
    session = requests.Session()
    initial = _get(session, url, timeout=timeout, headers=base_headers)
    initial_html = initial.content.decode("utf-8", errors="replace")
    initial_rows, initial_header = parse_transaction_rows(initial_html)
    initial_keys = {_row_key(r) for r in initial_rows}
    cursors = _cursor_urls(initial_html, str(initial.url))
    if len(cursors) != 1:
        raise RuntimeError(f"expected exactly one after cursor, found {len(cursors)}")
    cursor = cursors[0]

    variants: list[dict[str, Any]] = []

    fresh = requests.Session()
    response = _get(fresh, cursor, timeout=timeout, headers=base_headers)
    variants.append({"variant": "fresh_default", **_record_response(response, initial_keys)})

    response = _get(session, cursor, timeout=timeout, headers=base_headers)
    variants.append({"variant": "same_session_default", **_record_response(response, initial_keys)})

    browser_headers = {
        **base_headers,
        "Referer": str(initial.url),
        "Accept-Language": "en-US,en;q=0.9",
        "Upgrade-Insecure-Requests": "1",
    }
    response = _get(session, cursor, timeout=timeout, headers=browser_headers)
    variants.append({"variant": "same_session_browser_referer", **_record_response(response, initial_keys)})

    no_cache_headers = {
        **browser_headers,
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    response = _get(session, cursor, timeout=timeout, headers=no_cache_headers)
    variants.append({"variant": "same_session_browser_referer_no_cache", **_record_response(response, initial_keys)})

    initial_sha = _sha(initial.content)
    for row in variants:
        row["bytes_advanced_vs_initial"] = row["raw_sha256"] != initial_sha
        row["rows_advanced_vs_initial"] = int(row["novel_row_count_vs_initial"]) > 0

    return {
        "season": int(item["season"]),
        "month": int(item["month"]),
        "category": str(item["category"]),
        "initial_url": url,
        "initial_final_url": str(initial.url),
        "initial_status_code": int(initial.status_code),
        "initial_raw_bytes": len(initial.content),
        "initial_raw_sha256": initial_sha,
        "initial_rows_parsed": len(initial_rows),
        "initial_literal_required_header_seen": bool(initial_header),
        "initial_cache_headers": _headers(initial),
        "cursor_url": cursor,
        "cursor_query": parse_qs(urlparse(cursor).query, keep_blank_values=True),
        "embedded_evidence": _embedded_evidence(initial_html, str(initial.url)),
        "variants": variants,
        "any_transport_variant_advanced_bytes": any(v["bytes_advanced_vs_initial"] for v in variants),
        "any_transport_variant_advanced_rows": any(v["rows_advanced_vs_initial"] for v in variants),
    }


def run(contract_path: Path, *, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    endpoints: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for item in contract["fixed_endpoints"]:
        try:
            endpoints.append(diagnose_endpoint(item, timeout=timeout))
        except Exception as exc:
            errors.append({
                "season": str(item.get("season")),
                "category": str(item.get("category")),
                "error": f"{type(exc).__name__}: {exc}",
            })

    return {
        "diagnostic_version": 2,
        "contract_id": CONTRACT_ID,
        "endpoints_expected": 2,
        "endpoints_completed": len(endpoints),
        "errors": errors,
        "endpoints": endpoints,
        "any_endpoint_transport_advanced_bytes": any(x["any_transport_variant_advanced_bytes"] for x in endpoints),
        "any_endpoint_transport_advanced_rows": any(x["any_transport_variant_advanced_rows"] for x in endpoints),
        "content_advancement_is_observation_not_gate": True,
        "diagnostic_complete": len(endpoints) == 2 and not errors,
        "diagnostic_has_source_qualification_authority": False,
        "diagnostic_has_chronology_authority": False,
        "full_paginated_source_class_qualified": False,
        "transaction_state_machine_defined": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
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
    result = run(args.contract, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "endpoints"}, indent=2, sort_keys=True))
    if not result["diagnostic_complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
