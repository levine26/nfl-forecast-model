# Spread & Points Next-Generation — Current State & Next Steps

**Last updated:** 2026-09-22 America/Los_Angeles  
**Program authority:** `research/spread-points-nextgen/MASTER_PLAN.md`  
**Phase 0:** **COMPLETE**  
**Phase 1:** **COMPLETE**  
**Phase 2:** **COMPLETE**  
**Phase 3:** **COMPLETE**  
**Phase 4:** **IN PROGRESS — scientific package complete; GitHub closeout pending**  
**Phase 5 Candidate 5:** **NOT STARTED**  
**Active branch:** `research/spread-points-nextgen-phase4`  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

## Phase 4 one-time holdout state

2025 is now **OPENED / SPENT** for the frozen underlying A0/B0/C0 evaluation.

Correct description: **final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions**.

The pre-result receipt was committed before scoring at:

`362af7af7db43a715b9ab9537a52d2749c37e7a6`

Two initial workflow attempts failed before holdout execution due to a pytest package-import defect. No 2025 challenger output was produced by those attempts. The first completed scientific run was:

- workflow: `35818332253`
- generator head: `f0b92217488a1a000bee74a903a9437931a53230`
- pre-holdout gate: **SUCCESS**
- complete frozen A0/B0/C0 computation: **SUCCESS**
- evidence/firewall verification: **SUCCESS**
- protected production-surface diff: **SUCCESS**
- exact first-run artifact: `10732945725`
- artifact metadata digest: `sha256:7e231406237dc0f27681cc974d07ba34a6fe3bb976bea42531bedc8166557671`
- exact first-run evidence preservation workflow: `35819413238` — **SUCCESS**

The workflow's original bot-push step failed only because the branch advanced concurrently; the scientific package had already completed and was preserved. The dedicated preservation workflow re-downloaded the exact first-run artifact, verified its provenance and every evidence SHA, and committed the same bytes.

## Exact frozen identities

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

Frozen shifted pregame states may update from prior completed 2025 games because that was already part of the candidate identity; no current-game or future 2025 outcome enters its own prediction, and estimators/tuning remain fit through 2024.

## Phase 4 headline results

| Model | Margin MAE | Total MAE | Market-relative interpretation |
|---|---:|---:|---|
| A0 | 10.495 | 10.689 | margin +0.772 vs market, 95% week-block interval +0.367 to +1.254; total +0.296 with interval crossing zero |
| B0 | 10.305 | 11.810 | margin +0.582, interval +0.185 to +1.050; total +1.417, interval +0.672 to +2.154 |
| Market M0 | **9.722** | 10.393 | frozen null benchmark |
| C0 M3 | 9.747 | **10.376** | M3-M0 margin +0.0246 and total -0.0179; both intervals cross zero |

A0 home/away score MAE: 7.488 / 7.724.  
B0 home/away score MAE: 7.654 / 7.942.  
B0 2025 total signed error (`actual - prediction`): **-5.493**, confirming persistent total overprediction.

C0's tiny nominal total improvement does not establish incremental football information. Development and holdout both leave C0 essentially at the market null.

## Final scientific dispositions

- A0: **valid underlying football-only representation; not a standalone historical scoring finalist**.
- B0: **valid underlying possession/drive representation and negative structural reference; not a standalone historical scoring finalist**.
- C0: **market-aware diagnostic only; no demonstrated incremental football information beyond M0**.
- D: remains `ENSEMBLE_NOT_ELIGIBLE` for margin and total.
- Phase 4 program-level result: **`NO_HISTORICAL_STANDALONE_FINALIST`**.

ATS/O-U diagnostics remain secondary and did not select or rescue any candidate. No new candidate family, feature search, threshold, ensemble, A1/B1/C1 or 2025 retuning was opened.

## Required durable Phase 4 package

Present on the branch:

- `phase4/HOLDOUT_OPENING_RECEIPT.json`
- `phase4/HOLDOUT_RUN_MANIFEST.json`
- `phase4/A0_HOLDOUT_2025.csv`
- `phase4/B0_HOLDOUT_2025.csv`
- `phase4/C0_HOLDOUT_2025.csv`
- `phase4/BASELINES_HOLDOUT_2025.csv`
- `phase4/DIAGNOSTIC_SLICES_2025.csv`
- `phase4/HOLDOUT_SUMMARY.json`
- `phase4/HOLDOUT_FAILURE_LOG.md`
- `phase4/HISTORICAL_VALIDATION_REPORT.md`
- `phase4/ABLATION_REPORT.md`
- `phase4/STATISTICAL_UNCERTAINTY_REPORT.md`
- `phase4/ROBUSTNESS_REPORT.md`
- `phase4/RED_TEAM_AUDIT.md`
- `phase4/PHASE4_SYNTHESIS.md`
- `phase4/PHASE5_HANDOFF.md`

## Candidate 5 boundary

Candidate 5 remains **NOT STARTED / NOT TRAINED**.

The preserved 2022–2024 OOF component surface remains unchanged at:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Because A0/B0/C0 2025 outputs are now observed, Phase 5 may not call 2025 a pristine Candidate 5 holdout. Phase 5 must obey its separate approved OOF/evidence-boundary charter. Completed 2026 outcomes remain unused for Phase 4 selection.

## Exact next actions

1. Update the remaining canonical `DECISION_LOG.md` and `RESEARCH_INDEX.md` with the Phase 4 result and artifact paths.
2. Re-resolve live `main`; inspect the complete branch diff and preserve unrelated concurrent work.
3. Open the single Phase 4 PR from `research/spread-points-nextgen-phase4`.
4. Require exact-head dedicated Phase 4 holdout validation, LevLine research firewall and full research validation. The dedicated PR run must byte-compare regenerated evidence with the committed first-run package.
5. Fix only genuine engineering/integration defects; do not alter scientific architecture or results.
6. Merge only the exact validated head.
7. Re-read the Phase 4 evidence and reports from merged `main`.
8. Record final Phase 4 PR/merge/CI receipt on the same Phase 4 branch via documentation-only closeout, merge it, mark Phase 4 COMPLETE, leave Phase 5 NOT STARTED, confirm 2025 spent and production unchanged, then STOP.

## Do not repeat / do not expand

Do not rerun Phase 3, change A0/B0/C0, resurrect D, add A1/B alternatives/nonlinear C/boosting, tune on 2025, use 2026 to validate 2025, train Candidate 5, modify F-ST, modify Sunday Signal, or promote any model.