# Phase 1 — Baseline Reproduction Report

**Status:** reproducible audit baseline; no challenger and no production change  
**Primary historical universe:** 1,087 NFL regular-season games, 2022–2025  
**Ties:** 3  
**Method labels:** score regressions = current-validation descriptive ensemble; winner = chronology-clean historical F-ST analogue

## 1. Reproduction status

The dedicated Phase 1 workflow successfully regenerated the current score/margin/total baseline from repository code and wrote:

- `baseline_metrics.json`;
- `baseline_predictions_2022_2025.csv`;
- `error_decomposition.csv`;
- `chronology_clean_winner_coefficients.csv`;
- `phase1_machine_summary.json`.

The workflow also verified that protected production surfaces were unchanged.

## 2. Independent score forecasts

| Target | Games | MAE | RMSE | Mean signed error, actual - prediction |
|---|---:|---:|---:|---:|
| Home points | 1,087 | **7.424** | 9.407 | -0.247 |
| Away points | 1,087 | **7.485** | 9.372 | -0.489 |
| Home margin | 1,087 | **9.962** | 12.888 | +0.242 |
| Game total | 1,087 | **10.854** | 13.658 | -0.735 |

These are the independent football regressions. The public Sunday Signal score pair is not exactly this object because public margin is later made coherent with the official F-ST win probability.

## 3. Regression model components

### Margin base-model mean OOF MAE

| Base regressor | Mean season-held-out MAE |
|---|---:|
| ElasticNet | **9.921** |
| CatBoost | 9.972 |
| Extra Trees | 10.032 |
| XGBoost | 10.130 |
| Current inverse-MAE ensemble | **9.962** |

### Total base-model mean OOF MAE

| Base regressor | Mean season-held-out MAE |
|---|---:|
| ElasticNet | **10.796** |
| CatBoost | 10.846 |
| Extra Trees | 10.888 |
| XGBoost | 11.050 |
| Current inverse-MAE ensemble | **10.854** |

The current descriptive inverse-MAE blend does **not** improve the reported OOF MAE over ElasticNet for either margin or total. Phase 1 does not replace it; the result is a direct Phase 2 simplification/stacking hypothesis.

The descriptive weights are nearly equal for all four regressors, approximately 25% each. That suggests the weighting rule is currently doing little more than an equal-ish average.

## 4. Market baselines on exact paired games

Historical schedule market data are treated as an opaque closing/late benchmark, not a specific T-minus horizon.

| Target | LevLine MAE | Market MAE | LevLine - market |
|---|---:|---:|---:|
| Margin / spread | **9.962** | **9.494** | **+0.468** |
| Total | **10.854** | **10.189** | **+0.665** |

Paired season+week block bootstrap:

- margin MAE difference: +0.468 points; 95% interval approximately **+0.30 to +0.64**;
- total MAE difference: +0.665 points; 95% interval approximately **+0.44 to +0.90**;
- in 10,000 block-bootstrap draws for each target, the model-vs-market MAE delta did not cross below zero.

Interpretation: on this exact current-validation universe, the historical market benchmark is materially better than the independent LevLine score regression for both margin and total.

This does **not** imply the market is unbeatable; it establishes the benchmark any Phase 2 score challenger must beat or add incremental information beyond.

## 5. Modern 2023–2025 sensitivity

The user requested emphasis on the modern NFL. Restricting to 816 games from 2023–2025:

| Target | LevLine MAE | Market MAE |
|---|---:|---:|
| Margin | **10.256** | **9.744** |
| Total | **10.680** | **10.121** |

The core conclusion is unchanged on the modern subset.

## 6. Season stability

| Season | Margin MAE | Market spread MAE | Total MAE | Market total MAE |
|---|---:|---:|---:|---:|
| 2022 | 9.076 | 8.742 | 11.379 | 10.395 |
| 2023 | 10.550 | 9.901 | 10.906 | 10.239 |
| 2024 | 9.978 | 9.610 | 10.008 | 9.730 |
| 2025 | 10.241 | 9.722 | 11.124 | 10.393 |

The market benchmark has lower MAE in every target season for both margin and total.

## 7. Winner probability baseline

The Phase 1 winner report uses the existing chronology-clean historical F-ST analogue rather than the ordinary non-nested Core stack.

| Probability model | Winner accuracy | Brier | Log loss |
|---|---:|---:|---:|
| Chronology-clean F-ST analogue | **68.17%** | 0.21065 | 0.60871 |
| Raw market probability | 67.62% | **0.21020** | **0.60765** |
| Football-only nested PURE | 64.49% | 0.22385 | 0.63895 |

Tie-excluded straight-up sensitivity:

- F-ST analogue: **68.08%** on 1,084 games;
- raw market: **67.53%**.

Thus the historical F-ST analogue has slightly better 0.5-threshold winner accuracy than the raw market on this sample, while the raw market has slightly better proper probability scores. Those are different evaluation goals and should not be collapsed into one “winner.”

## 8. ATS diagnostic baseline

Using the independent margin regression versus the historical spread benchmark:

- market-covered games: 1,087;
- ATS pushes: 29;
- non-push model-side decisions: 1,058;
- model-side ATS hit rate: **48.77%**;
- cover-probability Brier: 0.2604.

By fixed model-market margin disagreement:

| Absolute disagreement | Games | ATS decisions | Model ATS hit rate | Model margin MAE | Market spread MAE |
|---|---:|---:|---:|---:|---:|
| <2 | 525 | 504 | 48.41% | 9.444 | 9.294 |
| 2–4 | 348 | 343 | 49.27% | 9.757 | 9.343 |
| 4–6 | 141 | 139 | 46.04% | 11.520 | 10.543 |
| 6–8 | 43 | 42 | 52.38% | 11.124 | 9.570 |
| 8+ | 30 | 30 | 56.67% | 12.418 | 9.717 |

The small high-disagreement ATS samples should not be interpreted as a betting rule. Existing paired error forensics show that games with a model-market margin gap >=6 points have **worse**, not better, margin error than the market:

- 73 games;
- model minus market MAE = **+2.026 points**;
- block-bootstrap 95% interval = **+0.130 to +3.678**;
- bootstrap probability that the model is better = 1.7%.

Large disagreement is therefore not, by itself, evidence of LevLine edge.

## 9. Uncertainty / interval coverage

The current regression residual sigmas are:

- margin sigma: **12.892** points;
- total sigma: **13.644** points.

Nominal Normal 80% intervals cover:

- margin: **80.59%**;
- total: **80.13%**.

This is close to nominal unconditional coverage. It does not prove conditional calibration across favorite size, total regime, injuries, or other subgroups.

## 10. Prediction-range compression

Observed versus predicted cross-game standard deviations:

| Quantity | Actual SD | Model prediction SD | Market SD where applicable |
|---|---:|---:|---:|
| Home points | 9.894 | **3.243** | — |
| Away points | 9.550 | **2.803** | — |
| Margin | 13.865 | **5.779** | 5.863 |
| Total | 13.637 | **1.832** | 4.252 |

Expected-value forecasts should naturally vary less than noisy realized outcomes, so actual-versus-predicted SD is not by itself a calibration failure. The more actionable finding is that the **total prediction varies far less across games than even the market total**, and conditional diagnostics show strong regression-to-the-middle in low/high total environments.

## 11. Coherence between winner and independent margin

Across the 1,087 historical games:

- official-analogue winner direction and independent margin direction split on **200 games (18.4%)**;
- independent margin versus probability-implied margin correlation = **0.809**;
- mean absolute difference between those two margins = **3.149 points**.

This confirms the current architecture contains two distinct views of game strength. The public forecast resolves that conflict by deriving the displayed fair margin from official F-ST probability.

## 12. Baseline conclusion

Phase 1 reproduces the current system without a major unresolved baseline ambiguity:

- team score MAE is roughly 7.4–7.5 points per team;
- independent margin MAE is about 10.0;
- independent total MAE is about 10.85;
- the historical market benchmark is better on both margin and total;
- current independent-margin ATS decisions are below 50% overall;
- large model-market disagreements are not validated edges;
- F-ST winner classification remains competitive with the market but is a separate market-conditioned probability architecture;
- current regression blending and total-range compression are concrete Phase 2 research targets.
