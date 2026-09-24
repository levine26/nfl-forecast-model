# M1 PREREGISTRATION

## Identity

`FV2-PROS-M1-MARKETSTATE-01`

Historical state: `BLOCKED_PENDING_PAID_SOURCE`  
Research state: `PROSPECTIVE_ONLY`

No historical Phase-4 fitting is authorized.

## Scientific mechanism

Multiple contemporaneous books/prices are noisy observations of a latent market state. Information potentially lost by a single consensus spread includes side-price movement at an unchanged number, cross-book disagreement, active-book breadth, stale quotes and path movement preceding the decision horizon.

The mechanism must add information beyond **same-horizon market level**. A later market level reproducing a gain is not evidence for path information.

## Prospective prediction horizon

Primary: `T-120`.

Context path may use only captures at or before:

- T-2160;
- T-720;
- T-360;
- T-120.

T-60/T-30/latest-pre-kick are collected for later-market intermediate evaluation and calibration diagnostics but may not enter the T-120 predictor.

## Compact frozen feature set

At T-120:

1. consensus spread median;
2. consensus no-vig favorite/underdog side probability from spread prices;
3. consensus no-vig moneyline probability;
4. consensus total;
5. cross-book spread dispersion;
6. active-book count / breadth;
7. median quote age and stale-book share;
8. T-360 to T-120 consensus number movement;
9. T-360 to T-120 price movement conditional on unchanged number;
10. T-360 to T-120 movement breadth;
11. key-number crossing indicator for 3 or 7;
12. spread/moneyline consistency residual.

Leader/follower features are **not** in V1. The public-source audit cannot distinguish true price discovery from provider/feed latency robustly enough to justify them in the first frozen identity.

## Future-market intermediate target

Separately preregistered diagnostic target:

`later_consensus_spread_at_T60 - consensus_spread_at_T120`

and, where price is complete:

`later_no_vig_side_probability_at_T60 - T120_no_vig_side_probability`.

This is explicitly distinct from final ATS outcome.

## Final-outcome target

Cover/push/loss distribution at the T-120 quoted spread, only in future games recorded prospectively before kickoff.

## Model family

A compact regularized linear state model is frozen for first prospective use:

- standardized continuous features using prior-only moments;
- ridge regression for later-market intermediate target;
- ridge multinomial-logit correction around the static T-120 market probability for cover/push/loss;
- regularization selected only from `{10, 100}` using chronology-clean prior prospective observations once a future training window exists.

No tree/boosting/neural family search is authorized for this identity.

## Null

Same T-120 market state with all path/dispersion/staleness features removed. Market level, price, moneyline and total remain in the null so M1 cannot claim victory over a straw baseline.

## Primary metric

Multinomial cover/push/loss log loss on prospectively frozen rows versus the static market-state null.

Secondary: Brier, calibration intercept/slope, reliability, later-market prediction error. ATS hit rate/ROI are diagnostics only.

## Failure condition

The identity fails to establish dynamic-path information if the full model does not improve paired proper score versus the same-horizon market-state null, or if any apparent gain disappears in the path-feature ablation.

## Historical reopening rule

No historical model may be fit unless the paid/free data gate is amended before any M1 outcome inspection. The amendment must preserve this identity or explicitly open a new version; it may not silently retrofit a favorable horizon or book set.