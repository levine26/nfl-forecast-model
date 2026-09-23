# Phase 4 — Historical Validation Report

**Program:** LevLine Spread & Points Next-Generation Research Program  
**Target:** 2025 regular season  
**Evidence boundary:** final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions  
**Production:** `F-ST-01-FROZEN-2026`, unchanged

## Execution integrity

The one-time underlying-model holdout was opened only after the pre-result receipt commit `362af7af7db43a715b9ab9537a52d2749c37e7a6` and a successful pre-holdout contract gate. The first completed scientific package was workflow run `35818332253` at generator head `f0b92217488a1a000bee74a903a9437931a53230`. Its full evidence package was preserved as artifact `10732945725` and then committed byte-for-byte after hash verification.

All three frozen candidates used implementation SHA-256 `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579` and config SHA-256 `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`. All 272 eligible 2025 regular-season games are present for A0, B0 and C0, and every emitted prediction records `train_through_season = 2024`. The frozen shifted pregame state construction may use prior completed 2025 games, but no current-game or future 2025 outcome enters its own forecast and estimator fitting/tuning remains through 2024.

## Primary holdout results

| Model | Home pts MAE | Away pts MAE | Margin MAE | Margin RMSE | Total MAE | Total RMSE |
|---|---:|---:|---:|---:|---:|---:|
| A0 | 7.488 | 7.724 | 10.495 | 13.435 | 10.689 | 13.506 |
| B0 | 7.654 | 7.942 | 10.305 | 13.231 | 11.810 | 14.518 |
| Market M0 | — | — | **9.722** | 12.271 | 10.393 | 13.186 |
| C0 M3 | — | — | 9.747 | 12.300 | **10.376** | 13.170 |

A0 margin signed error was +0.090 points and total signed error was -2.139 points (`actual - prediction`). B0 margin signed error was +0.521 points; its total signed error was **-5.493 points**, confirming and worsening the development-period tendency to overpredict game totals.

## Market-relative results

A0 margin MAE exceeded the exact paired market by **+0.772 points**. The 10,000-draw week-block bootstrap 95% interval was **+0.367 to +1.254**, with bootstrap probability of lower A0 absolute error effectively 0. A0 total MAE exceeded market by +0.296 points; its interval of approximately -0.102 to +0.701 crosses zero, so the holdout does not establish a meaningful total difference even though the nominal direction is unfavorable.

B0 margin MAE exceeded market by **+0.582 points** with 95% interval **+0.185 to +1.050**. B0 total MAE exceeded market by **+1.417 points** with 95% interval **+0.672 to +2.154**. These are materially negative market-relative results.

For C0, M3 margin MAE was 9.747 versus M0 9.722: **M3 - M0 = +0.0246 points**, 95% interval approximately **-0.024 to +0.067**. M3 total MAE was 10.376 versus M0 10.393: **M3 - M0 = -0.0179 points**, 95% interval approximately **-0.059 to +0.023**. The tiny nominal total improvement lies entirely inside sampling uncertainty and does not establish incremental football information beyond the market.

## Reference baselines

On the same 272-game 2025 season:

| Baseline | Margin MAE | Total MAE |
|---|---:|---:|
| Market | **9.722** | **10.393** |
| Historical scoring average | 10.387 | 10.635 |
| Simple EPA/team strength | 10.342 | 10.678 |
| Naive HFA / league total | 11.056 | 10.971 |

Neither A0 nor B0 earns standalone finalist status against this compact baseline set. A0 is also slightly worse than the simple EPA and historical-scoring references on the two pooled continuous targets; B0 is materially worse on total.

The Phase 1 current LevLine score ensemble remains historical context only because its documented weighting/evaluation surface spans the same 2022–2025 block. It is not relabeled as a clean standalone 2025 comparator. Likewise, no production F-ST artifact trained with 2025 outcomes is scored as if it were 2025 out-of-sample evidence.

## Probability and distribution diagnostics

A0 straight-up accuracy was 56.99% (56.83% with the one tie excluded), Brier 0.2344 and log loss 0.6603. B0 straight-up accuracy was 62.50% (62.36% tie-excluded), Brier 0.2300 and log loss 0.6515. These remain secondary to the score/margin/total task.

A0 80% coverage was 76.5% for margin and 79.0% for total, with mean interval widths 34.23 and 35.17 points respectively. Its margin/total CRPS were 7.558/7.631, and its Monte Carlo joint energy score was 8.455. B0's 80% coverage was 92.3% for margin and 91.2% for total, with much wider mean widths of 45.15 and 49.07 points; margin/total CRPS were 7.616/8.230 and joint energy score 8.797. B0 therefore obtains high coverage partly through materially lower sharpness. No empirical B0 log score is reported because a finite 10,000-draw discrete score mass would require an arbitrary zero-cell smoothing rule not frozen in the candidate identity.

## Secondary ATS / O-U diagnostics

A0 ATS hit rate was 49.1% and O/U directional hit rate 52.2%; B0 ATS was 48.7% and O/U 51.8%; C0 M3 ATS was 51.3% and O/U 57.0%. These are descriptive only. They did not select a candidate, alter a threshold, or override continuous-error evidence.

## Historical disposition

- **A0:** methodologically valid football-only representation; negative standalone scoring result; **not a standalone historical finalist**.
- **B0:** methodologically valid possession/drive representation; negative standalone result with persistent total overprediction and materially worse market-relative total error; **not a standalone historical finalist**.
- **C0:** valid market-aware diagnostic; **no demonstrated incremental football information beyond M0**; not a standalone scoring finalist.
- **D:** remains `ENSEMBLE_NOT_ELIGIBLE`; it was not fit or reconsidered on 2025.

**Program-level Phase 4 disposition: NO HISTORICAL STANDALONE FINALIST.** This is a valid negative result. It does not invalidate A0/B0 as frozen underlying representations that Phase 5 may inspect under its separate Candidate 5 charter and evidence-boundary rules.