# ATS Next-Generation — Q2 Stage B Scoring/Reporting Receipt

**Status:** PRE-RESULT; no accepted Q2 historical performance generated.  
**Parent contract:** `Q2_STAGE_B_OPENING_RECEIPT.md`  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

This receipt freezes reporting semantics that the Phase-1 evaluation protocol names but does not numerically disambiguate. The calibration/interval additions below are frozen before any accepted Q2 result and do not change model fitting, tuning, candidate identity, or primary selection.

## Proper distribution scores

- Discrete CRPS/RPS is exactly the sum over thresholds `k=-75,...,74` of `(F(k)-I[y<=k])^2`.
- Multinomial CPL log loss uses the raw `(P_cover,P_push,P_loss)` vector and the realized three-way ATS outcome.
- Evaluation-only probability floor is `1e-15`; stored model probabilities are never clipped or recalibrated.

## Binary cover scores

A realized push is not a binary cover/loss observation. Therefore:

- realized pushes are excluded from cover Brier/log-loss and cover reliability;
- on non-push rows, the binary home-cover probability is the model's conditional probability `P_cover/(P_cover+P_loss)`;
- if that denominator is nonpositive or nonfinite, fail closed;
- no push is relabeled as a loss or half-win.

This convention is fixed before Q2 results and is applied identically to M1 and Q2 arms.

## Cover calibration intercept/slope

The Phase-1 protocol requires calibration intercept/slope where estimable. Pre-result implementation is fixed as a logistic calibration regression on non-push rows:

`logit(P(observed home cover)) = a + b*logit(p_model)`

where `p_model=P_cover/(P_cover+P_loss)`.

- model probabilities are clipped only inside this evaluation calculation to `[1e-15,1-1e-15]` for finite logits;
- `(a,b)` are estimated by deterministic unpenalized binomial negative-log-likelihood optimization;
- if the observed binary outcome has fewer than two classes or the logit predictor is degenerate, intercept/slope are reported as unavailable (`NaN`) rather than rescued with a different estimator;
- these calibration coefficients are descriptive evidence only and are never fed back into predictions.

## Margin summaries and interval coverage

- expected margin is `sum_k k*P(M=k)`;
- median margin is the smallest integer support value whose cumulative probability is at least `0.5`;
- MAE/RMSE for expected and median margin are secondary interpretability metrics only.

The preregistered secondary `interval coverage` diagnostic is frozen to exactly three equal-tailed central intervals:

- 50%: quantiles 0.25 to 0.75;
- 80%: quantiles 0.10 to 0.90;
- 90%: quantiles 0.05 to 0.95.

For each level, report empirical coverage and mean integer interval width. A discrete quantile is the smallest support value whose CDF is at least the requested probability. No alternative interval level may be added after Q2 results for V1 selection.

## Push calibration

Report mean predicted push probability and empirical push frequency:

- overall;
- by season;
- on the frozen key-number reporting buckets.

Half-point lines retain structural predicted push probability zero and cannot realize an integer-margin push. Whole-line push probability is the exact PMF mass at `k=-L`.

## Direct key-margin mass calibration

Because Q2 explicitly models excess probability at NFL key margins, report a second, distinct key diagnostic on realized **final margin**, not merely quoted-spread buckets.

For each `a in {3,6,7,10,14}` report:

- predicted probability `P(|M|=a)=P(M=-a)+P(M=+a)`;
- empirical frequency `I(|M|=a)`;
- calibration error = predicted rate minus empirical rate;
- sample count;
- overall and by outer season.

This diagnostic is reported for every frozen M1/Q2 arm and may diagnose the key-mass mechanism, but it cannot rescue a candidate that fails the primary paired proper-score comparison.

## Reliability bins

Cover reliability uses exactly the Phase-1 fixed bins:

`[0,.1), [.1,.2), ..., [.8,.9), [.9,1]`.

Report bin count, mean predicted conditional cover probability and empirical cover rate. Empty bins remain explicit under a deterministic reporting rule; bins are never merged after results.

## Frozen Stage-B arm set

For each center mode (`M1` market center and `Q2` Q1-adjusted center), report exactly:

1. generalized normal, no-key + conditional scale;
2. generalized normal, key excess + constant scale;
3. generalized normal, key excess + conditional scale (**primary GN arm**);
4. Gaussian, key excess + conditional scale;
5. Student-t, key excess + conditional scale;
6. empirical residual reference.

Thus the historical OOF package contains 12 paired arms. Q2's primary incremental claim is `Q2_GN_FULL` versus `M1_GN_FULL` on exact common rows. The other families and mandatory ablations are bounded preregistered references, not post-result rescue options.

## Inner selection pooling

For each continuous arm and outer target, every candidate shape/key-penalty combination is fitted separately inside each available prior inner target. Candidate selection minimizes **pooled row-level inner discrete CRPS** across those prior target seasons, not the unweighted mean of season means.

The 2019 Q2 inner target remains mechanically omitted under the opening receipt. No target-period score may alter this rule.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
