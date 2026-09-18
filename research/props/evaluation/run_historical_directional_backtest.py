from __future__ import annotations

"""Leakage-controlled recent-season directional backtest for LevLine Props.

The experiment contract is frozen in:
research/props/evaluation/HISTORICAL_DIRECTIONAL_ACCURACY_PREREGISTRATION.md

Sportsbook values are used only after the football simulation, except that the existence
of a pregame player market is used as the point-in-time player-population adapter and
primary-QB identity evidence. Postgame snap counts are grading-only void/participation
evidence and never enter the forecast model.
"""

import argparse
from collections import defaultdict
from datetime import timedelta
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import tempfile
from urllib.request import Request, urlopen

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.challenger_props_simulation import (  # noqa: E402
    build_game_input_from_upstream,
    evaluate_distribution,
    simulate_game,
)
from nfl_forecast.data import load_advanced_data, load_core_data  # noqa: E402
from nfl_forecast.props_player_sources import (  # noqa: E402
    add_nflverse_kickoff_timestamp,
    normalize_snap_counts_player_ids,
)
from nfl_forecast.props_player_state import SCHEMA_VERSION, normalize_team_code  # noqa: E402
from nfl_forecast.props_upstream import (  # noqa: E402
    build_empirical_scoring_context,
    build_game_upstream_package,
    build_lagged_props_history,
    fit_pre2026_efficiency_priors,
    residual_efficiency_by_team_from_empirical_priors,
)

CONTRACT_VERSION = "levline-props-historical-directional-v1.0"
SOURCE_REPOSITORY = "gcampb41/nfl_data-"
SOURCE_URL = (
    "https://raw.githubusercontent.com/gcampb41/nfl_data-/main/"
    "data/processed/football/nfl/player_props/{season}.parquet"
)
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})
HEADLINE_BET_TYPES = frozenset(
    {"passing_yards", "passing_tds", "rushing_yards", "receiving_yards", "receptions"}
)
PLAYER_POPULATION_BET_TYPES = HEADLINE_BET_TYPES | frozenset({"anytime_touchdown_scorer"})
ROUTE_PRIORS = {"RB": 0.55, "WR": 0.90, "TE": 0.75}
PRIMARY_BOOK = 30
BOOK_NAMES = {30: "OPEN", 15: "CONSENSUS", 68: "DRAFTKINGS", 69: "FANDUEL"}
TEAM_ALIASES = {
    "JAC": "JAX",
    "LA": "LAR",
    "STL": "LAR",
    "WSH": "WAS",
}
DISCRETE_PROPS = frozenset({"receptions", "passing_tds"})


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame


def _team(value) -> str:
    text = str(value or "").upper().strip()
    return normalize_team_code(TEAM_ALIASES.get(text, text))


def _valid_player_id(value) -> bool:
    try:
        if value is None or pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return bool(text) and text not in {"<NA>", "nan", "None", "null"}


def _scalar_id(value) -> str:
    return str(value).strip() if _valid_player_id(value) else ""


def _download(url: str, target: Path) -> None:
    request = Request(url, headers={"User-Agent": "LevLine-Historical-Props/1.0"})
    with urlopen(request, timeout=180) as response:
        target.write_bytes(response.read())


def load_market_source(season: int) -> tuple[pd.DataFrame, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{season}.parquet"
        _download(SOURCE_URL.format(season=season), path)
        raw = pd.read_parquet(path)

    required = {
        "bet_type",
        "event_id",
        "book_id",
        "player_id",
        "period",
        "side",
        "value",
        "odds",
        "team",
        "join_name",
        "position",
        "season",
        "week",
        "open_inferred",
    }
    missing = required - set(raw.columns)
    if missing:
        raise RuntimeError(f"historical market source missing columns: {sorted(missing)}")

    work = raw.copy()
    work["season"] = pd.to_numeric(work["season"], errors="coerce")
    work["week"] = pd.to_numeric(work["week"], errors="coerce")
    work["book_id"] = pd.to_numeric(work["book_id"], errors="coerce")
    work["event_id"] = pd.to_numeric(work["event_id"], errors="coerce")
    work["value"] = pd.to_numeric(work["value"], errors="coerce")
    work["odds"] = pd.to_numeric(work["odds"], errors="coerce")
    work["position"] = work["position"].astype("string").fillna("").str.upper().str.strip()
    work["team"] = work["team"].map(_team)
    work["bet_type"] = work["bet_type"].astype("string").fillna("").str.strip()
    work["side"] = work["side"].astype("string").fillna("").str.lower().str.strip()
    work["period"] = work["period"].astype("string").fillna("").str.lower().str.strip()
    work["player_id"] = work["player_id"].astype("string").fillna("").str.strip()
    work["open_inferred"] = work["open_inferred"].astype("boolean").fillna(False)

    work = work[
        work["season"].eq(int(season))
        & work["week"].between(1, 18)
        & work["event_id"].notna()
    ].copy()
    work["season"] = work["season"].astype(int)
    work["week"] = work["week"].astype(int)
    work["event_id"] = work["event_id"].astype(int)

    audit = {
        "source_repository": SOURCE_REPOSITORY,
        "season": int(season),
        "raw_rows": int(len(raw)),
        "regular_season_rows": int(len(work)),
        "regular_season_events": int(work["event_id"].nunique()),
        "stable_id_rows": int(work["player_id"].map(_valid_player_id).sum()),
    }
    return work, audit


def normalize_historical_pbp(pbp: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    work = pbp.copy()
    if "qb_scramble" not in work.columns or "rush_attempt" not in work.columns:
        return work, {"qb_scramble_rush_attempt_rows_normalized": 0}
    scramble = pd.to_numeric(work["qb_scramble"], errors="coerce").fillna(0).eq(1)
    rush = pd.to_numeric(work["rush_attempt"], errors="coerce").fillna(0).eq(1)
    fix = scramble & ~rush
    if fix.any():
        work.loc[fix, "rush_attempt"] = 1
    return work, {
        "qb_scramble_rush_attempt_rows_normalized": int(fix.sum()),
        "rule": "qb_scramble_1_implies_rush_attempt_1",
    }


def canonical_schedule(bundle, season: int) -> pd.DataFrame:
    schedule = add_nflverse_kickoff_timestamp(bundle.schedules)
    if "game_type" in schedule.columns:
        schedule = schedule[schedule["game_type"].astype(str).str.upper().eq("REG")].copy()
    schedule = schedule[
        pd.to_numeric(schedule["season"], errors="coerce").eq(int(season))
        & pd.to_numeric(schedule["week"], errors="coerce").between(1, 18)
    ].copy()
    schedule["season"] = pd.to_numeric(schedule["season"], errors="coerce").astype(int)
    schedule["week"] = pd.to_numeric(schedule["week"], errors="coerce").astype(int)
    schedule["home_team"] = schedule["home_team"].map(_team)
    schedule["away_team"] = schedule["away_team"].map(_team)
    schedule["kickoff"] = pd.to_datetime(schedule["kickoff"], utc=True, errors="coerce")
    schedule = schedule[
        schedule["game_id"].notna()
        & schedule["kickoff"].notna()
        & schedule["home_team"].ne("")
        & schedule["away_team"].ne("")
    ].copy()
    return schedule


def roster_metadata(
    market: pd.DataFrame,
    *,
    book_id: int,
    require_genuine_open: bool,
) -> pd.DataFrame:
    work = market[
        market["book_id"].eq(int(book_id))
        & market["position"].isin(SUPPORTED_POSITIONS)
        & market["player_id"].map(_valid_player_id)
        & market["bet_type"].isin(PLAYER_POPULATION_BET_TYPES)
    ].copy()
    if require_genuine_open:
        work = work[~work["open_inferred"].astype(bool)].copy()
    return work[
        ["event_id", "week", "player_id", "join_name", "position", "team", "bet_type"]
    ].drop_duplicates()


def map_events_to_schedule(
    roster: pd.DataFrame,
    schedule: pd.DataFrame,
) -> tuple[dict[int, dict], dict]:
    by_week_pair: dict[tuple[int, frozenset[str]], list[dict]] = defaultdict(list)
    for _, row in schedule.iterrows():
        key = (int(row["week"]), frozenset({_team(row["home_team"]), _team(row["away_team"])}))
        by_week_pair[key].append(row.to_dict())

    mapped: dict[int, dict] = {}
    reasons = defaultdict(int)
    schedule_teams = set(schedule["home_team"]) | set(schedule["away_team"])

    for event_id, rows in roster.groupby("event_id", sort=False):
        week_values = sorted(set(pd.to_numeric(rows["week"], errors="coerce").dropna().astype(int)))
        if len(week_values) != 1:
            reasons["ambiguous_event_week"] += 1
            continue
        week = week_values[0]
        teams = {
            _team(value)
            for value in rows["team"]
            if _team(value) in schedule_teams
        }
        if len(teams) != 2:
            reasons["event_not_exactly_two_schedule_teams"] += 1
            continue
        matches = by_week_pair.get((week, frozenset(teams)), [])
        if len(matches) != 1:
            reasons["event_schedule_mapping_not_unique"] += 1
            continue
        mapped[int(event_id)] = matches[0]

    return mapped, {
        "mapped_events": len(mapped),
        "unmapped_events": int(roster["event_id"].nunique() - len(mapped)),
        "unmapped_reasons": dict(reasons),
    }


def _unique_player_rows(rows: pd.DataFrame, teams: set[str]) -> tuple[pd.DataFrame, list[str]]:
    work = rows[
        rows["position"].isin(SUPPORTED_POSITIONS)
        & rows["player_id"].map(_valid_player_id)
        & rows["team"].isin(teams)
    ].copy()
    conflicts: list[str] = []
    keep: list[dict] = []
    for player_id, group in work.groupby("player_id", sort=False):
        identities = group[["team", "position"]].drop_duplicates()
        if len(identities) != 1:
            conflicts.append(str(player_id))
            continue
        first = group.iloc[0]
        keep.append(
            {
                "player_id": str(player_id),
                "player_name": str(first.get("join_name") or player_id),
                "position": str(first["position"]).upper(),
                "team": _team(first["team"]),
            }
        )
    return pd.DataFrame(keep), conflicts


def _resolve_primary_qb(event_rows: pd.DataFrame, players: pd.DataFrame, team: str) -> tuple[str | None, str]:
    qbs = set(
        players[
            players["team"].eq(team) & players["position"].eq("QB")
        ]["player_id"].astype(str)
    )
    for bet_type in ("passing_yards", "passing_tds"):
        candidates = set(
            event_rows[
                event_rows["team"].eq(team)
                & event_rows["position"].eq("QB")
                & event_rows["bet_type"].eq(bet_type)
                & event_rows["player_id"].map(_valid_player_id)
            ]["player_id"].astype(str)
        ) & qbs
        if len(candidates) == 1:
            return next(iter(candidates)), f"action_network_pregame_market_presence:{bet_type}"
    return None, "ambiguous_or_missing_pregame_qb_market"


def build_market_listed_player_state(
    event_rows: pd.DataFrame,
    schedule_row: dict,
) -> tuple[pd.DataFrame | None, dict[str, dict[str, str]], dict]:
    home = _team(schedule_row["home_team"])
    away = _team(schedule_row["away_team"])
    teams = {home, away}
    players, conflicts = _unique_player_rows(event_rows, teams)
    if players.empty:
        return None, {}, {"reason": "no_supported_market_listed_players", "identity_conflicts": conflicts}

    qb_overrides: dict[str, dict[str, str]] = {}
    for team in sorted(teams):
        qb_id, provenance = _resolve_primary_qb(event_rows, players, team)
        if qb_id is None:
            return None, {}, {
                "reason": "primary_qb_ambiguous",
                "team": team,
                "identity_conflicts": conflicts,
            }
        qb_overrides[team] = {"player_id": qb_id, "provenance": provenance}

    kickoff = pd.Timestamp(schedule_row["kickoff"])
    forecast = kickoff - pd.Timedelta(seconds=1)
    game_id = str(schedule_row["game_id"])

    rows: list[dict] = []
    for _, player in players.iterrows():
        team = str(player["team"])
        opponent = away if team == home else home
        is_primary = qb_overrides.get(team, {}).get("player_id") == str(player["player_id"])
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "game_id": game_id,
                "player_id": str(player["player_id"]),
                "player_name": str(player["player_name"]),
                "position": str(player["position"]),
                "team": team,
                "opponent": opponent,
                "kickoff_timestamp": kickoff.isoformat(),
                "forecast_timestamp": forecast.isoformat(),
                "expected_active_state": "AVAILABLE",
                "availability_source_status": "MARKET_LISTED_PREGAME",
                "expected_role": "QB_PRIMARY" if is_primary else "MARKET_LISTED",
            }
        )

    return pd.DataFrame(rows), qb_overrides, {
        "market_listed_players": len(rows),
        "identity_conflicts": conflicts,
        "forecast_timestamp_technical_anchor": forecast.isoformat(),
    }


def market_observations(
    market: pd.DataFrame,
    *,
    book_id: int,
    require_genuine_open: bool,
) -> tuple[pd.DataFrame, dict]:
    work = market[
        market["book_id"].eq(int(book_id))
        & market["bet_type"].isin(HEADLINE_BET_TYPES)
        & market["position"].isin(SUPPORTED_POSITIONS)
        & market["player_id"].map(_valid_player_id)
        & market["side"].isin({"over", "under"})
        & market["value"].notna()
        & market["odds"].notna()
    ].copy()
    if "period" in work.columns:
        work = work[work["period"].isin({"event", "game", ""})].copy()
    if require_genuine_open:
        work = work[~work["open_inferred"].astype(bool)].copy()

    if "last_updated" in work.columns:
        work = work.sort_values("last_updated")
    work = work.drop_duplicates(
        ["event_id", "player_id", "bet_type", "side"],
        keep="last",
    )

    rows: list[dict] = []
    rejected = defaultdict(int)
    for key, group in work.groupby(["event_id", "player_id", "bet_type"], sort=False):
        sides = set(group["side"])
        if sides != {"over", "under"}:
            rejected["missing_two_way_pair"] += 1
            continue
        over = group[group["side"].eq("over")]
        under = group[group["side"].eq("under")]
        if len(over) != 1 or len(under) != 1:
            rejected["duplicate_side_rows"] += 1
            continue
        over_row, under_row = over.iloc[0], under.iloc[0]
        if not math.isclose(float(over_row["value"]), float(under_row["value"]), abs_tol=1e-9):
            rejected["over_under_line_mismatch"] += 1
            continue
        position_values = sorted(set(group["position"].dropna().astype(str)))
        team_values = sorted(set(group["team"].dropna().astype(str)))
        if len(position_values) != 1 or len(team_values) != 1:
            rejected["ambiguous_market_identity"] += 1
            continue
        position = position_values[0]
        bet_type = str(key[2])
        if bet_type in {"passing_yards", "passing_tds"} and position != "QB":
            rejected["position_market_mismatch"] += 1
            continue
        if bet_type == "rushing_yards" and position not in {"QB", "RB"}:
            rejected["position_market_mismatch"] += 1
            continue
        if bet_type in {"receiving_yards", "receptions"} and position not in {"RB", "WR", "TE"}:
            rejected["position_market_mismatch"] += 1
            continue
        rows.append(
            {
                "event_id": int(key[0]),
                "player_id": str(key[1]),
                "prop_type": bet_type,
                "position": position,
                "team": team_values[0],
                "market_line": float(over_row["value"]),
                "over_odds": float(over_row["odds"]),
                "under_odds": float(under_row["odds"]),
                "book_id": int(book_id),
                "book_name": BOOK_NAMES.get(int(book_id), str(book_id)),
            }
        )

    frame = pd.DataFrame(rows)
    return frame, {
        "book_id": int(book_id),
        "book_name": BOOK_NAMES.get(int(book_id), str(book_id)),
        "require_genuine_open": bool(require_genuine_open),
        "paired_observations": int(len(frame)),
        "unique_events": int(frame["event_id"].nunique()) if not frame.empty else 0,
        "rejections": dict(rejected),
    }


def _candidate_col(frame: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    return next((name for name in names if name in frame.columns), None)


def _scalar_number(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(default)
    return number if math.isfinite(number) else float(default)


def build_game_stats_and_participation(
    pbp: pd.DataFrame,
    snap_counts: pd.DataFrame | None,
) -> tuple[dict[tuple[str, str], dict[str, float]], dict[tuple[str, str], dict[str, int]], dict]:
    stats: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {
            "passing_yards": 0.0,
            "passing_tds": 0.0,
            "rushing_yards": 0.0,
            "receiving_yards": 0.0,
            "receptions": 0.0,
        }
    )

    game_col = "game_id"
    passer_col = _candidate_col(pbp, ("passer_player_id", "passer_id"))
    rusher_col = _candidate_col(pbp, ("rusher_player_id", "rusher_id"))
    receiver_col = _candidate_col(pbp, ("receiver_player_id", "receiver_id"))
    required = {
        "game_id",
        "passing_yards",
        "rushing_yards",
        "receiving_yards",
        "complete_pass",
        "pass_touchdown",
    }
    if missing := required - set(pbp.columns):
        raise RuntimeError(f"PBP missing grading columns: {sorted(missing)}")
    if not passer_col or not rusher_col or not receiver_col:
        raise RuntimeError("PBP missing stable passer/rusher/receiver identity columns")

    for _, row in pbp.iterrows():
        game_id = str(row[game_col])
        passer = _scalar_id(row.get(passer_col))
        if _valid_player_id(passer):
            stats[(game_id, passer)]["passing_yards"] += _scalar_number(row.get("passing_yards"))
            stats[(game_id, passer)]["passing_tds"] += _scalar_number(row.get("pass_touchdown"))
        rusher = _scalar_id(row.get(rusher_col))
        if _valid_player_id(rusher):
            stats[(game_id, rusher)]["rushing_yards"] += _scalar_number(row.get("rushing_yards"))
        receiver = _scalar_id(row.get(receiver_col))
        if _valid_player_id(receiver):
            stats[(game_id, receiver)]["receiving_yards"] += _scalar_number(row.get("receiving_yards"))
            stats[(game_id, receiver)]["receptions"] += _scalar_number(row.get("complete_pass"))

    participation: dict[tuple[str, str], dict[str, int]] = {}
    snap_audit = {"available": snap_counts is not None and not snap_counts.empty}
    if snap_counts is None or snap_counts.empty:
        return dict(stats), participation, snap_audit

    snap_col = _candidate_col(snap_counts, ("offense_snaps", "offensive_snaps", "off_snaps"))
    if snap_col is None or "game_id" not in snap_counts.columns or "player_id" not in snap_counts.columns:
        snap_audit["usable"] = False
        return dict(stats), participation, snap_audit

    snaps = snap_counts.copy()
    snaps["_snaps"] = pd.to_numeric(snaps[snap_col], errors="coerce")
    snaps["_season"] = pd.to_numeric(snaps.get("season"), errors="coerce")
    snaps["_week"] = pd.to_numeric(snaps.get("week"), errors="coerce")
    snaps["player_id"] = snaps["player_id"].astype("string").fillna("").str.strip()
    snaps = snaps[
        snaps["game_id"].notna()
        & snaps["player_id"].map(_valid_player_id)
        & snaps["_snaps"].notna()
    ].copy()
    grouped = (
        snaps.groupby(["game_id", "player_id"], as_index=False, sort=False)
        .agg(offense_snaps=("_snaps", "max"), season=("_season", "max"), week=("_week", "max"))
    )
    for _, row in grouped.iterrows():
        participation[(str(row["game_id"]), str(row["player_id"]))] = {
            "offense_snaps": int(max(0.0, float(row["offense_snaps"]))),
            "season": int(row["season"]) if pd.notna(row["season"]) else -1,
            "week": int(row["week"]) if pd.notna(row["week"]) else -1,
        }

    # Positive-snap players with no PBP event still have valid zero actuals.
    for key, meta in participation.items():
        if meta["offense_snaps"] > 0 and key not in stats:
            stats[key]  # initialize zero stat row

    snap_audit.update(
        {
            "usable": True,
            "participation_rows": len(participation),
            "positive_snap_rows": sum(v["offense_snaps"] > 0 for v in participation.values()),
        }
    )
    return dict(stats), participation, snap_audit


def prior_five_average(
    stats: dict[tuple[str, str], dict[str, float]],
    participation: dict[tuple[str, str], dict[str, int]],
    *,
    player_id: str,
    season: int,
    week: int,
    prop_type: str,
) -> float | None:
    rows = []
    for (game_id, pid), meta in participation.items():
        if pid != player_id or meta.get("offense_snaps", 0) <= 0:
            continue
        period = (int(meta.get("season", -1)), int(meta.get("week", -1)))
        if period >= (int(season), int(week)):
            continue
        value = stats.get((game_id, pid), {}).get(prop_type, 0.0)
        rows.append((period, game_id, float(value)))
    if not rows:
        return None
    rows.sort(key=lambda item: (item[0][0], item[0][1], item[1]))
    return float(np.mean([value for _, _, value in rows[-5:]]))


def seed_for_game(game_id: str) -> int:
    return int.from_bytes(sha256(game_id.encode("utf-8")).digest()[:4], "big")


def wilson_interval(wins: int, losses: int) -> tuple[float | None, float | None]:
    n = int(wins + losses)
    if n <= 0:
        return None, None
    z = 1.959963984540054
    p = wins / n
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * n)) / n) / denom
    return max(0.0, center - half), min(1.0, center + half)


def summarize(rows: pd.DataFrame) -> dict:
    if rows.empty:
        return {
            "qualified": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "no_calls": 0,
            "accuracy": None,
            "wilson95": [None, None],
            "unique_games": 0,
            "unique_players": 0,
        }
    wins = int(rows["grading_result"].eq("WIN").sum())
    losses = int(rows["grading_result"].eq("LOSS").sum())
    pushes = int(rows["market_outcome"].eq("PUSH").sum())
    no_calls = int(rows["model_side"].isna().sum())
    lo, hi = wilson_interval(wins, losses)
    decided = wins + losses
    out = {
        "qualified": int(len(rows)),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "no_calls": no_calls,
        "accuracy": wins / decided if decided else None,
        "wilson95": [lo, hi],
        "unique_games": int(rows["game_id"].nunique()),
        "unique_players": int(rows["player_id"].nunique()),
        "mean_abs_fair_line_error": float(
            np.mean(np.abs(rows["fair_line"] - rows["actual_result"]))
        ) if len(rows) else None,
        "mean_abs_market_line_error": float(
            np.mean(np.abs(rows["market_line"] - rows["actual_result"]))
        ) if len(rows) else None,
        "observed_over_rate_nonpush": float(
            rows[rows["market_outcome"].isin(["OVER", "UNDER"])]["market_outcome"].eq("OVER").mean()
        ) if rows["market_outcome"].isin(["OVER", "UNDER"]).any() else None,
    }
    over_rate = out["observed_over_rate_nonpush"]
    out["majority_side_naive_accuracy"] = (
        max(over_rate, 1.0 - over_rate) if over_rate is not None else None
    )
    l5 = rows[rows["l5_side"].isin(["OVER", "UNDER"]) & rows["market_outcome"].isin(["OVER", "UNDER"])]
    out["l5_baseline_n"] = int(len(l5))
    out["l5_baseline_accuracy"] = (
        float((l5["l5_side"] == l5["market_outcome"]).mean()) if len(l5) else None
    )
    return out


def clustered_accuracy_interval(rows: pd.DataFrame, replicates: int = 5000) -> list[float | None]:
    work = rows[rows["grading_result"].isin(["WIN", "LOSS"])].copy()
    games = sorted(work["game_id"].unique()) if not work.empty else []
    if len(games) < 2:
        return [None, None]
    grouped = {game: work[work["game_id"].eq(game)] for game in games}
    rng = np.random.default_rng(20260917)
    values = []
    for _ in range(int(replicates)):
        sampled = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[g] for g in sampled], ignore_index=True)
        values.append(float(boot["grading_result"].eq("WIN").mean()))
    return [float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))]


def run(
    *,
    season: int,
    week_start: int,
    week_end: int,
    simulations: int,
    book_id: int,
    require_genuine_open: bool,
) -> tuple[pd.DataFrame, dict]:
    history_start = 2021
    seasons = list(range(history_start, int(season) + 1))
    bundle = load_core_data(seasons)
    bundle = load_advanced_data(bundle, seasons)
    pbp, pbp_normalization_audit = normalize_historical_pbp(bundle.pbp)
    players = _pandas(nfl.load_players())
    snap_counts, snap_identity_audit = normalize_snap_counts_player_ids(bundle.snap_counts, players)

    market, market_source_audit = load_market_source(season)
    market = market[market["week"].between(int(week_start), int(week_end))].copy()
    schedule = canonical_schedule(bundle, season)
    schedule = schedule[schedule["week"].between(int(week_start), int(week_end))].copy()
    roster = roster_metadata(
        market,
        book_id=book_id,
        require_genuine_open=require_genuine_open,
    )
    event_map, event_map_audit = map_events_to_schedule(roster, schedule)
    observations, market_pair_audit = market_observations(
        market,
        book_id=book_id,
        require_genuine_open=require_genuine_open,
    )
    observations = observations[observations["event_id"].isin(event_map)].copy()

    actual_stats, participation, participation_audit = build_game_stats_and_participation(
        pbp,
        snap_counts,
    )

    trained_through = int(season) - 1
    fitted_priors = fit_pre2026_efficiency_priors(
        pbp,
        players,
        trained_through_season=trained_through,
    )
    position_priors = fitted_priors["efficiency_position_priors"]

    result_rows: list[dict] = []
    exclusions = defaultdict(int)
    game_build_audit: dict[str, dict] = {}

    obs_by_event = {int(event): rows.copy() for event, rows in observations.groupby("event_id")}
    roster_by_event = {int(event): rows.copy() for event, rows in roster.groupby("event_id")}

    for week in range(int(week_start), int(week_end) + 1):
        week_obs_events = sorted(
            event for event, rows in obs_by_event.items()
            if event in event_map and int(event_map[event]["week"]) == week
        )
        if not week_obs_events:
            continue

        lagged = build_lagged_props_history(
            pbp,
            players,
            season=season,
            week=week,
        )
        week_teams = sorted(
            {
                _team(event_map[event]["home_team"])
                for event in week_obs_events
            }
            | {
                _team(event_map[event]["away_team"])
                for event in week_obs_events
            }
        )
        scoring = build_empirical_scoring_context(
            pbp,
            teams=week_teams,
            season=season,
            week=week,
            trained_through_season=trained_through,
        )["scoring_context_by_team"]

        for event_id in week_obs_events:
            schedule_row = event_map[event_id]
            game_id = str(schedule_row["game_id"])
            event_rows = roster_by_event.get(event_id)
            if event_rows is None or event_rows.empty:
                exclusions["missing_event_roster"] += len(obs_by_event[event_id])
                continue

            state, qb_overrides, state_audit = build_market_listed_player_state(
                event_rows,
                schedule_row,
            )
            if state is None:
                exclusions[str(state_audit.get("reason", "player_state_failed"))] += len(
                    obs_by_event[event_id]
                )
                game_build_audit[game_id] = state_audit
                continue

            teams = [_team(schedule_row["home_team"]), _team(schedule_row["away_team"])]
            residual = residual_efficiency_by_team_from_empirical_priors(teams, fitted_priors)
            try:
                package = build_game_upstream_package(
                    player_state=state,
                    history=lagged,
                    game_id=game_id,
                    season=season,
                    week=week,
                    forecast_timestamp=(
                        pd.Timestamp(schedule_row["kickoff"]) - pd.Timedelta(seconds=1)
                    ).isoformat(),
                    route_prior_means=ROUTE_PRIORS,
                    availability_priors={},
                    position_efficiency_priors=position_priors,
                    scoring_context_by_team=scoring,
                    residual_efficiency_by_team=residual,
                    source_status="qualified",
                    prior_model_trained_through_season=trained_through,
                    primary_qb_by_team=qb_overrides,
                )
                game_input = build_game_input_from_upstream(
                    home_team=_team(schedule_row["home_team"]),
                    away_team=_team(schedule_row["away_team"]),
                    opportunity_projections=package.opportunity_projections,
                    efficiency_player_parameters=package.efficiency_player_parameters,
                    team_td_parameters=package.team_td_parameters,
                    residual_efficiency_by_team=package.residual_efficiency_by_team,
                )
                simulation = simulate_game(
                    game_input,
                    simulations=int(simulations),
                    seed=seed_for_game(game_id),
                )
            except Exception as exc:
                exclusions[f"game_build_or_simulation:{type(exc).__name__}"] += len(
                    obs_by_event[event_id]
                )
                game_build_audit[game_id] = {
                    **state_audit,
                    "error": f"{type(exc).__name__}: {str(exc)[:400]}",
                }
                continue

            sim_players = set(simulation.player_stats)
            for _, obs in obs_by_event[event_id].iterrows():
                player_id = str(obs["player_id"])
                prop_type = str(obs["prop_type"])
                if player_id not in sim_players:
                    exclusions["market_player_not_simulated"] += 1
                    continue
                participation_meta = participation.get((game_id, player_id))
                if participation_meta is None:
                    exclusions["participation_unavailable"] += 1
                    continue
                if int(participation_meta.get("offense_snaps", 0)) <= 0:
                    exclusions["zero_offensive_snaps_void"] += 1
                    continue

                actual = float(
                    actual_stats.get((game_id, player_id), {}).get(prop_type, 0.0)
                )
                samples = simulation.player_stats[player_id][prop_type]
                dist = evaluate_distribution(
                    samples,
                    market_line=float(obs["market_line"]),
                    discrete=prop_type in DISCRETE_PROPS,
                    interval_level=0.80,
                )
                fair = float(dist.levline_fair_line)
                line = float(obs["market_line"])
                model_side = "OVER" if fair > line else "UNDER" if fair < line else None
                market_outcome = "OVER" if actual > line else "UNDER" if actual < line else "PUSH"
                grading_result = (
                    None
                    if model_side is None or market_outcome == "PUSH"
                    else "WIN"
                    if model_side == market_outcome
                    else "LOSS"
                )
                l5 = prior_five_average(
                    actual_stats,
                    participation,
                    player_id=player_id,
                    season=season,
                    week=week,
                    prop_type=prop_type,
                )
                l5_side = (
                    None
                    if l5 is None or math.isclose(l5, line, abs_tol=1e-12)
                    else "OVER"
                    if l5 > line
                    else "UNDER"
                )
                result_rows.append(
                    {
                        "contract_version": CONTRACT_VERSION,
                        "season": int(season),
                        "week": int(week),
                        "game_id": game_id,
                        "event_id": int(event_id),
                        "player_id": player_id,
                        "position": str(obs["position"]),
                        "team": str(obs["team"]),
                        "prop_type": prop_type,
                        "book_id": int(obs["book_id"]),
                        "book_name": str(obs["book_name"]),
                        "market_line": line,
                        "over_odds": float(obs["over_odds"]),
                        "under_odds": float(obs["under_odds"]),
                        "model_mean": float(dist.model_mean),
                        "fair_line": fair,
                        "model_sd": float(dist.standard_deviation),
                        "p_over": dist.p_over,
                        "p_under": dist.p_under,
                        "p_push": dist.p_push,
                        "pi_low": float(dist.prediction_interval_lower),
                        "pi_high": float(dist.prediction_interval_upper),
                        "actual_result": actual,
                        "model_side": model_side,
                        "market_outcome": market_outcome,
                        "grading_result": grading_result,
                        "l5_average": l5,
                        "l5_side": l5_side,
                        "offense_snaps": int(participation_meta["offense_snaps"]),
                        "simulations": int(simulations),
                        "seed": seed_for_game(game_id),
                        "prior_trained_through": trained_through,
                    }
                )
            game_build_audit[game_id] = {
                **state_audit,
                "simulation_players": len(sim_players),
                "opportunity_audit": package.audit,
            }

    results = pd.DataFrame(result_rows)
    summary = {
        "contract_version": CONTRACT_VERSION,
        "frozen_model_ref": "research/props-integration@db5478fd735ef0cad8fd1215e8b1fb6a96a3a21d",
        "season": int(season),
        "weeks": [int(week_start), int(week_end)],
        "simulations_per_game": int(simulations),
        "market_source": market_source_audit,
        "pbp_source_normalization": pbp_normalization_audit,
        "market_pairing": market_pair_audit,
        "event_mapping": event_map_audit,
        "snap_identity": snap_identity_audit,
        "participation": participation_audit,
        "exclusions": dict(exclusions),
        "headline": summarize(results),
        "clustered_accuracy_ci95": clustered_accuracy_interval(results),
        "by_prop": {
            str(key): summarize(group)
            for key, group in results.groupby("prop_type", sort=True)
        } if not results.empty else {},
        "by_position": {
            str(key): summarize(group)
            for key, group in results.groupby("position", sort=True)
        } if not results.empty else {},
        "by_side": {
            str(key): summarize(group)
            for key, group in results.groupby("model_side", dropna=False, sort=True)
        } if not results.empty else {},
        "game_build_count": len(game_build_audit),
        "game_build_errors": {
            game_id: audit
            for game_id, audit in game_build_audit.items()
            if audit.get("error") or audit.get("reason")
        },
    }
    return results, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run preregistered LevLine Props historical directional backtest.")
    parser.add_argument("--season", type=int, choices=(2023, 2024, 2025), required=True)
    parser.add_argument("--week-start", type=int, default=1)
    parser.add_argument("--week-end", type=int, default=18)
    parser.add_argument("--simulations", type=int, default=20_000)
    parser.add_argument("--book-id", type=int, default=PRIMARY_BOOK)
    parser.add_argument("--allow-inferred-open", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.week_start < 1 or args.week_end > 18 or args.week_start > args.week_end:
        raise ValueError("week range must be within regular-season Weeks 1-18")
    if args.simulations < 1:
        raise ValueError("--simulations must be positive")

    results, summary = run(
        season=args.season,
        week_start=args.week_start,
        week_end=args.week_end,
        simulations=args.simulations,
        book_id=args.book_id,
        require_genuine_open=(args.book_id == PRIMARY_BOOK and not args.allow_inferred_open),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.output_dir / f"{args.season}_forecast_level.csv", index=False)
    (args.output_dir / f"{args.season}_summary.json").write_text(
        json.dumps(summary, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
