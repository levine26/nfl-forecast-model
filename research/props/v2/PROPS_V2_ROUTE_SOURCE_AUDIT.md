# LevLine Props 2.0 — Route / Participation Source Audit

Status: **SOURCE AUDIT — NO ROUTE MODEL PROMOTION**

## Current production/research state

The current Props upstream intentionally leaves historical `routes` missing when they cannot be
observed from play-by-play. The opportunity model can accept route participation evidence, but the
default live player-source loader explicitly fails closed because a trustworthy live in-season route
source is not guaranteed.

That behavior should remain.

## nflverse participation data

nflverse exposes play-level participation data beginning in 2016.

The published dictionary includes:
- `offense_players`: all offensive players on the field for a play;
- `offense_positions`;
- formation/personnel fields;
- pressure/coverage fields;
- `route`: the route taken by the **primary receiver** on the play.

Therefore:

1. `offense_players` can support a player-level **pass-play on-field participation** proxy by
   counting a player's presence on offensive dropback/pass plays.
2. The `route` field cannot be converted into all-player routes-run because it describes only the
   primary receiver, not every eligible receiver on the play.
3. Pass-play participation must not be labeled as routes or routes-per-dropback.

## Chronology limitation

nflverse documents that participation data from 2023 onward are supplied by FTN only **after all
postseason games are completed**. Data before 2023 come from NFL NGS.

Consequences:
- 2023 participation may be used as prior-season evidence for a 2024 research forecast;
- 2024 participation may be used as prior-season evidence for a 2025 research forecast;
- 2023+ participation cannot be treated as if it were available week-by-week during that same
  season;
- retrospective same-season route reconstruction from these files would violate the PIT standard.

Historical release timing for every older NGS season has not been established here, so older
participation is mechanism-development evidence unless separately qualified.

## Research options

### Allowed now

A new candidate may test **season-lagged pass-play participation** as a role-level proxy, clearly
named as such and never called route participation. It must be ablated against snap-based dynamic
role and evaluated as retrospective mechanism research.

### Still blocked

The preferred route/target hierarchy remains blocked on a source that can provide, pregame and
live-capable:
- all-player routes run;
- routes per team dropback;
- target rate per route;
- route alignment/type where available.

No synthetic route count may be inferred from target counts or target-game participation.

## Disposition

**DO NOT IMPLEMENT AN ALL-PLAYER ROUTE MODEL FROM THE CURRENT PARTICIPATION FILES.**

The source is useful for prior-season pass-play participation and broader personnel/scheme research,
but it does not satisfy the semantic or chronology requirements for the desired live all-player
route model.
