from __future__ import annotations

"""Prospective shadow constructor for ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1.

This module is research-only. It consumes already-timestamped pregame evidence, applies the
frozen Candidate 4 rule, and creates content-hashed decision records. It never reads scores
or outcomes and never mutates production F-ST.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from typing import Any, Iterable

import pandas as pd

from research.market_state_v1 import (
    build_market_state,
    select_book_horizons,
    select_consensus_horizons,
)

CANDIDATE_ID = "ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1"
CANDIDATE_VERSION = "1.0.0"
PREREGISTRATION_SHA = "74ecd303545c09f57593546472d27438e3d8a204"
FST_ARTIFACT_ID = "F-ST-01-FROZEN-2026"
MIN_COMMON_BOOKS = 5
BREADTH_THRESHOLD = 0.50
DECISION_HORIZON_MINUTES = 60
INCUMBENT_WINDOW_MINUTES = 120


def _utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def _float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def _pick(home_team: str, away_team: str, home_probability: float) -> str:
    return home_team if home_probability >= 0.5 else away_team


def _direction_points_to_market(direction: float, market_home: bool) -> bool:
    return direction > 0 if market_home else direction < 0


def _content_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def select_frozen_incumbents(production_history: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Select the first immutable production F-ST lock for each game."""
    if production_history.empty:
        return {}
    required = {
        "game_id",
        "home_team",
        "away_team",
        "final_home_prob",
        "lock_status",
        "lock_timestamp_utc",
        "kickoff_utc",
        "minutes_to_kickoff_at_lock",
        "fst_artifact_id",
        "final_probability_strategy",
    }
    missing = required - set(production_history.columns)
    if missing:
        raise ValueError(f"production history missing fields: {sorted(missing)}")

    rows: list[dict[str, Any]] = []
    for row in production_history.to_dict("records"):
        if str(row.get("lock_status") or "").upper() != "LOCKED":
            continue
        if str(row.get("fst_artifact_id") or "") != FST_ARTIFACT_ID:
            continue
        if str(row.get("final_probability_strategy") or "") != FST_ARTIFACT_ID:
            continue
        probability = _float(row.get("final_home_prob"))
        lock_time = _utc(row.get("lock_timestamp_utc"))
        kickoff = _utc(row.get("kickoff_utc"))
        minutes = _float(row.get("minutes_to_kickoff_at_lock"))
        if probability is None or not 0.0 < probability < 1.0:
            continue
        if lock_time is None or kickoff is None or lock_time >= kickoff:
            continue
        if minutes is None or not (0.0 < minutes <= INCUMBENT_WINDOW_MINUTES + 1e-9):
            continue
        copy = dict(row)
        copy["_lock_dt"] = lock_time
        copy["_kickoff_dt"] = kickoff
        copy["_prob"] = probability
        rows.append(copy)

    rows.sort(key=lambda r: (str(r["game_id"]), r["_lock_dt"]))
    selected: dict[str, dict[str, Any]] = {}
    for row in rows:
        selected.setdefault(str(row["game_id"]), row)
    return selected


def _qb_state_by_game(qb_state: pd.DataFrame) -> dict[str, dict[str, Any]]:
    if qb_state.empty:
        return {}
    if "game_id" not in qb_state.columns:
        raise ValueError("QB state missing game_id")
    if qb_state["game_id"].astype(str).duplicated().any():
        raise ValueError("QB state must contain at most one row per game")
    return {str(row["game_id"]): dict(row) for row in qb_state.to_dict("records")}


def _qb_complete_for_decision(
    row: dict[str, Any] | None,
    *,
    incumbent_lock: datetime,
    kickoff: datetime,
) -> tuple[bool, int | None, list[str]]:
    reasons: list[str] = []
    if row is None:
        return False, None, ["missing_qb_state"]

    if not _bool(row.get("qb_state_complete")):
        reasons.append("qb_state_incomplete")
    if not _bool(row.get("source_qualified")):
        reasons.append("qb_source_unqualified")
    if not _bool(row.get("research_only")):
        reasons.append("qb_not_research_only")
    if _bool(row.get("production_authorized")):
        reasons.append("qb_production_authorized")

    direction_raw = _float(row.get("qb_shock_direction"))
    if direction_raw is None or direction_raw not in {-1.0, 0.0, 1.0}:
        reasons.append("invalid_qb_shock_direction")
        direction = None
    else:
        direction = int(direction_raw)

    known_by = _utc(row.get("qb_shock_known_by_utc"))
    inactive_capture = _utc(row.get("inactive_capture_timestamp_utc"))
    depth_time = _utc(row.get("t120_depth_timestamp_utc"))
    target_t60 = kickoff - timedelta(minutes=DECISION_HORIZON_MINUTES)
    target_t120 = kickoff - timedelta(minutes=120)

    if known_by is None:
        reasons.append("missing_qb_known_by")
    else:
        if known_by <= incumbent_lock:
            reasons.append("qb_shock_not_new_after_incumbent")
        if known_by > target_t60:
            reasons.append("qb_shock_after_t60")
        if known_by >= kickoff:
            reasons.append("qb_shock_postkickoff")

    if inactive_capture is None or inactive_capture > target_t60:
        reasons.append("inactive_capture_not_by_t60")
    if depth_time is None or depth_time > target_t120:
        reasons.append("depth_state_after_t120")

    required_text = (
        "t120_qb1_team",
        "t120_qb1_player_name",
        "t120_qb1_gsis_id",
        "inactive_raw_sha256",
    )
    for field in required_text:
        if not str(row.get(field) or "").strip():
            reasons.append(f"missing_{field}")

    return not reasons, direction, reasons


def build_candidate4_decisions(
    production_history: pd.DataFrame,
    market_ledger: pd.DataFrame,
    qb_state: pd.DataFrame,
    *,
    generated_at_utc: datetime | str | None = None,
) -> pd.DataFrame:
    """Build deterministic Candidate 4 decision attempts without loading outcomes."""
    generated = _utc(generated_at_utc) if generated_at_utc is not None else datetime.now(timezone.utc)
    if generated is None:
        raise ValueError("generated_at_utc must be timezone-aware")

    incumbents = select_frozen_incumbents(production_history)
    market_rows = market_ledger.to_dict("records") if not market_ledger.empty else []
    market_states, _ = build_market_state(market_rows)
    state_by_game = {str(row["game_id"]): row for row in market_states}
    selected_consensus = select_consensus_horizons(market_rows)
    selected_books = select_book_horizons(market_rows, selected_consensus)
    qb_by_game = _qb_state_by_game(qb_state)

    output: list[dict[str, Any]] = []
    for game_id, incumbent in sorted(incumbents.items()):
        home = str(incumbent.get("home_team"))
        away = str(incumbent.get("away_team"))
        kickoff = incumbent["_kickoff_dt"]
        lock_time = incumbent["_lock_dt"]
        p_fst = float(incumbent["_prob"])
        w_fst = _pick(home, away, p_fst)

        reasons: list[str] = []
        state = state_by_game.get(game_id)
        m60 = None
        d = None
        breadth = None
        common_books: list[str] = []
        provider = None
        t120_request = None
        t60_request = None

        if state is None:
            reasons.append("missing_market_state")
        else:
            provider = str(state.get("market_provider") or "") or None
            m120 = _float(state.get("market_home_prob_t120"))
            m60 = _float(state.get("market_home_prob_t60"))
            d = _float(state.get("home_logit_t60_minus_t120"))
            breadth = _float(state.get("book_movement_breadth_t60_minus_t120"))
            t120_request = _utc(state.get("request_timestamp_utc_t120"))
            t60_request = _utc(state.get("request_timestamp_utc_t60"))
            books = selected_books.get(game_id, {})
            common_books = sorted(set(books.get("T-120m", {})) & set(books.get("T-60m", {})))

            if m120 is None or m60 is None:
                reasons.append("missing_primary_market_horizon")
            if d is None or breadth is None:
                reasons.append("missing_market_path")
            if len(common_books) < MIN_COMMON_BOOKS:
                reasons.append("insufficient_common_books")
            if not provider:
                reasons.append("missing_market_provider")
            target_t120 = kickoff - timedelta(minutes=120)
            target_t60 = kickoff - timedelta(minutes=60)
            if t120_request is None or not (target_t120 - timedelta(minutes=7.5) <= t120_request <= target_t120):
                reasons.append("invalid_t120_timing")
            if t60_request is None or not (target_t60 - timedelta(minutes=7.5) <= t60_request <= target_t60):
                reasons.append("invalid_t60_timing")
            if t120_request is not None and t60_request is not None and t120_request >= t60_request:
                reasons.append("market_horizon_order_invalid")

        qb_row = qb_by_game.get(game_id)
        qb_complete, qb_direction, qb_reasons = _qb_complete_for_decision(
            qb_row,
            incumbent_lock=lock_time,
            kickoff=kickoff,
        )
        reasons.extend(qb_reasons)

        eligible = not reasons
        market_pick = _pick(home, away, float(m60)) if m60 is not None else None
        market_home = market_pick == home if market_pick is not None else False
        disagree = bool(market_pick is not None and market_pick != w_fst)
        path_direction = bool(d is not None and d != 0.0 and _direction_points_to_market(d, market_home))
        breadth_gate = bool(breadth is not None and abs(breadth) >= BREADTH_THRESHOLD)
        qb_nonzero = bool(qb_direction in {-1, 1})
        qb_direction_gate = bool(
            qb_nonzero and market_pick is not None and _direction_points_to_market(float(qb_direction), market_home)
        )

        level_switch = bool(eligible and disagree)
        path_switch = bool(eligible and disagree and path_direction and breadth_gate)
        qb_switch = bool(eligible and disagree and qb_nonzero and qb_direction_gate)
        candidate_switch = bool(
            eligible
            and disagree
            and path_direction
            and breadth_gate
            and qb_nonzero
            and qb_direction_gate
        )

        p_c4 = float(m60) if candidate_switch and m60 is not None else p_fst
        p_level = float(m60) if level_switch and m60 is not None else p_fst
        p_path = float(m60) if path_switch and m60 is not None else p_fst
        p_qb = float(m60) if qb_switch and m60 is not None else p_fst

        record = {
            "schema_version": "adaptive-candidate4-shadow-v1",
            "candidate_id": CANDIDATE_ID,
            "candidate_version": CANDIDATE_VERSION,
            "preregistration_sha": PREREGISTRATION_SHA,
            "game_id": game_id,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": _iso(kickoff),
            "incumbent_lock_timestamp_utc": _iso(lock_time),
            "incumbent_home_prob": p_fst,
            "incumbent_pick": w_fst,
            "market_provider": provider,
            "market_t120_request_utc": _iso(t120_request),
            "market_t60_request_utc": _iso(t60_request),
            "market_t60_home_prob": m60,
            "market_t60_pick": market_pick,
            "market_path_median_logit_change": d,
            "market_path_breadth": breadth,
            "common_sportsbook_count": len(common_books),
            "common_sportsbooks": "|".join(common_books),
            "qb_state_complete": qb_complete,
            "qb_shock_direction": qb_direction,
            "qb_shock_known_by_utc": str((qb_row or {}).get("qb_shock_known_by_utc") or "") or None,
            "t120_qb1_team": str((qb_row or {}).get("t120_qb1_team") or "") or None,
            "t120_qb1_player_name": str((qb_row or {}).get("t120_qb1_player_name") or "") or None,
            "t120_qb1_gsis_id": str((qb_row or {}).get("t120_qb1_gsis_id") or "") or None,
            "t120_depth_timestamp_utc": str((qb_row or {}).get("t120_depth_timestamp_utc") or "") or None,
            "inactive_raw_sha256": str((qb_row or {}).get("inactive_raw_sha256") or "") or None,
            "inactive_capture_timestamp_utc": str((qb_row or {}).get("inactive_capture_timestamp_utc") or "") or None,
            "eligible": eligible,
            "ineligibility_reasons": "|".join(sorted(set(reasons))),
            "gate_market_disagreement": disagree,
            "gate_path_direction": path_direction,
            "gate_path_breadth": breadth_gate,
            "gate_qb_nonzero": qb_nonzero,
            "gate_qb_direction": qb_direction_gate,
            "candidate_switch": candidate_switch,
            "candidate_home_prob": p_c4,
            "candidate_pick": _pick(home, away, p_c4),
            "level_only_home_prob": p_level,
            "level_only_pick": _pick(home, away, p_level),
            "path_only_home_prob": p_path,
            "path_only_pick": _pick(home, away, p_path),
            "qb_only_home_prob": p_qb,
            "qb_only_pick": _pick(home, away, p_qb),
            "generated_at_utc": _iso(generated),
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        record["decision_sha256"] = _content_hash(record)
        output.append(record)

    return pd.DataFrame(output)


def append_immutable(
    existing: pd.DataFrame | None,
    new_rows: pd.DataFrame,
) -> pd.DataFrame:
    """Append first-seen decision attempts; reject any rewrite of an existing identity."""
    if existing is None or existing.empty:
        return new_rows.copy().reset_index(drop=True)
    if "game_id" not in existing.columns or "decision_sha256" not in existing.columns:
        raise ValueError("existing Candidate 4 ledger lacks immutable identity fields")
    if existing["game_id"].astype(str).duplicated().any():
        raise ValueError("existing Candidate 4 ledger has duplicate game_id")

    out = existing.copy()
    known = {
        str(row["game_id"]): str(row["decision_sha256"])
        for row in out.to_dict("records")
    }
    additions: list[dict[str, Any]] = []
    for row in new_rows.to_dict("records"):
        game_id = str(row["game_id"])
        digest = str(row["decision_sha256"])
        if game_id in known:
            if known[game_id] != digest:
                raise ValueError(f"immutable Candidate 4 decision rewrite attempted for {game_id}")
            continue
        additions.append(row)
        known[game_id] = digest

    if additions:
        out = pd.concat([out, pd.DataFrame(additions)], ignore_index=True, sort=False)
    return out.reset_index(drop=True)
