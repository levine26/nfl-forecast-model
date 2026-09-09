from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1:"st",2:"nd",3:"rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _rank_map(frame: pd.DataFrame, column: str, ascending: bool) -> dict[str, int]:
    work = frame[["team", column]].copy()
    work[column] = pd.to_numeric(work[column], errors="coerce")
    work = work.dropna(subset=[column]).sort_values([column, "team"], ascending=[ascending, True]).reset_index(drop=True)
    return {str(row.team): int(index + 1) for index, row in work.iterrows()}


def _movement_phrase(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("▲"):
        return f"up {text[1:]}"
    if text.startswith("▼"):
        return f"down {text[1:]}"
    if text == "NEW":
        return "new"
    return "steady"


def build_power_editorial_v2(power: pd.DataFrame) -> dict[str, Any]:
    """Explain Elo ordering without pretending every efficiency metric agrees with it."""
    generated = datetime.now(timezone.utc).isoformat()
    if power is None or power.empty:
        return {"generated_utc": generated, "teams": [], "editorial_version":"power-v2"}

    p = power.copy()
    p["rank"] = pd.to_numeric(p.get("rank"), errors="coerce")
    p = p[p["rank"].notna()].sort_values("rank").copy()
    specs = {
        "off_epa": (False, "offensive EPA"),
        "def_epa_allowed": (True, "defensive EPA allowed"),
        "pass_epa": (False, "passing EPA"),
        "recent_win_pct": (False, "recent win rate"),
    }
    ranks = {col: _rank_map(p, col, asc) for col, (asc, _) in specs.items()}
    n = len(p)
    teams = []

    for _, row in p.iterrows():
        team = str(row.get("team") or "")
        elo_rank = int(row["rank"])
        metric_rows = [(ranks[col].get(team), label) for col, (_, label) in specs.items() if ranks[col].get(team) is not None]
        metric_rows.sort(key=lambda pair: pair[0])
        metric_ranks = [rank for rank, _ in metric_rows]
        avg_metric_rank = sum(metric_ranks) / len(metric_ranks) if metric_ranks else None
        best = metric_rows[0] if metric_rows else None
        worst = metric_rows[-1] if metric_rows else None

        if avg_metric_rank is None:
            why = f"Elo+ places {team} at No. {elo_rank}; the supporting efficiency sample is still incomplete."
            tension = "incomplete"
        elif avg_metric_rank <= elo_rank - 6:
            why = (
                f"Elo+ has {team} at No. {elo_rank}, but the recent efficiency profile looks stronger than that placement. "
                f"Its best supporting mark is {_ordinal(best[0])} in {best[1]}."
            )
            tension = "efficiency_stronger_than_elo"
        elif avg_metric_rank >= elo_rank + 6:
            why = (
                f"Elo+ still has {team} at No. {elo_rank}, while the recent efficiency profile is much shakier. "
                f"The biggest warning is {_ordinal(worst[0])} in {worst[1]}."
            )
            tension = "efficiency_weaker_than_elo"
        else:
            if best and worst and best[0] <= max(8, int(n*.25)) and worst[0] >= min(n, 24):
                why = (
                    f"Elo+ puts {team} at No. {elo_rank}, and the efficiency profile is split: {_ordinal(best[0])} in {best[1]}, "
                    f"but {_ordinal(worst[0])} in {worst[1]}."
                )
                tension = "mixed"
            elif best:
                why = f"Elo+ and the supporting profile are broadly aligned at No. {elo_rank}; the clearest strength is {_ordinal(best[0])} in {best[1]}."
                tension = "aligned"
            else:
                why = f"Elo+ places {team} at No. {elo_rank}."
                tension = "incomplete"

        if tension == "efficiency_stronger_than_elo":
            watch = "If that efficiency holds against new 2026 opponents, Elo has room to catch up quickly."
        elif tension == "efficiency_weaker_than_elo":
            watch = "The next few games will tell us whether Elo is carrying stale strength or the efficiency dip is temporary."
        elif worst and worst[0] >= 24:
            watch = f"The pressure point is {worst[1]}, currently {_ordinal(worst[0])} of {n}."
        else:
            watch = "There is no single extreme metric pulling against the ranking; new game data should drive the next move."

        teams.append({
            "team": team,
            "rank": elo_rank,
            "movement": str(row.get("movement") or "→"),
            "movement_text": _movement_phrase(row.get("movement")),
            "elo_plus": float(row.get("elo_plus")) if pd.notna(row.get("elo_plus")) else None,
            "why_here": why,
            "what_moves_them": watch,
            "tension": tension,
            "average_efficiency_rank": avg_metric_rank,
            "supporting_metric_ranks": {label: ranks[col].get(team) for col, (_, label) in specs.items() if ranks[col].get(team) is not None},
            "guardrail": "Elo+ alone sets the published rank; efficiency is shown as supporting or conflicting context, never retrofitted into a hidden composite.",
        })

    return {"generated_utc": generated, "teams": teams, "editorial_version":"power-v2"}
