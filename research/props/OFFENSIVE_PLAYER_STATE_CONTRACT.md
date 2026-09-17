# LevLine Props Offensive Player-State Contract

Status: research beta / worker-lane handoff
Schema: `levline_props_player_state.v1`
Branch: `research/props-data`

## Purpose

Provide the canonical point-in-time offensive player-state rows consumed by the Props opportunity, efficiency/TD, and simulation lanes. This contract is deliberately independent of the failed v0.9A player-value formulation and does not modify official LevLine/F-ST winner probabilities.

## Source adapter

`src/nfl_forecast/props_player_sources.py` is the safe default source entrypoint for this lane. It reuses the repository's existing `load_core_data()` / `load_advanced_data()` paths for schedules, PBP and snap counts, loads the current roster from nflreadpy, and converts nflverse `gameday` + `gametime` into an explicit UTC `kickoff` timestamp before the contract applies its pregame guard.

The adapter intentionally returns `routes=None`. A separate point-in-time-safe route source may be supplied when available, but the Sunday sprint does not fabricate or backfill live routes from postgame participation data.

Kickoff timestamps must have an explicit timezone before the contract will treat them as known. The nflverse adapter derives `gameday + gametime` in `America/New_York` and converts to UTC. A naive standalone `kickoff` value is treated as unknown rather than silently assumed to be UTC.

nflverse snap counts are PFR-sourced and may identify players with `pfr_player_id` rather than the GSIS IDs used by PBP and rosters. The adapter therefore crosswalks PFR IDs to `gsis_id` through nflverse player identity data. A PFR ID that maps to multiple GSIS IDs is discarded, an unmapped row remains missing, and a snap source with no safely mapped rows fails closed instead of being reported as usable.

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
- `kickoff_timestamp` plus `kickoff_known`
- `forecast_timestamp`
- `history_policy`
- `roster_status_raw` plus `roster_membership_state`
- timestamped availability provenance/raw status fields (nullable when unavailable)
- `schema_version`

A stable ID conflict fails closed. Name matching is used only to resolve a timestamped current availability row against the current roster for the same team, and only when that team+normalized-name mapping is unique.

When nflverse season-level roster data exposes a status field, clearly released/non-roster states (for example CUT/UFA/RFA/released/retired) are excluded before identity validation. Contracted reserve, PUP, suspended, inactive and practice-squad players remain visible with raw `roster_status_raw` plus `roster_membership_state`; those fields are context only and are not silently converted into an injury-derived availability probability.

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

Expected role is a deterministic classification derived from lagged usage only. It is not a calibrated availability probability or a production game-probability feature. If participation history exists but the relevant PBP-derived usage evidence is missing, the role fails closed to `UNKNOWN_NO_USAGE_HISTORY` instead of treating missing dropbacks/carry share/target share as zero.

## Point-in-time protections

### Historical state

`STRICT_PRIOR_WEEK` is intentionally conservative: for target season/week, only seasons before the target season or weeks strictly before the target week are admitted. No target-week PBP, snap, or route rows are used. This gives up same-week Thursday information in exchange for a simple leakage guarantee during the sprint.

Historical availability is never reconstructed from final participation, snaps, targets, carries or box-score presence.

Participation data can be published for a period whose PBP is unavailable. In that case the contract preserves PBP-derived usage as missing rather than filling it with zero. A zero carry/target/dropback value is created only when the relevant historical game has PBP coverage.

### Current availability

Availability rows must have an explicitly timezone-aware capture timestamp. Naive or unparseable timestamps are unusable rather than being assumed to be UTC, and rows captured after the forecast timestamp are discarded. Current availability is marked `availability_prospective_only=True` unless a separate future lane produces a validated historical reconstruction.

Known target games whose kickoff timestamp is at or before the forecast timestamp are dropped from the pregame contract. The source adapter converts canonical nflverse schedule date/time fields into UTC. If another schedule source lacks a timezone-aware kickoff timestamp, including a naive timestamp whose timezone is ambiguous, `kickoff_known=False` is exposed so publication QA can fail closed if required.

## Missing-data behavior

The contract never fabricates routes, snaps or status evidence. It exposes:

- `missing_history`
- `missing_usage_history` (no lagged PBP-derived opportunity evidence)
- `missing_snap_data`
- `missing_route_data`
- `missing_availability`
- `missing_red_zone_history`
- `data_quality_state` (`ENRICHED_HISTORY`, `CORE_HISTORY`, `LIMITED_NO_HISTORY`)
- source-level audit states

A player with no history can still appear with stable identity and current game mapping, but downstream models must apply their own rookie/no-history priors rather than treating nulls as observed zero usage.

Validation requires the canonical identity, kickoff/PIT, roster-membership, availability-provenance, usage, missingness and quality columns even when their values are nullable. It also rejects unexpected schema/history-policy values, invalid roster-membership states, invalid quality states and any disagreement between `kickoff_known` and the parsed kickoff timestamp.

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
- current roster membership context without treating roster status as a calibrated availability probability
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
- released/free-agent roster filtering while retaining explicit reserve membership state
- transaction-like duplicate roster rows not creating false identity conflicts after released rows are removed
- current availability timestamp cutoff
- naive availability timestamps failing closed instead of being assumed UTC
- missing usage history producing `UNKNOWN_NO_USAGE_HISTORY` rather than a fabricated reserve/rotation role
- ambiguous identity fail-closed behavior
- explicit route/snap missingness
- known-started-game removal
- duplicate identity/schema validation
- canonical roster-membership validation
- timezone-aware forecast requirement
- flattening of the existing NFL.com injury-report adapter with capture time preserved

`tests/test_props_player_sources.py` covers:

- nflverse `gameday` + `gametime` conversion from Eastern time to UTC
- preservation/normalization of already timezone-aware kickoff values
- explicit unknown kickoff when the source lacks time fields
- naive standalone kickoff values failing closed instead of being assumed UTC
- fallback to nflverse Eastern `gameday + gametime` when a naive `kickoff` field is present
- PFR-to-GSIS snap-count identity crosswalk
- ambiguous PFR identity fail-closed behavior
- snap rows with no supported stable identity failing closed

`tests/test_props_player_state.py` additionally verifies that snap-only periods without PBP do not fabricate zero opportunities or dilute observed target/carry/dropback history.

## Production boundary

This lane adds research-only player-state infrastructure. It does not alter, import into, or change official LevLine winner probabilities, F-ST probability logic, production thresholds, or game-pick selection.
