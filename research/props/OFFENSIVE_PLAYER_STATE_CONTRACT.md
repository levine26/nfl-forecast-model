# LevLine Props Offensive Player-State Contract

Status: research beta / worker-lane handoff
Schema: `levline_props_player_state.v1`
Branch: `research/props-data`

## Purpose

Provide the canonical point-in-time offensive player-state rows consumed by the Props opportunity, efficiency/TD, and simulation lanes. This contract is deliberately independent of the failed v0.9A player-value formulation and does not modify official LevLine/F-ST winner probabilities.

## Source adapter

`src/nfl_forecast/props_player_sources.py` is the safe default source entrypoint for this lane. It reuses the repository's existing `load_core_data()` / `load_advanced_data()` paths for schedules, PBP and snap counts, loads the current roster from nflreadpy, and converts nflverse `gameday` + `gametime` into an explicit UTC `kickoff` timestamp before the contract applies its pregame guard.

The adapter intentionally returns `routes=None`. A separate point-in-time-safe route source may be supplied when available, but the Sunday sprint does not fabricate or backfill live routes from postgame participation data.

```python
from nfl_forecast.props_player_sources import load_offensive_props_sources

sources = load_offensive_props_sources(
    seasons=[2024, 2025, 2026],
    current_season=2026,
)
```

## Primary API

```python
from nfl_forecast.props_player_state import build_offensive_player_state_contract

build = build_offensive_player_state_contract(
    schedules=sources.schedules,
    roster=sources.roster,
    pbp=sources.pbp,
    season=2026,
    week=3,
    forecast_timestamp="2026-09-17T21:00:00Z",
    snap_counts=sources.snap_counts,
    routes=sources.routes,
    availability=current_timestamped_availability,
)
player_state = build.player_state
audit = build.audit
```

The existing `injuries.py` NFL.com adapter can be converted with `flatten_current_injury_report()` so its source capture time survives into the contract.

## Required identity / game fields

Each output row contains one supported offensive player for one target game:

- `game_id`
- stable `player_id` (GSIS/nflverse-compatible)
- `player_name`
- `position` (`QB`, `RB`, `WR`, `TE` only)
- `team`
- `opponent`
- `forecast_timestamp`
- `history_policy`
- `schema_version`

A stable ID conflict fails closed. Name matching is used only to resolve a timestamped current availability row against the current roster for the same team, and only when that team+normalized-name mapping is unique.

## Historical opportunity state

The v1 contract exposes last-four-game central state plus historical coverage:

- `prior_games`
- QB dropbacks / pass attempts
- rush attempts / carries
- targets / receptions
- carry share / target share
- offensive snaps / snap share when supplied
- routes / route participation when supplied from a point-in-time-safe source
- targets per route
- QB rushes per dropback
- reception rate
- red-zone carries
- goal-line carries
- red-zone targets
- end-zone targets (PBP-derived approximation from target depth reaching the goal line)

Expected role is a deterministic classification derived from lagged usage only. It is not a calibrated availability probability or a production game-probability feature.

## Point-in-time protections

### Historical state

`STRICT_PRIOR_WEEK` is intentionally conservative: for target season/week, only seasons before the target season or weeks strictly before the target week are admitted. No target-week PBP, snap, or route rows are used. This gives up same-week Thursday information in exchange for a simple leakage guarantee during the sprint.

Historical availability is never reconstructed from final participation, snaps, targets, carries or box-score presence.

### Current availability

Availability rows must have a parseable capture timestamp. Rows captured after the forecast timestamp are discarded. Rows without a timestamp are unusable. Current availability is marked `availability_prospective_only=True` unless a separate future lane produces a validated historical reconstruction.

Known target games whose kickoff timestamp is at or before the forecast timestamp are dropped from the pregame contract. The source adapter converts canonical nflverse schedule date/time fields into UTC. If another schedule source lacks a parseable kickoff timestamp, `kickoff_known=False` is exposed so publication QA can fail closed if required.

## Missing-data behavior

The contract never fabricates routes, snaps or status evidence. It exposes:

- `missing_history`
- `missing_snap_data`
- `missing_route_data`
- `missing_availability`
- `missing_red_zone_history`
- `data_quality_state` (`ENRICHED_HISTORY`, `CORE_HISTORY`, `LIMITED_NO_HISTORY`)
- source-level audit states

A player with no history can still appear with stable identity and current game mapping, but downstream models must apply their own rookie/no-history priors rather than treating nulls as observed zero usage.

## Current availability states

The contract emits conservative categorical state only:

- `OUT`
- `DOUBTFUL`
- `QUESTIONABLE`
- `AVAILABLE` only when the supplied source explicitly indicates active/available/no-injury-status
- `UNKNOWN`

Practice-only information is retained in raw fields but is not converted into an assumed absence.

## Downstream reliance

The opportunity lane may rely on:

- stable player/game/team identity
- strictly lagged PBP opportunity state
- explicit carry/target shares
- QB dropback/rush state
- optional snap/route state with missingness flags
- current availability category and source timestamp when present
- deterministic role classification
- explicit data-quality/missingness indicators

The efficiency/TD lane may additionally rely on red-zone, goal-line and end-zone opportunity history as lagged inputs, subject to its own shrinkage and validation.

The simulation lane should not infer availability probabilities directly from the categorical state without an explicit model/prior supplied by the opportunity/efficiency layers.

## Known limitations

- v1 deliberately does not solve historical 2025 injury reconstruction.
- The strict prior-week rule omits safe same-week Thursday usage until a kickoff-aware historical cutoff is implemented and validated.
- Route data is optional; when no point-in-time-safe route source is supplied, route fields remain missing rather than imputed.
- PBP end-zone targets are an approximation based on target depth relative to `yardline_100`, not a tracking-grade end-zone target source.
- Expected role thresholds are descriptive handoff classifications, not validated predictive model coefficients.

## Tests

`tests/test_props_player_state.py` covers:

- target-week leakage exclusion
- lagged QB/RB/WR/TE opportunity state
- current availability timestamp cutoff
- ambiguous identity fail-closed behavior
- explicit route/snap missingness
- known-started-game removal
- duplicate identity/schema validation
- timezone-aware forecast requirement
- flattening of the existing NFL.com injury-report adapter with capture time preserved

`tests/test_props_player_sources.py` covers:

- nflverse `gameday` + `gametime` conversion from Eastern time to UTC
- preservation/normalization of already timezone-aware kickoff values
- explicit unknown kickoff when the source lacks time fields

## Production boundary

This lane adds research-only player-state infrastructure. It does not alter, import into, or change official LevLine winner probabilities, F-ST probability logic, production thresholds, or game-pick selection.
