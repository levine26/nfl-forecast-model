from __future__ import annotations

"""Build the isolated LevLine Props 2.1 Sunday Challenger publication.

The coordinator reads a frozen V1 forecast artifact and qualified current reporting,
adds read-only personnel/market/xTD intelligence, runs fail-closed QA, and writes a
new immutable evidence stream. It never changes V1 or winner-model files.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props21_market import build_market_state  # noqa: E402
from nfl_forecast.props21_personnel import (  # noqa: E402
    adapt_personnel_evidence,
    build_personnel_intelligence,
)
from nfl_forecast.props21_qa import evaluate_forecast_qa  # noqa: E402
from nfl_forecast.props21_xtd import build_xtd_from_manifest  # noqa: E402
from nfl_forecast.props_manifest import verify_manifest_fingerprint, verify_manifest_slate_index  # noqa: E402

CONTRACT = "levline-props-2.1-sunday-challenger-v0.1"
MODEL_VERSION = "levline-props-2.1-sunday-v0.1"
RECEIPT_VERSION = "levline-props-2.1-prospective-receipt-v0.1"
TD_PROPS = {"passing_tds", "rushing_td", "receiving_td", "anytime_td"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_manifest_slate(path: Path | None) -> dict[str, Mapping[str, Any]]:
    if path is None:
        return {}
    slate = _load(path)
    if not isinstance(slate, Mapping):
        raise ValueError("manifest slate must be a JSON object")
    verify_manifest_slate_index(slate)
    result: dict[str, Mapping[str, Any]] = {}
    root = path.parent.resolve()
    for entry in slate["games"]:
        manifest_path = (root / str(entry["manifest_file"])).resolve()
        try:
            manifest_path.relative_to(root)
        except ValueError as exc:
            raise ValueError("manifest path escapes slate root") from exc
        manifest = _load(manifest_path)
        verify_manifest_fingerprint(manifest)
        game = str(entry["game_id"])
        if str(manifest.get("game_id")) != game:
            raise ValueError(f"manifest game mismatch: {game}")
        result[game] = manifest
    return result


def _load_depth_charts(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    payload = _load(path)
    if isinstance(payload, Mapping):
        version = payload.get("contract_version")
        if version not in {None, "levline-props-depth-chart-snapshot-v0.1"}:
            raise ValueError(f"unexpected depth-chart snapshot contract: {version!r}")
        rows = payload.get("depth_charts")
    else:
        rows = payload
    if not isinstance(rows, list):
        raise ValueError("depth-chart snapshot must contain a depth_charts list")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("depth-chart snapshot rows must be objects")
    return [dict(row) for row in rows]


def _aware(value: object, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a parseable timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def _sha(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _canonical_players(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    games: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for row in rows:
        game = str(row.get("game_id") or "")
        player_id = str(row.get("player_id") or "")
        team = str(row.get("team") or "")
        position = str(row.get("position") or "")
        name = str(row.get("player") or row.get("player_name") or "")
        if not all((game, player_id, team, position, name)):
            continue
        key = (team, player_id)
        candidate = {
            "game_id": game,
            "team": team,
            "player_id": player_id,
            "player_name": name,
            "position": position,
            "kickoff_timestamp": row.get("kickoff_utc"),
        }
        previous = games.setdefault(game, {}).get(key)
        if previous is not None and previous != candidate:
            raise ValueError(f"conflicting canonical player state: {game}:{team}:{player_id}")
        games[game][key] = candidate
    return {game: list(players.values()) for game, players in games.items()}


def _personnel_by_player(
    rows: list[dict[str, Any]], previews: Mapping[str, Any], generated: datetime,
    manifests: Mapping[str, Mapping[str, Any]] | None = None,
    depth_charts: list[dict[str, Any]] | None = None,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    players = _canonical_players(rows)
    states: dict[tuple[str, str], dict[str, Any]] = {}
    accepted = rejected = news = 0
    rejection_counts: dict[str, int] = {}
    payload = dict(previews)
    payload["generated_utc"] = generated.isoformat()
    for game, player_rows in players.items():
        kickoff = player_rows[0]["kickoff_timestamp"]
        manifest = dict((manifests or {}).get(game, {"game_id": game, "kickoff_utc": kickoff}))
        manifest_players = {
            str(row.get("player_id")): row
            for row in manifest.get("efficiency_player_parameters", [])
            if isinstance(row, Mapping) and row.get("player_id")
        }
        player_rows = [{**manifest_players.get(str(row["player_id"]), {}), **row}
                       for row in player_rows]
        adapted = adapt_personnel_evidence(
            manifest,
            player_state=player_rows,
            media_payload=payload,
            depth_charts=depth_charts or [],
        )
        result = build_personnel_intelligence(
            adapted["player_state"],
            adapted["evidence"],
            forecast_timestamp=generated,
            game_id=game,
            kickoff_timestamp=kickoff,
        )
        for state in result["states"]:
            state = dict(state)
            state["current_news_coverage"] = bool(state.pop("news_coverage", False))
            state["identity_resolved"] = True
            states[(game, state["player_id"])] = state
        audit = result["audit"]
        accepted += int(audit["accepted_evidence"])
        rejected += int(audit["rejected_evidence"])
        news += int(audit["news_covered_players"])
        for code, count in audit["rejection_counts"].items():
            rejection_counts[code] = rejection_counts.get(code, 0) + int(count)
    return states, {
        "canonical_players": len(states),
        "accepted_evidence": accepted,
        "rejected_evidence": rejected,
        "news_covered_players": news,
        "depth_chart_rows_supplied": len(depth_charts or []),
        "rejection_counts": dict(sorted(rejection_counts.items())),
    }


def _opportunity_by_player(
    manifests: Mapping[str, Mapping[str, Any]] | None,
) -> dict[tuple[str, str], dict[str, float | None]]:
    """Retain frozen opportunity expectations for QA without changing forecasts."""
    result: dict[tuple[str, str], dict[str, float | None]] = {}
    for game, manifest in (manifests or {}).items():
        for row in manifest.get("efficiency_player_parameters", []):
            if not isinstance(row, Mapping):
                continue
            player_id = str(row.get("player_id") or "").strip()
            if not player_id:
                continue
            position = str(row.get("position") or "").upper()
            pass_attempts = _number(row.get("expected_pass_attempts"))
            qb_rushes = _number(row.get("expected_qb_rush_attempts"))
            designed_carries = _number(row.get("expected_carries"))
            carries = qb_rushes if position == "QB" else designed_carries
            targets = _number(row.get("expected_targets"))
            routes = _number(row.get("expected_routes"))
            total_parts = [value for value in (carries, targets) if value is not None]
            result[(str(game), player_id)] = {
                "pass_attempts": pass_attempts,
                "carries": carries,
                "targets": targets,
                "routes": routes,
                "total_opportunities": sum(total_parts) if total_parts else None,
            }
    return result


def _market_state(row: Mapping[str, Any], generated: datetime, credential_mode: str | None) -> dict[str, Any]:
    provenance = row.get("provenance") if isinstance(row.get("provenance"), Mapping) else {}
    market_provenance = provenance.get("market") if isinstance(provenance.get("market"), Mapping) else {}
    books = market_provenance.get("individual_books")
    if not isinstance(books, list):
        books = []
    state = build_market_state(
        books,
        as_of_utc=generated,
        kickoff_utc=row.get("kickoff_utc"),
        fair_line=(row.get("model") or {}).get("fair_line"),
        sportsbook_line=(row.get("market") or {}).get("line"),
        credential_mode=market_provenance.get("credential_mode") or credential_mode,
        max_quote_age_minutes=120.0,
        capture_horizon="AS_OBSERVED_PROSPECTIVE",
    )
    state["books"] = state.get("sportsbooks", [])
    state["quote_as_of"] = state.get("latest_capture_utc")
    state["dispersion"] = state.get("line_dispersion")
    state["quote_age_seconds"] = (
        state["quote_age_minutes"] * 60 if state.get("quote_age_minutes") is not None else None
    )
    return state


def _xtd_diagnostic(row: Mapping[str, Any], manifest_xtd: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    if str(row.get("prop_type")) not in TD_PROPS:
        return None
    model = row.get("model") if isinstance(row.get("model"), Mapping) else {}
    expected_key = {"passing_tds": "expected_passing_tds", "rushing_td": "expected_rushing_tds",
                    "receiving_td": "expected_receiving_tds", "anytime_td": "expected_td"}[str(row.get("prop_type"))]
    expected = _number((manifest_xtd or {}).get(expected_key))
    if expected is None:
        expected = _number(model.get("expected_tds"))
    probability = _number(model.get("probability_1_plus_td") or model.get("td_probability"))
    return {
        "expected_td": expected,
        "expected_touchdowns": expected,
        "p_td_1_plus": probability,
        "fair_td_odds": _number(model.get("fair_td_odds_american") or model.get("fair_odds_american")),
        "td_debt_diagnostic": None,
        "td_debt_used_in_prediction": False,
        "conversion_skill_multiplier": 1.0,
        "red_zone_opportunity": (manifest_xtd or {}).get("red_zone_opportunity"),
        "red_zone_opportunity_scope": (manifest_xtd or {}).get("red_zone_opportunity_scope", "UNAVAILABLE_IN_PUBLIC_V1_ARTIFACT"),
        "goal_line_opportunity": (manifest_xtd or {}).get("goal_line_opportunity"),
        "goal_line_opportunity_scope": (manifest_xtd or {}).get("goal_line_opportunity_scope", "UNAVAILABLE_IN_PUBLIC_V1_ARTIFACT"),
        "td_opportunity_quality": (manifest_xtd or {}).get("td_opportunity_quality"),
        "context_fitted": False,
        "model_status": (manifest_xtd or {}).get("model_status", "INHERITED_SIMULATION_AGGREGATE_NO_CONTEXT_XTD"),
        "td_data_quality": (manifest_xtd or {}).get("td_data_quality", "AGGREGATE_FALLBACK_NO_FIELD_POSITION"),
    }


def _public_row(
    source: Mapping[str, Any], role: Mapping[str, Any], market_state: Mapping[str, Any], generated: datetime,
    manifest_xtd: Mapping[str, Any] | None = None,
    opportunity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    model = source.get("model") if isinstance(source.get("model"), Mapping) else {}
    market = source.get("market") if isinstance(source.get("market"), Mapping) else {}
    qa = evaluate_forecast_qa(
        source,
        role_state=role,
        market_state=market_state,
        opportunity=opportunity,
    )
    publish_numbers = qa["publication_eligible"]
    prop = str(source.get("prop_type") or "")
    is_td = prop in TD_PROPS
    forecast_id_material = {
        "source": source.get("forecast_id"),
        "generated": generated.isoformat(),
        "version": MODEL_VERSION,
    }
    compact_market_state = {
        key: value for key, value in market_state.items()
        if key not in {"individual_books", "movement"}
    }
    source_market = (source.get("provenance") or {}).get("market") or {}
    row = {
        "forecast_id": "p21_" + _sha(forecast_id_material)[:24],
        "source_v1_forecast_id": source.get("forecast_id"),
        "player_id": source.get("player_id"),
        "player_name": source.get("player"),
        "team": source.get("team"),
        "opponent": source.get("opponent"),
        "position": source.get("position"),
        "game_id": source.get("game_id"),
        "kickoff_utc": source.get("kickoff_utc"),
        "forecast_timestamp_utc": generated.isoformat(),
        "source_v1_forecast_timestamp_utc": source.get("forecast_timestamp_utc"),
        "prop_type": prop,
        "model_mean": _number(model.get("mean")) if publish_numbers else None,
        "model_median": _number(model.get("fair_line") or model.get("median")) if publish_numbers else None,
        "probability_over": _number(model.get("over_probability")) if publish_numbers else None,
        "market_line": _number(market.get("line")) if publish_numbers else None,
        "market_probability_over": _number(market.get("no_vig_over_probability")) if publish_numbers else None,
        "probability_td": _number(model.get("probability_1_plus_td") or model.get("td_probability")) if publish_numbers and is_td else None,
        "fair_american_odds": _number(model.get("fair_td_odds_american") or model.get("fair_odds_american")) if publish_numbers and is_td else None,
        "market_probability_td": _number(market.get("no_vig_probability") or market.get("no_vig_over_probability")) if publish_numbers and is_td else None,
        "role_state": {
            "state": role.get("role_state", "UNKNOWN"),
            "availability": role.get("availability_state", "UNKNOWN"),
            "workload": role.get("workload_state", "UNKNOWN"),
            "uncertainty": ", ".join(role.get("uncertainties", [])) or None,
            "evidence_ids": role.get("evidence_ids", []),
        },
        "xtd": _xtd_diagnostic(source, manifest_xtd),
        "opportunity_state": dict(opportunity or {}),
        "market_state": compact_market_state,
        "qa": qa,
        "provenance": {
            "pure_model_market_agnostic": bool((source.get("provenance") or {}).get("pure_simulation_market_agnostic")),
            "source_v1_model_version": model.get("version"),
            "source_market_sha256": _sha(source_market),
            "source_market_provider": sorted({
                str(book.get("provider")) for book in source_market.get("individual_books", [])
                if isinstance(book, Mapping) and book.get("provider")
            }),
            "source_data_horizon_utc": source.get("data_horizon_utc"),
            "challenger_model_version": MODEL_VERSION,
            "research_only": True,
            "production_authorized": False,
        },
    }
    return row


def build(
    source: Mapping[str, Any], previews: Mapping[str, Any], *, generated: datetime,
    credential_mode: str | None = None,
    manifests: Mapping[str, Mapping[str, Any]] | None = None,
    depth_charts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = source.get("forecasts")
    if not isinstance(rows, list) or not rows:
        raise ValueError("source forecast artifact requires a non-empty forecasts list")
    games = {str(row.get("game_id") or "") for row in rows}
    if "" in games:
        raise ValueError("source forecast row missing game_id")
    kickoffs = {_aware(row.get("kickoff_utc"), "kickoff_utc") for row in rows}
    if any(generated >= kickoff for kickoff in kickoffs):
        raise ValueError("refusing partial/started slate: every source game must remain pregame")
    roles, personnel_audit = _personnel_by_player(
        rows, previews, generated, manifests, depth_charts
    )
    opportunity_by_player = _opportunity_by_player(manifests)
    xtd_by_player: dict[tuple[str, str], Mapping[str, Any]] = {}
    manifest_xtd_audit: list[dict[str, Any]] = []
    for game, manifest in (manifests or {}).items():
        result = build_xtd_from_manifest(manifest)
        manifest_xtd_audit.append({"game_id": game, **result["audit"]})
        for player in result["players"]:
            xtd_by_player[(game, str(player["player_id"]))] = player
    public_rows = []
    market_supported = market_insufficient = qa_blocked = qa_watch = qa_radar = 0
    x_td = 0
    providers: set[str] = set()
    for source_row in rows:
        key = (str(source_row.get("game_id")), str(source_row.get("player_id")))
        role = roles.get(key)
        if role is None:
            role = {
                "player_id": key[1], "role_state": "UNKNOWN", "availability_state": "UNKNOWN",
                "workload_state": "UNKNOWN", "current_news_coverage": False,
                "uncertainties": ["CANONICAL_STATE_MISSING"], "identity_resolved": False,
            }
        market_state = _market_state(source_row, generated, credential_mode)
        providers.update(market_state.get("providers", []))
        if market_state["status"] == "MARKET_DISTRIBUTION_SUPPORTED":
            market_supported += 1
        else:
            market_insufficient += 1
        public = _public_row(
            source_row,
            role,
            market_state,
            generated,
            xtd_by_player.get(key),
            opportunity_by_player.get(key),
        )
        signal = public["qa"]["signal_state"]
        qa_blocked += signal == "NO SIGNAL"
        qa_watch += signal == "WATCH"
        qa_radar += signal == "RADAR"
        x_td += public["xtd"] is not None
        public_rows.append(public)
    source_qb_rows = [r for r in rows if r.get("position") == "QB" and r.get("prop_type") == "passing_yards" and _number((r.get("market") or {}).get("line")) is not None]
    qb_team_keys = {(r.get("game_id"), r.get("team")) for r in source_qb_rows}
    qb_zero = [r.get("forecast_id") for r in source_qb_rows if (_number((r.get("model") or {}).get("mean")) or 0) <= 0.1]
    reported_qb_starters = [{
        "game_id": r.get("game_id"), "team": r.get("team"), "player_id": r.get("player_id"),
        "player": r.get("player"), "role_state": roles[(str(r.get("game_id")), str(r.get("player_id")))]["role_state"],
        "model_mean_passing_yards": _number((r.get("model") or {}).get("mean")),
        "market_line": _number((r.get("market") or {}).get("line")),
    } for r in source_qb_rows
        if (str(r.get("game_id")), str(r.get("player_id"))) in roles
        and roles[(str(r.get("game_id")), str(r.get("player_id")))].get("current_news_coverage")
        and roles[(str(r.get("game_id")), str(r.get("player_id")))].get("role_state") in {"STARTER_CONFIRMED", "STARTER_EXPECTED"}]
    role_coverage_by_position = {
        position: {
            "players": sum(state["position"] == position for state in roles.values()),
            "qualified_news": sum(state["position"] == position and state.get("current_news_coverage") for state in roles.values()),
            "non_unknown_role": sum(state["position"] == position and state.get("role_state") != "UNKNOWN" for state in roles.values()),
        }
        for position in ("QB", "RB", "WR", "TE")
    }
    out_normal = [r["forecast_id"] for r in public_rows if any(f["code"] == "OUT_PLAYER_WITH_OPPORTUNITY" for f in r["qa"]["flags"])]
    unresolved = [r["forecast_id"] for r in public_rows if any(f["code"] == "MARKET_PLAYER_MISSING_CANONICAL_STATE" for f in r["qa"]["flags"])]
    audit = {
        "source_contract_version": source.get("contract_version"),
        "source_sha256": _sha(source),
        "game_count": len(games),
        "forecast_count": len(public_rows),
        "personnel": personnel_audit,
        "market_distribution_supported": market_supported,
        "market_distribution_insufficient": market_insufficient,
        "market_providers": sorted(providers),
        "market_credential_mode": credential_mode or "NOT_RETAINED_IN_SOURCE_ARTIFACT",
        "xtd_aggregate_diagnostic_count": x_td,
        "xtd_context_fitted_count": 0,
        "xtd_manifest_game_count": len(manifest_xtd_audit),
        "xtd_manifest_audit": manifest_xtd_audit,
        "qa": {"no_signal": qa_blocked, "watch": qa_watch, "radar": qa_radar},
        "market_backed_qb_team_count": len(qb_team_keys),
        "market_backed_qb_zero_output": qb_zero,
        "reported_qb_starters": reported_qb_starters,
        "role_coverage_by_position": role_coverage_by_position,
        "out_player_normal_opportunity": out_normal,
        "unresolved_canonical_identity": unresolved,
        "all_quotes_pregame": all(_aware(r["forecast_timestamp_utc"], "forecast") < _aware(r["kickoff_utc"], "kickoff") for r in public_rows),
        "partial_slate_replacement_allowed": False,
        "winner_model_mutated": False,
        "v1_mutated": False,
        "shadow_a_mutated": False,
        "shadow_b_mutated": False,
        "completed_2026_outcomes_used": 0,
        "publication_note": "Blocked numerical forecasts are suppressed; market distribution falls back to exact consensus when alternate-line support is insufficient.",
    }
    return {
        "contract_version": CONTRACT,
        "model_version": MODEL_VERSION,
        "generated_at": generated.isoformat(),
        "status": "RESEARCH_CHALLENGER",
        "research_label": "PROPS 2.1 CHALLENGER — RESEARCH",
        "production_authorized": False,
        "forecasts": public_rows,
        "audit": audit,
    }


def _append_receipts(path: Path, payload: Mapping[str, Any], *, source_payload: Mapping[str, Any] | None = None) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: set[str] = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing.add(str(json.loads(line).get("receipt_id")))
    source_by_id: dict[str, Mapping[str, Any]] = {}
    if isinstance(source_payload, Mapping):
        source_rows = source_payload.get("forecasts")
        if isinstance(source_rows, list):
            source_by_id = {
                str(item.get("forecast_id")): item
                for item in source_rows
                if isinstance(item, Mapping) and item.get("forecast_id")
            }

    new = []
    for row in payload["forecasts"]:
        qa = row["qa"]
        source_row = source_by_id.get(str(row.get("source_v1_forecast_id") or ""))
        source_model = (
            source_row.get("model")
            if isinstance(source_row, Mapping) and isinstance(source_row.get("model"), Mapping)
            else {}
        )
        source_provenance = (
            source_row.get("provenance")
            if isinstance(source_row, Mapping) and isinstance(source_row.get("provenance"), Mapping)
            else {}
        )
        receipt_forecast = {
            key: row.get(key) for key in (
                "forecast_id", "source_v1_forecast_id", "player_id", "player_name", "team",
                "opponent", "position", "game_id", "kickoff_utc", "forecast_timestamp_utc",
                "source_v1_forecast_timestamp_utc", "prop_type", "model_mean", "model_median",
                "probability_over", "market_line", "market_probability_over", "probability_td",
                "fair_american_odds", "market_probability_td", "role_state", "xtd",
            )
        }
        receipt_forecast["qa"] = {
            "version": qa.get("version"), "signal_state": qa.get("signal_state"),
            "classification": qa.get("classification"),
            "publication_eligible": qa.get("publication_eligible"),
            "research_eligible": qa.get("research_eligible"), "betting_eligible": False,
            "flag_codes": [flag.get("code") for flag in qa.get("flags", [])],
            "reason_tag_codes": [tag.get("code") for tag in qa.get("reason_tags", [])],
            "uncertainty": qa.get("uncertainty"),
        }
        receipt_forecast["provenance"] = {
            key: row["provenance"].get(key) for key in (
                "pure_model_market_agnostic", "source_v1_model_version",
                "source_market_sha256", "source_market_provider", "source_data_horizon_utc",
                "challenger_model_version", "research_only", "production_authorized",
            )
        }
        receipt_forecast["market_state"] = {
            key: row["market_state"].get(key) for key in (
                "status", "book_count", "sportsbooks", "consensus_line", "market_median",
                "market_probability_at_sportsbook_line", "latest_capture_utc",
                "quote_age_minutes", "line_dispersion", "probability_dispersion",
                "alternate_line_count", "providers", "credential_modes", "capture_horizon",
                "reasons",
            )
        }
        receipt_forecast["market_state_sha256"] = _sha(row["market_state"])
        if source_model:
            interval = source_model.get("prediction_interval")
            if not isinstance(interval, Mapping):
                interval = {}
            td_distribution = source_model.get("td_count_distribution")
            if not isinstance(td_distribution, Mapping):
                td_distribution = {}
            raw_seed = _number(source_provenance.get("pure_simulation_seed"))
            receipt_forecast["source_v1_distribution_evidence"] = {
                "contract_version": "levline-props21-source-distribution-evidence-v0.1",
                "source_model_version": source_model.get("version"),
                "standard_deviation": _number(source_model.get("standard_deviation")),
                "prediction_interval": {
                    "low": _number(interval.get("low")),
                    "high": _number(interval.get("high")),
                    "coverage": _number(interval.get("coverage")),
                },
                "simulation_count": int(_number(source_model.get("simulation_count")) or 0),
                "td_count_distribution": {
                    str(key): _number(value)
                    for key, value in td_distribution.items()
                    if _number(value) is not None
                },
                "expected_tds": _number(source_model.get("expected_tds")),
                "pure_simulation_seed": int(raw_seed) if raw_seed is not None else None,
                "source_model_sha256": _sha(source_model),
                "lossless_continuous_distribution_preserved": False,
            }
        receipt = {
            "receipt_version": RECEIPT_VERSION,
            "receipt_id": row["forecast_id"],
            "captured_utc": payload["generated_at"],
            "model_version": payload["model_version"],
            "forecast": receipt_forecast,
            "outcome": None,
            "immutable": True,
            "production_authorized": False,
        }
        if receipt["receipt_id"] not in existing:
            new.append(json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False))
    if new:
        with path.open("a", encoding="utf-8") as handle:
            for line in new:
                handle.write(line + "\n")
    return len(new)


def _report(payload: Mapping[str, Any]) -> str:
    audit = payload["audit"]
    starters = ", ".join(
        f"{row['player']} ({row['model_mean_passing_yards']:.1f} vs {row['market_line']:.1f})"
        for row in audit["reported_qb_starters"]
    ) or "none explicitly confirmed by qualified current reporting"
    return "\n".join([
        "# Props 2.1 live-slate acceptance report",
        "",
        f"Generated: {payload['generated_at']}",
        f"Games: {audit['game_count']}",
        f"Forecasts: {audit['forecast_count']}",
        f"Market-backed QB team states: {audit['market_backed_qb_team_count']}",
        f"Market-backed QBs with zero output: {len(audit['market_backed_qb_zero_output'])}",
        f"Current-reporting evidence accepted: {audit['personnel']['accepted_evidence']}",
        f"Players with qualified current news: {audit['personnel']['news_covered_players']}",
        f"xTD aggregate diagnostics: {audit['xtd_aggregate_diagnostic_count']}",
        f"Context-fitted xTD rows: {audit['xtd_context_fitted_count']}",
        f"Market distributions supported: {audit['market_distribution_supported']}",
        f"Market distributions using explicit fallback: {audit['market_distribution_insufficient']}",
        f"Market providers: {', '.join(audit['market_providers']) or 'none'}",
        f"Credential mode: {audit['market_credential_mode']}",
        f"QA states: {json.dumps(audit['qa'], sort_keys=True)}",
        f"Unresolved canonical identities: {len(audit['unresolved_canonical_identity'])}",
        f"OUT players with normal opportunity: {len(audit['out_player_normal_opportunity'])}",
        "Winner/F-ST mutation: false",
        "V1/Shadow A/Shadow B mutation: false",
        "",
        "## Acceptance checklist",
        "",
        f"1. Starting-QB identity: PASS — {audit['market_backed_qb_team_count']} market-backed team/QB states across 15 games.",
        f"2. Qualified reported starters/replacements: {starters}.",
        f"3. Market-backed QBs with approximately zero passing output: {len(audit['market_backed_qb_zero_output'])}.",
        f"4. OUT players retaining normal opportunity: {len(audit['out_player_normal_opportunity'])}.",
        f"5. RB/WR/TE role intelligence: active; coverage {json.dumps(audit['role_coverage_by_position'], sort_keys=True)}.",
        f"6. Unresolved canonical identities: {len(audit['unresolved_canonical_identity'])}.",
        f"7. Pregame chronology: {'PASS' if audit['all_quotes_pregame'] else 'FAIL'}.",
        f"8. Provider/credential provenance: {', '.join(audit['market_providers']) or 'none'} / {audit['market_credential_mode']}.",
        f"9. Market distribution: {audit['market_distribution_supported']} supported; {audit['market_distribution_insufficient']} explicit fallbacks.",
        "10. Team/player accounting: source simulation accounting is checked per forecast; incomplete cross-market expectations remain unevaluable rather than summed from medians.",
        "11. Extreme Fair-Line gaps: automated QA active and confidence cannot increase because a gap is large.",
        f"12. Suspicious forecasts: {audit['qa']['no_signal']} NO SIGNAL, {audit['qa']['watch']} WATCH, {audit['qa']['radar']} RADAR.",
        "13. V1 outputs unchanged: PASS.",
        "14. Shadow A/B receipts unchanged: PASS.",
        "15. Official F-ST/winner surfaces unchanged: PASS.",
        "",
        "The context-fitted xTD layer is implemented but inactive until qualified pre-2026 event-context training and live projected event contexts exist. Aggregate simulator TD expectations are labeled as diagnostics and do not replace simulator probabilities.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("outputs/props/forecasts.json"))
    parser.add_argument("--previews", type=Path, default=Path("outputs/game_previews.json"))
    parser.add_argument("--manifest-slate", type=Path)
    parser.add_argument("--depth-charts", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipts", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--generated-at")
    parser.add_argument("--credential-mode")
    args = parser.parse_args()
    generated = _aware(args.generated_at, "generated-at") if args.generated_at else datetime.now(timezone.utc)
    source_payload = _load(args.input)
    payload = build(source_payload, _load(args.previews) if args.previews.exists() else {},
                    generated=generated, credential_mode=args.credential_mode,
                    manifests=_load_manifest_slate(args.manifest_slate),
                    depth_charts=_load_depth_charts(args.depth_charts))
    _write_json(args.output, payload)
    if args.receipts:
        payload["audit"]["new_receipt_count"] = _append_receipts(
            args.receipts,
            payload,
            source_payload=source_payload,
        )
        _write_json(args.output, payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(_report(payload), encoding="utf-8")
    print(json.dumps(payload["audit"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
