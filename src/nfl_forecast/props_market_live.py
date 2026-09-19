from __future__ import annotations

"""Live/offline sportsbook capture orchestration for LevLine Props Research Beta.

The pure builder accepts already captured provider payloads. Live capture supports
authorized sportsbook providers with deterministic failover and explicit provenance.
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
PROPLINE_API_BASE = "https://api.prop-line.com/v1"
DRAFTKINGS_NFL_EVENT_GROUP = "88808"
DRAFTKINGS_PUBLIC_CANDIDATES = (
    ("sportsbook.draftkings.com", "US-SB"),
    ("sportsbook.draftkings.com", "US-NJ-SB"),
    ("sportsbook.draftkings.com", "US-PA-SB"),
    ("sportsbook-us-nj.draftkings.com", "US-SB"),
    ("sportsbook-us-pa.draftkings.com", "US-SB"),
)
DRAFTKINGS_MARKET_HINTS = (
    ("player receiving yards", "player_reception_yds"),
    ("receiving yards", "player_reception_yds"),
    ("player rushing yards", "player_rush_yds"),
    ("rushing yards", "player_rush_yds"),
    ("player passing yards", "player_pass_yds"),
    ("passing yards", "player_pass_yds"),
    ("player receptions", "player_receptions"),
    ("receptions", "player_receptions"),
    ("player passing tds", "player_pass_tds"),
    ("passing touchdowns", "player_pass_tds"),
    ("passing tds", "player_pass_tds"),
    ("player rushing tds", "player_rush_tds"),
    ("rushing touchdowns", "player_rush_tds"),
    ("player receiving tds", "player_reception_tds"),
    ("receiving touchdowns", "player_reception_tds"),
    ("anytime touchdown scorer", "player_anytime_td"),
    ("to score a touchdown", "player_anytime_td"),
)
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



def _draftkings_public_get_json(
    *,
    timeout_seconds: float = 20.0,
) -> tuple[dict[str, Any], str]:
    """Fetch the public DraftKings NFL event-group JSON from a deterministic host list."""

    errors: list[str] = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://sportsbook.draftkings.com/leagues/football/nfl",
    }
    for host, site_code in DRAFTKINGS_PUBLIC_CANDIDATES:
        url = (
            f"https://{host}/sites/{site_code}/api/v5/eventgroups/"
            f"{DRAFTKINGS_NFL_EVENT_GROUP}?format=json"
        )
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
        except HTTPError as exc:
            errors.append(f"{host}/{site_code}: HTTP {exc.code}")
            continue
        except URLError:
            errors.append(f"{host}/{site_code}: network error")
            continue
        try:
            decoded = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            errors.append(f"{host}/{site_code}: invalid JSON")
            continue
        if not isinstance(decoded, Mapping):
            errors.append(f"{host}/{site_code}: root is not an object")
            continue
        return dict(decoded), url

    detail = "; ".join(errors) if errors else "no endpoint candidates"
    raise PropsMarketLiveError(f"DraftKings public feed failed: {detail}")


def _draftkings_market_key(*labels: object) -> str | None:
    text = " ".join(str(value or "").strip().lower() for value in labels)
    for hint, key in DRAFTKINGS_MARKET_HINTS:
        if hint in text:
            return key
    return None


def _draftkings_price(value: object) -> float | None:
    if isinstance(value, Mapping):
        value = value.get("american") or value.get("americanOdds")
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _draftkings_line(outcome: Mapping[str, Any]) -> float | None:
    value = outcome.get("line")
    if value is None:
        value = outcome.get("lineDisplay")
    if value is None:
        return None
    text = str(value).strip().replace("½", ".5")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _draftkings_participant(
    outcome: Mapping[str, Any],
    market_label: object,
) -> str | None:
    participant = outcome.get("participant")
    if isinstance(participant, Mapping):
        for key in ("name", "displayName", "shortName"):
            value = str(participant.get(key) or "").strip()
            if value:
                return value
    elif participant is not None:
        value = str(participant).strip()
        if value:
            return value

    participants = outcome.get("participants")
    if isinstance(participants, Sequence) and not isinstance(participants, (str, bytes)):
        for raw in participants:
            if not isinstance(raw, Mapping):
                continue
            for key in ("name", "displayName", "shortName"):
                value = str(raw.get(key) or "").strip()
                if value:
                    return value

    label = str(outcome.get("label") or "").strip()
    if label.lower() not in {"", "over", "under", "yes", "no"}:
        return label

    market_text = str(market_label or "").strip()
    for separator in (" - ", " – ", " — "):
        if separator in market_text:
            candidate = market_text.split(separator, 1)[0].strip()
            if candidate:
                return candidate
    return None


def _draftkings_event(
    raw: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "id": str(raw.get("eventId") or raw.get("id") or "").strip(),
        "home_team": raw.get("homeTeam") or raw.get("teamOneName"),
        "away_team": raw.get("awayTeam") or raw.get("teamTwoName"),
        "commence_time": (
            raw.get("startDate")
            or raw.get("startEventDate")
            or raw.get("startTime")
        ),
    }


def fetch_live_nfl_prop_events_draftkings(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    timeout_seconds: float = 20.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize credential-free DraftKings NFL sportsbook JSON to LevLine's market shape."""

    root, source_url = _draftkings_public_get_json(timeout_seconds=timeout_seconds)
    event_group = root.get("eventGroup")
    if not isinstance(event_group, Mapping):
        raise PropsMarketLiveError("DraftKings public feed missing eventGroup")

    game_directory = _game_directory(player_state_rows)
    raw_events = event_group.get("events")
    if not isinstance(raw_events, Sequence) or isinstance(raw_events, (str, bytes)):
        raise PropsMarketLiveError("DraftKings public feed missing events")

    canonical_events: dict[str, dict[str, Any]] = {}
    discovery_unmatched: list[dict[str, Any]] = []
    ordered_event_ids: list[str] = []
    for raw in raw_events:
        if not isinstance(raw, Mapping):
            continue
        event = _draftkings_event(raw)
        event_id = str(event.get("id") or "")
        game, reason = _match_event(event, game_directory)
        if game is None:
            discovery_unmatched.append(
                {"provider_event_id": event_id or None, "reason": reason}
            )
            continue
        if not event_id:
            continue
        canonical_events[event_id] = {
            **event,
            "bookmakers": [
                {
                    "key": "draftkings",
                    "title": "DraftKings",
                    "markets": [],
                }
            ],
        }
        ordered_event_ids.append(event_id)

    if not canonical_events:
        raise PropsMarketLiveError(
            "DraftKings public feed returned no canonical-slate events"
        )

    markets_by_event: dict[tuple[str, str], dict[str, Any]] = {}
    seen_outcomes: set[tuple[object, ...]] = set()
    categories = event_group.get("offerCategories")
    if not isinstance(categories, Sequence) or isinstance(categories, (str, bytes)):
        categories = []

    for category in categories:
        if not isinstance(category, Mapping):
            continue
        category_name = category.get("name")
        descriptors = category.get("offerSubcategoryDescriptors")
        if not isinstance(descriptors, Sequence) or isinstance(descriptors, (str, bytes)):
            continue
        for descriptor in descriptors:
            if not isinstance(descriptor, Mapping):
                continue
            subcategory = descriptor.get("offerSubcategory")
            if not isinstance(subcategory, Mapping):
                subcategory = descriptor
            sub_name = subcategory.get("name") or descriptor.get("name")
            offers = subcategory.get("offers")
            if not isinstance(offers, Sequence) or isinstance(offers, (str, bytes)):
                continue

            blocks: list[tuple[str | None, Sequence[Any]]] = []
            if offers and isinstance(offers[0], Mapping):
                blocks.append((None, offers))
            else:
                for index, block in enumerate(offers):
                    if not isinstance(block, Sequence) or isinstance(block, (str, bytes)):
                        continue
                    default_id = (
                        ordered_event_ids[index]
                        if index < len(ordered_event_ids)
                        else None
                    )
                    blocks.append((default_id, block))

            for default_event_id, block in blocks:
                for offer in block:
                    if not isinstance(offer, Mapping):
                        continue
                    event_id = str(
                        offer.get("eventId")
                        or offer.get("event_id")
                        or default_event_id
                        or ""
                    ).strip()
                    if event_id not in canonical_events:
                        continue
                    market_label = offer.get("label") or offer.get("name")
                    market_key = _draftkings_market_key(
                        category_name,
                        sub_name,
                        market_label,
                    )
                    if market_key is None or market_key not in DEFAULT_MARKET_MAP:
                        continue
                    outcomes = offer.get("outcomes")
                    if not isinstance(outcomes, Sequence) or isinstance(
                        outcomes, (str, bytes)
                    ):
                        continue

                    market_identity = (event_id, market_key)
                    market = markets_by_event.get(market_identity)
                    if market is None:
                        market = {"key": market_key, "outcomes": []}
                        markets_by_event[market_identity] = market
                        canonical_events[event_id]["bookmakers"][0]["markets"].append(
                            market
                        )

                    for outcome in outcomes:
                        if not isinstance(outcome, Mapping):
                            continue
                        price = _draftkings_price(
                            outcome.get("oddsAmerican")
                            or outcome.get("oddsAmericanDisplay")
                            or outcome.get("americanOdds")
                            or outcome.get("displayOdds")
                            or outcome.get("odds")
                        )
                        player = _draftkings_participant(outcome, market_label)
                        if price is None or not player:
                            continue
                        raw_side = str(outcome.get("label") or "").strip().lower()

                        if market_key == "player_anytime_td":
                            side = "No" if raw_side == "no" else "Yes"
                            normalized = {
                                "name": side,
                                "description": player,
                                "price": price,
                            }
                            identity = (
                                event_id,
                                market_key,
                                player,
                                side.lower(),
                                None,
                                price,
                            )
                        else:
                            if raw_side not in {"over", "under"}:
                                continue
                            point = _draftkings_line(outcome)
                            if point is None:
                                continue
                            normalized = {
                                "name": raw_side.title(),
                                "description": player,
                                "price": price,
                                "point": point,
                            }
                            identity = (
                                event_id,
                                market_key,
                                player,
                                raw_side,
                                point,
                                price,
                            )

                        if identity in seen_outcomes:
                            continue
                        seen_outcomes.add(identity)
                        market["outcomes"].append(normalized)

    event_odds = []
    for event_id in ordered_event_ids:
        event = canonical_events[event_id]
        markets = event["bookmakers"][0]["markets"]
        markets[:] = [market for market in markets if market["outcomes"]]
        if markets:
            event_odds.append(event)

    if not event_odds:
        raise PropsMarketLiveError(
            "DraftKings public feed yielded no supported canonical-slate prop markets"
        )

    raw_bundle = {
        "provider": "draftkings_public",
        "sport_key": SPORT_KEY,
        "source_url": source_url,
        "discovery_event_count": len(raw_events),
        "matched_discovery_events": [
            {key: event[key] for key in ("id", "home_team", "away_team", "commence_time")}
            for event in event_odds
        ],
        "discovery_unmatched": discovery_unmatched,
        "event_odds": event_odds,
        "raw_event_group_sha256": payload_sha256(root),
        "raw_event_group": root,
    }
    return event_odds, raw_bundle

def fetch_live_nfl_prop_events_with_fallback(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    the_odds_api_key: str = "",
    propline_api_key: str = "",
    regions: str = DEFAULT_REGIONS,
    bookmakers: str | None = None,
    timeout_seconds: float = 20.0,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Try authorized aggregators first, then credential-free DraftKings, and fail closed."""

    attempts: list[dict[str, Any]] = []
    configured = [
        ("the_odds_api", str(the_odds_api_key or "").strip()),
        ("propline", str(propline_api_key or "").strip()),
    ]
    errors: list[str] = []

    for provider, api_key in configured:
        if not api_key:
            attempts.append({"provider": provider, "status": "not_configured"})
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
            attempts.append({"provider": provider, "status": "failed", "detail": detail})
            errors.append(f"{provider}: {detail}")
            continue

        attempts.append({"provider": provider, "status": "selected"})
        return events, {**raw_bundle, "provider_attempts": attempts}

    try:
        events, raw_bundle = fetch_live_nfl_prop_events_draftkings(
            player_state_rows=player_state_rows,
            timeout_seconds=timeout_seconds,
        )
    except PropsMarketLiveError as exc:
        detail = str(exc)
        attempts.append(
            {"provider": "draftkings_public", "status": "failed", "detail": detail}
        )
        errors.append(f"draftkings_public: {detail}")
    else:
        attempts.append({"provider": "draftkings_public", "status": "selected"})
        return events, {**raw_bundle, "provider_attempts": attempts}

    raise PropsMarketLiveError(
        "all live Props market providers failed: " + "; ".join(errors)
    )

def utc_now() -> datetime:
    return datetime.now(timezone.utc)
