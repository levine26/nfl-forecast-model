# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**.

Phase 2 scientific work is **COMPLETE THROUGH STAGE D**. The only remaining Phase-2 action is exact-head closeout validation and merge of PR #563.

Production remains `F-ST-01-FROZEN-2026`. No completed-2026 outcome has been used by the ATS Next-Generation historical candidate program.

## Frozen Phase-2 evidence

### Q1 — quantile market-residual model

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` is a **valid negative incremental result** versus M2.

- 1,087 chronology-clean 2022–2025 outer OOF rows;
- accepted OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 minus M2 mean frozen-quantile pinball `+0.0001307888` (worse);
- no rescue authorized.

### Q2 — discrete key-margin distribution

`ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` is **structurally invalid under the frozen V1 support/truncation contract**.

- frozen support `[-75,+75]`;
- maximum folded endpoint mass `0.0033487075822347966` exceeded frozen `0.001` fail-closed threshold;
- no accepted Q2 OOF artifact or primary performance result;
- Q2 complementarity and Q2/Q3 blend unavailable;
- no support/family/grid/key/scale/smoothing rescue authorized.

### Q3 — direct cover/push/loss hurdle

`ATS-Q3-DIRECT-CPL-HURDLE-V1` is a **valid negative incremental result / not incremental versus Q3-M2**.

- 1,087 chronology-clean exact-row OOF games, 2022–2025;
- accepted OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- Q3 minus Q3-M2 multinomial CPL log loss `+0.0013157419` (worse);
- no learner/feature/C-grid/class-weight/calibration/threshold/slice rescue authorized.

## Stage D — accepted final evidence synthesis

Accepted execution:

- branch `research/ats-nextgen-phase2-stage-d` / PR #563;
- scientific execution head `0030de3fcc3fd094f1ce28eb0ab1c20b748ca67a`;
- scientific tree `cf161bc7b47d8d138fd35dfe4889ccc215c91b5b`;
- workflow `35936805090`: **SUCCESS**;
- artifact `10783239110`;
- artifact digest `sha256:4a3bd19a48528a2772e69232ad10b959b1f66e3885e44b56772f0b379abbcdd2`;
- 10,000 paired `(season, week)` bootstrap draws over 72 blocks, seed 26;
- Q1 and Q3 regenerated accepted evidence matched all frozen file hashes exactly;
- completed-2026 outcomes used: 0;
- production changed: no.

Paired uncertainty:

- Q1 − M2 mean-three-quantile pinball: `+0.0001307888`, 95% interval `[-0.0023784358,+0.0025555440]`, `P(better)=0.4554`;
- Q3 − Q3-M2 multinomial CPL log loss: `+0.0013157419`, 95% interval `[-0.0015590942,+0.0043366478]`, `P(better)=0.1842`;
- Q3 − Q3-M2 non-push conditional-cover Brier: `+0.0006716459`, 95% interval `[-0.0007977772,+0.0022129221]`, `P(better)=0.1851`.

Simple hit-rate diagnostic only:

- Q3-M2 `52.8355%` on 1,058 non-push rows, exact 95% CI `[49.7759%,55.8793%]`;
- Q3 `52.1739%`, exact 95% CI `[49.1142%,55.2215%]`.

The hit-rate diagnostic and intervals cannot rescue or reclassify a candidate. Historical side-price provenance remains insufficient for a new ROI/EV claim.

Immutable closeout evidence:

- `PHASE2_STAGE_D_RESULT_RECEIPT.md`;
- `phase2_stage_d_result_registry.json`.

## Exact next actions

1. validate the exact Stage-D closeout head with the Stage-D contract/synthesis workflow, research firewall, opening-gate reproduction, frozen Q1/Q2/Q3 closeout checks, research validation, and full repository validation;
2. verify PR #563 describes the accepted Stage-D result rather than the obsolete pre-execution state;
3. merge PR #563 only after required exact-head gates are green;
4. verify the resulting merge is current `main`;
5. treat Phase 2 as closed;
6. begin **Phase 3 — Scientific Synthesis, Candidate Selection & Freeze** only from that verified merge and only with accepted Phase-2 evidence.

## Phase-3 boundary

Phase 3 is classification, not another candidate-development round. It must classify each frozen architecture as `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` using the Phase-2 package.

Phase 3 must not:

- redesign or rescue Q1/Q2/Q3;
- manufacture Q2 OOF, complementarity, or a Q2/Q3 blend;
- use completed-2026 outcomes;
- search new thresholds/slices/features/learners;
- use ATS hit rate or hypothetical ROI to overturn proper-score evidence;
- change production F-ST/Sunday Signal numerical behavior;
- promote a candidate directly to production.

Phase 4 remains conditional: it may begin only if Phase 3 earns prospective-shadow eligibility and the user explicitly authorizes continuation.

> Historical 2022–2025 evidence is chronology-clean development evidence, not pristine independent confirmation, because those seasons have informed prior LevLine research.
