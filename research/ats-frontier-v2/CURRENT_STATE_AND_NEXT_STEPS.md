# CURRENT STATE AND NEXT STEPS

## Current program state

`LEVLINE_ATS_FRONTIER_V2` Phase 1 is `COMPLETE`.

The validated Phase-1 research package is merged. It reconciles prior LevLine failures, records the external evidence base, freezes a four-mechanism shortlist, defines the completed-2026 and production firewalls, and permanently records the seven-phase roadmap. No new Frontier candidate performance was inspected in Phase 1.

## Frozen Phase-1 shortlist

- `FRONTIER-M1-DYNAMIC-MARKET-STATE` — highest market-information/data priority.
- `FRONTIER-M2-PLAYER-STATE-DELTA` — highest non-market information priority and principal historical PIT-data risk.
- `FRONTIER-M3-HIERARCHICAL-STATE` — dynamic temporal-state replacement for fixed rolling summaries.
- `FRONTIER-M4-DISCRETE-MARGIN-V2` — tail-safe integer probability representation; not presumed to contain independent alpha.

## Phase 2 status

`NOT_STARTED`.

A future Phase-2 execution must remain outcome-blind and begin with data qualification/PIT reconstruction, not modeling.

### First authorized actions

1. Obtain sample historical multi-book NFL spread + side-price + moneyline + total records from the strongest candidate sources and verify snapshot semantics, timestamps, bookmaker identity continuity, missingness, opening/closing definitions and joins.
2. Build a player/QB PIT feasibility audit covering injury/practice-report timestamps, depth-chart snapshots, roster changes, starter probabilities, expected role/snap information and replacement candidates.
3. Establish a provenance table showing exactly when every potential feature became knowable and whether revisions are reconstructable.
4. Quantify coverage and missingness only. Do not calculate Frontier proper scores, ATS hit rates, ROI, or candidate-vs-market target performance.
5. Mark each Phase-1 mechanism `DATA_QUALIFIED` or `DATA_INFEASIBLE` before Phase 3.

## Recommended source qualification order

1. The Odds API and SportsDataIO samples for historical timestamped multi-book market-state reconstruction.
2. PropLine for schema/prospective history qualification where current access permits.
3. nflverse and directly sourced roster/depth/injury/transaction materials for player/QB state, with explicit attention to injury-source discontinuity after 2024.
4. Existing nflverse schedule odds remain a horizon-opaque benchmark only; they are not relabeled as T-120/T-60/etc.

No data purchase is authorized by Phase 1. Historical multi-book odds is the only paid-data category currently judged plausibly material enough to justify a later purchase decision after sample qualification.

## Mandatory future-chat read order

Before Phase 2 begins, read:

1. `MASTER_PLAN.md`
2. `PHASE_STATUS.md`
3. `CURRENT_STATE_AND_NEXT_STEPS.md`
4. `DECISION_LOG.md`
5. `FINAL_PHASE1_RECEIPT.md`
6. `EVIDENCE_BOUNDARY.md`
7. `MARKET_DATA_SOURCE_MATRIX.md`
8. `NFL_DATA_SOURCE_MATRIX.md`
9. `DATA_FEASIBILITY_PREVIEW.md`

Do not restart Phase 1. Do not resurrect killed hypotheses without a formal pre-result governance amendment.