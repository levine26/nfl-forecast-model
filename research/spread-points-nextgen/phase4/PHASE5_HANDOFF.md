# Phase 5 Handoff — Candidate 5 Remains NOT STARTED

## Starting state

Phase 4 has opened and spent the one-time 2025 underlying-model historical challenger holdout. Phase 5 may begin only after Phase 4 GitHub closeout is complete and merged.

Production remains `F-ST-01-FROZEN-2026`.

## Final underlying-model evidence

### A0

`A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`

- 2022–2024 development margin/total MAE: 9.8825 / 10.3869.
- 2025 holdout margin/total MAE: 10.4946 / 10.6892.
- 2025 home/away score MAE: 7.4881 / 7.7244.
- 2025 market-relative margin delta: +0.7722 MAE, clearly unfavorable in the week-block bootstrap.
- 2025 market-relative total delta: +0.2958 MAE, nominally unfavorable with uncertainty crossing zero.
- disposition: **valid underlying football-only representation; not a standalone historical scoring finalist**.

### B0

`B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`

- 2022–2024 development margin/total MAE: 10.2132 / 11.3044.
- 2025 holdout margin/total MAE: 10.3047 / 11.8102.
- 2025 home/away score MAE: 7.6538 / 7.9417.
- 2025 total signed error `actual - prediction`: -5.4931, continuing the development-period overprediction problem.
- 2025 market-relative deltas: +0.5823 margin and +1.4168 total MAE, both materially unfavorable.
- disposition: **valid underlying possession/drive representation and negative structural reference; not a standalone historical scoring finalist**.

### C0

`C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`

- 2022–2024 C0 M3 margin/total MAE: 9.4390 / 10.1376 versus M0 9.4184 / 10.1209.
- 2025 M3 margin/total MAE: 9.7470 / 10.3755 versus M0 9.7224 / 10.3934.
- 2025 M3-M0 margin delta: +0.0246 MAE, interval crosses zero.
- 2025 M3-M0 total delta: -0.0179 MAE, interval crosses zero.
- disposition: **market-aware diagnostic only; no demonstrated incremental football information beyond M0**.

### D

Margin: `ENSEMBLE_NOT_ELIGIBLE`  
Total: `ENSEMBLE_NOT_ELIGIBLE`

D was not trained or reconsidered in Phase 4.

## Program-level Phase 4 disposition

`NO_HISTORICAL_STANDALONE_FINALIST`

This does **not** authorize a post-hoc A1/B1/C1 rescue search and does not cancel the already-approved Phase 5 Candidate 5 charter. Phase 5's question is different: whether frozen chronology-clean underlying representations contain incremental winner information around F-ST under the separate Candidate 5 governance contract.

## Preserved historical component surface

The exact downstream OOF component surface remains unchanged:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Those 815 2022–2024 rows were produced out of sample for their games before the 2025 holdout was opened. Phase 4 did not rewrite them, reselect them, or append 2025 to them.

## 2025 evidence boundary

Phase 5 must explicitly record:

- 2025 A0/B0/C0 challenger outputs and performance have now been observed.
- 2025 therefore **cannot be described as a pristine Candidate 5 holdout**.
- Phase 5 architecture/feature decisions may not be selected by looking for combinations that would have won on the now-observed 2025 component results.
- Candidate 5 must obey its separately approved nested OOF/evidence-boundary charter and preserve the distinction between underlying-model holdout evidence and stack-development evidence.
- Completed 2026 outcomes remain prohibited for Candidate 5 design/selection unless the future phase charter explicitly allows prospective grading after predictions were frozen.

Do not solve or weaken this boundary by calling a 2025 stack evaluation “untouched.”

## Exact Phase 5 starting state

- Phase 0: COMPLETE
- Phase 1: COMPLETE
- Phase 2: COMPLETE
- Phase 3: COMPLETE
- Phase 4: pending final GitHub merge/receipt at the time this handoff was written
- Phase 5 Candidate 5: **NOT STARTED**
- Candidate 5 ID from approved roadmap: `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`
- Candidate 5 trained: **false**
- completed 2026 outcomes used for Phase 4 selection: **false**
- production model: `F-ST-01-FROZEN-2026`, unchanged

## Do not execute Phase 5 here

This file is a handoff only. Do not fit F-ST+A0, F-ST+B0, residual corrections, stack weights, Candidate 5 probabilities, or Candidate 5 winner accuracy during Phase 4.