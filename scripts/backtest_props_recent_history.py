from __future__ import annotations

"""Chronology-clean 2023-2025 historical replay for LevLine Props.

The sportsbook threshold is applied only after the pure football simulation. Historical
Action Network OPEN rows define the evaluated market population; they are never passed
into the simulation. See research/props/evaluation/RECENT_HISTORY_BACKTEST_PROTOCOL.md.
"""

import argparse
from collections import defaultdict
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
from urllib.request import Request, urlopen

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.challenger_props_simulation import (  # noqa: E402
    DISCRETE_PROPS,
    build_game_input_from_upstream,
    evaluate_distribution,
    simulate_game,
)
from nfl_forecast.data import configure_cache  # noqa: E402
from nfl_forecast.props_market import american_to_implied  # noqa: E402
from nfl_forecast.props_player_sources import (  # noqa: E402
    add_nflverse_kickoff_timestamp,
    normalize_snap_counts_player_ids,
)
from nfl_forecast.props_player_state import (  # noqa: E402
    SCHEMA_VERSION,
    normalize_team_code,
)
from nfl_forecast.props_upstream import (  # noqa: E402
    PropsUpstreamError,
    build_empirical_scoring_context,
    build_game_upstream_package,
    build_lagged_props_history,
    fit_pre2026_efficiency_priors,
    residual_efficiency_by_team_from_empirical_priors,
)


PROP_URL = (
    "https://raw.githubusercontent.com/gcampb41/nfl_data-/main/"
    "data/processed/football/nfl/player_props/{season}.parquet"
)
SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

SUPPORTED_LINE_MARKETS = {
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions",
    "passing_tds",
}
SUPPORTED_POSITIONS = {"QB", "RB", "WR", "TE"}
ROUTE_PRIORS = {"RB": 0.55, "WR": 0.90, "TE": 0.75}
OPEN_BOOK_ID = 30
BOOTSTRAP_REPS = 5000
BOOTSTRAP_SEED = 20260918


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame.copy()


def _download(url: str, target: Path) -> None:
    req = Request(url, headers={"User-Agent": "LevLine-Props-Backtest/1.0"})
    with urlopen(req, timeout=180) as response:
        target.write_bytes(response.read())


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not math.isfinite(float(value)) else float(value)
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _valid_id(series: pd.Series) -> pd.Series:
    text = series.astype("string").fillna("").str.strip()
    return text.ne("") & text.ne("<NA>") & text.str.lower().ne("nan")


def _normalize_props(frame: pd.DataFrame, season: int) -> pd.DataFrame:
    out = frame.copy()
    out = out[pd.to_numeric(out["season"], errors="coerce").eq(int(season))].copy()
    out["week"] = pd.to_numeric(out["week"], errors="coerce").astype("Int64")
    out["event_id"] = pd.to_numeric(out["event_id"], errors="coerce").astype("Int64")
    out["book_id"] = pd.to_numeric(out["book_id"], errors="coerce").astype("Int64")
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out["odds"] = pd.to_numeric(out["odds"], errors="coerce")
    out["player_id"] = out["player_id"].astype("string").fillna("").str.strip()
    out["position"] = out["position"].astype("string").fillna("").str.upper().str.strip()
    out["team"] = out["team"].map(normalize_team_code)
    out["bet_type"] = out["bet_type"].astype("string").fillna("").str.strip()
    out["side"] = out["side"].astype("string").fillna("").str.lower().str.strip()
    out["player_name"] = (
        out["join_name"].astype("string").fillna("").str.strip()
        if "join_name" in out.columns
        else out["player_id"]
    )
    if "open_inferred" not in out.columns:
        out["open_inferred"] = False
    out["open_inferred"] = out["open_inferred"].astype("boolean").fillna(False)
    return out


def _real_open_markets(props: pd.DataFrame) -> pd.DataFrame:
    work = props[
        props["book_id"].eq(OPEN_BOOK_ID)
        & ~props["open_inferred"].astype(bool)
        & props["bet_type"].isin(SUPPORTED_LINE_MARKETS)
        & props["position"].isin(SUPPORTED_POSITIONS)
        & _valid_id(props["player_id"])
        & props["side"].isin(["over", "under"])
        & props["value"].notna()
    ].copy()
    if "period" in work.columns:
        period = work["period"].astype("string").fillna("").str.lower()
        work = work[period.isin(["", "event"])].copy()

    keys = [
        "season",
        "week",
        "event_id",
        "player_id",
        "player_name",
        "position",
        "team",
        "bet_type",
        "value",
    ]
    rows: list[dict] = []
    for key, group in work.groupby(keys, dropna=False, sort=False):
        sides = set(group["side"].astype(str))
        if not {"over", "under"}.issubset(sides):
            continue
        over = group[group["side"].eq("over")].iloc[0]
        under = group[group["side"].eq("under")].iloc[0]
        row = dict(zip(keys, key, strict=True))
        row.update(
            over_odds=float(over["odds"]) if pd.notna(over["odds"]) else math.nan,
            under_odds=float(under["odds"]) if pd.notna(under["odds"]) else math.nan,
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _event_to_game_map(
    props: pd.DataFrame,
    schedules: pd.DataFrame,
    season: int,
) -> tuple[dict[int, str], dict[str, dict]]:
    sched = schedules[pd.to_numeric(schedules["season"], errors="coerce").eq(int(season))].copy()
    sched["week"] = pd.to_numeric(sched["week"], errors="coerce").astype("Int64")
    sched["home_team"] = sched["home_team"].map(normalize_team_code)
    sched["away_team"] = sched["away_team"].map(normalize_team_code)

    map_event: dict[int, str] = {}
    audit: dict[str, dict] = {}
    for event_id, group in props.groupby("event_id", dropna=False, sort=False):
        if pd.isna(event_id):
            continue
        weeks = pd.to_numeric(group["week"], errors="coerce").dropna().astype(int).unique()
        if len(weeks) != 1:
            audit[str(event_id)] = {"status": "ambiguous_week"}
            continue
        week = int(weeks[0])
        candidate_teams = {
            normalize_team_code(v)
            for v in group["team"].dropna().astype(str)
            if normalize_team_code(v) not in {"", "FA"}
        }
        games = sched[sched["week"].eq(week)].copy()
        scored: list[tuple[int, str]] = []
        for _, row in games.iterrows():
            teams = {str(row["home_team"]), str(row["away_team"])}
            score = len(candidate_teams & teams)
            if score:
                scored.append((score, str(row["game_id"])))
        if not scored:
            audit[str(event_id)] = {
                "status": "unmatched",
                "week": week,
                "candidate_teams": sorted(candidate_teams),
            }
            continue
        scored.sort(reverse=True)
        best_score = scored[0][0]
        best = sorted(game_id for score, game_id in scored if score == best_score)
        if len(best) != 1:
            audit[str(event_id)] = {
                "status": "ambiguous_game",
                "week": week,
                "candidate_teams": sorted(candidate_teams),
                "best_score": best_score,
                "games": best,
            }
            continue
        map_event[int(event_id)] = best[0]
        audit[str(event_id)] = {
            "status": "mapped",
            "week": week,
            "candidate_teams": sorted(candidate_teams),
            "game_id": best[0],
            "overlap": best_score,
        }
    return map_event, audit


def _actual_stats(pbp: pd.DataFrame, season: int) -> dict[tuple[str, str], dict[str, float]]:
    work = pbp[pd.to_numeric(pbp["season"], errors="coerce").eq(int(season))].copy()
    out: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {
            "passing_yards": 0.0,
            "rushing_yards": 0.0,
            "receiving_yards": 0.0,
            "receptions": 0.0,
            "passing_tds": 0.0,
            "rushing_tds": 0.0,
            "receiving_tds": 0.0,
            "anytime_td": 0.0,
        }
    )

    def ids(*names: str) -> pd.Series:
        col = next((name for name in names if name in work.columns), None)
        if col is None:
            return pd.Series("", index=work.index, dtype="string")
        return work[col].astype("string").fillna("").str.strip()

    game = work["game_id"].astype("string").fillna("").str.strip()
    passer = ids("passer_player_id", "passer_id")
    rusher = ids("rusher_player_id", "rusher_id")
    receiver = ids("receiver_player_id", "receiver_id")
    complete = pd.to_numeric(work.get("complete_pass", 0), errors="coerce").fillna(0.0)
    pass_td = pd.to_numeric(work.get("pass_touchdown", 0), errors="coerce").fillna(0.0)
    rush_td = pd.to_numeric(work.get("rush_touchdown", 0), errors="coerce").fillna(0.0)

    def aggregate(pid: pd.Series, fields: dict[str, pd.Series]) -> pd.DataFrame:
        valid = _valid_id(pid) & game.ne("")
        if not bool(valid.any()):
            return pd.DataFrame()
        frame = pd.DataFrame(
            {
                "game_id": game.loc[valid].astype(str),
                "player_id": pid.loc[valid].astype(str),
                **{
                    name: pd.to_numeric(values.loc[valid], errors="coerce").fillna(0.0)
                    for name, values in fields.items()
                },
            }
        )
        return frame.groupby(["game_id", "player_id"], as_index=False, sort=False).sum(
            numeric_only=True
        )

    passing = aggregate(
        passer,
        {
            "passing_yards": pd.to_numeric(work.get("passing_yards", 0), errors="coerce").fillna(0.0),
            "passing_tds": pass_td,
        },
    )
    rushing = aggregate(
        rusher,
        {
            "rushing_yards": pd.to_numeric(work.get("rushing_yards", 0), errors="coerce").fillna(0.0),
            "rushing_tds": rush_td,
            "anytime_td": rush_td,
        },
    )
    receiving = aggregate(
        receiver,
        {
            "receiving_yards": pd.to_numeric(work.get("receiving_yards", 0), errors="coerce").fillna(0.0),
            "receptions": complete,
            "receiving_tds": pass_td,
            "anytime_td": pass_td,
        },
    )

    for frame in (passing, rushing, receiving):
        if frame.empty:
            continue
        value_cols = [c for c in frame.columns if c not in {"game_id", "player_id"}]
        for row in frame.itertuples(index=False):
            key = (str(row.game_id), str(row.player_id))
            stat = out[key]
            for column in value_cols:
                stat[column] += float(getattr(row, column))
    return out


def _participation_set(
    snap_counts: pd.DataFrame | None,
    players: pd.DataFrame,
    schedules: pd.DataFrame,
    season: int,
) -> tuple[set[tuple[str, str]], dict]:
    normalized, audit = normalize_snap_counts_player_ids(snap_counts, players)
    if normalized is None or normalized.empty:
        return set(), {**audit, "usable_for_grading": False}

    work = normalized.copy()
    work = work[pd.to_numeric(work.get("season"), errors="coerce").eq(int(season))].copy()
    offense_col = next(
        (
            c
            for c in (
                "offense_snaps",
                "offensive_snaps",
                "off_snaps",
                "offense_snap_count",
            )
            if c in work.columns
        ),
        None,
    )
    if offense_col is None:
        return set(), {**audit, "usable_for_grading": False, "reason": "missing_offense_snaps"}
    work["_off"] = pd.to_numeric(work[offense_col], errors="coerce").fillna(0)
    work = work[work["_off"].gt(0) & _valid_id(work["player_id"])].copy()

    if "game_id" in work.columns:
        pairs = set(zip(work["game_id"].astype(str), work["player_id"].astype(str)))
        return pairs, {
            **audit,
            "usable_for_grading": True,
            "offense_column": offense_col,
            "participation_pairs": len(pairs),
            "mapping": "direct_game_id",
        }

    if not {"week", "team"}.issubset(work.columns):
        return set(), {
            **audit,
            "usable_for_grading": False,
            "reason": "missing_game_id_and_week_team",
        }

    sched = schedules[pd.to_numeric(schedules["season"], errors="coerce").eq(int(season))].copy()
    sched["week"] = pd.to_numeric(sched["week"], errors="coerce").astype("Int64")
    sched["home_team"] = sched["home_team"].map(normalize_team_code)
    sched["away_team"] = sched["away_team"].map(normalize_team_code)
    team_week: dict[tuple[int, str], str] = {}
    for _, row in sched.iterrows():
        if pd.isna(row["week"]):
            continue
        for team in (str(row["home_team"]), str(row["away_team"])):
            team_week[(int(row["week"]), team)] = str(row["game_id"])

    pairs: set[tuple[str, str]] = set()
    for _, row in work.iterrows():
        try:
            week = int(row["week"])
        except (TypeError, ValueError):
            continue
        game_id = team_week.get((week, normalize_team_code(row["team"])))
        if game_id:
            pairs.add((game_id, str(row["player_id"])))
    return pairs, {
        **audit,
        "usable_for_grading": True,
        "offense_column": offense_col,
        "participation_pairs": len(pairs),
        "mapping": "season_week_team",
    }


def _market_player_state(
    event_props: pd.DataFrame,
    *,
    game_id: str,
    home_team: str,
    away_team: str,
    kickoff: pd.Timestamp,
    forecast: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, dict[str, str]]]:
    teams = {home_team, away_team}
    roster = event_props[
        event_props["position"].isin(SUPPORTED_POSITIONS)
        & _valid_id(event_props["player_id"])
        & event_props["team"].isin(teams)
    ].copy()
    roster = roster.sort_values(["team", "position", "player_id"]).drop_duplicates(
        ["team", "player_id"], keep="first"
    )

    qb_overrides: dict[str, dict[str, str]] = {}
    for team in sorted(teams):
        qbs = event_props[
            event_props["team"].eq(team)
            & event_props["position"].eq("QB")
            & event_props["bet_type"].eq("passing_yards")
            & _valid_id(event_props["player_id"])
        ]["player_id"].astype(str).unique()
        if len(qbs) != 1:
            raise PropsUpstreamError(
                f"{game_id}/{team} requires exactly one market-listed passing-yards QB; got {len(qbs)}"
            )
        qb_overrides[team] = {
            "player_id": str(qbs[0]),
            "provenance": "historical_action_network_passing_yards_market_presence",
        }

    rows: list[dict] = []
    for _, row in roster.iterrows():
        team = normalize_team_code(row["team"])
        opponent = away_team if team == home_team else home_team
        pid = str(row["player_id"])
        role = "QB_PRIMARY" if qb_overrides.get(team, {}).get("player_id") == pid else "OTHER"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "game_id": game_id,
                "player_id": pid,
                "player_name": str(row.get("player_name") or pid),
                "position": str(row["position"]),
                "team": team,
                "opponent": opponent,
                "kickoff_timestamp": kickoff.isoformat(),
                "forecast_timestamp": forecast.isoformat(),
                "expected_active_state": "AVAILABLE",
                "availability_source_status": "HISTORICAL_MARKET_LISTED",
                "expected_role": role,
            }
        )
    state = pd.DataFrame(rows)
    if state.empty:
        raise PropsUpstreamError(f"{game_id} has no supported market-listed players")
    return state, qb_overrides


def _seed(game_id: str, season: int) -> int:
    raw = hashlib.sha256(f"{season}:{game_id}".encode("utf-8")).hexdigest()
    return int(raw[:8], 16)


def _cluster_ci(frame: pd.DataFrame) -> list[float] | None:
    graded = frame[frame["graded_non_push"].astype(bool)].copy()
    if graded.empty:
        return None
    by_game = (
        graded.groupby("game_id", as_index=False)
        .agg(correct=("correct", "sum"), total=("correct", "size"))
    )
    if len(by_game) < 2:
        return None
    correct = by_game["correct"].to_numpy(dtype=float)
    total = by_game["total"].to_numpy(dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.empty(BOOTSTRAP_REPS, dtype=float)
    n = len(by_game)
    for i in range(BOOTSTRAP_REPS):
        idx = rng.integers(0, n, size=n)
        denom = float(total[idx].sum())
        draws[i] = float(correct[idx].sum() / denom) if denom else math.nan
    draws = draws[np.isfinite(draws)]
    if len(draws) == 0:
        return None
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return [float(lo), float(hi)]


def _summarize(frame: pd.DataFrame, *, season: int, simulations: int, audit: dict) -> dict:
    graded = frame[frame["graded_non_push"].astype(bool)].copy()
    pushes = int(frame["push"].fillna(False).astype(bool).sum()) if not frame.empty else 0
    ties = int(frame["model_tie"].fillna(False).astype(bool).sum()) if not frame.empty else 0
    correct = int(graded["correct"].sum()) if not graded.empty else 0
    total = int(len(graded))
    accuracy = correct / total if total else None

    def grouped(column: str) -> list[dict]:
        rows = []
        if graded.empty:
            return rows
        for key, group in graded.groupby(column, dropna=False, sort=True):
            n = int(len(group))
            c = int(group["correct"].sum())
            rows.append(
                {
                    column: None if pd.isna(key) else str(key),
                    "correct": c,
                    "total": n,
                    "accuracy": c / n if n else None,
                    "fair_line_mae": float(group["fair_abs_error"].mean()),
                    "market_line_mae": float(group["market_abs_error"].mean()),
                }
            )
        return rows

    market_baseline = graded[graded["market_predicted_side"].isin(["over", "under"])].copy()
    market_correct = (
        int((market_baseline["market_predicted_side"] == market_baseline["actual_side"]).sum())
        if not market_baseline.empty
        else 0
    )
    return {
        "protocol": "recent-history-backtest-v1",
        "season": int(season),
        "simulation_count": int(simulations),
        "headline": {
            "correct": correct,
            "incorrect": total - correct,
            "graded_non_push": total,
            "accuracy": accuracy,
            "accuracy_pct": None if accuracy is None else 100.0 * accuracy,
            "game_clustered_95_ci": _cluster_ci(frame),
            "pushes_excluded": pushes,
            "model_ties_excluded": ties,
            "games": int(graded["game_id"].nunique()) if not graded.empty else 0,
            "players": int(graded["player_id"].nunique()) if not graded.empty else 0,
            "props": total,
        },
        "error": {
            "fair_line_mae": float(graded["fair_abs_error"].mean()) if total else None,
            "market_line_mae": float(graded["market_abs_error"].mean()) if total else None,
            "fair_minus_market_mae": (
                float(graded["fair_abs_error"].mean() - graded["market_abs_error"].mean())
                if total
                else None
            ),
        },
        "opening_market_favorite_baseline": {
            "correct": market_correct,
            "total": int(len(market_baseline)),
            "accuracy": market_correct / len(market_baseline) if len(market_baseline) else None,
        },
        "by_prop_type": grouped("prop_type"),
        "by_position": grouped("position"),
        "audit": audit,
    }


def run(season: int, simulations: int, output_dir: Path, cache_dir: str, max_events: int | None = None) -> int:
    if season not in {2023, 2024, 2025}:
        raise ValueError("historical headline window is frozen to 2023-2025")
    if simulations < 1000:
        raise ValueError("simulation count must be at least 1000")

    output_dir.mkdir(parents=True, exist_ok=True)
    configure_cache(cache_dir)

    history_start = season - 2
    seasons = list(range(history_start, season + 1))
    print(f"loading nflverse seasons {seasons}")
    pbp = _pandas(nfl.load_pbp(seasons))
    players = _pandas(nfl.load_players())
    raw_snaps = _pandas(nfl.load_snap_counts([season]))
    schedules = pd.read_csv(SCHEDULE_URL, low_memory=False)
    schedules = add_nflverse_kickoff_timestamp(schedules)

    with tempfile.TemporaryDirectory() as tmp:
        prop_path = Path(tmp) / f"{season}.parquet"
        _download(PROP_URL.format(season=season), prop_path)
        props = _normalize_props(pd.read_parquet(prop_path), season)

    open_markets = _real_open_markets(props)
    event_map, event_map_audit = _event_to_game_map(props, schedules, season)
    open_markets["game_id"] = open_markets["event_id"].map(
        lambda x: event_map.get(int(x)) if pd.notna(x) else None
    )
    open_markets = open_markets[open_markets["game_id"].notna()].copy()

    actuals = _actual_stats(pbp, season)
    participation, participation_audit = _participation_set(
        raw_snaps, players, schedules, season
    )
    if not participation_audit.get("usable_for_grading"):
        raise RuntimeError(
            f"season {season} snap-count participation is not qualified: {participation_audit}"
        )

    fitted = fit_pre2026_efficiency_priors(
        pbp,
        players,
        trained_through_season=season - 1,
    )
    efficiency_priors = fitted["efficiency_position_priors"]

    sched = schedules[pd.to_numeric(schedules["season"], errors="coerce").eq(season)].copy()
    sched = sched.set_index("game_id", drop=False)

    rows: list[dict] = []
    game_failures: list[dict] = []
    mapped_events = sorted(set(int(x) for x in open_markets["event_id"].dropna().astype(int)))
    if max_events is not None:
        mapped_events = mapped_events[: int(max_events)]
    events_total = len(mapped_events)

    for n_event, event_id in enumerate(mapped_events, start=1):
        market_rows = open_markets[open_markets["event_id"].eq(event_id)].copy()
        if market_rows.empty:
            continue
        game_id = str(market_rows.iloc[0]["game_id"])
        if game_id not in sched.index:
            continue
        game_row = sched.loc[game_id]
        if isinstance(game_row, pd.DataFrame):
            game_failures.append({"event_id": event_id, "game_id": game_id, "reason": "duplicate_schedule"})
            continue
        week = int(pd.to_numeric(pd.Series([game_row["week"]]), errors="coerce").iloc[0])
        kickoff = pd.Timestamp(game_row["kickoff"])
        if pd.isna(kickoff):
            game_failures.append({"event_id": event_id, "game_id": game_id, "reason": "missing_kickoff"})
            continue
        if kickoff.tzinfo is None:
            kickoff = kickoff.tz_localize("UTC")
        else:
            kickoff = kickoff.tz_convert("UTC")
        forecast = kickoff - pd.Timedelta(hours=24)
        home = normalize_team_code(game_row["home_team"])
        away = normalize_team_code(game_row["away_team"])
        event_props = props[props["event_id"].eq(event_id)].copy()

        try:
            player_state, qb_overrides = _market_player_state(
                event_props,
                game_id=game_id,
                home_team=home,
                away_team=away,
                kickoff=kickoff,
                forecast=forecast,
            )
            history = build_lagged_props_history(
                pbp,
                players,
                season=season,
                week=week,
            )
            scoring = build_empirical_scoring_context(
                pbp,
                teams=[home, away],
                season=season,
                week=week,
                trained_through_season=season - 1,
            )
            residual = residual_efficiency_by_team_from_empirical_priors(
                [home, away],
                fitted,
            )
            package = build_game_upstream_package(
                player_state=player_state,
                history=history,
                game_id=game_id,
                season=season,
                week=week,
                forecast_timestamp=forecast,
                route_prior_means=ROUTE_PRIORS,
                availability_priors={},
                position_efficiency_priors=efficiency_priors,
                scoring_context_by_team=scoring["scoring_context_by_team"],
                residual_efficiency_by_team=residual,
                source_status="qualified",
                prior_model_trained_through_season=season - 1,
                primary_qb_by_team=qb_overrides,
            )
            game_input = build_game_input_from_upstream(
                home_team=home,
                away_team=away,
                opportunity_projections=package.opportunity_projections,
                efficiency_player_parameters=package.efficiency_player_parameters,
                team_td_parameters=package.team_td_parameters,
                residual_efficiency_by_team=package.residual_efficiency_by_team,
            )
            result = simulate_game(
                game_input,
                simulations=simulations,
                seed=_seed(game_id, season),
            )
        except Exception as exc:
            game_failures.append(
                {
                    "event_id": event_id,
                    "game_id": game_id,
                    "week": week,
                    "reason": f"{type(exc).__name__}: {str(exc)[:500]}",
                }
            )
            continue

        result_players = {p.player_id: p for p in result.players}
        for _, market in market_rows.iterrows():
            pid = str(market["player_id"])
            prop_type = str(market["bet_type"])
            if pid not in result_players:
                continue
            if prop_type not in result.player_stats.get(pid, {}):
                continue
            line = float(market["value"])
            summary = evaluate_distribution(
                result.player_stats[pid][prop_type],
                market_line=line,
                discrete=prop_type in DISCRETE_PROPS,
            )
            p_over = float(summary.p_over)
            p_under = float(summary.p_under)
            model_tie = math.isclose(p_over, p_under, abs_tol=1e-12)
            predicted_side = None if model_tie else ("over" if p_over > p_under else "under")

            participated = (game_id, pid) in participation
            actual = actuals[(game_id, pid)][prop_type] if participated else math.nan
            push = bool(participated and math.isclose(float(actual), line, abs_tol=1e-12))
            actual_side = (
                None
                if not participated or push
                else ("over" if float(actual) > line else "under")
            )
            graded = bool(participated and not push and not model_tie)
            correct = bool(graded and predicted_side == actual_side)

            over_odds = float(market["over_odds"]) if pd.notna(market["over_odds"]) else math.nan
            under_odds = float(market["under_odds"]) if pd.notna(market["under_odds"]) else math.nan
            market_predicted = None
            if math.isfinite(over_odds) and math.isfinite(under_odds):
                io = american_to_implied(over_odds)
                iu = american_to_implied(under_odds)
                if io + iu > 0 and not math.isclose(io, iu, abs_tol=1e-12):
                    market_predicted = "over" if io > iu else "under"

            rows.append(
                {
                    "season": season,
                    "week": week,
                    "event_id": event_id,
                    "game_id": game_id,
                    "player_id": pid,
                    "player": result_players[pid].player,
                    "position": result_players[pid].position,
                    "team": result_players[pid].team,
                    "opponent": result_players[pid].opponent,
                    "prop_type": prop_type,
                    "market_line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                    "model_mean": summary.model_mean,
                    "model_median": summary.model_median,
                    "fair_line": summary.levline_fair_line,
                    "model_sd": summary.standard_deviation,
                    "p_over": p_over,
                    "p_under": p_under,
                    "p_push": float(summary.p_push),
                    "predicted_side": predicted_side,
                    "model_tie": model_tie,
                    "participated": participated,
                    "actual": actual,
                    "actual_side": actual_side,
                    "push": push,
                    "graded_non_push": graded,
                    "correct": correct,
                    "fair_abs_error": (
                        abs(float(summary.levline_fair_line) - float(actual))
                        if participated
                        else math.nan
                    ),
                    "market_abs_error": abs(line - float(actual)) if participated else math.nan,
                    "market_predicted_side": market_predicted,
                }
            )
        if n_event % 25 == 0 or n_event == events_total:
            print(
                f"season {season}: processed {n_event}/{events_total} mapped events; "
                f"forecast rows={len(rows)} failures={len(game_failures)}"
            )

    frame = pd.DataFrame(rows)
    audit = {
        "source": {
            "provider": "Action Network",
            "repository": "gcampb41/nfl_data-",
            "book_id": OPEN_BOOK_ID,
            "real_open_only": True,
            "inferred_open_allowed": False,
        },
        "history_start_season": history_start,
        "prior_trained_through_season": season - 1,
        "route_priors": ROUTE_PRIORS,
        "market_rows_qualified": int(len(open_markets)),
        "mapped_events": events_total,
        "event_map_status_counts": dict(
            pd.Series([v["status"] for v in event_map_audit.values()]).value_counts()
        ),
        "participation": participation_audit,
        "game_failures": game_failures,
        "game_failure_count": len(game_failures),
        "efficiency_prior_audit": fitted["audit"],
        "no_outcomes_used_for_model_selection": True,
        "winner_model_modified": False,
    }
    summary = _summarize(frame, season=season, simulations=simulations, audit=audit)

    frame.to_csv(output_dir / f"props_backtest_{season}.csv", index=False)
    (output_dir / f"props_backtest_{season}.json").write_text(
        json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(_json_safe(summary["headline"]), indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--simulations", type=int, default=5000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("research_outputs/props_accuracy/recent_history"),
    )
    parser.add_argument("--cache-dir", default=".cache/nflreadpy")
    parser.add_argument("--max-events", type=int, default=None, help="QA smoke-test cap; never use for headline reporting")
    args = parser.parse_args()
    return run(args.season, args.simulations, args.output_dir, args.cache_dir, args.max_events)


if __name__ == "__main__":
    raise SystemExit(main())
