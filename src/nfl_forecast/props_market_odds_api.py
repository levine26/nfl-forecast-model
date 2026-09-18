from __future__ import annotations

"""Fail-closed adapters for The Odds API style player-prop payloads."""

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .props_market import PropMarketQuote, parse_utc


DEFAULT_MARKET_MAP = {
    "player_pass_yds": "passing_yards",
    "player_rush_yds": "rushing_yards",
    "player_reception_yds": "receiving_yards",
    "player_receptions": "receptions",
    "player_pass_tds": "passing_tds",
    "player_rush_tds": "rushing_tds",
    "player_reception_tds": "receiving_tds",
    "player_anytime_td": "anytime_td",
}


@dataclass(frozen=True)
class OddsApiIngestResult:
    quotes: tuple[PropMarketQuote, ...]
    rejected: tuple[dict, ...]
    ignored_market_keys: tuple[str, ...]


def _player_name(outcome: Mapping, *, binary: bool) -> str | None:
    name = str(outcome.get("name") or "").strip()
    description = str(outcome.get("description") or "").strip()
    lowered = name.lower()
    if binary:
        if lowered in {"yes", "no"}:
            return description or None
        if lowered not in {"over", "under"}:
            return name or None
        return None
    if lowered in {"over", "under"}:
        return description or None
    return None


def _price(outcome: Mapping) -> float | None:
    try:
        value = float(outcome.get("price"))
    except (TypeError, ValueError):
        return None
    return value


def _line(outcome: Mapping) -> float | None:
    try:
        value = float(outcome.get("point"))
    except (TypeError, ValueError):
        return None
    return value


def _context(
    player_id: str,
    resolver: Callable[[str], Mapping | None] | None,
) -> dict:
    if resolver is None:
        return {}
    value = resolver(player_id)
    return dict(value or {})


def _market_mapping(key: str, market_map: Mapping[str, str]) -> tuple[str | None, bool]:
    if key in market_map:
        return market_map[key], False
    suffix = "_alternate"
    if key.endswith(suffix):
        base = key[: -len(suffix)]
        if base in market_map:
            return market_map[base], True
    return None, False


def ingest_odds_api_event(
    event: Mapping,
    *,
    captured_at_utc: object,
    game_id: str,
    player_id_resolver: Callable[[str], str | None],
    player_context_resolver: Callable[[str], Mapping | None] | None = None,
    market_map: Mapping[str, str] | None = None,
    provider: str = "the_odds_api",
    is_closing: bool = False,
) -> OddsApiIngestResult:
    """Normalize an event-odds payload without guessing stable player identity.

    Player names are resolved through the caller-supplied stable-ID resolver.
    Unresolved names are rejected rather than emitted with synthetic identifiers.
    Unsupported market keys are reported as ignored, allowing the provider
    surface to expand without silently changing LevLine's supported scope.
    """

    mapping = dict(market_map or DEFAULT_MARKET_MAP)
    captured = parse_utc(captured_at_utc)
    kickoff = parse_utc(event.get("commence_time")) if event.get("commence_time") else None
    event_id = str(event.get("id") or "").strip() or None

    quotes: list[PropMarketQuote] = []
    rejected: list[dict] = []
    ignored: set[str] = set()

    bookmakers = event.get("bookmakers")
    if not isinstance(bookmakers, Sequence) or isinstance(bookmakers, (str, bytes)):
        return OddsApiIngestResult((), ({"reason": "missing_bookmakers"},), ())

    for bookmaker in bookmakers:
        if not isinstance(bookmaker, Mapping):
            rejected.append({"reason": "invalid_bookmaker"})
            continue
        book_key = str(bookmaker.get("key") or "").strip()
        book_title = str(bookmaker.get("title") or book_key).strip()
        if not book_key:
            rejected.append({"reason": "missing_sportsbook_key"})
            continue

        markets = bookmaker.get("markets")
        if not isinstance(markets, Sequence) or isinstance(markets, (str, bytes)):
            rejected.append({"reason": "missing_markets", "sportsbook_key": book_key})
            continue

        for market in markets:
            if not isinstance(market, Mapping):
                rejected.append({"reason": "invalid_market", "sportsbook_key": book_key})
                continue
            raw_key = str(market.get("key") or "").strip()
            prop_type, key_is_alternative = _market_mapping(raw_key, mapping)
            if prop_type is None:
                if raw_key:
                    ignored.add(raw_key)
                continue

            last_update_raw = market.get("last_update") or bookmaker.get("last_update")
            try:
                last_update = parse_utc(last_update_raw) if last_update_raw else None
            except ValueError:
                last_update = None

            outcomes = market.get("outcomes")
            if not isinstance(outcomes, Sequence) or isinstance(outcomes, (str, bytes)):
                rejected.append(
                    {
                        "reason": "missing_outcomes",
                        "sportsbook_key": book_key,
                        "market_key": raw_key,
                    }
                )
                continue

            if prop_type == "anytime_td":
                grouped: dict[str, dict[str, float | None]] = {}
                for outcome in outcomes:
                    if not isinstance(outcome, Mapping):
                        continue
                    player = _player_name(outcome, binary=True)
                    price = _price(outcome)
                    if not player or price is None:
                        rejected.append(
                            {
                                "reason": "unparseable_binary_outcome",
                                "sportsbook_key": book_key,
                                "market_key": raw_key,
                            }
                        )
                        continue
                    name = str(outcome.get("name") or "").strip().lower()
                    side = "no" if name == "no" else "yes"
                    grouped.setdefault(player, {"yes": None, "no": None})[side] = price

                for player, prices in grouped.items():
                    player_id = player_id_resolver(player)
                    if not player_id:
                        rejected.append(
                            {
                                "reason": "unresolved_player_id",
                                "sportsbook_key": book_key,
                                "market_key": raw_key,
                                "player": player,
                            }
                        )
                        continue
                    ctx = _context(player_id, player_context_resolver)
                    try:
                        quotes.append(
                            PropMarketQuote(
                                provider=provider,
                                sportsbook_key=book_key,
                                sportsbook_title=book_title,
                                captured_at_utc=captured,
                                player_id=player_id,
                                player=player,
                                game_id=game_id,
                                prop_type=prop_type,
                                yes_american=prices["yes"],
                                no_american=prices["no"],
                                team=ctx.get("team"),
                                opponent=ctx.get("opponent"),
                                position=ctx.get("position"),
                                kickoff_utc=kickoff,
                                sportsbook_last_update_utc=last_update,
                                provider_event_id=event_id,
                                provider_market_key=raw_key,
                                is_alternative_line=key_is_alternative,
                                is_closing=is_closing,
                                related_market_group_id=ctx.get("related_market_group_id"),
                            )
                        )
                    except ValueError as exc:
                        rejected.append(
                            {
                                "reason": "invalid_quote",
                                "detail": str(exc),
                                "sportsbook_key": book_key,
                                "market_key": raw_key,
                                "player": player,
                            }
                        )
                continue

            grouped_lines: dict[tuple[str, float], dict[str, float | None]] = {}
            player_lines: dict[str, set[float]] = {}
            for outcome in outcomes:
                if not isinstance(outcome, Mapping):
                    continue
                name = str(outcome.get("name") or "").strip().lower()
                if name not in {"over", "under"}:
                    continue
                player = _player_name(outcome, binary=False)
                point = _line(outcome)
                price = _price(outcome)
                if not player or point is None or price is None:
                    rejected.append(
                        {
                            "reason": "unparseable_two_way_outcome",
                            "sportsbook_key": book_key,
                            "market_key": raw_key,
                        }
                    )
                    continue
                grouped_lines.setdefault((player, point), {"over": None, "under": None})[name] = price
                player_lines.setdefault(player, set()).add(point)

            for (player, point), prices in grouped_lines.items():
                player_id = player_id_resolver(player)
                if not player_id:
                    rejected.append(
                        {
                            "reason": "unresolved_player_id",
                            "sportsbook_key": book_key,
                            "market_key": raw_key,
                            "player": player,
                            "line": point,
                        }
                    )
                    continue
                ctx = _context(player_id, player_context_resolver)
                alternative = key_is_alternative or len(player_lines.get(player, set())) > 1
                try:
                    quotes.append(
                        PropMarketQuote(
                            provider=provider,
                            sportsbook_key=book_key,
                            sportsbook_title=book_title,
                            captured_at_utc=captured,
                            player_id=player_id,
                            player=player,
                            game_id=game_id,
                            prop_type=prop_type,
                            line=point,
                            over_american=prices["over"],
                            under_american=prices["under"],
                            team=ctx.get("team"),
                            opponent=ctx.get("opponent"),
                            position=ctx.get("position"),
                            kickoff_utc=kickoff,
                            sportsbook_last_update_utc=last_update,
                            provider_event_id=event_id,
                            provider_market_key=raw_key,
                            is_alternative_line=alternative,
                            is_closing=is_closing,
                            related_market_group_id=ctx.get("related_market_group_id"),
                        )
                    )
                except ValueError as exc:
                    rejected.append(
                        {
                            "reason": "invalid_quote",
                            "detail": str(exc),
                            "sportsbook_key": book_key,
                            "market_key": raw_key,
                            "player": player,
                            "line": point,
                        }
                    )

    return OddsApiIngestResult(
        tuple(quotes),
        tuple(rejected),
        tuple(sorted(ignored)),
    )
