"""NFLverse PBP -> frozen C football state: offline, research-only data-integrity adapter.

Does NOT fetch from network, certify a provider's clock, license or complete
publication, or return a live gateway source_verifier. A separately witnessed
pre-lock source receipt and schedule completeness audit remain mandatory.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import hashlib
import math

from research.post_week4_phase4.c_shadow import iso_utc

METRICS = ("off_epa", "def_epa_allowed")


def acquisition_evidence(payload: bytes, *, received_utc: str, asset_id: str,
                         claimed_asset_updated_utc: str | None = None) -> dict:
    """Local observations only: these fields NEVER prove provider availability."""
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("Nonempty actual response bytes required")
    observed = iso_utc(received_utc, "response received")
    if not asset_id or not isinstance(asset_id, str):
        raise ValueError("Source asset identity missing")
    if claimed_asset_updated_utc is not None:
        if iso_utc(claimed_asset_updated_utc, "provider update") > observed:
            raise ValueError("Provider update after receipt")
    return {"asset_id": asset_id, "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "response_received_utc": observed.isoformat(),
            "provider_updated_claim_utc": claimed_asset_updated_utc,
            "publication_independently_attested": False,
            "prospective_qualified": False}


def team_game_epa(pbp_rows: list[dict], games: list[dict],
                  expected_play_counts: dict[str, int]) -> dict[tuple[str, str], dict]:
    """Same off/def mean of valid REG PBP EPA as features.aggregate_team_games.

    expected_play_counts MUST originate from an independent complete provider
    manifest; self-counting PBP rows would not establish completeness.
    """
    if not isinstance(pbp_rows, list) or not isinstance(games, list) or not games:
        raise ValueError("Missing PBP or authoritative schedule")
    indexed = {}
    for g in games:
        gid = g.get("game_id")
        if (not isinstance(gid, str) or gid in indexed or
            type(g.get("season")) is not int or type(g.get("week")) is not int or
            g.get("home_team") == g.get("away_team") or
            not all(isinstance(g.get(k), str) for k in ("home_team", "away_team")) or
            g.get("game_type", "REG") != "REG"):
            raise ValueError("Duplicate, malformed or nonregular schedule game")
        iso_utc(g.get("kickoff_utc"), "kickoff")
        indexed[gid] = g
    if set(indexed) != set(expected_play_counts):
        raise ValueError("No independent per-game play manifest for entire fixture set")
    agg = defaultdict(list)
    observed = defaultdict(int)
    seen = set()
    for play in pbp_rows:
        gid = play.get("game_id")
        if gid not in indexed:
            raise ValueError("Unexpected game in PBP source")
        g = indexed[gid]
        if (play.get("season") != g["season"] or play.get("week") != g["week"] or
            play.get("home_team") != g["home_team"] or play.get("away_team") != g["away_team"]):
            raise ValueError("Mismatched season/week/team PBP identity")
        if play.get("season_type", "REG") != "REG":
            raise ValueError("Nonregular play in regular-season source")
        key = (gid, play.get("play_id"))
        if key[1] is None or key in seen:
            raise ValueError("Missing or duplicate play identity")
        seen.add(key)
        observed[gid] += 1
        off, defense = play.get("posteam"), play.get("defteam")
        epa = play.get("epa")
        # Mirrors feature aggregation: plays with no possession/defense/EPA are excluded.
        if off is None or defense is None or epa is None:
            continue
        if not isinstance(epa, (float, int)) or isinstance(epa, bool) or not math.isfinite(epa):
            raise ValueError("Invalid nonnull EPA")
        if off not in (g["home_team"], g["away_team"]) or defense not in (g["home_team"], g["away_team"]) or off == defense:
            raise ValueError("Foreign team or invalid offensive/defensive pairing")
        agg[(gid, off, "off")].append(float(epa))
        agg[(gid, defense, "def")].append(float(epa))
    for gid, n in expected_play_counts.items():
        if type(n) is not int or n <= 0 or observed[gid] != n:
            raise ValueError(f"Incomplete or revised PBP manifest for {gid}")
    out = {}
    for gid, g in indexed.items():
        for team in (g["home_team"], g["away_team"]):
            offense = agg.get((gid, team, "off"), [])
            defense = agg.get((gid, team, "def"), [])
            if not offense or not defense:
                raise ValueError(f"No valid offensive/defensive EPA for {gid}/{team}")
            out[(gid, team)] = {
                "team": team, "season": g["season"], "game_id": gid,
                "kickoff_utc": g["kickoff_utc"],
                "off_epa": sum(offense) / len(offense),
                "def_epa_allowed": sum(defense) / len(defense),
            }
    return out


def build_team_states(*, target: dict, historical_games: list[dict],
                      per_team_epa: dict, stats_observed_utc: str,
                      capture_cutoff_utc: str) -> dict:
    """Construct exact frozen-model prior-8/current-all/previous-league inputs.

    Require a SEPARATELY audited full 2025 season and all completed 2026
    fixtures. Does not assert that the supplied schedule list is complete.
    """
    cutoff = iso_utc(capture_cutoff_utc, "cutoff")
    received = iso_utc(stats_observed_utc, "source observed")
    if received > cutoff:
        raise ValueError("Provider response arrived after cutoff")
    season = target.get("season")
    if type(season) is not int or season < 2026:
        raise ValueError("Prospective season required")
    target_kickoff = iso_utc(target.get("kickoff_utc"), "target kickoff")
    if not cutoff < target_kickoff:
        raise ValueError("Target already kicked off")
    prev = season - 1
    if not isinstance(historical_games, list) or not historical_games:
        raise ValueError("Historical fixture source missing")
    teams = (target.get("home_team"), target.get("away_team"))
    all_prev = []
    selected = {t: {"prev": [], "current": []} for t in teams}
    found = set()
    for game in historical_games:
        gid, y = game.get("game_id"), game.get("season")
        if gid in found or y not in (prev, season) or gid == target.get("game_id"):
            raise ValueError("Duplicate/unqualified game or target-result leakage")
        found.add(gid)
        ko = iso_utc(game.get("kickoff_utc"), "previous kickoff")
        if ko >= received or ko >= cutoff:
            raise ValueError("Historical game not previously completed at source receipt")
        if game.get("game_type", "REG") != "REG" or game.get("completed_verified") is not True:
            raise ValueError("Nonregular or unverified completed game")
        if ko >= target_kickoff:
            raise ValueError("Future game in history")
        for team in (game["home_team"], game["away_team"]):
            metric = per_team_epa.get((gid, team))
            if metric is None or metric.get("team") != team or metric.get("season") != y:
                raise ValueError("Missing complete team-game EPA")
            row = dict(metric, stats_observed_utc=received.isoformat())
            if y == prev:
                all_prev.append(row)
            if team in selected:
                selected[team]["prev" if y == prev else "current"].append(row)
    if len({g["game_id"] for g in all_prev}) == 0:
        raise ValueError("Missing previous-season league")
    league = {m: sum(row[m] for row in all_prev) / len(all_prev) for m in METRICS}
    result = {}
    for side, team in (("home", teams[0]), ("away", teams[1])):
        if not isinstance(team, str):
            raise ValueError("Missing target team")
        hist = selected[team]
        prior = sorted(hist["prev"], key=lambda x: (x["kickoff_utc"], x["game_id"]))[-8:]
        current = sorted(hist["current"], key=lambda x: (x["kickoff_utc"], x["game_id"]))
        if len(prior) != 8:
            raise ValueError("Previous-season 8-game window unavailable")
        if len({r["game_id"] for r in current}) != len(current):
            raise ValueError("Duplicate current-game record")
        result[side] = {"team": team, "last_eight_previous_season": prior,
                        "current_season_completed": current,
                        "expected_completed_current_season_games": len(current),
                        "previous_season_league_mean": league}
    return result


def live_source_verifier_unavailable(_raw: dict) -> dict:
    """Prevent this offline adapter from being used as a gateway live proof."""
    raise RuntimeError("Independent source rights, external timestamp, schedule and PBP completeness proof not configured")
