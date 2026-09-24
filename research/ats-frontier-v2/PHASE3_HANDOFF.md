# PHASE 3 HANDOFF

Phase 3 is **Final Architecture Design & Preregistration**. It must not begin until Phase 2 is merged and its gate is authoritative.

## Qualified inputs to Phase 3

### M1 — partial only
- The Odds API: documented featured-market history from 2020-06-06; 10-minute snapshots initially, 5-minute snapshots from September 2022; at-or-before timestamp semantics; paid.
- SportsDataIO: viable line-movement schema with sportsbook ID, Created/Updated, spread + side payout, moneyline, total; historical real-data access remains product/licensing dependent.
- PropLine: prospective capture only for Frontier historical work; archive begins 2026-04.
- Fixed horizons remain T-2160/T-720/T-360/T-120/T-60/T-30/latest pre-kick, but no horizon may be preregistered as empirically supported until paid historical coverage is measured.

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

## Phase-3 first action

Before freezing final candidate IDs or hyperparameters, resolve the M1 dependency: either (a) obtain explicit user authorization for the bounded historical odds purchase/pull and measure coverage, or (b) preregister an architecture that excludes historical dynamic-market path features and records M1 as blocked/partial.

Then Phase 3 may freeze candidate IDs, fields, horizons, families, grids, chronology, market nulls, metrics, ablations and stopping rules. No performance-sensitive choice should precede that freeze.