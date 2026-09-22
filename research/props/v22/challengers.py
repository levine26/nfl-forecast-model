from __future__ import annotations

"""Deterministic, outcome-free Props 2.2 challenger transformations.

Research-only implementation of the coefficients frozen in CHALLENGER_GRID.json.
It consumes already-frozen Props 2.1 prospective rows, never reads outcomes, never
fits parameters, never changes LevLine/F-ST, and never publishes production artifacts.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

GRID_PATH = Path(__file__).with_name("CHALLENGER_GRID.json")


class Props22Error(RuntimeError):
    pass


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and abs(out) != float("inf") else None


def _timestamp(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def load_grid(path: Path = GRID_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise Props22Error("Props 2.2 challenger grid must be a JSON object")
    if payload.get("contract_version") != "levline-props-2.2-prereg-v0.2":
        raise Props22Error("Props 2.2 implementation requires frozen prereg v0.2")
    if payload.get("status") != "FROZEN_BEFORE_FUTURE_HOLDOUT":
        raise Props22Error("Props 2.2 challenger grid is not frozen")
    if payload.get("research_only") is not True or payload.get("production_authorized") is not False:
        raise Props22Error("Props 2.2 grid must remain research-only")
    if payload.get("outcome_fit_allowed") is not False:
        raise Props22Error("Props 2.2 grid may not authorize outcome fitting")
    challengers = payload.get("challengers")
    if not isinstance(challengers, list) or not challengers:
        raise Props22Error("Props 2.2 grid has no challengers")
    return payload


def _model_probability(row: Mapping[str, Any]) -> tuple[float | None, str | None]:
    td = _num(row.get("probability_td"))
    if td is not None:
        return td, "td"
    over = _num(row.get("probability_over"))
    if over is not None:
        return over, "over"
    return None, None


def _market_probability(row: Mapping[str, Any], probability_kind: str | None) -> float | None:
    if probability_kind == "td":
        return _num(row.get("market_probability_td"))
    if probability_kind == "over":
        return _num(row.get("market_probability_over"))
    return None


def _source_chronology(source: Mapping[str, Any]) -> dict[str, Any]:
    provenance = source.get("provenance") if isinstance(source.get("provenance"), Mapping) else {}
    market_state = source.get("market_state") if isinstance(source.get("market_state"), Mapping) else {}

    horizon = _timestamp(provenance.get("source_data_horizon_utc"))
    forecast = _timestamp(source.get("forecast_timestamp_utc"))
    kickoff = _timestamp(source.get("kickoff_utc"))
    market_as_of = _timestamp(market_state.get("quote_as_of"))

    source_ok = (
        horizon is not None
        and forecast is not None
        and kickoff is not None
        and horizon <= forecast < kickoff
    )
    market_ok = (
        source_ok
        and market_as_of is not None
        and market_as_of <= forecast
    )
    return {
        "source_data_horizon_utc": horizon.isoformat() if horizon else None,
        "forecast_timestamp_utc": forecast.isoformat() if forecast else None,
        "market_capture_utc": market_as_of.isoformat() if market_as_of else None,
        "kickoff_utc": kickoff.isoformat() if kickoff else None,
        "source_chronology_ok": source_ok,
        "market_chronology_ok": market_ok,
    }


def apply_challenger(
    source: Mapping[str, Any],
    challenger: Mapping[str, Any],
    *,
    contract_version: str = "levline-props-2.2-prereg-v0.2",
) -> dict[str, Any]:
    if source.get("outcome") is not None:
        raise Props22Error("Props 2.2 transformations refuse outcome-contaminated inputs")

    challenger_id = str(challenger.get("id") or "").strip()
    if not challenger_id:
        raise Props22Error("challenger id is required")

    line_market_weight = _num(challenger.get("line_market_weight"))
    line_model_weight = _num(challenger.get("line_model_weight"))
    prob_market_weight = _num(challenger.get("probability_market_weight"))
    prob_model_weight = _num(challenger.get("probability_model_weight"))
    shrink = _num(challenger.get("probability_shrink_to_half"))
    coefficients = (
        line_market_weight,
        line_model_weight,
        prob_market_weight,
        prob_model_weight,
        shrink,
    )
    if any(value is None for value in coefficients):
        raise Props22Error(f"{challenger_id}: challenger coefficients must be numeric")

    assert line_market_weight is not None
    assert line_model_weight is not None
    assert prob_market_weight is not None
    assert prob_model_weight is not None
    assert shrink is not None

    if not all(0.0 <= value <= 1.0 for value in coefficients):
        raise Props22Error(f"{challenger_id}: challenger coefficients must be within [0, 1]")
    if abs((line_market_weight + line_model_weight) - 1.0) > 1e-12:
        raise Props22Error(f"{challenger_id}: line weights must sum to one")
    if abs((prob_market_weight + prob_model_weight) - 1.0) > 1e-12:
        raise Props22Error(f"{challenger_id}: probability weights must sum to one")

    chronology = _source_chronology(source)
    if not chronology["source_chronology_ok"]:
        raise Props22Error(f"{challenger_id}: invalid source forecast chronology")

    model_line = _num(source.get("model_median"))
    market_line = _num(source.get("market_line"))
    model_probability, probability_kind = _model_probability(source)
    market_probability = _market_probability(source, probability_kind)

    prop_type = str(source.get("prop_type") or "")
    is_binary_td = prop_type in {"rushing_td", "receiving_td", "anytime_td"}

    line_available = False
    challenger_line = None
    line_unavailable_reason = None
    if is_binary_td:
        line_unavailable_reason = "binary_td_market_has_no_continuous_line"
    elif model_line is None:
        line_unavailable_reason = "missing_model_fair_line"
    elif line_market_weight > 0.0 and market_line is None:
        line_unavailable_reason = "missing_market_line_for_residual_challenger"
    elif line_market_weight > 0.0 and not chronology["market_chronology_ok"]:
        line_unavailable_reason = "missing_or_postforecast_market_timestamp"
    else:
        market_component = market_line if market_line is not None else 0.0
        challenger_line = (
            line_model_weight * model_line
            + line_market_weight * market_component
        )
        line_available = True

    probability_available = False
    challenger_probability = None
    probability_unavailable_reason = None
    if model_probability is None:
        probability_unavailable_reason = "missing_model_probability"
    elif prob_market_weight > 0.0 and market_probability is None:
        probability_unavailable_reason = "missing_market_probability_for_residual_challenger"
    elif prob_market_weight > 0.0 and not chronology["market_chronology_ok"]:
        probability_unavailable_reason = "missing_or_postforecast_market_timestamp"
    else:
        market_component = market_probability if market_probability is not None else 0.0
        blended = (
            prob_model_weight * model_probability
            + prob_market_weight * market_component
        )
        challenger_probability = 0.5 * shrink + blended * (1.0 - shrink)
        challenger_probability = min(1.0, max(0.0, challenger_probability))
        probability_available = True

    model_residual = None
    if model_line is not None and market_line is not None and not is_binary_td:
        model_residual = model_line - market_line
    probability_residual = None
    if model_probability is not None and market_probability is not None:
        probability_residual = model_probability - market_probability

    role = str(challenger.get("role") or "")
    promotion_eligible = bool(challenger.get("promotion_eligible"))

    record = {
        "contract_version": contract_version,
        "challenger_id": challenger_id,
        "challenger_role": role,
        "promotion_eligible": promotion_eligible,
        "source_props21_forecast_id": source.get("forecast_id"),
        "source_props21_forecast_sha256": _sha(source),
        "source_props21_model_version": (source.get("provenance") or {}).get("challenger_model_version"),
        "player_id": source.get("player_id"),
        "player_name": source.get("player_name"),
        "team": source.get("team"),
        "opponent": source.get("opponent"),
        "position": source.get("position"),
        "game_id": source.get("game_id"),
        "prop_type": prop_type,
        "kickoff_utc": source.get("kickoff_utc"),
        "forecast_timestamp_utc": source.get("forecast_timestamp_utc"),
        "source_data_horizon_utc": (source.get("provenance") or {}).get("source_data_horizon_utc"),
        "chronology": chronology,
        "line": {
            "model_fair_line": model_line,
            "market_line": market_line,
            "challenger_line": challenger_line,
            "line_available": line_available,
            "unavailable_reason": line_unavailable_reason,
            "market_weight": line_market_weight,
            "model_weight": line_model_weight,
            "model_residual_vs_market": model_residual,
        },
        "probability": {
            "kind": probability_kind,
            "model_probability": model_probability,
            "market_probability": market_probability,
            "challenger_probability": challenger_probability,
            "probability_available": probability_available,
            "unavailable_reason": probability_unavailable_reason,
            "market_weight": prob_market_weight,
            "model_weight": prob_model_weight,
            "shrink_to_half": shrink,
            "model_residual_vs_market": probability_residual,
        },
        "role_state": source.get("role_state"),
        "market_state": source.get("market_state"),
        "qa": source.get("qa"),
        "research_only": True,
        "production_authorized": False,
        "outcome": None,
    }
    record["receipt_sha256"] = _sha(record)
    return record


def build_challenger_set(
    source: Mapping[str, Any],
    *,
    grid: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    frozen = dict(grid or load_grid())
    challengers = frozen.get("challengers")
    if not isinstance(challengers, list):
        raise Props22Error("challenger grid missing challengers")
    contract = str(frozen.get("contract_version") or "")
    return [
        apply_challenger(source, challenger, contract_version=contract)
        for challenger in challengers
    ]


def build_slate(
    forecasts: list[Mapping[str, Any]],
    *,
    grid: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    frozen = dict(grid or load_grid())
    rows: list[dict[str, Any]] = []
    for source in forecasts:
        rows.extend(build_challenger_set(source, grid=frozen))
    return {
        "contract_version": frozen.get("contract_version"),
        "status": frozen.get("status"),
        "research_only": True,
        "production_authorized": False,
        "source_forecast_count": len(forecasts),
        "challenger_record_count": len(rows),
        "challengers": rows,
    }
