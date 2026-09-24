# CURRENT STATE AND NEXT STEPS

## Current program state

Phase 1 is complete. Phase 2 data qualification, PIT reconstruction feasibility, mechanism gating, and the free/open-source M1 follow-up are complete and merged through PR `#572` at `bdc16905b46c390338814b584a51be2c9784c436`. The authoritative immutable closeout is `FINAL_PHASE2_RECEIPT.md`. Phase 3 is not started.

A post-qualification free/open-source deep dive materially changed the market-data access recommendation without changing the frozen M1 mechanism: **do not purchase historical odds yet**. Free-source reconstruction must be empirically exhausted first.

## Phase-2 gate

- M1 dynamic market state — `PARTIALLY_QUALIFIED__FREE_FIRST_RECONSTRUCTION_REQUIRED`: genuine public historical market artifacts were found across 2020–2025, but exact season × game × book × fixed-horizon completeness is still unmeasured. Sparse daily snapshots/openers/closes cannot be relabeled as exact horizons.
- M2 player-state delta — `PARTIALLY_QUALIFIED`: lagged ability plus narrowly qualified/timestamped personnel sources survive; broad cross-era availability does not.
- M3 hierarchical state — `DATA_QUALIFIED` for core lagged team/QB state.
- M4 discrete margin V2 — `DATA_QUALIFIED` for numerical/data feasibility only.

## Historical-odds decision

No purchase occurred and none is currently recommended.

The free deep dive found, among other sources:
- provider-origin public historical NFL cache payloads covering verified examples in 2020–2024 with timestamps, bookmaker identity, spread/price, h2h and totals;
- a public dense 2025 multi-book DuckDB corpus with 1.8M+ rows, 636 captures and 30+ operators;
- broad free opening-line coverage through recent seasons;
- older archived multi-book PIT reconstructions;
- prospective free collection paths.

None of those findings is allowed to manufacture unsupported T-360/T-120/T-60/T-30 observations. Rights/licensing is tracked separately from temporal validity.

The Odds API remains the first commercial fallback only if the free-first audit demonstrates an explicit scientific coverage deficiency. SportsDataIO remains the second fallback. Any purchase still requires explicit user authorization.

## Next authorized program phase

Phase 3 — Final Architecture Design & Preregistration — must begin by reading `FINAL_PHASE2_RECEIPT.md`, `FREE_MARKET_DATA_DEEP_DIVE.md`, `MECHANISM_DATA_GATE.md`, the provenance manifest, and `PHASE3_HANDOFF.md`.

Its first M1 data action is the outcome-blind free reconstruction audit. Only after that audit may Phase 3 either freeze a free-supported M1 architecture or document the exact deficiency and seek authorization for a bounded commercial qualification pull. No source/horizon may be selected from candidate performance.

Production remains `F-ST-01-FROZEN-2026` and unchanged. Completed-2026 outcomes used in Phase 2: 0. Frontier candidate performance inspected in Phase 2: NO.