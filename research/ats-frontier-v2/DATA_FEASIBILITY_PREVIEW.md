# DATA FEASIBILITY PREVIEW

This is a Phase-1 planning assessment only. Phase 2 must prove these assertions with source samples and schema tests before any candidate fitting.

## M1 dynamic market state — feasibility: `PROMISING / NOT YET QUALIFIED`

**Available:** multiple commercial/current providers expose spread, side price, moneyline, total, bookmaker identity and timestamps. The Odds API documents historical snapshots from 2020; SportsDataIO documents every line change; PropLine exposes history/closing commands.  
**Unknown:** exact NFL book coverage by season, quote staleness, book renames, side-price completeness, archival cost/licensing and whether the same books exist consistently across development years.  
**Phase-2 pass gate:** reconstruct at least the preregisterable target horizons from actual at-or-before snapshots for a broad game panel, with book identity and no future quote leakage.

## M2 player-state delta — feasibility: `MATERIAL RISK`

**Available:** historical rosters, PBP, snap counts, some injury reports, timestamped modern depth charts, player-value training data.  
**Known obstacle:** nflverse documents no 2025 injury data after its injury source died post-2024. Historical public depth-chart/injury revision semantics may be incomplete.  
**Phase-2 pass gate:** construct a defensible timestamped player-status/role table for enough seasons to support development, or explicitly narrow M2 to event types with verifiable timestamps (e.g., QB starter announcements/transactions) before preregistration. No retrospective final inactive/snap fill-in.

## M3 hierarchical state — feasibility: `HIGH FOR CORE / MEDIUM FOR UNIT DETAIL`

**Available:** chronology-safe prior-game PBP and team efficiency are strong.  
**Risk:** rich unit states can require personnel continuity data whose historical PIT quality is lower.  
**Phase-2 pass gate:** prove a compact state decomposition can be computed with lagged public data without relying on realized target-game participation.

## M4 discrete margin V2 — feasibility: `HIGH FOR CORE`

**Available:** historical final scores, market spreads/totals and training-era distributions.  
**Risk:** if conditioned on M1 dynamic market state, it inherits M1 historical data needs.  
**Phase-2 pass gate:** prove canonical sign/join consistency, define training-only era windows, and establish tail/support diagnostics without target-performance inspection.

## Provider purchase decision

Do not buy general-purpose stats merely to increase feature count. The only category currently showing a direct ability to unlock a shortlisted information mechanism is **historical timestamped multi-book odds/price data**. A purchase recommendation, if any, should follow a Phase-2 sample audit comparing The Odds API and SportsDataIO on the exact M1 fields.

## Overall feasibility

The program has enough open data to test M3/M4 and enough provider evidence to believe M1 is obtainable. M2 is the principal data-risk candidate. This is a useful outcome: Phase 2 is explicitly allowed to kill M2 before model design rather than paper over PIT gaps with ex-post proxies.