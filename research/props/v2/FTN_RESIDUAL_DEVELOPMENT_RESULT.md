# LevLine Props 2.0 — FTN Matchup Residual Development Result

Status: **COMPLETED RETROSPECTIVE DEVELOPMENT EXPERIMENT — INCREMENTAL SIGNAL NOT ESTABLISHED**

Experiment contract: `levline-props-v2-ftn-residual-development-v0.1.0`  
Workflow run: `35375528258`  
Evaluation artifact: `10560557089`  
Artifact SHA-256: `bd642ff34cb66621d78e79d1119cfc46324b7073c0e14f880f4041ea73760221`

## Preregistered question

Do strictly lagged, live-capable FTN scheme/matchup features add incremental directional information
beyond a matched sportsbook no-vig prior plus frozen LevLine V1 probability-gap residual model?

## Preregistered decision

**Negative.** The experiment did not satisfy the frozen incremental-signal rule.

The rule required:
1. fixed-anchor FTN-minus-matched-baseline > 0;
2. fixed-anchor game-clustered 95% CI lower bound > 0; and
3. 2024 rolling-origin FTN-minus-matched-baseline > 0.

None of those three conditions was established.

## Fixed-anchor result

Training:
- 2023 Weeks 1–9 only.

Evaluation:
- 2023 Weeks 10–18 plus qualified 2024–2025 rows.

Results:
- decided props: **4,273**
- unique games: **197**
- FTN challenger accuracy: **52.21%**
- matched market+V1 residual accuracy: **52.23%**
- frozen V1 accuracy: **51.00%**
- sportsbook price-direction accuracy on informative rows: **54.51%**
- FTN minus matched baseline: **-0.02 percentage points**
- game-clustered 95% CI for FTN minus baseline: **-1.25 to +1.24 pp**
- FTN accuracy game-clustered 95% CI: **50.91%–53.56%**
- FTN Brier: **0.25331**
- matched residual Brier: **0.24768**
- sportsbook Brier: **0.24723**
- V1 Brier: **0.29743**
- FTN log loss: **0.70009**
- matched residual log loss: **0.68842**
- sportsbook log loss: **0.68752**
- V1 log loss: **0.88569**

Directional accuracy was effectively identical to the matched residual baseline, while FTN probability
quality was materially worse by both Brier score and log loss.

## Rolling-origin 2024

Training:
- qualified 2023 rows only.

Evaluation:
- qualified 2024 rows.

Results:
- decided props: **3,703**
- unique games: **137**
- FTN challenger accuracy: **51.80%**
- matched market+V1 residual accuracy: **52.07%**
- frozen V1 accuracy: **50.81%**
- sportsbook price-direction accuracy on informative rows: **55.00%**
- FTN minus matched baseline: **-0.27 pp**
- game-clustered 95% CI for FTN minus baseline: **-1.67 to +1.25 pp**
- FTN accuracy game-clustered 95% CI: **50.04%–53.54%**
- FTN Brier: **0.25349**
- matched residual Brier: **0.24773**
- sportsbook Brier: **0.24611**
- V1 Brier: **0.28898**

This is the largest reasonably covered single-season block, and FTN did not improve the matched
residual architecture.

## Rolling-origin 2025 sensitivity

Training:
- qualified 2023–2024 rows.

Evaluation:
- qualified 2025 genuine-OPEN rows.

Results:
- decided props: **413**
- unique games: **16**
- FTN challenger accuracy: **54.96%**
- matched market+V1 residual accuracy: **59.56%**
- frozen V1 accuracy: **54.96%**
- sportsbook price-direction accuracy on informative rows: **57.00%**
- FTN minus matched baseline: **-4.60 pp**
- game-clustered 95% CI for FTN minus baseline: **-10.30 to +0.25 pp**
- FTN Brier: **0.24417**
- matched residual Brier: **0.24239**

The 2025 sample is too small and incomplete for a season-wide standalone conclusion, but it does
not rescue the FTN hypothesis.

## Coverage

- frozen V1 forecast rows: **5,682**
- rows with some strictly lagged FTN state: **5,682 (100%)**
- resolved-opponent coverage: **99.86%**
- target-week FTN rows used: **0**
- completed 2026 outcomes used for tuning: **0**
- live source capable: **true**

Coverage therefore does not explain the null result.

## Descriptive subgroups

Some prop-family point estimates were positive, including 2024 rushing yards
(+1.11 pp versus matched residual) and 2024 passing yards (+0.75 pp). Others were negative,
including 2024 passing TDs (-1.53 pp) and receptions (-1.37 pp).

These are **descriptive only**. They were not the preregistered primary decision and are not eligible
for post-hoc selection or a selective production rule.

## Scientific conclusion

The tested FTN feature set/model form **does not demonstrate stable incremental information beyond
the matched market+V1 residual architecture**.

The FTN state builder remains useful research infrastructure because it is strictly lagged,
high-coverage, and live-capable. However, the current residual specification should not enter the
frozen prospective Props 2.0 candidate based on this evidence.

No production promotion is authorized.
