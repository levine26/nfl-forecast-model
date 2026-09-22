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

No finer grid is permitted until the above is evaluated.

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
- reference distribution: correlated Gaussian residual simulation;
- preserve a discrete-score sensitivity through training-residual bootstrap if stable.

A0 exists to test whether a simple dynamically weighted, opponent-adjusted structure beats the current four-regressor feature ensemble.

## A1 optional state-space refinement

A1 becomes eligible only if A0 is reproducible and Phase 3 development evidence shows meaningful remaining temporal lag.

Permitted change:

- replace the time-decay approximation with explicit offense/defense random-walk or AR(1) latent states.

State persistence / innovation parameters must use a small prior-time grid or likelihood fit inside the training fold. No 2025 result is available during this choice.

A1 does not gain new feature families merely because the estimator changes.

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

- regularized linear or Poisson regression.

If training-fold dispersion materially violates Poisson assumptions, a Negative Binomial alternative is permitted and the dispersion diagnostic must be recorded.

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

- Ridge or ElasticNet.

Prespecified alpha grid:

- `[0.01, 0.1, 1, 10, 100]`

For ElasticNet, prespecified l1 ratio:

- `[0.0, 0.2, 0.5]`

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

## C1 controlled nonlinear sensitivity

One low-complexity nonlinear model may be tested:

- GAM/spline on market level + football-market disagreement; **or**
- shallow gradient boosting with depth <=2 and a fixed small estimator grid.

Only one C1 family may be chosen before results; do not test both and select the winner.

Default Phase 3 choice: GAM/spline if the implementation stack supports it cleanly; otherwise skip C1 rather than substitute an unconstrained learner.

---

# D — Conditional ensemble

If activated, the first and only reference is a linear convex combination of frozen candidate OOF means/distributions.

Weights:

- nonnegative;
- sum to one;
- fitted only on inner/nested OOF rows.

No neural/meta-tree stack is authorized.

---

# Shared implementation rules

1. Same team/game identity contract across A/B/C.
2. No result-season feature normalization using future rows.
3. Standardization parameters fit on training only.
4. Hyperparameter grid evaluation occurs within prior-time folds only.
5. Every emitted prediction stores candidate ID, train-through season/week, feature contract version and source-code SHA.
6. Development outputs stop at 2024.
7. Phase 3 runner must fail if asked to emit 2025 holdout metrics before Phase 4 authorization.
8. 2026 completed outcomes remain unavailable to all selection code paths.

This bounded specification is intentionally conservative. If these models cannot improve the baseline, Phase 2 does not authorize an unlimited search for a more complicated rescue.
