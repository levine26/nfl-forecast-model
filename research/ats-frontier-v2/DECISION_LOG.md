# DECISION LOG

## Phase-1 decisions D001–D015
The Phase-1 decisions remain authoritative; see repository history / `FINAL_PHASE1_RECEIPT.md`. None is rescinded by Phase 2.

## D016 — M1 remains partial pending real historical coverage
**Decision:** `FRONTIER-M1-DYNAMIC-MARKET-STATE` = `PARTIALLY_QUALIFIED`.  
**Reason:** The Odds API and SportsDataIO document the required PIT-capable structure, but the no-purchase rule prevented an empirical season × book × horizon coverage audit. Documentation is not substituted for measured coverage.

## D017 — PropLine is prospective-only for the historical Frontier program
**Decision:** Do not use PropLine as pre-2026 historical M1 evidence.  
**Reason:** Current first-party documentation states that the archive starts in April 2026.

## D018 — M2 narrowed, not killed
**Decision:** `FRONTIER-M2-PLAYER-STATE-DELTA` = `PARTIALLY_QUALIFIED`.  
**Reason:** Lagged ability/replacement quality and narrow timestamped personnel states are legitimate, including the prior qualified 2025 T-120 final-practice reconstruction and 2025+ timestamped depth charts. The nflverse injury source ends after 2024, and the existing 2022–2025 harmonization failed closed.

## D019 — M3 core advances independently of rich personnel state
**Decision:** `FRONTIER-M3-HIERARCHICAL-STATE` = `DATA_QUALIFIED` for core lagged team/QB state.  
**Reason:** nflverse PBP is sufficient for chronology-safe prior-game state; current-week rich personnel fields remain governed by M2.

## D020 — M4 advances as representation only
**Decision:** `FRONTIER-M4-DISCRETE-MARGIN-V2` = `DATA_QUALIFIED` for numerical/data feasibility.  
**Reason:** historical score/spread/total fields exist and the required tail-safe integer-bin / structural-push representation is well-defined. No claim of predictive alpha is made.

## D021 — Historical odds is still the only justified paid-data category
**Decision:** If explicitly authorized, prefer a bounded The Odds API historical qualification pull first; SportsDataIO is the alternative.  
**Reason:** Exact multi-book timestamp history is the principal missing evidence needed to convert M1 from partial to fully data-qualified. No general football-stat purchase is recommended.

## D022 — Completed-2026 and production firewalls remain intact
**Decision:** Phase 2 uses zero completed-2026 outcomes for candidate design and makes no production forecasting changes.