from __future__ import annotations

"""Cross-lane integration contract for LevLine Props — Research Beta.

This module is deliberately downstream of the pure football simulation. Sportsbook
thresholds are applied only after simulation, then normalized into the publication
contract. It does not import or alter the official LevLine winner model.
"""

from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from nfl_forecast.challenger_props_simulation import (
    DISCRETE_PROPS,
    GameSimulationResult,
    SUPPORTED_PROPS,
    evaluate_distribution,
    probability_to_american,
)
from nfl_forecast.props_market import american_to_implied

FORECAST_CONTRACT_VERSION = "levline-props-forecast-v0.1"
RESEARCH_LABEL = "LEVLINE PROPS — RESEARCH BETA"

INTERNAL_TO_PUBLIC_PROP = {
    "rushing_tds": "rushing_td",
    "receiving_tds": "receiving_td",
}
PUBLIC_TO_INTERNAL_PROP = {value: key for key, value in INTERNAL_TO_PUBLIC_PROP.items()}
LINE_PUBLIC_PROPS = {
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions",
    "passing_tds",
}
BINARY_PUBLIC_PROPS = {"rushing_td", "receiving_td", "anytime_td"}


class PropsIntegrationError(ValueError):
    """Raised when independently valid lane outputs cannot be joined safely."""


def _aware_utc(value: object, *, label: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise PropsIntegrationError(f"{label} must be a parseable timestamp") from exc
    if parsed.tzinfo is None:
        raise PropsIntegrationError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def public_prop_type(prop_type: str) -> str:
    prop = str(prop_type).strip()
    return INTERNAL_TO_PUBLIC_PROP.get(prop, prop)


def internal_prop_type(prop_type: str) -> str:
    prop = str(prop_type).strip()
    return PUBLIC_TO_INTERNAL_PROP.get(prop, prop)


def _finite(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _price_american(value: object) -> float | None:
    if isinstance(value, Mapping):
        return _finite(value.get("american"))
    return _finite(value)


def _forecast_id(
    *,
    game_id: str,
    player_id: str,
    prop_type: str,
    forecast_timestamp_utc: str,
    market_line: float | None,
    model_version: str,
) -> str:
    payload = {
        "game_id": game_id,
        "player_id": player_id,
        "prop_type": prop_type,
        "forecast_timestamp_utc": forecast_timestamp_utc,
        "market_line": market_line,
        "model_version": model_version,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "prop_" + hashlib.sha256(raw).hexdigest()[:24]


def assert_simulation_accounting(result: GameSimulationResult) -> bool:
    """Fail closed unless the joint simulation satisfies the core football identities."""
    for team_code, team in result.team_stats.items():
        required = {
            "offensive_plays",
            "pass_attempts",
            "sacks",
            "rush_attempts",
            "team_targets",
            "targets",
            "residual_targets",
            "completions",
            "modeled_receptions",
            "residual_receptions",
            "passing_yards",
            "modeled_carries",
            "residual_carries",
            "modeled_receiving_yards",
            "residual_receiving_yards",
            "passing_tds",
            "modeled_receiving_tds",
            "residual_receiving_tds",
            "modeled_qb_passing_tds",
            "residual_qb_passing_tds",
            "rushing_tds",
            "modeled_rushing_tds",
            "residual_rushing_tds",
        }
        missing = required - set(team)
        if missing:
            raise PropsIntegrationError(
                f"{team_code} simulation accounting fields missing: {sorted(missing)}"
            )
        identities = (
            (team["pass_attempts"] + team["sacks"] + team["rush_attempts"], team["offensive_plays"], "plays"),
            (team["targets"] + team["residual_targets"], team["team_targets"], "targets"),
            (team["modeled_receptions"] + team["residual_receptions"], team["completions"], "receptions"),
            (team["modeled_carries"] + team["residual_carries"], team["rush_attempts"], "carries"),
            (team["modeled_receiving_yards"] + team["residual_receiving_yards"], team["passing_yards"], "passing_yards"),
            (team["modeled_receiving_tds"] + team["residual_receiving_tds"], team["passing_tds"], "receiving_tds"),
            (team["modeled_qb_passing_tds"] + team["residual_qb_passing_tds"], team["passing_tds"], "qb_passing_tds"),
            (team["modeled_rushing_tds"] + team["residual_rushing_tds"], team["rushing_tds"], "rushing_tds"),
        )
        for left, right, label in identities:
            if not np.array_equal(left, right):
                raise PropsIntegrationError(f"{team_code} simulation accounting failed: {label}")
        if np.any(team["team_targets"] > team["pass_attempts"]):
            raise PropsIntegrationError(f"{team_code} simulated targets exceed pass attempts")

    for player_id, stats in result.player_stats.items():
        if np.any(stats["targets"] > stats["routes"]):
            raise PropsIntegrationError(f"{player_id} targets exceed routes")
        if np.any(stats["receptions"] > stats["targets"]):
            raise PropsIntegrationError(f"{player_id} receptions exceed targets")
        if np.any(
            (stats["active"] == 0)
            & (
                (stats["routes"] > 0)
                | (stats["targets"] > 0)
                | (stats["receptions"] > 0)
                | (stats["carries"] > 0)
                | (stats["pass_attempts"] > 0)
            )
        ):
            raise PropsIntegrationError(f"{player_id} received normal opportunity while inactive")
    return True


def build_efficiency_player_inputs(
    projection: Mapping[str, Any],
    baselines: pd.DataFrame,
    *,
    kickoff_timestamp: object,
    source_status: str = "qualified",
    prior_model_trained_through_season: int = 2025,
) -> pd.DataFrame:
    """Join opportunity means to pre-2026 efficiency sufficient statistics and priors."""
    metadata = projection.get("metadata")
    marginals = projection.get("marginals")
    players = projection.get("players")
    if not isinstance(metadata, Mapping) or not isinstance(marginals, Mapping):
        raise PropsIntegrationError("opportunity projection metadata/marginals are required")
    if not isinstance(players, list):
        raise PropsIntegrationError("opportunity projection players must be a list")
    if "player_id" not in baselines.columns:
        raise PropsIntegrationError("efficiency baselines require player_id")
    ids = baselines["player_id"].astype(str)
    if ids.duplicated().any():
        raise PropsIntegrationError("efficiency baselines contain duplicate player_id")
    baseline_by_id = {str(row["player_id"]): row.to_dict() for _, row in baselines.iterrows()}

    game_id = str(metadata.get("game_id") or "")
    team = str(metadata.get("team") or "")
    opponent = str(metadata.get("opponent") or "")
    season = int(metadata.get("season"))
    week = int(metadata.get("week"))
    forecast_timestamp = str(metadata.get("forecast_timestamp") or "")
    data_horizon = str(metadata.get("data_horizon") or "")
    _aware_utc(forecast_timestamp, label="forecast_timestamp")
    _aware_utc(data_horizon, label="data_horizon")
    kickoff = _aware_utc(kickoff_timestamp, label="kickoff_timestamp").isoformat()

    dropbacks = _finite(
        (marginals.get("qb_dropbacks") or {}).get("mean")
        if isinstance(marginals.get("qb_dropbacks"), Mapping)
        else None
    ) or 0.0
    pass_attempts = _finite(
        (marginals.get("qb_pass_attempts") or {}).get("mean")
        if isinstance(marginals.get("qb_pass_attempts"), Mapping)
        else None
    ) or 0.0
    qb_rushes = _finite(
        (marginals.get("qb_rushing_opportunities") or {}).get("mean")
        if isinstance(marginals.get("qb_rushing_opportunities"), Mapping)
        else None
    ) or 0.0

    rows: list[dict[str, Any]] = []
    for raw_player in players:
        if not isinstance(raw_player, Mapping):
            raise PropsIntegrationError("opportunity player row must be a mapping")
        player_id = str(raw_player.get("player_id") or "")
        baseline = baseline_by_id.get(player_id)
        if baseline is None:
            raise PropsIntegrationError(f"missing efficiency baseline for supported player {player_id}")
        route = raw_player.get("route_participation")
        route_mean = _finite(route.get("mean")) if isinstance(route, Mapping) else None
        rows.append(
            {
                **baseline,
                "game_id": game_id,
                "season": season,
                "week": week,
                "team": team,
                "opponent": opponent,
                "player_id": player_id,
                "player_name": str(raw_player.get("player_name") or player_id),
                "position": str(raw_player.get("position") or "").upper(),
                "forecast_timestamp": forecast_timestamp,
                "kickoff_timestamp": kickoff,
                "feature_data_horizon": data_horizon,
                "source_status": source_status,
                "prior_model_trained_through_season": int(prior_model_trained_through_season),
                "expected_pass_attempts": pass_attempts if bool(raw_player.get("is_primary_qb")) else 0.0,
                "expected_qb_rush_attempts": qb_rushes if bool(raw_player.get("is_primary_qb")) else 0.0,
                "expected_carries": _finite(raw_player.get("designed_carries_mean")) or 0.0,
                "expected_routes": dropbacks * route_mean if route_mean is not None else 0.0,
                "expected_targets": _finite(raw_player.get("targets_mean")) or 0.0,
            }
        )
    return pd.DataFrame(rows)


def build_efficiency_team_input(
    projection: Mapping[str, Any],
    scoring_context: Mapping[str, Any],
    *,
    kickoff_timestamp: object,
    source_status: str = "qualified",
    prior_model_trained_through_season: int = 2025,
) -> pd.DataFrame:
    metadata = projection.get("metadata")
    if not isinstance(metadata, Mapping):
        raise PropsIntegrationError("opportunity projection metadata is required")
    required = {
        "expected_drives",
        "expected_red_zone_trips",
        "prior_red_zone_td_rate",
        "prior_pass_td_fraction",
        "expected_non_red_zone_pass_tds",
        "expected_non_red_zone_rush_tds",
    }
    missing = required - set(scoring_context)
    if missing:
        raise PropsIntegrationError(f"team scoring context missing fields: {sorted(missing)}")
    kickoff = _aware_utc(kickoff_timestamp, label="kickoff_timestamp").isoformat()
    row = {
        "game_id": str(metadata.get("game_id") or ""),
        "season": int(metadata.get("season")),
        "week": int(metadata.get("week")),
        "team": str(metadata.get("team") or ""),
        "opponent": str(metadata.get("opponent") or ""),
        "forecast_timestamp": str(metadata.get("forecast_timestamp") or ""),
        "kickoff_timestamp": kickoff,
        "feature_data_horizon": str(metadata.get("data_horizon") or ""),
        "source_status": source_status,
        "prior_model_trained_through_season": int(prior_model_trained_through_season),
        **{key: scoring_context[key] for key in required},
    }
    return pd.DataFrame([row])


def publication_quality_state(data_quality_state: str) -> str:
    text = str(data_quality_state or "").lower()
    if any(
        token in text
        for token in (
            "opportunity:low",
            "degraded_source_unknown",
            "prospective_unqualified",
            "efficiency:unknown",
        )
    ):
        return "LOW"
    if "opportunity:high" in text and "qualified_moderate_history" in text:
        return "HIGH"
    return "MEDIUM"


def _market_capture_utc(market: Mapping[str, Any]) -> str | None:
    captures: list[datetime] = []
    rows = market.get("individual_books")
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            raw = row.get("captured_at_utc")
            if raw is None:
                continue
            try:
                captures.append(_aware_utc(raw, label="market capture"))
            except PropsIntegrationError:
                continue
    if captures:
        return max(captures).isoformat()
    raw_as_of = market.get("as_of_utc")
    if raw_as_of is None:
        return None
    try:
        return _aware_utc(raw_as_of, label="market as_of_utc").isoformat()
    except PropsIntegrationError:
        return None


def _market_index(
    market_artifacts: Sequence[Mapping[str, Any]],
    *,
    game_id: str,
) -> dict[tuple[str, str], Mapping[str, Any]]:
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for market in market_artifacts:
        if str(market.get("game_id") or "") != game_id:
            raise PropsIntegrationError("market game_id does not match simulation game")
        player_id = str(market.get("player_id") or "")
        prop = internal_prop_type(str(market.get("prop_type") or ""))
        key = (player_id, prop)
        if not player_id or not prop:
            raise PropsIntegrationError("market artifact missing stable identity")
        if key in out:
            raise PropsIntegrationError(f"duplicate market artifact for {player_id}/{prop}")
        out[key] = market
    return out


def _market_provenance(market: Mapping[str, Any] | None) -> dict[str, Any]:
    if market is None:
        return {}
    return {
        "schema_version": market.get("schema_version"),
        "as_of_utc": market.get("as_of_utc"),
        "sportsbooks": market.get("sportsbooks"),
        "market_data_quality": market.get("market_data_quality"),
        "line_min": market.get("line_min"),
        "line_max": market.get("line_max"),
        "line_range": market.get("line_range"),
        "line_stddev": market.get("line_stddev"),
        "movement": market.get("movement"),
        "closing_evaluation_in_forecast": False,
    }


def build_forecast_artifact(
    result: GameSimulationResult,
    market_artifacts: Sequence[Mapping[str, Any]],
    *,
    kickoff_utc: object,
    forecast_timestamp_utc: object,
    interval_level: float = 0.80,
    drivers_by_key: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Create publication-lane forecasts from pure simulation plus frozen markets."""
    assert_simulation_accounting(result)
    forecast_dt = _aware_utc(forecast_timestamp_utc, label="forecast_timestamp_utc")
    kickoff_dt = _aware_utc(kickoff_utc, label="kickoff_utc")
    horizon_dt = _aware_utc(result.data_horizon, label="data_horizon")
    if not horizon_dt <= forecast_dt < kickoff_dt:
        raise PropsIntegrationError("forecast requires data_horizon <= forecast_timestamp < kickoff")

    markets = _market_index(market_artifacts, game_id=result.game_id)
    drivers = drivers_by_key or {}
    forecasts: list[dict[str, Any]] = []

    for player in result.players:
        position = player.position.upper()
        if position not in SUPPORTED_PROPS:
            continue
        for internal_prop in SUPPORTED_PROPS[position]:
            public_prop = public_prop_type(internal_prop)
            market = markets.get((player.player_id, internal_prop))
            samples = np.asarray(result.player_stats[player.player_id][internal_prop], dtype=float)
            quality_state = publication_quality_state(player.data_quality_state)
            notes: list[str] = []
            critical_ok = market is not None and quality_state != "LOW"
            market_block: dict[str, Any] = {"source": None, "sportsbook": None, "captured_utc": None}
            model_block: dict[str, Any] = {
                "version": result.model_version,
                "simulation_count": int(result.simulations),
                "simulation_accounting_ok": True,
            }

            if public_prop in LINE_PUBLIC_PROPS:
                line = _finite(market.get("consensus_line")) if market else None
                summary = evaluate_distribution(
                    samples,
                    market_line=line,
                    discrete=internal_prop in DISCRETE_PROPS,
                    interval_level=interval_level,
                )
                best_over = market.get("best_over_price") if market else None
                best_under = market.get("best_under_price") if market else None
                over_price = _price_american(best_over)
                under_price = _price_american(best_under)
                no_vig_over = _finite(market.get("consensus_no_vig_p_over")) if market else None
                no_vig_under = _finite(market.get("consensus_no_vig_p_under")) if market else None
                if line is None or over_price is None or under_price is None or no_vig_over is None or no_vig_under is None:
                    critical_ok = False
                    notes.append("complete two-way line market unavailable")
                market_block.update(
                    {
                        "source": "consensus" if market else None,
                        "sportsbook": "consensus" if market else None,
                        "captured_utc": _market_capture_utc(market) if market else None,
                        "line": line,
                        "over_price_american": over_price,
                        "under_price_american": under_price,
                        "raw_implied_over_probability": american_to_implied(over_price) if over_price is not None else None,
                        "raw_implied_under_probability": american_to_implied(under_price) if under_price is not None else None,
                        "no_vig_over_probability": no_vig_over,
                        "no_vig_under_probability": no_vig_under,
                        "consensus_line": line,
                        "line_range": market.get("line_range") if market else None,
                        "line_stddev": market.get("line_stddev") if market else None,
                    }
                )
                model_block.update(
                    {
                        "mean": summary.model_mean,
                        "median": summary.model_median,
                        "fair_line": summary.levline_fair_line,
                        "standard_deviation": summary.standard_deviation,
                        "over_probability": summary.p_over,
                        "under_probability": summary.p_under,
                        "push_probability": summary.p_push,
                        "fair_odds_american": summary.fair_over_american_odds,
                        "fair_over_odds_american": summary.fair_over_american_odds,
                        "fair_under_odds_american": summary.fair_under_american_odds,
                        "prediction_interval": {
                            "low": summary.prediction_interval_lower,
                            "high": summary.prediction_interval_upper,
                            "coverage": summary.prediction_interval_level,
                        },
                        "probability_difference": None if summary.p_over is None or no_vig_over is None else float(summary.p_over - no_vig_over),
                    }
                )
                market_line_for_id = line
            elif public_prop in BINARY_PUBLIC_PROPS:
                td_probability = float(np.mean(samples >= 1.0))
                p2 = float(np.mean(samples >= 2.0))
                expected_tds = float(np.mean(samples))
                if internal_prop in {"rushing_tds", "receiving_tds"}:
                    line = _finite(market.get("consensus_line")) if market else None
                    threshold_ok = line is not None and math.isclose(line, 0.5, abs_tol=1e-9)
                    no_vig = _finite(market.get("consensus_no_vig_p_over")) if market else None
                    best = market.get("best_over_price") if market else None
                    if not threshold_ok:
                        critical_ok = False
                        notes.append("rushing/receiving TD binary publication requires a 0.5 count line")
                else:
                    line = None
                    no_vig = _finite(market.get("consensus_no_vig_probability")) if market else None
                    best = market.get("best_yes_price") if market else None
                td_price = _price_american(best)
                if td_price is None or no_vig is None:
                    critical_ok = False
                    notes.append("two-way TD price/no-vig probability unavailable")
                market_block.update(
                    {
                        "source": "consensus" if market else None,
                        "sportsbook": "consensus" if market else None,
                        "captured_utc": _market_capture_utc(market) if market else None,
                        "td_price_american": td_price,
                        "raw_implied_probability": american_to_implied(td_price) if td_price is not None else None,
                        "no_vig_probability": no_vig,
                        "underlying_count_line": line,
                    }
                )
                fair_td_odds = probability_to_american(td_probability)
                model_block.update(
                    {
                        "td_probability": td_probability,
                        "expected_tds": expected_tds,
                        "probability_2_plus_td": p2,
                        "fair_odds_american": fair_td_odds,
                        "fair_td_odds_american": fair_td_odds,
                        "probability_difference": None if no_vig is None else td_probability - no_vig,
                    }
                )
                market_line_for_id = line
            else:
                raise PropsIntegrationError(f"unsupported publication prop type: {public_prop}")

            if market is not None and market.get("closing_evaluation") is not None:
                critical_ok = False
                notes.append("closing evaluation must not enter prospective forecast artifact")

            signal_state = "WATCH" if critical_ok else "NO SIGNAL"
            forecast_iso = forecast_dt.isoformat()
            forecasts.append(
                {
                    "forecast_id": _forecast_id(
                        game_id=result.game_id,
                        player_id=player.player_id,
                        prop_type=public_prop,
                        forecast_timestamp_utc=forecast_iso,
                        market_line=market_line_for_id,
                        model_version=result.model_version,
                    ),
                    "player_identity_resolved": True,
                    "player_id": player.player_id,
                    "player": player.player,
                    "position": position,
                    "team": player.team,
                    "opponent": player.opponent,
                    "game_id": result.game_id,
                    "kickoff_utc": kickoff_dt.isoformat(),
                    "forecast_timestamp_utc": forecast_iso,
                    "data_horizon_utc": horizon_dt.isoformat(),
                    "prop_type": public_prop,
                    "signal_state": signal_state,
                    "market": market_block,
                    "model": model_block,
                    "data_quality": {
                        "state": quality_state,
                        "critical_ok": bool(critical_ok),
                        "confidence": quality_state,
                        "notes": notes,
                    },
                    "drivers": list(
                        drivers.get(
                            (player.player_id, public_prop),
                            drivers.get((player.player_id, internal_prop), ()),
                        )
                    ),
                    "provenance": {
                        "research_label": RESEARCH_LABEL,
                        "pure_simulation_seed": int(result.seed),
                        "pure_simulation_market_agnostic": True,
                        "market_join_key": f"{result.game_id}:{player.player_id}:{internal_prop}",
                        "market": _market_provenance(market),
                    },
                }
            )

    return {
        "contract_version": FORECAST_CONTRACT_VERSION,
        "generated_utc": forecast_dt.isoformat(),
        "research_label": RESEARCH_LABEL,
        "scope": "OFFENSIVE_PROPS_ONLY",
        "forecasts": forecasts,
    }
