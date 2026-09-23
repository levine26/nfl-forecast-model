# Phase 2 Handoff

## Phase 2 status

`NOT STARTED`.

This file is an implementation handoff only. It does not authorize execution before Phase 1 is merged and closed by `FINAL_PHASE1_RECEIPT.md`.

## Frozen inputs Phase 2 must read first

Before writing or running candidate code, read:

1. `MASTER_PLAN.md`
2. `PHASE_STATUS.md`
3. `PHASE1_RESEARCH_CHARTER.md`
4. `ATS_PROBLEM_REFORMULATION.md`
5. `DATA_AND_PIT_INVENTORY.md`
6. `Q1_QUANTILE_PREREGISTRATION.md`
7. `Q2_MARGIN_DISTRIBUTION_PREREGISTRATION.md`
8. `Q3_DIRECT_ATS_PREREGISTRATION.md`
9. `EVALUATION_PROTOCOL.md`
10. `CHRONOLOGY_AND_EVIDENCE_BOUNDARY.md`
11. `ATS_ECONOMICS_AND_EV_CONTRACT.md`
12. `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`
13. `preregistration.json`
14. `FINAL_PHASE1_RECEIPT.md`

The machine-readable registry and human-readable documents are a single contract. If they appear inconsistent, stop official candidate execution and resolve the documentation defect without looking at Q1-Q3 outer results.

## Exact Phase-2 starting action

Create a research-only Phase-2 branch and implement the **shared data/chronology/grading harness first**, before fitting Q1/Q2/Q3.

Required order:

### Step 1 — immutable dataset/provenance layer

Materialize eligible 2015–2025 regular-season rows with:

- canonical game ID;
- home/away score only as target/evaluation data;
- canonical spread `L`, market margin `S=-L`, residual target `R=M+L`;
- spread/total/moneyline provenance;
- frozen compact football features;
- source/market-horizon labels;
- explicit 2026 rejection guard.

Record counts and missingness before model performance is computed.

### Step 2 — synthetic grading/economics tests

Implement every mandatory sign, push, odds and T-120 test in `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`. These must pass before official candidate execution.

### Step 3 — fold registry

Implement deterministic outer seasons 2022–2025 and inner rolling seasons exactly as preregistered. Persist a fold receipt proving every prediction is trained only on earlier seasons.

### Step 4 — market nulls

Implement M0, M1 and M2 before candidates so every candidate comparison has its benchmark from the start.

### Step 5 — Q1 implementation

Implement only `Q1-QR-MARKET-RESIDUAL-V1`, the frozen alpha grid, feature list, preprocessing and deterministic quantile rearrangement. Unit-test registry rejection of unregistered variants.

### Step 6 — Q2 implementation

Implement only `Q2-DISCRETE-KEY-PMF-V1`, the frozen PMF support/base families/scale/key-mass rules and inner selection.

### Step 7 — Q3 implementation

Implement only `Q3-DIRECT-CPL-V1`, including structural push masking, OOF temperature calibration and frozen blend grid.

### Step 8 — pre-run freeze receipt

Before generating official outer results, commit a receipt with:

- Phase-1 merge SHA;
- exact code head;
- candidate registry hash;
- feature/data contract hash;
- fold registry;
- dependency/package versions;
- all synthetic/red-team checks passing;
- `completed_2026_outcomes_used=false`.

### Step 9 — controlled historical development

Only after Steps 1–8 are committed may Phase 2 produce 2022–2025 outer candidate evidence.

## Non-negotiable implementation constraints

- No random K-fold.
- No completed 2026 outcomes.
- No production F-ST/Sunday Signal changes.
- No new feature/model family because a result disappoints.
- No historical juice fabrication.
- No threshold/ROI fishing.
- No candidate-specific result before shared contracts/tests are complete.
- Preserve negative results.

## Expected Phase-2 outputs

Phase 2 should create a new subdirectory such as `research/ats-nextgen/phase2/` containing:

- data/provenance receipt;
- fold registry;
- implementation contract/registry;
- red-team test report;
- M0/M1/M2 evaluation;
- Q1 evaluation;
- Q2 evaluation;
- Q3/blend evaluation;
- uncertainty/key-number/selective ATS reports;
- negative-results ledger;
- final Phase-2 receipt;
- Phase-3 handoff.

## Stop condition

Phase 2 ends after controlled implementation/historical development. It does not promote production and does not start prospective validation.