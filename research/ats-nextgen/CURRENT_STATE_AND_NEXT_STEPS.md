# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**.

Phase 2 is **COMPLETE — SCIENTIFIC AND GOVERNANCE CLOSEOUTS MERGED**.

Phase 3 is **COMPLETE — CLASSIFICATION & FREEZE** on branch `research/ats-nextgen-phase3`, pending validation/merge of the classification-only package.

Production remains `F-ST-01-FROZEN-2026`. Completed-2026 outcomes used by the ATS Next-Generation program: `0`.

The final Phase-3 classification is:

- Q1 `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`: **REJECTED** — failed the frozen primary incremental quantile gate versus M2;
- Q2 `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`: **REJECTED** — structurally invalid under the frozen V1 support/truncation contract;
- Q3 `ATS-Q3-DIRECT-CPL-HURDLE-V1`: **REJECTED** — failed the frozen primary incremental proper-score gate versus Q3-M2;
- `INCONCLUSIVE`: **0**;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`: **0**;
- prospective-shadow specification: **not created**;
- Phase 4: **NOT AUTHORIZED / NOT STARTED**.

No candidate was refit, rerun, retuned, rescued, recalibrated or redesigned in Phase 3. No new 2022–2025 predictions were generated.

## Authoritative opening boundary

- Phase-2 scientific closeout: PR #566 / merge `89f8b4fa48e22554029392b303225e4665b4b673`;
- Phase-2 governance closeout: PR #567;
- governance validated head: `ee056a281303f2b5e60e7652fb2c45d85337a116`;
- governance merge / verified Phase-3 base: `a5c7bf6c37b9d1b385bfe88bd1a329ddd3bb63f0`;
- Phase-3 opening receipt commit: `d2be05c3f74e5b6095a9714bd58e7f0984c59276`;
- Stage-D scientific origin: PR #564 / head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- Stage-D workflow `35938628588`, artifact `10783982962`, digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`.

## Final candidate evidence

### Q1 — REJECTED

- accepted OOF rows: 1,087;
- Q1 − M2 mean-three-quantile pinball: `+0.0001307887665715768`;
- paired 95% CI: `[-0.002378435765685505, +0.002555544033066125]`;
- P(Q1 better): `0.4554`;
- reason: `FAILED_PRIMARY_INCREMENTAL_QUANTILE_GATE`.

Q1 is rejected as the frozen V1 incremental architecture. The interval crossing zero means a material harmful effect is not established; it does not provide the positive primary-metric improvement required for prospective-shadow eligibility.

### Q2 — REJECTED

- frozen support `[-75,+75]`;
- frozen endpoint-mass threshold `0.001`;
- observed maximum folded endpoint mass `0.0033487075822347966`;
- accepted complete Q2 OOF: none;
- accepted primary Q2 performance: none;
- reason: `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`.

Q2 is rejected as V1 because the frozen numerical-support specification failed closed. A future wider-support architecture would be a new experiment, not a rescue or continuation of Q2 V1.

### Q3 — REJECTED

- accepted OOF rows: 1,087;
- Q3 − Q3-M2 CPL log-loss: `+0.0013157418572419255`;
- paired 95% CI: `[-0.0015590942193462521, +0.004336647782633088]`;
- P(Q3 better): `0.1842`;
- non-push Brier delta: `+0.0006716459171549338`;
- Q3 cover-calibration slope `0.27094382668690847` vs Q3-M2 `0.8130523437112027`;
- reason: `FAILED_PRIMARY_INCREMENTAL_PROPER_SCORE_GATE`.

Q3's preregistration explicitly requires rejection when its proper scores fail versus Q3-M2. Favorable ATS subsets or hit-rate diagnostics cannot rescue that result.

## Exact next actions

1. validate the Phase-3 classification-only branch against repository firewalls and normal checks;
2. confirm the final diff is confined to Phase-3 research/governance files plus the two read-first status documents;
3. merge the Phase-3 PR only if its exact head is green;
4. verify the Phase-3 merge on current `main` and preserve the final receipt/registry as the program's terminal V1 classification state;
5. do **not** start Phase 4 because no candidate is eligible for prospective shadow;
6. any future ATS architecture must begin as a new explicitly authorized research amendment/version rather than a post-hoc rescue of Q1/Q2/Q3 V1.

## Active firewalls

- no completed-2026 outcome use;
- no new historical candidate execution in Phase 3;
- no Q1 rescue;
- no Q2 reconstruction/support widening/rescue;
- no Q3 learner/calibration rescue;
- no substitute Q2 distribution or Q2/Q3 blend;
- no ATS hit-rate/ROI/slice override of failed primary evidence;
- no prospective shadow without an eligible candidate;
- no production F-ST/Sunday Signal numerical forecasting changes.

> 2022–2025 remains chronology-clean development evidence but is not pristine independent confirmation because those seasons have informed prior LevLine research.