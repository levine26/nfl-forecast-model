# Phase 4 — Ablation Report

Phase 4 did not create new model families. Every comparison below was frozen before the 2025 holdout.

## C0 mandatory M0/M1/M2/M3 hierarchy

All C0 arms use the same 272 exact paired 2025 market rows and the frozen market label `historical_closing_late_benchmark_exact_horizon_opaque`.

| Arm | Margin MAE | Total MAE | Interpretation |
|---|---:|---:|---|
| M0 — raw market | **9.7224** | 10.3934 | frozen market null |
| M1 — market + line-level calibration | 9.7235 | 10.3812 | essentially M0 |
| M2 — market + A0 football residual information | 9.7468 | **10.3754** | tiny total nominal gain; margin worse |
| M3 — full C0 | 9.7470 | 10.3755 | essentially M2; no added material value |

M3 versus M0: margin +0.0246 MAE (95% interval approximately -0.024 to +0.067); total -0.0179 MAE (95% interval approximately -0.059 to +0.023). Therefore the holdout does **not** establish incremental football information beyond M0 for either target.

The hierarchy is particularly informative because M1, M2 and M3 all collapse near the market null. No M4 or nonlinear residual rescue is authorized or created.

## Football-only versus market-aware separation

A0 and B0 remain football-only questions; C0 remains market-aware. On margin, the exact 2025 market M0 MAE of 9.722 is lower than A0 (10.495) and B0 (10.305). On total, M0 at 10.393 is lower than A0 (10.689) and B0 (11.810). The market-aware C0 arms remain close to M0 rather than demonstrating a distinct incremental signal.

This preserves the program's intended separation:

1. A0/B0 test whether structured football-only forecasts can improve the underlying scoring task.
2. C0 tests whether frozen football information can improve an already-strong market prior.

The 2025 result is negative on both questions at the standalone-model level.

## Existing simple baseline ablations

The compact frozen baseline set remains sufficient to reject complexity-for-complexity's-sake:

- market: margin 9.722, total 10.393;
- historical scoring average: margin 10.387, total 10.635;
- simple EPA/team strength: margin 10.342, total 10.678;
- naive HFA/league total: margin 11.056, total 10.971.

A0 does not beat the simple EPA reference on either margin or total and does not beat the historical-scoring reference on either pooled target. B0 is slightly better than the simple EPA reference on margin but materially worse on total, and both football-only challengers remain worse than the market.

## Distribution versus point-estimate comparison

A0's Gaussian distribution is comparatively sharper but mildly undercovers its nominal margin interval on the single-season holdout. B0's simulation distribution is much wider and substantially overcovers 80% margin/total intervals. B0 therefore does not earn complexity credit merely from high coverage; calibration and sharpness must be interpreted together.

A0 margin CRPS = 7.558; B0 margin CRPS = 7.616. A0 total CRPS = 7.631; B0 total CRPS = 8.230. A0 joint energy score = 8.455; B0 = 8.797. These proper-score diagnostics do not reverse the point-estimate conclusion.

## D remains absent

D was development-gated and frozen `ENSEMBLE_NOT_ELIGIBLE` for margin and total before 2025. No D predictions, weights, alternate stacker, threshold change or D2 were created in Phase 4.

## Prohibited ablations not performed

No QB layer, injury layer, weather, new decay window, A1 state-space model, Negative Binomial B variant, alternative red-zone formula, nonlinear C residual learner, boosted tree, new ensemble, or post-hoc feature search was opened after the 2025 result.