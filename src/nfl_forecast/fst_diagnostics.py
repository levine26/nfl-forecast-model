from __future__ import annotations

"""Diagnostics whose semantics changed with the F-ST production regime."""

from typing import Any

import pandas as pd


def _num(value) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if pd.notna(out) else None


def build_fst_movement_attribution(run_history: pd.DataFrame) -> pd.DataFrame:
    """Describe official F-ST movement without inventing a linear probability decomposition.

    F-ST is linear in log-odds but nonlinear in probability space. Therefore this output
    reports observed movement in official F-ST, nested PURE, MARKET, and the legacy 75/25
    counterfactual. The historical `model_component_pp` / `market_component_pp` fields are
    retained only as explicitly legacy-counterfactual diagnostics for downstream schema
    compatibility; they are never represented as components of the official F-ST move.
    """
    if run_history is None or run_history.empty or "game_id" not in run_history:
        return pd.DataFrame()
    rh = run_history.copy()
    rh["_ts"] = pd.to_datetime(rh.get("prediction_timestamp_utc"), errors="coerce", utc=True)
    rh = rh.sort_values(["game_id", "_ts"], kind="stable")
    rows: list[dict[str, Any]] = []
    for gid, group in rh.groupby("game_id", sort=False):
        group = group[group["_ts"].notna()]
        if len(group) < 2:
            continue
        prev, cur = group.iloc[-2], group.iloc[-1]
        final_prev, final_cur = _num(prev.get("final_home_prob")), _num(cur.get("final_home_prob"))
        if final_prev is None or final_cur is None:
            continue

        def delta(field: str) -> float | None:
            a, b = _num(prev.get(field)), _num(cur.get(field))
            return None if a is None or b is None else 100.0 * (b - a)

        final_delta = 100.0 * (final_cur - final_prev)
        fst_pure_delta = delta("fst_pure_home_prob")
        market_delta = delta("market_home_prob")
        legacy_pure_delta = delta("legacy_pure_home_prob")
        if legacy_pure_delta is None:
            legacy_pure_delta = delta("pure_home_prob")
        legacy_final_delta = delta("legacy_final_home_prob")

        # Preserve the old component columns solely as a legacy comparator decomposition.
        both_legacy_inputs = market_delta is not None and legacy_pure_delta is not None
        legacy_model_component = (
            0.75 * legacy_pure_delta
            if both_legacy_inputs
            else (legacy_pure_delta if legacy_pure_delta is not None else 0.0)
        )
        legacy_market_component = 0.25 * market_delta if both_legacy_inputs else 0.0
        legacy_residual = (
            None
            if legacy_final_delta is None
            else legacy_final_delta - legacy_model_component - legacy_market_component
        )

        latest_pick = str(cur.get("pick") or "")
        home = str(cur.get("home_team") or "")
        pick_delta = final_delta if latest_pick == home else -final_delta
        drivers = {
            "F-ST nested PURE movement": abs(fst_pure_delta or 0.0),
            "Market movement": abs(market_delta or 0.0),
        }
        largest = max(drivers, key=drivers.get)
        if drivers[largest] < 0.05:
            largest = "No material input move"

        rows.append({
            "game_id": gid,
            "away_team": cur.get("away_team"),
            "home_team": cur.get("home_team"),
            "pick": latest_pick,
            "from_timestamp_utc": prev.get("prediction_timestamp_utc"),
            "to_timestamp_utc": cur.get("prediction_timestamp_utc"),
            "final_home_delta_pp": final_delta,
            "pick_delta_pp": pick_delta,
            "pure_delta_pp": legacy_pure_delta,
            "fst_pure_delta_pp": fst_pure_delta,
            "market_delta_pp": market_delta,
            "legacy_final_delta_pp": legacy_final_delta,
            "model_component_pp": legacy_model_component,
            "market_component_pp": legacy_market_component,
            "residual_component_pp": legacy_residual,
            "attribution_scope": "official_fst_inputs_plus_legacy_counterfactual",
            "legacy_component_scope": "legacy_75_25_counterfactual_only",
            "margin_delta": (
                None
                if _num(prev.get("expected_margin")) is None or _num(cur.get("expected_margin")) is None
                else _num(cur.get("expected_margin")) - _num(prev.get("expected_margin"))
            ),
            "total_delta": (
                None
                if _num(prev.get("expected_total")) is None or _num(cur.get("expected_total")) is None
                else _num(cur.get("expected_total")) - _num(prev.get("expected_total"))
            ),
            "largest_driver": largest,
        })
    return pd.DataFrame(rows)
