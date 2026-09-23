# Spread & Points Next-Generation — Phase Status

**Program:** LevLine spread setting, team-point, margin, total, and joint-score research  
**Authority:** `MASTER_PLAN.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Active closeout branch:** `research/spread-points-nextgen-phase5-receipt`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged

The authoritative completion receipts are `FINAL_PHASE3_RECEIPT.md`, `FINAL_PHASE4_RECEIPT.md`, and `FINAL_PHASE5_RECEIPT.md`. Phase 5 Candidate 5 is closed `REJECTED`; no Phase 6 handoff exists for this identity.

| Phase | Name | Status | Primary branch | Supporting PR(s) | Key evidence / artifacts | Exact next action |
|---|---|---|---|---|---|---|
| 0 | Master Program Initialization | **COMPLETE** | `docs/spread-points-nextgen-phase0` — merged | #512 — MERGED | merge `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25` | Closed |
| 1 | Current LevLine Audit, Baseline Reproduction & Error Decomposition | **COMPLETE** | `research/spread-points-nextgen-phase1` — merged | #513 — MERGED | merge `a4f7172c0c4ff82b1689411181e7a9042a1628a8` | Closed |
| 2 | Deep External Research & Challenger Design | **COMPLETE** | `research/spread-points-nextgen-phase2` — merged | #520 — MERGED | merge `405906942013252c158244c9b033a3240baa37f8`; frozen holdout protocol | Closed |
| 3 | Controlled Challenger Implementation | **COMPLETE** | `research/spread-points-nextgen-phase3` — merged | #547 — MERGED; final receipt #549 — MERGED | final synchronized head `8c061cd400a6bb52a037d5e98880efd19a451fcb`; merge `d4d29d8c2340864e2d9e4bcd793852e8643be80c`; exact-head CI `35813365004`, `35813364985`, `35813364975` SUCCESS; 815-game 2022–2024 OOF package; D ineligible | Closed; do not rerun |
| 4 | Historical Validation, Ablation & Model Selection | **COMPLETE** | `research/spread-points-nextgen-phase4` — merged | #550 — MERGED; receipt #551 — MERGED | 272 exact common 2025 games; exact validated head `c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`; exact-head CI `35820561374`, `35820561354`, `35820561327` SUCCESS; merge `733f6d6a0497e996358282f38c61ea5fdd827040`; disposition `NO_HISTORICAL_STANDALONE_FINALIST` | Closed; 2025 underlying holdout spent |
| 5 | Historical F-ST-Anchored Winner Integration (Candidate 5) | **COMPLETE — REJECTED** | `research/spread-points-nextgen-phase5` — merged | #552 — MERGED | preregistration `df14e51d73aad96899d3ba4364cbb76989f0d2bf`; first successful frozen execution `35828122187`; exact validated head `a4f892d64ab163a421eed203d9b50983e5bbd04b`; CI `35875417408`, `35875417416`, `35875417452`, `35875417543` SUCCESS; merge `a68afb1e1cf9675a7ff9e0e0af1f52343546f029`; final receipt `FINAL_PHASE5_RECEIPT.md` | Closed; no Phase 6 handoff |
| 6 | Prospective Shadow Validation & Operational Hardening | **NOT JUSTIFIED FOR CANDIDATE 5 V1** | none | None | Candidate 5 V1 failed the preregistered Phase 6 eligibility rule | Do not start for `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1` |
| 7 | Final Synthesis & Promotion Package | **NOT STARTED / NO PROMOTION CANDIDATE FROM PHASE 5** | TBD | None | future only if a separately authorized candidate completes prospective evidence | No production promotion |

## Frozen Phase 5 candidate identity

- Candidate: `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`
- architecture: F-ST-logit offset + strongly L2-regularized residual logistic correction
- scientific freeze commit: `df14e51d73aad96899d3ba4364cbb76989f0d2bf`
- Phase 5 branch base: `d9302207c3dd0a82c89fadd2cd5adc52f6541bd0`
- first workflow attempt: `35827845845` — stopped in a pre-result synthetic unit test; no Candidate-5-specific metrics generated
- correction commit: `b86b7c98b40a3b68e6fb4e42f9aeb6592554065a` — test expectation only; scientific contract unchanged
- first successful historical execution: `35828122187` — dedicated contract gate, historical package and exact-run gate all SUCCESS
- evidence preservation commit: `8fce0be359d93d68bc2c4bba852ede4181a38368`
- exact validated integration head: `a4f892d64ab163a421eed203d9b50983e5bbd04b`
- integration merge: `a68afb1e1cf9675a7ff9e0e0af1f52343546f029`
- development surface: 815 exact paired 2022–2024 games
- 2025 diagnostic surface: 272 games, explicitly `POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`
- historical F-ST provenance: chronology-clean reproduction, 741/1,087 correct across 2022–2025; not original prospective locks
- completed 2026 outcomes used for design/selection/evaluation: **NO**
- production changed: **NO**

## Final Phase 5 scientific result

Primary `PRIMARY_COMPACT_FOOTBALL` versus paired F-ST on 815 games:

- F-ST: **562/815 = 68.9571%**
- Candidate 5: **562/815 = 68.9571%**
- accuracy delta: **0.0000 pp**
- changed winners: **0 / 815 (0.0000%)**
- changed-winner accuracy: **not defined; no switches occurred**
- Brier: **0.21035034** vs F-ST **0.21034462**; delta **+0.00000573**
- log loss: **0.60909083** vs F-ST **0.60907731**; delta **+0.00001352**
- calibration intercept/slope: **0.09794 / 1.12581** vs F-ST **0.09772 / 1.12626**
- season+week block-bootstrap accuracy-delta interval: **0.0000 to 0.0000**
- scientific disposition: **`REJECTED`**
- Phase 6 eligibility: **NO**

The 2025 non-pristine diagnostic also produced zero winner changes: F-ST and the primary Candidate 5 were both **179/272 = 65.8088%**, with nominally worse proper-score point estimates for Candidate 5. It did not tune, redesign or rescue the candidate.

## Exact-head closeout validation

The exact Phase 5 integration head `a4f892d64ab163a421eed203d9b50983e5bbd04b` passed:

- dedicated Phase 5 validation `35875417408` — **SUCCESS**
- research firewall `35875417416` — **SUCCESS**
- full research validation `35875417452` — **SUCCESS**
- Phase 4 frozen-evidence regression `35875417543` — **SUCCESS**

The Phase 4 regression comparator was hardened only to ignore machine-level floating-point serialization noise while requiring exact structure/nonnumeric values and numeric agreement to `1e-12`. No scientific evidence changed.

## Phase transition rule

Candidate 5 V1 is fully closed. Do not rescue it by loosening regularization, changing features/interactions, adding a nonlinear learner, recalibrating, changing the 0.5 winner threshold, mining 2025, or using completed-2026 outcomes.

No Phase 6 handoff is authorized for `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`. A materially different future hypothesis requires a new preregistered identity and evidence clock.

Production remains `F-ST-01-FROZEN-2026`. **STOP.**
