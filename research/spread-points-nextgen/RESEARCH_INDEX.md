# Spread & Points Next-Generation — Research Index

**Authority:** `MASTER_PLAN.md`  
**Purpose:** Canonical map of the Spread & Points research program.  
**Last reconciled:** 2026-09-22 America/Los_Angeles

This index is a map, not an authorization mechanism. Candidate identity and evidence boundaries are controlled by the frozen contracts and phase receipts.

## Program controls

- `research/spread-points-nextgen/MASTER_PLAN.md`
- `research/spread-points-nextgen/PHASE_STATUS.md`
- `research/spread-points-nextgen/CURRENT_STATE_AND_NEXT_STEPS.md`
- `research/spread-points-nextgen/DECISION_LOG.md`
- `research/spread-points-nextgen/RESEARCH_INDEX.md`
- `research/spread-points-nextgen/FINAL_PHASE3_RECEIPT.md`
- `research/spread-points-nextgen/FINAL_PHASE4_RECEIPT.md`

## Production firewall

Production remains `F-ST-01-FROZEN-2026`. Key protected surfaces include:

- `src/nfl_forecast/fst_production.py`
- `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json`
- `research/fst/F-ST-01-FROZEN-2026.json`
- `src/nfl_forecast/pipeline.py`
- `src/nfl_forecast/public_forecast.py`
- `outputs/`
- `site/`
- weekly publication/lock scripts

Research may not alter production F-ST coefficients, winner selection, public fair-spread semantics, official history, forecast locks, grading, or Sunday Signal forecasting behavior without later explicit authorization.

## Phase 1 — COMPLETE

Canonical evidence is under `research/spread-points-nextgen/phase1/`, including:

- `CURRENT_ARCHITECTURE_AUDIT.md`
- `BASELINE_REPRODUCTION_REPORT.md`
- `ERROR_DECOMPOSITION_REPORT.md`
- `DATA_API_INVENTORY.md`
- `LEAKAGE_PIT_AUDIT.md`
- `PHASE1_SYNTHESIS.md`
- `PHASE1_SUMMARY.json`

PR #513 merged at `a4f7172c0c4ff82b1689411181e7a9042a1628a8`.

## Phase 2 — COMPLETE

Canonical frozen design is under `research/spread-points-nextgen/phase2/`, especially:

- `EVALUATION_HOLDOUT_PROTOCOL.md`
- `BOUNDED_IMPLEMENTATION_SPEC.md`
- `CHALLENGER_PREREGISTRATION.md`
- `MARKET_RESIDUAL_SPECIFICATION.md`
- `DATA_GAPS_AND_SOURCE_POLICY.md`
- `PHASE2_SYNTHESIS.md`

PR #520 merged at `405906942013252c158244c9b033a3240baa37f8`.

## Phase 3 — COMPLETE

Authoritative closeout: `FINAL_PHASE3_RECEIPT.md`.

Frozen implementation/evidence lives under `research/spread-points-nextgen/phase3/`, including the candidate registry, feature-provenance contract, implementation index, development evaluation, D eligibility receipt, synthesis, red-team audit, Phase 4 handoff, implementation modules and durable `phase3/evidence/` directory.

Preserved downstream component surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Final Phase 3 integration:

- PR #547 — MERGED
- final synchronized head `8c061cd400a6bb52a037d5e98880efd19a451fcb`
- merge `d4d29d8c2340864e2d9e4bcd793852e8643be80c`
- exact-head Phase 3 validation `35813365004` — SUCCESS
- exact-head research firewall `35813364985` — SUCCESS
- exact-head research validation `35813364975` — SUCCESS
- implementation SHA-256 `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256 `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`

## Phase 4 — COMPLETE

Authoritative closeout:

`research/spread-points-nextgen/FINAL_PHASE4_RECEIPT.md`

Primary branch:

`research/spread-points-nextgen-phase4`

Canonical Phase 4 evidence is under:

`research/spread-points-nextgen/phase4/`

Durable package:

- `HOLDOUT_OPENING_RECEIPT.json`
- `HOLDOUT_RUN_MANIFEST.json`
- `A0_HOLDOUT_2025.csv`
- `B0_HOLDOUT_2025.csv`
- `C0_HOLDOUT_2025.csv`
- `BASELINES_HOLDOUT_2025.csv`
- `DIAGNOSTIC_SLICES_2025.csv`
- `HOLDOUT_SUMMARY.json`
- `HOLDOUT_FAILURE_LOG.md`
- `HISTORICAL_VALIDATION_REPORT.md`
- `ABLATION_REPORT.md`
- `STATISTICAL_UNCERTAINTY_REPORT.md`
- `ROBUSTNESS_REPORT.md`
- `RED_TEAM_AUDIT.md`
- `PHASE4_SYNTHESIS.md`
- `PHASE5_HANDOFF.md`

Evidence boundary and execution receipts:

- pre-result opening receipt commit: `362af7af7db43a715b9ab9537a52d2749c37e7a6`
- first complete scientific holdout run: `35818332253`
- first-run generator head: `f0b92217488a1a000bee74a903a9437931a53230`
- exact first-run artifact: `10732945725`
- artifact metadata digest: `sha256:7e231406237dc0f27681cc974d07ba34a6fe3bb976bea42531bedc8166557671`
- exact artifact preservation workflow: `35819413238` — SUCCESS
- exact common 2025 games: **272**
- B0 simulations/game: **10,000**
- block bootstrap resamples: **10,000**
- Candidate 5 trained: **false**
- completed 2026 outcomes used: **false**
- production changed: **false**
- 2025 underlying holdout: **OPENED / SPENT**

Scientific disposition:

`NO_HISTORICAL_STANDALONE_FINALIST`

- A0 — valid underlying representation; not standalone finalist
- B0 — valid underlying possession/drive representation and negative structural reference; not standalone finalist
- C0 — market-aware diagnostic only; no demonstrated incremental football information beyond M0
- D — `ENSEMBLE_NOT_ELIGIBLE`

Primary Phase 4 integration:

- PR #550 — MERGED
- exact validated scientific head: `c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`
- dedicated Phase 4 exact-head validation `35820561374` — SUCCESS, including full regeneration and byte comparison
- research firewall `35820561354` — SUCCESS
- full research validation `35820561327` — SUCCESS
- primary merge `733f6d6a0497e996358282f38c61ea5fdd827040`
- merged `main` re-read and verified

The 2025 evidence must always be described as the **final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions**.

## Phase 5 — NOT STARTED

Working Candidate 5 identity remains:

`LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`

Phase 5 must consume the preserved chronology-clean 2022–2024 OOF component surface under its separate evidence-boundary rules. Because A0/B0/C0 2025 outputs and performance have now been observed, 2025 may not be described as a pristine Candidate 5 holdout.

Before Candidate-5-specific output is inspected, a future Phase 5 task must freeze the evidence boundary, component-inclusion rules, OOF stacking construction, model/tuning contract, mandatory ablations, uncertainty analysis and prospective-confirmation plan.

## Validation workflows

- `.github/workflows/research_validation.yml`
- `.github/workflows/research_firewall.yml`
- `.github/workflows/research_spread_points_phase3.yml`
- `.github/workflows/research_spread_points_phase4.yml`

## Current program stop

Phase 4 is complete. Candidate 5 is not trained. Completed 2026 outcomes remain outside Phase 4 selection. Production remains `F-ST-01-FROZEN-2026`.

**STOP until a separate Phase 5 task is started.**