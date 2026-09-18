# LevLine Props 2.0 — Market-Prior Development Result

Status: **RETROSPECTIVE CHALLENGER DEVELOPMENT — NOT PROMOTION EVIDENCE**

Frozen V1 source run: `35363701921`  
Frozen V1 historical baseline: **51.02% (2,888 / 5,660 decided non-push props)**

## Headline development result

On the rolling-origin 2024–2025 development evaluation, the low-dimensional
market-prior challenger was:

**53.74% accurate (2,208 / 4,109 decided props)**

versus the frozen V1 directions on the same rows:

**51.23% (2,105 / 4,109).**

The paired improvement is **+2.51 percentage points**. A game-clustered 95% bootstrap
interval for the paired accuracy difference is approximately **+0.14 to +4.91
percentage points** across 153 unique games.

This is not promotion evidence. The 2023–2025 outcomes were already inspected during
the V1 diagnosis.

## Critical market comparison

Exactly balanced no-vig sportsbook prices are **not** directional predictions. The
evaluation therefore abstains on the market-direction comparator when
`P(over) == 0.50`.

Across the 4,109 rolling-origin rows:
- price-informative sportsbook rows: **3,002**
- exactly balanced price rows: **1,107**
- sportsbook price-direction accuracy on informative rows: **55.13%**
- challenger accuracy on those same informative rows: **55.06%**
- challenger minus market direction: **-0.07 percentage points**
- game-clustered 95% interval for challenger minus market: approximately
  **-1.11 to +0.98 percentage points**

Thus the current experiment does **not** show incremental directional information over
the sportsbook price direction.

Probability scoring says the same thing:
- V1 Brier: **0.28600**
- market Brier: **0.24608**
- challenger Brier: **0.24621**
- V1 log loss: **0.83248**
- market log loss: **0.68514**
- challenger log loss: **0.68540**

The market prior is marginally better than the challenger on both Brier and log loss.

## Fitted residual coefficients

The market coefficient is fixed at 1.0 by contract. LevLine may contribute only
through its logit disagreement with the market.

Fixed-anchor training on 2023 Weeks 1–9:
- intercept: **+0.0090**
- LevLine residual beta: **-0.0100**

The residual coefficient is effectively zero.

Rolling-origin:
- 2024 evaluation, trained on 2023: intercept **+0.0409**, residual beta **-0.0054**
- 2025 evaluation, trained on 2023–2024: intercept **-0.0551**, residual beta **+0.0295**

The 2025 coefficient/result is not a season-wide estimate because the genuine-OPEN
2025 sample contains only 16 unique games.

## By prop family — rolling-origin development

| Prop | N | V1 accuracy | Challenger accuracy | Price-informative market accuracy |
|---|---:|---:|---:|---:|
| Passing TDs | 286 | 50.35% | 60.49% | 60.14% (276 rows) |
| Passing yards | 298 | 52.35% | 48.32% | 51.49% (101 rows) |
| Receptions | 1,374 | 53.20% | 56.55% | 56.73% (1,315 rows) |
| Receiving yards | 1,448 | 50.41% | 51.31% | 51.93% (853 rows) |
| Rushing yards | 703 | 48.93% | 52.77% | 54.27% (457 rows) |

These subgroup results are descriptive development diagnostics, not validated
selective signals.

## Fixed-anchor stability check

Training once on 2023 Weeks 1–9 and freezing thereafter produced:
- evaluation rows: **5,030**
- V1 accuracy: **51.27%**
- challenger accuracy: **53.60%**
- paired improvement: **+2.33 percentage points**
- paired game-clustered 95% interval: approximately **+0.20 to +4.52 points**
- price-informative market accuracy: **54.86%**
- challenger accuracy on those same market-informative rows: **54.86%**

Again, the improvement over V1 is explained by anchoring to the market rather than a
demonstrated LevLine residual.

## Provenance

Independent reproduction used the exact forecast-level files previously downloaded
from the authoritative V1 run:

- 2023 `2023_forecast_level.csv`:
  `b89835c777fbef531afbdbadda3e07c6ac4da72b6a22178aa8dbc4e9ef29d4bd`
- 2024 `2024_forecast_level.csv`:
  `cf9e31d0e80cc141e47db3c4f6d167e52f66302e8e0085c16d8e9bfa0bb98e12`
- 2025 `2025_forecast_level.csv`:
  `6d2d8aaf95a549b1cc6841f23d49b07c3d9f9d38c1e7ee1be6242cced34d085a`

The repository workflow independently reproduces this experiment from the historical
artifacts and remains the canonical automated path.

## Scientific conclusion

**Market anchoring is a real architecture improvement over V1's unanchored all-call
directions, but LevLine V1 has not yet shown useful residual information after the
market is included.**

The next model must therefore earn incremental signal from better football inputs
(dynamic role, NGS efficiency, matchup state, availability/workload uncertainty)
rather than merely recalibrating the existing V1 disagreement.
