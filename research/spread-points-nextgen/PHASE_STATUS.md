# Spread & Points Next-Generation — Phase Status

**Program:** LevLine spread setting, team-point, margin, total, and joint-score research  
**Authority:** `MASTER_PLAN.md`  
**Last updated:** 2026-09-22 America/Los_Angeles  
**Current Phase 4 branch:** `research/spread-points-nextgen-phase4`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged

The authoritative Phase 3 completion receipt is `FINAL_PHASE3_RECEIPT.md`. It supersedes older pre-merge wording that said Phase 3 merge/PR/CI were pending.

| Phase | Name | Status | Primary branch | Supporting PR(s) | Key evidence / artifacts | Exact next action |
|---|---|---|---|---|---|---|
| 0 | Master Program Initialization | **COMPLETE** | `docs/spread-points-nextgen-phase0` — merged | #512 — MERGED | merge `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25` | Closed |
| 1 | Current LevLine Audit, Baseline Reproduction & Error Decomposition | **COMPLETE** | `research/spread-points-nextgen-phase1` — merged | #513 — MERGED | merge `a4f7172c0c4ff82b1689411181e7a9042a1628a8` | Closed |
| 2 | Deep External Research & Challenger Design | **COMPLETE** | `research/spread-points-nextgen-phase2` — merged | #520 — MERGED | merge `405906942013252c158244c9b033a3240baa37f8`; frozen holdout protocol | Closed |
| 3 | Controlled Challenger Implementation | **COMPLETE** | `research/spread-points-nextgen-phase3` — merged | #547 — MERGED; final receipt #549 — MERGED | final synchronized head `8c061cd400a6bb52a037d5e98880efd19a451fcb`; merge `d4d29d8c2340864e2d9e4bcd793852e8643be80c`; exact-head CI `35813365004`, `35813364985`, `35813364975` SUCCESS; 815-game 2022–2024 OOF package; D ineligible | Closed; do not rerun |
| 4 | Historical Validation, Ablation & Model Selection | **IN PROGRESS** | `research/spread-points-nextgen-phase4` | None yet | one-time 2025 underlying A0/B0/C0 challenger holdout; opening receipt must precede scoring | Establish opening receipt and pre-holdout gate, then open 2025 once |
| 5 | Historical F-ST-Anchored Winner Integration (Candidate 5) | **NOT STARTED** | TBD | None | future `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`; preserve Phase 3 2022–2024 OOF component surface | Await Phase 4 completion |
| 6 | Prospective Shadow Validation & Operational Hardening | **NOT STARTED** | TBD | None | future immutable prospective evidence | Await Phase 5 |
| 7 | Final Synthesis & Promotion Package | **NOT STARTED** | TBD | None | future final promotion package | Await Phase 6 and explicit user approval |

## Frozen Phase 3 state carried into Phase 4

- A0: `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`
- B0: `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`
- C0: `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`
- D margin: `ENSEMBLE_NOT_ELIGIBLE`
- D total: `ENSEMBLE_NOT_ELIGIBLE`
- implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`
- validated Phase 3 development source head: `3d893ec8e26824f7e6c1883f4d0d09c19160c712`
- historical market horizon: `historical_closing_late_benchmark_exact_horizon_opaque`
- Phase 3 development universe: 815 regular-season games, 2022–2024
- 2025 A0/B0/C0 challenger output before Phase 4: **UNOPENED**
- Candidate 5: **NOT STARTED**
- completed 2026 outcomes for selection: **PROHIBITED / NOT USED**

## Phase transition rule

Only one program phase is normally active. Phase 4 is confirmatory: no new candidate family, no D resurrection, no 2025 rescue tuning, no Candidate 5 training, no production change. Phase 4 becomes COMPLETE only after the frozen 2025 package, uncertainty, diagnostics, red-team audit, exact-head CI, merge, and merged-main verification are complete.
