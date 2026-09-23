# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**. PR #556 merged the exact-head validated ATS research/preregistration package at `80f84dc8282205c48dbfd8ca700f481a91ad25538`.

Phase 2 is **IN PROGRESS — STAGE A Q1 COMPLETE (NEGATIVE); STAGE B Q2 COMPLETE (STRUCTURALLY INVALID); STAGE C Q3 NEXT**.

The Phase-2 opening gate is complete and merged. PR #559 merged at `f43e17ba783e3e389969cd1649889b37bd91afe9` after exact-head validation.

Stage A Q1 is complete and merged through PR #560 at `a2581a62e3797a6ac466d614326bc72b7d5a1c57`. Its accepted Q1 OOF identity is SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365` across 1,087 chronology-clean 2022–2025 outer OOF games. Q1 V1 is a valid negative incremental result versus M2 and may not be rescued.

Stage B Q2 is on `research/ats-nextgen-phase2-q2` / PR #561. The controlling pre-result head was `8503dbf250c97b0520cec30f985e9981fce83767`.

## Stage-B Q2 scientific result

Q2 is `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`.

The final pre-result contract froze:

- support exactly `[-75,+75]`;
- material folded endpoint mass threshold `1e-3`;
- fail-closed behavior rather than widening support after historical inspection;
- the bounded 12-arm M1/Q2 experiment surface;
- prior-only rolling-origin selection;
- no completed-2026 outcomes;
- no production mutation.

On exact head `8503dbf250c97b0520cec30f985e9981fce83767`, all repository/governance gates outside the Q2 historical job succeeded:

- research firewall `35927280868`: **SUCCESS**;
- Phase-2 opening gate `35927280994`: **SUCCESS**;
- Q1 Stage-A reproducibility `35927280912`: **SUCCESS**;
- Daily NFL model refresh / full repository validation `35927281014`: **SUCCESS**;
- research validation `35927280856`: **SUCCESS**.

Q2 workflow `35927280982` behaved correctly:

- pre-result contract job `107405457674`: **SUCCESS**;
- chronology-clean historical job `107405820497`: **FAILURE** before a complete OOF artifact could be generated/uploaded.

The exact failure was the preregistered endpoint-mass guard:

- generalized normal;
- `beta=1.0`;
- `no_key_conditional_scale` ablation;
- no key penalty;
- observed maximum folded endpoint mass `0.0033487075822347966`;
- frozen threshold `0.001`.

Therefore Q2 V1 is **structurally invalid under its own frozen support/truncation contract**.

This is not a proper-score loss to M1: no complete Stage-B OOF artifact exists, no accepted primary Q2-vs-M1 CRPS comparison exists, and no candidate-performance result is being inferred from the aborted run.

The invalidation is frozen in:

- `PHASE2_Q2_RESULT_RECEIPT.md`;
- `phase2_q2_result_registry.json`.

No Q2 V1 rescue is authorized. In particular, do not widen support, relax the endpoint threshold, drop the failing arm, change family/shape grids, modify scale/key machinery, or inspect target performance to design a replacement inside Stage B.

## Exact next actions

1. validate the Stage-B result/status head on PR #561;
2. require research firewall, Phase-2 opening gate, frozen Q1 reproducibility, research validation, full repository validation, and Q2 contract tests to be green on the exact final Stage-B head;
3. merge PR #561 only after that result record is stable and validated;
4. verify the Stage-B merge is current `main`;
5. create Stage C from that exact merged SHA;
6. read `Q3_COVER_PUSH_LOSS_PREREGISTRATION.md` plus the evaluation/chronology/red-team contracts before implementation;
7. implement `ATS-Q3-DIRECT-CPL-HURDLE-V1` exactly as frozen;
8. before any Q3 historical score exists, prove half-point structural zero push and three-outcome cover/push/loss normalization, freeze any open engineering details, and write a pre-result Stage-C receipt;
9. preserve the completed-2026 outcome firewall and keep production F-ST/Sunday Signal forecasting unchanged;
10. do not open Stage D until Q3 Stage C is complete.

## Active firewalls

- no completed-2026 outcome use;
- no random K-fold;
- no historical market-horizon relabeling;
- no global/full-sample preprocessing that leaks target information;
- no Q1 post-result rescue;
- no Q2 post-result support, family, grid, key, scale, smoothing, threshold, slice, or calibration rescue;
- no Q3 historical execution before its exact-head tests-before-results contract passes;
- no production F-ST/Sunday Signal forecasting changes.

> 2022–2025 is chronology-clean development evidence and is not pristine independent confirmation because those seasons have informed prior LevLine research.
