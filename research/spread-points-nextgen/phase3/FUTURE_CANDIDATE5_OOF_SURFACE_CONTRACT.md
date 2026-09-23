# Future Candidate 5 OOF Surface Contract

This file documents the Phase 3 component surfaces preserved for possible later Phase 5 use. It does **not** authorize or implement Candidate 5.

Canonical durable surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Rows: 815 games, seasons 2022-2024 only.

## A0 preserved fields

At minimum the surface contains:

- home-win probability;
- expected margin;
- expected total;
- score uncertainty;
- offense-strength difference;
- defense-strength difference;
- candidate/config/code identity;
- train-through season.

## B0 preserved fields

At minimum:

- home-win probability;
- expected margin;
- expected total;
- margin variance;
- total variance;
- selected margin/total tail summaries;
- candidate/config/code identity;
- train-through season.

## C0 preserved fields

At minimum:

- market margin and total benchmark;
- predicted margin and total residual;
- hybrid margin and total;
- exact historical market-horizon label;
- candidate/config/code identity;
- train-through season.

## D

No D fields are eligible for downstream use because D failed its frozen eligibility gate for both targets. The component surface contract must not reinterpret the diagnostic nested blends as eligible D candidates.

## OOF provenance

Every preserved component row asserts that its `train_through_season` is strictly earlier than the target season. The source manifest records:

- generator head `3d893ec8e26824f7e6c1883f4d0d09c19160c712`;
- implementation SHA-256 `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`;
- config SHA-256 `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`;
- loaded seasons 2016-2024;
- 2025 loaded = false;
- 2025 challenger scored = false;
- completed-2026 outcomes used = false;
- Candidate 5 trained = false.

Phase 5 must independently re-verify these receipts before consuming any component input. It may not convert these surfaces into same-row/in-sample stacking data or infer a pristine 2025 Candidate 5 holdout.
