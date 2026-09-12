from __future__ import annotations

"""Compose outcome-blind LevLine 4 evidence bundles for prospective grading.

This module is intentionally *not* a picker.  It joins three already-qualified research
channels at strict pre-kickoff horizons:

1. component-resolved football probabilities;
2. strict point-in-time market state and same-book movement microstructure; and
3. timestamped, explainability-only player availability state.

No winner switch, threshold, coefficient, or learned cross-channel weight is defined here.
The output exists only so a future candidate can be specified on genuinely prior evidence
and then graded prospectively on a fresh sample.
"""

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "levline4-upset-evidence-v1"
COMPONENTS = ("logistic", "extra_trees", "xgboost", "catboost")
HORIZON_MINUTES = {
    "T-120m": 120,
    "T-60m": 60,
    "T-45m": 45,
    "T-30m": 30,
}
HORIZON_SUFFIX = {
    "T-120m": "t120",
    "T-60m": "t60",
    "T-45m": "t45",
    "T-30m": "t30",
}
PAIR_FROM_T120 = {
    "T-60m": "t60_minus_t120",
    "T-45m": "t45_minus_t120",
    "T-30m": "t30_minus_t120",
}
FORBIDDEN_OUTCOME_KEYS = {
    "home_win",
    "away_win",
    "winner",
    "winning_team",
    "result",
    "home_score",
    "away_score",
    "actual_home_score",
    "actual_away_score",
    "actual_margin",
    "actual_winner",
    "final_home_score",
    "final_away_score",
    "final_score",
}


def _parse_utc(value: object) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _float(value: object) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    parsed = float(value)
    if parsed != parsed:
        return None
    return parsed


def _int(value: object) -> int | None:
    parsed = _float(value)
    return int(parsed) if parsed is not None else None


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _assert_outcome_blind(value: Any, *, context: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).strip().lower() in FORBIDDEN_OUTCOME_KEYS:
                raise ValueError(f"{context} contains forbidden outcome field {key!r}")
            _assert_outcome_blind(child, context=context)
    elif isinstance(value, list):
        for child in value:
            _assert_outcome_blind(child, context=context)


def _validate_research_flags(row: dict[str, Any], *, context: str) -> None:
    if "research_only" in row and not _truthy(row.get("research_only")):
        raise ValueError(f"{context} is not marked research-only")
    if "production_authorized" in row and _truthy(row.get("production_authorized")):
        raise ValueError(f"{context} is production-authorized")
    if "completed_2026_outcomes_used" in row:
        used = _int(row.get("completed_2026_outcomes_used"))
        if used not in (None, 0):
            raise ValueError(f"{context} used completed 2026 outcomes")


def _cutoff(kickoff: datetime, horizon: str) -> datetime:
    return kickoff - timedelta(minutes=HORIZON_MINUTES[horizon])


def _select_component_row(
    rows: Iterable[dict[str, Any]],
    *,
    game_id: str,
    cutoff: datetime,
) -> dict[str, Any] | None:
    eligible: list[tuple[datetime, dict[str, Any]]] = []
    for raw in rows:
        row = dict(raw)
        if str(row.get("game_id") or "").strip() != game_id:
            continue
        _assert_outcome_blind(row, context="component snapshot")
        _validate_research_flags(row, context="component snapshot")
        stamp_raw = row.get("generated_utc")
        if not stamp_raw:
            continue
        stamp = _parse_utc(stamp_raw)
        if stamp <= cutoff:
            eligible.append((stamp, row))
    if not eligible:
        return None
    eligible.sort(key=lambda item: item[0])
    return eligible[-1][1]


def _component_summary(row: dict[str, Any], *, market_home_prob: float | None) -> dict[str, Any]:
    probs: dict[str, float] = {}
    for name in COMPONENTS:
        value = _float(row.get(f"{name}_home_prob"))
        if value is None or not 0.0 <= value <= 1.0:
            raise ValueError(f"component snapshot has invalid {name} probability")
        probs[name] = value
    votes = sum(value >= 0.5 for value in probs.values())
    mean_prob = sum(probs.values()) / len(probs)
    mean_square = sum(value * value for value in probs.values()) / len(probs)
    std = max(0.0, mean_square - mean_prob * mean_prob) ** 0.5
    if votes >= 3:
        majority_side = "home"
    elif votes <= 1:
        majority_side = "away"
    else:
        majority_side = "split"
    unanimous_side = "home" if votes == 4 else "away" if votes == 0 else None
    return {
        "generated_utc": str(row.get("generated_utc")),
        "source_sha": str(row.get("source_sha") or ""),
        "feature_set": row.get("feature_set"),
        "probabilities": probs,
        "home_votes": votes,
        "mean_home_prob": mean_prob,
        "std_home_prob": std,
        "min_home_prob": min(probs.values()),
        "max_home_prob": max(probs.values()),
        "range_home_prob": max(probs.values()) - min(probs.values()),
        "majority_side": majority_side,
        "unanimous_side": unanimous_side,
        "component_minus_market_home_prob": (
            mean_prob - market_home_prob if market_home_prob is not None else None
        ),
        "descriptive_only": True,
    }


def _market_summary(row: dict[str, Any], *, horizon: str, cutoff: datetime) -> dict[str, Any] | None:
    _assert_outcome_blind(row, context="market state")
    _validate_research_flags(row, context="market state")
    if not _truthy(row.get("strict_no_later_than_cutoff")):
        raise ValueError("market state is not strict no-later-than-cutoff")
    suffix = HORIZON_SUFFIX[horizon]
    request_raw = row.get(f"request_timestamp_utc_{suffix}")
    if not request_raw:
        return None
    request_time = _parse_utc(request_raw)
    if request_time > cutoff:
        raise ValueError(
            f"market state for {row.get('game_id')} {horizon} is after its nominal cutoff"
        )
    timing_error = _float(row.get(f"timing_error_minutes_{suffix}"))
    if timing_error is not None and timing_error > 0:
        raise ValueError("market state has positive timing error")
    market_prob = _float(row.get(f"market_home_prob_{suffix}"))
    if market_prob is None or not 0.0 <= market_prob <= 1.0:
        raise ValueError("market state has invalid home probability")
    summary: dict[str, Any] = {
        "request_timestamp_utc": _iso(request_time),
        "timing_error_minutes": timing_error,
        "home_probability": market_prob,
        "home_spread": _float(row.get(f"home_spread_{suffix}")),
        "total_points": _float(row.get(f"total_points_{suffix}")),
        "probability_range": _float(row.get(f"probability_range_{suffix}")),
        "source_count": _int(row.get(f"source_count_{suffix}")),
        "max_freshness_minutes": _float(row.get(f"max_freshness_minutes_{suffix}")),
        "strict_no_later_than_cutoff": True,
    }
    pair = PAIR_FROM_T120.get(horizon)
    if pair:
        summary["movement_from_t120"] = {
            "home_probability_change": _float(row.get(f"home_probability_{pair}")),
            "home_probability_change_pp": _float(row.get(f"home_probability_pp_{pair}")),
            "home_logit_change": _float(row.get(f"home_logit_{pair}")),
            "home_spread_change": _float(row.get(f"home_spread_{pair}")),
            "total_points_change": _float(row.get(f"total_points_{pair}")),
            "probability_range_change": _float(row.get(f"probability_range_{pair}")),
            "same_book_common_count": _int(row.get(f"book_common_count_{pair}")),
            "sportsbook_overlap_fraction": _float(row.get(f"book_overlap_fraction_{pair}")),
            "home_move_share": _float(row.get(f"book_home_move_share_{pair}")),
            "away_move_share": _float(row.get(f"book_away_move_share_{pair}")),
            "unchanged_share": _float(row.get(f"book_unchanged_share_{pair}")),
            "movement_breadth": _float(row.get(f"book_movement_breadth_{pair}")),
            "median_probability_change_pp": _float(
                row.get(f"book_median_probability_change_pp_{pair}")
            ),
            "median_logit_change": _float(row.get(f"book_median_logit_change_{pair}")),
        }
    else:
        summary["movement_from_t120"] = None
    return summary


def _status_label(player: dict[str, Any]) -> str:
    availability = player.get("availability") or {}
    return str(
        availability.get("game_status")
        or availability.get("practice_status")
        or "attention_required"
    )


def _select_personnel_payload(
    payloads: Iterable[dict[str, Any]],
    *,
    cutoff: datetime,
) -> dict[str, Any] | None:
    eligible: list[tuple[datetime, dict[str, Any]]] = []
    for payload in payloads:
        _assert_outcome_blind(payload, context="player-state payload")
        if payload.get("probability_feature_authorized") is not False:
            raise ValueError("player-state payload is authorized as a probability feature")
        if payload.get("live_site_consumes_this_file") is not False:
            raise ValueError("player-state payload is consumed by the live site")
        audit = payload.get("capture_audit") or {}
        if _int(audit.get("completed_2026_outcomes_used")) not in (None, 0):
            raise ValueError("player-state payload used completed 2026 outcomes")
        stamp_raw = audit.get("source_commit_timestamp_utc")
        if not stamp_raw:
            continue
        stamp = _parse_utc(stamp_raw)
        if stamp <= cutoff:
            eligible.append((stamp, payload))
    if not eligible:
        return None
    eligible.sort(key=lambda item: item[0])
    return eligible[-1][1]


def _personnel_summary(
    payload: dict[str, Any],
    *,
    game_id: str,
    home_team: str,
    away_team: str,
    cutoff: datetime,
) -> dict[str, Any] | None:
    game = next(
        (row for row in payload.get("games", []) if str(row.get("game_id") or "") == game_id),
        None,
    )
    if game is None:
        return None
    audit = payload.get("capture_audit") or {}
    source_time = _parse_utc(audit.get("source_commit_timestamp_utc"))
    if source_time > cutoff:
        return None
    players = [dict(player) for player in game.get("players", []) if isinstance(player, dict)]
    compact_players: list[dict[str, Any]] = []
    statuses: dict[str, Counter[str]] = {home_team: Counter(), away_team: Counter()}
    counts = {home_team: 0, away_team: 0}
    for player in players:
        team = str(player.get("team") or "")
        if team not in counts:
            continue
        availability = player.get("availability") or {}
        if availability.get("source_status") != "qualified":
            raise ValueError("player-state card is not source-qualified")
        as_of = availability.get("source_data_as_of")
        if as_of and _parse_utc(as_of) > cutoff:
            raise ValueError("player-state card was not available by the horizon cutoff")
        counts[team] += 1
        statuses[team][_status_label(player)] += 1
        compact_players.append(
            {
                "team": team,
                "player_id": player.get("player_id"),
                "player_name": player.get("player_name"),
                "position": player.get("position"),
                "practice_status": availability.get("practice_status"),
                "game_status": availability.get("game_status"),
                "source_data_as_of": as_of,
            }
        )

    changes = {home_team: 0, away_team: 0}
    for event in payload.get("state_changes", []):
        if not isinstance(event, dict):
            continue
        team = str(event.get("team") or "")
        if team not in changes:
            continue
        stamp_raw = event.get("current_source_commit_timestamp_utc")
        if stamp_raw and _parse_utc(stamp_raw) <= cutoff:
            changes[team] += 1

    compact_players.sort(key=lambda row: (str(row["team"]), str(row["position"]), str(row["player_name"])))
    return {
        "source_commit_timestamp_utc": _iso(source_time),
        "source_commit_sha": audit.get("source_commit_sha"),
        "home_attention_count": counts[home_team],
        "away_attention_count": counts[away_team],
        "home_status_counts": dict(sorted(statuses[home_team].items())),
        "away_status_counts": dict(sorted(statuses[away_team].items())),
        "home_state_change_count": changes[home_team],
        "away_state_change_count": changes[away_team],
        "players": compact_players,
        "modeled_player_impacts_created": 0,
        "probability_feature_authorized": False,
        "descriptive_only": True,
    }


def build_evidence_payload(
    component_rows: Iterable[dict[str, Any]],
    market_rows: Iterable[dict[str, Any]],
    *,
    personnel_payloads: Iterable[dict[str, Any]] = (),
    generated_utc: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    components = [dict(row) for row in component_rows]
    markets = [dict(row) for row in market_rows]
    personnel = [dict(payload) for payload in personnel_payloads]
    _assert_outcome_blind(components, context="component inputs")
    _assert_outcome_blind(markets, context="market inputs")
    _assert_outcome_blind(personnel, context="player-state inputs")

    records: list[dict[str, Any]] = []
    market_seen: set[str] = set()
    for market_row in sorted(markets, key=lambda row: str(row.get("game_id") or "")):
        game_id = str(market_row.get("game_id") or "").strip()
        if not game_id:
            raise ValueError("market state row missing game_id")
        if game_id in market_seen:
            raise ValueError(f"duplicate market state row for {game_id}")
        market_seen.add(game_id)
        kickoff = _parse_utc(market_row.get("kickoff_timestamp_utc"))
        home_team = str(market_row.get("home_team") or "").strip()
        away_team = str(market_row.get("away_team") or "").strip()
        if not home_team or not away_team:
            raise ValueError(f"market state row missing teams for {game_id}")

        for horizon in HORIZON_MINUTES:
            cutoff = _cutoff(kickoff, horizon)
            market = _market_summary(market_row, horizon=horizon, cutoff=cutoff)
            component_row = _select_component_row(components, game_id=game_id, cutoff=cutoff)
            component = (
                _component_summary(
                    component_row,
                    market_home_prob=market["home_probability"] if market else None,
                )
                if component_row is not None
                else None
            )
            personnel_payload = _select_personnel_payload(personnel, cutoff=cutoff)
            player_state = (
                _personnel_summary(
                    personnel_payload,
                    game_id=game_id,
                    home_team=home_team,
                    away_team=away_team,
                    cutoff=cutoff,
                )
                if personnel_payload is not None
                else None
            )
            record = {
                "schema_version": SCHEMA_VERSION,
                "game_id": game_id,
                "home_team": home_team,
                "away_team": away_team,
                "kickoff_timestamp_utc": _iso(kickoff),
                "horizon": horizon,
                "horizon_cutoff_utc": _iso(cutoff),
                "channel_available": {
                    "market": market is not None,
                    "components": component is not None,
                    "player_state": player_state is not None,
                },
                "market": market,
                "components": component,
                "player_state": player_state,
                "strict_pit_bundle_complete": all(
                    item is not None for item in (market, component, player_state)
                ),
                "winner_switch_rule_defined": False,
                "threshold_defined": False,
                "learned_cross_channel_weight_defined": False,
                "research_only": True,
                "production_authorized": False,
                "completed_2026_outcomes_used": 0,
            }
            _assert_outcome_blind(record, context="evidence output")
            records.append(record)

    generated = generated_utc or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": generated,
        "mode": "prospective_evidence_capture_not_picker",
        "primary_objective": "straight_up_winner_accuracy",
        "records": records,
        "winner_switch_rule_defined": False,
        "threshold_defined": False,
        "learned_cross_channel_weight_defined": False,
        "automatic_promotion": False,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    _assert_outcome_blind(payload, context="evidence payload")
    complete = sum(bool(row["strict_pit_bundle_complete"]) for row in records)
    audit = {
        "schema_version": SCHEMA_VERSION,
        "games": len(market_seen),
        "records": len(records),
        "strict_pit_complete_records": complete,
        "records_with_market": sum(bool(row["channel_available"]["market"]) for row in records),
        "records_with_components": sum(bool(row["channel_available"]["components"]) for row in records),
        "records_with_player_state": sum(bool(row["channel_available"]["player_state"]) for row in records),
        "horizons": list(HORIZON_MINUTES),
        "missingness_policy": "preserve_missing_no_imputation",
        "component_selection_policy": "latest_capture_generated_at_or_before_horizon_cutoff",
        "player_state_selection_policy": "latest_source_commit_available_at_or_before_horizon_cutoff",
        "market_policy": "strict_selected_consensus_request_at_or_before_nominal_cutoff",
        "winner_switch_rule_defined": False,
        "threshold_defined": False,
        "learned_cross_channel_weight_defined": False,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    return payload, audit


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--components", type=Path, action="append", required=True)
    parser.add_argument("--market-state", type=Path, required=True)
    parser.add_argument("--personnel", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()

    component_rows: list[dict[str, Any]] = []
    for path in args.components:
        component_rows.extend(_read_csv(path))
    personnel_payloads = [_read_json(path) for path in args.personnel]
    payload, audit = build_evidence_payload(
        component_rows,
        _read_csv(args.market_state),
        personnel_payloads=personnel_payloads,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
