from __future__ import annotations

"""Derive prospective LevLine 4 market-path diagnostics from strict PIT market state.

This module is research-only and outcome-blind. It consumes the already-qualified four-horizon
market-state derivative and summarizes path geometry without changing a forecast. Missing
horizons stay missing: a path is computed only when all T-120/T-60/T-45/T-30 probabilities
exist for the same event identity under the upstream strict-PIT contract.
"""

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable

HORIZON_FIELDS = (
    "market_home_prob_t120",
    "market_home_prob_t60",
    "market_home_prob_t45",
    "market_home_prob_t30",
)
ADJACENT_LABELS = ("t60_minus_t120", "t45_minus_t60", "t30_minus_t45")
EPS = 1e-12


def _float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _sign(value: float, *, eps: float = EPS) -> int:
    if value > eps:
        return 1
    if value < -eps:
        return -1
    return 0


def _reversal_count(deltas: list[float]) -> int:
    nonzero = [_sign(delta) for delta in deltas if _sign(delta) != 0]
    return sum(int(left != right) for left, right in zip(nonzero, nonzero[1:]))


def derive_market_path_row(row: dict[str, Any]) -> dict[str, Any]:
    probs = [_float(row.get(field)) for field in HORIZON_FIELDS]
    complete = all(value is not None and 0.0 < value < 1.0 for value in probs)
    base = {
        "game_id": row.get("game_id"),
        "event_id": row.get("event_id"),
        "home_team": row.get("home_team"),
        "away_team": row.get("away_team"),
        "kickoff_timestamp_utc": row.get("kickoff_timestamp_utc"),
        "complete_four_horizon_path": bool(complete),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    if not complete:
        return {
            **base,
            "net_move_pp_t30_minus_t120": None,
            "total_variation_pp": None,
            "path_efficiency": None,
            "reversal_count": None,
            "late_reversal": None,
            "max_excursion_pp": None,
            "largest_adjacent_move_pp": None,
            "adjacent_sign_pattern": None,
            "acceleration_pp": None,
        }

    values = [float(value) for value in probs]  # type: ignore[arg-type]
    deltas = [values[i + 1] - values[i] for i in range(3)]
    net = values[-1] - values[0]
    total_variation = sum(abs(delta) for delta in deltas)
    signs = [_sign(delta) for delta in deltas]
    reversal_count = _reversal_count(deltas)
    earlier_nonzero = next((sign for sign in reversed(signs[:-1]) if sign != 0), 0)
    late_sign = signs[-1]
    late_reversal = bool(earlier_nonzero and late_sign and earlier_nonzero != late_sign)
    path_efficiency = abs(net) / total_variation if total_variation > EPS else 1.0
    acceleration = abs(deltas[-1]) - abs(deltas[-2])

    output = {
        **base,
        "net_move_pp_t30_minus_t120": net * 100.0,
        "total_variation_pp": total_variation * 100.0,
        "path_efficiency": path_efficiency,
        "reversal_count": int(reversal_count),
        "late_reversal": late_reversal,
        "max_excursion_pp": (max(values) - min(values)) * 100.0,
        "largest_adjacent_move_pp": max(abs(delta) for delta in deltas) * 100.0,
        "adjacent_sign_pattern": "|".join(str(sign) for sign in signs),
        "acceleration_pp": acceleration * 100.0,
    }
    for label, delta in zip(ADJACENT_LABELS, deltas):
        output[f"home_probability_pp_{label}"] = delta * 100.0
    return output


def derive_market_paths(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    output = [derive_market_path_row(dict(row)) for row in rows]
    complete = [row for row in output if row["complete_four_horizon_path"]]
    audit = {
        "schema_version": "levline-market-path-state-v1",
        "rows": len(output),
        "complete_four_horizon_paths": len(complete),
        "incomplete_paths": len(output) - len(complete),
        "feature_family": [
            "adjacent_probability_moves",
            "net_move",
            "total_variation",
            "path_efficiency",
            "reversal_count",
            "late_reversal",
            "max_excursion",
            "largest_adjacent_move",
            "acceleration",
        ],
        "missingness_policy": "preserve_missing_no_imputation",
        "upstream_requirement": "strict market_state_v1 four-horizon event identity",
        "outcome_blind": True,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
        "promotion_authorized": False,
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
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--market-state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    rows, audit = derive_market_paths(_read_csv(args.market_state))
    _write_csv(args.output, rows)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
