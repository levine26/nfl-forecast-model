from __future__ import annotations

"""Derive strict point-in-time market-state features from the v2 research capture ledger.

The derivative is descriptive research/UX state only. It never changes the frozen
production forecast. Missing horizons remain missing; retries are resolved only by the
closest qualifying consensus request at or before the preregistered target timestamp.
Book-level movement features are paired only across the exact sportsbook snapshots that
belong to those selected consensus requests, so retry mixing cannot manufacture breadth.
"""

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from research.market_capture_v2 import CAPTURE_TOLERANCE_MINUTES, HORIZONS, logit
from research.market_capture_contract_v2 import MIN_CONSENSUS_BOOKS

HORIZON_ORDER = ("T-120m", "T-60m", "T-45m", "T-30m")
PAIR_DEFINITIONS = (
    ("t60_minus_t120", "T-60m", "T-120m"),
    ("t45_minus_t120", "T-45m", "T-120m"),
    ("t30_minus_t120", "T-30m", "T-120m"),
    ("t45_minus_t60", "T-45m", "T-60m"),
    ("t30_minus_t60", "T-30m", "T-60m"),
    ("t30_minus_t45", "T-30m", "T-45m"),
)
IDENTITY_FIELDS = (
    "event_id",
    "provider_commence_time_utc",
    "home_team",
    "away_team",
    "kickoff_timestamp_utc",
)


def _float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _int(value: Any) -> int | None:
    parsed = _float(value)
    if parsed is None or not parsed.is_integer():
        return None
    return int(parsed)


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


def _strict_pit_row(row: dict[str, Any]) -> bool:
    if str(row.get("horizon")) not in HORIZONS:
        return False
    probability = _float(row.get("h2h_home_no_vig"))
    if probability is None or not 0.0 < probability < 1.0:
        return False
    timing_error = _float(row.get("timing_error_minutes"))
    if timing_error is None or timing_error < -CAPTURE_TOLERANCE_MINUTES or timing_error > 0.0:
        return False
    if not _truthy(row.get("research_only")) or _truthy(row.get("production_authorized")):
        return False
    target = _parse_utc(row.get("target_timestamp_utc"))
    request = _parse_utc(row.get("request_timestamp_utc"))
    kickoff = _parse_utc(row.get("kickoff_timestamp_utc"))
    if target is None or request is None or kickoff is None:
        return False
    if request > target or request >= kickoff:
        return False
    return True


def _qualifying_consensus(row: dict[str, Any]) -> bool:
    if str(row.get("row_type")) != "consensus" or not _strict_pit_row(row):
        return False
    source_count = _int(row.get("source_count"))
    return source_count is not None and source_count >= MIN_CONSENSUS_BOOKS


def _qualifying_book(row: dict[str, Any]) -> bool:
    if str(row.get("row_type")) != "book" or not _strict_pit_row(row):
        return False
    return bool(str(row.get("sportsbook_key") or "").strip())


def _choose_horizon(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot select from empty horizon rows")
    identities = {tuple(str(row.get(field) or "") for field in IDENTITY_FIELDS) for row in rows}
    if len(identities) != 1:
        raise ValueError("market consensus retries disagree on event identity")
    return sorted(
        rows,
        key=lambda row: (
            abs(float(row["timing_error_minutes"])),
            _parse_utc(row.get("request_timestamp_utc")) or datetime.max.replace(tzinfo=timezone.utc),
        ),
    )[0]


def select_consensus_horizons(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in rows:
        if not _qualifying_consensus(row):
            continue
        game_id = str(row.get("game_id") or "").strip()
        horizon = str(row.get("horizon") or "")
        if not game_id:
            continue
        grouped.setdefault(game_id, {}).setdefault(horizon, []).append(dict(row))

    selected: dict[str, dict[str, dict[str, Any]]] = {}
    for game_id, horizons in grouped.items():
        selected[game_id] = {
            horizon: _choose_horizon(candidates)
            for horizon, candidates in horizons.items()
        }
    return selected


def select_book_horizons(
    rows: Iterable[dict[str, Any]],
    selected_consensus: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, dict[str, dict[str, Any]]]]:
    """Select books from the exact requests chosen for each qualifying consensus horizon."""
    selected: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for original in rows:
        row = dict(original)
        if not _qualifying_book(row):
            continue
        game_id = str(row.get("game_id") or "").strip()
        horizon = str(row.get("horizon") or "")
        consensus = selected_consensus.get(game_id, {}).get(horizon)
        if consensus is None:
            continue
        if _parse_utc(row.get("request_timestamp_utc")) != _parse_utc(consensus.get("request_timestamp_utc")):
            continue
        if any(str(row.get(field) or "") != str(consensus.get(field) or "") for field in IDENTITY_FIELDS):
            raise ValueError(f"book/consensus identity mismatch for {game_id} {horizon}")
        book_key = str(row.get("sportsbook_key") or "").strip()
        horizon_books = selected.setdefault(game_id, {}).setdefault(horizon, {})
        prior = horizon_books.get(book_key)
        if prior is not None:
            prior_prob = _float(prior.get("h2h_home_no_vig"))
            current_prob = _float(row.get("h2h_home_no_vig"))
            if prior_prob != current_prob:
                raise ValueError(f"duplicate sportsbook conflict for {game_id} {horizon} {book_key}")
            continue
        horizon_books[book_key] = row
    return selected


def _difference(
    rows: dict[str, dict[str, Any]],
    newer: str,
    older: str,
    field: str,
) -> float | None:
    if newer not in rows or older not in rows:
        return None
    left = _float(rows[newer].get(field))
    right = _float(rows[older].get(field))
    if left is None or right is None:
        return None
    return left - right


def _logit_difference(
    rows: dict[str, dict[str, Any]],
    newer: str,
    older: str,
) -> float | None:
    if newer not in rows or older not in rows:
        return None
    left = _float(rows[newer].get("h2h_home_no_vig"))
    right = _float(rows[older].get("h2h_home_no_vig"))
    if left is None or right is None or not (0 < left < 1 and 0 < right < 1):
        return None
    return logit(left) - logit(right)


def _book_pair_features(
    books: dict[str, dict[str, dict[str, Any]]],
    newer: str,
    older: str,
) -> dict[str, float | int | None]:
    newer_books = books.get(newer, {})
    older_books = books.get(older, {})
    common = sorted(set(newer_books) & set(older_books))
    union = set(newer_books) | set(older_books)
    if not common:
        return {
            "common_count": 0,
            "overlap_fraction": 0.0 if union else None,
            "home_move_share": None,
            "away_move_share": None,
            "unchanged_share": None,
            "movement_breadth": None,
            "median_probability_change_pp": None,
            "median_logit_change": None,
        }

    probability_changes: list[float] = []
    logit_changes: list[float] = []
    home_moves = 0
    away_moves = 0
    unchanged = 0
    for book in common:
        newer_prob = _float(newer_books[book].get("h2h_home_no_vig"))
        older_prob = _float(older_books[book].get("h2h_home_no_vig"))
        if newer_prob is None or older_prob is None:
            continue
        change = newer_prob - older_prob
        probability_changes.append(change)
        logit_changes.append(logit(newer_prob) - logit(older_prob))
        if change > 0:
            home_moves += 1
        elif change < 0:
            away_moves += 1
        else:
            unchanged += 1

    paired = len(probability_changes)
    if paired == 0:
        return {
            "common_count": 0,
            "overlap_fraction": 0.0 if union else None,
            "home_move_share": None,
            "away_move_share": None,
            "unchanged_share": None,
            "movement_breadth": None,
            "median_probability_change_pp": None,
            "median_logit_change": None,
        }
    return {
        "common_count": paired,
        "overlap_fraction": paired / len(union) if union else None,
        "home_move_share": home_moves / paired,
        "away_move_share": away_moves / paired,
        "unchanged_share": unchanged / paired,
        "movement_breadth": (home_moves - away_moves) / paired,
        "median_probability_change_pp": median(probability_changes) * 100.0,
        "median_logit_change": median(logit_changes),
    }


def _assert_cross_horizon_identity(game_id: str, rows: dict[str, dict[str, Any]]) -> None:
    identities = {
        tuple(str(row.get(field) or "") for field in IDENTITY_FIELDS)
        for row in rows.values()
    }
    if len(identities) > 1:
        raise ValueError(f"market horizons disagree on event identity for {game_id}")


def build_market_state(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    materialized = [dict(row) for row in rows]
    selected = select_consensus_horizons(materialized)
    selected_books = select_book_horizons(materialized, selected)
    output: list[dict[str, Any]] = []
    complete_games = 0
    for game_id in sorted(selected):
        horizons = selected[game_id]
        books = selected_books.get(game_id, {})
        _assert_cross_horizon_identity(game_id, horizons)
        available = [horizon for horizon in HORIZON_ORDER if horizon in horizons]
        missing = [horizon for horizon in HORIZON_ORDER if horizon not in horizons]
        if not missing:
            complete_games += 1
        template = horizons[available[0]]
        record: dict[str, Any] = {
            "game_id": game_id,
            "event_id": template.get("event_id"),
            "provider_commence_time_utc": template.get("provider_commence_time_utc"),
            "home_team": template.get("home_team"),
            "away_team": template.get("away_team"),
            "kickoff_timestamp_utc": template.get("kickoff_timestamp_utc"),
            "available_horizons": available,
            "missing_horizons": missing,
            "complete_horizons": not missing,
            "strict_no_later_than_cutoff": True,
            "research_only": True,
            "production_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        for horizon in HORIZON_ORDER:
            suffix = horizon.lower().replace("-", "").replace("m", "")
            row = horizons.get(horizon)
            record[f"market_home_prob_{suffix}"] = _float(row.get("h2h_home_no_vig")) if row else None
            record[f"home_spread_{suffix}"] = _float(row.get("home_spread")) if row else None
            record[f"total_points_{suffix}"] = _float(row.get("total_points")) if row else None
            record[f"probability_range_{suffix}"] = _float(row.get("probability_range")) if row else None
            record[f"source_count_{suffix}"] = _int(row.get("source_count")) if row else None
            record[f"max_freshness_minutes_{suffix}"] = _float(row.get("max_freshness_minutes")) if row else None
            record[f"request_timestamp_utc_{suffix}"] = row.get("request_timestamp_utc") if row else None
            record[f"timing_error_minutes_{suffix}"] = _float(row.get("timing_error_minutes")) if row else None

        for label, newer, older in PAIR_DEFINITIONS:
            prob = _difference(horizons, newer, older, "h2h_home_no_vig")
            record[f"home_probability_{label}"] = prob
            record[f"home_probability_pp_{label}"] = prob * 100.0 if prob is not None else None
            record[f"home_logit_{label}"] = _logit_difference(horizons, newer, older)
            record[f"home_spread_{label}"] = _difference(horizons, newer, older, "home_spread")
            record[f"total_points_{label}"] = _difference(horizons, newer, older, "total_points")
            record[f"probability_range_{label}"] = _difference(horizons, newer, older, "probability_range")
            micro = _book_pair_features(books, newer, older)
            for key, value in micro.items():
                record[f"book_{key}_{label}"] = value
        output.append(record)

    audit = {
        "schema_version": "levline-market-state-v1",
        "games_with_any_qualifying_horizon": len(output),
        "games_with_all_four_horizons": complete_games,
        "games_with_missing_horizons": len(output) - complete_games,
        "minimum_consensus_books": MIN_CONSENSUS_BOOKS,
        "capture_tolerance_minutes": CAPTURE_TOLERANCE_MINUTES,
        "valid_timing_error_minutes": [-CAPTURE_TOLERANCE_MINUTES, 0.0],
        "strict_no_later_than_cutoff": True,
        "horizons": list(HORIZON_ORDER),
        "book_microstructure_features": True,
        "book_pairing_policy": "same_sportsbook_exact_selected_consensus_request_only",
        "missingness_policy": "preserve_missing_no_imputation",
        "research_only": True,
        "production_authorized": False,
        "completed_2026_outcomes_used": 0,
    }
    return output, audit


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
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            serial = dict(row)
            serial["available_horizons"] = "|".join(row["available_horizons"])
            serial["missing_horizons"] = "|".join(row["missing_horizons"])
            writer.writerow(serial)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    states, audit = build_market_state(_read_csv(args.ledger))
    _write_csv(args.output, states)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
