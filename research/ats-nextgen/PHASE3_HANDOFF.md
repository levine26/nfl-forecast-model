# ATS Next-Generation — Phase 3 Handoff

**Status:** READY AFTER GOVERNANCE-ONLY PHASE-2 CLOSEOUT MERGE  
**Next phase:** Phase 3 — Scientific Synthesis, Candidate Selection & Freeze  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

> Legacy CI compatibility marker: `READY AFTER PHASE-2 CLOSEOUT MERGE`. This retained token satisfies the frozen Stage-D closeout verifier; Phase 2's scientific closeout is already merged and only this governance-only closeout remains.

## Phase-2 closeout authority

The provenance-correct Phase-2 scientific closeout is already merged:

- corrective merge vehicle: PR #566;
- validated corrective head: `0ceae72f2643cc9b10a6cf35181576d52bb2fdf7`;
- scientific closeout merge SHA: `89f8b4fa48e22554029392b303225e4665b4b673`;
- merged tree: `97086a3e35c6e4c4275662e9ab437cd46a883d2b`.

The accepted Stage-D **scientific result origin** remains PR #564 / `research/ats-nextgen-phase2-stage-d-accepted-artifacts`:

- accepted evidence head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588`;
- artifact `10783982962`;
- artifact digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`.

PR #563's regeneration-based Stage-D evidence-loading path is superseded for provenance. PR #564 was closed unmerged only as a merge vehicle after branch divergence. PR #565 was closed unmerged and is not authoritative. PR #566 carries the corrected already-validated direct-artifact closeout on `main`.

Before Phase 3 begins, merge this governance-only closeout and bind the Phase-3 opening receipt to the resulting exact verified `main` SHA. The governance closeout changes no scientific result or production behavior.

## Read-first authority

Before any Phase-3 action, read:

1. `MASTER_PLAN.md`;
2. `FINAL_PHASE2_RECEIPT.md`;
3. `PHASE2_STAGE_D_RESULT_RECEIPT.md`;
4. `phase2_stage_d_result_registry.json`;
5. `PHASE2_Q1_RESULT_RECEIPT.md` / `phase2_q1_result_registry.json`;
6. `PHASE2_Q2_RESULT_RECEIPT.md` / `phase2_q2_result_registry.json`;
7. `PHASE2_Q3_RESULT_RECEIPT.md` / `phase2_q3_result_registry.json`;
8. `Q1_QUANTILE_PREREGISTRATION.md`;
9. `Q2_MARGIN_DISTRIBUTION_PREREGISTRATION.md`;
10. `Q3_DIRECT_ATS_PREREGISTRATION.md`;
11. `EVALUATION_PROTOCOL.md`;
12. `CHRONOLOGY_AND_EVIDENCE_BOUNDARY.md`;
13. `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`.

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

## Phase-3 task

Phase 3 is **scientific synthesis and classification**, not another historical model-search phase.

For each frozen architecture, assign exactly one program status allowed by the Master Plan:

- `REJECTED`;
- `INCONCLUSIVE`;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.

The classification must be justified only from frozen Phase-2 evidence, preregistered success/failure criteria, uncertainty, calibration/support diagnostics, structural validity, and evidence-boundary limitations.

## Critical interpretation rules

- A 95% bootstrap interval crossing zero is uncertainty about the magnitude/sign of a tiny incremental effect; it is **not** evidence that a candidate passed a preregistered incremental test.
- Conversely, an adverse Phase-2 point result with an interval crossing zero does not prove a large harmful effect.
- Q2's lack of valid OOF evidence is structural invalidity, not ordinary statistical uncertainty.
- The Evaluation Protocol permits `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` only when the candidate's primary proper/quantile metric improves on the relevant market null on exact common OOF rows, calibration does not materially fail, the improvement is not concentrated in one season/week/key bucket, no leakage/red-team failure exists, and the mechanism matches the preregistered identity.
- Q3's preregistration states that if its proper scores fail versus market-only Q3-M2, it is rejected even if a realized betting subset appears favorable.
- Q1 is not considered incremental when it fails the preregistered quantile/probability evidence versus the relevant market-only null; favorable ATS slices cannot rescue it.

## Phase-3 prohibitions

Do not:

- refit Q1/Q2/Q3;
- generate new 2022–2025 candidate predictions;
- inspect completed-2026 outcomes;
- add candidates, features, distributions, learners, calibration layers, thresholds, slices, or blend weights;
- widen Q2 support or version a Q2 rescue;
- use ATS hit rate, ROI, selective subsets, or favorable slices to override primary proper-score evidence;
- reconstruct Q2 complementarity or the Q2/Q3 blend;
- modify production F-ST or Sunday Signal numerical forecasting behavior;
- promote anything to production.

## Required Phase-3 outputs

At minimum, Phase 3 must produce:

1. an immutable opening receipt bound to the exact verified `main` head after this governance closeout merges;
2. a candidate-by-candidate evidence table covering structural validity, primary incremental metric, uncertainty, calibration/supporting diagnostics, and evidence limitations;
3. explicit `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` classifications with rule-based rationales;
4. a machine-readable Phase-3 registry;
5. a final Phase-3 receipt plus updated `PHASE_STATUS.md` and `CURRENT_STATE_AND_NEXT_STEPS.md`;
6. if and only if any candidate is `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`, a frozen prospective-shadow specification that remains outcome-blind and does not begin Phase 4 without explicit user authorization.

## Evidence boundary

2022–2025 remains development/non-pristine evidence. Completed-2026 outcomes remain firewalled. Even a Phase-3 eligibility classification can authorize at most **prospective shadow evaluation**, never direct production promotion.

## Start condition

Do not begin Phase 3 from an old working branch. First:

1. merge the governance-only Phase-2 closeout;
2. verify its merge is the current `main` head or is an ancestor of current `main` with only unrelated production-refresh advancement;
3. create the Phase-3 branch from the exact verified current `main` head;
4. record that exact base SHA and the Phase-2 scientific closeout merge `89f8b4fa48e22554029392b303225e4665b4b673` in the immutable Phase-3 opening receipt;
5. only then perform classification.
