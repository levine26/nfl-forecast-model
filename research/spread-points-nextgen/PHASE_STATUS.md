# Spread & Points Next-Generation — Phase Status

**Program:** LevLine spread setting, team-point, margin, total, and joint-score research  
**Authority:** `MASTER_PLAN.md`  
**Last updated:** 2026-09-22 America/Los_Angeles  
**Phase 4 branch:** `research/spread-points-nextgen-phase4`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged

The authoritative Phase 3 completion receipt is `FINAL_PHASE3_RECEIPT.md`. The authoritative Phase 4 completion receipt is `FINAL_PHASE4_RECEIPT.md`. Phase 4 is COMPLETE. Phase 5 Candidate 5 remains NOT STARTED.

| Phase | Name | Status | Primary branch | Supporting PR(s) | Key evidence / artifacts | Exact next action |
|---|---|---|---|---|---|---|
| 0 | Master Program Initialization | **COMPLETE** | `docs/spread-points-nextgen-phase0` — merged | #512 — MERGED | merge `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25` | Closed |
| 1 | Current LevLine Audit, Baseline Reproduction & Error Decomposition | **COMPLETE** | `research/spread-points-nextgen-phase1` — merged | #513 — MERGED | merge `a4f7172c0c4ff82b1689411181e7a9042a1628a8` | Closed |
| 2 | Deep External Research & Challenger Design | **COMPLETE** | `research/spread-points-nextgen-phase2` — merged | #520 — MERGED | merge `405906942013252c158244c9b033a3240baa37f8`; frozen holdout protocol | Closed |
| 3 | Controlled Challenger Implementation | **COMPLETE** | `research/spread-points-nextgen-phase3` — merged | #547 — MERGED; final receipt #549 — MERGED | final synchronized head `8c061cd400a6bb52a037d5e98880efd19a451fcb`; merge `d4d29d8c2340864e2d9e4bcd793852e8643be80c`; exact-head CI `35813365004`, `35813364985`, `35813364975` SUCCESS; 815-game 2022–2024 OOF package; D ineligible | Closed; do not rerun |
| 4 | Historical Validation, Ablation & Model Selection | **COMPLETE** | `research/spread-points-nextgen-phase4` — merged | #550 — MERGED | opening receipt `362af7af7db43a715b9ab9537a52d2749c37e7a6`; 272 exact common 2025 games; first complete holdout run `35818332253`; exact first-run artifact `10732945725`; preservation run `35819413238` SUCCESS; exact validated head `c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`; exact-head CI `35820561374`, `35820561354`, `35820561327` SUCCESS; primary merge `733f6d6a0497e996358282f38c61ea5fdd827040`; disposition `NO_HISTORICAL_STANDALONE_FINALIST`; `FINAL_PHASE4_RECEIPT.md` | Closed; 2025 underlying holdout spent; STOP |
| 5 | Historical F-ST-Anchored Winner Integration (Candidate 5) | **NOT STARTED** | TBD | None | future `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`; preserved Phase 3 2022–2024 OOF component surface; underlying 2025 results now observed | Begin only in a separate Phase 5 task by freezing the Candidate 5 evidence-boundary/component/model/tuning/evaluation contracts before Candidate-5-specific outputs |
| 6 | Prospective Shadow Validation & Operational Hardening | **NOT STARTED** | TBD | None | future immutable prospective evidence | Await Phase 5 |
| 7 | Final Synthesis & Promotion Package | **NOT STARTED** | TBD | None | future final promotion package | Await Phase 6 and explicit user approval |

## Frozen candidate identities and final Phase 4 execution

- A0: `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`
- B0: `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`
- C0: `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`
- D margin: `ENSEMBLE_NOT_ELIGIBLE`
- D total: `ENSEMBLE_NOT_ELIGIBLE`
- implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`
- historical market horizon: `historical_closing_late_benchmark_exact_horizon_opaque`
- first completed 2025 scientific run: `35818332253`, generator head `f0b92217488a1a000bee74a903a9437931a53230`
- 2025 eligible/common rows: 272 / 272
- B0 simulations/game: 10,000
- bootstrap resamples: 10,000; one-season Phase 4 means week is the operative block
- 2025 holdout: **OPENED / SPENT for A0/B0/C0 underlying-model evaluation**
- Candidate 5 trained: **NO**
- completed 2026 outcomes used for selection: **NO**
- production changed: **NO**

## Final Phase 4 scientific disposition

- A0: `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST`
- B0: `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST`
- C0: `MARKET_AWARE_DIAGNOSTIC_ONLY_NO_INCREMENTAL_FOOTBALL_EDGE`
- D: remains ineligible
- program-level: **`NO_HISTORICAL_STANDALONE_FINALIST`**

The 2025 result is a **final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions**. No post-hoc rescue, new threshold, feature search or new challenger family was opened.

## Phase 4 integration receipt

Exact merged scientific head:

`c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`

Exact-head checks before primary merge:

- dedicated Phase 4 holdout validation `35820561374` — **SUCCESS**
- research firewall `35820561354` — **SUCCESS**
- full research validation `35820561327` — **SUCCESS**

PR #550 merged the exact validated head at:

`733f6d6a0497e996358282f38c61ea5fdd827040`

Merged `main` was re-read and verified to contain the manifest, all 272-game evidence, fixed slices, reports, synthesis and Phase 5 handoff with the same frozen evidence boundary. `FINAL_PHASE4_RECEIPT.md` is the authoritative final closeout receipt.

## Phase transition rule

Phase 4 is closed. Do not reopen the 2025 A0/B0/C0 holdout, reinterpret reproducibility reruns as pristine holdouts, rescue A0/B0/C0/D, inspect completed-2026 outcomes for Phase 4 selection, or train Candidate 5 in Phase 4.

The exact next program action, only when the user separately starts Phase 5, is to write and freeze the Candidate 5 evidence-boundary, component-inclusion, OOF stacking, model/tuning, ablation and evaluation contracts before any Candidate-5-specific result is inspected. Until then Phase 5 remains **NOT STARTED** and production remains `F-ST-01-FROZEN-2026`.