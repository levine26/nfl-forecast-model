from __future__ import annotations

"""Descriptive forward audit of Props personnel/opportunity evidence coverage.

This is an instrumentation lane, not a forecast model. It measures whether prospective
Props 2.1 receipts carry usable role, availability, workload, opportunity and evidence
provenance while enforcing pregame chronology. It does not fit, exclude, reweight or
alter any forecast.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd


class PersonnelCoverageError(RuntimeError):
    pass


UNKNOWN = {"", "UNKNOWN", "UNAVAILABLE", "NONE", "NULL"}


def read_receipts(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict) or not isinstance(value.get("forecast"), dict):
                raise PersonnelCoverageError(f"{path}:{line_no}: invalid prospective receipt")
            rows.append(value)
    if not rows:
        raise PersonnelCoverageError("no receipts found")
    return rows


def _known(value: Any) -> bool:
    return str(value or "").strip().upper() not in UNKNOWN


def _chronology_ok(forecast: Mapping[str, Any]) -> bool:
    forecast_time = pd.to_datetime(forecast.get("forecast_timestamp_utc"), utc=True, errors="coerce")
    kickoff = pd.to_datetime(forecast.get("kickoff_utc"), utc=True, errors="coerce")
    horizon = pd.to_datetime(
        (forecast.get("provenance") or {}).get("source_data_horizon_utc"),
        utc=True,
        errors="coerce",
    )
    return bool(
        pd.notna(forecast_time)
        and pd.notna(kickoff)
        and pd.notna(horizon)
        and horizon <= forecast_time < kickoff
    )


def receipt_row(receipt: Mapping[str, Any]) -> dict[str, Any]:
    forecast = receipt.get("forecast")
    if not isinstance(forecast, Mapping):
        raise PersonnelCoverageError("receipt forecast is missing")
    role = forecast.get("role_state")
    if not isinstance(role, Mapping):
        role = {}
    opportunity = forecast.get("opportunity_state")
    if not isinstance(opportunity, Mapping):
        opportunity = {}
    evidence_ids = role.get("evidence_ids")
    if not isinstance(evidence_ids, list):
        evidence_ids = []

    opportunity_fields = ("pass_attempts", "carries", "targets", "routes", "total_opportunities")
    opportunity_known = any(opportunity.get(key) is not None for key in opportunity_fields)

    return {
        "forecast_id": forecast.get("forecast_id"),
        "game_id": forecast.get("game_id"),
        "player_id": forecast.get("player_id"),
        "position": forecast.get("position"),
        "prop_type": forecast.get("prop_type"),
        "role_state": role.get("state"),
        "availability_state": role.get("availability"),
        "workload_state": role.get("workload"),
        "role_known": _known(role.get("state")),
        "availability_known": _known(role.get("availability")),
        "workload_known": _known(role.get("workload")),
        "evidence_present": bool(evidence_ids),
        "evidence_count": len(evidence_ids),
        "opportunity_known": opportunity_known,
        "chronology_ok": _chronology_ok(forecast),
    }


def audit(receipts: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], pd.DataFrame]:
    frame = pd.DataFrame([receipt_row(row) for row in receipts])
    if frame.empty:
        raise PersonnelCoverageError("no receipt rows to audit")
    if not frame["chronology_ok"].all():
        bad = frame.loc[~frame["chronology_ok"], "forecast_id"].astype(str).tolist()
        raise PersonnelCoverageError(f"non-pregame receipt chronology detected: {bad[:10]}")

    dimensions = [
        "role_known",
        "availability_known",
        "workload_known",
        "evidence_present",
        "opportunity_known",
    ]
    summary = {
        "contract": "props-personnel-coverage-audit-v1",
        "descriptive_only": True,
        "forecast_mutation_authorized": False,
        "receipt_count": int(len(frame)),
        "unique_games": int(frame["game_id"].nunique()),
        "unique_players": int(frame["player_id"].nunique()),
        "coverage": {
            key: {
                "count": int(frame[key].sum()),
                "rate": float(frame[key].mean()),
            }
            for key in dimensions
        },
    }

    grouped_rows: list[dict[str, Any]] = []
    for grouping in ("position", "prop_type"):
        for value, group in frame.groupby(grouping, dropna=False):
            row = {
                "grouping": grouping,
                "group": str(value),
                "n": int(len(group)),
            }
            for key in dimensions:
                row[f"{key}_rate"] = float(group[key].mean())
            grouped_rows.append(row)
    grouped = pd.DataFrame(grouped_rows)
    return summary, grouped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    summary, grouped = audit(read_receipts(args.receipts))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    grouped.to_csv(args.output_dir / "coverage_by_group.csv", index=False)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
