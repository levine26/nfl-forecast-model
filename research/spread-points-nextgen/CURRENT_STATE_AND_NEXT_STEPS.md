# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-23 America/Los_Angeles  
**Program authority:** `research/spread-points-nextgen/MASTER_PLAN.md`  
**Phase 0:** **COMPLETE**  
**Phase 1:** **COMPLETE**  
**Phase 2:** **COMPLETE**  
**Phase 3:** **COMPLETE**  
**Phase 4:** **COMPLETE**  
**Phase 5 Candidate 5:** **COMPLETE — `REJECTED`**  
**Phase 6 for Candidate 5 V1:** **NOT JUSTIFIED / DO NOT START**  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

Authoritative closeout receipts:

- `research/spread-points-nextgen/FINAL_PHASE3_RECEIPT.md`
- `research/spread-points-nextgen/FINAL_PHASE4_RECEIPT.md`
- `research/spread-points-nextgen/FINAL_PHASE5_RECEIPT.md`

## Phase 5 frozen identity and evidence boundary

Candidate:

`LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`

Scientific freeze commit:

`df14e51d73aad96899d3ba4364cbb76989f0d2bf`

Merged Candidate 5 identities:

- code SHA-256: `55f62f9de44e853f820016c893c6d94a9a2226f7c08e412260a7cf5d10c9b4c2`
- config SHA-256: `5762ac921519e594412d0dbcc6ced49d8fb332672e83bb0c5e54cd53d04299ce`
- exact validated head: `a4f892d64ab163a421eed203d9b50983e5bbd04b`
- merge SHA: `a68afb1e1cf9675a7ff9e0e0af1f52343546f029`
- PR: #552 — MERGED

The freeze predates every Candidate-5-specific performance result and fixes the evidence boundary, component policy, features, F-ST provenance, OOF meta-chronology, L2 residual-logistic learner, lambda grid, proper-score tuning, threshold, ablations, uncertainty procedure, 2025 policy, and final classification rule.

Primary historical surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

- exact rows: **815**
- seasons: **2022–2024**
- all A0/B0/C0 component inputs retain their frozen OOF provenance
- D remains `ENSEMBLE_NOT_ELIGIBLE`

Historical F-ST baseline is the accepted chronology-clean annual reproduction from `challenger_outputs/fst/provenance/training_frame_keyed.csv` via `build_chronological_logit_stack`. It reproduces **741/1,087** correct across 2022–2025 and is explicitly a historical reproduction rather than an assertion of original prospective forecast locks.

2025 is not pristine for Candidate 5. The only Candidate-5-specific 2025 use is the frozen, post-conception diagnostic labeled:

`POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`

Completed-2026 outcomes did not participate in Candidate 5 design, fitting, tuning, historical evaluation, rescue, or survival.

## Phase 5 execution provenance

First Phase 5 workflow attempt:

- workflow `35827845845`
- stopped in the pre-result unit-test gate
- cause: incorrect expected discordant-count split in a synthetic test fixture
- Candidate-5-specific historical metrics generated: **NO**

Engineering-only correction:

`b86b7c98b40a3b68e6fb4e42f9aeb6592554065a`

The correction changed only the synthetic test expectation. It did not alter any scientific term.

First successful frozen historical execution:

- workflow `35828122187`
- contract gate: **SUCCESS**
- frozen historical package: **SUCCESS**
- exact-run gate: **SUCCESS**
- evidence preservation commit: `8fce0be359d93d68bc2c4bba852ede4181a38368`

## Primary scientific result

Exact paired 2022–2024 primary football arm:

| Metric | F-ST | Candidate 5 primary | Delta |
|---|---:|---:|---:|
| Games | 815 | 815 | — |
| Correct | 562 | 562 | 0 |
| Accuracy | 68.9571% | 68.9571% | **0.0000 pp** |
| Brier | 0.21034462 | 0.21035034 | **+0.00000573** |
| Log loss | 0.60907731 | 0.60909083 | **+0.00001352** |
| Calibration intercept | 0.09772 | 0.09794 | +0.00022 |
| Calibration slope | 1.12626 | 1.12581 | -0.00044 |

Winner-change mechanism:

- changed winners: **0 / 815 = 0.0000%**
- Candidate-5-only correct: **0**
- F-ST-only correct: **0**
- changed-winner accuracy: **not defined because no winner changed**
- mechanism identity: exactly zero accuracy delta from zero switch rate
- 10,000-resample season+week block-bootstrap accuracy-delta interval: **0.0000 to 0.0000**

Every preregistered residual ablation also made zero winner changes. Raw A0 and raw B0 were materially lower in straight-up accuracy than F-ST. The separately labeled market-aware diagnostic also made zero switches and did not rescue the football-only conclusion.

## 2025 fixed-model diagnostic

On 272 games:

- F-ST: **179/272 = 65.8088%**
- primary Candidate 5: **179/272 = 65.8088%**
- winner changes: **0**
- primary Brier delta: approximately **+0.000003**
- primary log-loss delta: approximately **+0.000006**

This evidence is non-pristine, post-conception, and non-selective. It caused no architecture, feature, lambda, calibration, threshold, learner, or classification change.

## Final scientific disposition

**`REJECTED`**

The preregistered Phase 6 eligibility rule required a positive paired accuracy delta, selective winner changes with changed-winner accuracy above 0.50, and no point-estimate degradation in Brier or log loss. Candidate 5 produced zero winner changes, zero accuracy gain, and microscopically worse proper-score point estimates.

This is an accepted negative result. There is no model rescue.

## Exact-head merge validation and closeout

Exact validated Phase 5 PR head:

`a4f892d64ab163a421eed203d9b50983e5bbd04b`

Exact-head checks:

- Spread & Points Phase 5 Candidate 5 validation `35875417408` — **SUCCESS**
- LevLine research firewall `35875417416` — **SUCCESS**
- LevLine research validation `35875417452` — **SUCCESS**
- Spread & Points Phase 4 reproducibility regression `35875417543` — **SUCCESS**

PR #552 merged that exact head into `main` at:

`a68afb1e1cf9675a7ff9e0e0af1f52343546f029`

Merged `main` was re-read and verified to contain the complete Phase 5 preregistration, implementation, evidence, diagnostics, uncertainty, red-team, synthesis, failure-log, and run-manifest package.

## Production and Phase 6 state

Production `F-ST-01-FROZEN-2026` is unchanged. Sunday Signal forecasting behavior is unchanged. No official forecast output was replaced by Candidate 5.

Phase 6 prospective shadow validation is **not justified for `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`**, so no Phase 6 handoff exists.

A future materially different research hypothesis would require a separately authorized and separately preregistered new candidate identity and a new evidence clock. It may not reinterpret the spent 2022–2025 evidence as untouched confirmation.

## Exact next action

**STOP this candidate program.**

Do not start Phase 6 for Candidate 5 V1. Do not rescue the rejected historical identity. Do not modify production. Any future challenger requires a new authorization, new preregistration, and new candidate identity.
