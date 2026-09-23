# Spread & Points Next-Generation — Final Phase 5 Receipt

**Phase:** 5 — Historical F-ST-Anchored Winner Integration (Candidate 5)  
**Status:** **COMPLETE — CANDIDATE 5 REJECTED**  
**Primary branch:** `research/spread-points-nextgen-phase5`  
**Primary integration PR:** #552 — **MERGED**  
**Exact validated PR head:** `a4f892d64ab163a421eed203d9b50983e5bbd04b`  
**Primary merge SHA:** `a68afb1e1cf9675a7ff9e0e0af1f52343546f029`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged  
**Phase 6 eligibility for Candidate 5 V1:** **NO**

This receipt supersedes any Phase 5 pre-merge wording in canonical control files that says the PR, merge, merged-main verification, or final receipt is still pending.

## Frozen scientific identity

Candidate:

`LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`

Scientific preregistration/freeze commit:

`df14e51d73aad96899d3ba4364cbb76989f0d2bf`

Frozen Phase 5 implementation/config identities from the merged run manifest:

- Candidate 5 code SHA-256: `55f62f9de44e853f820016c893c6d94a9a2226f7c08e412260a7cf5d10c9b4c2`
- Candidate 5 config SHA-256: `5762ac921519e594412d0dbcc6ced49d8fb332672e83bb0c5e54cd53d04299ce`
- frozen Phase 3 implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- frozen Phase 3 config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`
- Phase 3 OOF evidence surface: `research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`
- F-ST historical training-frame blob: `7085459ae2061cce18fda8095725be9f1e74a7f0`
- F-ST stacking-code blob: `d8988217d1149d08a1c472d0c1257f3cbbf4c9f3`
- production F-ST identity: `F-ST-01-FROZEN-2026`

The Phase 5 freeze predates Candidate-5-specific performance output and fixes the evidence boundary, component policy, F-ST provenance, feature sets, chronology-clean meta-stacking, L2 offset-logistic learner, lambda grid/tuning rule, winner threshold, ablations, metrics, uncertainty procedure, 2025 diagnostic policy, and scientific classification rule.

## Evidence boundary and chronology

Primary development/evaluation surface:

- seasons: **2022–2024**
- exact paired games: **815**
- component surface: chronology-clean frozen OOF A0/B0/C0 inputs from Phase 3
- D status: `ENSEMBLE_NOT_ELIGIBLE`

Historical F-ST comparator:

- chronology-clean historical reproduction, not original prospective forecast locks
- 2022–2025 reproduced games: **1,087**
- reproduced correct: **741**

2025 policy:

`POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC_ONLY_AFTER_FULL_FREEZE_NO_RESCUE`

The 2025 diagnostic contains **272** games and was not used for architecture, feature, lambda, threshold, learner, calibration, rescue, or survival decisions.

Completed 2026 outcomes used for Candidate 5 design, selection, fitting, historical evaluation, rescue, or survival: **NO**.

## Execution provenance

First workflow attempt:

- Actions run `35827845845`
- stopped in a pre-result synthetic unit-test gate
- Candidate-5-specific metrics generated: **NO**

Engineering-only correction:

- commit `b86b7c98b40a3b68e6fb4e42f9aeb6592554065a`
- changed only an incorrect expected discordant-count split in a synthetic test fixture
- scientific contract changed: **NO**

First successful frozen historical execution:

- Actions run `35828122187`
- frozen-contract gate: **SUCCESS**
- historical package: **SUCCESS**
- exact-run gate: **SUCCESS**
- evidence preservation commit: `8fce0be359d93d68bc2c4bba852ede4181a38368`

## Final scientific result

Primary `PRIMARY_COMPACT_FOOTBALL` arm versus paired F-ST on 815 games:

| Metric | F-ST | Candidate 5 | Delta |
|---|---:|---:|---:|
| Correct | 562 | 562 | 0 |
| Accuracy | 68.9571% | 68.9571% | **0.0000 pp** |
| Brier | 0.21034462 | 0.21035034 | **+0.00000573** |
| Log loss | 0.60907731 | 0.60909083 | **+0.00001352** |
| Calibration intercept | 0.09772 | 0.09794 | +0.00022 |
| Calibration slope | 1.12626 | 1.12581 | -0.00044 |

Winner-change mechanism:

- changed winners: **0 / 815**
- changed-winner rate: **0.0000%**
- Candidate-5-only correct: **0**
- F-ST-only correct: **0**
- changed-winner accuracy: **undefined because no winner changed**
- 10,000-resample season+week block-bootstrap accuracy-delta interval: **0.0000 to 0.0000**

Every preregistered residual ablation also produced zero winner changes. Candidate 5 therefore did not create selective incremental winner information beyond the F-ST anchor.

## Fixed 2025 non-pristine diagnostic

On 272 games:

- F-ST: **179/272 = 65.8088%**
- Candidate 5: **179/272 = 65.8088%**
- winner changes: **0**
- Candidate 5 proper-score point estimates: nominally worse

The diagnostic did not tune or rescue the candidate.

## Final scientific disposition

**`REJECTED`**

The preregistered Phase 6 eligibility rule required a positive paired accuracy delta, selective winner changes with changed-winner accuracy above 0.50, and no point-estimate degradation in Brier or log loss. Candidate 5 produced zero winner changes, zero accuracy gain, and slightly worse proper-score point estimates.

This is a preserved negative result. No post-hoc feature search, regularization loosening, nonlinear replacement, recalibration, threshold fishing, 2025 mining, or completed-2026 rescue was performed.

## Exact-head pre-merge validation

The exact merged Phase 5 head was:

`a4f892d64ab163a421eed203d9b50983e5bbd04b`

All required exact-head checks passed:

- Spread & Points Phase 5 Candidate 5 validation: **35875417408 — SUCCESS**
- LevLine research firewall: **35875417416 — SUCCESS**
- LevLine research validation: **35875417452 — SUCCESS**
- Spread & Points Phase 4 holdout reproducibility regression: **35875417543 — SUCCESS**

The additional Phase 4 regression was required because Phase 5 closeout touched shared research-control paths. An earlier regression run (`35873546260`) failed only at byte-for-byte regenerated-evidence comparison due machine-level floating-point serialization differences after all scientific evidence checks passed. Commit `a4f892d64ab163a421eed203d9b50983e5bbd04b` replaced that brittle byte comparator with exact structural/string comparison plus `1e-12` numeric tolerance. The rerun passed. No Phase 4 model, data, result, or scientific conclusion changed.

No stale CI was used for merge.

## Primary merge and merged-main verification

PR #552 merged the exact validated head into `main` at:

`a68afb1e1cf9675a7ff9e0e0af1f52343546f029`

The merge has parents:

- contemporaneous `main`: `4d2358d47bc82fa333172b17a803dd222f9b5047`
- exact Phase 5 validated head: `a4f892d64ab163a421eed203d9b50983e5bbd04b`

Merged `main` was re-read and verified to contain the complete Phase 5 package, including:

- preregistration/charter/evidence-boundary/model/evaluation contracts
- `CANDIDATE5_FREEZE_RECEIPT.json`
- reproducible Candidate 5 implementation and tests
- 815-game development predictions
- 272-game fixed 2025 diagnostic
- ablation, calibration, reliability, slice and bootstrap evidence
- model fits, run manifest and results JSON
- historical-results, uncertainty, calibration, red-team and synthesis reports
- failure log preserving the pre-result failed attempt

The merged run manifest confirms:

- `scientific_disposition = REJECTED`
- `phase6_eligible = false`
- `completed_2026_outcomes_used = false`
- `production_changed = false`
- `posthoc_calibration_applied = false`
- `winner_threshold_tuned = false`
- `nonlinear_learner_used = false`
- market horizon remains `historical_closing_late_benchmark_exact_horizon_opaque`

## Production firewall and program stop condition

Production remains `F-ST-01-FROZEN-2026`.

Phase 5 did not modify production F-ST coefficients/artifacts, production winner selection, Sunday Signal forecasting behavior, public fair-spread semantics, official history, forecast locks, or grading.

Candidate 5 V1 is **not eligible for Phase 6**. No Phase 6 handoff exists for this identity.

A future materially different hypothesis requires a separately authorized and separately preregistered candidate identity with a new evidence clock. The spent 2022–2025 evidence may not be relabeled as untouched confirmation.

**Phase 5 is COMPLETE. Candidate 5 V1 is REJECTED. Production is unchanged. Do not start Phase 6 for this identity. STOP.**
