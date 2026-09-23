# Phase 4 Handoff — Prepare Only

Phase 4 is **NOT STARTED**. This handoff freezes the Phase 3 starting state for the one-time 2025 underlying-model evaluation.

## Frozen underlying candidates

- A0: `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`
- B0: `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`
- C0: `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`
- D margin: `ENSEMBLE_NOT_ELIGIBLE`
- D total: `ENSEMBLE_NOT_ELIGIBLE`

Implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`

Config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`

Validated development source head: `3d893ec8e26824f7e6c1883f4d0d09c19160c712`

## Development evidence to carry forward

- A0 pooled margin/total MAE: 9.8825 / 10.3869
- B0 pooled margin/total MAE: 10.2132 / 11.3044
- C0 M3 pooled margin/total MAE: 9.4390 / 10.1376
- exact market M0 margin/total MAE: 9.4184 / 10.1209
- C0 disposition: `NO_INCREMENTAL_FOOTBALL_EDGE` for both targets
- D: not eligible for both targets

Negative results are part of the frozen record and may not be pruned before the 2025 holdout.

## Exact Phase 4 opening rule

Phase 4 may open the 2025 underlying-model holdout once. Before running it, Phase 4 must re-read:

- `MASTER_PLAN.md`
- `PHASE_STATUS.md`
- `CURRENT_STATE_AND_NEXT_STEPS.md`
- `phase2/EVALUATION_HOLDOUT_PROTOCOL.md`
- `phase3/PHASE3_SYNTHESIS.md`
- `phase3/evidence/RUN_MANIFEST.json`
- candidate registry and provenance contract.

The Phase 4 runner must use the frozen candidate code/config identities without development-result rescue changes.

Required evaluation remains the preregistered score, margin, total, probability, distributional, exact paired-market, season/week block-bootstrap, diagnostic-slice and ablation package.

## Required ablations / checks

At minimum Phase 4 must preserve the frozen A0/B0/C0 identities, repeat the C0 M0/M1/M2/M3 hierarchy on the one-time holdout rows, verify all market pairing/horizon labels, and audit prediction receipts before interpretation.

No Candidate 5 stack may be trained or evaluated as part of opening the Phase 4 underlying holdout.

## Statistical uncertainty

Use exact paired rows and the same season/week-aware paired uncertainty machinery where meaningful. Do not convert ATS or O/U diagnostics into the primary model-selection criterion.

## Preserved future Phase 5 surfaces

The chronology-clean 2022-2024 component surface is:

`phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Candidate 5 remains **NOT STARTED** until Phase 4 is formally complete.
