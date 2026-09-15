from __future__ import annotations

"""Capture the exact 72 V5 no-header response shapes without assigning empty semantics."""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from research.v09b_nfl_transaction_ledger_source_probe_v1 import parse_transaction_rows

CONTRACT_ID = "V09B-NFL-TRANSACTION-NO-HEADER-SOURCE-SHAPE-V6"
SPACE = re.compile(r"\s+")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _normalize_visible_text(html: str) -> str:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return SPACE.sub(" ", soup.get_text(" ", strip=True)).strip()


def _title_and_headings(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(str(html or ""), "html.parser")
    title = SPACE.sub(" ", soup.title.get_text(" ", strip=True)).strip() if soup.title else ""
    headings: list[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        value = SPACE.sub(" ", tag.get_text(" ", strip=True)).strip()
        if value:
            headings.append(value)
    return title, headings


def _forward_after_values(html: str, base_url: str, expected_path: str) -> list[str]:
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


def _validate_final(requested_url: str, final_url: str, allowed_hosts: set[str]) -> None:
    req = urlparse(requested_url)
    final = urlparse(final_url)
    if final.scheme.lower() != "https":
        raise ValueError(f"non-https final URL: {final_url}")
    if (final.hostname or "").lower() not in allowed_hosts:
        raise ValueError(f"unexpected final host: {final_url}")
    if final.path.rstrip("/") != req.path.rstrip("/"):
        raise ValueError(f"final path changed: requested={requested_url} final={final_url}")


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


def _case_raw_path(case: dict[str, Any]) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(case["case_id"]))
    return Path("raw") / f"{safe}.html.gz"


def capture_case(
    case: dict[str, Any],
    *,
    allowed_hosts: set[str],
    timeout: float,
    output_root: Path,
    visible_prefix_chars: int,
) -> dict[str, Any]:
    requested_url = str(case["requested_url"])
    record: dict[str, Any] = {
        "case_id": str(case["case_id"]),
        "kind": str(case["kind"]),
        "year": int(case["year"]),
        "month": int(case["month"]),
        "category": str(case["category"]),
        "requested_url": requested_url,
        "empty_result_semantics_assigned": False,
        "terminal_page_semantics_assigned": False,
        "error": None,
    }
    response: requests.Response | None = None
    try:
        response = requests.get(
            requested_url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-no-header-shape/6.0)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
        )
        raw = bytes(response.content)
        stored = _write_raw(raw, output_root / _case_raw_path(case))
        record.update(stored)
        record["status_code"] = int(response.status_code)
        record["final_url"] = str(response.url)
        record["content_type"] = str(response.headers.get("content-type", ""))
        record["content_length_header"] = str(response.headers.get("content-length", ""))
        record["response_history_statuses"] = [int(x.status_code) for x in response.history]

        response.raise_for_status()
        _validate_final(requested_url, str(response.url), allowed_hosts)

        html = raw.decode("utf-8", errors="replace")
        visible = _normalize_visible_text(html)
        title, headings = _title_and_headings(html)
        rows, header = parse_transaction_rows(html)
        expected_path = urlparse(requested_url).path
        forwards = _forward_after_values(html, str(response.url), expected_path)
        soup = BeautifulSoup(html, "html.parser")

        record.update(
            {
                "title": title,
                "headings": headings,
                "table_count": len(soup.find_all("table")),
                "standard_transaction_header_seen": bool(header),
                "standard_transaction_row_count": len(rows),
                "standard_transaction_rows": rows,
                "forward_after_cursor_count": len(forwards),
                "forward_after_cursors": forwards,
                "normalized_visible_text_chars": len(visible),
                "normalized_visible_text_sha256": _sha(visible.encode("utf-8")),
                "normalized_visible_text_prefix": visible[:visible_prefix_chars],
            }
        )
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if response is not None:
            response.close()
    return record


def run_diagnostic(
    contract_path: Path,
    *,
    output_root: Path,
    timeout: float,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")

    cases = list(contract["scope"]["fixed_requests"])
    case_ids = [str(x["case_id"]) for x in cases]
    if len(cases) != int(contract["scope"]["fixed_request_count"]):
        raise ValueError("fixed request count mismatch")
    if len(set(case_ids)) != len(case_ids):
        raise ValueError("duplicate case ids")

    allowed_hosts = set(contract["capture"]["allowed_final_hosts"])
    prefix_chars = int(contract["capture"]["record_normalized_visible_text_prefix_chars"])
    output_root.mkdir(parents=True, exist_ok=True)

    results = [
        capture_case(
            case,
            allowed_hosts=allowed_hosts,
            timeout=timeout,
            output_root=output_root,
            visible_prefix_chars=prefix_chars,
        )
        for case in cases
    ]
    errors = [r for r in results if r.get("error")]
    status_failures = [r for r in results if r.get("status_code") != 200]
    raw_missing = [r for r in results if not r.get("raw_sha256")]
    gzip_failures = [r for r in results if not r.get("gzip_roundtrip_matches")]

    gate_pass = bool(
        len(results) == 72
        and not errors
        and not status_failures
        and not raw_missing
        and not gzip_failures
        and len({r["case_id"] for r in results}) == 72
    )

    shape_counts: dict[str, int] = {}
    for result in results:
        shape_key = "|".join(
            [
                f"header={int(bool(result.get('standard_transaction_header_seen')))}",
                f"rows={int(result.get('standard_transaction_row_count') or 0)}",
                f"tables={int(result.get('table_count') or 0)}",
                f"after={int(result.get('forward_after_cursor_count') or 0)}",
                f"visible_sha={str(result.get('normalized_visible_text_sha256') or '')}",
            ]
        )
        shape_counts[shape_key] = shape_counts.get(shape_key, 0) + 1

    result = {
        "diagnostic_version": 6,
        "contract_id": CONTRACT_ID,
        "fixed_requests_expected": 72,
        "fixed_requests_accounted_for": len(results),
        "transport_errors": len(errors),
        "http_status_failures": len(status_failures),
        "raw_preservation_failures": len(raw_missing),
        "gzip_roundtrip_failures": len(gzip_failures),
        "initial_cases": sum(r["kind"] == "initial" for r in results),
        "post_pagination_cases": sum(r["kind"] == "post_pagination" for r in results),
        "standard_header_seen_count": sum(bool(r.get("standard_transaction_header_seen")) for r in results),
        "standard_rows_total": sum(int(r.get("standard_transaction_row_count") or 0) for r in results),
        "unique_raw_response_shas": len({r.get("raw_sha256") for r in results if r.get("raw_sha256")}),
        "unique_normalized_visible_text_shas": len(
            {r.get("normalized_visible_text_sha256") for r in results if r.get("normalized_visible_text_sha256")}
        ),
        "shape_signature_counts": shape_counts,
        "frozen_diagnostic_gate_pass": gate_pass,
        "no_header_shape_capture_complete": gate_pass,
        "empty_result_semantics_qualified": False,
        "terminal_page_semantics_qualified": False,
        "all_month_full_ledger_qualified": False,
        "durable_full_ledger_source_archive_qualified": False,
        "transaction_state_machine_defined": False,
        "same_day_transaction_order_resolved": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
        "cases": results,
    }
    (output_root / "diagnostic.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_diagnostic(args.contract, output_root=args.output_root, timeout=args.timeout)
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2, sort_keys=True))
    if not result["frozen_diagnostic_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
