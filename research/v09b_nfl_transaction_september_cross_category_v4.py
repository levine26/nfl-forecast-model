from __future__ import annotations

"""Five-season, six-category September AMP pagination qualification diagnostic."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from research.v09b_nfl_transaction_ledger_source_probe_v1 import parse_transaction_rows

CONTRACT_ID = "V09B-NFL-TRANSACTION-SEPTEMBER-CROSS-CATEGORY-V4"
ROW_FIELDS = ("from", "to", "date", "name", "position", "transaction")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _row_key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(str(row.get(k, "")) for k in ROW_FIELDS)


def _endpoint_url(contract: dict[str, Any], *, season: int, category: str) -> str:
    return str(contract["scope"]["url_template"]).format(
        category=category,
        season=season,
        month=int(contract["scope"]["month"]),
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
        values = parse_qs(p.query, keep_blank_values=True).get("after", [])
        for value in values:
            if value and value not in found:
                found.append(value)
    return found


def _get(url: str, *, timeout: float, expected_path: str, allowed_hosts: set[str]) -> requests.Response:
    r = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LevLine-V09B-transaction-september/4.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )
    r.raise_for_status()
    _validate_final(str(r.url), expected_path, allowed_hosts)
    return r


def crawl_endpoint(
    contract: dict[str, Any], *, season: int, category: str, timeout: float
) -> dict[str, Any]:
    endpoint_url = _endpoint_url(contract, season=season, category=category)
    expected_path = urlparse(endpoint_url).path
    allowed_hosts = set(contract["transport_and_pagination"]["allowed_final_hosts"])
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
            sha = _sha(raw)
            row_keys = {_row_key(row) for row in rows}
            novel_keys = row_keys - all_row_keys
            overlap_keys = row_keys & all_row_keys
            if page_index > 0:
                if sha in seen_page_shas:
                    raise RuntimeError("cursor response repeated a prior page SHA")
                if not novel_keys:
                    raise RuntimeError("cursor response contained zero novel transaction rows")
            if not header:
                raise RuntimeError("required transaction table header missing")

            next_values = _next_after_values(html, str(response.url), expected_path)
            current_after = parse_qs(urlparse(current_url).query, keep_blank_values=True).get("after", [])
            current_after_value = current_after[0] if current_after else None
            next_values = [x for x in next_values if x != current_after_value]
            if len(next_values) > 1:
                raise RuntimeError(f"multiple forward after cursors found: {len(next_values)}")

            page_record = {
                "page_index": page_index,
                "requested_url": current_url,
                "final_url": str(response.url),
                "status_code": int(response.status_code),
                "raw_bytes": len(raw),
                "raw_sha256": sha,
                "rows_parsed": len(rows),
                "literal_required_header_seen": bool(header),
                "novel_rows_vs_prior_union": len(novel_keys),
                "overlap_rows_vs_prior_union": len(overlap_keys),
                "rows": rows,
                "forward_after_cursor_count": len(next_values),
                "forward_after_cursor": next_values[0] if next_values else None,
            }
            pages.append(page_record)
            seen_page_urls.add(current_url)
            seen_page_shas.add(sha)
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
        "season": int(season),
        "month": int(contract["scope"]["month"]),
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
        if ep["season"] != int(item["season"]) or ep["category"] != str(item["category"]):
            continue
        for page in ep["pages"]:
            for row in page["rows"]:
                if str(row.get("name", "")) != str(item["name"]):
                    continue
                if str(item["transaction_contains"]).casefold() in str(row.get("transaction", "")).casefold():
                    return True
    return False


def audit_season(contract_path: Path, *, season: int, timeout: float) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected contract id")
    if int(season) not in contract["scope"]["seasons"]:
        raise ValueError("season outside frozen scope")

    endpoints = [
        crawl_endpoint(contract, season=int(season), category=category, timeout=timeout)
        for category in contract["scope"]["categories"]
    ]
    source_errors = [ep for ep in endpoints if ep["error"]]
    rows_total = sum(ep["unique_transaction_rows"] for ep in endpoints)
    transitions = sum(max(0, ep["pages_fetched"] - 1) for ep in endpoints)
    all_transitions_advanced = all(
        page["page_index"] == 0 or page["novel_rows_vs_prior_union"] >= 1
        for ep in endpoints for page in ep["pages"]
    )
    semantic = [
        {**item, "found": _evidence_found(endpoints, item)}
        for item in contract["known_semantic_evidence"]
        if int(item["season"]) == int(season)
    ]
    season_gate = bool(
        len(endpoints) == 6
        and not source_errors
        and all(ep["converged"] for ep in endpoints)
        and all(ep["unique_page_urls"] == ep["pages_fetched"] for ep in endpoints)
        and all(ep["unique_page_shas"] == ep["pages_fetched"] for ep in endpoints)
        and all_transitions_advanced
        and rows_total > 0
        and all(item["found"] for item in semantic)
    )
    return {
        "diagnostic_version": 4,
        "contract_id": CONTRACT_ID,
        "season": int(season),
        "endpoints_expected": 6,
        "endpoints_completed": len(endpoints),
        "source_errors": len(source_errors),
        "pages_fetched_total": sum(ep["pages_fetched"] for ep in endpoints),
        "cursor_transitions_total": transitions,
        "unique_transaction_rows_across_categories_sum": rows_total,
        "categories_with_parsed_rows": [ep["category"] for ep in endpoints if ep["unique_transaction_rows"] > 0],
        "known_semantic_evidence": semantic,
        "season_gate_pass": season_gate,
        "endpoints": endpoints,
        "september_cross_category_amp_pagination_qualified": False,
        "all_month_full_ledger_qualified": False,
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
    p.add_argument("--season", type=int, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--timeout", type=float, default=60.0)
    args = p.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.contract, season=args.season, timeout=args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "endpoints"}, indent=2, sort_keys=True))
    if not result["season_gate_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
