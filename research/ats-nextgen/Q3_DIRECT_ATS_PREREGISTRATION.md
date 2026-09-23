# Q3 Preregistration — Direct Cover/Push/Loss Probability Head

**Candidate ID:** `ATS-Q3-DIRECT-CPL-HURDLE-V1`  
**Phase-1 status:** frozen design; untrained; no candidate performance generated

## 1. Scientific question

Does a discriminative model trained directly on spread outcomes add incremental probability information beyond the market and Q2's generative margin distribution?

## 2. Target

Use the same ATS residual:

`R = M + L`.

Outcomes:

- cover if `R>0`;
- push if `R=0`;
- loss if `R<0`.

Pushes are never silently coded as losses or removed from the three-outcome probability evaluation.

## 3. Structural hurdle architecture

Q3 is a two-part model that produces a coherent three-outcome probability vector.

### Head A — push model

Fit an L2-regularized logistic model only on **whole-number spread** rows:

`p_push = P(push | X, whole-line)`.

For half-point spreads, set `p_push = 0` by structural contract rather than asking a classifier to learn an impossible event.

### Head B — conditional cover model

Fit an L2-regularized logistic model on non-push rows:

`q = P(cover | nonpush, X)`.

Combine:

- `P(push) = p_push`;
- `P(cover) = (1-p_push)*q`;
- `P(loss) = (1-p_push)*(1-q)`.

This preserves exact unit-sum probability and structural zero pushes on half-lines.

## 4. Learner and regularization

Only standard L2-regularized logistic regression is authorized in V1.

Fixed inverse-regularization grid:

`C ∈ {0.01, 0.1, 1.0, 10.0}`.

The pair of head hyperparameters is selected inside inner rolling-origin chronology by combined multinomial log loss. No class reweighting is allowed; push rarity is part of the probability problem and must not be artificially balanced.

No LightGBM, XGBoost, random forest, neural net, GAM, isotonic calibrator or post-result replacement learner is authorized in V1.

## 5. Feature contract

The cover head uses the exact compact market + football feature hierarchy in `DATA_AND_PIT_INVENTORY.md`.

The push head uses the same market features plus fixed binary indicators that the **absolute quoted spread number** is exactly one of:

`3, 6, 7, 10, 14`.

The push head may also use favorite size × centered total. It may not use target-season push frequency, realized game score components or postgame state.

## 6. Nulls

- **Q3-M2:** identical hurdle architecture using market features only.
- **Q3:** market + compact football state.
- **Q2:** evaluated as the generative comparator on exact common rows.

An incremental Q3 claim requires proper-score improvement over Q3-M2 and evidence of complementary value versus Q2, not merely higher ATS hit rate on a selected subset.

## 7. Calibration policy

No post-hoc probability calibration layer is authorized in V1. Raw chronology-clean probabilities are evaluated directly for:

- multinomial log loss;
- cover Brier;
- calibration intercept/slope for cover where defined;
- reliability curves;
- push calibration.

Poor calibration is a result, not permission for isotonic/Platt rescue.

## 8. Q2/Q3 blend policy

A probability blend **is authorized**:

`P_final = w*P_Q2 + (1-w)*P_Q3`

component-wise for cover/push/loss.

Frozen weight grid:

`w ∈ {0, 0.25, 0.50, 0.75, 1.0}`.

Select `w` only inside inner chronology by multinomial log loss on prior OOF rows. Never select the weight from final outer ATS hit rate, ROI, favorite slices or target-season performance.

No separate weights by season, side, spread bucket, key number or book in V1.

## 9. Chronology

Same outer 2022–2025 expanding-season evaluation and inner rolling-origin tuning contract as Q1/Q2.

For each outer target season, all logistic preprocessing, medians, scaling, coefficients and C selection come from prior-time rows only.

## 10. Scientific interpretation

Q3 is intended to falsify or complement Q2, not replace it because a classifier happens to win a noisy ATS slice. If Q3 proper scores fail against market-only Q3-M2, it is rejected even if a small realized betting subset looks favorable.