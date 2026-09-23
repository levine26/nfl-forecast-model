# Spread & Points Next-Generation — Research Index

**Authority:** `MASTER_PLAN.md`  
**Purpose:** Canonical map of the Spread & Points research program.  
**Last reconciled:** 2026-09-23 America/Los_Angeles

This index is a map, not an authorization mechanism. Candidate identity and evidence boundaries are controlled by frozen contracts and phase receipts.

## Program controls

- `research/spread-points-nextgen/MASTER_PLAN.md`
- `research/spread-points-nextgen/PHASE_STATUS.md`
- `research/spread-points-nextgen/CURRENT_STATE_AND_NEXT_STEPS.md`
- `research/spread-points-nextgen/DECISION_LOG.md`
- `research/spread-points-nextgen/RESEARCH_INDEX.md`
- `research/spread-points-nextgen/FINAL_PHASE3_RECEIPT.md`
- `research/spread-points-nextgen/FINAL_PHASE4_RECEIPT.md`
- `research/spread-points-nextgen/FINAL_PHASE5_RECEIPT.md`

## Production firewall

Production remains `F-ST-01-FROZEN-2026`. Key protected surfaces include `src/nfl_forecast/fst_production.py`, `src/nfl_forecast/artifacts/F-ST-01-FROZEN-2026.json`, `research/fst/F-ST-01-FROZEN-2026.json`, `src/nfl_forecast/pipeline.py`, `src/nfl_forecast/public_forecast.py`, `outputs/`, `site/`, and weekly publication/lock scripts.

Research may not alter production F-ST coefficients, winner selection, public fair-spread semantics, official history, forecast locks, grading, or Sunday Signal forecasting behavior without later explicit authorization.

## Phase 1 — COMPLETE

Canonical evidence is under `research/spread-points-nextgen/phase1/`. PR #513 merged at `a4f7172c0c4ff82b1689411181e7a9042a1628a8`.

## Phase 2 — COMPLETE

Canonical frozen design is under `research/spread-points-nextgen/phase2/`. PR #520 merged at `405906942013252c158244c9b033a3240baa37f8`.

## Phase 3 — COMPLETE

Authoritative closeout: `FINAL_PHASE3_RECEIPT.md`.

Frozen implementation/evidence lives under `research/spread-points-nextgen/phase3/`. Preserved downstream component surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Final integration:

- PR #547 — MERGED
- final synchronized head `8c061cd400a6bb52a037d5e98880efd19a451fcb`
- merge `d4d29d8c2340864e2d9e4bcd793852e8643be80c`
- exact-head Phase 3 validation `35813365004` — SUCCESS
- research firewall `35813364985` — SUCCESS
- full research validation `35813364975` — SUCCESS
- implementation SHA-256 `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256 `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`

## Phase 4 — COMPLETE

Authoritative closeout: `research/spread-points-nextgen/FINAL_PHASE4_RECEIPT.md`.

Canonical evidence is under `research/spread-points-nextgen/phase4/`, including the opening receipt, frozen A0/B0/C0 2025 outputs, baselines, diagnostics, historical-validation/ablation/uncertainty/robustness/red-team reports, synthesis, and Phase 5 handoff.

Key receipts:

- pre-result opening receipt commit `362af7af7db43a715b9ab9537a52d2749c37e7a6`
- first complete scientific holdout run `35818332253`
- exact common 2025 games: **272**
- scientific disposition: **`NO_HISTORICAL_STANDALONE_FINALIST`**
- exact validated head `c314dece97e5048f95ec5bb021d3fb7eb9f5dd33`
- exact-head validation `35820561374` — SUCCESS
- research firewall `35820561354` — SUCCESS
- full research validation `35820561327` — SUCCESS
- merge `733f6d6a0497e996358282f38c61ea5fdd827040`

2025 is **OPENED / SPENT** for the underlying A0/B0/C0 evaluation.

## Phase 5 — COMPLETE; CANDIDATE 5 REJECTED

Authoritative closeout:

`research/spread-points-nextgen/FINAL_PHASE5_RECEIPT.md`

Primary branch:

`research/spread-points-nextgen-phase5`

Candidate identity:

`LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`

Scientific freeze:

`df14e51d73aad96899d3ba4364cbb76989f0d2bf`

Merged implementation identities:

- code SHA-256 `55f62f9de44e853f820016c893c6d94a9a2226f7c08e412260a7cf5d10c9b4c2`
- config SHA-256 `5762ac921519e594412d0dbcc6ced49d8fb332672e83bb0c5e54cd53d04299ce`

The Phase 5 contract was committed before Candidate-5-specific performance. It freezes the evidence boundary, component policy, F-ST provenance, feature sets, chronology-clean meta-stacking, L2 offset-logistic model, lambda selection, threshold, ablations, metrics, uncertainty, 2025 diagnostic rule, and scientific disposition rule.

Canonical Phase 5 package under `research/spread-points-nextgen/phase5/`:

### Preregistration / contract

- `CANDIDATE5_RESEARCH_CHARTER.md`
- `CANDIDATE5_EVIDENCE_BOUNDARY.md`
- `CANDIDATE5_FEATURE_AND_COMPONENT_CONTRACT.md`
- `CANDIDATE5_OOF_STACKING_PROTOCOL.md`
- `CANDIDATE5_MODEL_SPECIFICATION.md`
- `CANDIDATE5_ABLATION_PLAN.md`
- `CANDIDATE5_EVALUATION_PROTOCOL.md`
- `CANDIDATE5_FREEZE_RECEIPT.json`
- `candidate5_config.json`

### Reproducible implementation / validation

- `candidate5_residual_stack_v1.py`
- `test_candidate5_residual_stack_v1.py`
- `.github/workflows/research_spread_points_phase5.yml`
- `PHASE5_FAILURE_LOG.md`

### Immutable evidence / results

- `CANDIDATE5_DEVELOPMENT_PREDICTIONS_2022_2024.csv`
- `CANDIDATE5_2025_DIAGNOSTIC.csv`
- `CANDIDATE5_ABLATION_METRICS.csv`
- `CANDIDATE5_CALIBRATION.csv`
- `CANDIDATE5_RELIABILITY.csv`
- `CANDIDATE5_SLICES.csv`
- `CANDIDATE5_MODEL_FITS.json`
- `CANDIDATE5_RUN_MANIFEST.json`
- `CANDIDATE5_RESULTS.json`
- `CANDIDATE5_BOOTSTRAP_SUMMARY.json`
- `CANDIDATE5_HISTORICAL_RESULTS.md`
- `CANDIDATE5_UNCERTAINTY_REPORT.md`
- `CANDIDATE5_CALIBRATION_REPORT.md`
- `CANDIDATE5_RED_TEAM_AUDIT.md`
- `PHASE5_SYNTHESIS.md`

Execution provenance:

- first workflow attempt `35827845845` — pre-result unit-test failure only; no Candidate-5-specific metrics generated
- engineering-only fixture correction `b86b7c98b40a3b68e6fb4e42f9aeb6592554065a`
- first successful frozen historical workflow `35828122187` — contract gate, historical package, and exact-run gate SUCCESS
- evidence preservation commit `8fce0be359d93d68bc2c4bba852ede4181a38368`

Primary 2022–2024 result:

- games: **815**
- F-ST: **562/815 = 68.9571%**
- Candidate 5 primary: **562/815 = 68.9571%**
- accuracy delta: **0.0000 pp**
- winner switches: **0**
- Brier delta: **+0.00000573**
- log-loss delta: **+0.00001352**
- calibration intercept/slope: Candidate 5 **0.09794 / 1.12581**, F-ST **0.09772 / 1.12626**
- scientific disposition: **`REJECTED`**
- Phase 6 eligible: **false**

2025 was executed only after the complete freeze and is labeled `POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`. On 272 games, both F-ST and Candidate 5 were 179/272 with zero winner switches. It did not select or rescue the candidate.

Final integration:

- PR #552 — **MERGED**
- exact validated head `a4f892d64ab163a421eed203d9b50983e5bbd04b`
- Phase 5 validation `35875417408` — SUCCESS
- research firewall `35875417416` — SUCCESS
- full research validation `35875417452` — SUCCESS
- Phase 4 reproducibility regression `35875417543` — SUCCESS
- merge `a68afb1e1cf9675a7ff9e0e0af1f52343546f029`

No Phase 6 handoff exists because the preregistered eligibility rule was not satisfied.

## Validation workflows

- `.github/workflows/research_validation.yml`
- `.github/workflows/research_firewall.yml`
- `.github/workflows/research_spread_points_phase3.yml`
- `.github/workflows/research_spread_points_phase4.yml`
- `.github/workflows/research_spread_points_phase5.yml`

## Current program state

Phase 5 is fully closed with Candidate 5 V1 `REJECTED`. Completed 2026 outcomes remained outside Candidate 5 historical selection. Production remains `F-ST-01-FROZEN-2026`.

**STOP this candidate program. Do not start Phase 6 for Candidate 5 V1. Do not rescue the rejected identity. Any future challenger requires separate authorization, a new preregistration, and a new candidate identity.**
