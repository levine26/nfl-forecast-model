# Q2 Preregistration — Discrete NFL Margin Distribution

**Candidate ID:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Phase-1 status:** frozen design; untrained; no candidate performance generated

## 1. Scientific question

Does replacing LevLine's fixed Normal margin bridge with an empirically calibrated discrete, heavy-tail-capable, key-number-aware distribution improve margin-distribution, cover/push/loss and calibration quality around the market line?

## 2. Output space

Q2 outputs an integer PMF:

`P(M=k), k=-75,...,+75`.

Any fitted continuous tail outside the range is folded into the `-75` / `+75` boundary bins. Boundary mass must be reported; if material, Q2 is invalid until a new pre-result range specification is frozen.

From the PMF compute directly:

- mean margin;
- median margin;
- win/tie/loss probability;
- cover/push/loss at any quoted spread;
- alternate-line probabilities;
- expected margin and quantiles.

## 3. Center

Market baseline center:

`C = -L`.

Main Q2 center:

`μ_Q2 = C + q0.5_Q1(R|X)`

using only chronology-clean Q1 median residual output.

This design tests whether Q1 location plus a better NFL distribution improves probabilities without reopening generic C0 mean-residual stacking.

## 4. Bounded base-distribution comparison set

Exactly four predeclared arms:

1. **Q2-GN (primary):** generalized normal;
2. **Q2-N:** Gaussian reference;
3. **Q2-T:** Student-t heavy-tail reference;
4. **Q2-EMP:** empirical discrete residual distribution reference.

No mixture model, skew family, spline density, normalizing flow or new distribution family may be introduced after results.

### Frozen shape grids

Generalized-normal `beta ∈ {1.0, 1.25, 1.5, 1.75, 2.0}`.

Student-t `df ∈ {4, 6, 10}`.

Shape choice occurs only inside inner chronology using full-distribution proper score. Gaussian has no shape search. Q2-EMP uses training-only residual frequencies with deterministic smoothing specified in implementation tests; it cannot use target-season counts.

## 5. Conditional scale

Q2 explicitly separates location from dispersion.

The only V1 scale predictors are:

`log(scale) = b0 + b1*|L| + b2*T_c + b3*|L|*T_c`

where `T_c = (market_total - training_fold_median_total)/10`.

Coefficients are fit only on the training window under the chosen base likelihood/proper-score implementation. No football-state, QB, injury or weather variance head is authorized in V1.

A constant-scale ablation is mandatory.

## 6. Key-number excess mass

The only key margins receiving explicit excess-mass terms are:

`|k| ∈ {3, 6, 7, 10, 14}`.

Key-number excess is estimated only on training history. V1 permits dependence on distance from the distribution center using exactly these predeclared absolute-distance bands:

- `0 <= |k-μ| < 3.5`;
- `3.5 <= |k-μ| < 7.5`;
- `|k-μ| >= 7.5`.

The implementation must use L2/shrinkage toward **no excess** and a fixed penalty grid `{1, 10, 100}` selected only by inner chronology. Positive/negative margins may share the same absolute-key coefficient unless a pre-result synthetic/identifiability test proves separate signs are necessary; target performance may not make that decision.

Mandatory ablations:

- no key-number excess;
- key-number excess with constant scale;
- full key-number + conditional scale.

## 7. Normalization and integer support

The final PMF must be nonnegative and sum to 1 to machine tolerance.

Q2 may discretize continuous base mass by integrating each integer bin `[k-0.5,k+0.5)` rather than point-evaluating the density. The exact discretization method must be fixed in Phase 2 before any Q2 historical score is generated and then unit-tested against known symmetric distributions. This is an engineering detail, not a performance-tunable choice.

After applying key-number adjustments, renormalize the entire PMF. Do not force artificial 50/50 mass around the sportsbook line; the market is a center/null, not a hard probability constraint on the Q2 challenger.

## 8. Whole- and half-point spread grading

For sportsbook spread `L`:

- `P_cover = sum P(M=k)` over `k+L>0`;
- `P_push = sum P(M=k)` over `k+L=0`;
- `P_loss = sum P(M=k)` over `k+L<0`.

For half-point lines, `P_push=0` exactly. For whole-number lines, push mass is the PMF at `k=-L`.

## 9. Market null M1

Q2 must construct a market-derived M1 distribution using the same distribution machinery but:

- center fixed at `C=-L`;
- no football/Q1 residual;
- scale/key parameters trained only on prior history;
- optional market total and no-vig moneyline may be used if qualified.

Q2's incremental claim is relative to M1, not only to LevLine's current fixed Normal bridge.

## 10. Evaluation

Primary:

- ranked probability score / discrete CRPS;
- multinomial cover/push/loss log loss where the quote is eligible;
- cover Brier and log loss;
- empirical push calibration;
- key-number calibration.

Secondary:

- mean/median margin MAE and RMSE;
- interval coverage;
- ATS hit rate/ROI only as non-selecting diagnostics.

## 11. Chronology

Same outer/inner expanding-season structure as Q1. Every Q2 parameter — center model, base shape, scale, key excess and any smoothing constant selected from the fixed grid — must be fit/tuned from prior-time data only.

Completed 2026 outcomes are prohibited.