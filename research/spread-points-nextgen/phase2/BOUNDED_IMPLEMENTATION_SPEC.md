# Phase 2 — Bounded Phase 3 Implementation Specification

**Status:** frozen before challenger implementation/results  
**Purpose:** prevent Phase 3 from becoming an unconstrained model/hyperparameter search.

This document refines the model families in `CHALLENGER_PREREGISTRATION.md`. Phase 3 may simplify an implementation for numerical/stability reasons, but expanding these search spaces requires a logged preregistration amendment before the new result is inspected.

## Frozen search-space rule

The initial Phase 3 implementation is exactly **A0 + B0 + C0**.

- A1 and C1 are **deferred research ideas**, not development-period escape hatches.
- No alternate learner family may be substituted because A0/B0/C0 underperform.
- Any material extension requires a new candidate/version and a preregistration amendment written **before** that extension's outputs are inspected.
- The mandatory A0/B0/C0 development outputs are preserved even when negative.

## Fixed lagged-state construction

To prevent rolling-window fishing, all compact lagged process summaries used by A0/B0/C0 are computed from prior completed regular-season team games with an exponentially weighted mean using a **fixed 8-team-game half-life**. No 3/5/8/16-window sweep is permitted.

The A0 observation-weight half-life remains a model hyperparameter because it controls training-row influence, not feature-window construction. These are separate mechanisms.

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

Initial compact set, all using the fixed 8-team-game lagged-state rule above:

- offense EPA/play;
- opponent defense EPA/play allowed;
- offense pass EPA/play;
- opponent defense pass EPA/play allowed;
- offense success rate;
- opponent defense success rate allowed;
- rest differential;
- home indicator.

No rush/pass interaction search, arbitrary rolling-window duplication, or team-name correction is authorized.

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

Model expected team offensive drives with one fixed design.

Initial predictors are exactly:

- offense prior-game drive-count state: exponentially weighted mean with half-life **8 team games**;
- opponent prior-game drive-count-allowed state: exponentially weighted mean with half-life **8 team games**;
- offense prior-game plays-per-drive state: exponentially weighted mean with half-life **8 team games**;
- opponent prior-game plays-per-drive-allowed state: exponentially weighted mean with half-life **8 team games**;
- home indicator;
- rest differential.

No A0 output enters B0. This keeps B structurally distinct rather than turning it into an A wrapper.

Reference estimator:

- **Poisson regression with L2 regularization.**

Prespecified L2 alpha grid:

- `[0.0, 0.1, 1.0, 10.0]`

If fewer than two valid inner validation seasons exist, use fixed fallback `alpha=1.0`.

Training-fold overdispersion must be recorded as a diagnostic, but it does not authorize switching B0 to linear or Negative Binomial after seeing development performance. A different count family requires a preregistration amendment before its result is inspected.

### Component 2 — drive scoring outcome

Each prior offensive drive is classified into the compact scoring family:

- TD;
- FG;
- EMPTY / other zero-point offensive outcome.

B0 uses one fixed pregame feature design for every drive in the forecast game:

- offense team indicator;
- defense team indicator;
- home indicator;
- rest differential;
- offense EPA/play state, EWMA half-life **8 team games**;
- defense EPA/play-allowed state, EWMA half-life **8 team games**;
- offense success-rate state, EWMA half-life **8 team games**;
- defense success-rate-allowed state, EWMA half-life **8 team games**;
- offense turnover-per-drive state, EWMA half-life **8 team games**;
- defense takeaways-per-drive state, EWMA half-life **8 team games**;
- offense explosive-play rate state, EWMA half-life **8 team games**;
- defense explosive-play-allowed state, EWMA half-life **8 team games**;
- offense red-zone TD conversion state, shrinkage-smoothed using prior drives only;
- defense red-zone TD allowed state, shrinkage-smoothed using prior drives only.

The red-zone definition and shrinkage formula must be fixed in code before the first development metric is emitted; changing them after observing results is a candidate-identity change requiring preregistration amendment.

Rare safeties / defensive scores are not given unconstrained team-specific classifiers. They enter through a low-frequency empirical residual/tail component.

Reference estimator:

- L2-regularized multinomial logistic regression.

Prespecified inverse-regularization grid:

- `C = [0.05, 0.2, 1.0, 5.0]`

If fewer than two valid inner validation seasons exist, use fixed fallback `C=0.2`.

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

- **Ridge regression only.**

Prespecified alpha grid:

- `[0.01, 0.1, 1, 10, 100]`

If fewer than two valid inner validation seasons exist, use fixed fallback `alpha=1.0`.

All selection is prior-time nested.

### Initial predictor set

C0 uses **A0 only** as its football base; it may not choose A versus B after seeing which looks better.

For the margin residual model:

- market home margin;
- A0 football-only expected margin;
- A0 minus market margin disagreement;
- A0 offense-strength difference;
- A0 defense-strength difference;
- rest differential.

For the total residual model:

- market total;
- A0 football-only expected total;
- A0 minus market total disagreement;
- A0 summed offense-strength state;
- A0 summed defense-strength state;
- rest differential.

Home context is already encoded in the home-oriented market and A0 forecasts and is not duplicated as an extra C0 switch variable.

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

## Final red-team reconciliation — authoritative

This section records the final pre-result reconciliation after concurrent Phase 2 hardening edits. It supersedes any earlier Phase 2 wording that is more permissive.

- **A:** A0 is the only initial Challenger A implementation. Explicit state-space A1 is deferred.
- **B:** B0 is independent of A0; no A-derived predictor enters B0. Expected drives use the fixed Poisson design above. Negative Binomial, Gaussian alternatives, and `B0_PLUS_A0_STATE` are not initial Phase 3 candidates.
- **C:** C0 is Ridge-only on the fixed A0 football base. GAM, spline, ElasticNet and tree residual variants are deferred.
- **D:** D is target-specific and exists only if the objective complementarity gate in this document passes.
- No weak development result authorizes opening a broader learner/feature search under the same candidate identity.
