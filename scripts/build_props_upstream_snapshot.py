from __future__ import annotations

"""Build immutable upstream inputs for LevLine Props Research Beta.

Observable lagged history is derived from nflverse. Non-observable route, availability,
efficiency and scoring assumptions must be supplied in an explicit preregistered config.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import nflreadpy as nfl
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.injuries import fetch_nfl_injuries  # noqa: E402
from nfl_forecast.props_contextual_intelligence import (  # noqa: E402
    load_levline_game_previews,
    load_levline_media_payload,
    resolve_primary_qbs_from_current_reporting,
    resolve_primary_qbs_from_levline_media,
)
from nfl_forecast.props_player_sources import (  # noqa: E402
    load_offensive_props_sources,
    normalize_snap_counts_player_ids,
    resolve_primary_qbs_from_depth_charts,
)
from nfl_forecast.props_player_state import (  # noqa: E402
    build_offensive_player_state_contract,
    flatten_current_injury_report,
    normalize_team_code,
)
from nfl_forecast.props_upstream import (  # noqa: E402
    PropsUpstreamError,
    build_empirical_scoring_context,
    build_game_upstream_package,
    build_lagged_props_history,
    fit_pre2026_efficiency_priors,
    fit_pre2026_injury_availability_priors,
    normalize_nflverse_scramble_semantics,
    residual_efficiency_by_team_from_empirical_priors,
)


def _pandas(frame):
    return frame.to_pandas() if hasattr(frame, "to_pandas") else frame.copy()


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


DEPTH_CHART_SNAPSHOT_CONTRACT = "levline-props-depth-chart-snapshot-v0.1"


def _snapshot_rank1_depth_charts(
    depth_charts: pd.DataFrame | None,
    *,
    forecast_timestamp: datetime,
) -> dict:
    """Freeze the latest qualified pregame rank-1 depth-chart rows by team/position.

    Source snapshot time and local capture time are distinct. Naive, future,
    unidentifiable, unsupported-position, and non-rank-1 rows fail closed. The
    snapshot is categorical personnel evidence only; it never asserts workload.
    """
    captured = forecast_timestamp.astimezone(timezone.utc)
    audit = {
        "status": "missing",
        "rows_received": 0,
        "invalid_timestamp_rows": 0,
        "future_rows_discarded": 0,
        "invalid_identity_rows": 0,
        "unsupported_position_rows": 0,
        "non_rank1_rows_discarded": 0,
        "superseded_rows_discarded": 0,
        "rows_frozen": 0,
        "teams_frozen": 0,
    }
    if depth_charts is None or depth_charts.empty:
        return {
            "contract_version": DEPTH_CHART_SNAPSHOT_CONTRACT,
            "captured_at_utc": captured.isoformat(),
            "depth_charts": [],
            "audit": audit,
        }

    work = depth_charts.copy()
    audit["rows_received"] = int(len(work))
    required = {"dt", "team", "gsis_id", "pos_rank"}
    missing = sorted(required - set(work.columns))
    if missing:
        audit["status"] = "unusable_missing_required_columns"
        audit["missing_columns"] = missing
        return {
            "contract_version": DEPTH_CHART_SNAPSHOT_CONTRACT,
            "captured_at_utc": captured.isoformat(),
            "depth_charts": [],
            "audit": audit,
        }

    parsed = []
    for value in work["dt"]:
        try:
            stamp = pd.Timestamp(value)
        except Exception:
            stamp = pd.NaT
        if pd.isna(stamp) or stamp.tzinfo is None:
            parsed.append(pd.NaT)
        else:
            parsed.append(stamp.tz_convert("UTC"))
    work["_dt"] = pd.to_datetime(parsed, utc=True, errors="coerce")
    audit["invalid_timestamp_rows"] = int(work["_dt"].isna().sum())

    future = work["_dt"].gt(pd.Timestamp(captured))
    audit["future_rows_discarded"] = int(future.fillna(False).sum())
    work = work[work["_dt"].notna() & ~future].copy()

    work["_team"] = work["team"].map(normalize_team_code)
    work["_id"] = work["gsis_id"].astype("string").fillna("").str.strip()
    invalid_identity = (
        work["_team"].astype("string").fillna("").str.strip().eq("")
        | work["_id"].eq("")
        | work["_id"].eq("<NA>")
        | work["_id"].str.lower().eq("nan")
    )
    audit["invalid_identity_rows"] = int(invalid_identity.sum())
    work = work[~invalid_identity].copy()

    position_col = next(
        (column for column in ("pos_abb", "position", "pos_name") if column in work.columns),
        None,
    )
    if position_col is None:
        audit["status"] = "unusable_missing_position_column"
        return {
            "contract_version": DEPTH_CHART_SNAPSHOT_CONTRACT,
            "captured_at_utc": captured.isoformat(),
            "depth_charts": [],
            "audit": audit,
        }
    work["_position"] = work[position_col].astype("string").fillna("").str.upper().str.strip()
    work["_position"] = work["_position"].replace({
        "QUARTERBACK": "QB",
        "RUNNING BACK": "RB",
        "HALFBACK": "RB",
        "WIDE RECEIVER": "WR",
        "TIGHT END": "TE",
        "HB": "RB",
    })
    supported = work["_position"].isin({"QB", "RB", "WR", "TE"})
    audit["unsupported_position_rows"] = int((~supported).sum())
    work = work[supported].copy()

    ranks = pd.to_numeric(work["pos_rank"], errors="coerce")
    rank1 = ranks.eq(1)
    audit["non_rank1_rows_discarded"] = int((~rank1).sum())
    work = work[rank1].copy()
    if work.empty:
        audit["status"] = "qualified_empty"
        return {
            "contract_version": DEPTH_CHART_SNAPSHOT_CONTRACT,
            "captured_at_utc": captured.isoformat(),
            "depth_charts": [],
            "audit": audit,
        }

    latest_by_group = work.groupby(["_team", "_position"])["_dt"].transform("max")
    superseded = work["_dt"].ne(latest_by_group)
    audit["superseded_rows_discarded"] = int(superseded.sum())
    work = work[~superseded].copy()
    work = work.sort_values(["_team", "_id", "_dt"]).drop_duplicates(
        subset=["_team", "_id", "_dt"], keep="last"
    )

    rows = []
    for _, row in work.iterrows():
        rows.append({
            "dt": row["_dt"].isoformat(),
            "capture_timestamp": captured.isoformat(),
            "team": row["_team"],
            "gsis_id": row["_id"],
            "player_id": row["_id"],
            "pos_rank": 1,
            "position": str(row["_position"]),
        })
    audit["status"] = "qualified"
    audit["rows_frozen"] = len(rows)
    audit["teams_frozen"] = len({row["team"] for row in rows})
    return {
        "contract_version": DEPTH_CHART_SNAPSHOT_CONTRACT,
        "captured_at_utc": captured.isoformat(),
        "depth_charts": rows,
        "audit": audit,
    }


def _write_new(path: Path, payload: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen upstream artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(
            _json_safe(payload),
            handle,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        handle.write("\n")


def _game_config(scoring: dict, game_id: str) -> dict:
    games = scoring.get("games")
    if isinstance(games, dict):
        value = games.get(game_id)
    else:
        value = scoring
    if not isinstance(value, dict):
        raise ValueError(f"scoring context has no object for game {game_id}")
    return value


def _game_teams(player_state, game_id: str) -> tuple[str, str, str]:
    rows = player_state[player_state["game_id"].astype(str).eq(game_id)]
    if rows.empty:
        raise ValueError(f"canonical player state has no rows for {game_id}")
    teams = sorted(set(rows["team"].map(normalize_team_code)))
    if len(teams) != 2:
        raise ValueError(f"{game_id} must have exactly two teams")
    opponent_map = {
        normalize_team_code(row["team"]): normalize_team_code(row["opponent"])
        for _, row in rows.iterrows()
    }
    home = None
    away = None
    # nflverse game IDs are typically YEAR_WEEK_AWAY_HOME; never infer home/away from
    # that string when schedule evidence is available. Caller below replaces these from schedule.
    return teams[0], teams[1], str(rows.iloc[0]["kickoff_timestamp"])


def _schedule_game(schedules, game_id: str) -> tuple[str, str, str]:
    rows = schedules[schedules["game_id"].astype(str).eq(game_id)]
    if len(rows) != 1:
        raise ValueError(f"schedule must contain exactly one row for {game_id}")
    row = rows.iloc[0]
    home = normalize_team_code(row.get("home_team"))
    away = normalize_team_code(row.get("away_team"))
    kickoff = row.get("kickoff")
    if not home or not away or kickoff is None:
        raise ValueError(f"schedule game {game_id} missing teams/kickoff")
    ts = datetime.fromisoformat(str(kickoff).replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise ValueError(f"schedule kickoff for {game_id} is not timezone-aware")
    return home, away, ts.astimezone(timezone.utc).isoformat()



def _scheduled_pregame_game_ids(
    schedules,
    *,
    season: int,
    week: int,
    forecast_timestamp: datetime,
) -> tuple[list[str], list[str]]:
    """Return upcoming target-week game IDs and already-started game IDs."""

    if "game_id" not in schedules.columns:
        raise PropsUpstreamError("schedule source missing game_id")
    work = schedules.copy()
    if "season" in work.columns:
        work = work[
            pd.to_numeric(work["season"], errors="coerce").eq(int(season))
        ].copy()
    if "week" in work.columns:
        work = work[
            pd.to_numeric(work["week"], errors="coerce").eq(int(week))
        ].copy()
    if work.empty:
        raise PropsUpstreamError(
            f"schedule source has no rows for season={season}, week={week}"
        )
    kickoff_col = next(
        (
            column
            for column in (
                "kickoff",
                "game_datetime",
                "start_time",
                "game_start",
                "datetime",
            )
            if column in work.columns
        ),
        None,
    )
    if kickoff_col is None:
        raise PropsUpstreamError("schedule source missing kickoff timestamp")
    kickoff = pd.to_datetime(work[kickoff_col], utc=True, errors="coerce")
    if kickoff.isna().any():
        bad = work.loc[kickoff.isna(), "game_id"].astype(str).tolist()
        raise PropsUpstreamError(
            f"target-week schedule has unknown kickoff timestamp: {bad}"
        )
    ids = work["game_id"].astype("string").fillna("").str.strip()
    if ids.eq("").any() or ids.duplicated().any():
        raise PropsUpstreamError("target-week schedule has missing/duplicate game_id")

    forecast = pd.Timestamp(forecast_timestamp)
    if forecast.tzinfo is None:
        raise PropsUpstreamError("forecast timestamp must be timezone-aware")
    forecast = forecast.tz_convert("UTC")
    pregame = sorted(ids[kickoff.gt(forecast)].astype(str).tolist())
    started = sorted(ids[~kickoff.gt(forecast)].astype(str).tolist())
    return pregame, started

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build frozen point-in-time upstream artifacts for LevLine Props."
    )
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument(
        "--game-id",
        nargs="+",
        help="One or more canonical game IDs from the target week.",
    )
    parser.add_argument(
        "--all-games",
        action="store_true",
        help="Build every canonical pregame player-state game in the target week.",
    )
    parser.add_argument(
        "--history-start-season",
        type=int,
        default=2024,
        help="First season loaded for strictly lagged state. This is data coverage, not tuning.",
    )
    parser.add_argument("--priors", type=Path, required=True)
    parser.add_argument(
        "--scoring-context",
        type=Path,
        help="Optional explicit scoring/residual context; otherwise derive strictly lagged context.",
    )
    parser.add_argument(
        "--levline-current-reporting",
        type=Path,
        default=ROOT / "outputs" / "game_previews.json",
        help=(
            "Sunday Signal game previews containing the persisted current_reported_sources "
            "handoff from LevLine's ranked media pass."
        ),
    )
    parser.add_argument(
        "--levline-media",
        type=Path,
        default=ROOT / "outputs" / "copilot_media_reads.json",
        help=(
            "Validated provider/Copilot media artifact retained as a secondary starter-QB "
            "fallback. Stale/missing/ambiguous entries fail closed."
        ),
    )
    parser.add_argument(
        "--skip-levline-current-reporting",
        action="store_true",
        help="Disable LevLine current-reporting starter handoff for controlled/offline research.",
    )
    parser.add_argument(
        "--skip-levline-media",
        action="store_true",
        help="Disable the provider/Copilot media fallback for controlled/offline research.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", default=".cache/nflreadpy")
    parser.add_argument(
        "--skip-injury-fetch",
        action="store_true",
        help="Use UNKNOWN availability plus explicit availability priors.",
    )
    args = parser.parse_args()

    if args.week < 1:
        raise ValueError("--week must be positive")
    if args.all_games and args.game_id:
        raise ValueError("use either --all-games or --game-id, not both")
    if not args.all_games and not args.game_id:
        raise ValueError("one of --all-games or --game-id is required")

    seasons = list(range(int(args.history_start_season), int(args.season) + 1))
    priors = _load(args.priors)
    scoring = _load(args.scoring_context) if args.scoring_context is not None else {}
    levline_current_reporting = (
        None
        if args.skip_levline_current_reporting
        else load_levline_game_previews(args.levline_current_reporting)
    )
    levline_media = (
        None
        if args.skip_levline_media
        else load_levline_media_payload(args.levline_media)
    )

    sources = load_offensive_props_sources(
        seasons=seasons,
        current_season=args.season,
        cache_dir=args.cache_dir,
    )
    identity = _pandas(nfl.load_players())
    props_pbp, pbp_normalization_audit = normalize_nflverse_scramble_semantics(
        sources.pbp
    )

    availability = None
    availability_audit = {
        "status": "skipped" if args.skip_injury_fetch else "not_attempted",
        "error": None,
    }
    if not args.skip_injury_fetch:
        try:
            injuries, source_meta = fetch_nfl_injuries(args.season, args.week)
            availability = flatten_current_injury_report(injuries, source_meta)
            availability_audit = {
                "status": "loaded",
                "provider": source_meta.get("provider"),
                "as_of": source_meta.get("as_of"),
                "source": source_meta.get("source"),
                "rows": int(len(availability)),
                "error": None,
            }
        except Exception as exc:
            availability_audit = {
                "status": "unavailable_fail_closed_to_unknown",
                "error": f"{type(exc).__name__}: {str(exc)[:240]}",
            }

    # Capture only after live-source requests complete, so no later source can masquerade
    # as knowledge available at an earlier forecast timestamp.
    forecast_timestamp = datetime.now(timezone.utc)

    state_build = build_offensive_player_state_contract(
        schedules=sources.schedules,
        roster=sources.roster,
        pbp=props_pbp,
        season=args.season,
        week=args.week,
        forecast_timestamp=forecast_timestamp.isoformat(),
        snap_counts=sources.snap_counts,
        routes=sources.routes,
        availability=availability,
    )
    player_state = state_build.player_state
    schedule_pregame_ids, started_game_ids = _scheduled_pregame_game_ids(
        sources.schedules,
        season=args.season,
        week=args.week,
        forecast_timestamp=forecast_timestamp,
    )
    state_game_ids = {
        str(value)
        for value in player_state["game_id"].dropna().astype(str)
        if str(value).strip()
    }
    missing_upcoming_state = sorted(set(schedule_pregame_ids) - state_game_ids)
    if missing_upcoming_state:
        raise PropsUpstreamError(
            "upcoming scheduled game(s) missing canonical player state: "
            f"{missing_upcoming_state}"
        )
    available_game_ids = sorted(set(schedule_pregame_ids) & state_game_ids)
    if not available_game_ids:
        raise PropsUpstreamError("canonical player state contains no scheduled pregame games")

    if args.all_games:
        game_ids = available_game_ids
    else:
        game_ids = list(dict.fromkeys(str(value) for value in args.game_id))
        invalid_games = sorted(set(game_ids) - set(available_game_ids))
        if invalid_games:
            raise PropsUpstreamError(
                "requested game_id(s) are not scheduled pregame games with canonical state: "
                f"{invalid_games}"
            )
    if len(game_ids) > 1 and scoring and not isinstance(scoring.get("games"), dict):
        raise ValueError(
            "multi-game explicit scoring context must use a top-level 'games' mapping"
        )

    history = build_lagged_props_history(
        props_pbp,
        identity,
        season=args.season,
        week=args.week,
    )

    route_priors = priors.get("route_prior_means")
    configured_availability_priors = priors.get("availability_beta_priors", {})
    if not isinstance(route_priors, dict):
        raise ValueError("priors require route_prior_means")
    if not isinstance(configured_availability_priors, dict):
        raise ValueError("availability_beta_priors must be an object when supplied")

    fitted_availability_priors: dict = {}
    availability_prior_fit_audit = {
        "status": "unavailable",
        "reason": None,
    }
    availability_fit_end = min(2024, int(args.season) - 1)
    if availability_fit_end >= 2012:
        try:
            availability_fit_seasons = list(range(2012, availability_fit_end + 1))
            historical_injuries = _pandas(nfl.load_injuries(availability_fit_seasons))
            raw_availability_snaps = _pandas(
                nfl.load_snap_counts(availability_fit_seasons)
            )
            availability_snaps, availability_snap_audit = normalize_snap_counts_player_ids(
                raw_availability_snaps,
                identity,
            )
            if availability_snaps is None or availability_snaps.empty:
                raise PropsUpstreamError(
                    "historical snap-count crosswalk produced no stable-ID rows"
                )
            availability_fit = fit_pre2026_injury_availability_priors(
                historical_injuries,
                availability_snaps,
                trained_through_season=availability_fit_end,
            )
            fitted_availability_priors = dict(
                availability_fit["availability_beta_priors"]
            )
            availability_prior_fit_audit = {
                "status": "qualified",
                "snap_identity": availability_snap_audit,
                **availability_fit["audit"],
            }
        except Exception as exc:
            availability_prior_fit_audit = {
                "status": "unavailable_fail_closed_to_explicit_config",
                "reason": f"{type(exc).__name__}: {str(exc)[:240]}",
            }
    availability_priors = {
        **fitted_availability_priors,
        **configured_availability_priors,
    }

    fitted_empirical = fit_pre2026_efficiency_priors(
        props_pbp,
        identity,
        trained_through_season=2025,
    )
    explicit_efficiency = priors.get("efficiency_position_priors")
    if explicit_efficiency is not None:
        if not isinstance(explicit_efficiency, dict):
            raise ValueError("efficiency_position_priors must be an object")
        efficiency_priors = explicit_efficiency
        trained_through = priors.get("prior_model_trained_through_season")
        if trained_through is None:
            raise ValueError(
                "explicit efficiency_position_priors require prior_model_trained_through_season"
            )
        efficiency_prior_source = "explicit_preregistered_file"
    else:
        efficiency_priors = fitted_empirical["efficiency_position_priors"]
        trained_through = fitted_empirical["trained_through_season"]
        efficiency_prior_source = "empirical_pre2026_pbp"

    source_status = str(priors.get("source_status") or "qualified").strip()
    builds: list[dict] = []

    for game_id in game_ids:
        game_config = _game_config(scoring, game_id) if scoring else {}
        game_rows = player_state[player_state["game_id"].astype(str).eq(game_id)]
        game_teams = sorted(set(game_rows["team"].map(normalize_team_code)))
        if len(game_teams) != 2:
            raise PropsUpstreamError(
                f"{game_id} must resolve to exactly two canonical teams"
            )

        depth_qbs, depth_qb_audit = resolve_primary_qbs_from_depth_charts(
            sources.depth_charts,
            player_state,
            game_id=game_id,
            forecast_timestamp=forecast_timestamp,
        )
        if args.skip_levline_current_reporting:
            current_reporting_qbs = {}
            current_reporting_qb_audit = {
                "status": "skipped",
                "game_id": game_id,
                "teams_resolved": 0,
            }
        else:
            current_reporting_qbs, current_reporting_qb_audit = (
                resolve_primary_qbs_from_current_reporting(
                    levline_current_reporting,
                    player_state,
                    game_id=game_id,
                    forecast_timestamp=forecast_timestamp,
                )
            )

        if args.skip_levline_media:
            media_qbs = {}
            media_qb_audit = {
                "status": "skipped",
                "game_id": game_id,
                "teams_resolved": 0,
            }
        else:
            media_qbs, media_qb_audit = resolve_primary_qbs_from_levline_media(
                levline_media,
                player_state,
                game_id=game_id,
                forecast_timestamp=forecast_timestamp,
            )

        explicit_scoring = game_config.get("scoring_context_by_team")
        if explicit_scoring is not None:
            if not isinstance(explicit_scoring, dict):
                raise ValueError("scoring_context_by_team must be an object")
            scoring_by_team = explicit_scoring
            scoring_source = "explicit_preregistered_file"
            empirical_scoring_audit = None
        else:
            empirical_scoring = build_empirical_scoring_context(
                props_pbp,
                teams=game_teams,
                season=args.season,
                week=args.week,
                trained_through_season=2025,
            )
            scoring_by_team = empirical_scoring["scoring_context_by_team"]
            scoring_source = "strictly_lagged_pbp"
            empirical_scoring_audit = empirical_scoring["audit"]

        explicit_residual = game_config.get("residual_efficiency_by_team")
        if explicit_residual is not None:
            if not isinstance(explicit_residual, dict):
                raise ValueError("residual_efficiency_by_team must be an object")
            residual = explicit_residual
            residual_source = "explicit_preregistered_file"
        else:
            residual = residual_efficiency_by_team_from_empirical_priors(
                game_teams,
                fitted_empirical,
            )
            residual_source = "empirical_pre2026_pbp"

        explicit_qb_overrides = game_config.get("primary_qb_by_team")
        if explicit_qb_overrides is not None and not isinstance(
            explicit_qb_overrides, dict
        ):
            raise ValueError("primary_qb_by_team must be an object when supplied")
        qb_overrides = dict(depth_qbs)
        qb_overrides.update(media_qbs)
        # Fresh deterministic LevLine reporting outranks the optional provider overlay.
        qb_overrides.update(current_reporting_qbs)
        qb_overrides.update(explicit_qb_overrides or {})

        package = build_game_upstream_package(
            player_state=player_state,
            history=history,
            game_id=game_id,
            season=args.season,
            week=args.week,
            forecast_timestamp=forecast_timestamp,
            route_prior_means=route_priors,
            availability_priors=availability_priors,
            position_efficiency_priors=efficiency_priors,
            scoring_context_by_team=scoring_by_team,
            residual_efficiency_by_team=residual,
            source_status=source_status,
            prior_model_trained_through_season=int(trained_through),
            primary_qb_by_team=qb_overrides,
        )

        home, away, kickoff = _schedule_game(sources.schedules, game_id)
        kickoff_dt = datetime.fromisoformat(kickoff)
        if forecast_timestamp >= kickoff_dt:
            raise PropsUpstreamError(f"upstream build completed at/after kickoff: {game_id}")

        builds.append(
            {
                "game_id": game_id,
                "home_team": home,
                "away_team": away,
                "kickoff_utc": kickoff,
                "package": package,
                "depth_qb_audit": depth_qb_audit,
                "current_reporting_qb_audit": current_reporting_qb_audit,
                "media_qb_audit": media_qb_audit,
                "empirical_scoring_audit": empirical_scoring_audit,
                "scoring_context_source": scoring_source,
                "residual_efficiency_source": residual_source,
            }
        )

    root = args.output_dir
    multi = len(builds) > 1
    common_player_state = root / "player_state.json"
    common_depth_charts = root / "depth_charts.json"
    slate_index = root / "upstream_slate.json"
    depth_chart_snapshot = _snapshot_rank1_depth_charts(
        sources.depth_charts,
        forecast_timestamp=forecast_timestamp,
    )
    planned: list[tuple[Path, object]] = [
        (
            common_player_state,
            {
                "contract_version": "levline-props-player-state-snapshot-v0.1",
                "captured_at_utc": forecast_timestamp.isoformat(),
                "player_state": player_state.to_dict("records"),
                "audit": {
                    **state_build.audit,
                    "pbp_source_normalization": pbp_normalization_audit,
                },
            },
        ),
        (common_depth_charts, depth_chart_snapshot),
    ]
    index_games: list[dict] = []

    for build in builds:
        game_id = build["game_id"]
        package = build["package"]
        game_root = root / "games" / game_id if multi else root
        outputs = {
            "opportunity": game_root / f"{game_id}.opportunity.json",
            "efficiency_player": game_root / f"{game_id}.efficiency_player.json",
            "team_td": game_root / f"{game_id}.team_td.json",
            "residual_efficiency": game_root / f"{game_id}.residual_efficiency.json",
            "game_spec": game_root / f"{game_id}.game_spec.json",
            "audit": game_root / f"{game_id}.upstream_audit.json",
        }
        planned.extend(
            [
                (
                    outputs["opportunity"],
                    {"opportunity_projections": list(package.opportunity_projections)},
                ),
                (
                    outputs["efficiency_player"],
                    {
                        "efficiency_player_parameters": list(
                            package.efficiency_player_parameters
                        )
                    },
                ),
                (
                    outputs["team_td"],
                    {"team_td_parameters": list(package.team_td_parameters)},
                ),
                (
                    outputs["residual_efficiency"],
                    {
                        "residual_efficiency_by_team":
                            package.residual_efficiency_by_team
                    },
                ),
                (
                    outputs["game_spec"],
                    {
                        "game_id": game_id,
                        "home_team": build["home_team"],
                        "away_team": build["away_team"],
                        "kickoff_utc": build["kickoff_utc"],
                        "upstream_forecast_timestamp_utc":
                            forecast_timestamp.isoformat(),
                    },
                ),
                (
                    outputs["audit"],
                    {
                        "research_only": True,
                        "production_authorized": False,
                        "captured_at_utc": forecast_timestamp.isoformat(),
                        "source_status": sources.source_status,
                        "pbp_source_normalization": pbp_normalization_audit,
                        "availability": availability_audit,
                        "availability_prior_fit": availability_prior_fit_audit,
                        "availability_priors_applied": availability_priors,
                        "depth_chart_primary_qb": build["depth_qb_audit"],
                        "levline_current_reporting_primary_qb":
                            build["current_reporting_qb_audit"],
                        "levline_current_reporting_source_file": (
                            None
                            if args.skip_levline_current_reporting
                            else str(args.levline_current_reporting)
                        ),
                        "levline_media_primary_qb": build["media_qb_audit"],
                        "levline_media_source_file": (
                            None
                            if args.skip_levline_media
                            else str(args.levline_media)
                        ),
                        "player_state": state_build.audit,
                        "upstream": package.audit,
                        "empirical_prior_fit": fitted_empirical["audit"],
                        "empirical_scoring_context":
                            build["empirical_scoring_audit"],
                        "efficiency_prior_source": efficiency_prior_source,
                        "scoring_context_source":
                            build["scoring_context_source"],
                        "residual_efficiency_source":
                            build["residual_efficiency_source"],
                        "priors_source_file": args.priors.name,
                        "scoring_context_source_file": (
                            args.scoring_context.name
                            if args.scoring_context is not None
                            else None
                        ),
                    },
                ),
            ]
        )
        index_games.append(
            {
                "game_id": game_id,
                "home_team": build["home_team"],
                "away_team": build["away_team"],
                "kickoff_utc": build["kickoff_utc"],
                "files": {
                    key: str(path.relative_to(root))
                    for key, path in outputs.items()
                },
            }
        )

    index_payload = {
        "contract_version": "levline-props-upstream-slate-v0.1",
        "research_only": True,
        "production_authorized": False,
        "season": int(args.season),
        "week": int(args.week),
        "captured_at_utc": forecast_timestamp.isoformat(),
        "player_state_file": str(common_player_state.relative_to(root)),
        "depth_charts_file": str(common_depth_charts.relative_to(root)),
        "game_count": len(index_games),
        "scheduled_pregame_game_count": len(schedule_pregame_ids),
        "excluded_started_game_ids": started_game_ids,
        "games": index_games,
    }
    planned.append((slate_index, index_payload))

    existing = [str(path) for path, _ in planned if path.exists()]
    if existing:
        raise FileExistsError(
            f"refusing partial overwrite; upstream output already exists: {existing}"
        )

    # No output is written until every selected game has built and every destination is
    # preflighted. This prevents a source/model failure from leaving a partial Sunday slate.
    for path, payload in planned:
        _write_new(path, payload)

    print(
        json.dumps(
            {
                "season": int(args.season),
                "week": int(args.week),
                "captured_at_utc": forecast_timestamp.isoformat(),
                "game_count": len(builds),
                "game_ids": [build["game_id"] for build in builds],
                "player_state": str(common_player_state),
                "depth_charts": str(common_depth_charts),
                "depth_chart_rows": depth_chart_snapshot["audit"]["rows_frozen"],
                "slate_index": str(slate_index),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
