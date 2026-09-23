# Phase 5 Handoff — Candidate 5 Remains NOT STARTED

## Starting state

Phase 4 is **COMPLETE**.

Primary scientific integration:

- PR #550 — MERGED
- exact validated Phase 4 head: `c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`
- primary merge: `733f6d6a0497e996358282f38c61ea5fdd827040`
- dedicated Phase 4 validation `35820561374` — SUCCESS
- research firewall `35820561354` — SUCCESS
- full research validation `35820561327` — SUCCESS

Authoritative closeout receipt:

`research/spread-points-nextgen/FINAL_PHASE4_RECEIPT.md`

Production remains `F-ST-01-FROZEN-2026`.

Candidate 5 remains **NOT STARTED / NOT TRAINED**.

## Final underlying-model evidence

### A0

`A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`

- 2022–2024 development margin/total MAE: 9.8825 / 10.3869
- 2025 holdout margin/total MAE: 10.4946 / 10.6892
- 2025 home/away score MAE: 7.4881 / 7.7244
- 2025 market-relative margin delta: +0.7722 MAE, 95% week-block interval +0.3670 to +1.2541
- disposition: **valid underlying football-only representation; not a standalone historical scoring finalist**

### B0

`B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`

- 2022–2024 development margin/total MAE: 10.2132 / 11.3044
- 2025 holdout margin/total MAE: 10.3047 / 11.8102
- 2025 home/away score MAE: 7.6538 / 7.9417
- 2025 total signed error `actual - prediction`: -5.4931
- 2025 market-relative deltas: +0.5823 margin and +1.4168 total MAE
- disposition: **valid underlying possession/drive representation and negative structural reference; not a standalone historical scoring finalist**

### C0

`C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`

- 2022–2024 C0 M3 margin/total MAE: 9.4390 / 10.1376 versus M0 9.4184 / 10.1209
- 2025 M3 margin/total MAE: 9.7470 / 10.3755 versus M0 9.7224 / 10.3934
- 2025 M3-M0 margin delta: +0.0246 MAE; uncertainty crosses zero
- 2025 M3-M0 total delta: -0.0179 MAE; uncertainty crosses zero
- disposition: **market-aware diagnostic only; no demonstrated incremental football information beyond M0**

### D

Margin: `ENSEMBLE_NOT_ELIGIBLE`  
Total: `ENSEMBLE_NOT_ELIGIBLE`

D was not trained, reconsidered, reweighted or rescued in Phase 4.

## Program-level Phase 4 disposition

`NO_HISTORICAL_STANDALONE_FINALIST`

This does **not** authorize a post-hoc A1/B1/C1 rescue search and does not cancel the already-approved Phase 5 Candidate 5 charter. Phase 5 asks a different question: whether frozen chronology-clean underlying representations contain incremental winner information around F-ST under a separately frozen stacking/evidence contract.

## Preserved historical component surface

The exact downstream OOF component surface remains unchanged:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Those 815 rows were produced out of sample for their 2022–2024 games before the 2025 underlying holdout opened. Phase 4 did not rewrite, reselect or append to this surface.

## 2025 evidence boundary

2025 is **OPENED / SPENT** for A0/B0/C0 underlying-model evaluation.

Phase 5 must explicitly preserve these facts:

- 2025 A0/B0/C0 challenger outputs and performance have been observed.
- 2025 therefore **cannot be described as a pristine Candidate 5 holdout**.
- Phase 5 architecture, feature, component and tuning decisions may not be selected by looking for combinations that would have won on the observed 2025 component results.
- Candidate 5 must obey a separately frozen OOF/evidence-boundary charter and distinguish underlying-model holdout evidence from stack-development evidence.
- completed 2026 outcomes remain prohibited for Candidate 5 design/selection unless a later prospective charter explicitly permits grading predictions that were frozen before outcomes occurred.

Do not weaken this boundary by labeling a 2025 stack evaluation “untouched.”

## Required Phase 5 preregistration before any Candidate-5-specific output

A future Phase 5 task must first write and freeze, on GitHub:

1. the exact evidence boundary and role of 2022–2024 OOF versus observed 2025 component evidence;
2. the allowed A0/B0/C0/D component surface and any exclusions;
3. the F-ST anchor construction and exact Candidate 5 model identity;
4. chronology-clean OOF stacking construction;
5. preprocessing, hyperparameter grid, tuning objective and deterministic tie-breaks;
6. mandatory nulls/ablations, including F-ST alone and component-removal tests;
7. uncertainty/calibration/proper-score evaluation;
8. the rule for any use of 2025 in final fitting after architecture freeze;
9. the prospective Phase 6 confirmation boundary;
10. leakage, production and completed-2026 firewalls.

Only after those contracts are committed may Candidate 5 be trained.

## Exact Phase 5 starting state

- Phase 0: COMPLETE
- Phase 1: COMPLETE
- Phase 2: COMPLETE
- Phase 3: COMPLETE
- Phase 4: **COMPLETE**
- Phase 5 Candidate 5: **NOT STARTED**
- approved working Candidate 5 ID: `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`
- Candidate 5 trained: **false**
- completed 2026 outcomes used for Phase 4 selection: **false**
- production model: `F-ST-01-FROZEN-2026`, unchanged

## Stop condition

This file is a handoff only. Do not fit F-ST+A0, F-ST+B0, residual corrections, stack weights, Candidate 5 probabilities or Candidate 5 winner accuracy during Phase 4 closeout.

**Phase 4 COMPLETE. Candidate 5 NOT STARTED. STOP.**