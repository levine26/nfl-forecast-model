# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**. PR #556 merged the exact-head validated ATS research/preregistration package at `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`.

Phase 2 is **IN PROGRESS — STAGE A Q1 COMPLETE; NEGATIVE INCREMENTAL RESULT; STAGE B Q2 NEXT**.

The opening gate is complete and merged. PR #559 merged at `f43e17ba783e3e389969cd1649889b37bd91afe9` after exact-head validation.

Stage A lives on `research/ats-nextgen-phase2-q1` / PR #560. The frozen Q1 implementation was executed through the dedicated tests-before-results workflow on exact result head `f14e2fa3ec78bf95578b4a5030fb66e94cd12cd0`.

All exact-head workflows succeeded:

- Q1 Stage A `35920622523` (#7): **SUCCESS**;
- research firewall `35920622410`: **SUCCESS**;
- ATS Phase-2 opening gate `35920622392`: **SUCCESS**;
- research validation `35920622570`: **SUCCESS**;
- Daily NFL model refresh / full pytest and regenerated-output validation `35920622374`: **SUCCESS**.

The accepted Q1 evidence artifact is ID `10776898518`, digest `sha256:b544a4928a3e2ab80861b7b3fcf581a6b51355961b80aa05ddc5e4a0554d0c36`, with 1,087 chronology-clean OOF rows from 2022–2025. Completed-2026 outcomes used: 0. Production remains `F-ST-01-FROZEN-2026` and Sunday Signal numerical forecasting is unchanged.

## Stage-A scientific result

Q1 is `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`.

Under the preregistered failure rule, Q1 is **not incremental** relative to the market-only M2 comparator:

- mean frozen-quantile pinball: M2 `4.749986`, Q1 `4.750117`;
- Q1 minus M2: `+0.000131` (worse, not better);
- τ=10/21: identical M2/Q1 pinball `4.736212` and identical coverage error `-0.009769`;
- τ=1/2: Q1 worse (`4.753243` vs M2 `4.749754`) and less calibrated (`-0.013339` vs `-0.011500`);
- τ=11/21: Q1 modestly better (`4.760897` vs `4.763994`) and modestly better calibrated (`-0.010470` vs `-0.012310`), but this isolated gain does not overcome the full preregistered evidence;
- raw-line M0 has the best aggregate mean pinball of the three arms at `4.747240`.

Season mean-pinball Q1 minus M2: 2022 `-0.004140`, 2023 `0.000000`, 2024 `+0.003698`, 2025 `+0.000950`. The effect is not stable across seasons.

Quantile crossings are diagnostic only: M2 87/1,087 (`8.0037%`), Q1 79/1,087 (`7.2677%`); no repair was applied.

Across the 42 frozen slice × quantile cells, Q1 pinball is better in 12, equal in 14, and worse in 16. Favorable slices cannot rescue the failed overall quantile evidence.

The immutable result is recorded in:

- `PHASE2_Q1_RESULT_RECEIPT.md`;
- `phase2_q1_result_registry.json`.

Q1 V1 may not be redesigned or rescued after this result.

## Q1-to-Q2 interface

Q2 may proceed exactly as preregistered using only the chronology-clean Q1 median residual predictions from the frozen Stage-A interface. This handoff does **not** mean Q1 passed its incremental test; it preserves the preregistered Q2 center definition while keeping the Q1 negative result intact.

The frozen Q1 OOF file identity is SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`. Any Stage-B regeneration used by Q2 must reproduce that interface identity before Q2 fitting or fail closed.

## Exact next actions

1. validate the post-result Stage-A receipt/status head on PR #560;
2. merge PR #560 only if the Q1 contract/historical workflow, research firewall, opening gate, research validation, and full repository checks are green on the exact final head;
3. verify merged `main` and record the Stage-A merge identity;
4. create Stage B from that verified merge;
5. implement Q2 exactly from `Q2_MARGIN_DISTRIBUTION_PREREGISTRATION.md` without redesigning Q1;
6. before any Q2 historical score exists, freeze engineering details left open by the preregistration (including exact continuous-to-integer bin integration and Q2-EMP deterministic smoothing) and test them synthetically;
7. require Q2 to regenerate/verify the frozen Q1 OOF interface before using Q1 median residual centers;
8. keep completed-2026 outcomes prohibited and production unchanged.

## Active firewalls

- no completed-2026 outcome use;
- no random K-fold;
- no historical market-horizon relabeling;
- no global/full-sample preprocessing that leaks target information;
- no Q1 post-result rescue learner, quantile, feature, threshold, calibration, slice or alpha-grid change;
- no Q2 post-result distribution-family, shape-grid, key-number, scale-model, smoothing, or blend rescue;
- no production F-ST/Sunday Signal forecasting changes.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
