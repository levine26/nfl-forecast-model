"""Point-in-time personnel evidence for the distinct Props 2.1 challenger.

Evidence is categorical, auditable and never a fantasy-style projection adjustment.
Availability, role and workload are independent. In particular, active != normal.
This module does not modify an input, frozen forecast, or winner-model surface.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

SCHEMA_VERSION = "levline-props-2.1-personnel-v0.1"
SUPPORTED_POSITIONS = {"QB", "RB", "WR", "TE"}
EVIDENCE_TYPES = {
    "STARTER_CONFIRMED", "STARTER_EXPECTED", "REPLACEMENT_STARTER", "ROLE_ELEVATED",
    "ROLE_REDUCED", "OUT", "AVAILABLE", "ACTIVATED", "QUESTIONABLE", "DOUBTFUL",
    "EXPECTED_TO_PLAY", "WORKLOAD_LIMITED", "SNAP_LIMITED", "RETURNING_FROM_INJURY",
    "COMMITTEE_UNCERTAIN", "GOAL_LINE_ROLE", "TEAMMATE_ABSENCE", "UNKNOWN",
    "NORMAL_WORKLOAD_CONFIRMED",
}
# Source qualification is descriptive and explicit, not learned book/news weighting.
MEDIA_HOSTS = {"nfl.com", "espn.com", "apnews.com", "reuters.com", "cbssports.com",
               "nbcsports.com", "foxsports.com", "si.com", "theathletic.com", "nytimes.com"}
TEAM_HOSTS = {"azcardinals.com", "atlantafalcons.com", "baltimoreravens.com", "buffalobills.com",
              "panthers.com", "chicagobears.com", "bengals.com", "clevelandbrowns.com",
              "dallascowboys.com", "denverbroncos.com", "detroitlions.com", "packers.com",
              "houstontexans.com", "colts.com", "jaguars.com", "chiefs.com", "raiders.com",
              "chargers.com", "therams.com", "miamidolphins.com", "vikings.com", "patriots.com",
              "neworleanssaints.com", "giants.com", "newyorkjets.com", "philadelphiaeagles.com",
              "steelers.com", "49ers.com", "seahawks.com", "buccaneers.com", "tennesseetitans.com",
               "commanders.com", "nfl.com"}
QUALIFIED_REPORTING_REFERENCE = "levline_current_reported_sources:qualified"

STRUCTURED_AVAILABILITY_STATUS = {
    "OUT": "OUT",
    "DOUBTFUL": "DOUBTFUL",
    "QUESTIONABLE": "QUESTIONABLE",
    "AVAILABLE": "AVAILABLE",
    "ACTIVE": "AVAILABLE",
}


def _structured_availability_claim(title: Any) -> tuple[str, str, str] | None:
    """Parse only exact team/player/status labels emitted by Sunday Signal evidence."""
    match = re.fullmatch(
        r"\s*([A-Z]{2,3})\s*:\s*(.+?)\s*[—-]\s*(Out|Doubtful|Questionable|Available|Active)\s*",
        _text(title),
        re.I,
    )
    if not match:
        return None
    team, player_name, raw_status = match.groups()
    status = STRUCTURED_AVAILABILITY_STATUS.get(raw_status.upper())
    if not status:
        return None
    return _team(team), _text(player_name), status



def _text(value: Any) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def _team(value: Any) -> str:
    value = _text(value).upper()
    return {"JAC": "JAX", "LA": "LAR"}.get(value, value)


def _name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _text(value).lower())


def _stamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def _rows(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if hasattr(value, "to_dict"):
        return value.to_dict("records")
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _host_allowed(url: Any, domains: set[str]) -> bool:
    try:
        parsed = urlparse(_text(url))
        host = (parsed.hostname or "").lower()
        return parsed.scheme in {"http", "https"} and any(host == d or host.endswith("." + d) for d in domains)
    except ValueError:
        return False


def _qualified(row: Mapping[str, Any]) -> bool:
    if row.get("qualification_state") != "QUALIFIED" or not _text(row.get("source")):
        return False
    kind = row.get("source_kind")
    if kind == "official":
        return _host_allowed(row.get("source_url"), TEAM_HOSTS)
    if kind == "media":
        return (_host_allowed(row.get("source_url"), MEDIA_HOSTS | TEAM_HOSTS)
                or row.get("qualification_reference") == QUALIFIED_REPORTING_REFERENCE)
    # Structured provider/depth evidence must already have a provider qualification receipt.
    return kind in {"provider", "depth_chart"} and bool(_text(row.get("qualification_reference")))


def build_personnel_intelligence(
    player_state: Any,
    evidence: Sequence[Mapping[str, Any]] = (),
    *,
    forecast_timestamp: Any,
    game_id: str | None = None,
    kickoff_timestamp: Any = None,
    max_age_hours: float = 48.0,
    depth_chart_max_age_hours: float = 168.0,
) -> dict[str, Any]:
    """Return JSON-safe states and every accepted/rejected structured evidence row.

    ``states`` is a list with unique (game_id, team, player_id) keys. ``state_by_key``
    indexes that list by ``game_id|team|player_id``. OUT alone permits a zero multiplier;
    every other state leaves numeric workload unset. Downstream consumers must honor
    opportunity_policy and must not replace null uncertainty with normal workload.
    """
    forecast = _stamp(forecast_timestamp)
    if forecast is None:
        raise ValueError("forecast_timestamp must be timezone-aware")
    if not all(math.isfinite(v) and v > 0 for v in (max_age_hours, depth_chart_max_age_hours)):
        raise ValueError("evidence age policies must be finite and positive")
    players = _rows(player_state)
    canonical: dict[tuple[str, str, str], dict[str, Any]] = {}
    invalid_identities = []
    for raw in players:
        row = dict(raw)
        row.update(game_id=_text(row.get("game_id") or game_id), team=_team(row.get("team")),
                   player_id=_text(row.get("player_id")), position=_text(row.get("position")).upper())
        if game_id and row["game_id"] != game_id:
            continue
        key = (row["game_id"], row["team"], row["player_id"])
        if not all(key) or row["position"] not in SUPPORTED_POSITIONS or not _text(row.get("player_name")):
            invalid_identities.append({"game_id": key[0], "team": key[1], "player_id": key[2]})
            continue
        if key in canonical:
            raise ValueError(f"duplicate canonical player identity: {key}")
        canonical[key] = row
    accepted, rejected = [], []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {key: [] for key in canonical}
    seen = set()
    for raw in evidence:
        row = dict(raw)
        row["game_id"] = _text(row.get("game_id"))
        row["team"] = _team(row.get("team"))
        row["player_id"] = _text(row.get("player_id"))
        row["evidence_type"] = _text(row.get("evidence_type")).upper()
        observed = _stamp(row.get("timestamp"))
        captured = _stamp(row.get("capture_timestamp"))
        row["available_before_forecast"] = bool(observed and captured and observed <= forecast and captured <= forecast)
        reason = None
        matches = [key for key, player in canonical.items()
                   if key[:2] == (row["game_id"], row["team"])
                   and ((row["player_id"] and key[2] == row["player_id"])
                        or (not row["player_id"] and _name(row.get("player_name"))
                            and _name(player.get("player_name")) == _name(row.get("player_name"))))]
        if len(matches) != 1:
            reason = "UNRESOLVED_PLAYER_IDENTITY"
            key = None
        else:
            key = matches[0]
            player = canonical[key]
            if row.get("player_name") and _name(row["player_name"]) != _name(player["player_name"]):
                reason = "CONFLICTING_PLAYER_IDENTITY"
            if row.get("position") and row["position"] != player["position"]:
                reason = "CONFLICTING_PLAYER_IDENTITY"
            row.update(player_id=key[2], player_name=player["player_name"], position=player["position"])
        if reason is None and not _qualified(row):
            reason = "UNQUALIFIED_SOURCE"
        if reason is None and row["evidence_type"] not in EVIDENCE_TYPES:
            reason = "UNSUPPORTED_EVIDENCE_TYPE"
        if reason is None and (observed is None or captured is None):
            reason = "MISSING_AWARE_TIMESTAMP"
        if reason is None and observed > captured:
            reason = "PUBLICATION_AFTER_CAPTURE"
        if reason is None and not row["available_before_forecast"]:
            reason = "FUTURE_EVIDENCE"
        if reason is None:
            age_limit = depth_chart_max_age_hours if row.get("source_kind") == "depth_chart" else max_age_hours
            if (forecast - observed).total_seconds() / 3600 > age_limit:
                reason = "STALE_EVIDENCE"
        if reason is None:
            kickoff = _stamp(canonical[key].get("kickoff_timestamp") or kickoff_timestamp)
            if kickoff is None or forecast >= kickoff:
                reason = "UNKNOWN_OR_STARTED_GAME"
        # Stable ID binds normalized evidence, not its input position or caller-supplied ID.
        row["timestamp"] = observed.isoformat() if observed else _text(row.get("timestamp"))
        row["capture_timestamp"] = captured.isoformat() if captured else _text(row.get("capture_timestamp"))
        identity = {k: row.get(k) for k in ("game_id", "team", "player_id", "evidence_type", "source", "source_url", "timestamp", "capture_timestamp")}
        row["evidence_id"] = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
        if reason is None and row["evidence_id"] in seen:
            reason = "DUPLICATE_EVIDENCE"
        row["accepted"] = reason is None
        row["rejection_reason"] = reason
        if reason:
            rejected.append(row)
        else:
            seen.add(row["evidence_id"])
            accepted.append(row)
            grouped[key].append(row)
    states = [_resolve_state(player, grouped[key], forecast, kickoff_timestamp)
              for key, player in sorted(canonical.items())]
    # Two equally current QB starter claims for the same team cannot both be valid.
    for game, team in sorted({(s["game_id"], s["team"]) for s in states}):
        qbs = [s for s in states if s["game_id"] == game and s["team"] == team and s["position"] == "QB"
               and s["role_state"] in {"STARTER_CONFIRMED", "STARTER_EXPECTED"}]
        if len(qbs) > 1:
            latest = max(s["role_evidence_timestamp"] for s in qbs)
            newest = [s for s in qbs if s["role_evidence_timestamp"] == latest]
            for s in qbs:
                if len(newest) > 1 or s not in newest:
                    s["role_state"] = "UNKNOWN"
                    s["opportunity_policy"] = "BLOCK_ROLE_DEPENDENT_SIGNAL"
                    s["uncertainties"].append("STARTER_CONFLICT" if len(newest) > 1 else "SUPERSEDED_STARTER")
                    s["reason_tags"] = [t for t in s["reason_tags"] if not t.startswith("STARTER")]
                    s["reason_tags"].append("ROLE UNCERTAIN")
    return {"schema_version": SCHEMA_VERSION, "forecast_timestamp": forecast.isoformat(),
            "states": states,
            "state_by_key": {"|".join((s["game_id"], s["team"], s["player_id"])): s for s in states},
            "evidence": accepted + rejected,
            "audit": {"players": len(states), "accepted_evidence": len(accepted), "rejected_evidence": len(rejected),
                      "rejection_counts": dict(Counter(r["rejection_reason"] for r in rejected)),
                      "invalid_canonical_identities": invalid_identities,
                      "news_covered_players": sum(s["news_coverage"] for s in states),
                      "completed_outcomes_used": False, "numeric_role_adjustments_fitted": False}}


def _resolve_state(player: Mapping[str, Any], evidence: list[dict], forecast: datetime, kickoff: Any) -> dict[str, Any]:
    types = {r["evidence_type"] for r in evidence}
    availability_types = {"OUT", "AVAILABLE", "ACTIVATED", "QUESTIONABLE", "DOUBTFUL", "EXPECTED_TO_PLAY"}
    availability_rows = [r for r in evidence if r["evidence_type"] in availability_types]
    availability = "UNKNOWN"
    uncertain = []
    if availability_rows:
        latest = max(r["timestamp"] for r in availability_rows)
        current = {r["evidence_type"] for r in availability_rows if r["timestamp"] == latest}
        # A later positive report cannot clear an official OUT unless equally official.
        outs = [r for r in availability_rows if r["evidence_type"] == "OUT"]
        cleared = [r for r in availability_rows if r["evidence_type"] in {"AVAILABLE", "ACTIVATED"}
                   and all(r["timestamp"] > o["timestamp"] and (o["source_kind"] != "official" or r["source_kind"] == "official") for o in outs)]
        if outs and not cleared:
            availability = "OUT"
            if types & {"STARTER_CONFIRMED", "STARTER_EXPECTED", "REPLACEMENT_STARTER", "AVAILABLE", "ACTIVATED"}:
                uncertain.append("OUT_ROLE_CONFLICT")
        elif len(current) > 1 and not current <= {"AVAILABLE", "ACTIVATED", "EXPECTED_TO_PLAY"}:
            uncertain.append("AVAILABILITY_CONFLICT")
        else:
            availability = "AVAILABLE" if current & {"AVAILABLE", "ACTIVATED"} else sorted(current)[0]
    role_map = {"STARTER_CONFIRMED": "STARTER_CONFIRMED", "STARTER_EXPECTED": "STARTER_EXPECTED",
                "REPLACEMENT_STARTER": "STARTER_EXPECTED", "ROLE_ELEVATED": "ROLE_ELEVATED",
                "ROLE_REDUCED": "ROLE_REDUCED", "COMMITTEE_UNCERTAIN": "COMMITTEE_UNCERTAIN"}
    roles = [r for r in evidence if r["evidence_type"] in role_map]
    role, role_time = "UNKNOWN", None
    if roles:
        role_time = max(r["timestamp"] for r in roles)
        current_roles = {role_map[r["evidence_type"]] for r in roles if r["timestamp"] == role_time}
        if len(current_roles) > 1 and not current_roles <= {"STARTER_CONFIRMED", "STARTER_EXPECTED", "ROLE_ELEVATED"}:
            uncertain.append("ROLE_CONFLICT")
        else:
            role = next(r for r in ("STARTER_CONFIRMED", "STARTER_EXPECTED", "ROLE_ELEVATED", "ROLE_REDUCED", "COMMITTEE_UNCERTAIN") if r in current_roles)
    workload = "UNKNOWN"
    if types & {"WORKLOAD_LIMITED", "SNAP_LIMITED"}:
        workload, role = "LIMITED", "WORKLOAD_LIMITED"
    elif "RETURNING_FROM_INJURY" in types:
        uncertain.append("RETURNING_FROM_INJURY")
    elif "NORMAL_WORKLOAD_CONFIRMED" in types and availability == "AVAILABLE":
        workload = "NORMAL_CONFIRMED"
    policy = "RETAIN_BASELINE_RADAR_ONLY"
    if role in {"ROLE_ELEVATED", "ROLE_REDUCED", "WORKLOAD_LIMITED", "COMMITTEE_UNCERTAIN"} or "ROLE_CONFLICT" in uncertain:
        policy = "BLOCK_ROLE_DEPENDENT_SIGNAL"
    if availability == "OUT":
        role, workload, policy = "OUT", "ZERO", "ZERO_OPPORTUNITY"
    elif availability in {"UNKNOWN", "QUESTIONABLE", "DOUBTFUL", "EXPECTED_TO_PLAY"}:
        uncertain.append("AVAILABILITY_UNCERTAIN")
    if workload == "UNKNOWN" and availability != "OUT":
        uncertain.append("WORKLOAD_UNQUANTIFIED")
    if role in {"UNKNOWN", "COMMITTEE_UNCERTAIN", "STARTER_EXPECTED"}:
        uncertain.append("ROLE_UNCERTAIN")
    news = any(r["source_kind"] in {"media", "official"} and r.get("channel") != "availability" for r in evidence)
    if not news:
        uncertain.append("MISSING_CURRENT_NEWS_COVERAGE")
    game_kickoff = _stamp(player.get("kickoff_timestamp") or kickoff)
    if game_kickoff is None or forecast >= game_kickoff:
        uncertain.append("UNKNOWN_OR_STARTED_GAME")
        policy = "BLOCK_ROLE_DEPENDENT_SIGNAL"
    tags = [role.replace("_", " ")] if role != "UNKNOWN" else ["ROLE UNCERTAIN"]
    if "GOAL_LINE_ROLE" in types:
        tags.append("GOAL-LINE ROLE")
    if uncertain and "ROLE UNCERTAIN" not in tags and availability != "OUT":
        tags.append("ROLE UNCERTAIN")
    return {k: player[k] for k in ("game_id", "team", "player_id", "player_name", "position")} | {
        "role_state": role, "availability_state": availability, "workload_state": workload,
        "role_evidence_timestamp": role_time, "opportunity_policy": policy,
        "workload_multiplier": 0.0 if availability == "OUT" else None,
        "active_probability": 0.0 if availability == "OUT" else None,
        "reason_tags": tags, "uncertainties": sorted(set(uncertain)), "news_coverage": news,
        "evidence_ids": sorted(r["evidence_id"] for r in evidence),
        "evidence_types": sorted(types), "research_only": True}


def _headline_claims(title: str, player_name: str) -> list[str]:
    """A small conservative subject-bound grammar; no free-text numerical mapping."""
    match = re.search(r"(?<!\w)" + re.escape(player_name) + r"(?!\w)", title, re.I)
    if not match:
        return []
    # An anchored clause prevents 'A ruled out; B starts' attributing B's role to A.
    clause = title[match.end():].lower().strip(" :,-")
    clause = re.sub(r"^\([^)]{1,40}\)\s*", "", clause)
    clause = re.split(r"[;.!?]|\b(?:after|while|because|but)\b", clause, maxsplit=1)[0]
    clause = re.sub(r"^(?:is |was |has been |will be )", "", clause)
    patterns = (
        (r"^(?:ruled out|out\b|inactive\b)", "OUT"),
        (r"^(?:expected to be |will be )?(?:on a snap count|limited\b)", "WORKLOAD_LIMITED"),
        (r"^(?:expected to play|likely to play)\b", "EXPECTED_TO_PLAY"),
        (r"^(?:will start|starts\b|starting\b|named (?:the )?starter)", "STARTER_CONFIRMED"),
        (r"^(?:expected to start|set to start|slated to start)", "STARTER_EXPECTED"),
        (r"^auditioning\b.*\bwith (?:a )?start\b", "STARTER_EXPECTED"),
        (r"^(?:expected to (?:lead the backfield|see an expanded role)|promoted (?:to|into) (?:the )?(?:lead|top[- ]?[23])|role expands)", "ROLE_ELEVATED"),
        (r"^(?:role reduced|demoted|expected to see (?:a )?reduced role)", "ROLE_REDUCED"),
        (r"^(?:in (?:an? )?(?:uncertain )?committee|could start|may start|role uncertain)", "COMMITTEE_UNCERTAIN"),
        (r"^(?:activated|active\b|available\b)", "AVAILABLE"),
        (r"^(?:returning from injury|returns from injury)", "RETURNING_FROM_INJURY"),
        (r"^questionable\b", "QUESTIONABLE"), (r"^doubtful\b", "DOUBTFUL"),
    )
    return [kind for pattern, kind in patterns if re.search(pattern, clause)]


def adapt_personnel_evidence(
    manifest: Mapping[str, Any], player_state: Any = None, media_payload: Mapping[str, Any] | None = None,
    *, depth_charts: Any = None,
) -> dict[str, Any]:
    """Adapt existing manifest/canonical state/current_reported_sources without mutation.

    Returns ``player_state`` and ``evidence`` ready for build_personnel_intelligence.
    Manifest alone supplies identity only: prior usage and simulation availability
    probabilities never masquerade as current role/availability evidence. News capture
    time is required separately from publication time; generated-at time may supply it.
    """
    game = _text(manifest.get("game_id"))
    kickoff = manifest.get("kickoff_utc")
    players = _rows(player_state) if player_state is not None else _rows(manifest.get("player_state"))
    if not players:
        players = _rows(manifest.get("efficiency_player_parameters"))
    players = [{**p, "game_id": p.get("game_id") or game, "kickoff_timestamp": p.get("kickoff_timestamp") or kickoff} for p in players]
    evidence = _rows(manifest.get("personnel_evidence"))
    for player in players:
        status = _text(player.get("expected_active_state")).upper()
        if status in {"OUT", "AVAILABLE", "QUESTIONABLE", "DOUBTFUL"}:
            evidence.append({"game_id": player["game_id"], "team": player.get("team"),
                             "player_id": player.get("player_id"), "player_name": player.get("player_name"),
                             "evidence_type": status, "source": player.get("availability_source_name"),
                             "source_url": player.get("availability_source_url"), "source_kind": "provider",
                             "qualification_state": "QUALIFIED" if player.get("availability_source_status") == "CURRENT_TIMESTAMPED" else "UNQUALIFIED",
                             "qualification_reference": "canonical_player_state:CURRENT_TIMESTAMPED",
                             "timestamp": player.get("availability_capture_timestamp"),
                             "capture_timestamp": player.get("availability_capture_timestamp"),
                             "timestamp_basis": "provider_observation", "channel": "availability"})
    payload = media_payload or {}
    game_map = payload.get("games", payload)
    entry = game_map.get(game, {}) if isinstance(game_map, Mapping) else {}
    if isinstance(entry, Mapping):
        capture = entry.get("captured_at_utc") or entry.get("generated_utc") or payload.get("captured_at_utc") or payload.get("generated_utc")

        # Reuse Sunday Signal's structured official availability observations only
        # when the timestamped matchup row joins exactly to a structured personnel
        # record that carries an allowlisted official URL. This is intentionally
        # narrower than free-text headline parsing and never infers workload.
        structured_sources: dict[tuple[str, str], set[tuple[str, str]]] = {}
        for collection in ("evidence_used", "key_factors"):
            for source_row in entry.get(collection, []) or []:
                if not isinstance(source_row, Mapping):
                    continue
                title = _text(source_row.get("title"))
                source_name = _text(source_row.get("source_name"))
                source_url = _text(source_row.get("source_url"))
                category = _text(source_row.get("category") or source_row.get("family")).lower()
                if not title or not source_url or category not in {"personnel", "availability"}:
                    continue
                structured_sources.setdefault((title, source_name), set()).add((source_name, source_url))
        for observation in entry.get("matchup_meter", []) or []:
            if not isinstance(observation, Mapping) or _text(observation.get("family")).lower() != "availability":
                continue
            claim = _structured_availability_claim(observation.get("title"))
            if claim is None:
                continue
            claim_team, claim_name, kind = claim
            matches = [
                player for player in players
                if _text(player.get("game_id")) == game
                and _team(player.get("team")) == claim_team
                and _name(player.get("player_name")) == _name(claim_name)
            ]
            if len(matches) != 1:
                continue
            source_name = _text(observation.get("source_name"))
            source_candidates = structured_sources.get((_text(observation.get("title")), source_name), set())
            if len(source_candidates) != 1:
                continue
            qualified_source_name, source_url = next(iter(source_candidates))
            if not _host_allowed(source_url, TEAM_HOSTS):
                continue
            observed = observation.get("as_of") or observation.get("timestamp")
            captured = observation.get("capture_timestamp") or observation.get("captured_at_utc") or capture
            if _stamp(observed) is None or _stamp(captured) is None:
                continue
            player = matches[0]
            evidence.append({
                "game_id": game,
                "team": player.get("team"),
                "player_id": player.get("player_id"),
                "player_name": player.get("player_name"),
                "position": player.get("position"),
                "evidence_type": kind,
                "source": qualified_source_name,
                "source_url": source_url,
                "source_kind": "official",
                "qualification_state": "QUALIFIED",
                "qualification_reference": "sunday_signal:structured_official_availability",
                "timestamp": observed,
                "capture_timestamp": captured,
                "timestamp_basis": "official_status_observation",
                "title": observation.get("title"),
                "channel": "availability",
            })

        for source in entry.get("current_reported_sources", []) or []:
            if not isinstance(source, Mapping):
                continue
            url = source.get("source_url") or source.get("url")
            for player in players:
                if _text(player.get("game_id")) != game:
                    continue
                for kind in _headline_claims(_text(source.get("title")), _text(player.get("player_name"))):
                    evidence.append({"game_id": game, "team": player.get("team"), "player_id": player.get("player_id"),
                                     "player_name": player.get("player_name"), "evidence_type": kind,
                                     "source": source.get("source_name") or source.get("name"), "source_url": url,
                                     "source_kind": "official" if _host_allowed(url, TEAM_HOSTS) else "media",
                                     "qualification_state": "QUALIFIED", "confidence": "EXPLICIT_SUBJECT_BOUND_CLAIM",
                                     "qualification_reference": QUALIFIED_REPORTING_REFERENCE,
                                     "timestamp": source.get("as_of") or source.get("published_at"),
                                     "capture_timestamp": source.get("capture_timestamp") or source.get("captured_at_utc") or capture,
                                     "title": source.get("title"), "channel": "current_reported_sources"})
    for depth in _rows(depth_charts):
        for player in players:
            if _text(depth.get("gsis_id") or depth.get("player_id")) != _text(player.get("player_id")) or _team(depth.get("team")) != _team(player.get("team")):
                continue
            if _text(depth.get("pos_rank")) not in {"1", "1.0"}:
                continue
            evidence.append({"game_id": player["game_id"], "team": player.get("team"), "player_id": player.get("player_id"),
                             "evidence_type": "STARTER_EXPECTED", "source": "nflverse_timestamped_depth_chart",
                             "source_kind": "depth_chart", "qualification_state": "QUALIFIED",
                             "qualification_reference": "nflverse:timestamped_depth_chart",
                             "timestamp": depth.get("dt"), "capture_timestamp": depth.get("capture_timestamp"),
                             "confidence": "DEPTH_CHART_ONLY"})
    return {"player_state": players, "evidence": evidence}
