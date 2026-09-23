# Phase 4 — Statistical Uncertainty Report

## Design

The final historical challenger holdout contains one target season, 2025, with 272 exact common A0/B0/C0 regular-season games. The preregistered uncertainty method is a season+week block bootstrap with 10,000 resamples. Because Phase 4 contains only one target season, **week is the operative resampling block**. This preserves within-week dependence but cannot estimate between-season variation from the holdout itself.

Accordingly, all confidence intervals below should be interpreted as single-season conditional uncertainty, not as precise estimates of future multi-season performance.

## Candidate versus market paired error

| Comparison | Mean candidate - market MAE | 95% block interval | Bootstrap P(candidate lower error) |
|---|---:|---:|---:|
| A0 margin | +0.772 | +0.367 to +1.254 | ~0.0000 |
| A0 total | +0.296 | -0.102 to +0.701 | 0.0759 |
| B0 margin | +0.582 | +0.185 to +1.050 | 0.0006 |
| B0 total | +1.417 | +0.672 to +2.154 | ~0.0000 |
| C0 M3 margin vs M0 | +0.0246 | -0.0242 to +0.0675 | 0.1488 |
| C0 M3 total vs M0 | -0.0179 | -0.0593 to +0.0228 | 0.7963 |

Positive values mean the challenger has higher absolute error than the market reference.

A0 and B0 margin results are clearly unfavorable within this single-season block analysis. B0 total is also clearly unfavorable. A0 total is nominally worse but uncertain. C0's tiny M3 total improvement and tiny margin loss both lie inside uncertainty; neither supports a meaningful incremental-information claim.

## Development consistency

The holdout direction is broadly consistent with 2022–2024 development evidence:

- A0 development margin/total MAE: 9.883 / 10.387 versus market 9.418 / 10.121; holdout again trails market.
- B0 development margin/total MAE: 10.213 / 11.304 versus market 9.418 / 10.121; holdout again trails market and retains a strong total-overprediction problem.
- C0 development M3 margin/total MAE: 9.439 / 10.138 versus M0 9.418 / 10.121; holdout again shows no material separation from M0.

This cross-period directional agreement strengthens the negative standalone interpretation even though Phase 4 itself contains only one target season.

## Distributional uncertainty and sharpness

A0 nominal 80% coverage is 76.5% for margin and 79.0% for total. B0 nominal 80% coverage is 92.3% and 91.2%, but with substantially wider mean intervals (45.15 margin / 49.07 total points versus A0 34.23 / 35.17). High B0 coverage is therefore not treated as evidence of superiority; its forecasts are materially less sharp.

Proper scores also do not support a B0 distributional advantage: A0 margin/total CRPS 7.558/7.631 versus B0 7.616/8.230; A0/B0 joint energy scores 8.455/8.797.

## Multiple diagnostics

Fixed diagnostic slices and ATS/O-U figures are descriptive. Phase 4 does not attach multiplicity-adjusted confirmatory significance to those slices, because they were not the primary model-selection targets and the single-season subgroup samples can be small. No slice can override worse pooled continuous error or trigger a new threshold.

## Inference limitations

1. Phase 1 had already inspected broad baseline 2025 failures, so the holdout is a final historical **challenger** holdout rather than a philosophically pristine never-seen season.
2. Only one target season is available; bootstrap intervals condition on the 2025 environment and week structure.
3. Historical market lines have an opaque closing/late horizon and are not T-120.
4. No result here substitutes for prospective Phase 6 evidence if any downstream candidate eventually becomes eligible.
5. Small nominal differences inside uncertainty, especially C0 total's -0.018-point MAE delta, are not promoted into claims of predictive edge.