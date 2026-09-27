from __future__ import annotations

"""Publication postconditions for the immutable T-120 lock."""

from datetime import datetime, timezone

import pandas as pd

from .publish import ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY, LOCK_WINDOW_MINUTES, kickoff_utc


def _as_utc(value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _verify_ats_receipt(locked: pd.Series, gid: str, failures: list[str]) -> None:
    gameday = str(locked.get("gameday") or "")[:10]
    if gameday < ATS_LOCK_POLICY_EFFECTIVE_GAMEDAY:
        return

    status = str(locked.get("locked_ats_status") or "").strip().upper()
    model_margin = pd.to_numeric(locked.get("locked_ats_model_margin_home"), errors="coerce")
    market_margin = pd.to_numeric(locked.get("locked_ats_market_margin_home"), errors="coerce")
    if pd.isna(model_margin) or pd.isna(market_margin):
        if status != "UNAVAILABLE":
            failures.append(f"{gid}: missing ATS inputs must lock as UNAVAILABLE")
        return

    edge = float(model_margin) - float(market_margin)
    if abs(edge) <= 1e-12:
        if status != "NO_EDGE":
            failures.append(f"{gid}: zero ATS edge must lock as NO_EDGE")
        return

    if status != "VALUE":
        failures.append(f"{gid}: nonzero ATS edge is missing VALUE lock")
        return

    home = str(locked.get("home_team") or "")
    away = str(locked.get("away_team") or "")
    expected_side = home if edge > 0 else away
    expected_spread = -float(market_margin) if edge > 0 else float(market_margin)
    side = str(locked.get("locked_ats_pick_team") or "")
    spread = pd.to_numeric(locked.get("locked_ats_pick_market_spread"), errors="coerce")
    if side != expected_side:
        failures.append(f"{gid}: locked ATS side {side or 'missing'} contradicts lock-row model-vs-market edge")
    if pd.isna(spread) or abs(float(spread) - expected_spread) > 1e-9:
        failures.append(f"{gid}: locked ATS grading spread is missing or not the selected side's market spread")


def verify_pregame_locks(
    current: pd.DataFrame,
    official: pd.DataFrame,
    now_utc: datetime,
    lock_window_minutes: float = LOCK_WINDOW_MINUTES,
) -> list[str]:
    """Validate that every currently eligible game has one coherent lock row.

    This function never creates or modifies a lock. ``publish.write_outputs`` is
    the sole authority for locking; this is only a fail-closed workflow check.
    """
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    failures: list[str] = []
    eligible: list[str] = []

    if not official.empty and "game_id" in official.columns:
        counts = official["game_id"].astype(str).value_counts()
        duplicates = sorted(counts[counts > 1].index.tolist())
        if duplicates:
            failures.append(f"duplicate official game ids: {duplicates}")

    for _, row in current.iterrows():
        gid = str(row.get("game_id") or "")
        if not gid:
            continue
        try:
            kickoff = kickoff_utc(row.get("gameday"), row.get("gametime"))
        except Exception:
            continue
        minutes = (kickoff - now_utc).total_seconds() / 60.0
        if not (0.0 < minutes <= lock_window_minutes):
            continue
        eligible.append(gid)

        if official.empty or "game_id" not in official.columns:
            failures.append(f"{gid}: no official history exists at T-{minutes:.1f}")
            continue
        match = official[official["game_id"].astype(str).eq(gid)]
        if len(match) != 1:
            failures.append(f"{gid}: expected exactly one official row at T-{minutes:.1f}, found {len(match)}")
            continue
        locked = match.iloc[0]
        if str(locked.get("lock_status")) != "LOCKED":
            failures.append(f"{gid}: official row is not LOCKED")
        if pd.isna(locked.get("final_home_prob")) or not str(locked.get("pick") or "").strip():
            failures.append(f"{gid}: locked probability/pick is missing")
        _verify_ats_receipt(locked, gid, failures)
        try:
            lock_time = _as_utc(str(locked.get("lock_timestamp_utc")))
            lock_minutes = (kickoff - lock_time).total_seconds() / 60.0
            if not (0.0 < lock_minutes <= lock_window_minutes):
                failures.append(f"{gid}: stored lock time is outside T-120 ({lock_minutes:.1f} minutes)")
        except Exception as exc:
            failures.append(f"{gid}: invalid lock timestamp ({exc})")

    if failures:
        raise RuntimeError("Pregame lock postcondition failed: " + "; ".join(failures))
    return eligible
