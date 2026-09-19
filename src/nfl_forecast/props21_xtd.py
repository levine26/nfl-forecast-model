"""Separate Props 2.1 xTD research contract; no conversion-skill or 'due' boost.

Context xTD is sum(projected opportunities * context TD probability). Existing
live manifests lack field-position projections: the adapter explicitly reports
an inherited aggregate fallback, not a fitted contextual improvement.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

VERSION = "levline-props-2.1-xtd-v0.1"
MAX_TRAINING_SEASON = 2025
# Football-defined disjoint field zones, NOT scoring weights.
ZONE_EDGES = (5, 10, 20, 50, 100)
POSITIONS = frozenset({"QB", "RB", "FB", "WR", "TE"})
KINDS = frozenset({"rush", "target"})
FORBIDDEN = frozenset({"actual_current_game_snaps", "actual_participation",
    "actual_passing_tds", "actual_rushing_tds", "actual_receiving_tds",
    "actual_anytime_tds", "actual_td", "touchdown", "td_debt", "due_bonus"})


def _number(value: Any, label: str, *, high: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite nonnegative number")
    try:
        n = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be a finite nonnegative number") from exc
    if not math.isfinite(n) or n < 0 or (high is not None and n > high):
        raise ValueError(f"{label} outside permitted range")
    return n


def _time(value: Any, label: str) -> datetime:
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} requires an aware timestamp") from exc
    if t.tzinfo is None:
        raise ValueError(f"{label} requires an aware timestamp")
    return t.astimezone(timezone.utc)


def _season(value: Any) -> int:
    n = _number(value, "training season", high=MAX_TRAINING_SEASON)
    if n != int(n) or n < 1920:
        raise ValueError("training season must be an integer through 2025")
    return int(n)


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    result = tuple(str(row.get(k) or "").strip() for k in ("game_id", "team", "player_id"))
    if any(not x or x.lower() in {"nan", "none", "<na>"} for x in result):
        raise ValueError("canonical game/team/player identity required")
    return result  # type: ignore[return-value]


def _zone(value: Any) -> int:
    distance = _number(value, "yardline_100", high=100)
    if distance == 0:
        raise ValueError("yardline_100 must be positive before the play")
    return next(i for i, edge in enumerate(ZONE_EDGES) if distance <= edge)


def _monotone_decreasing(values: Sequence[float], weights: Sequence[float]) -> list[float]:
    """Weighted pool-adjacent-violators projection onto nearer >= farther."""
    blocks: list[list[float]] = []
    for i, (value, weight) in enumerate(zip(values, weights, strict=True)):
        blocks.append([float(i), float(i), value * weight, weight])
        while len(blocks) > 1 and blocks[-2][2] / blocks[-2][3] < blocks[-1][2] / blocks[-1][3]:
            right, left = blocks.pop(), blocks.pop()
            blocks.append([left[0], right[1], left[2] + right[2], left[3] + right[3]])
    result = [0.0] * len(values)
    for start, end, total, weight in blocks:
        for i in range(int(start), int(end) + 1):
            result[i] = total / weight
    return result


def fit_xtd_context_model(
    history: Sequence[Mapping[str, Any]], *, fit_timestamp: str,
    prior_strength: float = 40.0,
) -> dict[str, Any]:
    """Fit retrospective mechanism model; NEVER auto-promote to the live model.

    Inputs are distinct actual historical rush/target events (event_id, season,
    position, kind, yardline_100, touchdown, available_at, source). A 40-trial
    regularization design is fixed before evaluation, not claimed empirically
    optimal. Kind/zone -> position/kind/zone partial pooling uses no player TD
    conversion residual. Isotonic projection imposes opportunity monotonicity.
    """
    cutoff = _time(fit_timestamp, "fit_timestamp")
    strength = _number(prior_strength, "prior_strength")
    if strength < 20:
        raise ValueError("prior_strength below conservative research floor of 20")
    if not history:
        raise ValueError("training history cannot be empty")
    seen: set[str] = set()
    counts: dict[tuple[str, str, int], list[float]] = {}
    material = []
    seasons = []
    for row in history:
        season = _season(row.get("season"))
        event_id = str(row.get("event_id") or "").strip()
        if not event_id or event_id in seen:
            raise ValueError("distinct historical event_id required")
        seen.add(event_id)
        if not row.get("source"):
            raise ValueError("historical event source required")
        if _time(row.get("available_at"), "available_at") > cutoff:
            raise ValueError("historical event unavailable at fit timestamp")
        kind, position = str(row.get("kind")), str(row.get("position"))
        if kind not in KINDS or position not in POSITIONS:
            raise ValueError("unsupported opportunity kind/position")
        z = _zone(row.get("yardline_100"))
        td = _number(row.get("touchdown"), "touchdown", high=1)
        if td not in (0, 1):
            raise ValueError("historical touchdown must be binary")
        for key in ((kind, "ALL", z), (kind, position, z)):
            c = counts.setdefault(key, [0.0, 0.0]); c[0] += td; c[1] += 1
        seasons.append(season)
        material.append(dict(row))
    cells = []
    for kind in sorted({key[0] for key in counts}):
        successes = sum(counts.get((kind, "ALL", z), [0, 0])[0] for z in range(5))
        trials = sum(counts.get((kind, "ALL", z), [0, 0])[1] for z in range(5))
        pooled = (successes + .5) / (trials + 1)  # Jeffreys base smoothing.
        parent_values, parent_weights = [], []
        for z in range(5):
            s, n = counts.get((kind, "ALL", z), [0, 0])
            parent_values.append((s + strength * pooled) / (n + strength))
            parent_weights.append(n + strength)
        parent = _monotone_decreasing(parent_values, parent_weights)
        for position in ["ALL", *sorted(POSITIONS)]:
            values, weights = [], []
            for z in range(5):
                s, n = counts.get((kind, position, z), [0, 0])
                values.append(parent[z] if position == "ALL" else (s + strength * parent[z]) / (n + strength))
                weights.append(n + strength)
            probs = _monotone_decreasing(values, weights)
            for z, probability in enumerate(probs):
                s, n = counts.get((kind, position, z), [0, 0])
                cells.append({"kind": kind, "position": position, "zone": z,
                              "probability": probability, "events": int(n),
                              "parent_probability": parent[z],
                              "history_weight": n / (n + strength)})
    digest = hashlib.sha256(json.dumps(sorted(material, key=lambda r: str(r["event_id"])),
                                     sort_keys=True, allow_nan=False).encode()).hexdigest()
    return {"model_version": VERSION, "status": "CONTEXT_MODEL_RESEARCH_ONLY",
            "fit_timestamp": cutoff.isoformat(), "trained_through_season": max(seasons),
            "training_sha256": digest, "training_events": len(history),
            "prior_strength": strength, "cells": cells, "conversion_skill_multiplier": 1.0,
            "conversion_persistence_status": "NOT_ESTABLISHED_NO_ADJUSTMENT",
            "production_authorized": False}


def _summary(mean: float) -> dict[str, Any]:
    # Poisson thinning approximation, not the full shared-team simulator PMF.
    p = -math.expm1(-mean)
    american = None if p <= 0 or p >= 1 else (100 * (1 - p) / p if p < .5 else -100 * p / (1 - p))
    return {"expected_td": mean, "p_td_1_plus": p, "fair_td_odds": american,
            "probability_method": "POISSON_MARGINAL_APPROXIMATION_NOT_SIMULATOR",
            "probability_calibration_status": "UNVALIDATED_RESEARCH",
            "fair_td_odds_format": "american"}


def project_context_xtd(
    opportunities: Sequence[Mapping[str, Any]], model: Mapping[str, Any], *,
    forecast_timestamp: str, kickoff_timestamp: str,
) -> dict[str, Any]:
    """Score disjoint *projected* opportunity bins, never target-game events.

    Every row requires projected=True, opportunity_id, source, available_at,
    captured_at, game_id/team/player_id, position, kind, yardline_100 and
    expected_opportunities. Rows are expected opportunity mass, not observed
    future plays. The caller must supply a qualified pregame opportunity model.
    """
    forecast, kickoff = _time(forecast_timestamp, "forecast"), _time(kickoff_timestamp, "kickoff")
    if forecast >= kickoff:
        raise ValueError("forecast must be before kickoff")
    _season(model.get("trained_through_season"))
    if _time(model.get("fit_timestamp"), "model fit_timestamp") > forecast:
        raise ValueError("model was fitted after forecast")
    if model.get("model_version") != VERSION or not model.get("training_sha256"):
        raise ValueError("qualified context model provenance required")
    lookup = {(r["kind"], r["position"], r["zone"]): r for r in model["cells"]}
    sums: dict[tuple[str, str, str], dict[str, Any]] = {}
    seen: set[str] = set()
    for row in opportunities:
        if FORBIDDEN.intersection(row):
            raise ValueError("postgame outcomes/debt cannot enter projected opportunities")
        if row.get("projected") is not True or not row.get("source"):
            raise ValueError("qualified projected opportunity source required")
        oid = str(row.get("opportunity_id") or "")
        if not oid or oid in seen:
            raise ValueError("distinct disjoint opportunity_id required")
        seen.add(oid)
        available, captured = _time(row.get("available_at"), "available_at"), _time(row.get("captured_at"), "captured_at")
        if available > captured or captured > forecast:
            raise ValueError("projected opportunity information unavailable before forecast")
        identity = _identity(row)
        kind, pos = str(row.get("kind")), str(row.get("position"))
        if kind not in KINDS or pos not in POSITIONS:
            raise ValueError("unsupported opportunity kind/position")
        z = _zone(row.get("yardline_100"))
        cell = lookup.get((kind, pos, z))
        if cell is None:
            raise ValueError("context model has no supported event kind")
        n = _number(row.get("expected_opportunities"), "expected_opportunities")
        p = _number(cell["probability"], "context probability", high=1)
        target = sums.setdefault(identity, {"game_id": identity[0], "team": identity[1],
            "player_id": identity[2], "position": pos, "expected_td": 0.0,
            "red_zone_opportunity": 0.0, "goal_line_opportunity": 0.0,
            "total_opportunity": 0.0})
        if target["position"] != pos:
            raise ValueError("conflicting position within player identity")
        target["expected_td"] += n * p
        target["total_opportunity"] += n
        target["red_zone_opportunity"] += n if z <= 2 else 0
        target["goal_line_opportunity"] += n if z == 0 else 0
    result = []
    for row in sums.values():
        mean, n = row["expected_td"], row.pop("total_opportunity")
        result.append({**row, **_summary(mean), "td_opportunity_quality": mean / n if n else None,
            "td_debt_diagnostic": None, "td_data_quality": "PROJECTED_CONTEXT_RESEARCH_UNVALIDATED",
            "model_status": "CONTEXT_XTD_RESEARCH_ONLY", "model_version": VERSION,
            "training_sha256": model["training_sha256"], "conversion_skill_multiplier": 1.0})
    return {"model_version": VERSION, "players": result, "production_authorized": False}


def td_debt_diagnostic(*, historical_xtd: float, historical_actual_td: float,
                       through_season: int, available_at: str, forecast_timestamp: str) -> dict[str, Any]:
    """Separate historical diagnostic; never accepted as a projection feature."""
    _season(through_season)
    if _time(available_at, "available_at") > _time(forecast_timestamp, "forecast"):
        raise ValueError("diagnostic history unavailable before forecast")
    debt = _number(historical_xtd, "historical_xtd") - _number(historical_actual_td, "historical_actual_td")
    return {"td_debt_diagnostic": debt, "used_in_prediction": False,
            "conversion_skill_multiplier": 1.0,
            "persistence_status": "NOT_ESTABLISHED_NO_ADJUSTMENT"}


def build_xtd_from_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Read-only live adapter. Inherited aggregate expectations are explicit.

    Context xTD requires a trained model AND projected event contexts. Neither
    is fabricated from live manifest totals. Conditional marginals below are
    descriptive and never replace simulator probabilities.
    """
    forecast = _time(manifest.get("forecast_timestamp_utc"), "forecast")
    kickoff = _time(manifest.get("kickoff_utc"), "kickoff")
    if forecast >= kickoff:
        raise ValueError("manifest forecast must be pregame")
    players = manifest.get("efficiency_player_parameters")
    teams = manifest.get("team_td_parameters")
    if not isinstance(players, (list, tuple)) or not players or not isinstance(teams, (list, tuple)) or not teams:
        raise ValueError("manifest requires efficiency player and team TD rows")
    team_map = {}
    for row in teams:
        key = (str(row.get("game_id")), str(row.get("team")))
        if key in team_map:
            raise ValueError("duplicate team identity")
        team_map[key] = row
    result, seen = [], set()
    totals: dict[tuple[str, str], list[float]] = {}
    for row in players:
        key = _identity(row)
        if key in seen or key[0] != str(manifest.get("game_id")):
            raise ValueError("duplicate/mismatched player identity")
        seen.add(key)
        if FORBIDDEN.intersection(row):
            raise ValueError("postgame/debt fields prohibited in xTD adapter")
        if key[:2] not in team_map:
            raise ValueError("player has no team scoring environment")
        for item in (row, team_map[key[:2]]):
            _season(item.get("prior_model_trained_through_season"))
            if _time(item.get("feature_data_horizon"), "feature_data_horizon") > forecast:
                raise ValueError("feature horizon after forecast")
            if _time(item.get("forecast_timestamp"), "row forecast") != forecast:
                raise ValueError("row forecast must match manifest forecast")
            if _time(item.get("kickoff_timestamp"), "row kickoff") != kickoff:
                raise ValueError("row kickoff must match manifest kickoff")
        pos = str(row.get("position"))
        if pos not in POSITIONS:
            raise ValueError("unsupported position")
        passing, receiving, rushing = [_number(row.get(f"expected_{kind}_tds"), f"expected_{kind}_tds") for kind in ("passing", "receiving", "rushing")]
        attempts = _number(row.get("expected_pass_attempts"), "expected_pass_attempts")
        targets = _number(row.get("expected_targets"), "expected_targets")
        carries = _number(row.get("expected_qb_rush_attempts" if pos == "QB" else "expected_carries"), "rush opportunities")
        invalid = (passing > 0 and attempts == 0) or (receiving > 0 and targets == 0) or (rushing > 0 and carries == 0)
        total = totals.setdefault(key[:2], [0.0, 0.0, 0.0])
        for i, n in enumerate((passing, receiving, rushing)): total[i] += n
        mean = rushing if pos == "QB" else rushing + receiving
        red_zone = _number(row.get("expected_red_zone_targets"), "expected_red_zone_targets")
        goal_line = _number(row.get("expected_goal_line_carries"), "expected_goal_line_carries")
        if red_zone > targets + 1e-9 or goal_line > carries + 1e-9:
            invalid = True
        result.append({"game_id": key[0], "team": key[1], "player_id": key[2], "position": pos,
            **_summary(mean), "expected_passing_tds": passing, "expected_receiving_tds": receiving,
            "expected_rushing_tds": rushing, "red_zone_opportunity": red_zone,
            "red_zone_opportunity_scope": "TARGETS_ONLY_RUSH_RED_ZONE_UNAVAILABLE",
            "goal_line_opportunity": goal_line, "goal_line_opportunity_scope": "CARRIES_ONLY",
            "td_opportunity_quality": None, "td_debt_diagnostic": None,
            "td_data_quality": "INVALID_ZERO_OPPORTUNITY" if invalid else "AGGREGATE_FALLBACK_NO_FIELD_POSITION",
            "source_status": row.get("source_status", "unknown"),
            "model_status": "INHERITED_AGGREGATE_DIAGNOSTIC_NOT_CONTEXT_XTD",
            "model_version": VERSION, "conversion_skill_multiplier": 1.0,
            "probability_is_authoritative": False, "context_fitted": False,
            "used_to_modify_simulation": False})
    reconciliation = []
    for key, total in totals.items():
        team = team_map[key]
        passing = _number(team.get("expected_passing_td_opportunities"), "team passing TD")
        rushing = _number(team.get("expected_rushing_td_opportunities"), "team rushing TD")
        errors = [total[0] - passing, total[1] - passing, total[2] - rushing]
        reconciliation.append({"game_id": key[0], "team": key[1], "errors": errors,
                               "reconciled": all(abs(e) < 1e-8 for e in errors)})
    return {"model_version": VERSION, "players": result, "audit": {
        "player_count": len(result), "context_fitted_count": 0,
        "aggregate_fallback_count": len(result), "td_debt_used_in_prediction": False,
        "conversion_persistence_status": "NOT_ESTABLISHED_NO_ADJUSTMENT",
        "completed_2026_outcomes_used": 0, "source_manifest_mutated": False,
        "invalid_opportunity_count": sum(r["td_data_quality"].startswith("INVALID") for r in result),
        "team_reconciliation": reconciliation,
        "probabilities_replace_simulator": False}}
