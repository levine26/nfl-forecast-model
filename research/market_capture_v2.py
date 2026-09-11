from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Iterable


HORIZONS = {"T-120m": 120, "T-60m": 60, "T-30m": 30}
CAPTURE_TOLERANCE_MINUTES = 7.5
EPS = 1e-9


def american_implied(odds: float) -> float:
    value = float(odds)
    if not math.isfinite(value) or value == 0:
        raise ValueError("American odds must be finite and non-zero")
    return (-value) / ((-value) + 100.0) if value < 0 else 100.0 / (value + 100.0)


def two_way_metrics(first_odds: float, second_odds: float) -> dict[str, float]:
    first = american_implied(first_odds)
    second = american_implied(second_odds)
    total = first + second
    if not math.isfinite(total) or total <= 0:
        raise ValueError("invalid two-way market")
    return {
        "first_implied": first,
        "second_implied": second,
        "overround": total - 1.0,
        "first_no_vig": min(1.0 - EPS, max(EPS, first / total)),
        "second_no_vig": min(1.0 - EPS, max(EPS, second / total)),
    }


def logit(value: float) -> float:
    p = min(1.0 - EPS, max(EPS, float(value)))
    return math.log(p / (1.0 - p))


def inv_logit(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def median_logit(values: Iterable[float]) -> float:
    vals = [float(v) for v in values if math.isfinite(float(v)) and 0 < float(v) < 1]
    if not vals:
        raise ValueError("consensus requires at least one valid probability")
    return inv_logit(median(logit(v) for v in vals))


def horizon_target(kickoff_utc: datetime, horizon: str) -> datetime:
    if horizon not in HORIZONS:
        raise ValueError(f"unsupported horizon: {horizon}")
    return kickoff_utc.astimezone(timezone.utc) - timedelta(minutes=HORIZONS[horizon])


def due_horizons(kickoff_utc: datetime, now_utc: datetime) -> list[dict[str, Any]]:
    kickoff = kickoff_utc.astimezone(timezone.utc)
    now = now_utc.astimezone(timezone.utc)
    out = []
    for label, minutes in HORIZONS.items():
        target = kickoff - timedelta(minutes=minutes)
        error = (now - target).total_seconds() / 60.0
        if abs(error) <= CAPTURE_TOLERANCE_MINUTES:
            out.append({"horizon": label, "target_timestamp_utc": target, "timing_error_minutes": error})
    return out


def _outcome(market: dict[str, Any] | None, name: str) -> dict[str, Any] | None:
    if not market:
        return None
    return next((row for row in market.get("outcomes", []) if row.get("name") == name), None)


def _market(bookmaker: dict[str, Any], key: str) -> dict[str, Any] | None:
    return next((row for row in bookmaker.get("markets", []) if row.get("key") == key), None)


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def normalize_bookmaker(
    *,
    event: dict[str, Any],
    bookmaker: dict[str, Any],
    game_id: str,
    home_team: str,
    away_team: str,
    horizon: str,
    target_timestamp_utc: datetime,
    request_timestamp_utc: datetime,
    kickoff_timestamp_utc: datetime,
) -> dict[str, Any] | None:
    h2h = _market(bookmaker, "h2h")
    home_ml = _outcome(h2h, event.get("home_team"))
    away_ml = _outcome(h2h, event.get("away_team"))
    if not home_ml or not away_ml:
        return None

    home_price = _float_or_none(home_ml.get("price"))
    away_price = _float_or_none(away_ml.get("price"))
    if home_price is None or away_price is None:
        return None
    try:
        ml = two_way_metrics(home_price, away_price)
    except ValueError:
        return None

    spread = _market(bookmaker, "spreads")
    home_spread = _outcome(spread, event.get("home_team"))
    away_spread = _outcome(spread, event.get("away_team"))
    home_spread_price = _float_or_none(home_spread.get("price")) if home_spread else None
    away_spread_price = _float_or_none(away_spread.get("price")) if away_spread else None
    home_spread_point = _float_or_none(home_spread.get("point")) if home_spread else None
    away_spread_point = _float_or_none(away_spread.get("point")) if away_spread else None
    spread_metrics = None
    if home_spread_price is not None and away_spread_price is not None:
        try:
            spread_metrics = two_way_metrics(home_spread_price, away_spread_price)
        except ValueError:
            spread_metrics = None

    totals = _market(bookmaker, "totals")
    over = _outcome(totals, "Over")
    under = _outcome(totals, "Under")
    over_price = _float_or_none(over.get("price")) if over else None
    under_price = _float_or_none(under.get("price")) if under else None
    total_point = _float_or_none(over.get("point")) if over else None
    total_metrics = None
    if over_price is not None and under_price is not None:
        try:
            total_metrics = two_way_metrics(over_price, under_price)
        except ValueError:
            total_metrics = None

    last_update = _parse_time(bookmaker.get("last_update"))
    freshness = None
    if last_update:
        freshness = max(0.0, (request_timestamp_utc - last_update).total_seconds() / 60.0)

    provider_kickoff = _parse_time(event.get("commence_time"))
    provider_kickoff_delta = None
    if provider_kickoff:
        provider_kickoff_delta = (
            provider_kickoff - kickoff_timestamp_utc.astimezone(timezone.utc)
        ).total_seconds() / 60.0

    return {
        "row_type": "book",
        "game_id": game_id,
        "event_id": event.get("id"),
        "provider_commence_time_utc": provider_kickoff.isoformat() if provider_kickoff else None,
        "provider_kickoff_delta_minutes": provider_kickoff_delta,
        "home_team": home_team,
        "away_team": away_team,
        "kickoff_timestamp_utc": kickoff_timestamp_utc.isoformat(),
        "horizon": horizon,
        "target_timestamp_utc": target_timestamp_utc.isoformat(),
        "request_timestamp_utc": request_timestamp_utc.isoformat(),
        "timing_error_minutes": (request_timestamp_utc - target_timestamp_utc).total_seconds() / 60.0,
        "sportsbook_key": bookmaker.get("key"),
        "sportsbook_title": bookmaker.get("title"),
        "sportsbook_last_update_utc": last_update.isoformat() if last_update else None,
        "freshness_minutes": freshness,
        "home_moneyline": home_price,
        "away_moneyline": away_price,
        "h2h_home_implied": ml["first_implied"],
        "h2h_away_implied": ml["second_implied"],
        "h2h_overround": ml["overround"],
        "h2h_home_no_vig": ml["first_no_vig"],
        "home_spread": home_spread_point,
        "home_spread_price": home_spread_price,
        "away_spread": away_spread_point,
        "away_spread_price": away_spread_price,
        "spread_overround": spread_metrics["overround"] if spread_metrics else None,
        "spread_home_cover_no_vig": spread_metrics["first_no_vig"] if spread_metrics else None,
        "total_points": total_point,
        "over_price": over_price,
        "under_price": under_price,
        "total_overround": total_metrics["overround"] if total_metrics else None,
        "over_no_vig": total_metrics["first_no_vig"] if total_metrics else None,
        "research_only": True,
        "production_authorized": False,
    }


def consensus_row(book_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [row for row in book_rows if row.get("h2h_home_no_vig") is not None]
    if not valid:
        return None

    identity_fields = (
        "game_id",
        "event_id",
        "provider_commence_time_utc",
        "home_team",
        "away_team",
        "kickoff_timestamp_utc",
        "horizon",
        "target_timestamp_utc",
        "request_timestamp_utc",
    )
    identities = {tuple(row.get(field) for field in identity_fields) for row in valid}
    if len(identities) != 1:
        return None

    sportsbook_keys = [str(row.get("sportsbook_key") or "").strip() for row in valid]
    if any(not key for key in sportsbook_keys) or len(set(sportsbook_keys)) != len(sportsbook_keys):
        return None

    spread_values = [float(row["home_spread"]) for row in valid if row.get("home_spread") is not None]
    total_values = [float(row["total_points"]) for row in valid if row.get("total_points") is not None]
    freshness = [float(row["freshness_minutes"]) for row in valid if row.get("freshness_minutes") is not None]
    probs = [float(row["h2h_home_no_vig"]) for row in valid]
    template = valid[0]
    return {
        "row_type": "consensus",
        "game_id": template["game_id"],
        "event_id": template.get("event_id"),
        "provider_commence_time_utc": template.get("provider_commence_time_utc"),
        "provider_kickoff_delta_minutes": template.get("provider_kickoff_delta_minutes"),
        "home_team": template["home_team"],
        "away_team": template["away_team"],
        "kickoff_timestamp_utc": template["kickoff_timestamp_utc"],
        "horizon": template["horizon"],
        "target_timestamp_utc": template["target_timestamp_utc"],
        "request_timestamp_utc": template["request_timestamp_utc"],
        "timing_error_minutes": template["timing_error_minutes"],
        "sportsbook_key": "sportsbook_consensus",
        "sportsbook_title": "Robust sportsbook consensus",
        "h2h_home_no_vig": median_logit(probs),
        "home_spread": median(spread_values) if spread_values else None,
        "total_points": median(total_values) if total_values else None,
        "source_count": len(valid),
        "source_names": "|".join(sorted(sportsbook_keys)),
        "max_freshness_minutes": max(freshness) if freshness else None,
        "probability_range": max(probs) - min(probs) if len(probs) > 1 else 0.0,
        "research_only": True,
        "production_authorized": False,
    }
