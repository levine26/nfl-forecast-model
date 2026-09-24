# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**.

Phase 2 is **COMPLETE**. PR #563 passed all eight exact-head validation workflows and merged to `main` at `a9ba2a5759c1308e6a47e682240a4e79dd419726`.

Production remains `F-ST-01-FROZEN-2026`. No completed-2026 outcome has been used by the ATS Next-Generation historical candidate program.

## Frozen Phase-2 evidence

### Q1 — quantile market-residual model

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` is a **valid negative incremental result** versus M2.

- 1,087 chronology-clean 2022–2025 outer OOF rows;
- accepted OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 minus M2 mean frozen-quantile pinball `+0.0001307888` (worse);
- Stage-D 95% interval `[-0.0023784358,+0.0025555440]`, `P(better)=0.4554`;
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
- Stage-D 95% interval `[-0.0015590942,+0.0043366478]`, `P(better)=0.1842`;
- non-push Brier delta `+0.0006716459`, `P(better)=0.1851`;
- no learner/feature/C-grid/class-weight/calibration/threshold/slice rescue authorized.

## Stage D — accepted final evidence synthesis

Accepted execution:

- scientific execution head `0030de3fcc3fd094f1ce28eb0ab1c20b748ca67a`;
- scientific tree `cf161bc7b47d8d138fd35dfe4889ccc215c91b5b`;
- workflow `35936805090`: **SUCCESS**;
- artifact `10783239110`;
- artifact digest `sha256:4a3bd19a48528a2772e69232ad10b959b1f66e3885e44b56772f0b379abbcdd2`;
- 10,000 paired `(season, week)` bootstrap draws over 72 blocks, seed 26;
- Q1 and Q3 regenerated accepted evidence matched all frozen file hashes exactly;
- completed-2026 outcomes used: 0;
- production changed: no.

Final closeout validation:

- closeout head `619959f50bb7f9cbbc1ed9fbc562547db7f17487`;
- research firewall: **SUCCESS**;
- Phase-2 opening gate: **SUCCESS**;
- Q1 frozen reproduction: **SUCCESS**;
- Q2 structural-invalidity closeout: **SUCCESS**;
- Q3 negative-result closeout: **SUCCESS**;
- Stage-D frozen synthesis reproduction: **SUCCESS**;
- research validation: **SUCCESS**;
- full pytest / regenerated-output validation: **SUCCESS**;
- Stage-D reproduction artifact `10784362608`: all four scientific files matched the accepted Stage-D artifact byte-for-byte by SHA-256;
- PR #563 merge / verified `main`: `a9ba2a5759c1308e6a47e682240a4e79dd419726`.

Simple hit-rate diagnostic only:

- Q3-M2 `52.8355%` on 1,058 non-push rows, exact 95% CI `[49.7759%,55.8793%]`;
- Q3 `52.1739%`, exact 95% CI `[49.1142%,55.2215%]`.

The hit-rate diagnostic and intervals cannot rescue or reclassify a candidate. Historical side-price provenance remains insufficient for a new ROI/EV claim.

Immutable Phase-2 evidence:

- `PHASE2_STAGE_D_RESULT_RECEIPT.md`;
- `phase2_stage_d_result_registry.json`;
- `FINAL_PHASE2_RECEIPT.md`.

## Exact next actions

1. merge this governance-only final receipt after its exact-head research/production-firewall validation;
2. verify the resulting governance merge on `main`;
3. create the Phase-3 branch from that exact verified merge SHA;
4. read `PHASE3_HANDOFF.md` and the frozen Phase-1 evaluation/classification rules;
5. freeze a Phase-3 opening/classification receipt before assigning any disposition;
6. perform classification only — no candidate development, fitting, rescue, or completed-2026 outcome use;
7. stop before Phase 4 unless the user explicitly authorizes continuation.

## Phase-3 boundary

Phase 3 is classification, not another candidate-development round. It must classify each frozen architecture as `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` using the accepted Phase-2 package.

The Phase-1 eligibility gate requires improvement in the candidate's primary proper/quantile metric versus the matching market null on exact common OOF rows, along with no material calibration/systematic failure, no single-season/week/key-bucket dependence, no leakage/red-team failure, and consistency with the preregistered model identity.

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
