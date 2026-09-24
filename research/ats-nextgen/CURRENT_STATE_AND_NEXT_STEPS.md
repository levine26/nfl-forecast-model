# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**.

Phase 2 is **COMPLETE — SCIENTIFIC CLOSEOUT MERGED**.

The provenance-correct Phase-2 scientific closeout merged through PR #566 at `89f8b4fa48e22554029392b303225e4665b4b673` after all exact-head gates passed on corrective head `0ceae72f2643cc9b10a6cf35181576d52bb2fdf7`.

Production remains `F-ST-01-FROZEN-2026`. Completed-2026 outcomes used by the ATS Next-Generation historical candidate program: `0`.

The frozen final Phase-2 state is:

- Q1 `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`: **valid negative incremental result versus M2**;
- Q2 `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`: **structurally invalid under the frozen V1 support/truncation contract**; no valid Q2 OOF/performance artifact exists;
- Q3 `ATS-Q3-DIRECT-CPL-HURDLE-V1`: **valid negative incremental result versus Q3-M2**;
- Q2 complementarity and Q2/Q3 blend: **unavailable**;
- Stage-D paired uncertainty: **complete** from immutable accepted Q1/Q3 artifacts;
- candidate repair, retuning, rescue or reselection: **none**.

Phase 3 — Scientific Synthesis, Candidate Selection & Freeze — is next. It has **not** yet assigned the formal `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` statuses.

## Authoritative Phase-2 identities

### Opening gate

- PR #559 merge `f43e17ba783e3e389969cd1649889b37bd91afe9`;
- 2,895 historical ATS-eligible rows, 73 pushes;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`.

### Q1

- PR #560 merge/base `a2581a62e3797a6ac466d614326bc72b7d5a1c57`;
- accepted workflow `35920622523`, artifact `10776898518`;
- OOF SHA `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- 1,087 OOF rows;
- Q1 − M2 pinball delta `+0.0001307887665715768`;
- Stage-D 95% CI `[-0.002378435765685505, +0.002555544033066125]`;
- P(Q1 better) `0.4554`.

### Q2

- PR #561 merge `16859845573c3344ed82ae0b9bd27fa8b891eee4`;
- frozen support `[-75,+75]`;
- material endpoint threshold `0.001`;
- observed maximum folded endpoint mass `0.0033487075822347966`;
- failed closed before valid complete OOF scoring.

### Q3

- PR #562 merge `539081c59e62a5d4dbc0a8f849d8a332424ea06e`;
- accepted workflow `35931071604`, artifact `10781521222`;
- OOF SHA `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- 1,087 OOF rows;
- Q3 − Q3-M2 CPL log-loss delta `+0.0013157418572419255`, 95% CI `[-0.0015590942193462521, +0.004336647782633088]`, P(Q3 better) `0.1842`;
- non-push Brier delta `+0.0006716459171549338`, 95% CI `[-0.0007977772384239724, +0.002212922097716785]`, P(Q3 better) `0.1851`.

### Stage D

Scientific origin remains PR #564 / branch `research/ats-nextgen-phase2-stage-d-accepted-artifacts`:

- accepted head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588` — SUCCESS;
- artifact `10783982962`;
- digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`;
- 10,000 paired `(season, week)` bootstrap draws, seed 26, 72 blocks.

The final merge vehicle is corrective PR #566 / merge `89f8b4fa48e22554029392b303225e4665b4b673`. PR #563's regeneration-based evidence-loading path is superseded for provenance; PR #564 was closed unmerged only as a merge vehicle after divergence; PR #565 was closed unmerged and is not authoritative.

## Exact next actions

1. merge this **governance-only** closeout after confirming its diff contains only `FINAL_PHASE2_RECEIPT.md`, `PHASE_STATUS.md`, `CURRENT_STATE_AND_NEXT_STEPS.md`, and `PHASE3_HANDOFF.md`;
2. verify the governance merge on current `main` and record that exact `main` SHA in the immutable Phase-3 opening receipt;
3. create the Phase-3 branch from that exact verified `main` head;
4. perform Phase-3 scientific synthesis/classification only—no refitting, rerunning, rescue, new candidate, new threshold, new slice, Q2 reconstruction, or completed-2026 outcome inspection;
5. assign each frozen architecture exactly one allowed status: `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`;
6. preserve the Evaluation Protocol rule that prospective-shadow eligibility requires improvement on the relevant primary proper/quantile market-null comparison;
7. Phase 4 remains conditional on Phase-3 eligibility **and** explicit user authorization.

## Active firewalls

- no completed-2026 outcome use;
- no historical market-horizon relabeling;
- no random K-fold/full-sample preprocessing leakage;
- no Q1 rescue;
- no Q2 reconstruction/support widening/rescue;
- no Q3 rescue/calibration replacement;
- no substitute Q2 distribution or Q2/Q3 blend;
- no ATS hit-rate/ROI/slice override of failed primary proper-score evidence;
- no production F-ST/Sunday Signal numerical forecasting changes.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
