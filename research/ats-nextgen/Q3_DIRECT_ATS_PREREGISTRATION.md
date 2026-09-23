# Q3 Preregistration — Direct ATS Probability Head

Experiment ID: `Q3-DIRECT-CPL-V1`
Status: FROZEN BEFORE RESULTS

## Scientific question

Does a model trained directly on the wagering outcome add incremental probability information beyond the chronology-clean Q1/Q2 distributional path?

## Target

Three mutually exclusive outcomes derived from the fixed residual `R=M+L`:

- `COVER` if `R>0`;
- `PUSH` if `R=0`;
- `LOSS` if `R<0`.

Pushes are not dropped from the main target.

## Frozen learner comparison

Exactly two learner families are allowed.

### Q3-LR — regularized multinomial logistic

- multinomial softmax;
- L2 penalty;
- `C in {0.1, 1.0}`;
- fixed maximum iterations sufficiently high for convergence;
- deterministic solver/random state.

### Q3-XGB — one shallow boosting family

Exactly two depth configurations are permitted:

- `max_depth in {1,2}`;
- `n_estimators=150`;
- `learning_rate=0.03`;
- `subsample=0.8`;
- `colsample_bytree=0.8`;
- `min_child_weight=20`;
- `reg_lambda=10`;
- `gamma=0`;
- objective `multi:softprob`;
- deterministic `random_state=20260923`;
- `n_jobs=1` for reproducibility.

No LightGBM alternative, deeper trees, expanded tuning grid, neural classifier or post-result rescue learner is allowed.

## Frozen feature contract

Q3 receives only chronology-clean information available before its row:

### Q1 outputs

- `q1_q476`;
- `q1_q500`;
- `q1_q524`.

### Q2 outputs

With epsilon fixed at `1e-6`:

- `q2_cover_logodds = log((p_cover+eps)/(p_loss+eps))`;
- `q2_push_prob = p_push`.

### Market state

- `S`;
- `abs_S`;
- `total_line`;
- paired-moneyline no-vig `market_home_prob` when available.

### Football state

Same exact compact feature list frozen for Q1.

No Q3-specific new football feature is allowed.

## Missingness/preprocessing

Same training-only median imputation, fixed missing indicators and training-only standardization contract as Q1.

Tree inputs use the same imputed canonical matrix rather than relying on model-specific missing-value behavior.

## Structural push constraint

For half-point spreads an exact push is impossible. After any Q3 softmax prediction on a half-point line:

1. set predicted push probability to exactly zero;
2. renormalize cover/loss probabilities to sum to one.

For whole-number spreads all three outcomes remain possible.

This mask is structural and never tuned.

## Inner learner selection

For each outer season, compare exactly four configurations:

- logistic C=.1;
- logistic C=1.0;
- XGBoost depth 1;
- XGBoost depth 2.

Primary selection score: chronology-clean inner OOF **multinomial log loss**, with validation seasons weighted equally.

Tie rule within `1e-8`:

1. logistic C=.1;
2. logistic C=1.0;
3. XGBoost depth 1;
4. XGBoost depth 2.

ATS hit rate/ROI/selective-subset results may not choose the learner.

## Probability calibration

After learner/config selection, create the chosen learner's pooled inner OOF logits. Fit exactly one scalar temperature `T` by minimizing multinomial log loss over those prior inner OOF rows subject to:

`0.5 <= T <= 3.0`.

Apply `softmax(logits/T)` to the future outer season, followed by the structural half-point push mask.

No isotonic, Platt-per-class or outer-season recalibration is allowed in V1. The outer season never participates in temperature fitting.

## Q2/Q3 blend

A blend is authorized:

`P_blend = w*P_Q2 + (1-w)*P_Q3`

with exactly:

`w in {0, 0.25, 0.50, 0.75, 1.0}`.

Both component probabilities must first satisfy the structural push rule. After blending, normalize numerically to sum to one.

Weight selection uses pooled prior inner OOF multinomial log loss with equal season weights. It may not use ATS hit rate, realized return or the outer evaluated season. Endpoints remain legal, so blending is never forced.

## Nulls/comparators

Q3 is evaluated against:

- M1 market-derived probability distribution;
- M2 market-only calibrated distribution;
- Q2 full distributional probability;
- Q3 direct probability;
- frozen Q2/Q3 blend.

A Q3 incremental claim requires improvement over Q2 full on proper probability scoring. A blended claim requires the selected blend to improve the relevant proper score without target-period weight fitting.

## Chronology

For outer season Y:

- Q1 and Q2 features supplied to Q3 must be row-wise chronology-clean predictions;
- Q3 inner learner selection uses only validation seasons earlier than Y, each predicted from still-earlier training history;
- temperature scaling uses only prior inner OOF rows;
- blend selection uses only prior inner OOF rows;
- final outer Y probabilities are produced once with all choices frozen.

Random K-fold and same-row calibration are prohibited.

## Primary metrics

- multinomial cover/push/loss log loss;
- cover Brier score;
- decisive-outcome cover log loss/Brier where applicable;
- calibration intercept/slope;
- reliability curves;
- empirical push calibration;
- key-bucket calibration;
- season-level score differences versus Q2/M2;
- ATS and economics only as secondary frozen evaluations.

## Decision interpretation

- If Q3 improves Q2 proper scoring with stable evidence, direct outcome modeling adds incremental probability information.
- If blend improves both components under the frozen prior-OOF rule, complementarity is supported.
- If flexible XGBoost wins only by ATS/ROI but not the primary log score, it does not earn selection.
- If Q3 adds no proper-score information, it is rejected/inconclusive even if a small selective subset looks profitable.