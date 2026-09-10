from __future__ import annotations

"""Publication source policy and best-effort advanced-data discovery.

Sunday Signal uses nflverse/nflreadpy as the reproducible analytical backbone,
then distinguishes official/current truth, derived analysis, and manual research
cross-checks. StatMuse is deliberately *not* an automated production dependency.
"""

from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urlparse

import nflreadpy as nfl


OFFICIAL_TEAM_MEDIA_DOMAIN_BY_CODE = {
    "ARI": "arizonacardinals.com",
    "ATL": "atlantafalcons.com",
    "BAL": "baltimoreravens.com",
    "BUF": "buffalobills.com",
    "CAR": "panthers.com",
    "CHI": "chicagobears.com",
    "CIN": "bengals.com",
    "CLE": "clevelandbrowns.com",
    "DAL": "dallascowboys.com",
    "DEN": "denverbroncos.com",
    "DET": "detroitlions.com",
    "GB": "packers.com",
    "HOU": "houstontexans.com",
    "IND": "colts.com",
    "JAX": "jaguars.com",
    "KC": "chiefs.com",
    "LA": "therams.com",
    "LAC": "chargers.com",
    "LV": "raiders.com",
    "MIA": "miamidolphins.com",
    "MIN": "vikings.com",
    "NE": "patriots.com",
    "NO": "neworleanssaints.com",
    "NYG": "giants.com",
    "NYJ": "newyorkjets.com",
    "PHI": "philadelphiaeagles.com",
    "PIT": "steelers.com",
    "SEA": "seahawks.com",
    "SF": "49ers.com",
    "TB": "buccaneers.com",
    "TEN": "tennesseetitans.com",
    "WAS": "commanders.com",
}

OFFICIAL_TEAM_MEDIA_DOMAINS = frozenset(OFFICIAL_TEAM_MEDIA_DOMAIN_BY_CODE.values())

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


def media_domain_allowed(url: str) -> bool:
    try:
        host = (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return False
    return any(host == domain or host.endswith("." + domain) for domain in APPROVED_MEDIA_DOMAINS)


def media_domain_family(url: str) -> str:
    try:
        host = (urlparse(str(url or "")).hostname or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    if host.endswith("sports.yahoo.com"):
        return "yahoo.com"
    if host in {"twitter.com", "x.com"} or host.endswith(".twitter.com") or host.endswith(".x.com"):
        return "x.com"
    return host


def is_direct_media_report_url(url: str) -> bool:
    """Return True only for a direct article/report URL on an approved publisher.

    Publication sources must point to attributable reporting, not publisher homepages,
    team landing pages, schedules, matchup shells, rosters, statistics dashboards,
    search results, or other generic navigation/data pages.
    """
    raw = str(url or "").strip()
    if not raw or not media_domain_allowed(raw):
        return False
    try:
        parsed = urlparse(raw)
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    segments = [segment.lower() for segment in (parsed.path or "").split("/") if segment]
    if not segments:
        return False

    if host == "x.com" or host == "twitter.com" or host.endswith(".x.com") or host.endswith(".twitter.com"):
        return len(segments) >= 3 and segments[1] == "status" and segments[2].isdigit()
    if host == "nfl.com" or host.endswith(".nfl.com"):
        return len(segments) >= 2 and segments[0] == "news"
    if host == "espn.com" or host.endswith(".espn.com"):
        return (
            len(segments) >= 3 and segments[0] == "nfl" and segments[1] == "story"
        ) or (
            len(segments) >= 3 and segments[0] == "video" and segments[1] == "clip"
        )
    if host == "cbssports.com" or host.endswith(".cbssports.com"):
        return len(segments) >= 3 and segments[0] == "nfl" and segments[1] == "news"
    if host == "foxsports.com" or host.endswith(".foxsports.com"):
        return len(segments) >= 3 and segments[0] == "stories" and segments[1] == "nfl"
    if host == "sports.yahoo.com" or host.endswith(".sports.yahoo.com"):
        return (
            len(segments) >= 2 and segments[0] == "articles"
        ) or (
            len(segments) >= 3 and segments[0] == "nfl" and segments[1] in {"article", "news"}
        )
    if host == "yahoo.com" or host.endswith(".yahoo.com"):
        return len(segments) >= 2 and segments[0] in {"articles", "sports"}
    if any(host == domain or host.endswith("." + domain) for domain in OFFICIAL_TEAM_MEDIA_DOMAINS):
        return len(segments) >= 2 and segments[0] in {"news", "video", "podcasts"}
    if host == "apnews.com" or host.endswith(".apnews.com"):
        return len(segments) >= 2 and segments[0] == "article"

    generic = {
        "team", "teams", "schedule", "schedules", "scores", "stats", "standings",
        "roster", "players", "injuries", "transactions", "search", "tickets",
        "fantasy", "odds", "watch", "live", "games", "game",
    }
    if any(segment in generic for segment in segments[:2]):
        return False
    return len(segments) >= 2


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
