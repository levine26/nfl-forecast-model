from __future__ import annotations

"""Prospective rendered inactive-name -> GSIS resolver candidate for LevLine 4.

This is a deterministic research resolver only. It is intentionally unable to infer roster
membership, health, availability probability, role, player value, or forecast effect. It may
run only on observations known on/after the frozen 2026 identity-source capture time.
"""

import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import polars as pl

CONTRACT_ID = "LEVLINE-2026-PROSPECTIVE-INACTIVE-GSIS-RESOLVER-V1"
SOURCE_KNOWN_BY = datetime.fromisoformat("2026-09-16T12:35:57+00:00")
SOURCE_PROJECTION_SHA256 = "fc993e0543950222cd20e0c29e457980da572d100bebff6a5d4bf5f7b72b051f"
SOURCE_FIELDS = (
    "season",
    "game_type",
    "week",
    "team",
    "gsis_id",
    "jersey_number",
    "first_name",
    "football_name",
    "last_name",
)
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")


def _parse_utc(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"missing required timestamp: {field}")
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid ISO timestamp for {field}: {text}") from exc
    if dt.tzinfo is None:
        raise ValueError(f"timestamp must be timezone-aware: {field}")
    return dt.astimezone(timezone.utc)


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = NON_ALNUM_RE.sub(" ", text).strip()
    tokens = [token for token in text.split() if token]
    if tokens and tokens[-1] in SUFFIXES:
        tokens = tokens[:-1]
    return " ".join(tokens)


def normalize_team(value: Any) -> str:
    return str(value or "").strip().upper()


def _alias(first: Any, last: Any) -> str:
    return normalize_name(f"{str(first or '').strip()} {str(last or '').strip()}")


def build_identity_index(frame: pl.DataFrame) -> dict[tuple[int, str, str], set[str]]:
    if tuple(frame.columns) != SOURCE_FIELDS:
        raise RuntimeError("identity projection fields do not match frozen source contract")
    out: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    for row in frame.to_dicts():
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        if int(row.get("season") or -1) != 2026 or str(row.get("game_type") or "") != "REG":
            continue
        team = normalize_team(row.get("team"))
        gsis = str(row.get("gsis_id") or "").strip()
        if not team or not gsis:
            continue
        aliases = {
            _alias(row.get("first_name"), row.get("last_name")),
            _alias(row.get("football_name"), row.get("last_name")),
        }
        for alias in aliases:
            if alias:
                out[(week, team, alias)].add(gsis)
    return out


def resolve_observation(
    row: dict[str, Any],
    *,
    identity_index: dict[tuple[int, str, str], set[str]],
) -> dict[str, Any]:
    observation_id = str(row.get("observation_id") or "").strip()
    team = normalize_team(row.get("team"))
    rendered = str(row.get("player_name_rendered") or "").strip()
    raw_sha = str(row.get("raw_evidence_sha256") or "").strip().lower()
    if not observation_id or not team or not rendered:
        raise ValueError("observation_id, team, and player_name_rendered are required")
    if len(raw_sha) != 64 or any(ch not in "0123456789abcdef" for ch in raw_sha):
        raise ValueError("raw_evidence_sha256 must be a lowercase 64-character hex digest")
    try:
        week = int(row.get("week"))
    except (TypeError, ValueError) as exc:
        raise ValueError("week must be an integer") from exc
    if week <= 1:
        raise ValueError("Week 1 retrospective identity resolution is forbidden by contract")

    known_by = _parse_utc(row.get("source_known_by_utc"), "source_known_by_utc")
    if known_by < SOURCE_KNOWN_BY:
        raise ValueError("observation predates frozen prospective identity source")

    normalized = normalize_name(rendered)
    candidates = sorted(identity_index.get((week, team, normalized), set()))
    if len(candidates) == 1:
        state = "RESOLVED_EXACT_UNIQUE"
        resolved = candidates[0]
    elif len(candidates) == 0:
        state = "UNRESOLVED"
        resolved = None
    else:
        state = "AMBIGUOUS"
        resolved = None

    return {
        "schema_version": "levline-2026-prospective-inactive-gsis-resolver-v1",
        "contract_id": CONTRACT_ID,
        "observation_id": observation_id,
        "week": week,
        "team": team,
        "player_name_rendered": rendered,
        "normalized_name": normalized,
        "source_known_by_utc": known_by.isoformat().replace("+00:00", "Z"),
        "raw_evidence_sha256": raw_sha,
        "resolution_state": state,
        "candidate_gsis_ids": candidates,
        "resolved_gsis_id": resolved,
        "resolution_basis": "same_week_team_exact_normalized_full_name_unique" if resolved else None,
        "position_used": False,
        "jersey_number_used": False,
        "status_used": False,
        "fuzzy_matching_used": False,
        "phonetic_matching_used": False,
        "manual_override_used": False,
        "player_identity_to_gsis_qualified": False,
        "player_value_join_authorized": False,
        "availability_probability_feature_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }


def resolve_observations(
    rows: Iterable[dict[str, Any]],
    *,
    projection_path: Path,
    expected_projection_sha256: str = SOURCE_PROJECTION_SHA256,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    projection_raw = projection_path.read_bytes()
    observed_sha = hashlib.sha256(projection_raw).hexdigest()
    if observed_sha != expected_projection_sha256:
        raise RuntimeError(
            f"identity projection sha256 mismatch: {observed_sha} != {expected_projection_sha256}"
        )
    frame = pl.read_parquet(projection_path)
    index = build_identity_index(frame)
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        resolved = resolve_observation(dict(row), identity_index=index)
        observation_id = str(resolved["observation_id"])
        if observation_id in seen:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        seen.add(observation_id)
        output.append(resolved)

    counts = {state: 0 for state in ("RESOLVED_EXACT_UNIQUE", "UNRESOLVED", "AMBIGUOUS")}
    for row in output:
        counts[str(row["resolution_state"])] += 1
    receipt = {
        "schema_version": "levline-2026-prospective-inactive-gsis-resolver-v1-execution",
        "contract_id": CONTRACT_ID,
        "source_projection_sha256": observed_sha,
        "rows": len(output),
        "resolution_counts": counts,
        "real_execution_is_self_qualifying": False,
        "player_identity_to_gsis_qualified": False,
        "player_value_join_authorized": False,
        "game_day_membership_qualified": False,
        "availability_probability_feature_authorized": False,
        "forecast_probability_effect_authorized": False,
        "model_fit_authorized": False,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    return output, receipt


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("contract_id") != CONTRACT_ID:
        raise ValueError("unexpected resolver contract_id")
    dep = contract.get("dependency") or {}
    if dep.get("source_projection_sha256") != SOURCE_PROJECTION_SHA256:
        raise ValueError("source projection SHA drifted")
    if tuple(dep.get("source_fields") or ()) != SOURCE_FIELDS:
        raise ValueError("source fields drifted")
    if dep.get("status_fields_available_to_resolver") is not False:
        raise ValueError("resolver may not access status fields")
    return contract
