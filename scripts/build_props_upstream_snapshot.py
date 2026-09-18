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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build frozen point-in-time upstream artifacts for LevLine Props."
    )
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--game-id", required=True)
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
    seasons = list(range(int(args.history_start_season), int(args.season) + 1))
    priors = _load(args.priors)
    scoring = _load(args.scoring_context) if args.scoring_context is not None else {}

    sources = load_offensive_props_sources(
        seasons=seasons,
        current_season=args.season,
        cache_dir=args.cache_dir,
    )
    identity = _pandas(nfl.load_players())
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

    # The forecast timestamp is captured only after every live source request above has
    # completed. This prevents a source fetched later from masquerading as an earlier state.
    forecast_timestamp = datetime.now(timezone.utc)

    state_build = build_offensive_player_state_contract(
        schedules=sources.schedules,
        roster=sources.roster,
        pbp=sources.pbp,
        season=args.season,
        week=args.week,
        forecast_timestamp=forecast_timestamp.isoformat(),
        snap_counts=sources.snap_counts,
        routes=sources.routes,
        availability=availability,
    )
    player_state = state_build.player_state
    depth_qbs, depth_qb_audit = resolve_primary_qbs_from_depth_charts(
        sources.depth_charts,
        player_state,
        game_id=args.game_id,
        forecast_timestamp=forecast_timestamp,
    )

    history = build_lagged_props_history(
        sources.pbp,
        identity,
        season=args.season,
        week=args.week,
    )

    game_config = _game_config(scoring, args.game_id) if scoring else {}
    game_rows = player_state[player_state["game_id"].astype(str).eq(str(args.game_id))]
    game_teams = sorted(set(game_rows["team"].map(normalize_team_code)))
    if len(game_teams) != 2:
        raise ValueError(f"{args.game_id} must resolve to exactly two teams")

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
            raw_availability_snaps = _pandas(nfl.load_snap_counts(availability_fit_seasons))
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
        sources.pbp,
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

    explicit_scoring = game_config.get("scoring_context_by_team")
    if explicit_scoring is not None:
        if not isinstance(explicit_scoring, dict):
            raise ValueError("scoring_context_by_team must be an object")
        scoring_by_team = explicit_scoring
        scoring_source = "explicit_preregistered_file"
        empirical_scoring_audit = None
    else:
        empirical_scoring = build_empirical_scoring_context(
            sources.pbp,
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
    if explicit_qb_overrides is not None and not isinstance(explicit_qb_overrides, dict):
        raise ValueError("primary_qb_by_team must be an object when supplied")
    qb_overrides = dict(depth_qbs)
    qb_overrides.update(explicit_qb_overrides or {})

    package = build_game_upstream_package(
        player_state=player_state,
        history=history,
        game_id=args.game_id,
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

    home, away, kickoff = _schedule_game(sources.schedules, args.game_id)
    if forecast_timestamp >= datetime.fromisoformat(kickoff):
        raise PropsUpstreamError("upstream build completed at/after kickoff")

    root = args.output_dir
    stem = args.game_id
    outputs = {
        "player_state": root / "player_state.json",
        "opportunity": root / f"{stem}.opportunity.json",
        "efficiency_player": root / f"{stem}.efficiency_player.json",
        "team_td": root / f"{stem}.team_td.json",
        "residual_efficiency": root / f"{stem}.residual_efficiency.json",
        "game_spec": root / f"{stem}.game_spec.json",
        "audit": root / f"{stem}.upstream_audit.json",
    }
    if any(path.exists() for path in outputs.values()):
        existing = [str(path) for path in outputs.values() if path.exists()]
        raise FileExistsError(f"refusing partial overwrite; output already exists: {existing}")

    _write_new(
        outputs["player_state"],
        {
            "contract_version": "levline-props-player-state-snapshot-v0.1",
            "captured_at_utc": forecast_timestamp.isoformat(),
            "player_state": player_state.to_dict("records"),
            "audit": state_build.audit,
        },
    )
    _write_new(
        outputs["opportunity"],
        {"opportunity_projections": list(package.opportunity_projections)},
    )
    _write_new(
        outputs["efficiency_player"],
        {"efficiency_player_parameters": list(package.efficiency_player_parameters)},
    )
    _write_new(
        outputs["team_td"],
        {"team_td_parameters": list(package.team_td_parameters)},
    )
    _write_new(
        outputs["residual_efficiency"],
        {"residual_efficiency_by_team": package.residual_efficiency_by_team},
    )
    _write_new(
        outputs["game_spec"],
        {
            "game_id": args.game_id,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": kickoff,
            "upstream_forecast_timestamp_utc": forecast_timestamp.isoformat(),
        },
    )
    _write_new(
        outputs["audit"],
        {
            "research_only": True,
            "production_authorized": False,
            "captured_at_utc": forecast_timestamp.isoformat(),
            "source_status": sources.source_status,
            "availability": availability_audit,
            "availability_prior_fit": availability_prior_fit_audit,
            "availability_priors_applied": availability_priors,
            "depth_chart_primary_qb": depth_qb_audit,
            "player_state": state_build.audit,
            "upstream": package.audit,
            "empirical_prior_fit": fitted_empirical["audit"],
            "empirical_scoring_context": empirical_scoring_audit,
            "efficiency_prior_source": efficiency_prior_source,
            "scoring_context_source": scoring_source,
            "residual_efficiency_source": residual_source,
            "priors_source_file": args.priors.name,
            "scoring_context_source_file": (
                args.scoring_context.name if args.scoring_context is not None else None
            ),
        },
    )

    print(
        json.dumps(
            {
                "game_id": args.game_id,
                "captured_at_utc": forecast_timestamp.isoformat(),
                "outputs": {key: str(value) for key, value in outputs.items()},
                "opportunity_projections": len(package.opportunity_projections),
                "efficiency_player_parameters": len(package.efficiency_player_parameters),
                "team_td_parameters": len(package.team_td_parameters),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
