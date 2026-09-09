from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from typing import Any

import numpy as np
import pandas as pd


def _num(v) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def confidence_components(prob: float, disagreement: float | None, consistency: str | None) -> dict[str, float]:
    """Transparent confidence index components.

    This is deliberately *not* a second win probability.  It is an explanatory
    index describing how decisive and internally coherent a forecast is.  It
    should only be mapped to empirical hit rates after sufficient locked-game
    history exists.
    """
    p = float(np.clip(prob, 0.0, 1.0))
    q = max(p, 1.0 - p)
    conviction = float(np.clip((q - 0.50) / 0.25, 0.0, 1.0))
    d = _num(disagreement)
    agreement = 0.5 if d is None else float(np.clip(1.0 - d / 0.12, 0.0, 1.0))
    c = str(consistency or "").upper()
    consistency_component = 1.0 if c == "ALIGNED" else 0.70 if c == "NEUTRAL" else 0.35
    index = 100.0 * (0.55 * conviction + 0.30 * agreement + 0.15 * consistency_component)
    return {
        "confidence_index": float(np.clip(index, 0.0, 100.0)),
        "confidence_conviction": conviction,
        "confidence_agreement": agreement,
        "confidence_consistency": consistency_component,
    }


def add_confidence_diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rows = [
        confidence_components(r["final_home_prob"], r.get("model_disagreement"), r.get("consistency_flag"))
        for _, r in out.iterrows()
    ]
    comp = pd.DataFrame(rows, index=out.index)
    for c in comp.columns:
        out[c] = comp[c]
    return out


def build_calibration_table(
    historical: pd.DataFrame,
    baseline_oof: pd.DataFrame,
    core_oof: pd.DataFrame,
    bins: int = 10,
) -> pd.DataFrame:
    """Fixed-width chronological OOS reliability table.

    All rows come from the already-walk-forward OOF predictions.  Nothing here
    is fit on 2026 outcomes.
    """
    idx = core_oof.index.intersection(historical.index)
    if len(idx) == 0:
        return pd.DataFrame()

    y = pd.to_numeric(core_oof.loc[idx, "home_win"], errors="coerce")
    core = pd.to_numeric(core_oof.loc[idx, "stack"], errors="coerce")
    sujar = pd.to_numeric(baseline_oof.reindex(idx).get("stack"), errors="coerce")
    market = pd.to_numeric(historical.reindex(idx).get("market_home_prob"), errors="coerce")
    final = core.copy()
    market_mask = market.notna()
    final.loc[market_mask] = 0.75 * core.loc[market_mask] + 0.25 * market.loc[market_mask]

    models = {
        "Sujar Baseline": sujar,
        "Core Sujar+": core,
        "Market": market,
        "Final Ensemble": final,
    }
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows: list[dict[str, Any]] = []
    for model_name, pred in models.items():
        frame = pd.DataFrame({"y": y, "p": pred}).dropna()
        if frame.empty:
            continue
        frame["bin"] = pd.cut(frame["p"], bins=edges, include_lowest=True, right=True, duplicates="drop")
        parts = []
        for interval, g in frame.groupby("bin", observed=True):
            if g.empty:
                continue
            avg_pred = float(g["p"].mean())
            observed = float(g["y"].mean())
            gap = observed - avg_pred
            parts.append((len(g), abs(gap)))
            rows.append({
                "model": model_name,
                "bin_low": float(interval.left),
                "bin_high": float(interval.right),
                "games": int(len(g)),
                "avg_pred": avg_pred,
                "observed_home_win": observed,
                "calibration_gap": gap,
                "bin_brier": float(np.mean((g["p"] - g["y"]) ** 2)),
            })
        total = sum(n for n, _ in parts)
        ece = sum(n * gap for n, gap in parts) / total if total else np.nan
        for row in rows:
            if row["model"] == model_name:
                row["ece"] = float(ece)
                row["model_games"] = int(len(frame))
    return pd.DataFrame(rows)


def build_movement_attribution(run_history: pd.DataFrame) -> pd.DataFrame:
    """Attribute the most recent forecast move to model vs market inputs.

    The current production MARKET+ rule is 75% PURE / 25% market whenever both
    snapshots have market probabilities.  Residual captures blend-regime changes
    or rounding/data transitions and prevents false precision.
    """
    if run_history is None or run_history.empty or "game_id" not in run_history:
        return pd.DataFrame()
    rh = run_history.copy()
    rh["_ts"] = pd.to_datetime(rh.get("prediction_timestamp_utc"), errors="coerce", utc=True)
    rh = rh.sort_values(["game_id", "_ts"], kind="stable")
    rows: list[dict[str, Any]] = []
    for gid, g in rh.groupby("game_id", sort=False):
        g = g[g["_ts"].notna()]
        if len(g) < 2:
            continue
        prev, cur = g.iloc[-2], g.iloc[-1]
        final_prev, final_cur = _num(prev.get("final_home_prob")), _num(cur.get("final_home_prob"))
        pure_prev, pure_cur = _num(prev.get("pure_home_prob")), _num(cur.get("pure_home_prob"))
        market_prev, market_cur = _num(prev.get("market_home_prob")), _num(cur.get("market_home_prob"))
        if final_prev is None or final_cur is None:
            continue
        final_delta = 100.0 * (final_cur - final_prev)
        pure_delta = None if pure_prev is None or pure_cur is None else 100.0 * (pure_cur - pure_prev)
        market_delta = None if market_prev is None or market_cur is None else 100.0 * (market_cur - market_prev)
        both_market = market_delta is not None and pure_delta is not None
        model_component = (0.75 * pure_delta) if both_market else (pure_delta if pure_delta is not None else 0.0)
        market_component = (0.25 * market_delta) if both_market else 0.0
        residual = final_delta - model_component - market_component
        latest_pick = str(cur.get("pick") or "")
        home = str(cur.get("home_team") or "")
        pick_delta = final_delta if latest_pick == home else -final_delta
        drivers = {
            "Model refresh": abs(model_component),
            "Market movement": abs(market_component),
            "Blend/data transition": abs(residual),
        }
        largest = max(drivers, key=drivers.get)
        if drivers[largest] < 0.05:
            largest = "No material move"
        rows.append({
            "game_id": gid,
            "away_team": cur.get("away_team"),
            "home_team": cur.get("home_team"),
            "pick": latest_pick,
            "from_timestamp_utc": prev.get("prediction_timestamp_utc"),
            "to_timestamp_utc": cur.get("prediction_timestamp_utc"),
            "final_home_delta_pp": final_delta,
            "pick_delta_pp": pick_delta,
            "pure_delta_pp": pure_delta,
            "market_delta_pp": market_delta,
            "model_component_pp": model_component,
            "market_component_pp": market_component,
            "residual_component_pp": residual,
            "margin_delta": None if _num(prev.get("expected_margin")) is None or _num(cur.get("expected_margin")) is None else _num(cur.get("expected_margin")) - _num(prev.get("expected_margin")),
            "total_delta": None if _num(prev.get("expected_total")) is None or _num(cur.get("expected_total")) is None else _num(cur.get("expected_total")) - _num(prev.get("expected_total")),
            "largest_driver": largest,
        })
    return pd.DataFrame(rows)


def build_team_profiles(power: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    if power is None or power.empty:
        return pd.DataFrame()
    p = predictions.copy() if predictions is not None else pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for _, r in power.iterrows():
        team = str(r.get("team"))
        profile = r.to_dict()
        profile.update({
            "next_game_id": None,
            "next_opponent": None,
            "next_site": None,
            "next_win_prob": np.nan,
            "next_projected_points": np.nan,
            "next_expected_margin": np.nan,
            "next_game_date": None,
        })
        if not p.empty:
            matches = p[(p.get("home_team") == team) | (p.get("away_team") == team)]
            if len(matches):
                g = matches.iloc[0]
                home = str(g.get("home_team")); away = str(g.get("away_team"))
                hp = _num(g.get("final_home_prob")); margin = _num(g.get("expected_margin")); total = _num(g.get("expected_total"))
                is_home = team == home
                profile["next_game_id"] = g.get("game_id")
                profile["next_opponent"] = away if is_home else home
                profile["next_site"] = "HOME" if is_home else "AWAY"
                profile["next_game_date"] = g.get("gameday")
                if hp is not None:
                    profile["next_win_prob"] = hp if is_home else 1.0 - hp
                if margin is not None:
                    profile["next_expected_margin"] = margin if is_home else -margin
                if margin is not None and total is not None:
                    home_pts = (total + margin) / 2.0
                    away_pts = (total - margin) / 2.0
                    profile["next_projected_points"] = home_pts if is_home else away_pts
        rows.append(profile)
    return pd.DataFrame(rows)


def build_weekly_brief(predictions: pd.DataFrame, movement: pd.DataFrame | None = None) -> dict[str, Any]:
    p = predictions.copy()
    generated = datetime.now(timezone.utc).isoformat()
    if p.empty:
        return {"generated_utc": generated, "week": None, "strongest": [], "market_disagreements": [], "most_uncertain": [], "biggest_movers": []}
    p["_pick_prob"] = np.where(
        p["pick"].astype(str).eq(p["home_team"].astype(str)),
        pd.to_numeric(p["final_home_prob"], errors="coerce"),
        1.0 - pd.to_numeric(p["final_home_prob"], errors="coerce"),
    )
    p["_market_gap"] = (pd.to_numeric(p.get("pure_home_prob"), errors="coerce") - pd.to_numeric(p.get("market_home_prob"), errors="coerce")).abs()
    p["_uncertainty"] = (p["_pick_prob"] - 0.5).abs()

    def game_item(r: pd.Series) -> dict[str, Any]:
        return {
            "game_id": r.get("game_id"),
            "matchup": f"{r.get('away_team')} @ {r.get('home_team')}",
            "pick": r.get("pick"),
            "pick_prob": _num(r.get("_pick_prob")),
            "projected_score": r.get("projected_score"),
            "confidence": r.get("confidence"),
        }

    strongest = [game_item(r) for _, r in p.sort_values("_pick_prob", ascending=False).head(3).iterrows()]
    disagreements = []
    for _, r in p[p["_market_gap"].notna()].sort_values("_market_gap", ascending=False).head(3).iterrows():
        x = game_item(r); x["pure_market_gap_pp"] = 100.0 * float(r["_market_gap"]); disagreements.append(x)
    uncertain = [game_item(r) for _, r in p.sort_values("_uncertainty", ascending=True).head(3).iterrows()]
    movers: list[dict[str, Any]] = []
    if movement is not None and not movement.empty:
        m = movement.copy(); m["_abs"] = pd.to_numeric(m.get("pick_delta_pp"), errors="coerce").abs()
        for _, r in m.sort_values("_abs", ascending=False).head(3).iterrows():
            movers.append({
                "game_id": r.get("game_id"), "pick": r.get("pick"), "pick_delta_pp": _num(r.get("pick_delta_pp")),
                "largest_driver": r.get("largest_driver"),
            })
    return {
        "generated_utc": generated,
        "week": int(pd.to_numeric(p["week"], errors="coerce").dropna().iloc[0]) if "week" in p and p["week"].notna().any() else None,
        "strongest": strongest,
        "market_disagreements": disagreements,
        "most_uncertain": uncertain,
        "biggest_movers": movers,
    }


def build_postgame_autopsies(official: pd.DataFrame) -> dict[str, Any]:
    if official is None or official.empty:
        return {}
    out: dict[str, Any] = {}
    for _, r in official.iterrows():
        hs, aw = _num(r.get("actual_home_score")), _num(r.get("actual_away_score"))
        if hs is None or aw is None:
            continue
        margin_error = _num(r.get("margin_abs_error")); total_error = _num(r.get("total_abs_error"))
        winner_raw = r.get("winner_correct")
        winner_correct = None if pd.isna(winner_raw) else bool(winner_raw)
        right: list[str] = []
        missed: list[str] = []
        if winner_correct is True:
            right.append("The locked forecast got the winner direction right.")
        elif winner_correct is False:
            missed.append("The locked forecast missed the outright winner.")
        if margin_error is not None:
            (right if margin_error <= 7.0 else missed).append(
                f"The predicted margin finished {margin_error:.1f} points from the actual margin."
            )
        if total_error is not None:
            (right if total_error <= 7.0 else missed).append(
                f"The predicted total finished {total_error:.1f} points from the actual total."
            )
        error_tags: list[str] = []
        if winner_correct is False:
            error_tags.append("winner_miss")
        if margin_error is not None and margin_error > 7.0:
            error_tags.append("margin_miss")
        if total_error is not None and total_error > 7.0:
            error_tags.append("total_miss")
        if not error_tags:
            error_tags.append("no_major_error_flag")

        gid = str(r.get("game_id"))
        out[gid] = {
            "game_id": gid,
            "matchup": f"{r.get('away_team')} @ {r.get('home_team')}",
            "official_pick": r.get("pick"),
            "official_home_prob": _num(r.get("final_home_prob")),
            "projected_score": r.get("projected_score"),
            "actual_score": f"{r.get('home_team')} {hs:.0f} – {r.get('away_team')} {aw:.0f}",
            "winner_correct": winner_correct,
            "margin_abs_error": margin_error,
            "total_abs_error": total_error,
            "what_went_right": right,
            "what_missed": missed,
            "error_tags": error_tags,
            "causal_analysis_status": "Quantitative autopsy only. Play-level causal analysis is added when current-season PBP is available and verified.",
        }
    return out


def write_json(path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=str), encoding="utf-8")
