# NFL DATA SOURCE MATRIX

The key distinction is **data useful for ex-post ability estimation** versus **data provably available pregame at prediction time**.

| Data | Primary public source(s) | Coverage / cadence notes | Ex-post training value | PIT pregame status |
|---|---|---|---|---|
| Play-by-play | nflverse `nflfastR` / `nflreadr::load_pbp()` | broad modern history; updated after game days | Excellent for team/QB/player ability, EPA, tendencies | Safe only when lagged to completed prior games |
| Rosters | nflverse releases / roster pipeline | updated regularly | identity/position history | Historical row existence alone does not prove exact as-of transaction timing; verify timestamps |
| Depth charts | nflverse | source changed after 2024; from 2025 updates use ISO timestamps | role priors | Promising prospectively; historical snapshot completeness must be verified |
| Injury/practice reports | nflverse `load_injuries()` historically | documented since 2009, but source died after 2024; no 2025 data currently in public feed | status-label research | **Major historical gap for M2**; cannot assume continuity |
| Snap counts | nflverse / PFR | game-level from 2012; polled multiple times/day | Excellent realized-role labels | Realized same-game snaps are forbidden pregame; lagged snaps can train role expectation |
| PFR advanced stats | nflverse PFR pipeline | regularly updated | ability/unit decomposition | Prior-game values okay after publication; same-game realized stats forbidden |
| Next Gen Stats | nflverse NGS pipeline | availability depends on NGS publication | tracking-derived ability metrics | Use only after published; historical revision/timestamp details need qualification |
| Participation / starters | provider / gamebook-derived datasets | often finalized after game | training labels for starter/role models | Final realized starter cannot be used at earlier pregame horizons unless confirmed then |
| Team efficiency | derived from lagged PBP | fully reproducible | M3 latent states | High feasibility if chronology is enforced |
| Coaching changes | league/team records / schedules | dates generally public | regime indicators | Feasible when announcement timestamps are recorded; avoid retroactive season labels |
| Officials | league/public assignments | announced before games | possible penalty/style context | feasible if historical announcement time retained; low priority |
| Weather forecast | provider archives required | realized station weather easy; forecast-at-horizon harder | realized weather can diagnose | Only archived forecasts at target timestamp are PIT-safe; realized weather is not |
| Stadium/surface/roof | schedules/venue records | mostly static but renovations/roof status vary | context | static venue safe; roof decision/weather-dependent status needs timestamp |
| Betting markets | see market matrix | exact timing varies by source | market null and M1 | must use snapshots at-or-before horizon |

## Critical PIT rules

1. **Realized information may train latent ability but cannot become a same-game feature.** Example: Week 5 snap counts can update a player's ability/role state for Week 6 after they were published; they cannot be used to pretend Week 5 expected role was known.
2. **Final corrected archives are not automatically PIT archives.** If a source overwrites earlier depth/status values, historical access today is ex-post.
3. **Availability lag belongs in the data contract.** A statistic produced Monday cannot be used for a Sunday game that preceded its publication.
4. **Missingness is information only if it was observable then.** Modern backfill success/failure may not equal historical live missingness.

## Phase-2 outcome-blind qualification fields

For every source/column: source identity, original timestamp, ingestion timestamp if available, revision behavior, historical coverage, update cadence, missingness by season/team, key normalization, and whether an as-of query can reconstruct the state at T-2160/T-720/T-360/T-120/T-60/close. No game result should be joined to perform this qualification.