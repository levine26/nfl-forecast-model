from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from statistics import NormalDist
from typing import Any

import pandas as pd

PUBLIC_CONTRACT_VERSION = "1.0"
_MIN_PROBABILITY = 1e-6


class PublicForecastError(RuntimeError):
    """Raised when a public forecast cannot be made coherent without inventing data."""


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return text or None


def _iso(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _kickoff_utc(row: pd.Series) -> datetime | None:
    try:
        from .publish import kickoff_utc

        return kickoff_utc(row.get("gameday"), row.get("gametime"))
    except Exception:
        return None


def fair_moneyline(probability: float) -> int:
    probability = min(1.0 - _MIN_PROBABILITY, max(_MIN_PROBABILITY, float(probability)))
    if probability >= 0.5:
        return int(round(-100.0 * probability / (1.0 - probability)))
    return int(round(100.0 * (1.0 - probability) / probability))


def probability_implied_margin(home_probability: float, margin_sigma: float) -> float:
    """Map win probability to a coherent home margin using existing margin uncertainty.

    This is a presentation bridge, not a replacement fit for the independent margin model.
    Under a Normal(margin, sigma) approximation, P(home margin > 0) = home_probability.
    """
    probability = min(1.0 - _MIN_PROBABILITY, max(_MIN_PROBABILITY, float(home_probability)))
    sigma = float(margin_sigma)
    if not math.isfinite(sigma) or sigma <= 0:
        raise PublicForecastError("margin_sigma must be finite and positive")
    return float(NormalDist().inv_cdf(probability) * sigma)


def _integer_score_pair(total: float, margin: float, home_probability: float) -> tuple[int, int]:
    raw_home = (total + margin) / 2.0
    raw_away = (total - margin) / 2.0
    home = max(0, int(round(raw_home)))
    away = max(0, int(round(raw_away)))

    # Reader-facing whole-number scores must preserve the official winner even when
    # a tiny coherent margin would otherwise round to a tie.
    if home_probability > 0.5 and home <= away:
        home = away + 1
    elif home_probability < 0.5 and away <= home:
        away = home + 1
    elif home_probability == 0.5:
        average = max(0, int(round(total / 2.0)))
        home = away = average
    return home, away


def _winner_for_probability(row: pd.Series, home_probability: float) -> str:
    home = _text(row.get("home_team"))
    away = _text(row.get("away_team"))
    if not home or not away:
        raise PublicForecastError("home_team and away_team are required")
    if home_probability == 0.5:
        return "PICKEM"
    return home if home_probability > 0.5 else away


def _lifecycle(row: pd.Series, *, locked: bool, now_utc: datetime) -> str:
    actual_home = _number(row.get("actual_home_score"))
    actual_away = _number(row.get("actual_away_score"))
    if locked and actual_home is not None and actual_away is not None:
        return "GRADED"

    kickoff = _kickoff_utc(row)
    if kickoff and now_utc >= kickoff:
        return "IN_PROGRESS"
    if locked:
        return "FINAL_PREGAME"
    return "LIVE_FORECAST"


def _football_signal(row: pd.Series) -> tuple[float | None, str | None]:
    fst = _number(row.get("fst_pure_home_prob"))
    if fst is not None:
        return fst, "F_ST_NESTED_FOOTBALL"
    legacy = _number(row.get("pure_home_prob"))
    if legacy is not None:
        return legacy, "LEGACY_FOOTBALL"
    return None, None


def _market_probability_for_winner(home_probability: float | None, winner: str, row: pd.Series) -> float | None:
    if home_probability is None or winner == "PICKEM":
        return None
    home = _text(row.get("home_team"))
    return home_probability if winner == home else 1.0 - home_probability


def _public_row(row: pd.Series, *, locked: bool, now_utc: datetime) -> dict[str, Any]:
    game_id = _text(row.get("game_id"))
    if not game_id:
        raise PublicForecastError("game_id is required")

    home_probability = _number(row.get("final_home_prob"))
    if home_probability is None or not 0.0 <= home_probability <= 1.0:
        raise PublicForecastError(f"{game_id}: final_home_prob must be in [0, 1]")

    sigma = _number(row.get("margin_sigma"))
    if sigma is None:
        raise PublicForecastError(f"{game_id}: margin_sigma is required for the public fair-margin bridge")
    fair_margin_home = probability_implied_margin(home_probability, sigma)
    fair_spread_home = -fair_margin_home

    projected_total = _number(row.get("expected_total"))
    if projected_total is None or projected_total < 0:
        raise PublicForecastError(f"{game_id}: expected_total is required")
    projected_home_raw = (projected_total + fair_margin_home) / 2.0
    projected_away_raw = (projected_total - fair_margin_home) / 2.0
    projected_home, projected_away = _integer_score_pair(projected_total, fair_margin_home, home_probability)

    home = _text(row.get("home_team"))
    away = _text(row.get("away_team"))
    winner = _winner_for_probability(row, home_probability)
    winner_probability = max(home_probability, 1.0 - home_probability)
    if winner == "PICKEM":
        winner_probability = 0.5

    football_home_probability, football_signal_kind = _football_signal(row)
    market_home_probability = _number(row.get("market_home_prob"))
    market_winner_probability = _market_probability_for_winner(market_home_probability, winner, row)
    probability_difference_pp = (
        None
        if market_winner_probability is None
        else (winner_probability - market_winner_probability) * 100.0
    )

    independent_margin = _number(row.get("expected_margin"))
    independent_total = _number(row.get("expected_total"))
    independent_home_score = None
    independent_away_score = None
    if independent_margin is not None and independent_total is not None:
        independent_home_score = (independent_total + independent_margin) / 2.0
        independent_away_score = (independent_total - independent_margin) / 2.0

    forecast = {
        "contract_version": PUBLIC_CONTRACT_VERSION,
        "game_id": game_id,
        "season": int(_number(row.get("season")) or 0),
        "week": int(_number(row.get("week")) or 0),
        "gameday": _text(row.get("gameday")),
        "gametime": _text(row.get("gametime")),
        "away_team": away,
        "home_team": home,
        "official_winner": winner,
        "official_home_win_probability": home_probability,
        "official_winner_probability": winner_probability,
        "football_only_home_win_probability": football_home_probability,
        "market_home_win_probability": market_home_probability,
        "probability_derived_fair_home_moneyline": fair_moneyline(home_probability),
        "coherent_fair_margin_home": fair_margin_home,
        "coherent_fair_spread_home": fair_spread_home,
        "public_projected_total": projected_total,
        "projected_home_score_raw": projected_home_raw,
        "projected_away_score_raw": projected_away_raw,
        "projected_home_score": projected_home,
        "projected_away_score": projected_away,
        "market_margin_home": _number(row.get("spread_line")),
        "market_total": _number(row.get("total_line")),
        "levline_vs_market_winner_probability_pp": probability_difference_pp,
        "forecast_timestamp_utc": _iso(row.get("prediction_timestamp_utc")),
        "market_timestamp_utc": _iso(row.get("market_snapshot_timestamp_utc")),
        "lifecycle_status": _lifecycle(row, locked=locked, now_utc=now_utc),
        "immutable": bool(locked),
        "source_snapshot": "LOCKED" if locked else "LIVE",
        "signals": {
            "football": {
                "home_win_probability": football_home_probability,
                "kind": football_signal_kind,
            },
            "market": {
                "home_win_probability": market_home_probability,
                "timestamp_utc": _iso(row.get("market_snapshot_timestamp_utc")),
                "source": _text(row.get("market_snapshot_source")),
            },
            "official": {
                "home_win_probability": home_probability,
                "winner": winner,
                "winner_probability": winner_probability,
            },
        },
        "diagnostics": {
            "independent_margin_home": independent_margin,
            "independent_projected_home_score": independent_home_score,
            "independent_projected_away_score": independent_away_score,
            "legacy_pure_home_probability": _number(row.get("legacy_pure_home_prob")),
            "legacy_final_home_probability": _number(row.get("legacy_final_home_prob")),
            "model_disagreement": _number(row.get("model_disagreement")),
        },
        "provenance": {
            "model_version": _text(row.get("model_version")),
            "probability_strategy": _text(row.get("final_probability_strategy")),
            "artifact_id": _text(row.get("fst_artifact_id")),
            "artifact_training_data_sha256": _text(row.get("fst_artifact_training_data_sha256")),
            "artifact_freeze_implementation_sha": _text(row.get("fst_artifact_freeze_implementation_sha")),
            "fst_fallback": bool(row.get("fst_fallback")) if pd.notna(row.get("fst_fallback")) else False,
            "fst_fallback_reason": _text(row.get("fst_fallback_reason")),
        },
    }
    validate_public_forecast(forecast)
    return forecast


def validate_public_forecast(forecast: dict[str, Any]) -> None:
    game_id = forecast.get("game_id", "unknown")
    p = float(forecast["official_home_win_probability"])
    winner = forecast["official_winner"]
    home = forecast["home_team"]
    away = forecast["away_team"]
    margin = float(forecast["coherent_fair_margin_home"])
    spread = float(forecast["coherent_fair_spread_home"])
    home_score = int(forecast["projected_home_score"])
    away_score = int(forecast["projected_away_score"])

    expected_winner = "PICKEM" if p == 0.5 else home if p > 0.5 else away
    if winner != expected_winner:
        raise PublicForecastError(f"{game_id}: official winner contradicts official probability")
    if not math.isclose(spread, -margin, abs_tol=1e-9):
        raise PublicForecastError(f"{game_id}: fair spread and fair margin are not opposites")

    if p > 0.5:
        if not margin > 0 or not spread < 0 or not home_score > away_score:
            raise PublicForecastError(f"{game_id}: home-favorite public forecast is contradictory")
    elif p < 0.5:
        if not margin < 0 or not spread > 0 or not away_score > home_score:
            raise PublicForecastError(f"{game_id}: away-favorite public forecast is contradictory")
    else:
        if not math.isclose(margin, 0.0, abs_tol=1e-9) or home_score != away_score:
            raise PublicForecastError(f"{game_id}: pick'em public forecast is contradictory")

    football = forecast.get("football_only_home_win_probability")
    market = forecast.get("market_home_win_probability")
    for label, value in (("football", football), ("market", market)):
        if value is not None and not 0.0 <= float(value) <= 1.0:
            raise PublicForecastError(f"{game_id}: {label} probability must be in [0, 1]")


def build_public_forecasts(
    current: pd.DataFrame,
    official: pd.DataFrame,
    *,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    locked_by_game: dict[str, pd.Series] = {}
    if official is not None and not official.empty and "game_id" in official.columns:
        locked = official[official.get("lock_status", pd.Series("", index=official.index)).eq("LOCKED")]
        for _, row in locked.iterrows():
            locked_by_game[str(row.get("game_id"))] = row

    games: list[dict[str, Any]] = []
    for _, current_row in current.iterrows():
        game_id = str(current_row.get("game_id"))
        locked_row = locked_by_game.get(game_id)
        source = locked_row if locked_row is not None else current_row
        kickoff = _kickoff_utc(source)
        if locked_row is None and kickoff is not None and now_utc >= kickoff:
            raise PublicForecastError(
                f"{game_id}: kickoff has passed without an immutable pregame lock; refusing to publish a live replacement"
            )
        games.append(_public_row(source, locked=locked_row is not None, now_utc=now_utc))

    return {
        "contract_version": PUBLIC_CONTRACT_VERSION,
        "generated_utc": now_utc.isoformat(),
        "games": games,
    }
