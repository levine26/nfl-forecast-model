from __future__ import annotations

"""Validate explicit NFL transaction empty-result semantics with fixed controls."""

import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from research.v09b_nfl_transaction_ledger_source_probe_v1 import parse_transaction_rows
from research.v09b_nfl_transaction_no_header_source_shape_v6 import (
    _forward_after_values,
    _title_and_headings,
    _validate_final,
)

CONTRACT_ID = "V09B-NFL-TRANSACTION-EMPTY-SEMANTICS-V7"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


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


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", value)


def _current_after(url: str) -> str | None:
    values = parse_qs(urlparse(url).query, keep_blank_values=True).get("after", [])
    return values[0] if values else None


def _distinct_forward_values(values: list[str], requested_url: str) -> list[str]:
    current = _current_after(requested_url)
    return [x for x in values if x != current]


def _candidate_rule(record: dict[str, Any], contract: dict[str, Any]) -> bool:
    rule = contract["candidate_rule"]
    headings = list(record.get("headings") or [])
    return bool(
        rule["exact_heading_required"] in headings
        and bool(record.get("standard_transaction_header_seen"))
        == bool(rule["standard_transaction_header_seen_must_equal"])
        and int(record.get("standard_transaction_row_count") or 0)
        == int(rule["standard_transaction_row_count_must_equal"])
        and int(record.get("table_count") or 0) == int(rule["html_table_count_must_equal"])
        and int(record.get("distinct_forward_after_cursor_count") or 0)
        == int(rule["distinct_forward_after_cursor_count_must_equal"])
    )


def _capture(
    case: dict[str, Any],
    *,
    contract: dict[str, Any],
    output_root: Path,
    timeout: float,
) -> dict[str, Any]:
    requested_url = str(case["requested_url"])
    record: dict[str, Any] = {
        **case,
        "requested_url": requested_url,
        "error": None,
    }
    response: requests.Response | None = None
    try:
        response = requests.get(
            requested_url,
            timeout=timeout,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-empty-semantics/7.0)",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Cache-Control": "no-cache",
            },
        )
        raw = bytes(response.content)
        stored = _write_raw(
            raw,
            output_root / "raw" / f"{_safe_name(str(case['case_id']))}.html.gz",
        )
        record.update(stored)
        record["status_code"] = int(response.status_code)
        record["final_url"] = str(response.url)
        record["content_type"] = str(response.headers.get("content-type", ""))
        record["response_history_statuses"] = [int(x.status_code) for x in response.history]

        response.raise_for_status()
        _validate_final(
            requested_url,
            str(response.url),
            set(contract["transport"]["allowed_final_hosts"]),
        )

        html = raw.decode("utf-8", errors="replace")
        rows, header = parse_transaction_rows(html)
        _, headings = _title_and_headings(html)
        soup = BeautifulSoup(html, "html.parser")
        all_after = _forward_after_values(html, str(response.url), urlparse(requested_url).path)
        distinct_after = _distinct_forward_values(all_after, requested_url)
        record.update(
            {
                "headings": headings,
                "standard_transaction_header_seen": bool(header),
                "standard_transaction_row_count": len(rows),
                "standard_transaction_rows": rows,
                "table_count": len(soup.find_all("table")),
                "all_after_values": all_after,
                "distinct_forward_after_values": distinct_after,
                "distinct_forward_after_cursor_count": len(distinct_after),
            }
        )
        record["candidate_rule_match"] = _candidate_rule(record, contract)
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        record["candidate_rule_match"] = False
    finally:
        if response is not None:
            response.close()
    return record


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_validation(
    contract_path: Path,
    *,
    v6_contract_path: Path,
    output_root: Path,
    timeout: float,
) -> dict[str, Any]:
    contract = _load_json(contract_path)
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected V7 contract id")
    v6 = _load_json(v6_contract_path)
    positives_src = list(v6["scope"]["fixed_requests"])
    if len(positives_src) != 72:
        raise ValueError("V6 positive universe is not 72 cases")

    positives = [
        {
            "case_id": f"positive-{x['case_id']}",
            "control_class": "positive_v6",
            "v6_case_id": x["case_id"],
            "v6_kind": x["kind"],
            "year": x["year"],
            "month": x["month"],
            "category": x["category"],
            "requested_url": x["requested_url"],
        }
        for x in positives_src
    ]

    grid = contract["negative_controls"]["september_grid"]
    september_controls: list[dict[str, Any]] = []
    for year in grid["years"]:
        for category in grid["categories"]:
            september_controls.append(
                {
                    "case_id": f"negative-september-{year}-{category}",
                    "control_class": "negative_september",
                    "year": int(year),
                    "month": int(grid["month"]),
                    "category": str(category),
                    "requested_url": str(grid["url_template"]).format(category=category, year=year),
                }
            )

    preterminal_controls = [
        {**x, "control_class": "negative_preterminal"}
        for x in contract["negative_controls"]["pre_terminal_cursor_pages"]
    ]
    negatives = september_controls + preterminal_controls
    if len(negatives) != 32:
        raise ValueError("negative-control universe is not 32 cases")

    output_root.mkdir(parents=True, exist_ok=True)
    positive_results = [
        _capture(x, contract=contract, output_root=output_root, timeout=timeout) for x in positives
    ]
    negative_results = [
        _capture(x, contract=contract, output_root=output_root, timeout=timeout) for x in negatives
    ]
    all_results = positive_results + negative_results

    errors = [x for x in all_results if x.get("error")]
    status_failures = [x for x in all_results if x.get("status_code") != 200]
    raw_failures = [
        x for x in all_results if not x.get("raw_sha256") or not x.get("gzip_roundtrip_matches")
    ]
    positive_matches = sum(bool(x.get("candidate_rule_match")) for x in positive_results)
    negative_matches = sum(bool(x.get("candidate_rule_match")) for x in negative_results)

    september_ok = all(
        x.get("standard_transaction_header_seen") is True
        and int(x.get("standard_transaction_row_count") or 0) >= 1
        and contract["candidate_rule"]["exact_heading_required"] not in (x.get("headings") or [])
        for x in negative_results
        if x["control_class"] == "negative_september"
    )

    preterminal_ok = True
    for x in [r for r in negative_results if r["control_class"] == "negative_preterminal"]:
        expected = next(
            c
            for c in contract["negative_controls"]["pre_terminal_cursor_pages"]
            if c["case_id"] == x["case_id"]
        )
        if not (
            x.get("standard_transaction_header_seen") is True
            and int(x.get("standard_transaction_row_count") or 0)
            == int(expected["standard_transaction_rows_expected"])
            and x.get("distinct_forward_after_values")
            == [expected["expected_distinct_forward_after_cursor"]]
            and contract["candidate_rule"]["exact_heading_required"] not in (x.get("headings") or [])
        ):
            preterminal_ok = False

    gate_pass = bool(
        len(positive_results) == 72
        and len(negative_results) == 32
        and not errors
        and not status_failures
        and not raw_failures
        and positive_matches == 72
        and negative_matches == 0
        and september_ok
        and preterminal_ok
    )

    result = {
        "validation_version": 7,
        "contract_id": CONTRACT_ID,
        "positive_cases_accounted_for": len(positive_results),
        "positive_rule_matches": positive_matches,
        "positive_false_negatives": len(positive_results) - positive_matches,
        "negative_controls_accounted_for": len(negative_results),
        "negative_rule_matches": negative_matches,
        "negative_false_positives": negative_matches,
        "september_negative_controls": len(september_controls),
        "september_negative_controls_pass": september_ok,
        "preterminal_negative_controls": len(preterminal_controls),
        "preterminal_negative_controls_pass": preterminal_ok,
        "transport_errors": len(errors),
        "http_status_failures": len(status_failures),
        "raw_preservation_failures": len(raw_failures),
        "frozen_semantics_gate_pass": gate_pass,
        "explicit_no_transactions_empty_result_semantics_qualified": gate_pass,
        "post_pagination_explicit_empty_terminal_semantics_qualified": gate_pass,
        "qualification_scope": contract["authority_if_gate_passes"]["qualification_scope"],
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
        "positive_cases": positive_results,
        "negative_controls": negative_results,
    }
    (output_root / "validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--v6-contract", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = run_validation(
        args.contract,
        v6_contract_path=args.v6_contract,
        output_root=args.output_root,
        timeout=args.timeout,
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"positive_cases", "negative_controls"}},
            indent=2,
            sort_keys=True,
        )
    )
    if not result["frozen_semantics_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
