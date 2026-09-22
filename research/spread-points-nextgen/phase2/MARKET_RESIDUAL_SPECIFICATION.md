# Phase 2 — Market-Residual Challenger Specification

**Candidate:** C — Market Residual Margin and Total  
**Class:** market-aware  
**Status:** preregistered; no implementation yet

## 1. Scientific question

Can pregame football information explain **the market's remaining error** better than current LevLine can predict final margin/total from scratch?

This is explicitly different from asking whether LevLine can reconstruct sportsbook prices.

---

## 2. Targets

Using the canonical home-margin convention:

`r_margin = actual_home_margin - market_home_margin`

`r_total = actual_total - market_total`

Forecasts:

`hybrid_margin = market_home_margin + E[r_margin | football_state]`

`hybrid_total = market_total + E[r_total | football_state]`

A zero-residual model exactly equals the market and is the mandatory nested null.

---

## 3. Historical market family

Primary historical development uses the nflverse schedule market fields on exact paired games.

Those fields are labeled:

**historical closing/late benchmark; exact bookmaker and capture horizon opaque**

They are not T-120 evidence.

Every table must show both:

- raw market error;
- hybrid residual-model error.

---

## 4. Prospective horizon family

Prospective T-120 residual research is a distinct candidate family.

It requires:

- immutable timestamped market snapshot at/before kickoff-120 minutes;
- book/consensus construction fixed in advance;
- no closing-line backfill;
- explicit stale/missing status.

The historical closing-like candidate cannot be silently promoted into the T-120 family.

---

## 5. Initial C0 predictors

Keep the initial residual model deliberately small and fixed.

For both margin and total C0:

- market line level;
- frozen football-only predicted margin or total from A0;
- football-model minus market discrepancy;
- A0 dynamic offense-strength difference;
- A0 dynamic defense-strength difference;
- rest differential;
- home indicator where not already absorbed by target orientation.

No market favorite-size bands, total bands, arbitrary interactions, polynomial expansion, player state, weather or post-result feature additions are authorized in C0.

---

## 6. Initial learner

Reference model:

- **Ridge regression only**, under the fixed alpha grid in `BOUNDED_IMPLEMENTATION_SPEC.md`.

No nonlinear secondary learner is part of initial Phase 3. GAM/spline/ElasticNet/tree residual models are deferred and require a preregistration amendment before any such result is inspected.

---

## 7. Shrinkage interpretation

Predicted residuals should naturally be small if the market is hard to beat.

No constraint forces nonzero corrections.

A candidate that learns residuals close to zero is a valid negative result.

---

## 8. Disagreement policy

Do not presume large disagreement means more LevLine edge.

Phase 1 >=6-point disagreement evidence was worse than the market in continuous error.

Therefore:

- discrepancy may be a predictor;
- its functional effect must be learned only from prior-time data;
- no monotonic “trust LevLine more as gap grows” rule is imposed;
- no edge bucket chooses model weight on the final holdout.

---

## 9. Market duplication test

For every football predictor used in C, report its incremental contribution against the market-only null.

Required comparison ladder:

1. **Market only:** predicted residual = 0.
2. **Market + line-level calibration:** a Ridge residual model using only the market line level for that target; no football variables.
3. **Market + football residual information:** a Ridge residual model using the frozen A0 football forecast/state variables but excluding the market-line calibration term beyond the residual anchor.
4. **Full C0:** the complete preregistered target-specific predictor set in `BOUNDED_IMPLEMENTATION_SPEC.md`.

All four use the same paired games and nested chronology. The ladder distinguishes genuine football information from simple calibration of the market level itself.

---

## 10. Evaluation

Primary:

- paired margin/total MAE;
- paired RMSE;
- season+week block bootstrap of hybrid minus market;
- residual mean and SD;
- closer rate.

Secondary:

- distribution calibration if residual variance model exists;
- ATS/O-U diagnostics without threshold tuning.

No ROI metric is required for candidate survival.

---

## 11. Acceptance standard

Candidate C is scientifically interesting only if it:

- improves over market on development OOS rows or has credible complementary residual information;
- does not rely on one season;
- does not generate improvement solely from retrospective line timing;
- remains transparent about market dependence.

The program accepts “market-only wins” as a valid outcome.

## 12. Mandatory four-arm null hierarchy

Every Phase 3 development table for C must report the same exact paired rows for these four arms, in this order:

1. **M0 — market only**
   - predicted residual = 0;
   - forecast = market.

2. **M1 — market + line-level calibration only**
   - residual model uses the market line level only;
   - no football-state predictor;
   - same Ridge family and nested chronology as C0.

3. **M2 — market + football residual information**
   - residual model uses the frozen football-only forecast/state terms plus prespecified home/rest context;
   - no extra line-level calibration term beyond the market already present in the base forecast.

4. **M3 — full preregistered residual model**
   - combines the eligible M1 line-level calibration term and M2 football terms;
   - this is the full C0 reference.

Interpretation:

- M1 improving M0 means calibration structure exists, not that football adds information.
- M2 improving M0 is the direct test that football information explains sportsbook residual error.
- M3 improving M1 shows whether football adds information beyond simple market recalibration.
- If M2/M3 do not improve the relevant nulls, record **NO_INCREMENTAL_FOOTBALL_EDGE**.

No arm may use future line movement, closing data for an earlier horizon, completed-2026 outcomes, or hindsight personnel/weather state.


## 12. Same-horizon honesty

Historical C0 uses only the closing/late nflverse market family and must be labeled that way.

No Phase 3 or Phase 4 table may:

- call those rows T-120;
- mix timestamped prospective market receipts with closing-like historical rows in one headline metric;
- use a later market update to backfill an earlier simulated horizon.

Prospective T-120 is a separately versioned future candidate family.
