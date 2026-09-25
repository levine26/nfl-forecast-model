# Experiment Contract

This contract is frozen before any ATS-XM candidate target-season score is generated.

## Frozen base distribution

Use the accepted `KMASS-MARKET` nuisance fits from `research/ats-historical-challenger/v2_nuisance_freeze.json`, separately by 2022–2025 outer season. The repository's `spread_line` field is already normalized to expected home margin; mathematically it is `C=-L` if `L` denotes a conventional home spread. Do not negate it again.

The full integer-margin PMF is the accepted Student-t cell probability with finite log-mass corrections only at `0`, `±3`, and `±7`, using constant scale. No new key numbers, scale model, center correction, clipping, hard support, or endpoint folding is allowed.

## Historical source signal

Reuse the immutable F-ST training archive through `load_frozen_training_frame()` and reconstruct each target-season F-ST probability with the already-accepted historical method: fit the two-logit stack on seasons strictly before the target season and score that target season only. The exact archived `market_prob` is the market comparator. Its historical horizon is not relabeled or upgraded.

Define only:

`d = logit(p_FST) - logit(p_market)`.

No generic football feature may enter a primary ATS-XM candidate.

## Candidate 1: sign-mass information projection

For base PMF q, preserve `q(0)`. Let `q+ = Pq(M>0)` and `q- = Pq(M<0)`. For target conditional non-tie home-win probability u:

- positive margins are multiplied by `((1-q0)u/q+)`;
- negative margins are multiplied by `((1-q0)(1-u)/q-)`;
- margin zero is unchanged.

Market null: `u=p_market`.

F-ST challenger: `u=logistic(logit(p_market)+alpha*d)` with alpha in `{0,.25,.50,.75,1,1.25}`. Alpha is selected only on rows preceding the target season, by mean CPL log loss. Exact ties prefer the smaller alpha. Alpha=1 is also reported as a fixed structural ablation.

## Candidate 2: mean-preserving information projection

Use the same selected alpha. Preserve normalization, q(0), target positive/negative sign masses, and the expected margin of baseline KMASS-MARKET. Solve the minimum-KL problem by exponential tilting on an adaptive integer support. Expand support until omitted q-tail mass is below `1e-12`; omitted tails are not folded into endpoints. If the constraints cannot be solved numerically, the row fails closed.

The market null uses the identical solver with `u=p_market`.

## Candidate 3: direct conditional-cover offset

From baseline KMASS CPL probabilities define `c0=Pcover/(1-Ppush)` and

`logit(c)=logit(c0)+beta*d`.

Preserve baseline push probability exactly. Beta grid is `{0,.25,.50,.75,1,1.25,1.5}`, selected only on rows preceding the target season by mean CPL log loss. Exact ties prefer the smaller beta. No intercept or interaction is allowed.

## Evaluation

Primary comparisons:

- `ATS-XM-IPROJ-FST-V1` vs `KMASS-MARKETML-IPROJ`;
- `ATS-XM-IPROJ-MEANFIX-V1` vs `KMASS-MARKETML-MEANFIX`;
- `ATS-XM-CPL-OFFSET-V1` vs beta=0 / baseline KMASS CPL.

Primary uncertainty is a deterministic 10,000-resample paired season-stratified NFL-week block bootstrap. Report raw one-sided bootstrap evidence and Holm adjustment across the three F-ST candidate comparisons. Also report per-season and leave-one-season-out deltas.

## Advancement rule

`IMPLEMENTATION_CANDIDATE` requires all user-specified gates: better primary CPL log loss than strongest matched market null; bootstrap 95% upper bound below zero; favorable in at least 3/4 outer seasons; no material calibration degradation; zero leakage/numerical failures; at least 10 candidate-vs-null side switches and no one-week concentration; ATS not materially adverse; reasonable operational complexity.

For this contract, material calibration degradation means either absolute calibration-intercept error worsens by more than 0.05 or absolute slope error from 1 worsens by more than 0.15 versus the matched null. Material ATS adversity means ex-push hit rate is at least 1.0 percentage point worse than the matched null when there are at least 10 side switches.

A favorable point estimate that misses the implementation gate may be `HISTORICALLY_PROMISING`; no material gain is `NO_MATERIAL_IMPROVEMENT`; numerical/leakage invalidity is `FAILED`.

No subset, threshold, bucket, or post-hoc calibration result may promote a candidate.
