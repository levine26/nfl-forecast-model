# Props 2.0 Route / Target Engine — Source Audit Contract

Status: **ACTIVE SOURCE AUDIT / LIVE ROUTE DATA BLOCKER IDENTIFIED**  
Candidate: `P2-ROUTE-TARGET`  
Version: `levline-props-v2-route-target-source-audit-v0.1.0`

## Research question

Can repository-accessible historical participation data support a scientifically defensible
route/target hierarchy, and which pieces can later be reproduced from information actually
available in-season?

## Release-latency boundary

nflverse documents `load_participation()` as historical play-level participation. Data before
2023 is sourced from NFL NGS. Data from 2023 onward is supplied by FTN and is documented as being
provided only after all postseason games are completed.

Therefore:

- 2023–2025 participation may be used for retrospective mechanism/proxy development;
- it may **not** be represented as information that LevLine would have possessed before those games;
- it cannot be used as a live 2026 route feature;
- a proxy trained on historical participation must use only live-compatible inputs at deployment;
- later postseason backfills may grade a pre-frozen 2026 proxy, but may not rewrite the original
  pregame feature state.

Sources:
- https://github.com/nflverse/nflreadr/blob/main/R/load_participation.R
- https://github.com/nflverse/nflreadpy

## Semantic boundary

The schema audit inventories fields. It does not call "offensive player on the field during a
dropback" a route unless source documentation explicitly says the field represents a route.

A blocker is preferable to inventing route counts.

## Next decision

If the schema supports a credible historical on-field/dropback participation target, build a
separate proxy experiment using only deployable predictors such as lagged snap share, position,
team dropbacks, target history, depth-chart state, and timestamp-qualified personnel context.

If it exposes documented route fields, audit their provenance and release latency separately before
use.

No prop outcomes or completed 2026 outcomes are part of this source audit.
