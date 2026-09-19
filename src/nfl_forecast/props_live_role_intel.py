from __future__ import annotations

"""Point-in-time live role intelligence for LevLine Props Research Beta.

This layer reconciles canonical player state with the same current reporting and market
surfaces used elsewhere in Sunday Signal. It is deliberately narrow:

* explicit, timestamped media reporting may identify the expected starting QB;
* a unique multi-book QB passing-yards market may corroborate or identify the expected QB;
* official/canonical OUT evidence vetoes a candidate;
* market *presence* may inform lineup identity, but market line/price magnitude never enters
  the football projection.

The output is a provenance-rich primary-QB override contract consumed by the existing
opportunity model. It does not alter F-ST, winner probabilities, model coefficients, or
statistical efficiency priors.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re
import unicodedata
from typing import Any, Mapping, Sequence

from .props_player_state import normalize_team_code

CONTRACT_VERSION = "levline-props-live-role-intel-v0.1"
MIN_QB_PASSING_MARKET_BOOKS = 2
MAX_MEDIA_AGE_HOURS = 72.0
FRESH_CONFLICT_HOURS = 24.0


class PropsLiveRoleIntelError(ValueError):
    pass


def _utc(value: object, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PropsLiveRoleIntelError(f"{label} must be a valid ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise PropsLiveRoleIntelError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _norm_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _source_urls(value: object) -> list[str]:
    rows = value if isinstance(value, list) else []
    return sorted(
        {
            str(row.get("url") or "").strip()
            for row in rows
            if isinstance(row, Mapping) and str(row.get("url") or "").strip()
        }
    )


def _explicit_starter_phrase(text: str, player_name: str) -> str | None:
    """Return a conservative explicit-starter phrase for one named player.

    We require the player's full normalized name to occur in the same sentence as a
    starter/takeover phrase. This intentionally misses vague reporting rather than
    guessing a role from generic depth-chart prose.
    """

    name_token = _norm_name(player_name)
    if not name_token:
        return None
    sentences = re.split(r"(?<=[.!?])\s+", str(text or ""))
    positive = (
        "expected to start",
        "will start",
        "set to start",
        "slated to start",
        "scheduled to start",
        "named the starter",
        "named starter",
        "starting at quarterback",
        "will take over",
        "take over at quarterback",
    )
    negative = (
        "expected to miss",
        "will miss",
        "ruled out",
        "is out",
        "doubtful",
        "not expected to play",
    )
    for sentence in sentences:
        normalized_sentence = _norm_name(sentence)
        if name_token not in normalized_sentence:
            continue
        lower = sentence.lower()
        if any(marker in lower for marker in negative):
            continue
        for marker in positive:
            if marker in lower:
                return marker
    return None


@dataclass(frozen=True)
class _QbState:
    game_id: str
    team: str
    player_id: str
    player_name: str
    expected_active_state: str


def _qb_directory(player_state_rows: Sequence[Mapping[str, Any]]) -> tuple[
    dict[tuple[str, str], list[_QbState]],
    dict[tuple[str, str], _QbState],
]:
    by_team: dict[tuple[str, str], list[_QbState]] = {}
    by_id: dict[tuple[str, str], _QbState] = {}
    for raw in player_state_rows:
        row = dict(raw)
        if str(row.get("position") or "").upper().strip() != "QB":
            continue
        game_id = str(row.get("game_id") or "").strip()
        team = normalize_team_code(row.get("team"))
        player_id = str(row.get("player_id") or "").strip()
        player_name = str(row.get("player_name") or "").strip()
        if not game_id or not team or not player_id or not player_name:
            raise PropsLiveRoleIntelError("QB player-state rows require stable game/team/player identity")
        state = _QbState(
            game_id=game_id,
            team=team,
            player_id=player_id,
            player_name=player_name,
            expected_active_state=str(row.get("expected_active_state") or "UNKNOWN").upper().strip(),
        )
        by_team.setdefault((game_id, team), []).append(state)
        key = (game_id, player_id)
        if key in by_id:
            raise PropsLiveRoleIntelError(f"duplicate QB identity in player state: {key}")
        by_id[key] = state
    return by_team, by_id


def _official_out_ids(
    player_state_rows: Sequence[Mapping[str, Any]],
    contextual_evidence: Mapping[str, Any] | None,
    *,
    as_of: datetime,
) -> tuple[set[tuple[str, str]], list[dict[str, Any]]]:
    """Return QB identities explicitly OUT in canonical or official contextual evidence."""

    by_team, _ = _qb_directory(player_state_rows)
    out: set[tuple[str, str]] = set()
    evidence_rows: list[dict[str, Any]] = []

    for qbs in by_team.values():
        for qb in qbs:
            if qb.expected_active_state == "OUT":
                out.add((qb.game_id, qb.player_id))
                evidence_rows.append(
                    {
                        "game_id": qb.game_id,
                        "team": qb.team,
                        "player_id": qb.player_id,
                        "source": "canonical_player_state",
                        "status": "OUT",
                    }
                )

    if not isinstance(contextual_evidence, Mapping):
        return out, evidence_rows

    for game_id, items in contextual_evidence.items():
        if not isinstance(items, list):
            continue
        qbs_for_game = [
            qb
            for (gid, _team), team_qbs in by_team.items()
            if str(gid) == str(game_id)
            for qb in team_qbs
        ]
        for item in items:
            if not isinstance(item, Mapping):
                continue
            meta = item.get("metadata") if isinstance(item.get("metadata"), Mapping) else {}
            position = str(meta.get("position") or "").upper().strip()
            text = " ".join(
                str(item.get(key) or "") for key in ("title", "summary")
            )
            if position and position != "QB":
                continue
            lower = text.lower()
            if "— out" not in lower and " as out" not in lower and " ruled out" not in lower:
                continue
            raw_ts = item.get("as_of")
            if not raw_ts:
                continue
            try:
                observed = _utc(raw_ts, "contextual evidence as_of")
            except PropsLiveRoleIntelError:
                continue
            if observed > as_of:
                continue
            for qb in qbs_for_game:
                if _norm_name(qb.player_name) and _norm_name(qb.player_name) in _norm_name(text):
                    out.add((qb.game_id, qb.player_id))
                    evidence_rows.append(
                        {
                            "game_id": qb.game_id,
                            "team": qb.team,
                            "player_id": qb.player_id,
                            "source": str(item.get("source_name") or "contextual_evidence"),
                            "source_url": item.get("source_url"),
                            "observed_at_utc": observed.isoformat(),
                            "status": "OUT",
                        }
                    )
    return out, evidence_rows


def _media_candidates(
    by_team: Mapping[tuple[str, str], Sequence[_QbState]],
    media_reads: Mapping[str, Any] | None,
    *,
    as_of: datetime,
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = {}
    audit: list[dict[str, Any]] = []
    if not isinstance(media_reads, Mapping):
        return candidates, audit
    games = media_reads.get("games")
    if not isinstance(games, Mapping):
        return candidates, audit

    for (game_id, team), qbs in by_team.items():
        game = games.get(game_id)
        if not isinstance(game, Mapping):
            continue
        timestamp_raw = game.get("generated_utc") or media_reads.get("generated_utc")
        if not timestamp_raw:
            audit.append({"game_id": game_id, "team": team, "status": "media_missing_timestamp"})
            continue
        try:
            observed = _utc(timestamp_raw, "media generated_utc")
        except PropsLiveRoleIntelError:
            audit.append({"game_id": game_id, "team": team, "status": "media_invalid_timestamp"})
            continue
        age_hours = (as_of - observed).total_seconds() / 3600.0
        if observed > as_of:
            audit.append({"game_id": game_id, "team": team, "status": "media_future_discarded"})
            continue
        if age_hours > MAX_MEDIA_AGE_HOURS:
            audit.append(
                {
                    "game_id": game_id,
                    "team": team,
                    "status": "media_stale_discarded",
                    "age_hours": age_hours,
                }
            )
            continue
        text = " ".join(
            str(game.get(key) or "")
            for key in ("headline", "paragraph1", "read", "model_rationale")
        )
        urls = _source_urls(game.get("sources"))
        for qb in qbs:
            phrase = _explicit_starter_phrase(text, qb.player_name)
            if phrase is None:
                continue
            candidates.setdefault((game_id, team), []).append(
                {
                    "player_id": qb.player_id,
                    "player_name": qb.player_name,
                    "observed_at_utc": observed.isoformat(),
                    "age_hours": age_hours,
                    "phrase": phrase,
                    "source_urls": urls,
                    "source": "sunday_signal_media_reporting",
                }
            )
    return candidates, audit


def _market_candidates(
    by_id: Mapping[tuple[str, str], _QbState],
    market_artifacts: Sequence[Mapping[str, Any]],
    *,
    captured_at: datetime,
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    candidates: dict[tuple[str, str], list[dict[str, Any]]] = {}
    audit: list[dict[str, Any]] = []

    for raw in market_artifacts:
        artifact = dict(raw)
        if str(artifact.get("prop_type") or "") != "passing_yards":
            continue
        game_id = str(artifact.get("game_id") or "").strip()
        player_id = str(artifact.get("player_id") or "").strip()
        qb = by_id.get((game_id, player_id))
        if qb is None:
            audit.append(
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "status": "passing_market_not_canonical_qb",
                }
            )
            continue
        books = int(_finite(artifact.get("sportsbook_count")) or 0)
        line = _finite(artifact.get("consensus_line"))
        if books < MIN_QB_PASSING_MARKET_BOOKS or line is None or line <= 0:
            audit.append(
                {
                    "game_id": game_id,
                    "team": qb.team,
                    "player_id": player_id,
                    "status": "passing_market_too_thin_for_role_inference",
                    "sportsbook_count": books,
                }
            )
            continue
        candidates.setdefault((game_id, qb.team), []).append(
            {
                "player_id": qb.player_id,
                "player_name": qb.player_name,
                "sportsbook_count": books,
                "captured_at_utc": captured_at.isoformat(),
                # We deliberately record that a valid line exists but never serialize its
                # magnitude into the role evidence used by the football model.
                "source": "the_odds_api_multi_book_passing_market_presence",
            }
        )
    return candidates, audit


def _unique_candidate(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    by_player: dict[str, dict[str, Any]] = {}
    for row in rows:
        player_id = str(row.get("player_id") or "").strip()
        if not player_id:
            continue
        current = by_player.get(player_id)
        if current is None:
            by_player[player_id] = dict(row)
            continue
        if int(row.get("sportsbook_count") or 0) > int(current.get("sportsbook_count") or 0):
            by_player[player_id] = dict(row)
    if len(by_player) != 1:
        return None
    return next(iter(by_player.values()))


def build_live_role_intelligence(
    *,
    player_state_rows: Sequence[Mapping[str, Any]],
    market_artifacts: Sequence[Mapping[str, Any]],
    market_captured_at_utc: object,
    contextual_evidence: Mapping[str, Any] | None = None,
    media_reads: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build provenance-rich expected-primary-QB overrides.

    Market magnitude is intentionally excluded from role inference. A unique multi-book
    passing-yards *presence* is treated as a strong expectation that the named QB will
    handle meaningful starting-quarterback volume. Fresh explicit media reporting can
    independently identify the starter. Conflicts fail closed.
    """

    captured_at = _utc(market_captured_at_utc, "market_captured_at_utc")
    by_team, by_id = _qb_directory(player_state_rows)
    out_ids, out_audit = _official_out_ids(
        player_state_rows,
        contextual_evidence,
        as_of=captured_at,
    )
    media, media_audit = _media_candidates(by_team, media_reads, as_of=captured_at)
    market, market_audit = _market_candidates(
        by_id,
        market_artifacts,
        captured_at=captured_at,
    )

    resolved: dict[str, dict[str, dict[str, Any]]] = {}
    conflicts: list[dict[str, Any]] = []
    team_audit: list[dict[str, Any]] = []

    for key in sorted(by_team):
        game_id, team = key
        news_candidate = _unique_candidate(media.get(key, []))
        market_candidate = _unique_candidate(market.get(key, []))

        if len({str(row.get("player_id")) for row in media.get(key, []) if row.get("player_id")}) > 1:
            conflicts.append(
                {
                    "game_id": game_id,
                    "team": team,
                    "reason": "multiple_explicit_media_starter_candidates",
                    "candidate_ids": sorted(
                        {str(row.get("player_id")) for row in media.get(key, []) if row.get("player_id")}
                    ),
                }
            )
            continue
        if len({str(row.get("player_id")) for row in market.get(key, []) if row.get("player_id")}) > 1:
            conflicts.append(
                {
                    "game_id": game_id,
                    "team": team,
                    "reason": "multiple_multi_book_passing_market_qbs",
                    "candidate_ids": sorted(
                        {str(row.get("player_id")) for row in market.get(key, []) if row.get("player_id")}
                    ),
                }
            )
            continue

        selected: Mapping[str, Any] | None = None
        source = None
        if news_candidate and market_candidate:
            news_id = str(news_candidate["player_id"])
            market_id = str(market_candidate["player_id"])
            if news_id == market_id:
                selected = market_candidate
                source = "news_and_market_agree"
            else:
                news_age = float(news_candidate.get("age_hours") or 0.0)
                if news_age <= FRESH_CONFLICT_HOURS:
                    conflicts.append(
                        {
                            "game_id": game_id,
                            "team": team,
                            "reason": "fresh_media_market_qb_conflict",
                            "media_player_id": news_id,
                            "market_player_id": market_id,
                            "media_age_hours": news_age,
                        }
                    )
                    continue
                selected = market_candidate
                source = "market_supersedes_older_media"
        elif market_candidate:
            selected = market_candidate
            source = "market_presence_unique"
        elif news_candidate:
            selected = news_candidate
            source = "explicit_media_starter"

        if selected is None:
            team_audit.append(
                {
                    "game_id": game_id,
                    "team": team,
                    "status": "no_live_override_depth_chart_fallback",
                }
            )
            continue

        player_id = str(selected["player_id"])
        if (game_id, player_id) in out_ids:
            conflicts.append(
                {
                    "game_id": game_id,
                    "team": team,
                    "reason": "selected_qb_explicitly_out",
                    "player_id": player_id,
                }
            )
            continue

        evidence = []
        if news_candidate and str(news_candidate.get("player_id")) == player_id:
            evidence.append(dict(news_candidate))
        if market_candidate and str(market_candidate.get("player_id")) == player_id:
            evidence.append(dict(market_candidate))

        provenance_parts = [
            f"levline_shared_live_role_intel:{source}",
            f"as_of={captured_at.isoformat()}",
        ]
        if market_candidate and str(market_candidate.get("player_id")) == player_id:
            provenance_parts.append(
                f"market_books={int(market_candidate.get('sportsbook_count') or 0)}"
            )
        if news_candidate and str(news_candidate.get("player_id")) == player_id:
            provenance_parts.append(
                f"media_observed={news_candidate.get('observed_at_utc')}"
            )

        resolved.setdefault(game_id, {})[team] = {
            "player_id": player_id,
            "provenance": ";".join(provenance_parts),
            "resolution": source,
            "evidence": evidence,
        }
        team_audit.append(
            {
                "game_id": game_id,
                "team": team,
                "status": "resolved_live_primary_qb",
                "player_id": player_id,
                "resolution": source,
            }
        )

    return {
        "contract_version": CONTRACT_VERSION,
        "research_only": True,
        "winner_model_mutated": False,
        "market_line_magnitude_used_for_projection": False,
        "market_price_used_for_projection": False,
        "market_presence_used_for_lineup_identity": True,
        "market_captured_at_utc": captured_at.isoformat(),
        "primary_qb_by_game": resolved,
        "blocking_conflicts": conflicts,
        "audit": {
            "games_in_player_state": len({key[0] for key in by_team}),
            "teams_in_player_state": len(by_team),
            "resolved_team_qbs": sum(len(value) for value in resolved.values()),
            "blocking_conflict_count": len(conflicts),
            "official_out_evidence": out_audit,
            "media_audit": media_audit,
            "market_audit": market_audit,
            "team_resolution": team_audit,
        },
    }


def primary_qbs_for_game(payload: Mapping[str, Any], game_id: str) -> dict[str, dict[str, Any]]:
    if str(payload.get("contract_version") or "") != CONTRACT_VERSION:
        raise PropsLiveRoleIntelError("unsupported live role intelligence contract")
    games = payload.get("primary_qb_by_game")
    if not isinstance(games, Mapping):
        raise PropsLiveRoleIntelError("live role intelligence missing primary_qb_by_game")
    value = games.get(str(game_id), {})
    if not isinstance(value, Mapping):
        raise PropsLiveRoleIntelError(f"live role intelligence game payload must be an object: {game_id}")
    return {
        normalize_team_code(team): dict(row)
        for team, row in value.items()
        if isinstance(row, Mapping)
    }


def validate_live_role_intelligence(payload: Mapping[str, Any]) -> None:
    if str(payload.get("contract_version") or "") != CONTRACT_VERSION:
        raise PropsLiveRoleIntelError("unsupported live role intelligence contract")
    _utc(payload.get("market_captured_at_utc"), "market_captured_at_utc")
    if payload.get("market_line_magnitude_used_for_projection") is not False:
        raise PropsLiveRoleIntelError("market line magnitude must not enter role intelligence")
    if payload.get("market_price_used_for_projection") is not False:
        raise PropsLiveRoleIntelError("market price must not enter role intelligence")
    games = payload.get("primary_qb_by_game")
    if not isinstance(games, Mapping):
        raise PropsLiveRoleIntelError("primary_qb_by_game must be an object")
    for game_id, teams in games.items():
        if not str(game_id).strip() or not isinstance(teams, Mapping):
            raise PropsLiveRoleIntelError("invalid game in primary_qb_by_game")
        for team, row in teams.items():
            if not normalize_team_code(team) or not isinstance(row, Mapping):
                raise PropsLiveRoleIntelError("invalid team override in live role intelligence")
            if not str(row.get("player_id") or "").strip():
                raise PropsLiveRoleIntelError("live primary-QB override missing player_id")
            if not str(row.get("provenance") or "").strip():
                raise PropsLiveRoleIntelError("live primary-QB override missing provenance")
