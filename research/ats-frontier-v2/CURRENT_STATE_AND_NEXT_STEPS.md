# CURRENT STATE AND NEXT STEPS

## Current scientific state

The prior LevLine program family has generated unusually useful negative evidence. Independent football-state models A0 and B0 were materially less accurate than the market in 2025; C0 did not establish incremental information; Candidate 5 residual stacking made zero winner changes; ATS-Q1 and ATS-Q3 failed their market-relative proper-score tests; ATS-Q2 V1 was numerically invalid under its finite-support contract; Adaptive Candidate 3 could not separate path information from later market level.

The implication is not that forecasting beyond the market is impossible. It is that a new program must pay for genuinely new information, point-in-time fidelity, or state representation—not more algorithms over substantially the same signal set.

## Phase-1 shortlist

- M1 dynamic multi-book latent market state — highest data priority.
- M2 player/QB information-delta — highest non-market information priority.
- M3 hierarchical latent team/unit state — strongest temporal-state replacement for fixed rolling windows.
- M4 discrete margin V2 — strongest probability-representation research path, but not independently presumed to contain edge.

## Immediate next action after Phase-1 closeout

Phase 2 must begin with an outcome-blind data qualification gate, in this order:

1. Obtain a sample of timestamped historical multi-book NFL spread + side-price + moneyline + total data and verify snapshot semantics, book identity continuity, timestamps, opening/closing definitions, missingness and game joins.
2. Build a PIT player-state feasibility table: injury/practice report timestamps, depth-chart snapshots, roster changes, starter probabilities, expected role/snap information and replacement candidates.
3. Validate that each candidate feature can be computed strictly from records available by its prediction timestamp; label any source that cannot satisfy this contract unusable.
4. Quantify coverage and missingness only. Do not join game outcomes or calculate candidate ATS/proper-score performance.
5. Eliminate candidates whose required data are not reproducibly available before writing Phase-3 preregistrations.

## Recommended market-data acquisition order

1. Use free/current PropLine and existing LevLine sources for schema/prospective qualification.
2. Request samples/quotes from The Odds API and SportsDataIO for historical timestamped multi-book movement. The Odds API is the cleanest documented self-service archive (featured-market snapshots from 2020; 5-minute snapshots from Sep-2022), while SportsDataIO explicitly retains line-movement revision history across 20+ books.
3. Treat nflverse schedule odds only as a benchmark with opaque historical horizon, not as dynamic-market evidence.
4. Do not buy anything in Phase 1. A paid historical odds source becomes justified only after a sample proves the exact PIT fields required by M1.

## Stop boundary

No Phase-2 ingestion, candidate construction, fitting or performance inspection is authorized until Phase 1 is merged and the final receipt is immutable.