from __future__ import annotations

"""Preregistered V3 diagnostic for NFL transaction pagination over the AMP transport."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlparse

import requests

from research.v09b_nfl_transaction_ledger_source_probe_v1 import parse_transaction_rows

CONTRACT_ID = "V09B-NFL-TRANSACTION-PAGINATION-DIAGNOSTIC-V3"
ROW_FIELDS = ("from", "to", "date", "name", "position", "transaction")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _row_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(k, "")) for k in ROW_FIELDS)


def _amp_url(www_url: str, cursor: str | None = None) -> str:
    p = urlparse(www_url)
    if p.scheme != "https" or p.hostname != "www.nfl.com":
        raise ValueError(f"unexpected www endpoint: {www_url}")
    url = f"https://amp.nfl.com{p.path}"
    if cursor is not None:
        url += "?after=" + quote(str(cursor), safe="")
    return url


def _validate_final(url: str, expected_path: str, allowed_hosts: set[str]) -> None:
    p = urlparse(str(url))
    if p.scheme != "https" or (p.hostname or "").lower() not in allowed_hosts:
        raise ValueError(f"unexpected final host: {url}")
    if p.path.rstrip("/") != expected_path.rstrip("/"):
        raise ValueError(f"transaction path changed: {url}")


def _get(url: str, *, timeout: float, expected_path: str, allowed_hosts: set[str]) -> requests.Response:
    r = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-transaction-AMP/3.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    r.raise_for_status()
    _validate_final(str(r.url), expected_path, allowed_hosts)
    return r


def _record(response: requests.Response) -> dict[str, Any]:
    raw = bytes(response.content)
    rows, header = parse_transaction_rows(raw.decode("utf-8", errors="replace"))
    return {
        "requested_url": str(response.request.url),
        "final_url": str(response.url),
        "status_code": int(response.status_code),
        "raw_bytes": len(raw),
        "raw_sha256": _sha(raw),
        "rows_parsed": len(rows),
        "literal_required_header_seen": bool(header),
        "row_keys": [list(_row_key(row)) for row in rows],
    }


def diagnose_endpoint(item: dict[str, Any], contract: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    www = str(item["www_initial_url"])
    cursor = str(item["frozen_after_cursor"])
    expected_path = urlparse(www).path
    allowed_hosts = set(contract["transport"]["allowed_final_hosts"])

    www_initial_r = _get(www, timeout=timeout, expected_path=expected_path, allowed_hosts=allowed_hosts)
    www_initial = _record(www_initial_r)
    amp_initial_url = _amp_url(www)
    amp_cursor_url = _amp_url(www, cursor)
    amp_initial_r = _get(amp_initial_url, timeout=timeout, expected_path=expected_path, allowed_hosts=allowed_hosts)
    amp_cursor_r = _get(amp_cursor_url, timeout=timeout, expected_path=expected_path, allowed_hosts=allowed_hosts)
    amp_initial = _record(amp_initial_r)
    amp_cursor = _record(amp_cursor_r)

    initial_keys = {tuple(x) for x in amp_initial["row_keys"]}
    cursor_keys = {tuple(x) for x in amp_cursor["row_keys"]}
    novel = cursor_keys - initial_keys
    overlap = cursor_keys & initial_keys
    gate = contract["frozen_advancement_gate"]
    passed = bool(
        amp_initial["rows_parsed"] >= int(gate["initial_rows_min"])
        and amp_initial["literal_required_header_seen"] is bool(gate["amp_initial_required_header"])
        and amp_cursor["literal_required_header_seen"] is bool(gate["amp_cursor_required_header"])
        and amp_cursor["raw_sha256"] != amp_initial["raw_sha256"]
        and len(novel) >= int(gate["amp_cursor_novel_rows_vs_amp_initial_min"])
    )
    return {
        "season": int(item["season"]),
        "month": int(item["month"]),
        "category": str(item["category"]),
        "frozen_after_cursor": cursor,
        "www_initial": www_initial,
        "amp_initial": amp_initial,
        "amp_cursor": amp_cursor,
        "amp_cursor_novel_rows_vs_amp_initial": len(novel),
        "amp_cursor_overlap_rows_vs_amp_initial": len(overlap),
        "amp_cursor_bytes_advanced": amp_cursor["raw_sha256"] != amp_initial["raw_sha256"],
        "endpoint_advancement_gate_pass": passed,
    }


def run(contract_path: Path, *, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    endpoints = []
    errors = []
    for item in contract["fixed_endpoints"]:
        try:
            endpoints.append(diagnose_endpoint(item, contract, timeout=timeout))
        except Exception as exc:
            errors.append({"season": item.get("season"), "error": f"{type(exc).__name__}: {exc}"})
    complete = len(endpoints) == len(contract["fixed_endpoints"]) and not errors
    all_pass = complete and all(row["endpoint_advancement_gate_pass"] for row in endpoints)
    return {
        "diagnostic_version": 3,
        "contract_id": CONTRACT_ID,
        "endpoints_expected": len(contract["fixed_endpoints"]),
        "endpoints_completed": len(endpoints),
        "errors": errors,
        "endpoints": endpoints,
        "diagnostic_complete": complete,
        "frozen_advancement_gate_pass": all_pass,
        "diagnostic_has_source_qualification_authority": False,
        "diagnostic_has_chronology_authority": False,
        "full_paginated_source_class_qualified": False,
        "transaction_state_machine_defined": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
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
    p.add_argument("--timeout", type=float, default=60.0)
    args = p.parse_args(list(argv) if argv is not None else None)
    result = run(args.contract, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "endpoints"}, indent=2, sort_keys=True))
    if not result["diagnostic_complete"]:
        raise SystemExit(1)
    if not result["frozen_advancement_gate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
