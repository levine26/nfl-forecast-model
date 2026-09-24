# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**.

Phase 2 is **COMPLETE — CONTROLLED IMPLEMENTATION & HISTORICAL DEVELOPMENT CLOSED**.

Production remains `F-ST-01-FROZEN-2026`. No completed-2026 outcome has been used by the ATS Next-Generation historical candidate program.

The final Phase-2 historical-development state is:

- Q1 `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`: **valid negative incremental result vs M2**;
- Q2 `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`: **structurally invalid under the frozen V1 support/truncation contract**; no valid Q2 OOF/performance artifact exists;
- Q3 `ATS-Q3-DIRECT-CPL-HURDLE-V1`: **valid negative incremental result vs Q3-M2**;
- Q2 complementarity and Q2/Q3 blend: **unavailable**, because Q2 has no valid accepted OOF distribution;
- Stage D final paired uncertainty: **complete** from immutable accepted Q1/Q3 artifacts; no candidate was repaired, retuned, rescued, or reselected.

Phase 3 — Scientific Synthesis, Candidate Selection & Freeze — is the next program phase. Phase 3 has **not** yet performed the formal `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` classification.

## Phase-2 opening gate

- PR #559 merge `f43e17ba783e3e389969cd1649889b37bd91afe9`;
- 2,895 historical rows / 2,895 ATS eligible / 73 pushes;
- completed-2026 outcomes: `0`;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- historical market evidence class `historical_closing_late_benchmark_exact_horizon_opaque`.

## Stage A — Q1

Accepted evidence:

- PR #560 merge/base `a2581a62e3797a6ac466d614326bc72b7d5a1c57`;
- workflow `35920622523`;
- artifact ID `10776898518`;
- 1,087 chronology-clean 2022–2025 OOF rows;
- OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 minus M2 mean-three-quantile pinball `+0.0001307887665715768` — worse.

Stage-D paired uncertainty:

- 95% season+week block-bootstrap CI `[-0.002378435765685505, +0.002555544033066125]`;
- bootstrap probability Q1 better `0.4554`.

The interval crosses zero but supplies no basis to overturn the frozen adverse point result or rescue Q1.

## Stage B — Q2

Stage-B closeout merged through PR #561 at `16859845573c3344ed82ae0b9bd27fa8b891eee4`.

The frozen contract required discrete support `[-75,+75]`, material folded endpoint-mass threshold `0.001`, and fail-closed behavior. Historical execution stopped before complete OOF scoring when maximum endpoint mass reached `0.0033487075822347966`.

No valid Q2 OOF, accepted Q2 proper-score result, complementarity test, or Q2/Q3 blend exists. No Q2 support/family/grid/key/scale/smoothing rescue is authorized.

## Stage C — Q3

Accepted evidence:

- PR #562 merge `539081c59e62a5d4dbc0a8f849d8a332424ea06e`;
- workflow `35931071604`;
- artifact ID `10781521222`;
- artifact digest `sha256:6062472dce30fddfcc6ad16d1d5c29203491f6e77d893aa673cc20bbb29a1bfa`;
- 1,087 chronology-clean 2022–2025 OOF rows;
- OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- Q3 minus Q3-M2 multinomial CPL log-loss `+0.0013157418572419255` — worse;
- Q3 minus Q3-M2 non-push conditional-cover Brier `+0.0006716459171549338` — worse.

Stage-D paired uncertainty:

- CPL log-loss 95% CI `[-0.0015590942193462521, +0.004336647782633088]`, probability Q3 better `0.1842`;
- Brier 95% CI `[-0.0007977772384239724, +0.002212922097716785]`, probability Q3 better `0.1851`.

Simple hit-rate diagnostic on non-push games:

- Q3-M2 `559/1058 = 52.8355%`;
- Q3 `552/1058 = 52.1739%`.

No post-hoc calibration, class weighting, learner replacement, C-grid change, feature change, threshold search, slice mining, or ATS/ROI rescue is authorized.

## Stage D — final evidence synthesis

Authoritative branch/PR: `research/ats-nextgen-phase2-stage-d-accepted-artifacts` / PR #564.

Accepted execution:

- exact result head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588`: **SUCCESS**;
- contract job `107441314608`: **SUCCESS**;
- synthesis job `107441551438`: **SUCCESS**;
- artifact ID `10783982962`;
- artifact digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`.

Stage D downloaded the immutable accepted Q1/Q3 artifacts directly, verified their complete registered SHA maps, ran exactly 10,000 paired `(season, week)` bootstrap draws with seed 26, proved protected production surfaces unchanged, and uploaded the final evidence package.

Result records:

- `PHASE2_STAGE_D_RESULT_RECEIPT.md`;
- `phase2_stage_d_result_registry.json`.

## Exact next actions

1. validate the final Phase-2 closeout head after the Stage-D result/state records with the ATS Stage-D closeout contract, research firewall, opening gate, Q1/Q2/Q3 closeouts, research validation, full repository validation, and normal repository checks;
2. convert the Stage-D workflow to closeout-only verification so the accepted synthesis is not rerun on documentation commits;
3. update PR #564 to the immutable final Phase-2 evidence state;
4. merge PR #564 only after the exact closeout head is green;
5. verify the Phase-2 closeout merge is present on current `main`;
6. create Phase 3 only from that verified merge;
7. Phase 3 may classify the frozen candidates `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` under the already-frozen evidence rules, but may not rescue or redesign them;
8. Phase 4 remains conditional and requires both Phase-3 eligibility and explicit user authorization.

## Active firewalls

- no completed-2026 outcome use;
- no random K-fold;
- no historical market-horizon relabeling;
- no full-sample preprocessing leakage;
- no Q1 rescue;
- no Q2 reconstruction or rescue;
- no Q3 rescue;
- no substitute Q2 distribution or Q2/Q3 blend;
- no new candidate family in Phase 2;
- no production F-ST/Sunday Signal numerical forecasting changes.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
