# PHASE 5 M4 CLASSIFICATION

## Frozen identity

Candidate: `FV2-HIST-M4-DMARGIN-01`  
Null: `M4-NULL-STUDENTT-CONSTANT-01`

Final Phase-5 classification: **`REJECTED`**.

## Primary hypothesis

Can the frozen full M4 representation—a market-centered, tail-safe Student-t integer PMF with both conditional scale and compact 0/|3|/|7| key-mass offsets—improve probability quality around NFL betting lines relative to the strong constant-scale Student-t null?

## OOF population

- outer development seasons: `2022–2025`, explicitly development/non-pristine;
- exact common rows: `1087`;
- completed-2026 outcomes used: `0`.

## Primary result

- candidate integer-margin log score: `3.852975162486858`;
- strong-null integer-margin log score: `3.935646861629811`;
- candidate-minus-null: `-0.08267169914295289`;
- lower is better, so the frozen full candidate strongly improves the primary proper score.

## Bootstrap uncertainty

Frozen 10,000-resample season-stratified NFL-week block bootstrap:

- 95% interval: `[-0.10748698706212485, -0.05796293485132338]`;
- descriptive `P(delta < 0)`: `1.0`;
- weeks: `72`.

The primary-score improvement is statistically stable under the frozen uncertainty procedure.

## Season stability

The primary delta is favorable in all four outer seasons: `2022`, `2023`, `2024`, and `2025`.

## Calibration-relative result

Null-side calibration was derived only from preserved canonical OOF probabilities under the frozen diagnostic:

- null intercept/slope: `0.0 / 0.0`;
- candidate intercept/slope: `0.01477013532177962 / 0.4366590498000353`.

Relative to null:

- absolute-intercept worsening: `0.01477013532177962` < `0.03`;
- null absolute slope departure from 1: `1.0`;
- candidate absolute slope departure from 1: `0.5633409501999647`;
- slope departure improves by `0.4366590498000353` rather than worsening.

M4 therefore passes the frozen calibration-relative eligibility gate. No exception is needed.

## Numerical / red-team result

- PMF/numerical audit: `PASS`;
- tail audit: `PASS`;
- finite-support endpoint folding: `NO`;
- chronology/leakage/red-team audit: `PASS`.

## Preregistered ablation result

The frozen ablation protocol defines:

1. `CONSTANT_SCALE_NO_KEY` — strong null;
2. `CONDITIONAL_SCALE_NO_KEY` — heteroskedastic scale only;
3. `CONSTANT_SCALE_KEY` — key-mass offsets only;
4. `FULL_CONDITIONAL_SCALE_KEY` — frozen candidate.

Accepted Phase-4 evidence:

- `CONDITIONAL_SCALE_NO_KEY - null`: `+0.00012506107970626913` — slightly worse;
- `CONSTANT_SCALE_KEY - null`: `-0.08271839184340689` — reproduces essentially the entire gain;
- `FULL_CONDITIONAL_SCALE_KEY - CONSTANT_SCALE_KEY`: `+0.00004669270045401389` — the full model is slightly worse than the simpler key-mass ablation.

### Explicit Phase-5 ablation adjudication

**Yes. The frozen rejection clause concerning a simpler preregistered component reproducing the result applies to `FV2-HIST-M4-DMARGIN-01`.**

The Phase-3 candidate identity is the full conditional-scale-plus-key-mass representation. `CONSTANT_SCALE_KEY` was explicitly preregistered as a simpler ablation, not as an alternate candidate. The conditional-scale component contributes no improvement versus the strong null, while the simpler key-mass ablation reproduces slightly more than the full candidate's gain. Under `EVALUATION_PROTOCOL.md`, that is a direct rejection condition even though the full candidate otherwise passes the primary-score, bootstrap, season-stability, numerical, leakage, and calibration gates.

The M4 mechanism is not redefined after observing the results. `CONSTANT_SCALE_KEY` is not promoted, renamed, or sent to Phase 6.

## ATS diagnostic

`540-518-29`, ex-push hit rate `51.04%`.

ATS is diagnostic only and does not enter the classification.

## Frozen clauses applied

### Eligibility evidence before ablation override

1. Candidate mean primary score better than null: **PASS**.
2. 95% paired week-block interval entirely below 0: **PASS**.
3. No numerical/leakage failure: **PASS**.
4. Calibration not materially degraded: **PASS**.
5. Improvement not wholly concentrated in one season / >=10 rows: **PASS**.

### Rejection clause triggered

- `candidate mechanism ablation shows that the claimed mechanism contributes no improvement while a simpler preregistered component reproduces the result`: **TRIGGERED**.

Because `REJECTED` applies if any frozen rejection condition is met, the ablation clause controls the final classification.

## Scientific interpretation

Phase 4 found a strong and season-stable representation signal associated with NFL discrete scoring/key-number mass. It did **not** validate the frozen full M4 candidate mechanism as specified, because conditional variance modeling added no value and slightly degraded the simpler key-mass representation.

## What this does not establish

The result does not establish a durable betting edge, production readiness, or prospective validity. It also does not invalidate discrete integer-margin modeling or the key-mass finding. The key-mass-only representation survives only as future-version hypothesis evidence requiring a new candidate identity, new preregistration, fresh governance, and a legitimate future validation path.