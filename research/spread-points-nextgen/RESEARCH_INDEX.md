# Spread & Points Next-Generation — Research Index

**Authority:** `MASTER_PLAN.md`  
**Purpose:** Canonical map of the active Spread & Points research program.  
**Last reconciled:** 2026-09-22 America/Los_Angeles

This index is a map, not an authorization mechanism. Candidate identity and evidence boundaries are controlled by the frozen contracts and phase receipts.

## Program controls

- `research/spread-points-nextgen/MASTER_PLAN.md`
- `research/spread-points-nextgen/PHASE_STATUS.md`
- `research/spread-points-nextgen/CURRENT_STATE_AND_NEXT_STEPS.md`
- `research/spread-points-nextgen/DECISION_LOG.md`
- `research/spread-points-nextgen/RESEARCH_INDEX.md`
- `research/spread-points-nextgen/FINAL_PHASE3_RECEIPT.md`

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

Research may not alter production F-ST coefficients, winner selection, public fair-spread semantics, official history, forecast locks, grading, or Sunday Signal forecasting behavior.

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

Frozen implementation/evidence lives under `research/spread-points-nextgen/phase3/`:

- `CANDIDATE_REGISTRY.json`
- `FEATURE_PROVENANCE_CONTRACT.md`
- `IMPLEMENTATION_INDEX.md`
- `DEVELOPMENT_EVALUATION.md`
- `D_ELIGIBILITY_RECEIPT.md`
- `PHASE3_SYNTHESIS.md`
- `PHASE4_HANDOFF.md`
- `RED_TEAM_AUDIT.md`
- `run_phase3.py`
- `phase3_a0.py`
- `phase3_b0.py`
- `phase3_c0.py`
- `phase3_data.py`
- `phase3_evaluation.py`
- `phase3_scaffold.py`
- durable evidence directory `phase3/evidence/`

Preserved downstream component surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Final integration:

- Phase 3 PR #547 — MERGED
- final synchronized head `8c061cd400a6bb52a037d5e98880efd19a451fcb`
- merge `d4d29d8c2340864e2d9e4bcd793852e8643be80c`
- exact-head Phase 3 validation `35813365004` SUCCESS
- exact-head research firewall `35813364985` SUCCESS
- exact-head research validation `35813364975` SUCCESS
- implementation SHA-256 `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256 `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`

## Phase 4 — IN PROGRESS

Primary branch:

`research/spread-points-nextgen-phase4`

Phase 4 owns the one-time 2025 underlying-model holdout for frozen A0/B0/C0 only. Required canonical output directory:

`research/spread-points-nextgen/phase4/`

Expected durable package includes:

- `HOLDOUT_OPENING_RECEIPT.json`
- `HOLDOUT_RUN_MANIFEST.json`
- `A0_HOLDOUT_2025.csv`
- `B0_HOLDOUT_2025.csv`
- `C0_HOLDOUT_2025.csv`
- `BASELINES_HOLDOUT_2025.csv`
- `DIAGNOSTIC_SLICES_2025.csv`
- `HOLDOUT_SUMMARY.json`
- `HISTORICAL_VALIDATION_REPORT.md`
- `ABLATION_REPORT.md`
- `STATISTICAL_UNCERTAINTY_REPORT.md`
- `ROBUSTNESS_REPORT.md`
- `RED_TEAM_AUDIT.md`
- `PHASE4_SYNTHESIS.md`
- `PHASE5_HANDOFF.md`

2025 is described consistently as the **final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions**.

## Phase 5 — NOT STARTED

Working Candidate 5 identity remains `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`. Phase 5 must consume the preserved chronology-clean 2022–2024 OOF component surface and obey its separate evidence-boundary rules. Phase 4 must not train it.

## Validation workflows

- `.github/workflows/research_validation.yml`
- `.github/workflows/research_spread_points_phase3.yml`
- Phase 4 dedicated holdout workflow will be indexed here after it is committed.

### Phase 4 — scientific package complete; merge closeout pending

- pre-result opening receipt — `research/spread-points-nextgen/phase4/HOLDOUT_OPENING_RECEIPT.json` (commit `362af7af7db43a715b9ab9537a52d2749c37e7a6`)
- exact first completed holdout run — `35818332253`, generator head `f0b92217488a1a000bee74a903a9437931a53230`
- exact first-run artifact — `10732945725`, metadata digest `sha256:7e231406237dc0f27681cc974d07ba34a6fe3bb976bea42531bedc8166557671`
- exact artifact preservation workflow — `35819413238` SUCCESS; verified provenance and all evidence SHA-256 values before commit
- raw holdout predictions — `phase4/A0_HOLDOUT_2025.csv`, `B0_HOLDOUT_2025.csv`, `C0_HOLDOUT_2025.csv`
- reference baselines — `phase4/BASELINES_HOLDOUT_2025.csv`
- fixed diagnostic slices — `phase4/DIAGNOSTIC_SLICES_2025.csv`
- machine summary / run manifest — `phase4/HOLDOUT_SUMMARY.json`, `phase4/HOLDOUT_RUN_MANIFEST.json`
- execution failure/boundary log — `phase4/HOLDOUT_FAILURE_LOG.md`
- historical validation — `phase4/HISTORICAL_VALIDATION_REPORT.md`
- preregistered ablation analysis — `phase4/ABLATION_REPORT.md`
- uncertainty — `phase4/STATISTICAL_UNCERTAINTY_REPORT.md`
- robustness / fixed slices — `phase4/ROBUSTNESS_REPORT.md`
- red-team audit — `phase4/RED_TEAM_AUDIT.md`
- synthesis — `phase4/PHASE4_SYNTHESIS.md`
- Phase 5 handoff — `phase4/PHASE5_HANDOFF.md`
- scientific disposition — `NO_HISTORICAL_STANDALONE_FINALIST`; A0/B0 valid underlying representations but not standalone finalists; C0 market-aware diagnostic only; D remains ineligible
- Candidate 5 — NOT STARTED / untrained; completed 2026 outcomes unused; production `F-ST-01-FROZEN-2026` unchanged
