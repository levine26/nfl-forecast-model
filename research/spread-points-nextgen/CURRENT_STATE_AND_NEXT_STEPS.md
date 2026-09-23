# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-22 America/Los_Angeles  
**Program authority:** `research/spread-points-nextgen/MASTER_PLAN.md`  
**Phase 0:** **COMPLETE**  
**Phase 1:** **COMPLETE**  
**Phase 2:** **COMPLETE**  
**Phase 3:** **COMPLETE**  
**Phase 4:** **COMPLETE**  
**Phase 5 Candidate 5:** **NOT STARTED**  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

Authoritative Phase 4 closeout receipt:

`research/spread-points-nextgen/FINAL_PHASE4_RECEIPT.md`

## Phase 4 one-time holdout state

2025 is **OPENED / SPENT** for the frozen underlying A0/B0/C0 evaluation.

Correct description: **final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions**.

Pre-result receipt:

`362af7af7db43a715b9ab9537a52d2749c37e7a6`

First complete scientific holdout run:

- workflow: `35818332253`
- generator head: `f0b92217488a1a000bee74a903a9437931a53230`
- exact first-run artifact: `10732945725`
- artifact metadata digest: `sha256:7e231406237dc0f27681cc974d07ba34a6fe3bb976bea42531bedc8166557671`
- exact first-run evidence preservation workflow: `35819413238` — **SUCCESS**

The initial push failure after the scientific run was an operational non-fast-forward caused by concurrent branch advancement. The scientific package had already completed and was preserved; the dedicated preservation workflow subsequently verified provenance and every evidence SHA before committing the exact package.

## Frozen identities and contracts

- A0: `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`
- B0: `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`
- C0: `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`
- D margin/total: `ENSEMBLE_NOT_ELIGIBLE`
- implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`
- market label: `historical_closing_late_benchmark_exact_horizon_opaque`
- 2025 exact common rows: 272
- model fitting boundary: through 2024
- B0 simulations/game: 10,000
- paired bootstrap resamples: 10,000; week is the operative block in the single 2025 season
- Candidate 5 trained: **NO**
- completed 2026 outcomes used: **NO**
- production changed: **NO**

Frozen shifted pregame states may update from prior completed 2025 games because that behavior was already part of the candidate identity; no current-game or future 2025 outcome enters its own forecast and estimator fitting/tuning remained through 2024.

## Phase 4 headline results

| Model | Margin MAE | Total MAE | Market-relative interpretation |
|---|---:|---:|---|
| A0 | 10.495 | 10.689 | margin +0.772 vs market; 95% week-block interval +0.367 to +1.254; total nominally worse |
| B0 | 10.305 | 11.810 | margin +0.582 and total +1.417 vs market; both materially unfavorable |
| Market M0 | **9.722** | 10.393 | frozen market benchmark |
| C0 M3 | 9.747 | **10.376** | M3-M0 margin +0.0246 and total -0.0179; both intervals cross zero |

A0 home/away score MAE: **7.488 / 7.724**.  
B0 home/away score MAE: **7.654 / 7.942**.  
B0 2025 total signed error (`actual - prediction`): **-5.493**.

## Final scientific dispositions

- A0: `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST`
- B0: `VALID_UNDERLYING_REPRESENTATION_NOT_STANDALONE_FINALIST`
- C0: `MARKET_AWARE_DIAGNOSTIC_ONLY_NO_INCREMENTAL_FOOTBALL_EDGE`
- D: remains `ENSEMBLE_NOT_ELIGIBLE`
- Phase 4 program-level result: **`NO_HISTORICAL_STANDALONE_FINALIST`**

No new family, feature search, threshold, ensemble, A1/B1/C1, nonlinear rescue or 2025 retuning was opened. ATS/O-U diagnostics remained secondary and did not select or rescue a candidate.

## Final integration receipt

Primary Phase 4 PR:

- PR #550 — **MERGED**
- exact validated head: `c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`
- dedicated Phase 4 validation: `35820561374` — **SUCCESS**, including complete regeneration and byte comparison to the committed frozen holdout package
- research firewall: `35820561354` — **SUCCESS**
- full research validation: `35820561327` — **SUCCESS**
- primary merge: `733f6d6a0497e996358282f38c61ea5fdd827040`

Merged `main` was re-read after PR #550 and confirmed to contain the exact holdout manifest/evidence, fixed slices, validation/ablation/uncertainty/robustness/red-team/synthesis reports and Phase 5 handoff with unchanged frozen identities and evidence boundaries.

## Phase 5 starting state

Candidate 5 remains **NOT STARTED / NOT TRAINED**.

Approved working identity:

`LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`

Preserved chronology-clean historical component surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Because the 2025 A0/B0/C0 component outputs and performance are now observed, Phase 5 may **not** call 2025 a pristine Candidate 5 holdout. A future Phase 5 task must first freeze the Candidate 5 evidence-boundary, component-inclusion, OOF stacking, model/tuning, ablation and evaluation contracts before inspecting any Candidate-5-specific output.

## Exact next action

**STOP.**

Do not start Phase 5 in Phase 4 closeout. Do not rerun Phase 3, change A0/B0/C0, resurrect D, tune on 2025, use completed 2026 outcomes for historical selection, modify F-ST, modify Sunday Signal forecasting behavior, or promote any model.

When the user separately starts Phase 5, begin from `FINAL_PHASE4_RECEIPT.md` and `phase4/PHASE5_HANDOFF.md` and freeze the Phase 5 contract before training `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`.