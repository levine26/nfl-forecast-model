# ATS Next-Generation — Q3 Stage C Scoring/Reporting Receipt

**Candidate:** `ATS-Q3-DIRECT-CPL-HURDLE-V1`  
**Status:** **PRE-RESULT; NO Q3 HISTORICAL PERFORMANCE GENERATED**  
**Parent:** `Q3_STAGE_C_OPENING_RECEIPT.md`

This receipt freezes Stage-C reporting details before any Q3 historical result exists.

## Primary proper score

The primary Q3 score is row-level three-outcome multinomial log loss on the raw chronology-clean vector `(P_cover,P_push,P_loss)`.

The evaluation-only log floor is `1e-15`. Stored probabilities are never clipped, calibrated, or altered by the scoring layer.

The primary incremental comparison is paired exact-row:

`Q3 - Q3_M2`

on aggregate 2022–2025 outer OOF multinomial log loss. Lower is better.

Q2 proper-score comparison and Q2/Q3 blending are unavailable because Q2 V1 has no valid OOF distribution. Their absence may not be filled with a reconstructed or widened-support Q2.

## Cover score convention

Pushes are three-outcome observations and remain in multinomial scoring, but a realized push is not a binary cover/loss observation.

For binary cover diagnostics:

- exclude realized pushes;
- use conditional non-push cover probability `P_cover/(P_cover+P_loss)`;
- report Brier score and binary log loss;
- fail closed if the denominator is non-finite/nonpositive.

## Cover calibration

Calibration intercept/slope is diagnostic only and never feeds predictions.

On non-push rows:

1. compute conditional cover probability `q=P_cover/(P_cover+P_loss)`;
2. for numerical diagnostic fitting only, clip `q` to `[1e-15,1-1e-15]` before logit transformation;
3. fit unregularized binary logistic regression of realized cover on `logit(q)` using `lbfgs`, intercept enabled, no class weights, max 2000 iterations;
4. report fitted intercept and slope;
5. if both realized classes are unavailable or the diagnostic fit cannot converge, report NaN rather than alter model probabilities.

No calibration coefficients are applied back to Q3.

## Reliability

Use exactly ten fixed bins:

`[0,.1), [.1,.2), ..., [.8,.9), [.9,1]`.

Reliability uses conditional non-push cover probability and excludes realized pushes. Empty bins remain explicit with `n=0` and NaN empirical summaries.

## Push calibration

For both Q3-M2 and Q3 report mean predicted `P(push)`, empirical push rate, and difference:

- overall;
- by outer season;
- for exact whole quoted-spread sizes `abs(L)={3,6,7,10,14}`.

Half-point rows remain in overall/season summaries with structural predicted push probability zero; they can never be realized pushes under the line-lattice contract.

## Fixed reporting slices

Reuse only the Phase-1 frozen slice definitions already implemented for Q1:

- quoted-spread key buckets K3/K6/K7/K10/K14;
- favorite-size buckets `<3`, `3–<7`, `7–<10`, `10–<14`, `>=14`;
- market-total buckets `<42`, `42–<45`, `45–<48`, `>=48`.

For each nonempty slice report the same Q3 proper/calibration metrics. Slices are explanatory only and cannot redefine the primary candidate.

## Selection firewall

Neither ATS hit rate, ROI, calibration appearance, a season result, reliability bin, nor fixed slice can change:

- learner family;
- features;
- C grid;
- C-pair tie-break;
- hurdle combination;
- half-point push rule;
- primary Q3-vs-Q3-M2 comparison.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.