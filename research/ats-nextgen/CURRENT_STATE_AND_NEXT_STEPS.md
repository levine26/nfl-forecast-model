# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**.

Phase 2 is **IN PROGRESS — STAGE A Q1 COMPLETE (NEGATIVE); STAGE B Q2 COMPLETE (STRUCTURALLY INVALID); STAGE C Q3 COMPLETE (NEGATIVE); STAGE D NEXT**.

Production remains `F-ST-01-FROZEN-2026`. No completed-2026 outcome has been used by the ATS Next-Generation historical candidate program.

## Stage A — Q1

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` is a valid negative incremental result versus M2 and is closed without rescue.

Accepted evidence:

- PR #560 merge/base `a2581a62e3797a6ac466d614326bc72b7d5a1c57`;
- workflow `35920622523`;
- artifact ID `10776898518`;
- 1,087 chronology-clean 2022–2025 outer OOF rows;
- OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 minus M2 aggregate frozen-quantile pinball `+0.000131` (worse).

## Stage B — Q2

`ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` is closed as **structurally invalid under its frozen support/truncation contract**.

The exact pre-result contract required support `[-75,+75]`, a material folded endpoint-mass threshold `1e-3`, and fail-closed behavior rather than widening support after historical inspection. Workflow `35927280982` passed its contract job and then stopped before a complete OOF artifact when a frozen generalized-normal state produced maximum endpoint mass `0.0033487075822347966`.

No valid Q2 OOF or accepted Q2-vs-M1 proper-score comparison exists. No Q2 rescue is authorized.

Stage-B closeout merged through PR #561 at `16859845573c3344ed82ae0b9bd27fa8b891eee4`.

## Stage C — Q3

`ATS-Q3-DIRECT-CPL-HURDLE-V1` is complete and is a **valid negative incremental result versus Q3-M2**.

The full scientific surface was frozen before results at `d9dbfe24af7fd19f5b22e76fd5f57dd83c606a60`; historical execution was authorized only after exact blob verification on head `891d921c24bc045dd58de3b2dd05871f12d09183`.

Accepted execution:

- branch `research/ats-nextgen-phase2-q3`;
- PR #562;
- workflow `35931071604`: **SUCCESS**;
- contract job `107417390267`: **SUCCESS**;
- historical job `107418004469`: **SUCCESS**;
- artifact ID `10781521222`;
- artifact digest `sha256:6062472dce30fddfcc6ad16d1d5c29203491f6e77d893aa673cc20bbb29a1bfa`;
- 1,087 chronology-clean exact-row OOF games across 2022–2025;
- Q3 OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`.

Primary proper-score result:

- Q3-M2 multinomial CPL log loss `0.7716887205239867`;
- Q3 multinomial CPL log loss `0.7730044623812287`;
- Q3 minus Q3-M2 `+0.0013157418572419255` — worse.

Supporting diagnostics:

- Q3-M2 non-push cover Brier `0.24979992069239074`;
- Q3 non-push cover Brier `0.2504715666095457` — worse;
- Q3-M2 cover calibration slope `0.8130523437112027`;
- Q3 cover calibration slope `0.27094382668690847`;
- season primary deltas: 2022 `+0.00011298`, 2023 `+0.00334784`, 2024 `-0.00130926`, 2025 `+0.00310698`;
- Q3 worse in 3 of 4 seasons and 10 of 14 frozen reporting slices.

The push head is shared between Q3 and Q3-M2; both arms therefore have mean predicted push `0.023992664002116082` versus empirical `0.02667893284268629`. The failed incremental contribution comes from adding compact football state to the conditional-cover head.

No post-hoc calibration, class weighting, learner replacement, C-grid change, feature change, threshold search, or ATS/ROI rescue is authorized.

The immutable result is recorded in:

- `PHASE2_Q3_RESULT_RECEIPT.md`;
- `phase2_q3_result_registry.json`.

## Exact next actions

1. switch the Stage-C Q3 workflow to closeout-only mode so the accepted historical experiment is not rerun after interpretation;
2. require the closeout workflow to re-run frozen Q3 contract tests and verify the immutable Q3 result registry/artifact identities;
3. include Q3 model/reporting contract tests in the repository-wide research-validation foundation;
4. validate the exact final Stage-C head with the research firewall, Phase-2 opening gate, frozen Q1 reproducibility, Q2 closeout, Q3 closeout, research validation, and full repository validation;
5. update PR #562 to the preserved negative result and merge only after those exact-head gates are green;
6. verify the resulting Stage-C merge is current `main`;
7. create Stage D from that exact merge;
8. in Stage D, use accepted evidence only and run the final paired season+week block-bootstrap uncertainty analysis with at least 10,000 resamples where defined;
9. preserve Q2 complementarity/Q2-Q3 blend as **unavailable** because no valid Q2 OOF exists—do not reconstruct or substitute Q2;
10. produce the final Phase-2 evidence synthesis and Phase-3 handoff without opening any new candidate family.

## Active firewalls

- no completed-2026 outcome use;
- no random K-fold;
- no historical market-horizon relabeling;
- no full-sample preprocessing leakage;
- no Q1 rescue;
- no Q2 support/family/grid/key/scale/smoothing rescue;
- no Q3 learner/feature/C-grid/class-weight/calibration/threshold/slice rescue;
- no repeat Q3 historical execution after the accepted result;
- no substitute Q2 distribution or blend;
- no production F-ST/Sunday Signal numerical forecasting changes.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
