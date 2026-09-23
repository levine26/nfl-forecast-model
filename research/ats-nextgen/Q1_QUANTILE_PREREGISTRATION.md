# Q1 Preregistration — Quantile Market-Residual Model

Experiment ID: `Q1-QR-MARKET-RESIDUAL-V1`
Status: FROZEN BEFORE RESULTS

## Scientific question

Can compact chronology-clean football/market state improve estimation of ATS-relevant conditional quantiles around the sportsbook spread, beyond market-only calibration?

This is not a new mean-residual stack. The previously rejected C0 mean-residual hypothesis remains closed.

## Target and sign convention

- `M = home_score - away_score`
- `L = quoted sportsbook home spread` (favorite negative)
- `S = -L`
- `R = M + L = M - S`

Q1 predicts conditional quantiles of `R`.

Frozen quantiles:

- `tau_low = 10/21 = 0.47619047619047616`
- `tau_mid = 1/2 = 0.5`
- `tau_high = 11/21 = 0.5238095238095238`

The outer quantiles are standard -110 continuous/no-push reference quantiles. They are not substituted for the push-aware EV calculation.

## Frozen learner

Exactly one learner family is authorized: regularized linear quantile regression using the pinball/check loss.

Implementation target: an L1-penalized linear quantile regression equivalent to scikit-learn `QuantileRegressor`.

Frozen regularization grid:

`alpha in {0.001, 0.01, 0.1}`.

A separate model is fit for each frozen tau, but **one shared alpha** is selected for the experiment using the mean of the three inner-OOF pinball losses, with each inner validation season weighted equally.

Tie rule: if objective values are equal within `1e-8`, choose the larger alpha.

No nonlinear Q1 challenger is authorized in V1. No post-result GAM/boosting rescue is allowed.

## Frozen feature contract

### Market features

- `S = -spread_line`
- `abs_S = abs(S)`
- `total_line`
- `market_home_prob` from paired home/away moneylines after no-vig normalization, when both exist

No historical spread-side juice, book identity, line movement or book dispersion is used because those fields are not available under the current historical PIT contract.

### Football features

Exactly this compact set from existing shifted pregame state:

- `elo_diff = home_elo - away_elo`
- `rest_diff`
- `diff_off_epa_ewma`
- `diff_pass_epa_ewma`
- `diff_rush_epa_ewma`
- `diff_success_rate_ewma`
- `diff_def_epa_allowed_ewma`
- `diff_def_pass_epa_allowed_ewma`
- `diff_def_rush_epa_allowed_ewma`
- `diff_def_success_allowed_ewma`
- `diff_win_ewma`

No lag-window feature variants, new player-state reconstruction, weather variables or post-hoc feature additions are authorized.

## Missingness and preprocessing

For every frozen input variable:

1. append a fixed missing indicator;
2. replace missing numeric values with the training-fold median;
3. standardize continuous variables using training-fold mean and standard deviation;
4. reuse those exact parameters on validation/outer rows.

Zero-variance training columns are standardized with scale 1 rather than dropped based on target-period behavior.

No preprocessing statistic may use outer-season rows.

## Quantile crossing

Independent linear quantile fits can cross. Q1's official row-level output uses deterministic monotone rearrangement:

`[q_low*, q_mid*, q_high*] = sort([q_low_raw, q_mid_raw, q_high_raw])`.

No result-dependent crossing repair is allowed.

Primary Q1 pinball metrics use the rearranged official quantiles. Raw crossing frequency and raw pinball loss are also reported as diagnostics so rearrangement cannot conceal instability.

## Market nulls for Q1

### Q1-M0

Zero residual: `Q_tau(R|X)=0` for all three tau. This corresponds to accepting the quoted spread as the relevant center with no correction.

### Q1-M2 market-only quantile calibration

Same learner, chronology and alpha grid, but features are restricted to the frozen market features above. No football state.

### Q1 full

Market + frozen football features.

A football-incremental claim requires Q1 full to improve the preregistered quantile score against Q1-M2, not merely against zero residual.

## Chronology

For each outer season `Y in {2022,2023,2024,2025}`:

- eligible history begins 2015;
- inner validation seasons are `2019,...,Y-1`;
- inner fold `t` trains on `2015,...,t-1` and predicts season `t`;
- choose shared alpha from pooled inner OOF predictions with equal season weights;
- refit each tau model on all seasons `2015,...,Y-1`;
- predict outer `Y` once;
- no outer outcome may affect alpha, features, preprocessing or crossing policy.

Random K-fold is prohibited.

## Primary Q1 metrics

For each tau and pooled across taus:

- pinball loss versus Q1-M0 and Q1-M2;
- empirical quantile coverage/calibration (`P(R <= q_tau)`);
- quantile calibration by outer season;
- quantile calibration by frozen spread/key buckets;
- median absolute error of `S + q_mid`;
- MAE/RMSE as secondary location diagnostics;
- quantile crossing frequency before rearrangement.

ATS hit rate and ROI do not select Q1.

## Required ablations

Only these predeclared comparisons are allowed:

1. Q1-M0 zero residual;
2. Q1-M2 market-only QR;
3. Q1 full market + football.

No single-feature deletion tournament is authorized.

## Decision interpretation

- If full Q1 improves Q1-M2 on preregistered pinball/calibration metrics with stable season-level evidence, it may establish incremental quantile information.
- If Q1-M2 improves M0 but full Q1 does not improve Q1-M2, the finding is market-shape calibration only.
- If neither improves, Q1 is rejected/inconclusive under Phase-3 synthesis.

A favorable ATS percentage cannot rescue failed quantile evidence.