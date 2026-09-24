# CURRENT STATE AND NEXT STEPS

## Current program state

Phase 1 is complete. Phase 2 data qualification has been executed outcome-blind on `research/ats-frontier-v2-phase2` and is awaiting/under merge validation. Phase 3 is not started.

## Phase-2 gate

- M1 dynamic market state — `PARTIALLY_QUALIFIED`: legitimate PIT historical products exist, but authorized historical real-data access is still needed to quantify book/horizon completeness.
- M2 player-state delta — `PARTIALLY_QUALIFIED`: lagged ability plus narrowly qualified/timestamped personnel sources survive; broad cross-era availability does not.
- M3 hierarchical state — `DATA_QUALIFIED` for core lagged team/QB state.
- M4 discrete margin V2 — `DATA_QUALIFIED` for numerical/data feasibility only.

## Paid-data decision

No purchase occurred. If the user authorizes an M1 qualification pull, the current first choice is The Odds API because its historical snapshot endpoint explicitly guarantees at-or-before semantics and begins 2020-06-06. A bounded $30/month 20K-credit plan is the lowest listed historical tier at the Phase-2 evidence cutoff. SportsDataIO remains the alternative.

## Next authorized program phase

Phase 3 — Final Architecture Design & Preregistration — must begin by reading the Phase-2 receipt, `MECHANISM_DATA_GATE.md`, provenance manifest and `PHASE3_HANDOFF.md`. It must resolve M1's paid-history dependency before freezing any historical dynamic-market architecture. It may not infer missing M1 coverage from documentation.

Production remains `F-ST-01-FROZEN-2026` and unchanged.