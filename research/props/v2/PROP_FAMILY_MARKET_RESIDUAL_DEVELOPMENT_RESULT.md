# LevLine Props 2.0 — Prop-Family Market-Residual Development Result

Status: **RETROSPECTIVE DEVELOPMENT EVIDENCE — PREREGISTERED GATE FAILED**  
Workflow: `35376287018`  
Artifact: `levline-props-v2-market-prior-by-prop`  
Production promotion authorized: **NO**

## Frozen question

Does replacing the pooled global market-residual calibration with separate two-parameter
calibrations for each frozen prop family improve the already-established global market-residual
challenger?

The sportsbook logit coefficient remained fixed at 1.0. Each family was allowed only an intercept
and a shrunk LevLine-minus-market residual coefficient. The comparison used the same exact frozen
V1 historical receipts and the same eligible prop families.

## Preregistered decision rule

Development improvement required all three conditions:

1. fixed-anchor family-specific accuracy minus global-residual accuracy > 0;
2. 2024 rolling-origin family-specific accuracy minus global-residual accuracy > 0; and
3. aggregate rolling-origin family-specific Brier score <= global-residual Brier score.

The experiment failed this gate.

## Fixed-anchor evaluation

- N: **5,030**
- unique games: **197**
- unique players: **306**
- family-specific accuracy: **52.49%**
- global-residual accuracy: **53.60%**
- frozen V1 accuracy: **51.27%**
- family-specific minus global residual: **-1.11 pp**
- game-clustered 95% interval for family-minus-global: **-2.40 to +0.12 pp**
- price-informative sportsbook direction accuracy: **54.86%**
- family-specific accuracy on those informative rows: **53.54%**
- family-specific Brier: **0.24737**
- global-residual Brier: **0.24650**
- market Brier: **0.24626**
- family-specific log loss: **0.68773**
- global-residual log loss: **0.68600**
- market log loss: **0.68552**

## Rolling-origin 2024–2025 evaluation

- N: **4,109**
- unique games: **153**
- unique players: **295**
- family-specific accuracy: **52.74%**
- global-residual accuracy: **53.74%**
- frozen V1 accuracy: **51.23%**
- family-specific minus global residual: **-1.00 pp**
- game-clustered 95% interval for family-minus-global: **-2.19 to +0.17 pp**
- price-informative sportsbook direction accuracy: **55.13%**
- family-specific accuracy on those informative rows: **53.80%**
- family-specific Brier: **0.24672**
- global-residual Brier: **0.24621**
- market Brier: **0.24608**
- family-specific log loss: **0.68644**
- global-residual log loss: **0.68540**
- market log loss: **0.68514**

### 2024

- N: **3,696**
- family-specific accuracy: **52.00%**
- global-residual accuracy: **53.08%**
- family-minus-global: **-1.08 pp**
- family-specific Brier: **0.24721**
- global-residual Brier: **0.24677**

### 2025

The genuine-OPEN 2025 sample remains small and is not treated as season-wide evidence.

- N: **413**
- unique games: **16**
- family-specific accuracy: **59.32%**
- global-residual accuracy: **59.56%**
- family-minus-global: **-0.24 pp**
- family-specific Brier: **0.24230**
- global-residual Brier: **0.24117**

## Scientific disposition

**REJECT PROP-FAMILY-SPECIFIC MARKET CALIBRATION AS A REPLACEMENT FOR THE GLOBAL RESIDUAL.**

The more granular model is worse on the preregistered aggregate comparisons and also worsens proper
probability scores. Individual family diagnostics must not be used to rescue or redefine this
experiment after seeing the outcomes.

This null result is permanent evidence. Any future family-specific model must have a new scientific
rationale, a new frozen contract, and a new untouched evaluation path. No completed 2026 outcome may
be used to resurrect this specification.
