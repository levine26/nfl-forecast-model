# ATS Next-Generation — Q1 Stage A Opening Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** A — Q1 only  
**Candidate:** `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`  
**Status at receipt:** **AUTHORIZED TO IMPLEMENT; UNTRAINED; NO Q1 PERFORMANCE GENERATED**  
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

This stage will implement exactly `Q1_QUANTILE_PREREGISTRATION.md`:

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
- no random K-fold;
- no post-hoc calibration;
- no nonlinear rescue learner;
- no player-state/weather/news/juice/book-dispersion expansion;
- no completed-2026 outcomes.

## Pre-result implementation decisions required by software, not target results

The frozen scientific documents do not specify a numerical tie-break for exactly equal inner mean pinball losses. Before any Q1 output exists, Stage A fixes the deterministic tie-break to the **smaller alpha** after sorting by `(mean_pinball_loss, alpha)`.

The fixed feature implementation will create missingness indicators for every optional numeric V1 feature. This is a stable schema choice; indicators may be all-zero in a particular training fold. Missing numeric values are imputed only from that training fold. Market total is centered on the training-fold median before the two frozen spread-total interactions are constructed.

An inner fold is mechanically eligible when it contains target rows and at least 100 eligible prior training rows. A missing/insufficient fold is omitted with an explicit receipt; it is never replaced by random CV. The current gate has ample pre-2019 history, so this guard is not a data-driven tuning parameter.

## Execution boundary

Q1 historical outer OOF generation is permitted only after Q1 contract tests pass on the exact implementation head. If those tests fail, no Q1 result from that execution is interpretable.

After the first valid Q1 outer OOF result exists, the Q1 learner, quantiles, alpha grid, feature family, chronology, preprocessing semantics, tie-break and comparators may not be redesigned in response to those results.

Q2 and Q3 remain unopened.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
