from __future__ import annotations

"""Outcome-free market-microstructure features for LevLine Props 2.0.

Inputs are immutable rows from the prospective market archive. The builder preserves exact
capture times, computes only information available at each capture, and places later-market
movement in explicitly evaluation-only target fields.
"""

from collections import defaultdict
from datetime import datetime, timezone
import math
from statistics import median, pstdev
from typing import Any, Mapping, Sequence

CONTRACT_VERSION = "levline-props-v2-market-microstructure-v0.1.0"


class MarketMicrostructureError(ValueError):
    pass


def _dt(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise MarketMicrostructureError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise MarketMicrostructureError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    values = tuple(str(row.get(key) or "").strip() for key in ("game_id", "player_id", "prop_type"))
    if not all(values):
        raise MarketMicrostructureError("archive row missing game/player/prop identity")
    return values  # type: ignore[return-value]


def _probability(artifact: Mapping[str, Any]) -> float | None:
    for key in ("consensus_no_vig_p_over", "consensus_no_vig_probability"):
        value = _float(artifact.get(key))
        if value is not None and 0.0 < value < 1.0:
            return value
    return None


def _same_threshold_price_dispersion(artifact: Mapping[str, Any]) -> dict[str, Any]:
    consensus = _float(artifact.get("consensus_line"))
    books = artifact.get("individual_books")
    if consensus is None or not isinstance(books, Sequence) or isinstance(books, (str, bytes)):
        return {"n": 0, "stddev": None, "range": None}
    probabilities: list[float] = []
    for row in books:
        if not isinstance(row, Mapping):
            continue
        line = _float(row.get("line"))
        p = _float(row.get("over_no_vig"))
        if line is None or p is None:
            continue
        if math.isclose(line, consensus, abs_tol=1e-9) and 0.0 < p < 1.0:
            probabilities.append(p)
    if not probabilities:
        return {"n": 0, "stddev": None, "range": None}
    return {
        "n": len(probabilities),
        "stddev": float(pstdev(probabilities)) if len(probabilities) >= 2 else 0.0,
        "range": float(max(probabilities) - min(probabilities)),
    }


def _quote_age(artifact: Mapping[str, Any], captured: datetime) -> dict[str, Any]:
    books = artifact.get("individual_books")
    ages: list[float] = []
    if isinstance(books, Sequence) and not isinstance(books, (str, bytes)):
        for row in books:
            if not isinstance(row, Mapping):
                continue
            raw = row.get("sportsbook_last_update_utc")
            if raw in (None, ""):
                continue
            updated = _dt(raw)
            if updated > captured:
                raise MarketMicrostructureError("sportsbook update is after snapshot capture")
            ages.append((captured - updated).total_seconds() / 60.0)
    return {
        "n_with_update_timestamp": len(ages),
        "median_minutes": float(median(ages)) if ages else None,
        "max_minutes": float(max(ages)) if ages else None,
    }


def _book_state(artifact: Mapping[str, Any]) -> dict[str, tuple[float | None, float | None]]:
    books = artifact.get("individual_books")
    out: dict[str, tuple[float | None, float | None]] = {}
    if not isinstance(books, Sequence) or isinstance(books, (str, bytes)):
        return out
    for row in books:
        if not isinstance(row, Mapping):
            continue
        key = str(row.get("sportsbook_key") or "").strip()
        if not key:
            continue
        out[key] = (_float(row.get("line")), _float(row.get("over_no_vig") or row.get("yes_no_vig")))
    return out


def _changed_books(
    previous: Mapping[str, tuple[float | None, float | None]],
    current: Mapping[str, tuple[float | None, float | None]],
) -> dict[str, list[str]]:
    line_changed: list[str] = []
    price_changed: list[str] = []
    for book in sorted(set(previous).intersection(current)):
        prev_line, prev_prob = previous[book]
        cur_line, cur_prob = current[book]
        if prev_line is not None and cur_line is not None and not math.isclose(prev_line, cur_line, abs_tol=1e-12):
            line_changed.append(book)
        if prev_prob is not None and cur_prob is not None and not math.isclose(prev_prob, cur_prob, abs_tol=1e-12):
            price_changed.append(book)
    return {"line": line_changed, "price": price_changed}


def _movement(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else float(b - a)


def build_microstructure_rows(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Create point-in-time features plus separately flagged later-market targets."""
    groups: dict[tuple[str, str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in records:
        if row.get("research_only") is not True or row.get("production_authorized") is not False:
            raise MarketMicrostructureError("archive row violates research-only governance")
        groups[_identity(row)].append(row)

    output: list[dict[str, Any]] = []
    for identity, rows in sorted(groups.items()):
        ordered = sorted(rows, key=lambda row: _dt(row.get("captured_at_utc")))
        normalized: list[dict[str, Any]] = []
        for row in ordered:
            artifact = row.get("market_artifact")
            if not isinstance(artifact, Mapping):
                raise MarketMicrostructureError("archive row missing market_artifact")
            captured = _dt(row.get("captured_at_utc"))
            kickoff = _dt(row.get("kickoff_utc"))
            if captured >= kickoff:
                raise MarketMicrostructureError("post-kickoff row entered market history")
            if str(artifact.get("game_id") or "") != identity[0]:
                raise MarketMicrostructureError("artifact identity disagrees with archive row")
            normalized.append(
                {
                    "source": row,
                    "artifact": artifact,
                    "captured": captured,
                    "kickoff": kickoff,
                    "line": _float(artifact.get("consensus_line")),
                    "probability": _probability(artifact),
                    "line_stddev": _float(artifact.get("line_stddev")),
                    "line_range": _float(artifact.get("line_range")),
                    "book_state": _book_state(artifact),
                }
            )

        final = normalized[-1]
        for idx, cur in enumerate(normalized):
            prev = normalized[idx - 1] if idx else None
            elapsed_hours = (
                (cur["captured"] - prev["captured"]).total_seconds() / 3600.0
                if prev is not None
                else None
            )
            line_delta = _movement(prev["line"], cur["line"]) if prev else None
            prob_delta = _movement(prev["probability"], cur["probability"]) if prev else None
            dispersion_delta = (
                _movement(prev["line_stddev"], cur["line_stddev"]) if prev else None
            )
            changes = (
                _changed_books(prev["book_state"], cur["book_state"])
                if prev is not None
                else {"line": [], "price": []}
            )
            price_dispersion = _same_threshold_price_dispersion(cur["artifact"])
            age = _quote_age(cur["artifact"], cur["captured"])
            line_velocity = (
                line_delta / elapsed_hours
                if line_delta is not None and elapsed_hours and elapsed_hours > 0
                else None
            )
            probability_velocity = (
                prob_delta / elapsed_hours
                if prob_delta is not None and elapsed_hours and elapsed_hours > 0
                else None
            )
            convergence_velocity = (
                -dispersion_delta / elapsed_hours
                if dispersion_delta is not None and elapsed_hours and elapsed_hours > 0
                else None
            )

            output.append(
                {
                    "contract_version": CONTRACT_VERSION,
                    "snapshot_id": cur["source"].get("snapshot_id"),
                    "captured_at_utc": cur["captured"].isoformat(),
                    "kickoff_utc": cur["kickoff"].isoformat(),
                    "minutes_to_kickoff": (cur["kickoff"] - cur["captured"]).total_seconds() / 60.0,
                    "game_id": identity[0],
                    "player_id": identity[1],
                    "prop_type": identity[2],
                    "consensus_line": cur["line"],
                    "consensus_probability": cur["probability"],
                    "sportsbook_count": int(cur["artifact"].get("sportsbook_count") or 0),
                    "line_stddev": cur["line_stddev"],
                    "line_range": cur["line_range"],
                    "same_threshold_price_book_count": price_dispersion["n"],
                    "same_threshold_price_stddev": price_dispersion["stddev"],
                    "same_threshold_price_range": price_dispersion["range"],
                    "quote_age_book_count": age["n_with_update_timestamp"],
                    "median_quote_age_minutes": age["median_minutes"],
                    "max_quote_age_minutes": age["max_minutes"],
                    "hours_since_previous_capture": elapsed_hours,
                    "line_move_since_previous": line_delta,
                    "probability_move_since_previous": prob_delta,
                    "line_velocity_per_hour": line_velocity,
                    "probability_velocity_per_hour": probability_velocity,
                    "line_dispersion_change_since_previous": dispersion_delta,
                    "convergence_velocity_per_hour": convergence_velocity,
                    "books_line_changed_since_previous": changes["line"],
                    "books_price_changed_since_previous": changes["price"],
                    "evaluation_only_targets": {
                        "target_is_future_market_not_game_outcome": True,
                        "final_observed_capture_utc": final["captured"].isoformat(),
                        "minutes_from_capture_to_final_observed": (
                            final["captured"] - cur["captured"]
                        ).total_seconds() / 60.0,
                        "line_move_to_final_observed": _movement(cur["line"], final["line"]),
                        "probability_move_to_final_observed": _movement(
                            cur["probability"], final["probability"]
                        ),
                    },
                    "research_only": True,
                    "production_authorized": False,
                    "game_outcome_used": False,
                }
            )
    return output
