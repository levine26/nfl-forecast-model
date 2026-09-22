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

## 5. Initial predictors

Keep the initial residual model deliberately small.

Eligible:

- football-only expected margin / total from a frozen football base;
- dynamic offense-strength difference;
- dynamic defense-strength difference;
- rest differential;
- home context;
- prior-game opponent-adjusted efficiency;
- market line level itself for bounded nonlinear calibration if preregistered.

Optional prespecified interactions:

- football-model minus market discrepancy;
- market favorite-size band;
- market-total band.

No arbitrary high-order interaction search.

---

## 6. Initial learner

Reference model:

- Ridge or ElasticNet.

Secondary controlled ablation:

- low-complexity GAM/spline or shallow tree model.

A flexible tree ensemble must beat the simple reference in prior-time folds and survive complexity penalties before it becomes the candidate identity.

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

At minimum compare:

1. market-only zero residual;
2. market + football residual features;
3. market + line-level calibration only;
4. market + full preregistered residual candidate.

This distinguishes genuine football information from simple market calibration.

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
