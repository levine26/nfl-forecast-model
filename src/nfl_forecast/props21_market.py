"""Read-only market reconstruction for the separate Props 2.1 challenger.

No outcomes, book-reliability fit, football inputs, or frozen evidence mutations.
Only paired prices identify no-vig probabilities. Integer push prices identify
conditional probabilities and do not identify unconditional survival points.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import fields
import math
from statistics import median, pstdev
from typing import Mapping, Sequence

from .props_market import (
    PropMarketQuote, _pava_nonincreasing, median_logit, movement_summary,
    parse_utc, remove_vig_two_way,
)

VERSION = "levline-props-2.1-market-v0.1"
SUPPORTED = "MARKET_DISTRIBUTION_SUPPORTED"
INSUFFICIENT = "MARKET_DISTRIBUTION_INSUFFICIENT"


def _number(value: object) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def probability_at(points: Sequence[Mapping], threshold: float, *, interpolate: bool = True) -> float | None:
    """Integer-valued NFL outcomes: P(Y>x) = P(Y>floor(x)+0.5).

    Interpolation describes interior unobserved half-point thresholds only; it
    does not imply observations at those thresholds or extrapolate tails.
    """
    value = _number(threshold)
    if value is None:
        return None
    x = math.floor(value) + 0.5
    ordered = sorted(points, key=lambda row: row["line"])
    for row in ordered:
        if x == row["line"]:
            return float(row["monotone_p_over"])
    if interpolate:
        for left, right in zip(ordered, ordered[1:]):
            if left["line"] < x < right["line"]:
                weight = (x - left["line"]) / (right["line"] - left["line"])
                return left["monotone_p_over"] + weight * (right["monotone_p_over"] - left["monotone_p_over"])
    return None


def _quantile_bracket(points: Sequence[Mapping], quantile: float) -> list[float] | None:
    """Return evidence-bracketed integer quantile bounds; never invent tails."""
    target = 1.0 - quantile
    # F(k) = 1-S(k+0.5); bounds are actual stat values, not betting lines.
    lower = [math.floor(p["line"]) + 1 for p in points if p["monotone_p_over"] > target]
    upper = [math.floor(p["line"]) for p in points if p["monotone_p_over"] <= target]
    if not lower or not upper:
        return None
    lo, hi = max(lower), min(upper)
    return [lo, hi] if lo <= hi else None


def build_market_state(
    quotes: Sequence[PropMarketQuote | Mapping], *, as_of_utc: object,
    kickoff_utc: object | None = None, fair_line: float | None = None,
    sportsbook_line: float | None = None, credential_mode: str | None = None,
    max_quote_age_minutes: float = 120.0, capture_horizon: str | None = None,
    book_aliases: Mapping[str, str] | None = None,
) -> dict:
    """Build a JSON-safe, pregame-only snapshot for exactly one canonical market.

    Three distinct no-push thresholds and two independent book IDs are the
    minimum *structural* curve gate, not an empirical confidence criterion.
    Binary yes/no markets have known finite support and need two paired books.
    Passing record dictionaries preserves their provider/credential metadata.
    """
    as_of = parse_utc(as_of_utc)
    age_limit = _number(max_quote_age_minutes)
    if age_limit is None or age_limit <= 0:
        raise ValueError("max_quote_age_minutes must be positive and finite")
    explicit_kickoff = parse_utc(kickoff_utc) if kickoff_utc is not None else None
    aliases = {str(k).strip().casefold(): str(v).strip().casefold() for k, v in (book_aliases or {}).items()}
    names = {f.name for f in fields(PropMarketQuote)}
    rejected: Counter = Counter()
    parsed = []
    identities = set()
    stale_books = set()
    for raw in quotes:
        record = raw.to_record() if isinstance(raw, PropMarketQuote) else dict(raw)
        identity = tuple(str(record.get(k) or "").strip() for k in ("game_id", "player_id", "prop_type"))
        if all(identity):
            identities.add(identity)
        else:
            rejected["UNRESOLVED_IDENTITY"] += 1
            continue
        try:
            if record.get("is_closing") or record.get("closing_evaluation_only"):
                rejected["CLOSING_EVALUATION_ONLY"] += 1
                continue
            captured = parse_utc(record["captured_at_utc"])
            kickoff = parse_utc(record["kickoff_utc"]) if record.get("kickoff_utc") else explicit_kickoff
            updated = parse_utc(record["sportsbook_last_update_utc"]) if record.get("sportsbook_last_update_utc") else captured
            if kickoff is None:
                rejected["MISSING_KICKOFF"] += 1
                continue
            if explicit_kickoff is not None and kickoff != explicit_kickoff:
                rejected["KICKOFF_CONFLICT"] += 1
                continue
            if captured > as_of or updated > captured:
                rejected["FUTURE_QUOTE"] += 1
                continue
            if captured >= kickoff or as_of >= kickoff:
                rejected["POST_KICKOFF"] += 1
                continue
            book = str(record.get("sportsbook_key") or "").strip().casefold()
            book = aliases.get(book, book)
            if not book:
                rejected["MISSING_BOOK_IDENTITY"] += 1
                continue
            age = (as_of - updated).total_seconds() / 60.0
            if age > age_limit:
                stale_books.add(book)
                rejected["STALE_QUOTE"] += 1
                continue
            record["kickoff_utc"] = kickoff
            record["sportsbook_key"] = book
            quote = PropMarketQuote(**{k: v for k, v in record.items() if k in names})
            parsed.append((quote, record, updated, age))
        except (ValueError, TypeError, KeyError, OverflowError):
            rejected["INVALID_QUOTE"] += 1
    if len(identities) > 1:
        raise ValueError("cannot mix canonical game/player/prop identities")
    if len({q.kickoff_utc for q, *_ in parsed}) > 1:
        raise ValueError("conflicting kickoff timestamps for canonical game")

    # A provider is a delivery channel, not an extra independent bookmaker.
    groups = defaultdict(list)
    for row in parsed:
        q = row[0]
        groups[(q.sportsbook_key, q.line)].append(row)
    selected = []
    for key in sorted(groups, key=str):
        group = groups[key]
        latest_source = max(row[2] for row in group)
        latest = [row for row in group if row[2] == latest_source]
        price_keys = {(r[0].over_american, r[0].under_american, r[0].yes_american, r[0].no_american) for r in latest}
        if len(price_keys) != 1:
            rejected["CONFLICTING_SAME_TIME_QUOTES"] += len(latest)
            continue
        selected.append(max(latest, key=lambda r: (r[0].captured_at_utc, r[0].provider)))
        rejected["DUPLICATE_BOOK_THRESHOLD"] += len(group) - 1

    identity = next(iter(identities), (None, None, None))
    binary = identity[2] == "anytime_td"
    by_line = defaultdict(list)
    conditional = []
    records = []
    for quote, source, updated, age in selected:
        record = quote.to_record()
        record.update({"quote_age_minutes": age, "age_basis": "book_update" if quote.sportsbook_last_update_utc else "capture_only",
                       "credential_mode": source.get("credential_mode", credential_mode)})
        records.append(record)
        first, second = ((quote.yes_american, quote.no_american) if binary else (quote.over_american, quote.under_american))
        if first is None or second is None:
            rejected["UNPAIRED_PRICE"] += 1
            continue
        p = float(remove_vig_two_way(first, second)["first_no_vig"])
        line = 0.5 if binary else float(quote.line)
        if not binary and line.is_integer():
            conditional.append({"sportsbook_key": quote.sportsbook_key, "line": line,
                                "p_over_given_no_push": p, "push_probability": None})
            continue
        # Non-standard quarter lines are split bets, not a single survival event.
        if not binary and line % 1 != 0.5:
            rejected["UNSUPPORTED_SETTLEMENT_THRESHOLD"] += 1
            continue
        by_line[line].append((quote.sportsbook_key, p))
    lines = sorted(by_line)
    raw_probs = [median_logit(p for _, p in by_line[line]) for line in lines]
    weights = [len(by_line[line]) for line in lines]
    fitted = _pava_nonincreasing(raw_probs, weights) if lines else []
    points = [{"line": line, "raw_consensus_p_over": raw_probs[i], "monotone_p_over": fitted[i],
               "source_books": sorted(book for book, _ in by_line[line]), "source_count": weights[i],
               "probability_range": max(p for _, p in by_line[line]) - min(p for _, p in by_line[line])}
              for i, line in enumerate(lines)]
    curve_books = {book for rows in by_line.values() for book, _ in rows}
    supported = len(curve_books) >= 2 and (binary or len(points) >= 3)
    status = SUPPORTED if supported else INSUFFICIENT
    books = sorted({q.sportsbook_key for q, *_ in selected})
    # Primary line consensus counts each book once; alternates never become primaries.
    primary = defaultdict(list)
    for row in selected:
        if not row[0].is_alternative_line:
            primary[row[0].sportsbook_key].append(row)
    primary_quotes = []
    for rows in primary.values():
        stamp = max(r[2] for r in rows)
        latest = [r for r in rows if r[2] == stamp]
        if len({r[0].line for r in latest}) == 1:
            primary_quotes.append(latest[0][0])
    primary_lines = [float(q.line) for q in primary_quotes if q.line is not None]
    consensus = median(primary_lines) if primary_lines else None
    target = _number(sportsbook_line) if sportsbook_line is not None else consensus
    if binary:
        target = 0.5
    p_target = probability_at(points, target, interpolate=supported) if target is not None else None
    p_fair = probability_at(points, fair_line, interpolate=supported) if fair_line is not None else None
    # Preserve direct exact-line prices separately from unconditional survival.
    conditional_target = [r["p_over_given_no_push"] for r in conditional if r["line"] == target]
    ages = [row[3] for row in selected]
    captured_times = [row[0].captured_at_utc for row in selected]
    median_bracket = _quantile_bracket(points, 0.5) if supported and not binary else None
    interval_brackets = {str(q): _quantile_bracket(points, q) for q in (0.1, 0.9)} if supported and not binary else {}
    median_value = median_bracket[0] if median_bracket and median_bracket[0] == median_bracket[1] else None
    binary_p = points[0]["monotone_p_over"] if supported and binary else None
    if binary_p is not None:
        median_value = 0 if binary_p <= 0.5 else 1
    reasons = [] if supported else [INSUFFICIENT]
    if len(books) < 2:
        reasons.append("THIN_MARKET")
    if stale_books:
        reasons.append("STALE_BOOK_CANDIDATES")
    if conditional:
        reasons.append("PUSH_PROBABILITY_UNIDENTIFIED")
    if not binary:
        reasons.append("UNOBSERVED_TAILS")
    adjusted = max((abs(a - b) for a, b in zip(raw_probs, fitted)), default=0.0)
    if adjusted:
        reasons.append("MONOTONICITY_REPAIR")
    result = {
        "version": VERSION, "research_only": True, "status": status, "distribution_status": status,
        "game_id": identity[0], "player_id": identity[1], "prop_type": identity[2],
        "as_of_utc": as_of.isoformat(), "book_count": len(books), "sportsbooks": books,
        "contributing_curve_book_count": len(curve_books), "survival_points": points,
        "consensus_line": consensus, "market_median": median_value,
        "market_median_bracket": median_bracket, "market_mean": binary_p,
        "market_variance": binary_p * (1 - binary_p) if binary_p is not None else None,
        "market_interval_80": [interval_brackets["0.1"][0], interval_brackets["0.9"][1]]
            if interval_brackets and all(interval_brackets.values()) else None,
        "quantile_brackets": interval_brackets,
        "market_probability_at_fair_line": p_fair,
        "market_probability_at_sportsbook_line": p_target,
        "probability_sportsbook_line": target,
        "market_conditional_probability_at_sportsbook_line": median_logit(conditional_target) if conditional_target else None,
        "conditional_push_observations": conditional,
        "probability_semantics": "P(any TD)" if binary else "P(Y > line), unconditional",
        "tail_probabilities": [{"line": p["line"], "p_over": p["monotone_p_over"]} for p in points],
        "quote_age_minutes": max(ages) if ages else None,
        "latest_quote_age_minutes": min(ages) if ages else None,
        "latest_capture_utc": max(captured_times).isoformat() if captured_times else None,
        "stale_book_candidates": sorted(stale_books),
        "probability_dispersion": max((p["probability_range"] for p in points), default=None),
        "line_dispersion": pstdev(primary_lines) if primary_lines else None,
        "line_disagreement": max(primary_lines) - min(primary_lines) if primary_lines else None,
        "alternate_line_count": len({q.line for q, *_ in selected if q.is_alternative_line}),
        "providers": sorted({q.provider for q, *_ in selected}),
        "credential_mode": credential_mode,
        "credential_modes": sorted({str(r["credential_mode"]) for r in records if r["credential_mode"] is not None}),
        "capture_horizon": capture_horizon or "AS_OBSERVED",
        "minutes_to_kickoff": (selected[0][0].kickoff_utc - as_of).total_seconds() / 60 if selected else None,
        "individual_books": records, "rejected_counts": dict(sorted(rejected.items())), "reasons": reasons,
        "distribution_quality": {"point_count": len(points), "max_monotone_adjustment": adjusted,
            "tail_support_complete": binary and supported, "interpolation": "integer-grid piecewise linear within observed thresholds" if supported and not binary else "none",
            "quantiles": "integer bounds; point only when identified", "book_weights": "equal, no outcome fit"},
        "fallback": {"method": "primary-book median line; exact paired prices only", "consensus_line": consensus,
                     "no_vig_p_over": p_target, "conditional_p_over_given_no_push": median_logit(conditional_target) if conditional_target else None},
        "movement": movement_summary([r[0] for r in parsed], as_of_utc=as_of) if parsed else None,
    }
    return result
