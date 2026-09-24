# M4 PREREGISTRATION

## Candidate identity

`FV2-HIST-M4-DMARGIN-01`

Status: `FROZEN__PHASE4_ELIGIBLE`.

## Scientific question

Can a numerically valid, analytically tail-safe integer-margin distribution improve probability quality around NFL betting lines relative to a strong market-centered distributional null?

M4 is a **representation experiment**. It is not presumed independent football alpha.

## Historical era

- training history begins: 2010 regular season;
- outer development: 2022–2025 regular seasons;
- completed 2026 outcomes prohibited;
- target rows use the historical schedule market line only under its frozen `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE` label.

## Sign convention

Freeze one home-margin convention before fitting:

`margin = home_score - away_score`.

The nflverse market field must be transformed once into the same home-margin direction and unit-tested on synthetic favorites/underdogs before any candidate score is produced.

## Continuous base law

The latent home margin is:

`Y ~ StudentT(nu, loc = market_implied_home_margin, scale = sigma(x))`.

No skew family, generalized-normal family, distributional forest or distribution zoo is authorized in V1.

## Integer PMF

Base integer mass:

`p0(m) = F(m + 0.5) - F(m - 0.5)`.

This gives structural whole-number mass and therefore a true push probability on integer spreads.

### Compact scoring-lattice adjustment

Apply training-only log-mass offsets only at:

- `m = 0`;
- `|m| = 3`;
- `|m| = 7`.

For those finite categories:

`w(m) = exp(gamma0*I[m=0] + gamma3*I[|m|=3] + gamma7*I[|m|=7])`.

Then:

`p(m) = p0(m) * w(m) / Z`.

Because only finitely many bins receive an offset, `Z` is computed analytically from the full Student-t mass plus the finite adjustments. No hard-support endpoint is required and no tail mass is folded or clipped.

## Conditional scale

Freeze:

`log sigma(x) = a0 + a1 * log(total_line / 45) + a2 * abs(spread_line) / 7`.

This is the entire V1 scale model. No weather, team identity, favorite/underdog subset, key-number subset or target-selected interaction may be added.

## Hyperparameters

- Student-t degrees of freedom `nu ∈ {4, 6, 10, 30}`;
- L2 penalty for conditional-scale coefficients `lambda_scale ∈ {1, 10}`;
- L2 penalty for key-mass coefficients `lambda_key ∈ {1, 10}`.

Parameters are fit from prior-time training rows only. Hyperparameter selection uses the nested chronological inner procedure and integer-margin log score. No ATS/ROI target enters tuning.

## Strong distributional null

`M4-NULL-STUDENTT-CONSTANT-01`:

- identical market center;
- identical integer-bin integration;
- Student-t `nu` selected chronology-clean from the same frozen set;
- one prior-only constant scale;
- no conditional-scale covariates;
- no key-mass offsets.

This prevents M4 from claiming success merely because a heavy-tailed distribution is better than an artificially weak Gaussian baseline.

## Primary metric

Integer-margin logarithmic score:

`-log P(M = observed_integer_margin)`.

## Secondary metrics

- CRPS / ranked probability score;
- multinomial cover/push/loss log loss at the market line;
- Brier score;
- calibration intercept/slope and reliability;
- tail-mass diagnostics;
- margin MAE/RMSE only as secondary point diagnostics;
- ATS hit rate/ROI only as diagnostics.

## Preregistered ablations

1. `CONSTANT_SCALE_NO_KEY` — strong null;
2. `CONDITIONAL_SCALE_NO_KEY`;
3. `CONSTANT_SCALE_KEY`;
4. `FULL_CONDITIONAL_SCALE_KEY` — candidate.

## Numerical fail-closed tests

Before scoring any target results:

- PMF normalization error `< 1e-12` under synthetic and representative parameter combinations;
- every PMF value finite and nonnegative;
- cover + push + fail probability equals 1 within `1e-12`;
- non-integer spread has exact push probability 0;
- integer-spread push maps to the corresponding integer margin exactly;
- no finite-support endpoint accumulation exists;
- extreme spread/total inputs preserve finite probabilities;
- sign-reversal synthetic tests pass.

Any numerical contract failure stops M4 before performance inspection. Q2 V1 may not be rescued by relaxing these checks.

## Failure condition

M4 fails to establish a representation improvement if the full candidate does not improve paired integer-margin log score versus the constant-scale Student-t null, or if normalization/tail/calibration safety fails.

A favorable ATS headline cannot rescue a proper-score or numerical failure.

## Downstream use

Only after M3 independently survives may a later phase evaluate M4 as a probability translator centered on the M3 mean. That composition is not part of the primary M3 or M4 Phase-4 tests and cannot be created post hoc from favorable results.