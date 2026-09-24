# ATS Next-Generation — Phase 3 Handoff

**Status:** READY AFTER PHASE-2 CLOSEOUT MERGE  
**Next phase:** Phase 3 — Scientific Synthesis, Candidate Selection & Freeze  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

## Read-first authority

Before any Phase-3 action, read:

1. `MASTER_PLAN.md`;
2. `FINAL_PHASE2_RECEIPT.md`;
3. `PHASE2_STAGE_D_RESULT_RECEIPT.md`;
4. `phase2_stage_d_result_registry.json`;
5. `PHASE2_Q1_RESULT_RECEIPT.md` / `phase2_q1_result_registry.json`;
6. `PHASE2_Q2_RESULT_RECEIPT.md` / `phase2_q2_result_registry.json`;
7. `PHASE2_Q3_RESULT_RECEIPT.md` / `phase2_q3_result_registry.json`;
8. `EVALUATION_PROTOCOL.md`;
9. `CHRONOLOGY_AND_EVIDENCE_BOUNDARY.md`;
10. `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`.

If chat memory conflicts with those files, the repository controls.

## Immutable evidence entering Phase 3

### Q1

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` is a valid negative incremental result versus M2.

- accepted OOF rows: 1,087;
- Q1 − M2 mean-three-quantile pinball: `+0.0001307887665715768`;
- Stage-D paired 95% CI: `[-0.002378435765685505, +0.002555544033066125]`;
- bootstrap probability Q1 better: `0.4554`.

No Q1 rescue is authorized.

### Q2

`ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` is structurally invalid under its frozen V1 support/truncation contract.

- no valid accepted Q2 OOF;
- no accepted Q2-vs-M1 primary proper-score result;
- complementarity: unavailable;
- Q2/Q3 blend: unavailable.

Do not widen support, reconstruct a substitute distribution, rerun a new Q2 version, or fill missing cells in Phase 3.

### Q3

`ATS-Q3-DIRECT-CPL-HURDLE-V1` is a valid negative incremental result versus Q3-M2.

- accepted OOF rows: 1,087;
- Q3 − Q3-M2 multinomial CPL log loss: `+0.0013157418572419255`;
- Stage-D paired 95% CI: `[-0.0015590942193462521, +0.004336647782633088]`;
- bootstrap probability Q3 better: `0.1842`;
- Q3 − Q3-M2 non-push Brier: `+0.0006716459171549338`;
- Brier 95% CI: `[-0.0007977772384239724, +0.002212922097716785]`;
- simple non-push hit rates: Q3-M2 `52.8355%`, Q3 `52.1739%`.

No Q3 rescue is authorized.

## Stage-D authority

Accepted final synthesis:

- branch `research/ats-nextgen-phase2-stage-d-accepted-artifacts`;
- PR #564;
- exact accepted evidence head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588`;
- artifact `10783982962`;
- artifact digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`.

The Stage-D uncertainty package used immutable accepted upstream artifacts, not candidate regeneration.

## Phase-3 task

Phase 3 is **scientific synthesis and classification**, not another historical model-search phase.

For each frozen architecture, assign exactly one program status allowed by the Master Plan:

- `REJECTED`;
- `INCONCLUSIVE`;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.

The classification must be justified from the already-frozen Phase-2 evidence, preregistered success criteria, uncertainty, calibration evidence, structural validity, and evidence-boundary limitations.

Phase 3 may preserve an architecture as scientifically interesting while still classifying it `INCONCLUSIVE` or `REJECTED`; it may not change a Phase-2 metric, comparator, feature set, learner, support, hyperparameter grid, slice, threshold, or candidate definition to improve the classification.

## Critical interpretation rule

A 95% bootstrap interval crossing zero is uncertainty about the magnitude/sign of the tiny incremental effect; it is **not** evidence that the candidate passed a preregistered incremental test. Conversely, a negative Phase-2 point result does not by itself prove a large harmful effect. Phase 3 must distinguish lack of demonstrated improvement from evidence of material inferiority.

Q2's absence of valid OOF evidence is a structural-invalidity state, not statistical uncertainty. Do not convert it into a Q2 performance estimate.

## Phase-3 prohibitions

Do not:

- refit Q1/Q2/Q3;
- generate new 2022–2025 candidate predictions;
- inspect completed-2026 outcomes;
- add candidates, features, distributions, learners, calibration layers, thresholds, or blend weights;
- widen Q2 support or version a Q2 rescue;
- use ATS hit rate, ROI, selective subsets, or favorable slices to override the proper-score evidence;
- reconstruct Q2 complementarity or the Q2/Q3 blend;
- modify production F-ST or Sunday Signal numerical forecasting behavior;
- promote anything to production.

## Required Phase-3 outputs

At minimum, Phase 3 must produce:

1. an immutable opening receipt bound to the verified Phase-2 closeout merge;
2. a candidate-by-candidate evidence table covering structural validity, primary incremental metric, uncertainty, calibration/supporting diagnostics, and evidence limitations;
3. explicit `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` classifications with rule-based rationales;
4. a machine-readable Phase-3 registry;
5. a final Phase-3 receipt and updated `PHASE_STATUS.md` / `CURRENT_STATE_AND_NEXT_STEPS.md`;
6. if and only if any candidate is `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`, a frozen prospective-shadow specification that remains outcome-blind and does not begin Phase 4 without explicit user authorization.

## Evidence boundary

2022–2025 remains development/non-pristine evidence. Completed-2026 outcomes remain firewalled. Even a Phase-3 eligibility classification can authorize at most **prospective shadow evaluation**, never direct production promotion.

## Start condition

Do not begin Phase 3 from this working branch head. First:

1. validate the final Phase-2 closeout head;
2. merge PR #564;
3. verify the merge is present on current `main`;
4. create the Phase-3 branch from that exact verified merge.
