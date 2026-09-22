# Phase 2 — Paid Data Escalation Decision

**Decision:** NO PAID DATA DEPENDENCY REQUESTED  
**Date:** 2026-09-22

The user requested that meaningful paid accuracy opportunities be surfaced, while strongly preferring free/open data.

Phase 2 reviewed the existing repository source registry and the known classes of commercial football data.

Potential commercial value exists in:

- historical revision-aware injuries / expected availability;
- offensive-line assignments and blocking;
- pressure attribution;
- route / coverage charting;
- stable participation / lineup history.

However, there is not yet evidence that any paid source is necessary to address the dominant Phase 1 failures.

The initial Phase 3 challengers can be built with $0 sources:

- dynamic opponent-adjusted strength from nflverse PBP;
- drive/possession scoring from nflverse PBP;
- historical closing-like market residualization from existing market fields.

Buying data now would make it harder to separate architecture improvement from data improvement.

## Revisit gate

A paid source should be brought to the user only when all of the following are true:

1. Phase 3/4 isolates a persistent residual failure.
2. A named paid field plausibly measures that missing state.
3. No free/PIT-safe alternative is available.
4. A bounded test or sample can estimate incremental predictive value.
5. Expected value is large enough to matter relative to forecast uncertainty.
6. Price and ongoing operational burden are known.

Until that gate is met, the binding research budget remains $0.
