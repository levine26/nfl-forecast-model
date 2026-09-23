# ATS Next-Generation — Q2 Stage B Opening Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** B — Q2 only  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Status at receipt:** **AUTHORIZED TO IMPLEMENT; UNTRAINED; NO Q2 PERFORMANCE GENERATED**  
**Stage branch:** `research/ats-nextgen-phase2-q2`  
**Opening base:** verified merged `main` at `a2581a62e3797a6ac466d614326bc72b7d5a1c57` (PR #560)

## 1. Stage-A handoff is immutable

Stage A is complete. Q1 V1 is a valid negative incremental result and may not be redesigned or rescued.

The Q2 handoff uses the frozen Q1 implementation and evidence interface:

- Q1 accepted result head: `f14e2fa3ec78bf95578b4a5030fb66e94cd12cd0`;
- accepted Q1 workflow: `35920622523` (#7);
- accepted Q1 artifact ID: `10776898518`;
- Q1 outer-OOF SHA-256: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- final Stage-A receipt head `f4b6ee25c25ea439a3451194030373cd035a4463` regenerated all six Q1 evidence files identically before merge;
- completed-2026 outcomes used: 0;
- production forecasting changed: no.

Q2 must fail closed if its Stage-A outer-center regeneration does not reproduce the frozen Q1 OOF identity.

## 2. Frozen Q2 scientific identity

This stage implements `Q2_MARGIN_DISTRIBUTION_PREREGISTRATION.md` exactly:

- integer margin support `k=-75,...,+75`;
- Q2 center `mu = C + q0.5_Q1(R|X)`;
- market null M1 center `mu = C`;
- continuous families exactly generalized normal, Gaussian, and Student-t;
- empirical discrete residual reference Q2-EMP;
- generalized-normal beta grid exactly `{1.0,1.25,1.5,1.75,2.0}`;
- Student-t df grid exactly `{4,6,10}`;
- conditional scale exactly `log(scale)=b0+b1*|L|+b2*T_c+b3*|L|*T_c`;
- key margins exactly `|k| in {3,6,7,10,14}`;
- key distance bands exactly `<3.5`, `3.5-<7.5`, `>=7.5`;
- key L2 penalty grid exactly `{1,10,100}`;
- mandatory no-key, key+constant-scale, and key+conditional-scale ablations;
- primary selection by full-distribution proper score, never ATS hit rate or ROI;
- no completed-2026 outcomes.

## 3. Exact continuous-to-integer discretization

Before any Q2 historical score exists, Stage B freezes CDF bin integration as the only V1 discretization:

- for interior integer `k`, `P(M=k)=F(k+0.5)-F(k-0.5)`;
- `P(M=-75)=F(-74.5)`, folding all lower tail into the left endpoint;
- `P(M=+75)=1-F(74.5)`, folding all upper tail into the right endpoint;
- final PMFs must be nonnegative and sum to one to numerical tolerance;
- observed margins outside `[-75,75]` fail closed.

Continuous-family parameterization is the installed SciPy location/scale contract:

- generalized normal: `scipy.stats.gennorm(beta, loc=mu, scale=scale)`;
- Gaussian: `scipy.stats.norm(loc=mu, scale=scale)`;
- Student-t: `scipy.stats.t(df, loc=mu, scale=scale)`.

No point-density approximation is authorized.

The total endpoint probability `P(-75)+P(+75)` is reported for every prediction. A maximum endpoint mass above `1e-3` is frozen as a material boundary-mass failure for V1; the historical result must fail closed rather than widen support after inspection.

## 4. Frozen scale fitting

For each continuous family/shape and each training window:

1. market total is imputed from the training-window median only;
2. `T_c=(market_total-training_median_total)/10`, so a missing total maps to `T_c=0` after fold-local imputation;
3. constant-scale ablation fits only `b0`;
4. conditional-scale fits exactly `b0,b1,b2,b3`;
5. coefficients minimize mean negative **discrete observed-bin log likelihood** on training rows using the same integrated PMF definition used for scoring;
6. optimization is deterministic via SciPy L-BFGS-B from `b0=log(max(training residual SD,1.0))`, remaining coefficients zero;
7. numerical scale guard is fixed at `[0.25,100]`; a final fitted training or target row touching either guard invalidates that fit rather than becoming a tunable clipping device.

No football, QB, injury, weather, news, side-price, movement, or book-dispersion variance predictor may enter Q2 V1.

## 5. Frozen key-number excess fit

Positive and negative margins share the same absolute-key coefficient in V1. No target result may reopen sign-specific parameters.

For each row and key bin `k in {+/-3,+/-6,+/-7,+/-10,+/-14}`:

- assign the key bin to one of the three frozen bands using `|k-mu|`;
- multiply that base-bin mass by `exp(theta[abs(k), band])`;
- leave non-key bins at multiplier one;
- renormalize the entire 151-bin PMF.

There are exactly 15 key-excess coefficients (5 absolute keys x 3 bands). They are fit with scale parameters held fixed by minimizing training discrete negative log likelihood plus `0.5 * lambda * ||theta||^2`.

`lambda` is selected only from `{1,10,100}` by prior-time inner discrete CRPS. If CRPS values are equal within `1e-12`, choose the **larger lambda** (stronger shrinkage). No additional key, band, penalty, sign split, or post-hoc key calibration is authorized.

## 6. Frozen shape and ablation selection

Inner selection uses pooled prior-time discrete CRPS / ranked probability score on the registered rolling-origin validation rows.

Deterministic numerical ties within `1e-12` use the more regular/simple shape:

- generalized normal: larger `beta`;
- Student-t: larger `df`;
- key penalty: larger `lambda`.

Gaussian has no shape search. Each mandatory ablation is evaluated as frozen; an ablation result may not create a new model family.

M1 uses the same family/scale/key machinery and tuning procedure as the paired Q2 arm, differing only in center (`C` rather than `C+Q1 median residual`). The primary incremental comparison is Q2-GN versus its paired M1-GN null on exact common rows.

## 7. Frozen empirical reference

Q2-EMP is a standalone empirical residual-distribution reference; it does not receive an additional parametric scale or key-excess head because its training residual frequencies already contain the empirical shape/key structure.

For a training window:

- residual draw `e_i = observed_margin_i - training_center_i`;
- for target center `mu*`, shift each draw to `mu* + e_i` and count it into the same half-integer margin bins with endpoint tail folding;
- add a symmetric Dirichlet smoothing mass with **total pseudocount 1.0**, distributed uniformly across all 151 bins (`1/151` per bin);
- normalize exactly.

This smoothing constant is fixed before results and is not searched.

M1-EMP uses market centers for both training residual construction and target shift. Q2-EMP uses the frozen Q1-centered training/target interface described below.

## 8. Frozen Q1 stacking chronology inside Q2

Q1 remains unchanged. Stage B may reuse its frozen preprocessing, alpha grid, tie-break, and median learner but may not modify Q1 source code in response to Stage-A results.

For every Q2 **target** season (inner or outer), the Q1 target center must be strictly out of sample:

- upstream Q1 is fit only through the preceding season;
- its median alpha is selected only from earlier rolling-origin Q1 validation seasons under the frozen Q1 rules;
- the Q2 target season never contributes to the Q1 alpha, preprocessing, or fit.

For a Q2 training window, the upstream Q1 median model selected for that Q2 target is refit on the entire Q2 training window and its fitted centers may be used on those training rows when estimating Q2 distribution parameters. This does not expose the Q2 target outcome and is frozen here before Q2 results.

The first registered Q2 inner target, 2019, has no earlier Q1 inner-validation season from which a median alpha can be selected. Therefore **Q2 inner target 2019 is mechanically omitted** and recorded; no default alpha, random CV, or target-2019 tuning is allowed. For targets 2020 onward, Q1 median tuning uses exactly prior targets `2019..target-1`.

For outer targets 2022–2025, the generic Stage-B Q1-center generator must reproduce the existing frozen Stage-A Q1 median predictions. The complete regenerated Stage-A outer OOF must reproduce SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365` before any Q2 outer score is accepted.

## 9. Frozen scoring details

Discrete CRPS/RPS for observed integer margin `y` is the sum over support thresholds `k=-75,...,74` of `(F(k)-1[y<=k])^2`.

Cover/push/loss comes directly from the PMF and sportsbook home spread `L`:

- cover: sum where `k+L>0`;
- push: sum where `k+L=0`;
- loss: sum where `k+L<0`.

Half-point lines must have push probability exactly zero. Whole-number push probability must equal the PMF at `k=-L`.

Log-loss calculations use an evaluation-only probability floor `1e-15` to prevent `log(0)`; the stored model probabilities themselves are not clipped or recalibrated.

## 10. Tests-before-results boundary

Before Q2 historical execution, Stage B must test at minimum:

- PMF nonnegativity and sum-to-one;
- CDF monotonicity;
- symmetry for known zero-centered symmetric distributions;
- exact endpoint tail folding;
- exact whole-line push extraction and half-line zero push;
- key-excess normalization and shared-sign coefficient contract;
- training-only total centering;
- scale-guard failure behavior;
- Q2-EMP deterministic smoothing/normalization;
- 2019 inner-target omission and no random fallback;
- generic Q1 center chronology;
- exact reproduction of Stage-A outer Q1 median interface / OOF hash;
- completed-2026 exclusion;
- no production-surface mutation.

Q2 historical performance may exist only after these contract tests pass on the exact implementation head. No Q2 result may be used to alter any rule in this receipt.

Q3 remains unopened.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
