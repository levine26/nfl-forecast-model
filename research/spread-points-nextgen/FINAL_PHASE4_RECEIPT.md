# Spread & Points Next-Generation — Final Phase 4 Receipt

**Phase:** 4 — Historical Validation, Ablation & Model Selection  
**Status:** **COMPLETE**  
**Primary branch:** `research/spread-points-nextgen-phase4`  
**Primary integration PR:** #550 — **MERGED**  
**Exact validated PR head:** `c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`  
**Primary merge SHA:** `733f6d6a0497e996358282f38c61ea5fdd827040`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged  
**Phase 5 Candidate 5:** **NOT STARTED / NOT TRAINED**

This receipt supersedes any Phase 4 pre-merge wording in canonical control files that says the PR, merge, or final merged-main verification is still pending.

## Frozen scientific boundary

The pre-result opening receipt was committed before any 2025 A0/B0/C0 scoring at:

`362af7af7db43a715b9ab9537a52d2749c37e7a6`

The candidate identities remained frozen:

- A0 — `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`
- B0 — `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`
- C0 — `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`
- D margin — `ENSEMBLE_NOT_ELIGIBLE`
- D total — `ENSEMBLE_NOT_ELIGIBLE`

Frozen Phase 3 hashes remained:

- implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`

Historical market horizon remains exactly:

`historical_closing_late_benchmark_exact_horizon_opaque`

It is not T-120.

## One-time 2025 holdout execution

Correct evidence description:

**final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions.**

The first complete scientific holdout run was Actions run `35818332253` on generator head `f0b92217488a1a000bee74a903a9437931a53230`. The complete first-result artifact was preserved as artifact `10732945725`, metadata SHA-256 `7e231406237dc0f27681cc974d07ba34a6fe3bb976bea42531bedc8166557671`. Preservation workflow `35819413238` passed provenance and evidence-hash verification before the durable package was committed.

The holdout is now **OPENED / SPENT** for the underlying A0/B0/C0 identities.

Final evaluation facts:

- 2025 eligible/common games: **272**
- B0 simulations/game: **10,000**
- paired bootstrap resamples: **10,000**
- model estimators/tuning fit through 2024; frozen shifted pregame states may use only prior completed 2025 games under the already-frozen sequential state contract
- completed 2026 outcomes used: **false**
- Candidate 5 trained: **false**
- production changed: **false**

Two earlier workflow attempts failed before 2025 execution because of a test-import defect; no challenger output was produced by those attempts. No post-result scientific rescue was performed.

## Final 2025 scientific results

### A0

- home points MAE: **7.4881**
- away points MAE: **7.7244**
- margin MAE: **10.4946**
- total MAE: **10.6892**
- market margin MAE on exact paired rows: **9.7224**
- A0-minus-market margin MAE: **+0.7722**, 95% week-block interval **[+0.3670, +1.2541]**
- disposition: `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST`

### B0

- home points MAE: **7.6538**
- away points MAE: **7.9417**
- margin MAE: **10.3047**
- total MAE: **11.8102**
- B0-minus-market margin MAE: **+0.5823**, 95% interval **[+0.1848, +1.0495]**
- B0-minus-market total MAE: **+1.4168**, 95% interval **[+0.6723, +2.1543]**
- disposition: `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST`

### C0 mandatory null hierarchy

On the same 272 paired games:

- M0 market margin/total MAE: **9.7224 / 10.3934**
- M1 margin/total MAE: **9.7235 / 10.3812**
- M2 margin/total MAE: **9.7468 / 10.3754**
- M3 margin/total MAE: **9.7470 / 10.3755**
- M3-minus-M0 margin MAE: **+0.0246**, uncertainty crosses zero
- M3-minus-M0 total MAE: **-0.0179**, uncertainty crosses zero
- disposition: `MARKET_AWARE_DIAGNOSTIC_ONLY_NO_INCREMENTAL_FOOTBALL_EDGE`

The nominal total improvement is too small and uncertain to establish incremental football information and is directionally inconsistent with the development-period M3-vs-M0 result. No M4 or rescue model was created.

### D

D remained `ENSEMBLE_NOT_ELIGIBLE` for both margin and total. It was not fit on 2025, reweighted, threshold-adjusted, or replaced.

## Final model-selection disposition

**`NO_HISTORICAL_STANDALONE_FINALIST`**

A0 and B0 remain methodologically valid underlying representations and negative references, but their complexity did not earn standalone scoring/margin/total finalist status. C0 remains a market-aware diagnostic only. ATS/O-U diagnostics did not select or rescue a candidate.

## Exact-head pre-merge validation

The exact merged Phase 4 head was:

`c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`

All required exact-head checks passed:

- Spread & Points Phase 4 holdout validation: **35820561374 — SUCCESS**
  - frozen pre-holdout contracts/tests: PASS
  - complete frozen 2025 regeneration: PASS
  - required evidence/firewall verification: PASS
  - regenerated evidence byte-comparison against committed frozen package: PASS
  - protected production-surface check: PASS
  - exact-run gate: PASS
- LevLine research firewall: **35820561354 — SUCCESS**
- LevLine research validation: **35820561327 — SUCCESS**

No stale CI was used for merge.

## Primary merge and merged-main verification

PR #550 merged the exact validated head into `main` at:

`733f6d6a0497e996358282f38c61ea5fdd827040`

Merged `main` was re-read and verified to contain:

- `phase4/HOLDOUT_OPENING_RECEIPT.json`
- `phase4/HOLDOUT_RUN_MANIFEST.json`
- exact 272-game A0/B0/C0 evidence
- baselines and fixed diagnostic slices
- holdout summary and failure/boundary log
- historical validation, ablation, uncertainty, robustness, red-team and synthesis reports
- `phase4/PHASE5_HANDOFF.md`

The merged run manifest confirms frozen hashes/IDs, D ineligibility, 10,000 B0 simulations/game, 10,000 bootstrap resamples, `candidate5_trained=false`, `completed_2026_outcomes_used=false`, `production_changed=false`, and the exact historical market-horizon label.

## Phase 5 starting state

Phase 5 Candidate 5 remains:

**NOT STARTED**

Approved working ID:

`LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`

Preserved chronology-clean component surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

It remains the 815-row 2022–2024 OOF component-development surface and was not altered by Phase 4.

Because the 2025 A0/B0/C0 component outputs and performance have now been observed, Phase 5 may **not** describe 2025 as a pristine Candidate 5 holdout. Phase 5 must begin by writing and freezing its explicit evidence-boundary, component-inclusion, model/tuning and evaluation contracts before any Candidate-5-specific output is inspected. Completed 2026 outcomes remain unavailable for design/selection under the approved Phase 5 charter.

## Production firewall and stop condition

Production remains `F-ST-01-FROZEN-2026`.

Phase 4 did not modify F-ST coefficients/artifacts, production winner selection, Sunday Signal forecast behavior, public fair-spread semantics, official history, forecast locks, or grading.

**Phase 4 is COMPLETE. Phase 5 Candidate 5 remains NOT STARTED. STOP.**
