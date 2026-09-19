"""Fail-closed research QA for the distinct Props 2.1 challenger.

No forecast is changed here. Operational guardrails are not calibrated selection
thresholds, and simulation Monte Carlo error is not model uncertainty.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import math
from typing import Any

QA_VERSION = "levline-props-2.1-intelligence-qa-v0.1"
_ABS_GAPS = {"passing_yards": 100.0, "rushing_yards": 50.0,
             "receiving_yards": 50.0, "receptions": 4.0,
             "passing_tds": 1.5, "passing_touchdowns": 1.5}


def _map(value: Any) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _first_number(*values: Any) -> float | None:
    return next((n for value in values if (n := _number(value)) is not None), None)


def _time(value: Any) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, TypeError):
        return None


def _flag(code: str, severity: str, explanation: str, **details: Any) -> dict:
    return {"code": code, "severity": severity, "explanation": explanation,
            "details": details}


def check_accounting(accounting: Mapping | None) -> dict:
    """Check explicit complete expectation identities; partial populations skip.

    ``relationships`` entries have name, aggregate_mean, component_means,
    residual_mean, complete, statistic='expectation', source='model'|'market'.
    Residual must be explicit, including zero. Medians/lines never reconcile.
    Model tolerance defaults to numerical tolerance; market expectation tolerance
    defaults to max(1 unit, 20% of aggregate), a diagnostic guardrail only.
    """
    checked, skipped, flags = [], [], []
    for relation in _map(accounting).get("relationships", []):
        relation = _map(relation)
        name = str(relation.get("name", "unspecified"))
        source = str(relation.get("source", "model"))
        components = relation.get("component_means")
        if isinstance(components, Mapping):
            components = list(components.values())
        if (relation.get("complete") is not True or
                relation.get("statistic") != "expectation" or
                not isinstance(components, (list, tuple)) or not components or
                "residual_mean" not in relation):
            skipped.append({"name": name, "reason": "complete_expectations_and_explicit_residual_required"})
            continue
        aggregate = _number(relation.get("aggregate_mean"))
        residual = _number(relation.get("residual_mean"))
        values = [_number(value) for value in components]
        if aggregate is None or residual is None or any(value is None for value in values):
            flags.append(_flag("ACCOUNTING_INPUT_INVALID", "BLOCK", "Complete accounting contains non-finite or missing expectations.", relationship=name))
            continue
        total = sum(values) + residual
        default_tolerance = max(1.0, 0.20 * abs(aggregate)) if source == "market" else max(1e-6, 1e-6 * abs(aggregate))
        tolerance = _number(relation.get("tolerance"))
        tolerance = default_tolerance if tolerance is None else max(0.0, tolerance)
        detail = {"name": name, "source": source, "aggregate_mean": aggregate,
                  "component_sum_with_residual": total, "gap": aggregate - total,
                  "tolerance": tolerance}
        checked.append(detail)
        if abs(aggregate - total) > tolerance:
            market = source == "market"
            flags.append(_flag("MARKET_COHERENCE_ANOMALY" if market else "PLAYER_TEAM_ACCOUNTING_INCONSISTENCY",
                               "LIMIT" if market else "BLOCK",
                               "Complete expected-value components do not reconcile; this is not evidence the sportsbook is wrong." if market else "Complete player expectations do not reconcile to the team expectation and defined residual.", **detail))
    return {"checked": checked, "skipped": skipped, "flags": flags,
            "coverage": "CHECKED" if checked else "NOT_EVALUABLE"}


def evaluate_forecast_qa(forecast: Mapping, *, role_state: Mapping | None = None,
                         market_state: Mapping | None = None,
                         opportunity: Mapping | None = None,
                         accounting: Mapping | None = None,
                         stale_after_seconds: float = 3600.0) -> dict:
    """Return research eligibility and explanatory diagnostics without mutation.

    Publication eligibility means the forecast's numerical outputs may be shown;
    blocked rows may still be displayed as a NO SIGNAL diagnostic with numbers
    suppressed. No output is a wager recommendation or a confidence claim.
    """
    model, market = _map(forecast.get("model")), _map(forecast.get("market"))
    role, state, usage = _map(role_state), _map(market_state), _map(opportunity)
    provenance = _map(_map(forecast.get("provenance")).get("market"))
    flags, tags = [], []

    def add(code: str, severity: str, explanation: str, **details: Any) -> None:
        flags.append(_flag(code, severity, explanation, **details))

    def tag(code: str, label: str, explanation: str) -> None:
        tags.append({"code": code, "label": label, "explanation": explanation})

    player_id = str(forecast.get("player_id") or "")
    if not player_id or forecast.get("player_identity_resolved") is False or role.get("identity_resolved") is False:
        add("MARKET_PLAYER_MISSING_CANONICAL_STATE", "BLOCK", "A stable canonical player identity is required.")
    if role.get("player_id") and str(role["player_id"]) != player_id:
        add("MARKET_PLAYER_MISSING_CANONICAL_STATE", "BLOCK", "Role and forecast player identities disagree.")
    if not role:
        add("CURRENT_PLAYER_STATE_MISSING", "BLOCK", "Current canonical role state is unavailable.")

    forecast_at = _time(forecast.get("forecast_timestamp_utc"))
    kickoff = _time(forecast.get("kickoff_utc"))
    capture = _time(market.get("captured_utc") or provenance.get("as_of_utc"))
    if forecast_at is None or kickoff is None or forecast_at >= kickoff:
        add("FORECAST_NOT_PREGAME", "BLOCK", "Forecast and kickoff must establish a valid pregame cutoff.")
    if capture is None or (forecast_at is not None and capture > forecast_at) or (kickoff is not None and capture >= kickoff):
        add("MARKET_TIMESTAMP_INVALID", "BLOCK", "Market capture must be known, no later than forecast time, and before kickoff.")
    age = _first_number(state.get("oldest_quote_age_seconds"), state.get("quote_age_seconds"))
    if age is None and capture and forecast_at:
        age = (forecast_at - capture).total_seconds()
    if age is not None and age > stale_after_seconds:
        add("STALE_MARKET", "LIMIT", "At least one contributing quote exceeds the operational freshness limit.", quote_age_seconds=age, stale_after_seconds=stale_after_seconds)

    status = str(role.get("role_state") or role.get("state") or "UNKNOWN").upper()
    availability = str(role.get("availability_state") or role.get("availability_status") or role.get("availability") or "UNKNOWN").upper()
    out = status == "OUT" or availability in {"OUT", "INACTIVE", "IR"}
    if role.get("conflicts") or role.get("role_conflict") or status == "CONFLICT":
        add("ROLE_CONFLICT", "BLOCK", "Current qualified role evidence conflicts; the state must be resolved.")
    expected_starter = role.get("expected_starter_id")
    modeled_starter = usage.get("modeled_starter_id")
    if role.get("starter_mismatch") is True or (expected_starter and modeled_starter and expected_starter != modeled_starter):
        add("STARTER_MISMATCH", "BLOCK", "Expected and modeled starter identities disagree.", expected_starter_id=expected_starter, modeled_starter_id=modeled_starter)
    if availability in {"UNKNOWN", "UNRESOLVED", ""}:
        add("UNKNOWN_AVAILABILITY", "LIMIT", "Normal workload cannot be inferred without current availability evidence.")
    uncertain_states = {"UNKNOWN", "STARTER_EXPECTED", "COMMITTEE_UNCERTAIN", "WORKLOAD_LIMITED", "ROLE_REDUCED"}
    uncertain = status in uncertain_states or availability in {"QUESTIONABLE", "DOUBTFUL", "EXPECTED_TO_PLAY"} or role.get("role_uncertain") is True
    if uncertain:
        add("ROLE_UNCERTAINTY", "LIMIT", "Availability or workload remains uncertain; disagreement is research context only.", role_state=status, availability=availability)
    news = role.get("current_news_coverage")
    if news is not True:
        add("MISSING_CURRENT_NEWS_COVERAGE", "LIMIT", "No confirmed fresh qualified news coverage is recorded for this player.")

    prop = str(forecast.get("prop_type") or "")
    aliases = (("pass_attempts", "passing_attempts", "expected_pass_attempts") if prop.startswith("passing") else
               ("carries", "rush_attempts", "expected_carries") if prop.startswith("rushing") else
               ("targets", "expected_targets") if prop in {"receiving_yards", "receptions", "receiving_tds"} else
               ("total_opportunities", "touches"))
    amount = _first_number(*(usage.get(key) for key in aliases))
    line = _number(market.get("line"))
    market_exists = line is not None or _number(market.get("td_price_american")) is not None
    modeled_stat = _first_number(model.get("mean"), model.get("expected_tds"))
    if amount is None:
        add("OPPORTUNITY_UNVERIFIED", "LIMIT", "Expected opportunities are not retained for this prop; zero-volume state QA is incomplete.")
    elif amount < 0:
        add("OPPORTUNITY_INVALID", "BLOCK", "Expected opportunity cannot be negative.")
    elif market_exists and amount <= 0.1:
        add("MARKET_WITH_ZERO_MODEL_OPPORTUNITY", "BLOCK", "A quoted player market has approximately zero modeled opportunity.", expected_opportunity=amount)
    if market_exists and prop not in {"rushing_td", "receiving_td", "anytime_td"} and modeled_stat is not None and modeled_stat <= 0.1:
        add("MARKET_WITH_ZERO_MODEL_OUTPUT", "BLOCK", "A quoted player market has approximately zero modeled output; publish only as a suppressed diagnostic.", modeled_stat_expectation=modeled_stat)
    all_usage = [_number(usage.get(key)) for key in ("pass_attempts", "passing_attempts", "carries", "rush_attempts", "targets", "routes", "total_opportunities")]
    if out and (any(value is not None and value > 0.1 for value in all_usage) or (_number(model.get("mean")) or 0) > 0.1):
        add("OUT_PLAYER_WITH_OPPORTUNITY", "BLOCK", "An OUT/inactive player retains nonzero opportunity or a positive forecast.")
    elif out:
        add("PLAYER_OUT", "BLOCK", "The player is OUT/inactive and is ineligible for a research signal.")

    books = _first_number(state.get("book_count"), state.get("contributing_book_count"), _map(provenance.get("market_data_quality")).get("primary_sportsbook_count"))
    if books is None:
        names = {q.get("sportsbook_key") for q in provenance.get("individual_books", []) if isinstance(q, Mapping) and q.get("sportsbook_key")}
        books = float(len(names)) if names else None
    if books is None or books < 2:
        add("THIN_MARKET", "LIMIT", "Fewer than two verified contributing books; market agreement is weakly supported.", book_count=books)
    distribution_status = str(state.get("status") or state.get("distribution_status") or "MARKET_DISTRIBUTION_INSUFFICIENT")
    if distribution_status not in {"SUPPORTED", "MARKET_DISTRIBUTION_SUPPORTED", "AVAILABLE"}:
        add("MARKET_DISTRIBUTION_INSUFFICIENT", "INFO", "Supported threshold coverage does not establish a complete market distribution; use quoted consensus only.")

    fair = _number(model.get("fair_line"))
    gap = fair - line if fair is not None and line is not None else None
    if gap is not None and abs(gap) > max(_ABS_GAPS.get(prop, 4.0), 0.75 * abs(line)):
        add("IMPLAUSIBLY_LARGE_FAIR_LINE_GAP", "LIMIT", "Large disagreement requires state review and cannot increase confidence.", fair_line_gap=gap)
    if model.get("simulation_accounting_ok") is not True:
        add("SIMULATION_ACCOUNTING_UNVERIFIED", "BLOCK", "The upstream simulation has not affirmed football accounting integrity.")
    if _map(forecast.get("data_quality")).get("critical_ok") is False:
        add("UPSTREAM_CRITICAL_QA_FAILED", "BLOCK", "The source forecast failed its critical data-quality gate.")

    coherence = check_accounting(accounting)
    flags.extend(coherence["flags"])
    p = _first_number(model.get("over_probability"), model.get("td_probability"), model.get("probability_1_plus_td"))
    q = _first_number(market.get("no_vig_over_probability"), market.get("no_vig_probability"))
    if p is None or not 0 <= p <= 1:
        add("MODEL_PROBABILITY_INVALID", "BLOCK", "A finite model event probability in [0,1] is required.")
        p = None
    if q is None or not 0 <= q <= 1:
        add("MARKET_PROBABILITY_UNAVAILABLE", "LIMIT", "A comparable two-way no-vig market probability is unavailable.")
        q = None
    delta = p - q if p is not None and q is not None else None
    n = _number(model.get("simulation_count"))
    mcse = math.sqrt(p * (1 - p) / n) if p is not None and n is not None and n > 0 else None
    blocked = any(flag["severity"] == "BLOCK" for flag in flags)
    limited = any(flag["severity"] == "LIMIT" for flag in flags)
    signal = "NO SIGNAL" if blocked else "WATCH" if limited or delta is None or delta == 0 else "RADAR"
    classification = ("INSUFFICIENT EVIDENCE" if blocked or delta is None else
                      "ROLE-UNCERTAIN DISAGREEMENT" if uncertain else
                      "MARKET-THIN DISAGREEMENT" if books is None or books < 2 else
                      "DATA-QUALITY-LIMITED DISAGREEMENT" if limited else "MODEL DISAGREEMENT")
    role_labels = {"STARTER_CONFIRMED": "STARTER CONFIRMED", "ROLE_ELEVATED": "ROLE RISING", "ROLE_REDUCED": "ROLE REDUCED", "WORKLOAD_LIMITED": "WORKLOAD LIMITED", "COMMITTEE_UNCERTAIN": "COMMITTEE UNCERTAIN"}
    if status in role_labels and not blocked:
        tag(status, role_labels[status], "Qualified current role state: " + status.replace("_", " ").lower() + ".")
    tag_codes = {"THIN_MARKET": "MARKET THIN", "STALE_MARKET": "MARKET STALE", "ROLE_UNCERTAINTY": "ROLE UNCERTAIN", "MARKET_COHERENCE_ANOMALY": "MARKET COHERENCE ANOMALY"}
    for flag in flags:
        if flag["code"] in tag_codes and not any(t["code"] == flag["code"] for t in tags):
            tag(flag["code"], tag_codes[flag["code"]], flag["explanation"])
    if delta is not None and delta != 0 and not blocked:
        tag("MARKET_DISAGREEMENT", "MARKET DISAGREEMENT", "Pure model and no-vig market probabilities differ. Magnitude is not validated betting edge.")
    return {"version": QA_VERSION, "flags": flags, "signal_state": signal,
            "publication_eligible": not blocked, "research_eligible": not blocked,
            "betting_eligible": False, "research_only": True, "reason_tags": tags,
            "classification": classification, "accounting": coherence,
            "uncertainty": {"method": "uncalibrated_quality_proxy", "calibrated": False,
                            "delta": delta, "probability_interval": None,
                            "monte_carlo_standard_error": mcse,
                            "monte_carlo_caveat": "Simulation sampling error only; excludes model and parameter uncertainty.",
                            "components": {"role_state": status, "availability": availability,
                                           "book_count": books, "quote_age_seconds": age,
                                           "market_line_dispersion": _first_number(state.get("line_dispersion"), market.get("line_stddev")),
                                           "limitations": [flag["code"] for flag in flags if flag["severity"] != "INFO"]}}}
