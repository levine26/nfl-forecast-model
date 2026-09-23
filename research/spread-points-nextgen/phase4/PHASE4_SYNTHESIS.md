# Phase 4 — Scientific Synthesis

## Executive result

Phase 4 validly opened and spent the program's one-time 2025 underlying-model historical holdout for the already-frozen A0/B0/C0 identities. The evidence does **not** support a standalone historical scoring/margin/total finalist.

**Final Phase 4 scientific disposition: `NO_HISTORICAL_STANDALONE_FINALIST`.**

This is not a failed experiment. It is a confirmatory negative result under the preregistered program.

## Candidate dispositions

### A0 — `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`

**Methodological validity:** PASS. The frozen Ridge/Gaussian team-score implementation, tuning grid, 2016 floor, prior-time folds, process features and training-only covariance were preserved.

**Predictive result:** 2025 home/away MAE 7.488/7.724; margin MAE 10.495; total MAE 10.689.

**Market-relative result:** margin is materially worse than market (+0.772 MAE; 95% block interval +0.367 to +1.254). Total is nominally worse (+0.296) with uncertainty crossing zero.

**Robustness:** negative direction is consistent with 2022–2024 development. Large model-market disagreement remains especially weak; blowouts remain difficult.

**Complexity:** does not earn standalone survival against the market or compact simple baselines.

**Disposition:** `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST`.

### B0 — `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`

**Methodological validity:** PASS. Independent Poisson drive count, multinomial drive outcome model, frozen 6/7/8 conversion distribution, rare-score tail and 10,000-draw simulation were preserved.

**Predictive result:** 2025 home/away MAE 7.654/7.942; margin MAE 10.305; total MAE 11.810. Total signed error `actual - prediction = -5.493`, meaning substantial overprediction.

**Market-relative result:** materially worse than market on margin (+0.582 MAE; 95% interval +0.185 to +1.050) and total (+1.417; +0.672 to +2.154).

**Robustness:** persistent total overprediction and wider-than-needed predictive intervals are consistent with development weaknesses.

**Complexity:** the richer possession/drive simulation does not earn its cost in pooled point error or proper scores.

**Disposition:** `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST` and a preserved negative structural reference.

### C0 — `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`

**Methodological validity:** PASS. Ridge-only residual models, A0 football base, exact M0/M1/M2/M3 hierarchy and frozen market horizon were preserved.

**Predictive result:** M3 margin/total MAE 9.747/10.376 versus raw market M0 9.722/10.393.

**Market-relative result:** M3-M0 margin = +0.0246 MAE and total = -0.0179 MAE; both confidence intervals cross zero. The total nominal improvement is too small and uncertain to establish incremental information.

**Robustness:** development likewise showed no incremental football edge.

**Complexity:** M1/M2/M3 all collapse near M0. The market prior explains essentially all of the durable performance.

**Disposition:** `MARKET_AWARE_DIAGNOSTIC_ONLY_NO_INCREMENTAL_FOOTBALL_EDGE`.

### D

Margin and total remain `ENSEMBLE_NOT_ELIGIBLE`. Phase 4 did not fit D, search weights, change thresholds or create a successor ensemble.

## Why there is no finalist

The no-finalist decision does not use a newly invented numeric promotion threshold. It follows the preregistered objectives and evidence:

- both football-only candidates remain worse than the market on the central continuous targets;
- A0/B0 do not demonstrate a consistent advantage over the compact simple baseline set;
- B0 carries a persistent and larger total bias;
- C0 cannot establish incremental football information beyond M0;
- distributional/probability diagnostics do not reverse the continuous-error conclusion;
- ATS/O-U cannot select or rescue a candidate;
- 2025 is a single-season holdout with explicit uncertainty limits;
- complexity does not earn measurable standalone value.

A tiny nominal difference inside uncertainty is not treated as a finalist signal.

## Evidence boundary after Phase 4

2025 is now **OPENED / SPENT** for A0/B0/C0 underlying-model evaluation. Phase 1 had already observed broad baseline 2025 errors, so the precise description remains: **final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions.**

Candidate 5 has not been trained. Completed 2026 outcomes remain unused. Production remains `F-ST-01-FROZEN-2026` and no Sunday Signal forecasting behavior changed.

The preserved chronology-clean 2022–2024 component surface remains:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Phase 5 must treat those OOF rows as its historical component-development surface and must not casually treat 2025 as a pristine Candidate 5 holdout. That evidence-boundary problem belongs to the already-approved Phase 5 charter; Phase 4 does not solve it or train the stack.

## Phase 4 exit recommendation

Scientifically, the Phase 4 evaluation package is complete. GitHub closeout remains to validate the final branch head, merge the complete package, re-read it from merged `main`, record the final merge/CI receipt, leave Phase 5 `NOT STARTED`, and stop.