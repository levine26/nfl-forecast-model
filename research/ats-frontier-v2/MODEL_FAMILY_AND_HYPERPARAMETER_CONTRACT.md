# MODEL FAMILY AND HYPERPARAMETER CONTRACT

No candidate-family search is permitted in Phase 4. The only authorized families/grids are below.

## `FV2-HIST-M3-DSSM-01`

Family: linear-Gaussian hierarchical dynamic state-space model / Kalman-filter-compatible dynamic linear model with offense, defense and QB states.

Frozen grid:

- `q_team`: `[0.04, 0.10, 0.25]` standardized variance;
- `q_qb`: `[0.10, 0.25, 0.50]`;
- `season_carryover`: `[0.50, 0.75]`;
- `ridge_alpha`: `[10, 100]`;
- within-season state persistence: fixed `1.0`;
- candidate evaluation residual family: Normal with prior-only constant scale.

No changepoint learner, boosting, neural model, pass/rush state expansion or arbitrary process-noise search is authorized.

## `FV2-HIST-M4-DMARGIN-01`

Family: market-centered Student-t base distribution, exact integer-bin integration, compact conditional scale, finite 0/|3|/|7| mass offsets.

Frozen grid:

- `nu`: `[4, 6, 10, 30]`;
- `lambda_scale`: `[1, 10]`;
- `lambda_key`: `[1, 10]`.

Conditional scale formula is fixed. No skew family, generalized-normal competitor, empirical-distribution tournament, distributional forest, NGBoost or GAMLSS tournament is authorized in this version.

## `FV2-PROS-M1-MARKETSTATE-01`

Family: ridge linear state correction / ridge multinomial-logit correction.

Future regularization set: `[10, 100]` only after sufficient prior prospective observations exist. No historical performance may be manufactured under the current blocked data state.

## `FV2-PROS-M2-QBDELTA-01`

Family: hierarchical shrinkage QB-value state + ridge market-residual correction. No broad position/injury learner.

## Tuning rule

Use only `CHRONOLOGY_CONTRACT.md`. Select by preregistered primary proper score. ATS, ROI, profit, winner changes, favorable key numbers, and completed-2026 outcomes are prohibited tuning signals.

## Family versioning

Any family, feature family or hyperparameter outside this file requires a new explicitly named candidate/version opened before its target results are inspected. Phase 4 may not silently amend this contract after seeing results.