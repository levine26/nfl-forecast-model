# ATS Next-Generation — Q1 Stage A Opening Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** A — Q1 only  
**Candidate:** `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`  
**Status at receipt:** **AUTHORIZED TO IMPLEMENT; UNTRAINED; NO COMPLETED Q1 PERFORMANCE ARTIFACT**  
**Stage branch:** `research/ats-nextgen-phase2-q1`  
**Opening base:** merged `main` at `f43e17ba783e3e389969cd1649889b37bd91afe9`

## Authorization chain

PR #559 merged the Phase-2 pre-result opening gate and receipt at `f43e17ba783e3e389969cd1649889b37bd91afe9` after exact-head validation of:

- LevLine research firewall `35917266533`: SUCCESS;
- ATS NextGen Phase 2 opening gate `35917266606`: SUCCESS;
- LevLine research validation `35917266598`: SUCCESS;
- Daily NFL model refresh/full pytest `35917266639`: SUCCESS.

The receipt-head re-materialization reproduced the exact historical gate identity from the pre-receipt run:

- 2,895 rows / 2,895 ATS eligible / 73 pushes;
- raw gate SHA-256 `0fabdc442e914ee9dc5cd501a728f1c1d69e11e01e44dd16ff800f46231fa20e`;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- completed-2026 outcomes used: 0.

The Phase-2 opening condition is therefore satisfied and Stage A may begin.

## Frozen Q1 contract

This stage implements exactly `Q1_QUANTILE_PREREGISTRATION.md`:

- target `R = M + L`;
- `M = home_score-away_score`;
- canonical sportsbook `L = -nflverse spread_line`;
- quantiles exactly `10/21`, `1/2`, `11/21`;
- learner exactly `sklearn.linear_model.QuantileRegressor` with L1 penalty;
- alpha grid exactly `{0.001,0.01,0.1,1.0}`;
- alpha selected separately for each quantile by prior-time inner rolling-origin mean pinball loss;
- Q1-M0 is zero residual correction;
- Q1-M2 is the identical quantile learner using market features only;
- Q1 is market plus the frozen compact football state;
- training-fold-only median imputation, total centering and scaling;
- fixed preregistered key-number, favorite-size and market-total reporting slices only;
- no random K-fold;
- no post-hoc calibration or quantile-crossing repair;
- no nonlinear rescue learner;
- no player-state/weather/news/juice/book-dispersion expansion;
- no completed-2026 outcomes.

## Earliest pre-result implementation decisions

The frozen scientific documents do not specify a numerical tie-break for exactly equal inner mean pinball losses. The **earliest Stage-A receipt, before any completed Q1 historical artifact existed, fixed ties to the smaller alpha** after numerical equality within tolerance `1e-12`. That earliest decision controls this candidate version and is encoded in the implementation/tests.

The same earliest receipt fixed a mechanical minimum of **100 eligible prior training rows** for an inner rolling-origin fold. A fold with fewer than 100 eligible prior training rows or no eligible target rows is omitted, never replaced by random CV, and the implementation records both `inner_targets_used` and `inner_targets_omitted` in tuning evidence.

The fixed feature implementation creates missingness indicators for every optional numeric V1 feature. Indicators may be all-zero in a particular fold. Missing numeric values are imputed only from that training fold. Market total is centered on the training-fold median before the two frozen spread-total interactions are constructed.

Quantile crossings are reported as diagnostics only. No sorting, clipping, isotonic repair or other post-hoc monotonicity correction is authorized for Q1 V1.

## Governance reconciliation before results

A later pre-result edit briefly proposed the opposite tie-break (larger alpha) and removal of the 100-row guard. No completed Q1 evidence artifact was produced under that conflicting state: the corresponding first historical job was cancelled when the branch moved and uploaded no Q1 evidence. To avoid choosing between implementation rules after seeing target-period evidence, Stage A therefore reverts to and preserves the **earliest documented pre-result receipt**: smaller-alpha tie-break plus the 100-row inner-training minimum.

This reconciliation is governance-only; it is not motivated by candidate performance and does not authorize any new feature, learner, quantile, threshold, calibration or rescue mechanism.

## Execution boundary

Q1 historical outer OOF generation is permitted only after the Phase-2 gate tests and Q1 contract/reporting tests pass on the exact implementation head. The dedicated Stage-A workflow enforces this dependency: the historical job cannot start unless the contract job succeeds.

The historical runner must first regenerate the 2015–2025 gate and match the frozen canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`; a mismatch fails closed before any Q1 fit.

After the first valid completed Q1 outer OOF artifact exists, the learner, quantiles, alpha grid, feature family, chronology, preprocessing semantics, tie-break, 100-row fold guard, comparators and fixed reporting slices may not be redesigned in response to those results.

Q2 and Q3 remain unopened.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
