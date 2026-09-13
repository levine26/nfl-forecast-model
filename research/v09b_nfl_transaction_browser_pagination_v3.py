from __future__ import annotations

"""Headless-browser diagnostic for frozen NFL transaction cursor URLs.

No transaction state is constructed and no source/chronology authority is granted.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlencode

from research.v09b_nfl_transaction_ledger_source_probe_v1 import (
    page_identity_markers,
    parse_transaction_rows,
    row_key,
)

CONTRACT_ID = "V09B-NFL-TRANSACTION-BROWSER-PAGINATION-DIAGNOSTIC-V3"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def cursor_url(initial_url: str, cursor: str) -> str:
    return f"{str(initial_url).rstrip('/')}?{urlencode({'after': str(cursor)})}"


def chrome_binary() -> str:
    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        value = shutil.which(candidate)
        if value:
            return value
    raise RuntimeError("no supported Chrome/Chromium binary found")


def render_dom(url: str, *, virtual_time_budget_ms: int, timeout_seconds: int) -> dict[str, Any]:
    binary = chrome_binary()
    command = [
        binary,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        f"--virtual-time-budget={int(virtual_time_budget_ms)}",
        "--dump-dom",
        str(url),
    ]
    proc = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=int(timeout_seconds),
    )
    dom = proc.stdout or ""
    return {
        "requested_url": str(url),
        "browser_binary": binary,
        "returncode": int(proc.returncode),
        "dom": dom,
        "dom_sha256": sha256_text(dom),
        "stderr_tail": (proc.stderr or "")[-3000:],
        "render_succeeded": proc.returncode == 0 and bool(dom.strip()),
    }


def endpoint_result(endpoint: dict[str, Any], contract: dict[str, Any], *, timeout_seconds: int) -> dict[str, Any]:
    budget = int(contract["browser_requirements"]["virtual_time_budget_ms"])
    initial_url = str(endpoint["initial_url"])
    next_url = cursor_url(initial_url, str(endpoint["cursor"]))
    output: dict[str, Any] = {
        "id": endpoint["id"],
        "season": int(endpoint["season"]),
        "month": int(endpoint["month"]),
        "category": str(endpoint["category"]),
        "initial_url": initial_url,
        "cursor_url": next_url,
        "initial_render": None,
        "cursor_render": None,
        "initial_rows": [],
        "cursor_rows": [],
        "initial_page_identity_markers": {},
        "cursor_page_identity_markers": {},
        "novel_cursor_rows": [],
        "missing_initial_rows_from_cursor": [],
        "dom_sha_differs": False,
        "row_set_differs": False,
        "browser_render_error": None,
    }
    try:
        initial = render_dom(initial_url, virtual_time_budget_ms=budget, timeout_seconds=timeout_seconds)
        cursor = render_dom(next_url, virtual_time_budget_ms=budget, timeout_seconds=timeout_seconds)
        output["initial_render"] = {k: v for k, v in initial.items() if k != "dom"}
        output["cursor_render"] = {k: v for k, v in cursor.items() if k != "dom"}
        if not initial["render_succeeded"] or not cursor["render_succeeded"]:
            output["browser_render_error"] = "initial or cursor browser render did not produce a DOM"
            return output
        initial_rows, initial_header = parse_transaction_rows(initial["dom"])
        cursor_rows, cursor_header = parse_transaction_rows(cursor["dom"])
        output["initial_literal_header_seen"] = bool(initial_header)
        output["cursor_literal_header_seen"] = bool(cursor_header)
        output["initial_rows"] = initial_rows
        output["cursor_rows"] = cursor_rows
        output["initial_page_identity_markers"] = page_identity_markers(
            initial["dom"], season=int(endpoint["season"]), month=int(endpoint["month"]), category=str(endpoint["category"])
        )
        output["cursor_page_identity_markers"] = page_identity_markers(
            cursor["dom"], season=int(endpoint["season"]), month=int(endpoint["month"]), category=str(endpoint["category"])
        )
        initial_keys = {row_key(row) for row in initial_rows}
        cursor_keys = {row_key(row) for row in cursor_rows}
        output["novel_cursor_rows"] = [row for row in cursor_rows if row_key(row) not in initial_keys]
        output["missing_initial_rows_from_cursor"] = [row for row in initial_rows if row_key(row) not in cursor_keys]
        output["dom_sha_differs"] = initial["dom_sha256"] != cursor["dom_sha256"]
        output["row_set_differs"] = initial_keys != cursor_keys
        return output
    except Exception as exc:
        output["browser_render_error"] = f"{type(exc).__name__}: {str(exc)[:1000]}"
        return output


def run(contract_path: Path, *, timeout_seconds: int) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    endpoints = list(contract["fixed_endpoints"])
    rows = [endpoint_result(endpoint, contract, timeout_seconds=timeout_seconds) for endpoint in endpoints]
    complete = len(rows) == 2 and all(row.get("initial_render") is not None and row.get("cursor_render") is not None for row in rows)
    return {
        "diagnostic_version": 3,
        "contract_id": CONTRACT_ID,
        "endpoints_expected": 2,
        "endpoints_reported": len(rows),
        "render_attempts_expected": 4,
        "render_attempts_reported": sum(int(row.get("initial_render") is not None) + int(row.get("cursor_render") is not None) for row in rows),
        "browser_render_errors": sum(1 for row in rows if row.get("browser_render_error")),
        "endpoints_with_dom_sha_advancement": sum(1 for row in rows if row.get("dom_sha_differs")),
        "endpoints_with_row_set_advancement": sum(1 for row in rows if row.get("row_set_differs")),
        "novel_cursor_rows_total": sum(len(row.get("novel_cursor_rows") or []) for row in rows),
        "accounting_integrity_pass": complete,
        "endpoint_results": rows,
        "diagnostic_has_source_qualification_authority": False,
        "diagnostic_has_chronology_authority": False,
        "full_paginated_source_class_qualified": False,
        "transaction_state_machine_defined": False,
        "modern_game_day_roster_universe_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "weekly_roster_membership_used": False,
        "weekly_roster_status_used": False,
        "postgame_participation_used_as_training_authority": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "model_fit_performed": False,
        "production_dependency_authorized": False,
    }


def main(argv: Iterable[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout-seconds", type=int, default=45)
    args = p.parse_args(list(argv) if argv is not None else None)
    result = run(args.contract, timeout_seconds=args.timeout_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "endpoint_results"}, indent=2, sort_keys=True))
    if not result["accounting_integrity_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
