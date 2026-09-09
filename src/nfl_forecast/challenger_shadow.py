from __future__ import annotations

"""Immutable research-only challenger scoring against production T-120 locks."""

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .challenger import blend_probabilities
from .challenger_v06 import logit_blend_probabilities

SUPPORTED_METHODS = {"fixed", "linear", "logit", "pure"}

HISTORY_COLUMNS = [
    "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
    "challenger_pure_home_prob", "market_home_prob_t120", "challenger_final_home_prob",
    "challenger_pick", "effective_pure_weight", "effective_market_weight",
    "research_candidate", "research_method", "shadow_generated_utc", "shadow_source_sha",
    "production_snapshot_type", "production_model_version",
    "production_prediction_timestamp_utc", "production_lock_timestamp_utc",
    "kickoff_utc", "minutes_to_kickoff_at_production_lock", "shadow_recorded_timestamp_utc",
    "lock_status", "actual_home_score", "actual_away_score", "winner_correct",
]


def _utc(dt: datetime | None = None) -> datetime:
    value = dt or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse_utc(value) -> datetime | None:
    if value is None or pd.isna(value):
        return None
    try:
        dt = pd.Timestamp(value).to_pydatetime()
    except Exception:
        return None
    return _utc(dt)


def empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=HISTORY_COLUMNS)


def normalize_history(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return empty_history()
    out = frame.copy()
    for col in HISTORY_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA
    return out[HISTORY_COLUMNS].copy()


def probability_for_method(pure: float, market: float, weight: float, method: str) -> float:
    if method not in SUPPORTED_METHODS:
        raise RuntimeError(
            f"Unsupported challenger shadow method {method!r}; refusing to approximate T-120 forecast"
        )
    if method == "pure":
        if not np.isclose(weight, 1.0):
            raise RuntimeError("PURE shadow method must carry effective_pure_weight=1.0")
        return float(np.clip(pure, 1e-6, 1.0 - 1e-6))
    if weight < 0.25 - 1e-12:
        raise RuntimeError(f"Challenger PURE floor violated at shadow lock: {weight:.6f}")
    if method == "logit":
        return float(logit_blend_probabilities([pure], [market], weight)[0])
    return float(blend_probabilities([pure], [market], weight)[0])


def grade_existing(history: pd.DataFrame, production_locks: pd.DataFrame) -> pd.DataFrame:
    if history.empty or production_locks.empty or "game_id" not in production_locks.columns:
        return history
    if not {"actual_home_score", "actual_away_score"}.issubset(production_locks.columns):
        return history
    results = production_locks.drop_duplicates("game_id", keep="last").set_index("game_id")
    out = history.copy()
    for idx, row in out.iterrows():
        gid = str(row.get("game_id"))
        if gid not in results.index:
            continue
        result = results.loc[gid]
        hs = pd.to_numeric(result.get("actual_home_score"), errors="coerce")
        aw = pd.to_numeric(result.get("actual_away_score"), errors="coerce")
        if pd.isna(hs) or pd.isna(aw):
            continue
        out.at[idx, "actual_home_score"] = float(hs)
        out.at[idx, "actual_away_score"] = float(aw)
        winner = row.get("home_team") if float(hs) > float(aw) else row.get("away_team")
        out.at[idx, "winner_correct"] = bool(str(row.get("challenger_pick")) == str(winner))
    return out


def lock_shadow(
    production_locks: pd.DataFrame,
    challenger_week: pd.DataFrame,
    existing_history: pd.DataFrame | None = None,
    *,
    now_utc: datetime | None = None,
) -> tuple[pd.DataFrame, int, int]:
    """Append eligible shadow rows and grade old ones.

    Returns ``(history, locks_added, precommit_skips)``. A precommit skip means
    the challenger row was generated after the production lock and is therefore
    deliberately excluded from the forward test.
    """
    now = _utc(now_utc)
    history = normalize_history(existing_history)
    history = grade_existing(history, production_locks)

    required_prod = {
        "game_id", "season", "week", "gameday", "gametime", "away_team", "home_team",
        "market_home_prob", "snapshot_type", "lock_status", "lock_timestamp_utc",
        "kickoff_utc", "minutes_to_kickoff_at_lock",
    }
    required_shadow = {
        "game_id", "challenger_pure_home_prob", "effective_pure_weight",
        "research_candidate", "research_method", "shadow_generated_utc",
    }
    missing_prod = required_prod - set(production_locks.columns)
    missing_shadow = required_shadow - set(challenger_week.columns)
    if missing_prod:
        raise RuntimeError(f"Production lock history missing required fields: {sorted(missing_prod)}")
    if missing_shadow:
        raise RuntimeError(f"Challenger week missing required shadow fields: {sorted(missing_shadow)}")

    challenger = challenger_week.drop_duplicates("game_id", keep="last").set_index("game_id")
    already = set(history.game_id.astype(str)) if len(history) else set()
    new_rows: list[dict] = []
    precommit_skips = 0

    locked_rows = production_locks[
        production_locks.lock_status.astype(str).str.upper().eq("LOCKED")
    ].copy()
    for _, prod in locked_rows.iterrows():
        gid = str(prod.get("game_id"))
        if gid in already or gid not in challenger.index:
            continue
        if str(prod.get("snapshot_type", "")).upper() != "FINAL":
            continue

        production_lock_time = _parse_utc(prod.get("lock_timestamp_utc"))
        if production_lock_time is None:
            raise RuntimeError(f"Production lock {gid} has invalid lock_timestamp_utc")
        minutes = pd.to_numeric(prod.get("minutes_to_kickoff_at_lock"), errors="coerce")
        if pd.isna(minutes) or not (0.0 < float(minutes) <= 120.0 + 1e-9):
            raise RuntimeError(f"Production lock {gid} is outside authoritative T-120 window")

        shadow = challenger.loc[gid]
        shadow_generated = _parse_utc(shadow.get("shadow_generated_utc"))
        if shadow_generated is None:
            raise RuntimeError(f"Shadow row {gid} has invalid shadow_generated_utc")
        if shadow_generated > production_lock_time:
            precommit_skips += 1
            continue

        pure = pd.to_numeric(shadow.get("challenger_pure_home_prob"), errors="coerce")
        market = pd.to_numeric(prod.get("market_home_prob"), errors="coerce")
        weight = pd.to_numeric(shadow.get("effective_pure_weight"), errors="coerce")
        method = str(shadow.get("research_method", ""))
        if pd.isna(pure) or pd.isna(weight):
            raise RuntimeError(f"Shadow inputs incomplete for {gid}")
        if pd.isna(market) and method != "pure":
            final = float(np.clip(float(pure), 1e-6, 1.0 - 1e-6))
        else:
            final = probability_for_method(float(pure), float(market), float(weight), method)

        home = str(prod.get("home_team"))
        away = str(prod.get("away_team"))
        pick = home if final >= 0.5 else away
        new_rows.append({
            "game_id": gid,
            "season": prod.get("season"),
            "week": prod.get("week"),
            "gameday": prod.get("gameday"),
            "gametime": prod.get("gametime"),
            "away_team": away,
            "home_team": home,
            "challenger_pure_home_prob": float(pure),
            "market_home_prob_t120": float(market) if pd.notna(market) else np.nan,
            "challenger_final_home_prob": final,
            "challenger_pick": pick,
            "effective_pure_weight": float(weight),
            "effective_market_weight": 1.0 - float(weight),
            "research_candidate": shadow.get("research_candidate"),
            "research_method": method,
            "shadow_generated_utc": shadow_generated.isoformat(),
            "shadow_source_sha": shadow.get("shadow_source_sha", pd.NA),
            "production_snapshot_type": str(prod.get("snapshot_type")),
            "production_model_version": prod.get("model_version", pd.NA),
            "production_prediction_timestamp_utc": prod.get("prediction_timestamp_utc", pd.NA),
            "production_lock_timestamp_utc": production_lock_time.isoformat(),
            "kickoff_utc": prod.get("kickoff_utc"),
            "minutes_to_kickoff_at_production_lock": float(minutes),
            "shadow_recorded_timestamp_utc": now.isoformat(),
            "lock_status": "LOCKED",
            "actual_home_score": prod.get("actual_home_score", np.nan),
            "actual_away_score": prod.get("actual_away_score", np.nan),
            "winner_correct": pd.NA,
        })
        already.add(gid)

    if new_rows:
        history = pd.concat([history, pd.DataFrame(new_rows)], ignore_index=True)
    history = grade_existing(history, production_locks)
    history = history.drop_duplicates("game_id", keep="first")
    return history[HISTORY_COLUMNS].copy(), len(new_rows), precommit_skips
