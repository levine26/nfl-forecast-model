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
from nfl_forecast.props_player_sources import load_offensive_props_sources  # noqa: E402
from nfl_forecast.props_player_state import (  # noqa: E402
    build_offensive_player_state_contract,
    flatten_current_injury_report,
    normalize_team_code,
)
from nfl_forecast.props_upstream import (  # noqa: E402
    PropsUpstreamError,
    build_game_upstream_package,
    build_lagged_props_history,
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
    parser.add_argument("--scoring-context", type=Path, required=True)
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
    scoring = _load(args.scoring_context)

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

    history = build_lagged_props_history(
        sources.pbp,
        identity,
        season=args.season,
        week=args.week,
    )

    game_config = _game_config(scoring, args.game_id)
    scoring_by_team = game_config.get("scoring_context_by_team")
    residual = game_config.get("residual_efficiency_by_team")
    if not isinstance(scoring_by_team, dict):
        raise ValueError("game scoring context requires scoring_context_by_team")
    if not isinstance(residual, dict):
        raise ValueError("game scoring context requires residual_efficiency_by_team")

    route_priors = priors.get("route_prior_means")
    availability_priors = priors.get("availability_beta_priors")
    efficiency_priors = priors.get("efficiency_position_priors")
    if not isinstance(route_priors, dict):
        raise ValueError("priors require route_prior_means")
    if not isinstance(availability_priors, dict):
        raise ValueError("priors require availability_beta_priors")
    if not isinstance(efficiency_priors, dict):
        raise ValueError("priors require efficiency_position_priors")

    source_status = str(priors.get("source_status") or "").strip()
    trained_through = priors.get("prior_model_trained_through_season")
    if trained_through is None:
        raise ValueError("priors require prior_model_trained_through_season")
    qb_overrides = game_config.get("primary_qb_by_team")
    if qb_overrides is not None and not isinstance(qb_overrides, dict):
        raise ValueError("primary_qb_by_team must be an object when supplied")

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
            "player_state": state_build.audit,
            "upstream": package.audit,
            "priors_source_file": args.priors.name,
            "scoring_context_source_file": args.scoring_context.name,
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
