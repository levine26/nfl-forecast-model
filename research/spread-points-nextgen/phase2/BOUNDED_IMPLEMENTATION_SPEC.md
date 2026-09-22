# Phase 2 — Bounded Phase 3 Implementation Specification

**Status:** frozen before challenger implementation/results  
**Purpose:** prevent Phase 3 from becoming an unconstrained model/hyperparameter search.

This document refines the model families in `CHALLENGER_PREREGISTRATION.md`. Phase 3 may simplify an implementation for numerical/stability reasons, but expanding these search spaces requires a logged preregistration amendment before the new result is inspected.

---

# A — Dynamic Opponent-Adjusted Joint Score

## A0 mandatory reference: time-decayed partial-pooling score model

Model one team-score row per team/game:

`points_for = league_level + offense_team_effect - opponent_defense_effect + home_effect + rest_terms + compact_lagged_process_terms + error`

### Estimator

- Ridge regression / penalized Gaussian linear model.
- Offense-team and defense-team indicators share the same regularization mechanism, creating partial pooling.
- Historical observations receive exponential time-decay weights.

### Prespecified tuning grid

Selected only inside prior-time folds:

- ridge alpha: `[0.1, 1, 10, 100]`
- observation half-life in team games: `[4, 8, 16, 32]`

If the frozen inner-fold rule in `EVALUATION_HOLDOUT_PROTOCOL.md` yields fewer than two valid inner validation seasons, no data-driven tuning occurs. Use the fixed fallback `alpha=10`, `half_life=16`.

No finer grid is permitted in the initial Phase 3 candidate.

### Numeric process covariates

Initial compact set:

- lagged offense EPA/play;
- lagged defense EPA/play allowed;
- lagged pass EPA difference;
- lagged success-rate difference;
- rest differential;
- home indicator.

Opponent-team effects already supply opponent adjustment; no duplicate 3/5/8/EWMA copies of every variable are included.

### Joint score distribution

- generate home and away conditional means from the shared team-score model;
- estimate home/away residual covariance from training-only OOF/residual data;
- **primary reference distribution:** correlated Gaussian residual simulation;
- training-residual bootstrap may be reported only as a non-selective distributional sensitivity. It cannot replace A0 because its score looks better.

A0 is the complete initial Challenger A identity. It tests whether a simple dynamically weighted, opponent-adjusted structure beats the current four-regressor feature ensemble.

## Explicit state-space refinement — deferred

A random-walk / AR(1) offense-defense state-space implementation is scientifically motivated by Glickman & Stern, but it is **not an additional initial Phase 3 search branch**. It may be proposed later only through a preregistration amendment made before any new state-space result is inspected. Weak A0 performance alone is not sufficient reason to open that search.

---

# B — Possession / Drive Score Process

## B0 mandatory bounded implementation

### Component 1 — expected drives

Use a simple count/continuous regression for expected team offensive drives.

Initial predictors:

- lagged team drive count;
- lagged opponent drive count;
- lagged plays/drive or offensive plays;
- home/rest;
- A0 dynamic strength outputs if generated strictly OOF.

Reference estimator:

- **Poisson regression with L2 regularization.**

Training-fold overdispersion must be recorded as a diagnostic, but it does not authorize switching B0 to linear or Negative Binomial after seeing development performance. A different count family requires a preregistration amendment before its result is inspected.

### Component 2 — drive scoring outcome

Each prior offensive drive is classified into the compact scoring family:

- TD;
- FG;
- EMPTY / other zero-point offensive outcome.

Rare safeties / defensive scores are not given unconstrained team-specific classifiers. They enter through a low-frequency empirical residual/tail component.

Reference estimator:

- L2-regularized multinomial logistic regression.

Prespecified inverse-regularization grid:

- `C = [0.05, 0.2, 1.0, 5.0]`

### Component 3 — score simulation

For each game:

1. draw shared game-volume variation from training-only drive residuals;
2. draw each team's number of possessions;
3. draw drive outcomes from its pregame probabilities;
4. assign TD points using training-only empirical 6/7/8 conversion frequencies;
5. assign FG = 3;
6. add only the prespecified rare-score tail mechanism;
7. aggregate team points.

Reference simulation count:

- at least 10,000 draws/game for final evaluation;
- smaller fixed draws are allowed in unit tests only.

### No black-box fallback

XGBoost/CatBoost drive classifiers are not initial B0 alternatives.

A flexible learner can be proposed later only through a preregistered amendment after B0 establishes the structural baseline.

---

# C — Market Residual Margin / Total

## C0 mandatory reference

Two separate regularized residual regressions:

- margin residual;
- total residual.

Estimator:

- **ElasticNet only.** `l1_ratio=0.0` is the ridge endpoint inside the same fixed family.

Prespecified alpha grid:

- `[0.01, 0.1, 1, 10, 100]`

Prespecified l1 ratio:

- `[0.0, 0.2, 0.5]`

If fewer than two valid inner validation seasons exist, use fixed fallback `alpha=1.0`, `l1_ratio=0.0`.

All selection is prior-time nested.

### Initial predictor set

- market margin or total level;
- football-only predicted margin/total from the frozen development football base;
- football-model minus market difference;
- dynamic offense-strength difference;
- dynamic defense-strength difference;
- rest differential;
- home context where not already absorbed by orientation.

No injury/weather/player state unless separately qualified.

## Nonlinear residual sensitivity — deferred

No GAM, spline, tree or boosting residual model is authorized in the initial Phase 3 implementation. Challenger C is C0.

A nonlinear residual model requires a preregistration amendment before its result is inspected; poor C0 development performance is not, by itself, authorization to search for a rescue model.

---

# D — Conditional ensemble

D is **target-specific** (margin and total are gated separately).

Eligibility requires all of the following on common 2022–2024 outer-OOF rows:

1. at least two eligible component error series have absolute Pearson correlation <= 0.90;
2. a nonnegative, sum-to-one convex blend fitted only inside the nested training history improves the target MAE versus the best single component on the combined development OOF rows;
3. the blend improvement has the same sign in at least two of the three outer target seasons (2022, 2023, 2024);
4. season+week block bootstrap probability that the blend has lower MAE than the best component is >= 0.75.

If any condition fails for a target, D does not exist for that target.

No neural/meta-tree stack is authorized. No global all-target ensemble is inferred from a one-target gate.

---

# Shared implementation rules

1. Same team/game identity contract across A/B/C.
2. No result-season feature normalization using future rows.
3. Standardization parameters fit on training only.
4. Hyperparameter grid evaluation occurs within the deterministic prior-time folds in `EVALUATION_HOLDOUT_PROTOCOL.md` only.
5. Candidate-specific tuning loss is fixed there before implementation; no metric switching is allowed.
6. Every emitted prediction stores candidate ID, train-through season/week, feature contract version and source-code SHA.
7. Development outputs stop at 2024.
8. Phase 3 runner must fail if asked to emit 2025 holdout metrics before Phase 4 authorization.
9. 2026 completed outcomes remain unavailable to all selection code paths.

This bounded specification is intentionally conservative. If these models cannot improve the baseline, Phase 2 does not authorize an unlimited search for a more complicated rescue.
