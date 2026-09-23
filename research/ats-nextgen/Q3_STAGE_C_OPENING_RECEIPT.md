# ATS Next-Generation — Q3 Stage C Opening Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** C — Q3 only  
**Candidate:** `ATS-Q3-DIRECT-CPL-HURDLE-V1`  
**Status at receipt:** **AUTHORIZED TO IMPLEMENT; UNTRAINED; NO Q3 PERFORMANCE GENERATED**  
**Stage branch:** `research/ats-nextgen-phase2-q3`  
**Opening base / verified Stage-B merge:** `16859845573c3344ed82ae0b9bd27fa8b891eee4`  
**Date:** 2026-09-23 America/Los_Angeles

## 1. Immutable upstream state

Stage A Q1 and Stage B Q2 are closed scientific records.

### Q1

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` is a valid negative incremental result versus M2. It may not be redesigned or rescued.

Frozen Q1 OOF SHA-256:

`d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`

### Q2

`ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` is structurally invalid under its frozen `[-75,+75]` support / `1e-3` endpoint-mass contract. Its controlling pre-result execution failed closed before a complete Q2 OOF artifact existed.

Therefore:

- there is **no valid Q2 OOF probability distribution** available to Stage C;
- Q3 may still test its preregistered incremental claim against Q3-M2;
- Q2-complementarity evidence is **unavailable due upstream structural invalidation**;
- the authorized Q2/Q3 blend is **not computable in V1** and may not be replaced with another comparator or reconstructed Q2;
- this absence may not motivate a Q2 rescue inside Stage C.

Completed-2026 outcomes remain prohibited. Production F-ST/Sunday Signal numerical behavior remains unchanged.

## 2. Frozen Q3 architecture

Q3 is exactly the Phase-1 two-head hurdle.

### Head A — push

- learner: standard L2 logistic regression only;
- training rows: eligible **whole-number spread** rows only;
- target: push = 1, non-push = 0;
- half-point target rows: `p_push = 0` exactly, without classifier prediction;
- no class weighting or resampling.

### Head B — conditional cover

- learner: standard L2 logistic regression only;
- training rows: eligible **non-push** rows only;
- target: cover = 1, loss = 0;
- prediction `q = P(cover | nonpush, X)` is evaluated for every eligible target row.

Final probabilities are exactly:

- `P(push)=p_push`;
- `P(cover)=(1-p_push)*q`;
- `P(loss)=(1-p_push)*(1-q)`.

The implementation must fail if any probability is non-finite/outside `[0,1]` or if row sums differ from one by more than `1e-12`.

## 3. Frozen line lattice

Historical Q3 V1 accepts only spread numbers on the NFL whole/half-point lattice.

For canonical sportsbook home spread `L`:

- whole line: fractional absolute value is zero within `1e-9`;
- half line: fractional absolute value is `0.5` within `1e-9`;
- any other fractional line fails closed rather than being silently rounded.

Half-point rows must have realized push = false and predicted `P(push)=0` exactly.

## 4. Frozen features

All Q3 features come only from the compact V1 hierarchy in `DATA_AND_PIT_INVENTORY.md`.

### Cover head

Q3-M2 uses the frozen market feature design only.

Q3 uses the frozen market + compact football feature design.

The design reuses the already-frozen Q1 fold-local feature semantics:

- mandatory market fields: home spread, market home-margin center, favorite size;
- optional market total and no-vig home moneyline probability with missing indicators;
- fixed market-center × centered-total interaction;
- fixed favorite-size × centered-total interaction;
- for Q3 only, the 11 compact football features with fold-local medians and missing indicators.

No new football feature family or interaction is authorized.

### Push head

Both Q3-M2 and Q3 use the same **market-only** push design, plus exactly five binary indicators that `abs(L)` is exactly:

`3, 6, 7, 10, 14`.

No football feature enters the V1 push head. The same frozen market interactions remain present, including favorite-size × centered-total.

## 5. Frozen preprocessing

Every inner/outer fit uses training rows only.

- optional numeric medians are training-fold medians;
- missingness indicators follow the frozen feature contract;
- continuous/base design scaling uses training-only mean/standard deviation;
- zero/non-finite scale is deterministically replaced by 1.0;
- the five push key indicators are standardized using training whole-line rows only;
- target rows never influence medians, scaling, feature inclusion or coefficients.

The implementation may reuse the frozen Q1 market/full preprocessor as an upstream deterministic transform; Q1 fitting/results are not reopened by this reuse.

## 6. Frozen logistic implementation

Use `sklearn.linear_model.LogisticRegression` with:

- penalty: L2;
- inverse regularization `C` from the frozen grid `{0.01, 0.1, 1.0, 10.0}` only;
- solver: `lbfgs`;
- intercept: enabled;
- class weights: none;
- maximum iterations: 2000;
- deterministic binary probability output from `predict_proba`.

A training submodel must contain at least 100 rows and both binary classes. Otherwise that inner/outer fit fails closed; no random CV/default probability fallback is allowed.

## 7. Frozen hyperparameter selection

For each candidate arm and outer target, search all 16 ordered pairs:

`(C_push, C_cover) ∈ {0.01,0.1,1,10}²`.

Use the frozen inner rolling-origin targets `2019..outer-1`, with each inner target fit only on 2015..target-1.

Selection metric is pooled row-level three-outcome multinomial log loss across all usable prior inner target rows.

Evaluation-only probability floor for the logarithm is `1e-15`; stored probabilities are not clipped or recalibrated.

If pair losses are equal within `1e-12`, choose deterministically:

1. smaller `C_push` (stronger push-head regularization);
2. then smaller `C_cover` (stronger cover-head regularization).

No ATS hit rate, ROI, season slice or key bucket may select the pair.

## 8. Frozen arm/null comparison

Exactly two Q3 hurdle arms are primary in Stage C:

1. `Q3_M2` — market-only cover head + common market/key push head;
2. `Q3` — market+football cover head + common market/key push head.

Both are fit/tuned independently under the same 16-pair grid and chronology.

The primary incremental question is whether Q3 improves three-outcome proper score over Q3_M2 on exact common 2022–2025 outer OOF rows.

No Q2 proper-score comparison or Q2/Q3 blend will be fabricated because Q2 V1 has no valid OOF distribution.

## 9. Frozen reporting semantics

Primary:

- multinomial cover/push/loss log loss on all exact common eligible rows.

Calibration/secondary:

- conditional cover Brier and binary log loss on realized non-push rows, using `P_cover/(P_cover+P_loss)`;
- cover calibration intercept/slope where estimable;
- fixed decile reliability bins `[0,.1),...,[.9,1]` on realized non-push rows;
- mean predicted push probability versus empirical push frequency overall, by season and by the frozen quoted-spread key buckets;
- per-season proper-score estimates;
- exact common-row counts.

ATS hit rate/ROI/selective slices remain non-selecting diagnostics and cannot rescue failed proper-score evidence.

No post-hoc isotonic, Platt or other calibration layer is authorized.

## 10. Tests-before-results gate

Before any Q3 historical result exists, exact-head CI must prove at minimum:

- canonical ATS cover/push/loss grading remains unchanged;
- whole/half-line lattice detection is exact and quarter-point/off-lattice lines fail closed;
- push-head fitting sees whole-number rows only;
- half-point target `p_push` equals exactly zero;
- half-point realized pushes are impossible;
- pushes remain present in three-outcome evaluation and are never relabeled losses;
- no class weighting/resampling;
- hurdle cover/push/loss probabilities are finite, nonnegative and sum to one within `1e-12`;
- Q3 C grid is exactly `{0.01,0.1,1,10}` and pair search is exactly 16 combinations;
- pair selection uses prior-time pooled multinomial log loss only;
- training-only medians/scaling;
- Q3-M2 excludes football features;
- Q3 cover head uses exactly the frozen compact football set;
- push head uses market + exactly the five frozen key indicators and no football features;
- outer targets are exactly 2022–2025 and random K-fold is absent;
- completed-2026 outcomes are rejected;
- production surfaces are unchanged.

Only after this contract passes on the exact implementation head may Q3 historical development execute.

## 11. Repeated-use disclosure

Every Stage-C result must state:

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.

Q3 remains research-only. Stage D remains unopened until Stage C closes.