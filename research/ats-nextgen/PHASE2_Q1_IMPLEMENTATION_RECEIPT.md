# ATS Next-Generation — Phase 2 Stage A / Q1 Pre-Result Implementation Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** A — Q1  
**Candidate:** `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`  
**Receipt status:** **IMPLEMENTATION FROZEN; HISTORICAL Q1 PERFORMANCE NOT YET GENERATED**  
**Stage-A branch:** `research/ats-nextgen-phase2-q1`  
**Stage-A base / verified opening merge:** `f43e17ba783e3e389969cd1649889b37bd91afe9`  
**Frozen pre-receipt implementation head:** `6e9ad2eec0f4bc121f12a2133a85088df4a00d97`  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes used:** 0

This receipt freezes the Q1 implementation boundary before the dedicated Stage-A workflow is allowed to generate any historical Q1 outer-OOF candidate performance.

## 1. Opening-gate integration is complete

PR #559 merged the Phase-2 opening gate only after exact-head validation. The merge is current verified `main` at:

`f43e17ba783e3e389969cd1649889b37bd91afe9`.

The validated PR head was:

`446b8f963c4125bad972f79a793035d0a9a777e0`.

Required exact-head checks were all successful:

- LevLine research firewall — run `35917266533` (#1969): **SUCCESS**;
- ATS NextGen Phase 2 opening gate — run `35917266606` (#8): **SUCCESS**;
- LevLine research validation — run `35917266598` (#1551): **SUCCESS**;
- Daily NFL model refresh / full pytest + PR regenerated-output validation — run `35917266639` (#1104): **SUCCESS**.

The research-validation gate job `107376225489` also completed successfully after every parallel validation lane succeeded.

## 2. Frozen historical input boundary

Q1 is permitted to consume only the Phase-2 gate identity frozen before candidate fitting:

- seasons requested: 2015–2025 only;
- outer target seasons: 2022, 2023, 2024, 2025;
- inner target floor: 2019;
- historical market evidence class: `historical_closing_late_benchmark_exact_horizon_opaque`;
- opening gate rows: 2,895;
- ATS-eligible rows: 2,895;
- whole-line pushes: 73;
- completed-2026 outcomes: 0;
- canonical game-keyed SHA-256: `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`.

The Q1 historical runner must regenerate the gate and **fail closed before fitting** if its canonical game-keyed SHA-256 does not equal that value.

## 3. Frozen Q1 learner

The Stage-A implementation exactly preserves the Phase-1 Q1 identity:

- learner: `sklearn.linear_model.QuantileRegressor`;
- environment: `scikit-learn==1.9.0`;
- quantiles exactly `{10/21, 1/2, 11/21}`;
- L1 alpha grid exactly `{0.001, 0.01, 0.1, 1.0}`;
- `fit_intercept=True`;
- solver: `highs`;
- no GAM, tree, boosting, neural, calibration or replacement learner;
- no post-result quantile repair.

Each quantile chooses alpha separately using pooled chronology-clean inner rolling-origin pinball loss. A numerical tie within `1e-12` is resolved in favor of the **largest alpha / strongest regularization**. This deterministic tie rule was fixed before any Q1 historical result existed.

## 4. Frozen preprocessing and features

Every fit derives preprocessing from its own training rows only.

Frozen preprocessing:

- training-fold median imputation for each optional numeric feature;
- a fixed missingness-indicator column for each optional market/football feature, even when a particular training fold has zero missing rows;
- training-fold-only standardization using `StandardScaler`;
- market-total centering by that training fold's market-total median;
- no target-season preprocessing information.

Frozen market features:

- sportsbook `home_spread=L`;
- market home-margin center `C=-L`;
- favorite size `|L|`;
- market total;
- no-vig home moneyline probability;
- optional-feature missingness indicators;
- `C × centered_total`;
- `|L| × centered_total`.

Frozen football features are the single chronology-safe shifted alpha-0.15 matchup-state differentials defined in `DATA_AND_PIT_INVENTORY.md`: pregame Elo, offense/defense EPA, pass, rush, success, neutral EPA and rest differential. No player-state, weather, news, side juice, line movement or book-dispersion feature is authorized in Q1 V1.

## 5. Frozen comparators and chronology

Stage A generates exactly:

- **M0:** residual quantiles fixed at zero / raw quoted-line reference;
- **M2:** identical quantile learner with market features only;
- **Q1:** market + compact football state.

For outer season `s`, training is 2015 through `s-1`. For each inner target `t`, training is 2015 through `t-1`. Random K-fold is prohibited. The implementation records the inner targets actually used in every tuning row; no random replacement fold exists.

## 6. Frozen Q1 reporting

Primary Q1 reporting is frozen before results to:

- pinball loss at each of the three quantiles;
- empirical quantile coverage and coverage error;
- overall and per-season evidence;
- secondary median/location error metrics;
- quantile-crossing diagnostic with **no post-hoc repair**;
- exact preregistered fixed slices only.

Key-number quoted-spread/favorite-size buckets:

- K3 `{2.5,3.0,3.5}`;
- K6 `{5.5,6.0,6.5}`;
- K7 `{6.5,7.0,7.5}`;
- K10 `{9.5,10.0,10.5}`;
- K14 `{13.5,14.0,14.5}`.

The 6.5 overlap between K6 and K7 is intentional and preserved.

Favorite-size buckets:

- `<3`;
- `3–<7`;
- `7–<10`;
- `10–<14`;
- `>=14`.

Market-total buckets:

- `<42`;
- `42–<45`;
- `45–<48`;
- `>=48`.

No new bucket may be created after Q1 results.

## 7. Tests-before-results execution gate

`.github/workflows/research_ats_nextgen_q1.yml` enforces the required dependency:

1. `Q1 pre-result contract` must pass the Phase-2 gate tests plus both Q1 contract/reporting test files;
2. only then may `Q1 chronology-clean 2022-2025 OOF` run via `needs: contract`;
3. the historical job rechecks the frozen opening gate hash before fitting;
4. protected production surfaces must remain unchanged;
5. Q1 evidence is uploaded as an immutable workflow artifact.

At the time this receipt is written, that PR workflow has **not** executed and no Q1 historical performance has been generated or inspected.

## 8. Frozen implementation identities

Frozen at pre-receipt head `6e9ad2eec0f4bc121f12a2133a85088df4a00d97`:

- Q1 model: `src/nfl_forecast/challenger_ats_nextgen_q1.py` — blob `bec3da17d91e01cc14a5752d57e605c80af9a991`;
- Q1 fixed-slice reporter: `src/nfl_forecast/challenger_ats_nextgen_q1_reporting.py` — blob `b05c536fae784872666e29dbca3a3e7568e679af`;
- Q1 model tests: `tests/test_challenger_ats_nextgen_q1.py` — blob `1d0013d345d8cf63abcfec9f0af65d7b9a908e0e`;
- Q1 reporting tests: `tests/test_challenger_ats_nextgen_q1_reporting.py` — blob `17f2dde853bfc32eb35bb0b6a8affef6590f11fa`;
- Q1 runner: `scripts/run_challenger_ats_nextgen_q1.py` — blob `e63f046ed5d7ae87645c5c8561e23a31719b3f0e`;
- dedicated Q1 workflow: `.github/workflows/research_ats_nextgen_q1.yml` — blob `92a45f8a3aab852affdacbe6b1f2eb934c4b38c8`;
- general research validation workflow: `.github/workflows/research_validation.yml` — blob `731c91e2265a89009d16690a167dcbb3c34422c3`.

Scientific specifications remain bound to the already-frozen Phase-1 files, including Q1 preregistration blob `aea060d340ba272a46e244ab4cf621f32f9f04f4` and the Phase-2 opening registry blob `ef64d745cffe7b2e876618e86a4cf8a57e58d875`.

## 9. Authorization boundary

Opening-gate merge authorization is satisfied. **Q1 historical fitting is authorized only through the dedicated Stage-A workflow after its contract job passes on the exact PR head.** Manual or ad-hoc Q1 fitting outside that dependency chain does not count as program evidence.

No Q1 result may be used to redesign the learner, quantiles, alpha grid, features, preprocessing, fixed slices, crossing treatment or chronology. Q2 remains blocked until the chronology-clean Q1 OOF interface and Stage-A evidence are frozen.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
