from __future__ import annotations

"""Live/offline sportsbook capture orchestration for LevLine Props Research Beta.

The pure builder accepts already captured provider payloads. Live capture supports
authorized sportsbook providers with deterministic failover and explicit provenance.
No credential is serialized, logged, or written to artifacts.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
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
PROPLINE_API_BASE = "https://api.prop-line.com/v1"
# PropLine intentionally publishes this read-only, shared, rate-limited free-tier
# credential in its MIT-licensed MCP server so zero-config clients can make their
# first request. Keep it LAST in the fallback order; personal credentials always win.
PROPLINE_PUBLIC_DEMO_KEY = "be2b8487fcfacb1fbc292a8aa925a84c"
SPORTSGAMEODDS_API_BASE = "https://api.sportsgameodds.com/v2"
DEFAULT_REGIONS = "us"
DEFAULT_ODDS_FORMAT = "american"
KICKOFF_TOLERANCE_SECONDS = 30 * 60

SPORTSGAMEODDS_STAT_MAP = {
    "passing_yards": "player_pass_yds",
    "rushing_yards": "player_rush_yds",
    "receiving_yards": "player_reception_yds",
    "receiving_receptions": "player_receptions",
    "passing_touchdowns": "player_pass_tds",
    "rushing_touchdowns": "player_rush_tds",
    "receiving_touchdowns": "player_reception_tds",
    "touchdowns": "player_anytime_td",
}

# DFS pick'em and exchange prices are not sportsbook quotes. Keep them out of the
# sportsbook consensus even if a higher-tier SportsGameOdds account exposes them.
SPORTSGAMEODDS_NON_SPORTSBOOKS = {
    "prizepicks",
    "underdog",
    "polymarket",
    "kalshi",
}


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


def _request_provider_json(
    path: str,
    *,
    api_key: str,
    api_base: str,
    provider_label: str,
    params: Mapping[str, object] | None = None,
    timeout_seconds: float = 20.0,
) -> object:
    if not str(api_key or "").strip():
        raise PropsMarketLiveError(f"authorized {provider_label} key is required")
    query = {"apiKey": api_key, **{k: v for k, v in (params or {}).items() if v is not None}}
    url = f"{api_base}{path}?{urlencode(query)}"
    request = Request(url, headers={"User-Agent": "LevLine-Props-Research-Beta/0.1"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except HTTPError as exc:
        raise PropsMarketLiveError(
            f"{provider_label} request failed for {path} with HTTP {exc.code}"
        ) from exc
    except URLError as exc:
        raise PropsMarketLiveError(f"{provider_label} request failed for {path}") from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PropsMarketLiveError(f"{provider_label} returned invalid JSON for {path}") from exc


def _provider_get_json(
    path: str,
    *,
    api_key: str,
    params: Mapping[str, object] | None = None,
    timeout_seconds: float = 20.0,
) -> object:
    return _request_provider_json(
        path,
        api_key=api_key,
        api_base=API_BASE,
        provider_label="The Odds API",
        params=params,
        timeout_seconds=timeout_seconds,
    )


def _propline_get_json(
    path: str,
    *,
    api_key: str,
    params: Mapping[str, object] | None = None,
    timeout_seconds: float = 20.0,
) -> object:
    return _request_provider_json(
        path,
        api_key=api_key,
        api_base=PROPLINE_API_BASE,
        provider_label="PropLine",
        params=params,
        timeout_seconds=timeout_seconds,
    )


def _sportsgameodds_get_json(
    path: str,
    *,
    api_key: str,
    params: Mapping[str, object] | None = None,
    timeout_seconds: float = 20.0,
) -> object:
    if not str(api_key or "").strip():
        raise PropsMarketLiveError("authorized SportsGameOdds key is required")
    query = {k: v for k, v in (params or {}).items() if v is not None}
    url = f"{SPORTSGAMEODDS_API_BASE}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    request = Request(
        url,
        headers={
            "User-Agent": "LevLine-Props-Research-Beta/0.1",
            "x-api-key": api_key,
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
    except HTTPError as exc:
        raise PropsMarketLiveError(
            f"SportsGameOdds request failed for {path} with HTTP {exc.code}"
        ) from exc
    except URLError as exc:
        raise PropsMarketLiveError(
            f"SportsGameOdds request failed for {path}"
        ) from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PropsMarketLiveError(
            f"SportsGameOdds returned invalid JSON for {path}"
        ) from exc


def _sportsgameodds_player_name(
    players: Mapping[str, Any],
    player_id: str,
) -> str | None:
    raw = players.get(player_id)
    if not isinstance(raw, Mapping):
        return None
    name = str(raw.get("name") or "").strip()
    if name:
        return name
    first = str(raw.get("firstName") or "").strip()
    last = str(raw.get("lastName") or "").strip()
    combined = " ".join(part for part in (first, last) if part)
    return combined or None


def _sportsgameodds_event_to_odds_api(
    event: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize one SportsGameOdds NFL event into LevLine's stable market adapter shape."""

    event_id = str(event.get("eventID") or "").strip()
    teams = event.get("teams")
    status = event.get("status")
    players = event.get("players")
    odds = event.get("odds")
    if not event_id or not isinstance(teams, Mapping) or not isinstance(status, Mapping):
        raise PropsMarketLiveError("SportsGameOdds event is missing event/team/status identity")
    if not isinstance(players, Mapping):
        players = {}
    if not isinstance(odds, Mapping):
        odds = {}

    home = teams.get("home")
    away = teams.get("away")
    home_names = home.get("names") if isinstance(home, Mapping) else None
    away_names = away.get("names") if isinstance(away, Mapping) else None
    home_name = (
        str(home_names.get("long") or "").strip()
        if isinstance(home_names, Mapping)
        else ""
    )
    away_name = (
        str(away_names.get("long") or "").strip()
        if isinstance(away_names, Mapping)
        else ""
    )
    commence = status.get("startsAt")
    if not home_name or not away_name or not commence:
        raise PropsMarketLiveError(
            f"SportsGameOdds event {event_id} is missing canonical team or kickoff fields"
        )

    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(
        lambda: defaultdict(lambda: {"outcomes": [], "last_update": None})
    )

    for raw_odd in odds.values():
        if not isinstance(raw_odd, Mapping):
            continue
        if str(raw_odd.get("periodID") or "") != "game":
            continue
        stat_id = str(raw_odd.get("statID") or "").strip()
        market_key = SPORTSGAMEODDS_STAT_MAP.get(stat_id)
        if market_key is None:
            continue

        bet_type = str(raw_odd.get("betTypeID") or "").strip().lower()
        side = str(raw_odd.get("sideID") or "").strip().lower()
        if market_key == "player_anytime_td":
            if bet_type != "yn" or side not in {"yes", "no"}:
                continue
        elif bet_type != "ou" or side not in {"over", "under"}:
            continue

        player_id = str(
            raw_odd.get("playerID") or raw_odd.get("statEntityID") or ""
        ).strip()
        player_name = _sportsgameodds_player_name(players, player_id)
        if not player_id or not player_name:
            continue

        by_book = raw_odd.get("byBookmaker")
        if not isinstance(by_book, Mapping):
            continue
        for book_key_raw, book_raw in by_book.items():
            if not isinstance(book_raw, Mapping) or book_raw.get("available") is not True:
                continue
            book_key = str(book_key_raw or "").strip().lower()
            if not book_key or book_key in SPORTSGAMEODDS_NON_SPORTSBOOKS:
                continue
            try:
                price = float(book_raw.get("odds"))
            except (TypeError, ValueError):
                continue

            if market_key == "player_anytime_td":
                outcome = {
                    "name": side.title(),
                    "description": player_name,
                    "price": price,
                }
            else:
                try:
                    line = float(book_raw.get("overUnder"))
                except (TypeError, ValueError):
                    continue
                outcome = {
                    "name": side.title(),
                    "description": player_name,
                    "price": price,
                    "point": line,
                }

            bucket = grouped[book_key][market_key]
            bucket["outcomes"].append(outcome)
            updated = book_raw.get("lastUpdatedAt")
            if updated and (bucket["last_update"] is None or str(updated) > str(bucket["last_update"])):
                bucket["last_update"] = str(updated)

    bookmakers: list[dict[str, Any]] = []
    for book_key in sorted(grouped):
        markets: list[dict[str, Any]] = []
        book_last_update: str | None = None
        for market_key in sorted(grouped[book_key]):
            row = grouped[book_key][market_key]
            outcomes = row["outcomes"]
            if not outcomes:
                continue
            last_update = row["last_update"]
            market = {"key": market_key, "outcomes": outcomes}
            if last_update:
                market["last_update"] = last_update
                if book_last_update is None or last_update > book_last_update:
                    book_last_update = last_update
            markets.append(market)
        if markets:
            bookmaker = {
                "key": book_key,
                "title": book_key,
                "markets": markets,
            }
            if book_last_update:
                bookmaker["last_update"] = book_last_update
            bookmakers.append(bookmaker)

    return {
        "id": event_id,
        "home_team": home_name,
        "away_team": away_name,
        "commence_time": commence,
        "bookmakers": bookmakers,
    }


def fetch_sportsgameodds_nfl_prop_events(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    api_key: str,
    bookmakers: str | None = None,
    timeout_seconds: float = 20.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch one bounded NFL slate from SportsGameOdds and normalize it for LevLine."""

    game_directory = _game_directory(player_state_rows)
    kickoffs = sorted(game["kickoff_utc"] for game in game_directory.values())
    if not kickoffs:
        raise PropsMarketLiveError("cannot query SportsGameOdds without a canonical slate")

    params: dict[str, object] = {
        "leagueID": "NFL",
        "oddsAvailable": "true",
        "started": "false",
        "includeAltLines": "false",
        "includeOpposingOdds": "true",
        "limit": 50,
        "startsAfter": (kickoffs[0] - timedelta(hours=1)).isoformat(),
        "startsBefore": (kickoffs[-1] + timedelta(hours=1)).isoformat(),
    }
    if bookmakers:
        params["bookmakerID"] = bookmakers

    payload = _sportsgameodds_get_json(
        "/events",
        api_key=api_key,
        params=params,
        timeout_seconds=timeout_seconds,
    )
    if not isinstance(payload, Mapping):
        raise PropsMarketLiveError("SportsGameOdds events response must be an object")
    raw_events = payload.get("data")
    if not isinstance(raw_events, list):
        raise PropsMarketLiveError("SportsGameOdds events response must contain a data list")
    if payload.get("nextCursor"):
        raise PropsMarketLiveError(
            "SportsGameOdds slate exceeded one page; refusing partial live market capture"
        )

    normalized: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, Mapping):
            rejected.append({"reason": "invalid_event_payload"})
            continue
        try:
            normalized.append(_sportsgameodds_event_to_odds_api(event))
        except PropsMarketLiveError as exc:
            rejected.append(
                {
                    "provider_event_id": str(event.get("eventID") or "") or None,
                    "reason": "normalization_failed",
                    "detail": str(exc),
                }
            )

    raw_bundle = {
        "provider": "sportsgameodds",
        "sport_key": SPORT_KEY,
        "provider_response_sha256": payload_sha256(payload),
        "raw_provider_events": raw_events,
        "normalization_rejected": rejected,
        "event_odds": normalized,
    }
    return normalized, raw_bundle


def fetch_live_nfl_prop_events(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    api_key: str,
    regions: str = DEFAULT_REGIONS,
    bookmakers: str | None = None,
    timeout_seconds: float = 20.0,
    provider: str = "the_odds_api",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Fetch canonical-slate NFL events and supported props from one authorized provider."""

    if provider == "the_odds_api":
        getter = _provider_get_json
        discovery_params: dict[str, object] = {"dateFormat": "iso"}
        odds_params = {
            "regions": regions,
            "markets": ",".join(sorted(DEFAULT_MARKET_MAP)),
            "oddsFormat": DEFAULT_ODDS_FORMAT,
            "dateFormat": "iso",
            "bookmakers": bookmakers,
        }
    elif provider == "propline":
        getter = _propline_get_json
        discovery_params = {}
        odds_params = {
            "markets": ",".join(sorted(DEFAULT_MARKET_MAP)),
            "bookmakers": bookmakers,
        }
    elif provider == "sportsgameodds":
        return fetch_sportsgameodds_nfl_prop_events(
            player_state_rows=player_state_rows,
            api_key=api_key,
            bookmakers=bookmakers,
            timeout_seconds=timeout_seconds,
        )
    else:
        raise PropsMarketLiveError(f"unsupported live Props market provider: {provider}")

    game_directory = _game_directory(player_state_rows)
    raw_events = getter(
        f"/sports/{SPORT_KEY}/events",
        api_key=api_key,
        params=discovery_params,
        timeout_seconds=timeout_seconds,
    )
    if not isinstance(raw_events, list):
        raise PropsMarketLiveError(f"{provider} events response must be a list")

    matched_events: list[dict[str, Any]] = []
    event_odds: list[dict[str, Any]] = []
    discovery_unmatched: list[dict[str, Any]] = []

    for event in raw_events:
        if not isinstance(event, Mapping):
            continue
        game, reason = _match_event(event, game_directory)
        if game is None:
            discovery_unmatched.append(
                {
                    "provider_event_id": str(event.get("id") or "") or None,
                    "home_team": event.get("home_team"),
                    "away_team": event.get("away_team"),
                    "commence_time": event.get("commence_time"),
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
        payload = getter(
            f"/sports/{SPORT_KEY}/events/{event_id}/odds",
            api_key=api_key,
            params=odds_params,
            timeout_seconds=timeout_seconds,
        )
        if not isinstance(payload, Mapping):
            raise PropsMarketLiveError(
                f"{provider} event odds response must be an object for event {event_id}"
            )
        event_odds.append(dict(payload))

    raw_bundle = {
        "provider": provider,
        "sport_key": SPORT_KEY,
        "discovery_event_count": len(raw_events),
        "matched_discovery_events": matched_events,
        "discovery_unmatched": discovery_unmatched,
        "event_odds": event_odds,
    }
    return event_odds, raw_bundle


def fetch_live_nfl_prop_events_with_fallback(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    the_odds_api_key: str = "",
    propline_api_key: str = "",
    sportsgameodds_api_key: str = "",
    regions: str = DEFAULT_REGIONS,
    bookmakers: str | None = None,
    timeout_seconds: float = 20.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Try independent sportsbook providers in order while preserving fail-closed provenance."""

    attempts: list[dict[str, Any]] = []
    configured = [
        ("the_odds_api", "the_odds_api", str(the_odds_api_key or "").strip()),
        ("propline", "propline", str(propline_api_key or "").strip()),
        (
            "sportsgameodds",
            "sportsgameodds",
            str(sportsgameodds_api_key or "").strip(),
        ),
        ("propline_demo", "propline", PROPLINE_PUBLIC_DEMO_KEY),
    ]

    errors: list[str] = []
    for attempt_name, provider, api_key in configured:
        if not api_key:
            attempts.append({"provider": attempt_name, "status": "not_configured"})
            continue
        try:
            events, raw_bundle = fetch_live_nfl_prop_events(
                player_state_rows=player_state_rows,
                api_key=api_key,
                regions=regions,
                bookmakers=bookmakers,
                timeout_seconds=timeout_seconds,
                provider=provider,
            )
        except PropsMarketLiveError as exc:
            detail = str(exc)
            attempts.append(
                {"provider": attempt_name, "status": "failed", "detail": detail}
            )
            errors.append(f"{attempt_name}: {detail}")
            continue

        attempts.append({"provider": attempt_name, "status": "selected"})
        credential_mode = (
            "shared_public_demo" if attempt_name == "propline_demo" else "configured"
        )
        return events, {
            **raw_bundle,
            "provider_attempts": attempts,
            "credential_mode": credential_mode,
        }

    raise PropsMarketLiveError(
        "all configured live Props market providers failed: " + "; ".join(errors)
    )

def utc_now() -> datetime:
    return datetime.now(timezone.utc)
