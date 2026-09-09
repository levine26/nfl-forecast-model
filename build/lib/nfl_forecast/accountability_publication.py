from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

import numpy as np
import pandas as pd


def _num(value) -> float | None:
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def _rank_map(frame: pd.DataFrame, column: str, ascending: bool) -> dict[str, int]:
    if frame is None or frame.empty or column not in frame.columns:
        return {}
    work = frame[["team", column]].copy()
    work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=[column])
    work = work.sort_values([column, "team"], ascending=[ascending, True]).reset_index(drop=True)
    return {str(row.team): int(i + 1) for i, row in work.iterrows()}


def _movement_phrase(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("▲"):
        return f"up {text[1:]}"
    if text.startswith("▼"):
        return f"down {text[1:]}"
    if text == "NEW":
        return "new"
    return "steady"


def build_power_editorial(power: pd.DataFrame) -> dict[str, Any]:
    """Create short, metric-grounded explanations for the public power table.

    The prose explains the existing Elo+ ordering. It does not invent a new
    composite power score or feed narrative judgements back into the model.
    """
    generated = datetime.now(timezone.utc).isoformat()
    if power is None or power.empty:
        return {"generated_utc": generated, "teams": []}

    p = power.copy()
    p["rank"] = pd.to_numeric(p.get("rank"), errors="coerce")
    p = p[p["rank"].notna()].sort_values("rank").copy()

    metric_specs = {
        "off_epa": (False, "offensive EPA"),
        "def_epa_allowed": (True, "defensive EPA allowed"),
        "pass_epa": (False, "passing EPA"),
        "recent_win_pct": (False, "recent win rate"),
    }
    ranks = {col: _rank_map(p, col, ascending=asc) for col, (asc, _) in metric_specs.items()}
    n = max(1, len(p))
    teams: list[dict[str, Any]] = []

    for _, row in p.iterrows():
        team = str(row.get("team") or "")
        rank = int(row["rank"])
        movement = str(row.get("movement") or "→")
        candidates = []
        for col, (_, label) in metric_specs.items():
            r = ranks[col].get(team)
            if r is None:
                continue
            candidates.append((r, col, label))
        candidates.sort(key=lambda x: x[0])
        strengths = candidates[:2]
        weakness = max(candidates, key=lambda x: x[0]) if candidates else None

        if strengths:
            first = strengths[0]
            if len(strengths) > 1 and strengths[1][0] <= max(10, int(n * .4)):
                second = strengths[1]
                why = (
                    f"The No. {rank} Elo+ rating is backed by top-{first[0]} {first[2]} and "
                    f"top-{second[0]} {second[2]}."
                )
            else:
                why = f"The No. {rank} Elo+ rating is getting its strongest support from top-{first[0]} {first[2]}."
        else:
            why = f"The current placement is driven by Elo+; the supporting efficiency profile is still incomplete."

        if weakness and weakness[0] >= max(20, int(n * .65)):
            watch = (
                f"The pressure point is {weakness[2]}, which currently ranks {weakness[0]}th of {n}; "
                f"that is the clearest way this ranking can move."
            )
        elif rank <= 8:
            watch = "There is no obvious bottom-tier efficiency flag in the current profile; the next meaningful move likely comes from new game data."
        else:
            watch = "The ranking needs a stronger supporting efficiency signal before Elo+ has a reason to make a large move."

        teams.append({
            "team": team,
            "rank": rank,
            "movement": movement,
            "movement_text": _movement_phrase(movement),
            "elo_plus": _num(row.get("elo_plus")),
            "why_here": why,
            "what_moves_them": watch,
            "supporting_metric_ranks": {
                label: ranks[col].get(team)
                for col, (_, label) in metric_specs.items()
                if ranks[col].get(team) is not None
            },
            "guardrail": "Explanation describes the published Elo+ ordering; it is not a separate ranking model.",
        })

    return {"generated_utc": generated, "teams": teams}


def build_history_scoreboard(official: pd.DataFrame) -> dict[str, Any]:
    """Summarize immutable official forecasts without inventing betting results."""
    generated = datetime.now(timezone.utc).isoformat()
    if official is None or official.empty or "lock_status" not in official.columns:
        return {
            "generated_utc": generated,
            "locked": 0,
            "graded": 0,
            "record": "0-0",
            "winner_accuracy": None,
            "brier": None,
            "market_brier": None,
            "brier_vs_market": None,
            "margin_mae": None,
            "total_mae": None,
            "status": "waiting_for_first_official_lock",
        }

    locked = official[official["lock_status"].astype(str).eq("LOCKED")].copy()
    if locked.empty:
        return {
            "generated_utc": generated,
            "locked": 0,
            "graded": 0,
            "record": "0-0",
            "winner_accuracy": None,
            "brier": None,
            "market_brier": None,
            "brier_vs_market": None,
            "margin_mae": None,
            "total_mae": None,
            "status": "waiting_for_first_official_lock",
        }

    hs = pd.to_numeric(locked.get("actual_home_score"), errors="coerce")
    aw = pd.to_numeric(locked.get("actual_away_score"), errors="coerce")
    graded_mask = hs.notna() & aw.notna()
    graded = locked[graded_mask].copy()

    wins = 0
    losses = 0
    brier = None
    market_brier = None
    brier_vs_market = None
    margin_mae = None
    total_mae = None

    if len(graded):
        correct = graded.get("winner_correct", pd.Series(index=graded.index, dtype=object))
        correct_bool = correct.astype(str).str.lower().map({"true": True, "false": False})
        wins = int(correct_bool.eq(True).sum())
        losses = int(correct_bool.eq(False).sum())

        final_prob = pd.to_numeric(graded.get("final_home_prob"), errors="coerce")
        y = (pd.to_numeric(graded.get("actual_home_score"), errors="coerce") > pd.to_numeric(graded.get("actual_away_score"), errors="coerce")).astype(float)
        valid = final_prob.notna()
        if valid.any():
            brier = float(np.mean((final_prob[valid] - y[valid]) ** 2))

        market = pd.to_numeric(graded.get("market_home_prob"), errors="coerce")
        market_valid = market.notna()
        if market_valid.any():
            market_brier = float(np.mean((market[market_valid] - y[market_valid]) ** 2))
            if brier is not None:
                common = valid & market_valid
                if common.any():
                    model_common = float(np.mean((final_prob[common] - y[common]) ** 2))
                    market_common = float(np.mean((market[common] - y[common]) ** 2))
                    brier_vs_market = market_common - model_common

        m = pd.to_numeric(graded.get("margin_abs_error"), errors="coerce").dropna()
        t = pd.to_numeric(graded.get("total_abs_error"), errors="coerce").dropna()
        if len(m):
            margin_mae = float(m.mean())
        if len(t):
            total_mae = float(t.mean())

    graded_count = int(len(graded))
    accuracy = (wins / graded_count) if graded_count else None
    return {
        "generated_utc": generated,
        "locked": int(len(locked)),
        "graded": graded_count,
        "record": f"{wins}-{losses}",
        "winner_accuracy": accuracy,
        "brier": brier,
        "market_brier": market_brier,
        "brier_vs_market": brier_vs_market,
        "margin_mae": margin_mae,
        "total_mae": total_mae,
        "status": "live_forward_test" if graded_count else "official_locks_waiting_for_results",
        "notes": [
            "Only immutable official T-120 locks are included.",
            "Brier comparison uses games where both LevLine and market probability are available.",
            "No ROI is shown unless a separately defined, timestamped betting rule is being tracked.",
        ],
    }
