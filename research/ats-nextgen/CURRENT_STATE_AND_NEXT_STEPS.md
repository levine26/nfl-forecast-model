# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**. PR #556 merged the exact-head validated ATS research/preregistration package at `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`.

Phase 2 is now **IN PROGRESS — OPENING GATE COMPLETE** on `research/ats-nextgen-phase2` / PR #559. The pre-fit opening gate has been implemented and exercised against the real 2015–2025 historical data path. Q1/Q2/Q3 remain untrained and no candidate-specific historical performance has been generated. Production remains `F-ST-01-FROZEN-2026` and Sunday Signal numerical forecasting is unchanged.

The dedicated opening workflow passed on exact pre-receipt implementation head `961e486ee9747c69a4420373153adac5caa6d437`:

- workflow run `35916159139` (#4): SUCCESS;
- 2,895 historical gate rows, all ATS eligible;
- 73 whole-line pushes;
- 0 completed-2026 outcomes;
- canonical game-keyed gate SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- artifact ID `10774524253`, SHA-256 `71ffe60cb0e472bd311ead8eabb961afbca75a41f9f7eb04fb310a78800f4511`.

The opening boundary is frozen in `PHASE2_OPENING_RECEIPT.md` and `phase2_opening_registry.json`. The receipt/status package must pass exact-head CI and merge before Q1 fitting is authorized.

## Source-sign contract resolved before results

The Phase-2 audit verified that nflverse `spread_line` is positive when the home team is favored, while the frozen sportsbook home-spread notation uses a negative value for a home favorite. Therefore:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `R = (home_score-away_score) + home_spread`.

This was corrected before any candidate fitting or performance generation and conforms the implementation to the Phase-1 scientific contract.

## Frozen design summary

**Q1** — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`: estimates `R=M+L` at τ={10/21,1/2,11/21} with L1-regularized linear quantile regression.

**Q2** — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`: produces an integer PMF on [-75,75], centered on the quoted market plus chronology-clean Q1 median residual, with bounded generalized-normal/Gaussian/Student-t/empirical comparisons, fixed conditional-scale terms and training-only key-number excess at |margin|={3,6,7,10,14}.

**Q3** — `ATS-Q3-DIRECT-CPL-HURDLE-V1`: two-part L2-logistic hurdle estimating push on whole-number lines and conditional cover on non-push rows, with half-point push probability structurally zero.

A Q2/Q3 blend is authorized only on `w_Q2={0,.25,.50,.75,1}` selected by inner chronology-clean multinomial log loss.

Historical 2022–2025 evidence is development/non-pristine. Completed 2026 outcomes remain prohibited from candidate design, fitting, tuning, selection, rescue, and historical survival decisions.

## Exact next actions

1. validate the complete opening receipt/registry/status package on its exact PR head;
2. merge PR #559 only if the opening gate, research firewall, research validation, and full repository checks are green;
3. verify merged `main` and record the opening merge identity;
4. only then open Stage A and implement/execute Q1 exactly from `Q1_QUANTILE_PREREGISTRATION.md`;
5. generate chronology-clean 2022–2025 Q1 outer OOF only after all Q1 implementation tests pass;
6. do not redesign Q1 after viewing its outer results;
7. do not begin Q2 until the frozen Q1 OOF interface is complete.

## Active firewalls

- no completed-2026 outcome use;
- no random K-fold;
- no historical market-horizon relabeling;
- no global/full-sample preprocessing that leaks target information;
- no player-state/weather/news/juice/book-dispersion expansion in V1;
- no post-result rescue learner, quantile, key number, threshold, calibration, or blend grid;
- no production F-ST/Sunday Signal forecasting changes.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
