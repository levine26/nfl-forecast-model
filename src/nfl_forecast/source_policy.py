from __future__ import annotations

"""Publication source policy and best-effort advanced-data discovery.

Sunday Signal uses nflverse/nflreadpy as the reproducible analytical backbone,
then distinguishes official/current truth, derived analysis, and manual research
cross-checks. StatMuse is deliberately *not* an automated production dependency.
"""

from datetime import datetime, timezone
from typing import Any, Callable

import nflreadpy as nfl


OFFICIAL_TEAM_MEDIA_DOMAINS = frozenset(
    {
        "49ers.com",
        "arizonacardinals.com",
        "atlantafalcons.com",
        "baltimoreravens.com",
        "bengals.com",
        "buffalobills.com",
        "buccaneers.com",
        "chargers.com",
        "chicagobears.com",
        "chiefs.com",
        "clevelandbrowns.com",
        "colts.com",
        "commanders.com",
        "dallascowboys.com",
        "denverbroncos.com",
        "detroitlions.com",
        "houstontexans.com",
        "jaguars.com",
        "miamidolphins.com",
        "neworleanssaints.com",
        "newyorkjets.com",
        "packers.com",
        "panthers.com",
        "patriots.com",
        "philadelphiaeagles.com",
        "raiders.com",
        "seahawks.com",
        "steelers.com",
        "tennesseetitans.com",
        "therams.com",
        "vikings.com",
        "giants.com",
    }
)

APPROVED_MEDIA_DOMAINS = frozenset(
    {
        "apnews.com",
        "cbssports.com",
        "espn.com",
        "foxsports.com",
        "nbcsports.com",
        "nfl.com",
        "nytimes.com",
        "si.com",
        "sports.yahoo.com",
        "theathletic.com",
        "twitter.com",
        "x.com",
        "yahoo.com",
    }
) | OFFICIAL_TEAM_MEDIA_DOMAINS


SOURCE_MATRIX = [
    {
        "role": "quantitative_backbone",
        "source": "nflverse / nflreadpy",
        "use": "schedule, play-by-play, EPA, player/team stats, participation, rosters and identifiers",
        "automation": "production",
    },
    {
        "role": "advanced_player_context",
        "source": "NFL Next Gen Stats via nflverse",
        "use": "passing, rushing and receiving context when fields and season coverage are available",
        "automation": "production_best_effort",
    },
    {
        "role": "advanced_historical_context",
        "source": "PFR advanced stats via nflverse",
        "use": "historical passing/rushing/receiving context and cross-checking",
        "automation": "production_best_effort",
    },
    {
        "role": "official_truth",
        "source": "NFL.com / official team sources / official gamebooks",
        "use": "injuries, starters, transactions, venue/event facts and official game statistics",
        "automation": "production_when_supported",
    },
    {
        "role": "research_cross_check",
        "source": "StatMuse / PFR-style career queries",
        "use": "manual QA for career counts and historical claims; never required for production",
        "automation": "manual_only",
    },
]


def provenance_grade(*, independent_sources: int = 0, official: bool = False, derived: bool = False, conflict: bool = False) -> str:
    if conflict:
        return "HOLD"
    if independent_sources >= 2:
        return "A"
    if official or independent_sources == 1:
        return "B"
    if derived:
        return "C"
    return "HOLD"


def _rows(frame: Any) -> int | None:
    if frame is None:
        return None
    try:
        return int(len(frame))
    except Exception:
        return None


def _try(status: dict[str, Any], key: str, fn: Callable[[], Any]) -> Any | None:
    try:
        frame = fn()
        status[key] = {"status": "healthy", "rows": _rows(frame)}
        return frame
    except Exception as exc:
        status[key] = {"status": "degraded", "error": str(exc)[:220]}
        return None


def probe_advanced_sources(season: int) -> dict[str, Any]:
    """Probe free/public analytical supplements without making them hard dependencies."""
    years = list(range(max(2016, season - 4), season))
    status: dict[str, Any] = {
        "status": "healthy",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "seasons": years,
        "policy": "Best-effort context only; no advanced source may block or silently alter LevLine.",
    }

    player_stats = getattr(nfl, "load_player_stats", None)
    if player_stats:
        _try(status, "player_stats", lambda: player_stats(years))
    else:
        status["player_stats"] = {"status": "unavailable", "note": "loader not exposed by installed nflreadpy"}

    ngs = getattr(nfl, "load_nextgen_stats", None)
    if ngs:
        for stat_type in ("passing", "rushing", "receiving"):
            _try(status, f"ngs_{stat_type}", lambda stat_type=stat_type: ngs(years, stat_type=stat_type))
    else:
        for stat_type in ("passing", "rushing", "receiving"):
            status[f"ngs_{stat_type}"] = {"status": "unavailable", "note": "loader not exposed by installed nflreadpy"}

    pfr = getattr(nfl, "load_pfr_advstats", None)
    if pfr:
        for stat_type in ("pass", "rush", "rec"):
            _try(
                status,
                f"pfr_{stat_type}",
                lambda stat_type=stat_type: pfr(years, stat_type=stat_type, summary_level="week"),
            )
    else:
        for stat_type in ("pass", "rush", "rec"):
            status[f"pfr_{stat_type}"] = {"status": "unavailable", "note": "loader not exposed by installed nflreadpy"}

    players = getattr(nfl, "load_players", None)
    if players:
        _try(status, "player_id_map", players)
    else:
        status["player_id_map"] = {"status": "unavailable", "note": "loader not exposed by installed nflreadpy"}

    usable = [v for k, v in status.items() if isinstance(v, dict) and k not in {"policy"} and v.get("status") == "healthy"]
    if not usable:
        status["status"] = "degraded"
    status["matrix"] = SOURCE_MATRIX
    return status
