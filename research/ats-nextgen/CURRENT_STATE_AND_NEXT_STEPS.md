# ATS Next-Generation — Current State & Next Steps

## Current state

Phase 1 is **COMPLETE**. PR #556 merged the exact-head validated ATS research/preregistration package at `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`.

Phase 2 is **IN PROGRESS — STAGE A Q1 IMPLEMENTATION FROZEN; HISTORICAL EXECUTION PENDING CONTRACT CI**.

The opening gate is complete and merged. PR #559 passed all exact-head checks at `446b8f963c4125bad972f79a793035d0a9a777e0` and merged to `main` at `f43e17ba783e3e389969cd1649889b37bd91afe9`. That merge was verified as current `main` before Stage A was created.

Stage A now lives on `research/ats-nextgen-phase2-q1`, created from that exact opening merge. Q1 implementation is frozen in `PHASE2_Q1_IMPLEMENTATION_RECEIPT.md` and `phase2_q1_registry.json`. At the receipt boundary, **Q1/Q2/Q3 remain untrained and no new ATS NextGen candidate-specific historical performance has been generated or inspected**. Production remains `F-ST-01-FROZEN-2026` and Sunday Signal numerical forecasting is unchanged.

## Opening-gate evidence

The frozen 2015–2025 Phase-2 input boundary remains:

- 2,895 historical gate rows, all ATS eligible;
- 73 whole-line pushes;
- 0 completed-2026 outcomes;
- canonical game-keyed gate SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- historical market evidence class `historical_closing_late_benchmark_exact_horizon_opaque`.

The exact-head opening checks used to authorize Stage A were all successful:

- research firewall `35917266533` (#1969);
- ATS opening gate `35917266606` (#8);
- research validation `35917266598` (#1551), including gate job `107376225489`;
- Daily NFL model refresh/full pytest and regenerated-output validation `35917266639` (#1104).

## Stage-A Q1 boundary

Q1 is `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` and remains exactly the frozen Phase-1 design:

- residual target `R=M+L`;
- quantiles `{10/21,1/2,11/21}`;
- `QuantileRegressor`, L1 alpha grid `{0.001,0.01,0.1,1.0}`;
- alpha selected separately per quantile by prior-only inner rolling-origin pinball loss;
- fold-local medians and scaling only;
- fixed market-total interactions and fixed missingness indicators;
- M0 raw-line reference, M2 market-only learner, Q1 market+compact football state;
- no post-hoc quantile crossing repair;
- only the preregistered key-number/favorite-size/market-total slices.

The dedicated workflow `.github/workflows/research_ats_nextgen_q1.yml` enforces **contract tests before historical execution**. The historical job has an explicit `needs: contract` dependency and the Q1 runner independently refuses to fit unless the regenerated gate matches the frozen opening hash.

## Source-sign contract

The verified source mapping remains:

- nflverse `spread_line` is positive when the home team is favored;
- `market_home_margin_center = spread_line`;
- canonical sportsbook `home_spread = -spread_line`;
- `R = (home_score-away_score) + home_spread`.

## Exact next actions

1. open the Stage-A Q1 PR from `research/ats-nextgen-phase2-q1` to `main` with the implementation receipt already frozen;
2. require the dedicated Q1 contract job to pass before accepting any historical Q1 output;
3. if the contract passes, allow the workflow to generate the preregistered chronology-clean 2022–2025 Q1/M2/M0 outer OOF artifact;
4. inspect and preserve all Q1 results, including negative results, selected alphas, coverage, crossings and fixed slices;
5. do **not** redesign or rescue Q1 after viewing those results;
6. freeze the Q1 OOF interface and Stage-A result receipt before beginning Q2.

## Active firewalls

- no completed-2026 outcome use;
- no random K-fold;
- no historical market-horizon relabeling;
- no global/full-sample preprocessing that leaks target information;
- no player-state/weather/news/juice/book-dispersion expansion in V1;
- no post-result rescue learner, quantile, key number, threshold, calibration, slice or blend grid;
- no production F-ST/Sunday Signal forecasting changes.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
