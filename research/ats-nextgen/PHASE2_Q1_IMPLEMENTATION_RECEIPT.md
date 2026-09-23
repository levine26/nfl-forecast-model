# ATS Next-Generation — Phase 2 Stage A / Q1 Pre-Result Implementation Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** A — Q1  
**Candidate:** `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`  
**Receipt status:** **IMPLEMENTATION FROZEN; HISTORICAL Q1 PERFORMANCE NOT YET GENERATED**  
**Stage-A branch:** `research/ats-nextgen-phase2-q1`  
**Stage-A base / verified opening merge:** `f43e17ba783e3e389969cd1649889b37bd91afe9`  
**Frozen reconciled pre-receipt implementation head:** `0a1184ac8da924701bb84e90f3d249d8239436e5`  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes used:** 0

This receipt freezes the final Q1 implementation boundary before the dedicated Stage-A workflow is allowed to generate any historical Q1 outer-OOF candidate performance.

## 1. Opening-gate integration is complete

PR #559 merged the Phase-2 opening gate after exact-head validation. The verified opening merge and Stage-A base are:

`f43e17ba783e3e389969cd1649889b37bd91afe9`.

The validated PR head was `446b8f963c4125bad972f79a793035d0a9a777e0`.

Required exact-head checks all succeeded:

- LevLine research firewall — run `35917266533` (#1969);
- ATS NextGen Phase 2 opening gate — run `35917266606` (#8);
- LevLine research validation — run `35917266598` (#1551), including gate job `107376225489`;
- Daily NFL model refresh / full pytest + PR regenerated-output validation — run `35917266639` (#1104).

## 2. Frozen historical input boundary

Q1 may consume only the Phase-2 gate identity frozen before candidate fitting:

- seasons 2015–2025 only;
- outer targets 2022, 2023, 2024, 2025;
- inner targets begin in 2019;
- market evidence class `historical_closing_late_benchmark_exact_horizon_opaque`;
- 2,895 rows / 2,895 ATS eligible / 73 pushes;
- 0 completed-2026 outcomes;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`.

The historical runner must regenerate the gate and **fail closed before fitting** if that canonical hash does not match.

## 3. Pre-result receipt reconciliation

`Q1_STAGE_A_OPENING_RECEIPT.md` was created before the Q1 implementation and therefore governs software details that Phase 1 had left unspecified. During the later implementation-receipt drafting, two values were temporarily written inconsistently with that earlier receipt: the alpha tie-break and the minimum eligible inner-training size. The discrepancy was discovered and corrected **before any Q1 historical model fit, OOF prediction, candidate metric or performance result existed**.

The final binding choices are therefore the original Stage-A opening choices:

- minimum eligible prior-training rows for an inner fold: **100**;
- if mean inner pinball losses are equal within numerical tolerance `1e-12`, select the **smaller alpha**;
- omitted inner targets are recorded explicitly and are never replaced by random CV.

No target performance motivated this reconciliation. No Q1 performance existed to inspect.

## 4. Frozen Q1 learner

- learner: `sklearn.linear_model.QuantileRegressor`;
- environment: `scikit-learn==1.9.0`;
- quantiles exactly `{10/21, 1/2, 11/21}`;
- L1 alpha grid exactly `{0.001, 0.01, 0.1, 1.0}`;
- `fit_intercept=True`;
- solver `highs`;
- alpha selected separately per quantile using pooled prior-only inner rolling-origin pinball loss;
- no GAM/tree/boosting/neural replacement;
- no post-hoc calibration;
- no post-hoc quantile-crossing repair.

## 5. Frozen preprocessing and features

Every fit derives preprocessing from training rows only:

- training-fold median imputation for each optional numeric feature;
- fixed missingness indicator for every optional market/football feature;
- training-fold-only `StandardScaler`;
- market total centered on the training-fold market-total median;
- no target-season preprocessing information.

Frozen market features are sportsbook home spread `L`, market home-margin center `C=-L`, favorite size, market total, no-vig home moneyline probability, missingness indicators, `C × centered_total`, and `|L| × centered_total`.

Frozen football state is exactly the PIT-safe shifted alpha-0.15 differential set in `DATA_AND_PIT_INVENTORY.md`: pregame Elo, offense/defense EPA, pass, rush, success, neutral EPA and rest differential. No player-state, weather, news, side juice, movement or book-dispersion feature is authorized in Q1 V1.

## 6. Frozen comparators and chronology

Stage A generates exactly:

- **M0:** residual quantiles fixed at zero / raw quoted-line reference;
- **M2:** the same quantile learner using market features only;
- **Q1:** market plus compact football state.

For outer season `s`, training is 2015 through `s-1`. For inner target `t`, training is 2015 through `t-1`. An inner fold additionally requires at least 100 eligible training rows. Random K-fold is prohibited. OOF output is deterministically sorted by season and `game_id`.

## 7. Frozen reporting

Primary Stage-A evidence is frozen before results to:

- pinball loss at all three quantiles;
- empirical quantile coverage and coverage error;
- overall and per-season evidence;
- secondary median/location error metrics;
- quantile-crossing diagnostic with no repair;
- the exact preregistered fixed slices only.

Key-number buckets: K3 `{2.5,3.0,3.5}`, K6 `{5.5,6.0,6.5}`, K7 `{6.5,7.0,7.5}`, K10 `{9.5,10.0,10.5}`, K14 `{13.5,14.0,14.5}`. The 6.5 overlap between K6 and K7 is intentional.

Favorite-size buckets: `<3`, `3–<7`, `7–<10`, `10–<14`, `>=14`.

Market-total buckets: `<42`, `42–<45`, `45–<48`, `>=48`.

No new post-result bucket is authorized. ATS hit rate and ROI are not Q1 selection criteria.

## 8. Tests-before-results execution gate

`.github/workflows/research_ats_nextgen_q1.yml` enforces:

1. the Q1 contract job must pass opening-gate, Q1 model and Q1 reporting tests;
2. the historical job has `needs: contract` and cannot start first;
3. the runner revalidates the frozen opening gate hash before fitting;
4. protected production surfaces must remain unchanged;
5. successful Q1 outputs are uploaded as immutable workflow evidence.

At this receipt boundary, that PR workflow has not run and no Q1 historical performance has been generated or inspected.

## 9. Frozen implementation identities

Frozen at reconciled pre-receipt head `0a1184ac8da924701bb84e90f3d249d8239436e5`:

- Q1 model `src/nfl_forecast/challenger_ats_nextgen_q1.py` — blob `adee4d024bc7dd824d6702749f7b7ce8dae0d8e7`;
- Q1 fixed-slice reporter `src/nfl_forecast/challenger_ats_nextgen_q1_reporting.py` — blob `b05c536fae784872666e29dbca3a3e7568e679af`;
- Q1 model tests `tests/test_challenger_ats_nextgen_q1.py` — blob `f36a887fe0db353f7543dcaf8a515966f151ef90`;
- Q1 reporting tests `tests/test_challenger_ats_nextgen_q1_reporting.py` — blob `17f2dde853bfc32eb35bb0b6a8affef6590f11fa`;
- Q1 runner `scripts/run_challenger_ats_nextgen_q1.py` — blob `e63f046ed5d7ae87645c5c8561e23a31719b3f0e`;
- dedicated Q1 workflow `.github/workflows/research_ats_nextgen_q1.yml` — blob `92a45f8a3aab852affdacbe6b1f2eb934c4b38c8`;
- research validation workflow `.github/workflows/research_validation.yml` — blob `731c91e2265a89009d16690a167dcbb3c34422c3`.

The earlier Stage-A opening receipt remains the authority for the software tie/minimum decisions; this implementation receipt records that the code now conforms to it.

## 10. Authorization boundary

Q1 historical fitting is authorized only through the dedicated Stage-A workflow after its contract job passes on the exact PR head. Manual or ad-hoc fitting outside that dependency chain does not count as program evidence.

No Q1 result may be used to redesign the learner, quantiles, alpha grid, features, preprocessing, tie-break, minimum fold size, fixed slices, crossing treatment or chronology. Q2 remains blocked until the chronology-clean Q1 OOF interface and Stage-A evidence are frozen.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
