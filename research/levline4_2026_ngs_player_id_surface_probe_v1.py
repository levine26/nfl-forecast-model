from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

CONTRACT_PATH = Path("research/levline4_2026_ngs_player_id_surface_probe_v1_contract.json")
DEFAULT_OUTPUT = Path("research_outputs/levline4_2026_ngs_player_id_surface_probe_v1")
GSIS_RE = re.compile(r"\b00-[0-9]{7}\b")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_nfl_https_url(value: str) -> bool:
    parsed = urlparse(str(value or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme == "https" and (host == "nfl.com" or host.endswith(".nfl.com"))


def extract_gsis_values(text: str) -> list[str]:
    return sorted(set(GSIS_RE.findall(str(text or ""))))


def json_key_paths(value: Any, prefix: str = "") -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            part = str(key)
            path = f"{prefix}.{part}" if prefix else part
            out.add(path)
            out.update(json_key_paths(child, path))
    elif isinstance(value, list):
        path = f"{prefix}[]" if prefix else "[]"
        out.add(path)
        for child in value[:25]:
            out.update(json_key_paths(child, path))
    return out


def load_contract(path: Path = CONTRACT_PATH) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "LEVLINE-4-2026-NGS-PLAYER-ID-SURFACE-PROBE-V1"
    assert contract["status"] == "PREREGISTERED_DISCOVERY_CAPTURE_ONLY"
    assert contract["frozen_discovery_queries"] == ["Patrick Mahomes", "Josh Allen", "Justin Jefferson"]
    assert contract["browser_capture"]["no_week2_inactive_names_may_be_added_to_v1"] is True
    assert contract["authority"]["ngs_name_to_gsis_parser_qualified"] is False
    assert contract["authority"]["production_authorized"] is False
    return contract


def _table_headers(page) -> list[list[str]]:
    vectors: list[list[str]] = []
    tables = page.locator("table")
    for idx in range(tables.count()):
        headers = [" ".join(x.split()).strip() for x in tables.nth(idx).locator("th").all_text_contents()]
        if headers:
            vectors.append(headers)
    return vectors


def run_probe(output_dir: Path = DEFAULT_OUTPUT) -> dict:
    # Lazy import keeps deterministic helper tests independent of browser installation.
    from playwright.sync_api import sync_playwright

    contract = load_contract()
    page_url = contract["source"]["page_url"]
    queries = list(contract["frozen_discovery_queries"])
    placeholder = contract["browser_capture"]["query_input_placeholder_exact"]

    output_dir.mkdir(parents=True, exist_ok=True)
    dom_dir = output_dir / "dom"
    network_body_dir = output_dir / "network_json"
    dom_dir.mkdir(parents=True, exist_ok=True)
    network_body_dir.mkdir(parents=True, exist_ok=True)

    network: list[dict] = []
    query_diagnostics: list[dict] = []
    errors: list[dict] = []
    current_context = {"query": "INITIAL_PAGE"}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="LevLine-Research/1.0 (+https://github.com/levine26/nfl-forecast-model)",
            locale="en-US",
        )
        page = context.new_page()

        def on_response(response):
            if not is_nfl_https_url(response.url):
                return
            content_type = str(response.headers.get("content-type", ""))
            record = {
                "ordinal": len(network),
                "query_context": current_context["query"],
                "url": response.url,
                "status": int(response.status),
                "content_type": content_type,
                "captured_at_utc": utc_now(),
                "body_sha256": None,
                "body_bytes": None,
                "json_body_relpath": None,
                "json_parse_ok": None,
                "json_key_paths": [],
            }
            if "json" in content_type.lower():
                try:
                    body = response.body()
                    record["body_sha256"] = sha256_bytes(body)
                    record["body_bytes"] = len(body)
                    rel = Path("network_json") / f"response_{len(network):04d}.json"
                    (output_dir / rel).write_bytes(body)
                    record["json_body_relpath"] = rel.as_posix()
                    try:
                        parsed = json.loads(body)
                        record["json_parse_ok"] = True
                        record["json_key_paths"] = sorted(json_key_paths(parsed))
                    except Exception:
                        record["json_parse_ok"] = False
                except Exception as exc:
                    record["body_capture_error"] = f"{type(exc).__name__}: {exc}"
            network.append(record)

        page.on("response", on_response)
        page_loaded = False
        initial_input_count = 0
        initial_search_button_count = 0
        try:
            page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(1500)
            page_loaded = True
            initial_dom = page.content().encode("utf-8")
            (dom_dir / "initial.html").write_bytes(initial_dom)
            input_locator = page.get_by_placeholder(placeholder, exact=True)
            initial_input_count = input_locator.count()
            search_buttons = page.locator("button").filter(has_text=re.compile(r"search", re.IGNORECASE))
            initial_search_button_count = search_buttons.count()

            for ordinal, query in enumerate(queries, start=1):
                current_context["query"] = query
                start_network = len(network)
                try:
                    if input_locator.count() != 1:
                        raise RuntimeError(f"expected exactly one name query input, found {input_locator.count()}")
                    input_locator.fill(query)
                    search_buttons = page.locator("button").filter(has_text=re.compile(r"search", re.IGNORECASE))
                    action = "click_first_search_button"
                    if search_buttons.count() >= 1:
                        search_buttons.first.click(timeout=10_000)
                    else:
                        action = "press_enter_fallback"
                        input_locator.press("Enter")
                    page.wait_for_timeout(2000)
                    dom = page.content().encode("utf-8")
                    (dom_dir / f"query_{ordinal}.html").write_bytes(dom)
                    visible_text = page.locator("body").inner_text(timeout=10_000)
                    gsis_values = extract_gsis_values(visible_text)
                    query_diagnostics.append({
                        "query_ordinal": ordinal,
                        "query": query,
                        "action": action,
                        "action_completed": True,
                        "post_query_dom_sha256": sha256_bytes(dom),
                        "post_query_dom_bytes": len(dom),
                        "query_text_visible": query.casefold() in visible_text.casefold(),
                        "visible_gsis_values": gsis_values,
                        "visible_gsis_count": len(gsis_values),
                        "table_header_vectors": _table_headers(page),
                        "nfl_domain_responses_during_query": len(network) - start_network,
                    })
                except Exception as exc:
                    errors.append({
                        "query": query,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    })
                    query_diagnostics.append({
                        "query_ordinal": ordinal,
                        "query": query,
                        "action_completed": False,
                        "visible_gsis_values": [],
                        "visible_gsis_count": 0,
                        "table_header_vectors": [],
                        "nfl_domain_responses_during_query": len(network) - start_network,
                    })
            current_context["query"] = "AFTER_QUERIES"
        except Exception as exc:
            errors.append({"query": "INITIAL_PAGE", "error_type": type(exc).__name__, "error": str(exc)})
        finally:
            browser.close()

    (output_dir / "query_diagnostics.json").write_text(
        json.dumps(query_diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "network_responses.json").write_text(
        json.dumps(network, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    executed = sum(1 for row in query_diagnostics if row.get("action_completed") is True)
    json_responses = [row for row in network if row.get("json_body_relpath")]
    complete = page_loaded and executed == len(queries) and not errors
    receipt = {
        "schema_version": "levline4-2026-ngs-player-id-surface-probe-v1",
        "contract_id": contract["contract_id"],
        "status": "PASS" if complete else "FAIL",
        "captured_at_utc": utc_now(),
        "page_url": page_url,
        "page_loaded": page_loaded,
        "fixed_query_count": len(queries),
        "queries_action_completed": executed,
        "initial_query_input_count": initial_input_count,
        "initial_search_button_count": initial_search_button_count,
        "nfl_domain_response_count": len(network),
        "json_response_count": len(json_responses),
        "queries_with_visible_gsis_pattern": sum(1 for row in query_diagnostics if row.get("visible_gsis_count", 0) > 0),
        "ngs_surface_capture_qualified": complete,
        "ngs_backend_endpoint_qualified": False,
        "ngs_name_to_gsis_parser_qualified": False,
        "week2_sunday_due_inactive_player_identity_to_gsis_qualified": False,
        "general_2026_player_identity_to_gsis_qualified": False,
        "game_day_membership_qualified": False,
        "availability_state_authorized": False,
        "player_value_join_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used_for_design_or_selection": 0,
        "postgame_participation_used": False,
        "week2_inactive_execution_evidence_used_for_design": False,
        "f_st_01_frozen_2026_unchanged": True,
        "errors": errors,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_probe(args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
