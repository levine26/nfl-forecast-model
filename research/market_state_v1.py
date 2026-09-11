from __future__ import annotations

"""Derive point-in-time market-state features from the v2 research capture ledger.

The derivative is descriptive research/UX state only. It never changes the frozen
production forecast. Missing horizons remain missing; retries are resolved only by the
closest qualifying consensus request to the preregistered target timestamp.
"""

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from research.market_capture_v2 import CAPTURE_TOLERANCE_MINUTES, HORIZONS, logit
from research.market_capture_contract_v2 import MIN_CONSENSUS_BOOKS

HORIZON_ORDER = ("T-120m", "T-60m", "T-30m")
PAIR_DEFINITIONS = (
    ("t60_minus_t120", "T-60m", "T-120m"),
    ("t30_minus_t120", "T-30m", "T-120m"),
    ("t30_minus_t60", "T-30m", "T-60m"),
)
IDENTITY_FIELDS = (
    "event_id",
    "provider_commence_time_utc",
    "home_team",
    "away_team",
    "kickoff_timestamp_utc",
)


def _float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _int(value: Any) -> int | None:
    parsed = _float(value)
    if parsed is None or not parsed.is_integer():
        return None
    return int(parsed)


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _parse_utc(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _qualifying_consensus(row: dict[str, Any]) -> bool:
    if str(row.get("row_type")) != "consensus":
        return False
    if str(row.get("horizon")) not in HORIZONS:
        return False
    source_count = _int(row.get("source_count"))
    if source_count is None or source_count < MIN_CONSENSUS_BOOKS:
        return False
    probability = _float(row.get("h2h_home_no_vig"))
    if probability is None or not 0.0 < probability < 1.0:
        return False
    timing_error = _float(row.get("timing_error_minutes"))
    if timing_error is None or abs(timing_error) > CAPTURE_TOLERANCE_MINUTES:
        return False
    if not _truthy(row.get("research_only")) or _truthy(row.get("production_authorized")):
        return False
    target = _parse_utc(row.get("target_timestamp_utc"))
    request = _parse_utc(row.get("request_timestamp_utc"))
    kickoff = _parse_utc(row.get("kickoff_timestamp_utc"))
    if target is None or request is None or kickoff is None or request >= kickoff:
        return False
    return True


def _choose_horizon(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot select from empty horizon rows")
    identities = {tuple(str(row.get(field) or "") for field in IDENTITY_FIELDS) for row in rows}
    if len(identities) != 1:
        raise ValueError("market consensus retries disagree on event identity")
    return sorted(
        rows,
        key=lambda row: (
            abs(float(row["timing_error_minutes"])),
            _parse_utc(row.get("request_timestamp_utc")) or datetime.max.replace(tzinfo=timezone.utc),
        ),
    )[0]


def select_consensus_horizons(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        if not _qualifying_consensus(row):
            continue
        game_id = str(row.get("game_id") or "").strip()
        horizon = str(row.get("horizon") or "")
        if not game_id:
            continue
        grouped.setdefault(game_id, {}).setdefault(horizon, []).append(dict(row))

    selected: dict[str, dict[str, dict[str, Any]]] = {}
    for game_id, horizons in grouped.items():
        selected[game_id] = {
            horizon: _choose_horizon(candidates)
            for horizon, candidates in horizons.items()
        }
    return selected


def _difference(
    rows: dict[str, dict[str, Any]],
    newer: str,
    older: str,
    field: str,
) -> float | None:
    if newer not in rows or older not in rows:
        return None
    left = _float(rows[newer].get(field))
    right = _float(rows[older].get(field))
    if left is None or right is None:
        return None
    return left - right


def _logit_difference(
    rows: dict[str, dict[str, Any]],
    newer: str,
    older: str,
) -> float | None:
    if newer not in rows or older not in rows:
        return None
    left = _float(rows[newer].get("h2h_home_no_vig"))
    right = _float(rows[older].get("h2h_home_no_vig"))
    if left is None or right is None or not (0 < left < 1 and 0 < right < 1):
        return None
    return logit(left) - logit(right)


def _assert_cross_horizon_identity(game_id: str, rows: dict[str, dict[str, Any]]) -> None:
    identities = {
        tuple(str(row.get(field) or "") for field in IDENTITY_FIELDS)
        for row in rows.values()
    }
    if len(identities) > 1:
        raise ValueError(f"market horizons disagree on event identity for {game_id}")


def build_market_state(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    selected = select_consensus_horizons(rows)
    output: list[dict[str, Any]] = []
    complete_games = 0
    for game_id in sorted(selected):
        horizons = selected[game_id]
        _assert_cross_horizon_identity(game_id, horizons)
        available = [horizon for horizon in HORIZON_ORDER if horizon in horizons]
        missing = [horizon for horizon in HORIZON_ORDER if horizon not in horizons]
        if not missing:
            complete_games += 1
        template = horizons[available[0]]
        record: dict[str, Any] = {
            "game_id": game_id,
            "event_id": template.get("event_id"),
            "provider_commence_time_utc": template.get("provider_commence_time_utc"),
            "home_team": template.get("home_team"),
            "away_team": template.get("away_team"),
            "kickoff_timestamp_utc": template.get("kickoff_timestamp_utc"),
            "available_horizons": available,
            "missing_horizons": missing,
            "complete_horizons": not missing,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        for horizon in HORIZON_ORDER:
            suffix = horizon.lower().replace("-", "").replace("m", "")
            row = horizons.get(horizon)
            record[f"market_home_prob_{suffix}"] = _float(row.get("h2h_home_no_vig")) if row else None
            record[f"home_spread_{suffix}"] = _float(row.get("home_spread")) if row else None
            record[f"total_points_{suffix}"] = _float(row.get("total_points")) if row else None
            record[f"probability_range_{suffix}"] = _float(row.get("probability_range")) if row else None
            record[f"source_count_{suffix}"] = _int(row.get("source_count")) if row else None
            record[f"max_freshness_minutes_{suffix}"] = _float(row.get("max_freshness_minutes")) if row else None
            record[f"request_timestamp_utc_{suffix}"] = row.get("request_timestamp_utc") if row else None
            record[f"timing_error_minutes_{suffix}"] = _float(row.get("timing_error_minutes")) if row else None

        for label, newer, older in PAIR_DEFINITIONS:
            prob = _difference(horizons, newer, older, "h2h_home_no_vig")
            record[f"home_probability_{label}"] = prob
            record[f"home_probability_pp_{label}"] = prob * 100.0 if prob is not None else None
            record[f"home_logit_{label}"] = _logit_difference(horizons, newer, older)
            record[f"home_spread_{label}"] = _difference(horizons, newer, older, "home_spread")
            record[f"total_points_{label}"] = _difference(horizons, newer, older, "total_points")
            record[f"probability_range_{label}"] = _difference(horizons, newer, older, "probability_range")
        output.append(record)

    audit = {
        "schema_version": "levline-market-state-v1",
        "games_with_any_qualifying_horizon": len(output),
        "games_with_all_three_horizons": complete_games,
        "games_with_missing_horizons": len(output) - complete_games,
        "minimum_consensus_books": MIN_CONSENSUS_BOOKS,
        "capture_tolerance_minutes": CAPTURE_TOLERANCE_MINUTES,
        "horizons": list(HORIZON_ORDER),
        "missingness_policy": "preserve_missing_no_imputation",
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    return output, audit


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serial = dict(row)
            serial["available_horizons"] = "|".join(row["available_horizons"])
            serial["missing_horizons"] = "|".join(row["missing_horizons"])
            writer.writerow(serial)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    states, audit = build_market_state(_read_csv(args.ledger))
    _write_csv(args.output, states)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
