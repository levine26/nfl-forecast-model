# Phase 3 Synthesis

## Disposition

Phase 3 implemented the frozen A0/B0/C0 program under the pre-result decision:

**KEEP_FROZEN_PHASE3_CONTRACT**

No preregistration amendment was made after the research delta. No model zoo, rescue model, threshold search, completed-2026 selection, 2025 scoring, Candidate 5 training, or production change occurred.

## Research gate

The targeted preimplementation review added the required user-supplied systems and additional chronology-aware/negative evidence. The review reinforced rather than displaced the Phase 2 design: simple/shrunk football representations, explicit market reconciliation, temporal validation, and strong skepticism toward randomly split sportsbook-beating claims.

The external-research delta is recorded in `PREIMPLEMENTATION_RESEARCH_REVIEW.md`; the frozen gate is machine-readable in `PRE_RESULT_GATE.json`.

## Implementation

One shared scaffold controls identity, sign, folds, training-only preprocessing, source/PIT semantics, receipts, block bootstrap, development guards, 2025 firewall and completed-2026 firewall.

Frozen candidate identities:

- A0: `A0-DYNAMIC-OPPONENT-ADJUSTED-JOINT-SCORE-V1`
- B0: `B0-POSSESSION-DRIVE-SCORE-PROCESS-V1`
- C0: `C0-MARKET-RESIDUAL-MARGIN-TOTAL-V1`

The first full CI regeneration exposed a schedule/PBP merge-schema defect (`home_team` suffixing). The failed run was retained. The defect was fixed by canonicalizing schedule-owned identity columns before the drive join, and a regression test was added. No scientific feature, grid, estimator or selection rule changed.

## Development evidence

The corrected exact validated development run is `35810171571` at head `3d893ec8e26824f7e6c1883f4d0d09c19160c712`.

Pooled 2022-2024 findings:

- A0 margin/total MAE: **9.8825 / 10.3869**
- B0 margin/total MAE: **10.2132 / 11.3044**
- market M0 margin/total MAE: **9.4184 / 10.1209**
- C0 M3 margin/total MAE: **9.4390 / 10.1376**
- C0 margin disposition: **NO_INCREMENTAL_FOOTBALL_EDGE**
- C0 total disposition: **NO_INCREMENTAL_FOOTBALL_EDGE**
- D margin: **ENSEMBLE_NOT_ELIGIBLE**
- D total: **ENSEMBLE_NOT_ELIGIBLE**

A0 and B0 remain valid negative/reference models because methodological validity is not conditioned on winning development MAE.

## Durable evidence

The exact validated package is preserved under `phase3/evidence/`, including:

- A0/B0/C0 2022-2024 OOF rows;
- baselines;
- diagnostic slices;
- candidate run receipts;
- development summary;
- D eligibility receipt;
- run manifest;
- compact future Candidate 5 OOF component surface.

Validated evidence artifact before preservation:

- workflow run: `35810171571`
- artifact: `spread-points-phase3-35810171571`
- artifact digest: `sha256:516496990fec29e17479e0f55b7e21f82381f510f394a631df6bf4dea3475b41`

## Firewalls

The evidence manifest proves:

- loaded seasons: 2016-2024 only;
- development targets: 2022-2024 only;
- 2025 loaded: false;
- 2025 challenger scored: false;
- completed-2026 outcomes used for selection: false;
- Candidate 5 trained: false;
- production model remains `F-ST-01-FROZEN-2026`.

## Scientific interpretation

The development result is deliberately not converted into a favorable narrative. The market remains the strongest exact paired margin/total baseline. A0 carries an independent football representation useful for downstream scientific comparison, B0 demonstrates that a bounded possession/drive decomposition does not automatically buy accuracy, and C0 fails to establish incremental football residual information beyond the historical closing/late benchmark.

That negative finding is a successful Phase 3 scientific outcome because it narrows what can be claimed without contaminating the 2025 holdout.

## Next action

Phase 4 is the next program phase and remains **NOT STARTED** until this Phase 3 package is merged and verified from `main`.

Phase 4 must open the 2025 underlying-model holdout once using the frozen identities above. It must not start Candidate 5. See `PHASE4_HANDOFF.md`.
