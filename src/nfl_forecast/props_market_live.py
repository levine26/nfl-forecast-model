from __future__ import annotations

"""Live/offline sportsbook capture orchestration for LevLine Props Research Beta.

The pure builder accepts already captured provider payloads. The optional network client
fetches The Odds API only when the caller explicitly supplies an authorized API key.
No credential is serialized, logged, or written to artifacts.
"""

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .props_market import PropMarketQuote, build_market_artifact, parse_utc
from .props_market_odds_api import DEFAULT_MARKET_MAP, ingest_odds_api_event
from .props_player_state import normalize_player_name, normalize_team_code


SNAPSHOT_CONTRACT_VERSION = "levline-props-market-snapshot-v0.1"
SPORT_KEY = "americanfootball_nfl"
API_BASE = "https://api.the-odds-api.com/v4"
DEFAULT_REGIONS = "us"
DEFAULT_ODDS_FORMAT = "american"
KICKOFF_TOLERANCE_SECONDS = 30 * 60

# Provider display names are used only to identify the canonical game. Player identity
# is always resolved from the canonical player-state roster and never guessed here.
NFL_TEAM_ALIASES = {
    "arizonacardinals": "ARI",
    "atlantafalcons": "ATL",
    "baltimoreravens": "BAL",
    "buffalobills": "BUF",
    "carolinapanthers": "CAR",
    "chicagobears": "CHI",
    "cincinnatibengals": "CIN",
    "clevelandbrowns": "CLE",
    "dallascowboys": "DAL",
    "denverbroncos": "DEN",
    "detroitlions": "DET",
    "greenbaypackers": "GB",
    "houstontexans": "HOU",
    "indianapoliscolts": "IND",
    "jacksonvillejaguars": "JAX",
    "kansascitychiefs": "KC",
    "lasvegasraiders": "LV",
    "losangeleschargers": "LAC",
    "lachargers": "LAC",
    "losangelesrams": "LAR",
    "larams": "LAR",
    "miamidolphins": "MIA",
    "minnesotavikings": "MIN",
    "newenglandpatriots": "NE",
    "neworleanssaints": "NO",
    "newyorkgiants": "NYG",
    "newyorkjets": "NYJ",
    "philadelphiaeagles": "PHI",
    "pittsburghsteelers": "PIT",
    "sanfrancisco49ers": "SF",
    "seattleseahawks": "SEA",
    "tampabaybuccaneers": "TB",
    "tennesseetitans": "TEN",
    "washingtoncommanders": "WAS",
}


class PropsMarketLiveError(ValueError):
    pass


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _team_token(value: object) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def provider_team_code(value: object) -> str | None:
    token = _team_token(value)
    if token in NFL_TEAM_ALIASES:
        return NFL_TEAM_ALIASES[token]
    code = normalize_team_code(str(value or "").strip())
    if code and len(code) <= 4:
        return code
    return None


def _game_directory(player_state_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    games: dict[str, dict[str, Any]] = {}
    for raw in player_state_rows:
        row = dict(raw)
        game_id = str(row.get("game_id") or "").strip()
        team = normalize_team_code(row.get("team"))
        opponent = normalize_team_code(row.get("opponent"))
        kickoff_raw = row.get("kickoff_timestamp") or row.get("kickoff_utc")
        if not game_id or not team or not opponent or kickoff_raw is None:
            raise PropsMarketLiveError(
                "player-state rows require game_id, team, opponent, and kickoff_timestamp"
            )
        kickoff = parse_utc(kickoff_raw)
        entry = games.setdefault(
            game_id,
            {
                "game_id": game_id,
                "teams": set(),
                "kickoff_utc": kickoff,
                "players": [],
            },
        )
        if entry["kickoff_utc"] != kickoff:
            raise PropsMarketLiveError(f"inconsistent kickoff timestamp for {game_id}")
        entry["teams"].update((team, opponent))
        entry["players"].append(row)

    pair_index: dict[tuple[str, str], dict[str, Any]] = {}
    for game_id, entry in games.items():
        teams = sorted(entry["teams"])
        if len(teams) != 2:
            raise PropsMarketLiveError(f"game {game_id} does not resolve to exactly two teams")
        key = (teams[0], teams[1])
        if key in pair_index:
            raise PropsMarketLiveError(f"duplicate canonical team pair for {key}")
        entry["teams"] = tuple(teams)
        pair_index[key] = entry
    return pair_index


def _match_event(
    event: Mapping[str, Any],
    game_directory: Mapping[tuple[str, str], Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, str | None]:
    home = provider_team_code(event.get("home_team"))
    away = provider_team_code(event.get("away_team"))
    if not home or not away:
        return None, "unresolved_provider_team"
    game = game_directory.get(tuple(sorted((home, away))))
    if game is None:
        return None, "provider_event_not_on_canonical_slate"

    commence_raw = event.get("commence_time")
    if commence_raw is None:
        return None, "provider_event_missing_commence_time"
    try:
        commence = parse_utc(commence_raw)
    except ValueError:
        return None, "provider_event_invalid_commence_time"
    kickoff = game["kickoff_utc"]
    if abs((commence - kickoff).total_seconds()) > KICKOFF_TOLERANCE_SECONDS:
        return None, "provider_event_kickoff_mismatch"
    return game, None


def _player_resolvers(
    game: Mapping[str, Any],
) -> tuple[Any, Any]:
    by_normalized: dict[str, set[str]] = defaultdict(set)
    context: dict[str, dict[str, Any]] = {}
    game_id = str(game["game_id"])

    for raw in game["players"]:
        row = dict(raw)
        player_id = str(row.get("player_id") or "").strip()
        player_name = str(row.get("player_name") or "").strip()
        if not player_id or not player_name:
            continue
        normalized = normalize_player_name(player_name)
        if normalized:
            by_normalized[normalized].add(player_id)
        context[player_id] = {
            "team": normalize_team_code(row.get("team")),
            "opponent": normalize_team_code(row.get("opponent")),
            "position": str(row.get("position") or "").upper() or None,
            "related_market_group_id": f"{game_id}:{normalize_team_code(row.get('team'))}",
        }

    def player_id_resolver(name: str) -> str | None:
        ids = by_normalized.get(normalize_player_name(name), set())
        if len(ids) != 1:
            return None
        return next(iter(ids))

    def player_context_resolver(player_id: str) -> Mapping[str, Any] | None:
        return context.get(str(player_id))

    return player_id_resolver, player_context_resolver


def build_market_snapshot(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    provider_events: Sequence[Mapping[str, Any]],
    captured_at_utc: object,
    provider: str = "the_odds_api",
) -> dict[str, Any]:
    """Convert captured event-odds payloads into stable-ID prospective market artifacts."""

    captured = parse_utc(captured_at_utc)
    game_directory = _game_directory(player_state_rows)
    all_quotes: list[PropMarketQuote] = []
    rejected: list[dict[str, Any]] = []
    ignored_keys: set[str] = set()
    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    seen_games: set[str] = set()

    for event in provider_events:
        if not isinstance(event, Mapping):
            unmatched.append({"reason": "invalid_event_payload"})
            continue
        event_id = str(event.get("id") or "").strip() or None
        game, reason = _match_event(event, game_directory)
        if game is None:
            unmatched.append({"provider_event_id": event_id, "reason": reason})
            continue
        game_id = str(game["game_id"])
        if game_id in seen_games:
            rejected.append(
                {
                    "provider_event_id": event_id,
                    "game_id": game_id,
                    "reason": "duplicate_provider_event_for_game",
                }
            )
            continue
        seen_games.add(game_id)

        kickoff = game["kickoff_utc"]
        if captured >= kickoff:
            rejected.append(
                {
                    "provider_event_id": event_id,
                    "game_id": game_id,
                    "reason": "capture_not_pregame",
                }
            )
            continue

        player_id_resolver, player_context_resolver = _player_resolvers(game)
        result = ingest_odds_api_event(
            event,
            captured_at_utc=captured,
            game_id=game_id,
            player_id_resolver=player_id_resolver,
            player_context_resolver=player_context_resolver,
            provider=provider,
            is_closing=False,
        )
        all_quotes.extend(result.quotes)
        ignored_keys.update(result.ignored_market_keys)
        for row in result.rejected:
            rejected.append(
                {
                    "provider_event_id": event_id,
                    "game_id": game_id,
                    **dict(row),
                }
            )
        matched.append(
            {
                "provider_event_id": event_id,
                "game_id": game_id,
                "kickoff_utc": kickoff.isoformat(),
                "quote_count": len(result.quotes),
                "payload_sha256": payload_sha256(event),
            }
        )

    grouped: dict[tuple[str, str, str], list[PropMarketQuote]] = defaultdict(list)
    for quote in all_quotes:
        grouped[quote.identity].append(quote)

    artifacts: list[dict[str, Any]] = []
    artifact_rejections: list[dict[str, Any]] = []
    for identity in sorted(grouped):
        quotes = grouped[identity]
        try:
            artifacts.append(build_market_artifact(quotes, as_of_utc=captured))
        except ValueError as exc:
            artifact_rejections.append(
                {
                    "game_id": identity[0],
                    "player_id": identity[1],
                    "prop_type": identity[2],
                    "reason": "market_artifact_rejected",
                    "detail": str(exc),
                }
            )
    rejected.extend(artifact_rejections)

    return {
        "contract_version": SNAPSHOT_CONTRACT_VERSION,
        "research_only": True,
        "production_authorized": False,
        "provider": provider,
        "captured_at_utc": captured.isoformat(),
        "sport_key": SPORT_KEY,
        "market_keys_requested": sorted(DEFAULT_MARKET_MAP),
        "market_artifacts": artifacts,
        "audit": {
            "canonical_game_count": len(game_directory),
            "matched_event_count": len(matched),
            "unmatched_event_count": len(unmatched),
            "quote_count": len(all_quotes),
            "artifact_count": len(artifacts),
            "rejected_count": len(rejected),
            "ignored_market_keys": sorted(ignored_keys),
            "matched_events": matched,
            "unmatched_events": unmatched,
            "rejected": rejected,
        },
    }


def _provider_get_json(
    path: str,
    *,
    api_key: str,
    params: Mapping[str, object] | None = None,
    timeout_seconds: float = 20.0,
) -> object:
    if not str(api_key or "").strip():
        raise PropsMarketLiveError("authorized The Odds API key is required")
    query = {"apiKey": api_key, **{k: v for k, v in (params or {}).items() if v is not None}}
    url = f"{API_BASE}{path}?{urlencode(query)}"
    request = Request(url, headers={"User-Agent": "LevLine-Props-Research-Beta/0.1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except HTTPError as exc:
        raise PropsMarketLiveError(
            f"The Odds API request failed for {path} with HTTP {exc.code}"
        ) from exc
    except URLError as exc:
        raise PropsMarketLiveError(f"The Odds API request failed for {path}") from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PropsMarketLiveError(f"The Odds API returned invalid JSON for {path}") from exc


def fetch_live_nfl_prop_events(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    api_key: str,
    regions: str = DEFAULT_REGIONS,
    bookmakers: str | None = None,
    timeout_seconds: float = 20.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch only canonical-slate NFL events, then request supported prop markets per event."""

    game_directory = _game_directory(player_state_rows)
    raw_events = _provider_get_json(
        f"/sports/{SPORT_KEY}/events",
        api_key=api_key,
        params={"dateFormat": "iso"},
        timeout_seconds=timeout_seconds,
    )
    if not isinstance(raw_events, list):
        raise PropsMarketLiveError("The Odds API events response must be a list")

    matched_events: list[dict[str, Any]] = []
    event_odds: list[dict[str, Any]] = []
    discovery_unmatched: list[dict[str, Any]] = []
    market_keys = ",".join(sorted(DEFAULT_MARKET_MAP))

    for event in raw_events:
        if not isinstance(event, Mapping):
            continue
        game, reason = _match_event(event, game_directory)
        if game is None:
            discovery_unmatched.append(
                {
                    "provider_event_id": str(event.get("id") or "") or None,
                    "reason": reason,
                }
            )
            continue
        event_id = str(event.get("id") or "").strip()
        if not event_id:
            discovery_unmatched.append(
                {"provider_event_id": None, "reason": "provider_event_missing_id"}
            )
            continue
        matched_events.append(dict(event))
        payload = _provider_get_json(
            f"/sports/{SPORT_KEY}/events/{event_id}/odds",
            api_key=api_key,
            params={
                "regions": regions,
                "markets": market_keys,
                "oddsFormat": DEFAULT_ODDS_FORMAT,
                "dateFormat": "iso",
                "bookmakers": bookmakers,
            },
            timeout_seconds=timeout_seconds,
        )
        if not isinstance(payload, Mapping):
            raise PropsMarketLiveError(
                f"The Odds API event odds response must be an object for event {event_id}"
            )
        event_odds.append(dict(payload))

    raw_bundle = {
        "provider": "the_odds_api",
        "sport_key": SPORT_KEY,
        "discovery_event_count": len(raw_events),
        "matched_discovery_events": matched_events,
        "discovery_unmatched": discovery_unmatched,
        "event_odds": event_odds,
    }
    return event_odds, raw_bundle


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
