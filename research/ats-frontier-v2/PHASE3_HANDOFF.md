# PHASE 3 HANDOFF

Phase 3 is **Final Architecture Design & Preregistration**. It must not begin until Phase 2 is merged and its gate is authoritative.

## Qualified inputs to Phase 3

### M1 — partial; free-first reconstruction required

- Public provider-origin historical The Odds API cache material has been verified across 2020–2024, preserving timestamps, books, h2h/spread/total, point and price. The bulk cache is sparse and some requested times can be equal/post-kick, so row-level strict pre-kick validation is mandatory.
- A public 2025 DuckDB corpus documents dense real multi-book data: 1.8M+ rows, 636 snapshots, four captures/day, 30+ operators. Exact frozen-horizon coverage still must be measured rather than assumed.
- Australia Sports Betting and SportsbookReviewsOnline provide valuable open/close benchmarks but are not exact-horizon substitutes.
- Older VegasInsider/Wayback artifacts provide archived timestamped multi-book PIT evidence in earlier eras where row-level provenance passes.
- Action Network/ESPN free public endpoints are useful prospectively/currently; retroactive exact-horizon history is not accepted without concrete same-book time-series evidence.
- ParlayAPI free history is too shallow for 2020–2025 backfill; PropLine remains prospective-only for the pre-2026 historical program.
- The Odds API remains the strongest commercial fallback: documented featured-market history from 2020-06-06, at-or-before timestamp semantics, 10-minute then 5-minute cadence. SportsDataIO remains the commercial alternative.
- Fixed horizons remain T-2160/T-720/T-360/T-120/T-60/T-30/latest pre-kick. No opener/close/daily snapshot may be relabeled as one of them without the frozen timestamp selector.

### M2 — partial only
- lagged ability and replacement quality are feasible;
- narrow 2025 final-practice T-120 state is qualified under the existing reconstruction receipt;
- 2025+ nflverse depth charts carry PIT timestamps;
- no unified 2022–2025 availability state is qualified;
- no same-game realized snaps/inactives may be backfilled.

### M3 — qualified core

Lagged PBP-derived offense/defense/QB state may proceed to a frozen architecture. Current-week personnel/unit features require separate M2 provenance.

### M4 — qualified numerical/data contract

Use integer-bin integration and structural push mass with tail-safe/unbounded support. Do not repeat Q2-V1 folded/clipped endpoint behavior. M4 is not presumed independent alpha.

## Mandatory first M1 data action in Phase 3

Before freezing a historical dynamic-market architecture or requesting a paid source, execute the **free-first reconstruction audit** defined in `FREE_MARKET_DATA_DEEP_DIVE.md` and `MECHANISM_DATA_GATE.md`.

The audit must be outcome-blind and report season × game × book × horizon coverage, exact timestamp/kickoff relationships, spread line + price completeness, ML/total completeness, quote ages, rejection counts, source conflicts and rights/provenance classes.

Then, using only coverage/provenance evidence:

1. if free data supports a scientifically coherent M1 path, preregister M1 only on those supported eras/horizons;
2. if free data does not support a coherent M1 path, record the exact deficiency and seek explicit user authorization for a bounded commercial qualification pull, with The Odds API first and SportsDataIO second;
3. if the user does not authorize a purchase, freeze M1 as blocked/partial or exclude the unsupported historical path.

No horizon, source, feature or architecture may be selected because historical ATS/ROI/predictive results look favorable.

## Remaining Phase-3 freeze

Only after the M1 data decision is resolved may Phase 3 freeze candidate IDs, fields, horizons, families, grids, chronology, market nulls, metrics, ablations and stopping rules. No performance-sensitive choice should precede that freeze.

**Phase 3 remains `NOT_STARTED` at Phase-2 closeout.**