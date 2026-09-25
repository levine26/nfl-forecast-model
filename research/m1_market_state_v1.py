from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median, pstdev
from typing import Any, Iterable

from research.m1_market_contract_v1 import (
    CAPTURE_TOLERANCE_MINUTES,
    COMPLETE_BOOK_FIELDS,
    DIAGNOSTIC_HORIZONS,
    FORBIDDEN_OUTCOME_FIELDS,
    KEY_NUMBERS,
    LATEST_PREKICK,
    LATEST_PREKICK_SAFETY_MINUTES,
    LATEST_PREKICK_WINDOW_MINUTES,
    MAX_EVENT_KICKOFF_DELTA_MINUTES,
    MIN_COMPLETE_BOOKS,
    PREDICTOR_FEATURE_COLUMNS,
    PREDICTOR_HORIZONS,
    PROGRAM_ID,
    SCHEMA_VERSION,
    STALE_QUOTE_MINUTES,
)
from research.market_capture_v2 import logit, median_logit

IDENTITY_FIELDS = (
    "event_id",
    "home_team",
    "away_team",
    "kickoff_timestamp_utc",
)


def _float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _parse_utc(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _has_outcome_data(row: dict[str, Any]) -> bool:
    for field in FORBIDDEN_OUTCOME_FIELDS:
        value = row.get(field)
        if value is not None and str(value).strip() not in {"", "nan", "None"}:
            return True
    return False


def _strict_book(row: dict[str, Any]) -> bool:
    if str(row.get("row_type")) != "book":
        return False
    if _has_outcome_data(row):
        return False
    if not _truthy(row.get("research_only")) or _truthy(row.get("production_authorized")):
        return False
    if not str(row.get("sportsbook_key") or "").strip():
        return False

    horizon = str(row.get("horizon") or "")
    request = _parse_utc(row.get("request_timestamp_utc"))
    kickoff = _parse_utc(row.get("kickoff_timestamp_utc"))
    if request is None or kickoff is None or request >= kickoff:
        return False

    provider_delta = _float(row.get("provider_kickoff_delta_minutes"))
    if provider_delta is not None and abs(provider_delta) > MAX_EVENT_KICKOFF_DELTA_MINUTES:
        return False

    if horizon == LATEST_PREKICK:
        minutes_to_kick = (kickoff - request).total_seconds() / 60.0
        return LATEST_PREKICK_SAFETY_MINUTES <= minutes_to_kick <= LATEST_PREKICK_WINDOW_MINUTES

    if horizon not in PREDICTOR_HORIZONS and horizon not in DIAGNOSTIC_HORIZONS:
        return False
    target = _parse_utc(row.get("target_timestamp_utc"))
    timing_error = _float(row.get("timing_error_minutes"))
    if target is None or timing_error is None:
        return False
    if request > target:
        return False
    return -CAPTURE_TOLERANCE_MINUTES <= timing_error <= 0.0


def _complete_book(row: dict[str, Any]) -> bool:
    return _strict_book(row) and all(_float(row.get(field)) is not None for field in COMPLETE_BOOK_FIELDS)


def _request_groups(rows: Iterable[dict[str, Any]], game_id: str, horizon: str) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for original in rows:
        row = dict(original)
        if str(row.get("game_id") or "") != game_id or str(row.get("horizon") or "") != horizon:
            continue
        if not _strict_book(row):
            continue
        request = _parse_utc(row.get("request_timestamp_utc"))
        if request is None:
            continue
        groups.setdefault(request.isoformat(), []).append(row)
    return list(groups.values())


def _group_complete_books(group: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    books: dict[str, dict[str, Any]] = {}
    for row in group:
        if not _complete_book(row):
            continue
        key = str(row.get("sportsbook_key") or "").strip()
        if key in books:
            prior = books[key]
            if any(prior.get(field) != row.get(field) for field in COMPLETE_BOOK_FIELDS):
                raise ValueError(f"conflicting duplicate sportsbook row: {key}")
            continue
        books[key] = row
    return books


def _identity(group: list[dict[str, Any]]) -> tuple[str, ...] | None:
    identities = {tuple(str(row.get(field) or "") for field in IDENTITY_FIELDS) for row in group}
    if len(identities) != 1:
        return None
    identity = next(iter(identities))
    return identity if identity[0] else None


def _choose_fixed_request(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]] | None:
    qualified: list[tuple[float, datetime, list[dict[str, Any]]]] = []
    for group in groups:
        if _identity(group) is None or len(_group_complete_books(group)) < MIN_COMPLETE_BOOKS:
            continue
        row = group[0]
        timing = _float(row.get("timing_error_minutes"))
        request = _parse_utc(row.get("request_timestamp_utc"))
        if timing is None or request is None:
            continue
        qualified.append((abs(timing), request, group))
    if not qualified:
        return None
    qualified.sort(key=lambda item: (item[0], item[1]))
    return qualified[0][2]


def _choose_latest_request(groups: list[list[dict[str, Any]]]) -> list[dict[str, Any]] | None:
    qualified: list[tuple[datetime, list[dict[str, Any]]]] = []
    for group in groups:
        if _identity(group) is None or len(_group_complete_books(group)) < MIN_COMPLETE_BOOKS:
            continue
        request = _parse_utc(group[0].get("request_timestamp_utc"))
        if request is not None:
            qualified.append((request, group))
    if not qualified:
        return None
    qualified.sort(key=lambda item: item[0], reverse=True)
    return qualified[0][1]


def select_game_state(rows: Iterable[dict[str, Any]], game_id: str) -> dict[str, list[dict[str, Any]]]:
    materialized = [dict(row) for row in rows]
    selected: dict[str, list[dict[str, Any]]] = {}
    for horizon in (*PREDICTOR_HORIZONS.keys(), *DIAGNOSTIC_HORIZONS.keys()):
        chosen = _choose_fixed_request(_request_groups(materialized, game_id, horizon))
        if chosen is not None:
            selected[horizon] = chosen
    latest = _choose_latest_request(_request_groups(materialized, game_id, LATEST_PREKICK))
    if latest is not None:
        selected[LATEST_PREKICK] = latest

    identities = {_identity(group) for group in selected.values() if _identity(group) is not None}
    if len(identities) > 1:
        raise ValueError(f"cross-horizon event/kickoff identity mismatch for {game_id}")
    return selected


def _favorite_is_home(home_spread: float, home_ml_prob: float) -> bool:
    if home_spread < 0:
        return True
    if home_spread > 0:
        return False
    return home_ml_prob >= 0.5


def _oriented(probability: float, favorite_is_home: bool) -> float:
    return probability if favorite_is_home else 1.0 - probability


def _consensus(group: list[dict[str, Any]]) -> dict[str, Any]:
    books = _group_complete_books(group)
    if len(books) < MIN_COMPLETE_BOOKS:
        raise ValueError("insufficient complete books")
    rows = list(books.values())
    home_spreads = [float(row["home_spread"]) for row in rows]
    home_spread_probs = [float(row["spread_home_cover_no_vig"]) for row in rows]
    home_ml_probs = [float(row["h2h_home_no_vig"]) for row in rows]
    totals = [float(row["total_points"]) for row in rows]
    freshness = [float(row["freshness_minutes"]) for row in rows]
    return {
        "books": books,
        "home_spread": median(home_spreads),
        "home_spread_no_vig": median_logit(home_spread_probs),
        "home_ml_no_vig": median_logit(home_ml_probs),
        "total": median(totals),
        "spread_dispersion": pstdev(home_spreads),
        "active_book_count": len(rows),
        "median_quote_age": median(freshness),
        "stale_share": sum(age >= STALE_QUOTE_MINUTES for age in freshness) / len(freshness),
    }


def _key_crossing(first_strength: float, second_strength: float) -> int:
    low, high = sorted((abs(first_strength), abs(second_strength)))
    return int(any(low <= key <= high and not math.isclose(low, high) for key in KEY_NUMBERS))


def _path_features(t360: dict[str, Any], t120: dict[str, Any], favorite_is_home: bool) -> dict[str, Any]:
    books360 = t360["books"]
    books120 = t120["books"]
    common = sorted(set(books360) & set(books120))
    if len(common) < MIN_COMPLETE_BOOKS:
        raise ValueError("insufficient common complete books for T-360 to T-120 path")

    strength360 = -t360["home_spread"] if favorite_is_home else t360["home_spread"]
    strength120 = -t120["home_spread"] if favorite_is_home else t120["home_spread"]

    unchanged_price_moves: list[float] = []
    direction_scores: list[int] = []
    for key in common:
        old = books360[key]
        new = books120[key]
        old_spread = float(old["home_spread"])
        new_spread = float(new["home_spread"])
        old_strength = -old_spread if favorite_is_home else old_spread
        new_strength = -new_spread if favorite_is_home else new_spread
        number_delta = new_strength - old_strength

        old_price = _oriented(float(old["spread_home_cover_no_vig"]), favorite_is_home)
        new_price = _oriented(float(new["spread_home_cover_no_vig"]), favorite_is_home)
        price_delta = new_price - old_price
        if math.isclose(old_spread, new_spread, abs_tol=1e-9):
            unchanged_price_moves.append(price_delta)

        movement = number_delta if not math.isclose(number_delta, 0.0, abs_tol=1e-9) else price_delta
        direction_scores.append(1 if movement > 0 else -1 if movement < 0 else 0)

    conditional_price_move = median(unchanged_price_moves) if unchanged_price_moves else 0.0
    return {
        "favorite_spread_strength_move_t360_to_t120": strength120 - strength360,
        "spread_price_move_unchanged_number_t360_to_t120": conditional_price_move,
        "movement_breadth_t360_to_t120": sum(direction_scores) / len(direction_scores),
        "key_number_crossing_3_or_7_t360_to_t120": _key_crossing(strength360, strength120),
        "path_common_book_count": len(common),
        "unchanged_number_common_book_count": len(unchanged_price_moves),
    }


def build_predictor_row(rows: Iterable[dict[str, Any]], game_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    state = select_game_state(materialized, game_id)
    missing_required = [h for h in ("T-360m", "T-120m") if h not in state]
    audit: dict[str, Any] = {
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "available_predictor_horizons": [h for h in PREDICTOR_HORIZONS if h in state],
        "available_diagnostic_horizons": [h for h in (*DIAGNOSTIC_HORIZONS.keys(), LATEST_PREKICK) if h in state],
        "completed_2026_outcomes_used": 0,
        "production_authorized": False,
        "diagnostic_fields_admitted_to_predictor": False,
        "minimum_complete_books": MIN_COMPLETE_BOOKS,
        "stale_quote_minutes": STALE_QUOTE_MINUTES,
    }
    if missing_required:
        audit.update({"eligible": False, "reason": "missing_required_predictor_horizon", "missing": missing_required})
        return None, audit

    t360 = _consensus(state["T-360m"])
    t120 = _consensus(state["T-120m"])
    favorite_is_home = _favorite_is_home(t120["home_spread"], t120["home_ml_no_vig"])
    spread_favorite = _oriented(t120["home_spread_no_vig"], favorite_is_home)
    ml_favorite = _oriented(t120["home_ml_no_vig"], favorite_is_home)
    path = _path_features(t360, t120, favorite_is_home)

    template = state["T-120m"][0]
    row: dict[str, Any] = {
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "event_id": template.get("event_id"),
        "home_team": template.get("home_team"),
        "away_team": template.get("away_team"),
        "kickoff_timestamp_utc": template.get("kickoff_timestamp_utc"),
        "decision_horizon": "T-120m",
        "favorite_side": "home" if favorite_is_home else "away",
        "consensus_spread_t120": t120["home_spread"],
        "spread_favorite_no_vig_t120": spread_favorite,
        "moneyline_favorite_no_vig_t120": ml_favorite,
        "consensus_total_t120": t120["total"],
        "spread_dispersion_t120": t120["spread_dispersion"],
        "active_book_count_t120": t120["active_book_count"],
        "median_quote_age_minutes_t120": t120["median_quote_age"],
        "stale_book_share_t120": t120["stale_share"],
        "favorite_spread_strength_move_t360_to_t120": path["favorite_spread_strength_move_t360_to_t120"],
        "spread_price_move_unchanged_number_t360_to_t120": path["spread_price_move_unchanged_number_t360_to_t120"],
        "movement_breadth_t360_to_t120": path["movement_breadth_t360_to_t120"],
        "key_number_crossing_3_or_7_t360_to_t120": path["key_number_crossing_3_or_7_t360_to_t120"],
        "spread_moneyline_logit_residual_t120": logit(spread_favorite) - logit(ml_favorite),
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    missing_features = [name for name in PREDICTOR_FEATURE_COLUMNS if row.get(name) is None]
    if missing_features:
        audit.update({"eligible": False, "reason": "missing_frozen_feature", "missing": missing_features})
        return None, audit

    audit.update(
        {
            "eligible": True,
            "reason": "qualified",
            "path_common_book_count": path["path_common_book_count"],
            "unchanged_number_common_book_count": path["unchanged_number_common_book_count"],
            "predictor_feature_columns": list(PREDICTOR_FEATURE_COLUMNS),
        }
    )
    return row, audit


def build_diagnostic_row(rows: Iterable[dict[str, Any]], game_id: str) -> dict[str, Any]:
    materialized = [dict(row) for row in rows]
    state = select_game_state(materialized, game_id)
    output: dict[str, Any] = {
        "program_id": PROGRAM_ID,
        "schema_version": f"{SCHEMA_VERSION}-diagnostic",
        "game_id": game_id,
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    for horizon, prefix in (("T-60m", "t60"), ("T-30m", "t30"), (LATEST_PREKICK, "latest_prekick")):
        group = state.get(horizon)
        if group is None:
            output[f"{prefix}_consensus_spread"] = None
            output[f"{prefix}_spread_home_no_vig"] = None
            output[f"{prefix}_moneyline_home_no_vig"] = None
            continue
        consensus = _consensus(group)
        output[f"{prefix}_consensus_spread"] = consensus["home_spread"]
        output[f"{prefix}_spread_home_no_vig"] = consensus["home_spread_no_vig"]
        output[f"{prefix}_moneyline_home_no_vig"] = consensus["home_ml_no_vig"]
    return output


def build_all(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    game_ids = sorted({str(row.get("game_id") or "") for row in materialized if str(row.get("game_id") or "")})
    predictors: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    for game_id in game_ids:
        predictor, audit = build_predictor_row(materialized, game_id)
        audits.append(audit)
        if predictor is not None:
            predictors.append(predictor)
        diagnostics.append(build_diagnostic_row(materialized, game_id))
    summary = {
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "games_seen": len(game_ids),
        "eligible_predictor_rows": len(predictors),
        "ineligible_predictor_rows": len(game_ids) - len(predictors),
        "completed_2026_outcomes_used": 0,
        "production_authorized": False,
        "diagnostic_fields_admitted_to_predictor": False,
        "game_audits": audits,
    }
    return predictors, diagnostics, summary


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default="research_outputs/m1_market_state_v1/market_snapshots.csv")
    parser.add_argument("--predictors", default="research_outputs/m1_market_state_v1/predictor_rows.csv")
    parser.add_argument("--diagnostics", default="research_outputs/m1_market_state_v1/diagnostic_rows.csv")
    parser.add_argument("--audit", default="research_outputs/m1_market_state_v1/audit.json")
    args = parser.parse_args()

    predictors, diagnostics, audit = build_all(_read_csv(Path(args.ledger)))
    _write_csv(Path(args.predictors), predictors)
    _write_csv(Path(args.diagnostics), diagnostics)
    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
