# LevLine ATS Historical Key-Mass Challenger

Status: IMPLEMENTATION / HISTORICAL EXECUTION

This program is research-only. It MUST NOT modify production F-ST, Sunday Signal, official locks, or any live forecasting behavior.

## Objective

Test whether the accepted ATS Frontier V2 constant-scale Student-t key-mass distribution improves when its location center is changed from the market to leakage-safe historical LevLine/F-ST fair margins, or a training-only blend of the two.

## Frozen candidates

All candidates use the same distributional family and exact integer-margin scoring.

- `KMASS-MARKET`: location = canonical repository market home-margin center.
- `KMASS-LEVLINE`: location = leakage-safe reconstructed LevLine/F-ST coherent fair home margin.
- `KMASS-BLEND`: location = `w * market + (1-w) * LevLine`, with `w` restricted to `{0.0, 0.1, ..., 1.0}` and selected only on rows preceding the target season.

## Frozen distribution family

- Student-t integer mass: `P(M=m)=F(m+0.5)-F(m-0.5)`.
- Finite log-mass adjustments only at `0`, `|3|`, and `|7|`.
- Analytic infinite-lattice normalization from accepted ATS Frontier V2 code.
- Constant scale only.
- No conditional scale.
- No finite support or endpoint folding.
- No probability clipping as a modeling device.
- No extra key numbers, skew, mixtures, or feature expansion.
- V2 hyperparameter grids are reused: `nu in {4,6,10,30}`, `lambda_key in {1,10}`.

## LevLine/F-ST center reconstruction

The fair-margin contract is the production public contract:

`fair_margin_home = Phi^-1(official_home_probability) * margin_sigma`

For every historical target season, both inputs are reconstructed without target-season outcome leakage:

1. The F-ST stack uses the immutable historical OOF `market_prob` and nested-PURE `pure_prob` archive, but the stack coefficients are refit using only seasons strictly before the season being scored. Final 2026 frozen coefficients are never back-applied to historical target seasons.
2. `margin_sigma` is the residual standard deviation from the production margin-regression architecture fit only on seasons strictly before the season being scored, using the same chronological validation discipline as production.

The immutable F-ST historical training archive begins in 2020. A pre-season stack can therefore first be reconstructed for 2021. Consequently the first scientifically clean outer target is 2022. The historical target set is frozen to 2022-2025. No claim will be made for 2016-2021, because the official F-ST architecture does not have an admissible prior-only center reconstruction for those requested years.

## Chronology

Outer target seasons: `2022, 2023, 2024, 2025`.

For each target season `T`:

- reconstruct all candidate centers only from information available before each scored game/season under the frozen OOF artifacts;
- fit distribution parameters using common candidate rows with season `< T`;
- select blend weight using only common rows with season `< T`;
- score season `T` once;
- never use target-season outcomes for fitting, nuisance selection, blend-weight selection, or calibration rescue.

The first 2022 distribution fit uses reconstructed 2021 common-center rows. Later folds expand chronologically.

## Training-only selection rules

For each center, nuisance parameters are selected by the minimum penalized training objective from the frozen V2 grid. Ties are broken by lower `nu`, then lower `lambda_key`.

For `KMASS-BLEND`, each frozen weight is fitted/scored on the same pre-target training rows. The selected weight minimizes the training-only penalized integer-margin objective. Ties are broken by distance to `0.5`, then by lower market weight. No target-season result can enter weight selection.

## Common-row contract

Primary comparisons are paired. Every reported candidate-vs-candidate delta uses identical game IDs. The runner records:

- eligible completed regular-season rows with a historical spread;
- archived F-ST candidate rows;
- rows surviving schedule/F-ST joins;
- rows removed for missing required market/total/center values;
- final common test N by season and aggregate.

## Primary and secondary evidence

Primary: exact observed integer-margin log score.

Also report:

- paired candidate-minus-market and candidate-minus-candidate deltas;
- 10,000-resample season/week-block bootstrap intervals and probability favorable;
- cover/push/loss log loss and multiclass Brier score;
- home-cover calibration diagnostics excluding pushes;
- full-slate ATS diagnostic with no confidence threshold;
- center margin MAE/RMSE;
- per-season results;
- constant-scale/no-key ablation for each frozen center;
- selected nuisance parameters and blend weights by outer season.

ATS ROI shown at reference -110 is diagnostic only and is not an empirical historical price/ROI claim.

## Preregistered decision gate

A non-market center (`KMASS-LEVLINE` or `KMASS-BLEND`) advances as the historical research winner only if all of the following hold against `KMASS-MARKET` on the paired outer-test rows:

1. aggregate primary paired delta is favorable (`candidate - market < 0`);
2. the 95% season/week-block bootstrap interval has an upper bound below `0`;
3. the primary paired delta is favorable in at least 3 of the 4 outer seasons;
4. every outer season has at least 200 common scored games and aggregate common N is at least 800.

If both non-market candidates pass, the one with the lower aggregate primary log score is selected; exact ties prefer the simpler pure LevLine center over the blend. If neither passes, the disposition is `RETAIN_KMASS_MARKET`. This gate authorizes only the next research/implementation stage; it never authorizes a production forecast change.

## Firewalls

- Completed 2026 outcomes are forbidden from data loading, fitting, tuning, or scoring.
- The runner requests historical data only through 2025.
- No production import may write or mutate production artifacts.
- Results live only under `research/ats-historical-challenger/results/` or a CI artifact.
- No production authorization is implied by a positive research result.
