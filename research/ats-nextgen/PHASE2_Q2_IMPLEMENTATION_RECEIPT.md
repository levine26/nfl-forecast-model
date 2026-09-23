# Phase 2 Stage B — Q2 Pre-Result Implementation Receipt

**Program:** `LEVLINE_ATS_NEXTGEN`  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Status:** PRE-RESULT IMPLEMENTATION CONTRACT FROZEN; Q2 UNTRAINED  
**Stage-B base / verified Stage-A merge:** `a2581a62e3797a6ac466d614326bc72b7d5a1c57`  
**Branch:** `research/ats-nextgen-phase2-q2`  
**Production:** `F-ST-01-FROZEN-2026` unchanged

## 1. Scientific boundary

Stage A is closed. Q1 is preserved as a valid negative incremental result; it is not rescued or redesigned. Stage B is authorized by the frozen Phase-1 Q2 preregistration and the Q1 result handoff only.

Before this receipt:

- Q2 fitting performed: **NO**;
- Q2 historical proper-score/performance generated: **NO**;
- Q3 started: **NO**;
- completed-2026 outcomes used: **0**;
- production behavior changed: **NO**.

The frozen Q1 OOF identity that Stage B must reproduce before any Q2 fit is:

`d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`

for `q1_outer_oof_2022_2025.csv` on 1,087 rows.

## 2. Integer support and continuous-family discretization

The Q2 support is exactly integer margin `k=-75,...,+75`.

For Gaussian, Student-t and generalized-normal arms, probability is obtained by **CDF integration**, not point-density evaluation:

- interior bin `k`: `[k-0.5, k+0.5)`;
- `k=-75`: `(-inf,-74.5)`;
- `k=+75`: `[74.5,+inf)`.

Thus all tail probability is folded into the two boundary bins exactly as preregistered. PMFs must be finite, nonnegative and sum to one to machine tolerance. Boundary mass is recorded.

## 3. Base-family identities

Exactly the frozen four arms are implemented:

1. `Q2-GN`: generalized normal, `beta in {1.0,1.25,1.5,1.75,2.0}`;
2. `Q2-N`: Gaussian;
3. `Q2-T`: Student-t, `df in {4,6,10}`;
4. `Q2-EMP`: empirical residual reference.

`Q2-GN` remains the primary Q2 family. N/T/EMP are bounded preregistered references; target results may not introduce or substitute a new family.

## 4. Conditional-scale engineering rule

For parametric families:

`log(scale) = b0 + b1*favorite_size + b2*T_c + b3*favorite_size*T_c`

with `T_c=(market_total-training_fold_median_total)/10`.

Missing market total is replaced only by the training-fold median, making `T_c=0` for that row. Scale coefficients are fit by minimizing **training-only discrete negative log likelihood of the observed integer-margin bins** under the same integrated PMF used at prediction time.

The constant-scale ablation uses only `b0`.

Fixed numerical bounds are engineering guards, not searched hyperparameters:

- `b0 in [log(1), log(40)]`;
- `b1 in [-0.15,0.15]`;
- `b2 in [-0.75,0.75]`;
- `b3 in [-0.075,0.075]`.

Optimization is deterministic L-BFGS-B from a robust training-residual scale initialization. No target-period rescue or alternate optimizer search is authorized.

## 5. Key-number excess-mass rule

Only `|k| in {3,6,7,10,14}` is eligible for explicit excess mass, with the already-frozen distance bands:

- `0 <= |k-mu| < 3.5`;
- `3.5 <= |k-mu| < 7.5`;
- `|k-mu| >= 7.5`.

Positive and negative margins share each absolute-key coefficient; no sign split is introduced.

The implementation uses one log-mass coefficient for each `(absolute key, distance band)` cell. For eligible PMF cells the base mass is multiplied by `exp(theta)` and the full PMF is renormalized. `theta=0` is exactly the no-excess null.

Coefficients are fit on training rows only by penalized discrete log loss:

`-sum(log p_observed) + lambda*sum(theta^2)`

with the frozen penalty grid `lambda in {1,10,100}` selected only by prior inner chronology. Fixed coefficient bounds `[-3,3]` are numerical guards and are not searched.

Mandatory ablations remain:

- no key-number excess;
- key-number excess + constant scale;
- full key-number excess + conditional scale.

## 6. Empirical reference smoothing

`Q2-EMP` is a deterministic reference, not a new tuning surface.

Training residuals relative to the applicable center are rounded to the nearest integer using deterministic half-away-from-zero rounding and clipped to `[-75,+75]`. Residual-bin counts receive fixed Jeffreys additive smoothing `0.5` in every bin, then normalize to one.

For a target center, the empirical residual PMF is shifted by the half-away-from-zero rounded center onto margin support `[-75,+75]`; shifted tail mass is folded into the boundary bins. There is no smoothing-constant search and no target-season count use.

## 7. Q1 center chronology inside Q2

The main Q2 center remains:

`mu_Q2 = C + q0.5_Q1(R|X)`.

The Stage-A Q1 identity is not changed.

For each Q2 target season `t`, the Q1 median alpha is selected using the exact Stage-A learner, feature contract, alpha grid, 100-row minimum, pinball objective and smaller-alpha numerical tie-break, with Q1 validation targets restricted to `2019,...,t-1` and each such fold trained only on `2015,...,u-1`.

Consequences fixed before Q2 results:

- Q2 inner target **2019 is omitted** because no prior Q1 validation target exists from which to select the frozen Q1 alpha without leakage;
- Q2 inner target 2020 may use Q1 validation target 2019;
- later Q2 inner targets expand analogously;
- Q2 outer targets 2022–2025 must reproduce the frozen Stage-A Q1 median predictions on the same rows before any Q2 fit is accepted.

For a given Q2 training window, after alpha is selected using prior-only Q1 OOF pinball, one Q1 median model is fit on that entire prior training window. Its predictions on those training rows may be used to define the training residual distribution; its prediction on the target season is out-of-sample. No target-season outcome contributes to Q1 or Q2 parameters.

## 8. Q2 tuning objective and tie rules

Q2 shape choice, key-penalty choice and ablation comparison use **mean discrete CRPS / ranked probability score** on prior-only inner target rows. This fixes the preregistered `full-distribution proper score` to a single implementation before results.

For a realized integer margin `y` and support CDF `F(k)`, the row score is:

`sum_k (F(k) - 1[y <= k])^2`.

All comparisons use exact common inner rows. Numerical ties within `1e-12` use deterministic conservative ordering:

1. simpler ablation before more complex ablation: no-key constant-scale, no-key conditional-scale, key constant-scale, key conditional-scale;
2. within a family, lower shape parameter first;
3. smaller key penalty value first only after identical proper score and identical complexity class.

These are tie rules only; they do not create a new search surface.

## 9. M1 null

M1 uses the same distribution machinery and chronology but center fixed to `C=-L`, with no Q1/football location adjustment. Its parameters are fit/tuned independently on prior history. Incremental Q2 claims are relative to this exact-row market null.

## 10. Tests-before-results gate

Before any Q2 historical score is authorized, Stage B must pass synthetic/unit tests proving:

- PMF nonnegativity and sum-to-one;
- integrated-bin symmetry for symmetric families;
- tail folding at ±75;
- half-point structural `P_push=0`;
- whole-point `P_push=PMF(k=-L)`;
- cover/push/loss normalization;
- deterministic empirical smoothing/shift;
- `theta=0` reproduces the base PMF;
- key adjustments preserve normalization;
- scale features use training-only total median;
- Q2 inner chronology omits 2019 and never trains on target/future seasons;
- Q1 median reproduction on the frozen Stage-A interface;
- completed-2026 refusal;
- protected production surfaces unchanged.

Only after a dedicated contract job passes may a historical Q2 workflow execute.

## 11. Active prohibitions

No mixture model, skew family, spline density, new distribution family, new key number, new scale feature, new smoothing grid, post-hoc calibrator, new ATS threshold, completed-2026 outcome signal, or production forecast change is authorized.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
