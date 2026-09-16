from __future__ import annotations

"""Prospective external-provider GSIS identity source capture for LevLine 4.

This module captures Sleeper's public all-NFL-player catalog and writes a strict
identity-only projection. Raw bytes are preserved for provenance, but all downstream
identity work is required to consume the projection, which excludes team, status,
injury, practice, and depth-chart fields.
"""

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

CONTRACT_PATH = Path("research/levline4_2026_sleeper_gsis_identity_source_v1_contract.json")
DEFAULT_OUTPUT = Path("research_outputs/levline4_2026_sleeper_gsis_identity_source_v1")
GSIS_RE = re.compile(r"^00-[0-9]{7}$")
NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
USER_AGENT = "LevLine-Research/1.0 (+https://github.com/levine26/nfl-forecast-model)"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = NON_ALNUM_RE.sub(" ", text).strip()
    tokens = [token for token in text.split() if token]
    if tokens and tokens[-1] in SUFFIXES:
        tokens = tokens[:-1]
    return " ".join(tokens)


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    assert contract["contract_id"] == "LEVLINE-4-2026-SLEEPER-GSIS-IDENTITY-SOURCE-V1"
    assert contract["status"] == "PREREGISTERED_EXTERNAL_IDENTITY_SOURCE_CAPTURE_ONLY"
    assert contract["source"]["endpoint"] == "https://api.sleeper.app/v1/players/nfl"
    assert contract["projection"]["source_team_or_status_used_for_identity"] is False
    assert contract["source_capture_gate"]["post_result_threshold_relaxation_allowed"] is False
    assert contract["authority_if_capture_gate_passes"]["player_identity_to_gsis_qualified"] is False
    assert contract["authority_if_capture_gate_passes"]["production_authorized"] is False
    return contract


def fetch_source(
    *,
    get: Callable[..., object] = requests.get,
    endpoint: str = "https://api.sleeper.app/v1/players/nfl",
) -> tuple[bytes, int, dict[str, str]]:
    response = get(
        endpoint,
        allow_redirects=False,
        timeout=(10, 45),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        },
    )
    status = int(response.status_code)
    headers = {str(k): str(v) for k, v in response.headers.items()}
    return bytes(response.content), status, headers


def project_identity_catalog(raw: bytes, contract: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    parsed = json.loads(raw.decode("utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("Sleeper players payload must be a top-level JSON object")

    allowed = tuple(contract["projection"]["allowed_fields"])
    forbidden = set(contract["projection"]["forbidden_fields"])
    rows: list[dict[str, Any]] = []
    malformed_records = 0
    embedded_player_id_mismatches = 0
    canonical_source_objects = 0
    invalid_gsis_rows = 0
    missing_gsis_rows = 0

    for sleeper_id, value in parsed.items():
        if not isinstance(value, dict):
            malformed_records += 1
            continue
        embedded = str(value.get("player_id") or "").strip()
        if embedded and embedded != str(sleeper_id):
            embedded_player_id_mismatches += 1
        gsis = str(value.get("gsis_id") or "").strip()
        if not gsis:
            missing_gsis_rows += 1
            continue
        if not GSIS_RE.fullmatch(gsis):
            invalid_gsis_rows += 1
            continue
        canonical_source_objects += 1
        row = {
            "sleeper_player_id": str(sleeper_id),
            "gsis_id": gsis,
            "full_name": str(value.get("full_name") or "").strip(),
            "first_name": str(value.get("first_name") or "").strip(),
            "last_name": str(value.get("last_name") or "").strip(),
            "position": str(value.get("position") or "").strip(),
            "number": value.get("number"),
            "birth_date": str(value.get("birth_date") or "").strip(),
            "espn_id": value.get("espn_id"),
            "sportradar_id": str(value.get("sportradar_id") or "").strip(),
        }
        if tuple(row.keys()) != allowed:
            raise RuntimeError("projection field order/allowlist drift")
        if forbidden.intersection(row):
            raise RuntimeError("forbidden source field leaked into projection")
        rows.append(row)

    by_gsis: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_gsis[str(row["gsis_id"])].append(row)
    conflicting_gsis: list[dict[str, Any]] = []
    duplicate_gsis_groups = 0
    for gsis, group in sorted(by_gsis.items()):
        if len(group) <= 1:
            continue
        duplicate_gsis_groups += 1
        names = {
            normalize_name(row["full_name"] or f"{row['first_name']} {row['last_name']}")
            for row in group
            if normalize_name(row["full_name"] or f"{row['first_name']} {row['last_name']}")
        }
        if len(names) > 1:
            conflicting_gsis.append(
                {
                    "gsis_id": gsis,
                    "sleeper_player_ids": sorted(str(row["sleeper_player_id"]) for row in group),
                    "normalized_names": sorted(names),
                }
            )

    diagnostics = {
        "total_player_objects": len(parsed),
        "malformed_record_count": malformed_records,
        "embedded_player_id_mismatch_count": embedded_player_id_mismatches,
        "canonical_gsis_source_object_count": canonical_source_objects,
        "projection_row_count": len(rows),
        "missing_gsis_row_count": missing_gsis_rows,
        "invalid_gsis_row_count": invalid_gsis_rows,
        "duplicate_gsis_group_count": duplicate_gsis_groups,
        "duplicate_gsis_conflicting_name_count": len(conflicting_gsis),
        "duplicate_gsis_conflicting_name_examples": conflicting_gsis[:50],
        "projection_fields": list(allowed),
        "projection_contains_forbidden_fields": any(forbidden.intersection(row) for row in rows),
    }
    return sorted(rows, key=lambda row: (str(row["gsis_id"]), str(row["sleeper_player_id"]))), diagnostics


def run_capture(output_dir: Path = DEFAULT_OUTPUT, *, get: Callable[..., object] = requests.get) -> dict[str, Any]:
    contract = load_contract()
    output_dir.mkdir(parents=True, exist_ok=True)
    captured_at = utc_now()
    raw, status, headers = fetch_source(get=get, endpoint=contract["source"]["endpoint"])
    raw_sha = sha256_bytes(raw)
    (output_dir / f"raw-{raw_sha}.json").write_bytes(raw)

    projection_rows: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {
        "total_player_objects": 0,
        "malformed_record_count": 0,
        "embedded_player_id_mismatch_count": 0,
        "canonical_gsis_source_object_count": 0,
        "projection_row_count": 0,
        "missing_gsis_row_count": 0,
        "invalid_gsis_row_count": 0,
        "duplicate_gsis_group_count": 0,
        "duplicate_gsis_conflicting_name_count": 0,
        "duplicate_gsis_conflicting_name_examples": [],
        "projection_fields": list(contract["projection"]["allowed_fields"]),
        "projection_contains_forbidden_fields": False,
    }
    source_error = None
    if status == int(contract["source_capture_gate"]["http_status_required"]):
        try:
            projection_rows, diagnostics = project_identity_catalog(raw, contract)
        except Exception as exc:
            source_error = f"{type(exc).__name__}: {exc}"
    else:
        source_error = f"http_status_not_required_value:{status}"

    projection_path = output_dir / "identity_projection.jsonl"
    with projection_path.open("w", encoding="utf-8") as handle:
        for row in projection_rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    projection_sha = sha256_bytes(projection_path.read_bytes())

    gate = contract["source_capture_gate"]
    capture_gate_pass = (
        status == int(gate["http_status_required"])
        and source_error is None
        and int(diagnostics["total_player_objects"]) >= int(gate["minimum_total_player_objects"])
        and int(diagnostics["projection_row_count"]) >= int(gate["minimum_canonical_gsis_rows"])
        and int(diagnostics["duplicate_gsis_conflicting_name_count"]) == 0
        and diagnostics["projection_contains_forbidden_fields"] is False
    )

    receipt = {
        "schema_version": "levline4-2026-sleeper-gsis-identity-source-v1",
        "contract_id": contract["contract_id"],
        "status": "PASS" if capture_gate_pass else "FAIL",
        "captured_at_utc": captured_at,
        "endpoint": contract["source"]["endpoint"],
        "http_status": status,
        "content_type": headers.get("Content-Type") or headers.get("content-type") or "",
        "raw_source_sha256": raw_sha,
        "raw_source_bytes": len(raw),
        "projection_sha256": projection_sha,
        "projection_bytes": projection_path.stat().st_size,
        **diagnostics,
        "source_error": source_error,
        "capture_gate_pass": capture_gate_pass,
        "sleeper_external_identity_source_capture_qualified": capture_gate_pass,
        "sleeper_is_treated_as_a_separate_publisher_from_nflverse": True,
        "statistical_independence_of_underlying_provider_data_proven": False,
        "player_identity_to_gsis_qualified": False,
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
        "f_st_01_frozen_2026_unchanged": True,
    }
    (output_dir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = run_capture(args.output_dir)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
