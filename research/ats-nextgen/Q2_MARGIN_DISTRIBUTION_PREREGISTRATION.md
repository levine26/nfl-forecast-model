# Q2 Preregistration — Discrete NFL Margin Distribution

Experiment ID: `Q2-DISCRETE-KEY-PMF-V1`
Status: FROZEN BEFORE RESULTS

## Scientific question

Does replacing LevLine's fixed continuous Normal-style margin bridge with a chronology-clean discrete, heavy-tail-capable, key-number-aware margin PMF improve cover/push/loss probability quality relative to market-only distribution nulls?

## Canonical output

For every eligible row, Q2 outputs:

`p_k = P(M=k | X)` for integer `k=-75,...,+75`.

The PMF sums to one. Continuous-base mass below -75 and above +75 is folded into endpoint bins so no probability disappears.

From this single PMF Q2 must deterministically derive:

- expected margin;
- median margin;
- home win/tie/loss probability;
- cover/push/loss probability at the quoted spread;
- alternate-line cover/push/loss probabilities for any integer/half-point line within support.

## Location

Candidate Q2 location is:

`mu_i = S_i + q1_mid_i`,

where `q1_mid_i` is Q1's chronology-clean official median residual prediction for that row.

M1 uses `mu_i=S_i` exactly. M2 uses `mu_i=S_i+q1_m2_mid_i`, where `q1_m2_mid_i` is the chronology-clean market-only Q1-M2 median residual. Q2 full uses the chronology-clean full-Q1 median residual.

Q2 may not refit a new outcome-dependent mean model.

## Frozen continuous base comparison

Exactly these base specifications are authorized:

1. Gaussian;
2. Student-t with `nu=8`;
3. Student-t with `nu=4`;
4. generalized normal with `beta=2.5`;
5. generalized normal with `beta=1.5`.

`beta=2` is the Gaussian and is not duplicated.

No finite mixtures, skew-normal family, BALE family, neural density estimator or post-result distribution rescue is allowed in V1.

## Discretization

For non-endpoint integer margin `k`:

`base_p(k)=F(k+0.5)-F(k-0.5)`.

For `k=-75`, include all lower-tail mass through `-74.5`. For `k=+75`, include all upper-tail mass from `74.5` upward.

The discretization rule is fixed before fitting.

## Frozen conditional scale

The positive scale is modeled as:

`log(sigma_i) = gamma0 + gamma1*abs(S_i) + gamma2*(T_i-45) + gamma3*abs(S_i)*(T_i-45)`

where `T_i` is market total after training-fold median imputation when missing.

The number 45 is a fixed centering constant, not estimated from target data. No additional pace/weather/injury/QB variance features are authorized in V1.

Scale coefficients are estimated only on eligible training history as part of penalized discrete likelihood fitting.

## Frozen key-number excess-mass model

The key set is fixed as:

`K = {0, -3,+3, -6,+6, -7,+7, -10,+10, -14,+14}`.

For key margin `k`, apply multiplicative factor `exp(delta_k)` to the discretized base probability, then renormalize the entire PMF.

All `delta_k` values are learned only from prior eligible training history. No external package's key weights or target-season key frequencies are imported.

Frozen L2 shrinkage grid on the key deltas:

`lambda_key in {1, 10}`.

The four conditional-scale coefficients are fit jointly with the key deltas under the same training objective; a weak fixed L2 penalty of `0.1` is applied to non-intercept scale coefficients to prevent numerical explosion. This penalty is not tuned on outer results.

## Inner selection rule

For each outer fold, compare exactly the 5 base specifications x 2 key-shrinkage values = 10 Q2 configurations.

Primary selection score: mean **discrete margin negative log likelihood** on chronology-clean inner OOF rows, with each inner validation season weighted equally.

Tie rule within `1e-8`, in order of parsimony:

1. Gaussian + lambda_key 10;
2. Student-t 8 + lambda_key 10;
3. Student-t 4 + lambda_key 10;
4. generalized normal 2.5 + lambda_key 10;
5. generalized normal 1.5 + lambda_key 10;
6. same base ordering with lambda_key 1.

ATS hit rate, ROI, key-bucket win percentage and outer-season results cannot choose the distribution.

## Empirical residual benchmark

Phase 2 must also report a non-selected empirical residual-distribution benchmark constructed from prior training history only, with deterministic additive smoothing. It is a diagnostic benchmark and cannot expand the Q2 candidate family or trigger post-result rescue.

Implementation detail is frozen as Laplace smoothing of one pseudo-count across the integer/half-integer residual support implied by the observed training-line grid, translated back to the row's market center and normalized on the Q2 margin support.

## Whole-number and half-point lines

Let `S=-L`.

For a whole-number market-implied margin `S`:

- `P(cover)=sum_{k>S} p_k`;
- `P(push)=p_S`;
- `P(loss)=sum_{k<S} p_k`.

For a half-point `S`:

- `P(push)=0` exactly;
- cover/loss partition all PMF mass around the boundary.

Quarter-point or other non-integer/non-half-point spreads are ineligible in V1; they are never rounded.

## Exact market nulls

### M1 — raw market distribution

Use the same selected Q2 base-family/key-mass/conditional-scale machinery, estimated with prior history only, but set location to `mu_i=S_i` exactly.

M1 inputs that can vary by row are therefore only:

- `S_i` through location and `abs(S_i)` through scale;
- `total_line` through scale;
- the fixed `abs(S)*(total-45)` scale interaction.

Key-mass parameters are prior-history calibration parameters. M1 contains no football variables, no Q1 residual, and no paired-moneyline input. Paired moneyline is reported as a market-shape diagnostic only for M1.

### M2 — market-only calibrated distribution

Use the same Q2 distribution machinery, but set location to:

`mu_i = S_i + q1_m2_mid_i`,

where `q1_m2_mid_i` comes from the chronology-clean **market-only** Q1 model using `S`, `abs(S)`, total, and paired-moneyline no-vig home probability where available.

M2 contains no football variables. It is the direct null for any claim that Q2 full adds football information rather than merely calibrating market shape.

### Q2 full

Use:

`mu_i = S_i + q1_full_mid_i`,

where `q1_full_mid_i` is the chronology-clean full-Q1 median residual using the frozen market + football feature contract. Conditional scale and key-mass machinery are otherwise the same frozen Q2 architecture.

## Moneyline constraint

Paired home/away moneyline may enter Q2 only indirectly through Q1-M2/Q1-full location calibration, according to Q1's frozen feature contract. Q2 adds no separate moneyline coefficient, matching constraint, family search or outcome-tuned transformation.

This resolves the market-null hierarchy exactly:

- M1 = quoted spread/total distribution shape;
- M2 = M1 + market-only Q1 location calibration (which may use paired-moneyline no-vig probability);
- Q2 full = M1 distribution machinery + full-Q1 location calibration.

## Chronology

Same outer/inner structure as the master plan. Critically:

- all key mass and scale parameters for outer season Y are estimated only from years <Y;
- Q1 predictions used in inner/outer Q2 rows are themselves OOF/forward predictions for those rows;
- no target-season residual standard deviation or key frequency may enter Q2;
- no same-row outcome can influence its own PMF.

## Primary Q2 metrics

- discrete margin log score/NLL;
- ranked probability score / discrete CRPS equivalent;
- cover Brier and cover log loss;
- multinomial cover/push/loss log loss;
- calibration intercept/slope for decisive cover probability;
- empirical push calibration;
- calibration around frozen key-number buckets;
- expected-margin MAE/RMSE as secondary diagnostics;
- median absolute error;
- PMF normalization/tail diagnostics.

## Decision interpretation

Q2 can establish:

- **distribution calibration value** if M1/M2 improve raw market probability representation under proper scoring;
- **incremental football-distribution information** only if full Q2 improves M2 under proper scoring with stable season evidence.

Realized ATS/ROI cannot rescue a proper-score failure.