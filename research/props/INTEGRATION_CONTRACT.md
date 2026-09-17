# LevLine Props — Integrated Research Beta Contract

Status: **CODE READY / LIVE MARKET FEED EXTERNAL**  
Branch: `research/props-integration`  
Forecast contract: `levline-props-forecast-v0.1`

## Integrated chain

The validated research path is:

`canonical player state -> opportunity hierarchy -> efficiency/TD parameters -> joint simulation -> Fair Lines -> frozen sportsbook comparison -> immutable forecast receipt -> publication/history/UI`.

The football simulation remains market-agnostic. Sportsbook thresholds and prices are applied only after the simulated player-stat distributions exist.

## Coordinator producer

`scripts/run_props_research_beta.py` consumes frozen upstream lane handoffs and writes:

- `outputs/props/forecasts.json` — canonical prospective forecast artifact;
- `outputs/props/public_props.json` — validated Research Beta publication payload;
- `outputs/props/history/forecast_originals.jsonl` — append-only original receipts.

The producer always attempts to lock originals before reporting success. Running at or after kickoff fails closed.

Example:

```bash
python scripts/run_props_research_beta.py --input /secure/path/props_integration_manifest.json
```

## Integration manifest

Required top-level fields:

```json
{
  "home_team": "ARI",
  "away_team": "LAR",
  "kickoff_utc": "2026-09-20T20:00:00+00:00",
  "forecast_timestamp_utc": "2026-09-17T22:00:00+00:00",
  "opportunity_projections": [],
  "efficiency_player_parameters": [],
  "team_td_parameters": [],
  "residual_efficiency_by_team": {},
  "market_artifacts": []
}
```

Optional controls are `model_version`, `simulations`, `seed`, `shared_pace_correlation`, `shared_scoring_log_sd`, `pass_rate_game_script_sensitivity`, and `prediction_interval_level`.

The opportunity projections must be the canonical `OpportunityProjection.to_dict()` handoffs. Efficiency and team-TD rows must be outputs of `build_efficiency_td_parameters`. Market artifacts must be outputs of `build_market_artifact` frozen at the prospective as-of horizon.

## Prop-name boundary

Simulation and market count models use:

- `rushing_tds`
- `receiving_tds`

The public product contract uses binary:

- `rushing_td`
- `receiving_td`

The integration adapter performs this translation only at the publication boundary. A rushing/receiving TD count market is eligible for the binary card only at a 0.5 threshold. Other TD count thresholds fail closed instead of being reinterpreted.

QB `passing_tds` remains a count Over/Under market and retains its Fair Line and full count distribution.

## No-signal receipts

Every prospective forecast row is immutable, including an explicit `NO SIGNAL` caused by missing market data. A no-signal receipt may preserve a missing market timestamp; it does not invent one. Any normal/WATCH forecast still requires a genuine pre-kickoff market timestamp.

## Data readiness

### Player data

The repository has a live-capable player-state source path through nflverse/current rosters and the existing timestamped injury adapter. Snap identity is crosswalked to stable GSIS IDs. Route data is deliberately not fabricated; when no point-in-time-safe route source is present, preregistered route priors are required by the opportunity handoff.

### Sportsbook data

The sportsbook engine and The Odds API-style parser are code-ready and fixture-validated. The repository does **not** contain or fabricate a live sportsbook credential. Prospective sportsbook comparison therefore requires an authorized live provider payload/API credential outside CI.

Stable player identity must be resolved from the canonical player-state roster. Unresolved provider names fail closed.

### Closing data

Closing prices are evaluation-only. They are never admitted to the prospective manifest or earlier forecast. They are appended after observation through the history close event.

## Production boundary

This integration is not imported by the official winner pipeline. Official LevLine/F-ST winner code remains unchanged. Props sportsbook information is not a winner-probability input.
