from __future__ import annotations

"""Validate research-only structured beat observations for LevLine 4.

The extraction layer is deliberately separated from forecasting. An observation may state a
point-in-time football fact or uncertainty state; it may not contain a pick, sentiment score,
edge, probability delta, model probability, recommendation, or any other direct forecast
adjustment.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "levline-structured-beat-observation-v1"

ALLOWED_OBSERVATION_TYPES = {
    "expected_starter",
    "expected_snap_role_tier",
    "position_change",
    "OL_combination",
    "return_to_full_role",
    "limited_role_expectation",
    "coach_confirmed_personnel_change",
    "scheme_or_personnel_usage_change",
    "uncertainty_state",
}

ALLOWED_ENTITY_TYPES = {"player", "coach", "unit", "team"}
ALLOWED_EXTRACTION_METHODS = {"deterministic", "manual_structured", "llm_fact_extraction"}
PROHIBITED_FORECAST_FIELDS = {
    "pick",
    "sentiment",
    "sentiment_score",
    "edge",
    "win_probability_delta",
    "probability_delta",
    "forecast_adjustment",
    "model_probability",
    "win_probability",
    "recommendation",
    "bet_recommendation",
}


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


def _sha256(value: Any, field: str) -> str:
    text = str(value or "").strip().lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{field} must be a 64-character lowercase hex digest")
    return text


def _confidence(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be numeric") from exc
    if not 0.0 <= out <= 1.0:
        raise ValueError("confidence must be between 0 and 1")
    return out


def _value_json(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("value_json is required")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("value_json must contain valid JSON") from exc
    else:
        parsed = value
    if parsed is None:
        raise ValueError("value_json cannot be null")
    return json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def validate_structured_observation(row: dict[str, Any]) -> dict[str, Any]:
    present_forbidden = [
        key for key in PROHIBITED_FORECAST_FIELDS if key in row and str(row.get(key) or "").strip()
    ]
    if present_forbidden:
        raise ValueError(f"forecast-effect fields are prohibited: {sorted(present_forbidden)}")

    observation_id = str(row.get("observation_id") or "").strip()
    game_id = str(row.get("game_id") or "").strip()
    team = str(row.get("team") or "").strip()
    if not observation_id or not game_id or not team:
        raise ValueError("observation_id, game_id, and team are required")

    observation_type = str(row.get("observation_type") or "").strip()
    if observation_type not in ALLOWED_OBSERVATION_TYPES:
        raise ValueError(f"unsupported observation_type: {observation_type!r}")

    entity_type = str(row.get("entity_type") or "").strip()
    entity_id = str(row.get("entity_id") or "").strip()
    if entity_type not in ALLOWED_ENTITY_TYPES or not entity_id:
        raise ValueError("valid entity_type and non-empty entity_id are required")

    source = str(row.get("source") or "").strip()
    source_url_or_id = str(row.get("source_url_or_id") or "").strip()
    raw_evidence_ref = str(row.get("raw_evidence_ref") or "").strip()
    if not source or not source_url_or_id or not raw_evidence_ref:
        raise ValueError("source, source_url_or_id, and raw_evidence_ref are required")
    raw_evidence_sha256 = _sha256(row.get("raw_evidence_sha256"), "raw_evidence_sha256")

    published_at = _parse_utc(row.get("published_at_utc"), "published_at_utc")
    captured_at = _parse_utc(row.get("captured_at_utc"), "captured_at_utc")
    forecast_asof = _parse_utc(row.get("forecast_asof_utc"), "forecast_asof_utc")
    kickoff = _parse_utc(row.get("kickoff_timestamp_utc"), "kickoff_timestamp_utc")
    if published_at > captured_at:
        raise ValueError("published_at_utc cannot be after captured_at_utc")
    if captured_at > forecast_asof:
        raise ValueError("captured_at_utc cannot be after forecast_asof_utc")
    if forecast_asof >= kickoff:
        raise ValueError("forecast_asof_utc must precede kickoff_timestamp_utc")

    extraction_method = str(row.get("extraction_method") or "").strip()
    extractor_id = str(row.get("extractor_id") or "").strip()
    extractor_version = str(row.get("extractor_version") or "").strip()
    if extraction_method not in ALLOWED_EXTRACTION_METHODS:
        raise ValueError(f"unsupported extraction_method: {extraction_method!r}")
    if not extractor_id or not extractor_version:
        raise ValueError("extractor_id and extractor_version are required")

    normalized_value_json = _value_json(row.get("value_json"))
    confidence = _confidence(row.get("confidence"))
    confidence_basis = str(row.get("confidence_basis") or "").strip()
    if not confidence_basis:
        raise ValueError("confidence_basis is required")

    source_priority = str(row.get("source_priority") or "").strip()
    if not source_priority:
        raise ValueError("source_priority is required")

    observation_payload = {
        "schema_version": SCHEMA_VERSION,
        "observation_id": observation_id,
        "game_id": game_id,
        "team": team,
        "observation_type": observation_type,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "value_json": normalized_value_json,
        "confidence": confidence,
        "confidence_basis": confidence_basis,
        "source_priority": source_priority,
        "source": source,
        "source_url_or_id": source_url_or_id,
        "raw_evidence_ref": raw_evidence_ref,
        "raw_evidence_sha256": raw_evidence_sha256,
        "published_at_utc": published_at.isoformat().replace("+00:00", "Z"),
        "captured_at_utc": captured_at.isoformat().replace("+00:00", "Z"),
        "forecast_asof_utc": forecast_asof.isoformat().replace("+00:00", "Z"),
        "kickoff_timestamp_utc": kickoff.isoformat().replace("+00:00", "Z"),
        "extraction_method": extraction_method,
        "extractor_id": extractor_id,
        "extractor_version": extractor_version,
        "research_only": True,
        "production_authorized": False,
        "probability_effect_authorized": False,
        "llm_directional_judgment_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    digest_basis = json.dumps(observation_payload, sort_keys=True, separators=(",", ":"))
    observation_payload["observation_sha256"] = hashlib.sha256(digest_basis.encode("utf-8")).hexdigest()
    return observation_payload


def validate_structured_observations(
    rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        validated = validate_structured_observation(dict(raw))
        observation_id = str(validated["observation_id"])
        if observation_id in seen:
            raise ValueError(f"duplicate observation_id: {observation_id}")
        seen.add(observation_id)
        output.append(validated)

    audit = {
        "schema_version": SCHEMA_VERSION,
        "rows": len(output),
        "observation_types": sorted({str(row["observation_type"]) for row in output}),
        "research_only": True,
        "production_authorized": False,
        "probability_effect_authorized": False,
        "llm_directional_judgment_authorized": False,
        "outcome_blind": True,
        "completed_2026_outcomes_used": 0,
    }
    return output, audit


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    rows, audit = validate_structured_observations(_read_csv(args.input))
    _write_jsonl(args.output, rows)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
