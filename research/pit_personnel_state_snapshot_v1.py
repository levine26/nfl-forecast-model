from __future__ import annotations

"""Build immutable point-in-time personnel-state snapshots from validated observations.

This is a research data reducer, not a forecasting model. It deliberately preserves categorical
football state and provenance without translating state into availability probabilities, starter
probabilities, role shares, win-probability deltas, picks, or production forecast changes.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

INPUT_SCHEMA_VERSION = "levline-structured-beat-observation-v1"
SNAPSHOT_SCHEMA_VERSION = "levline-pit-personnel-state-snapshot-v1"
CONTRACT_ID = "LEVLINE-4-PIT-PERSONNEL-STATE-V1"

STATE_KEY_FIELDS = (
    "game_id",
    "team",
    "entity_type",
    "entity_id",
    "observation_type",
)


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


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    # Match the upstream structured-observation digest exactly. In particular, leave
    # ensure_ascii at its json.dumps default (True) so Unicode text hashes identically.
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _verify_observation_integrity(row: dict[str, Any]) -> None:
    if row.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise ValueError(f"unsupported observation schema: {row.get('schema_version')!r}")
    if row.get("research_only") is not True:
        raise ValueError("input observation must be research_only=true")
    if row.get("production_authorized") is not False:
        raise ValueError("input observation violates production firewall")
    if row.get("probability_effect_authorized") is not False:
        raise ValueError("input observation violates probability-effect firewall")
    if row.get("llm_directional_judgment_authorized") is not False:
        raise ValueError("input observation violates LLM directional-judgment firewall")
    if int(row.get("completed_2026_outcomes_used", -1)) != 0:
        raise ValueError("input observation is not outcome-blind")

    expected = str(row.get("observation_sha256") or "").strip().lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError("input observation_sha256 is invalid")
    payload = dict(row)
    payload.pop("observation_sha256", None)
    actual = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    if actual != expected:
        raise ValueError("input observation_sha256 mismatch")

    try:
        json.loads(str(row.get("value_json") or ""))
    except json.JSONDecodeError as exc:
        raise ValueError("input observation value_json is invalid") from exc


def _state_key(row: dict[str, Any]) -> tuple[str, ...]:
    values = tuple(str(row.get(field) or "").strip() for field in STATE_KEY_FIELDS)
    if any(not value for value in values):
        raise ValueError(f"incomplete state key: {dict(zip(STATE_KEY_FIELDS, values))}")
    return values


def _rank(row: dict[str, Any]) -> tuple[datetime, datetime, datetime]:
    return (
        _parse_utc(row.get("forecast_asof_utc"), "forecast_asof_utc"),
        _parse_utc(row.get("captured_at_utc"), "captured_at_utc"),
        _parse_utc(row.get("published_at_utc"), "published_at_utc"),
    )


def _validate_row_chronology(row: dict[str, Any]) -> tuple[datetime, datetime, datetime, datetime]:
    published = _parse_utc(row.get("published_at_utc"), "published_at_utc")
    captured = _parse_utc(row.get("captured_at_utc"), "captured_at_utc")
    forecast_asof = _parse_utc(row.get("forecast_asof_utc"), "forecast_asof_utc")
    kickoff = _parse_utc(row.get("kickoff_timestamp_utc"), "kickoff_timestamp_utc")
    if published > captured:
        raise ValueError("published_at_utc cannot be after captured_at_utc")
    if captured > forecast_asof:
        raise ValueError("captured_at_utc cannot be after forecast_asof_utc")
    if forecast_asof >= kickoff:
        raise ValueError("forecast_asof_utc must precede kickoff_timestamp_utc")
    return published, captured, forecast_asof, kickoff


def build_personnel_state_snapshot(
    observations: Iterable[dict[str, Any]],
    *,
    game_id: str,
    snapshot_asof_utc: str | datetime,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    target_game = str(game_id or "").strip()
    if not target_game:
        raise ValueError("game_id is required")
    snapshot_asof = _parse_utc(snapshot_asof_utc, "snapshot_asof_utc")

    eligible: list[dict[str, Any]] = []
    future_excluded = 0
    other_game_excluded = 0
    kickoff_values: set[datetime] = set()

    for raw in observations:
        row = dict(raw)
        _verify_observation_integrity(row)
        _, _, observation_asof, kickoff = _validate_row_chronology(row)
        if str(row.get("game_id") or "").strip() != target_game:
            other_game_excluded += 1
            continue
        kickoff_values.add(kickoff)
        if snapshot_asof >= kickoff:
            raise ValueError("snapshot_asof_utc must precede kickoff_timestamp_utc")
        if observation_asof > snapshot_asof:
            future_excluded += 1
            continue
        eligible.append(row)

    if len(kickoff_values) > 1:
        raise ValueError("target game has inconsistent kickoff timestamps")

    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for row in eligible:
        grouped.setdefault(_state_key(row), []).append(row)

    state_rows: list[dict[str, Any]] = []
    superseded_total = 0
    coequal_support_total = 0

    for key in sorted(grouped):
        rows = grouped[key]
        best_rank = max(_rank(row) for row in rows)
        latest = [row for row in rows if _rank(row) == best_rank]
        values = {str(row.get("value_json") or "") for row in latest}
        if len(values) != 1:
            ids = sorted(str(row.get("observation_id") or "") for row in latest)
            raise ValueError(
                "coequal conflicting personnel observations fail closed for "
                f"state_key={key}: {ids}"
            )

        latest_sorted = sorted(latest, key=lambda row: str(row.get("observation_id") or ""))
        selected = latest_sorted[0]
        supporting_ids = [str(row.get("observation_id") or "") for row in latest_sorted]
        superseded_ids = sorted(
            str(row.get("observation_id") or "") for row in rows if row not in latest
        )
        superseded_total += len(superseded_ids)
        coequal_support_total += max(len(supporting_ids) - 1, 0)

        state_payload = {
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "contract_id": CONTRACT_ID,
            "snapshot_asof_utc": _iso(snapshot_asof),
            "game_id": key[0],
            "team": key[1],
            "entity_type": key[2],
            "entity_id": key[3],
            "observation_type": key[4],
            "value_json": selected["value_json"],
            "confidence": selected["confidence"],
            "confidence_basis": selected["confidence_basis"],
            "selected_observation_id": selected["observation_id"],
            "supporting_observation_ids": supporting_ids,
            "superseded_observation_ids": superseded_ids,
            "source_priority_recorded_not_adjudicated": selected["source_priority"],
            "source": selected["source"],
            "source_url_or_id": selected["source_url_or_id"],
            "raw_evidence_ref": selected["raw_evidence_ref"],
            "raw_evidence_sha256": selected["raw_evidence_sha256"],
            "published_at_utc": selected["published_at_utc"],
            "captured_at_utc": selected["captured_at_utc"],
            "observation_forecast_asof_utc": selected["forecast_asof_utc"],
            "kickoff_timestamp_utc": selected["kickoff_timestamp_utc"],
            "extraction_method": selected["extraction_method"],
            "extractor_id": selected["extractor_id"],
            "extractor_version": selected["extractor_version"],
            "research_only": True,
            "production_authorized": False,
            "probability_feature_authorized": False,
            "availability_probability_mapping_authorized": False,
            "starter_probability_mapping_authorized": False,
            "role_share_numeric_mapping_authorized": False,
            "complete_lineup_claim_authorized": False,
            "absence_of_observation_means_healthy": False,
            "completed_2026_outcomes_used": 0,
        }
        state_payload["state_row_sha256"] = hashlib.sha256(
            _canonical_json(state_payload).encode("utf-8")
        ).hexdigest()
        state_rows.append(state_payload)

    snapshot_digest_payload = [
        {key: value for key, value in row.items() if key != "state_row_sha256"}
        for row in state_rows
    ]
    snapshot_sha = hashlib.sha256(
        _canonical_json(snapshot_digest_payload).encode("utf-8")
    ).hexdigest()

    receipt = {
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "game_id": target_game,
        "snapshot_asof_utc": _iso(snapshot_asof),
        "state_rows": len(state_rows),
        "observed_entities": len({(row["team"], row["entity_type"], row["entity_id"]) for row in state_rows}),
        "eligible_observations": len(eligible),
        "future_observations_excluded": future_excluded,
        "other_game_observations_excluded": other_game_excluded,
        "superseded_observations": superseded_total,
        "coequal_supporting_observations": coequal_support_total,
        "snapshot_sha256": snapshot_sha,
        "snapshot_valid": True,
        "source_priority_used_for_adjudication": False,
        "absence_of_observation_means_healthy_or_active": False,
        "absence_of_observation_means_starter": False,
        "missing_state_imputation_used": False,
        "complete_lineup_claim_authorized": False,
        "availability_probability_mapping_authorized": False,
        "starter_probability_mapping_authorized": False,
        "role_share_numeric_mapping_authorized": False,
        "football_to_win_probability_mapping_authorized": False,
        "probability_feature_authorized": False,
        "production_authorized": False,
        "official_forecast_mutation_authorized": False,
        "outcome_blind": True,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }
    return state_rows, receipt


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL on line {line_no}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL line {line_no} must be an object")
        rows.append(value)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--game-id", required=True)
    parser.add_argument("--snapshot-asof-utc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    rows, receipt = build_personnel_state_snapshot(
        _read_jsonl(args.input),
        game_id=args.game_id,
        snapshot_asof_utc=args.snapshot_asof_utc,
    )
    _write_jsonl(args.output, rows)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
