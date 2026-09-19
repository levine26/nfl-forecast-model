# LevLine Props 2.0 — Prop-Family Market-Prior Residual Experiment

Status: **FROZEN BEFORE EMPIRICAL EVALUATION**  
Created: 2026-09-18  
Branch: `research/props-v2-market-prior-by-prop`  
Parent research boundary: `research/props/v2/PROPS_V2_RESEARCH_PREREGISTRATION.md`

## Question

Does allowing each prop family to have its own strongly shrunken market-residual calibration
improve chronology-held-out direction and probability quality relative to the already-tested
single global market-residual model?

This is a low-dimensional calibration experiment, not a selective betting strategy.

## Fixed model

For each of the five frozen prop families separately:

```
logit(P_over_prop)
  = logit(P_over_market)
  + intercept_prop
  + beta_prop * [logit(P_over_v1) - logit(P_over_market)]
```

The sportsbook coefficient is fixed at 1.0.

Frozen regularization:
- residual-beta L2 = 10.0
- intercept L2 = 1.0
- no hyperparameter search

Minimum decided training sample per family:
- **50 rows**

If a family has fewer than 50 decided training rows in a block, it is not scored in that block.
No global fallback is substituted after seeing outcomes.

Prop families are fixed:
- passing_yards
- passing_tds
- rushing_yards
- receiving_yards
- receptions

## Why family-specific calibration is scientifically plausible

The markets represent different count/yardage processes, price conventions, distribution shapes,
and V1 component models. Pooling all markets forces one residual coefficient and one intercept to
describe structurally different data-generating processes.

This hypothesis is frozen before its family-specific chronological result is evaluated.

## Chronology

### Fixed anchor
Train:
- 2023 Weeks 1–9 only.

Evaluate without refitting:
- 2023 Weeks 10–18
- all qualified 2024 rows
- all qualified 2025 rows

### Rolling origin
- evaluate 2024 using only 2023 for training
- evaluate 2025 using only 2023–2024 for training

No completed 2026 outcome is permitted.

## Comparators

On identical rows, report:
1. frozen V1 direction;
2. sportsbook no-vig price direction, abstaining at exactly 0.50;
3. the original **global** market-prior residual architecture;
4. the prop-family market-prior residual challenger.

The global comparator must use the same fixed L2 values and chronology.

## Metrics

Primary:
- all-call prop-family challenger directional accuracy
- prop-family challenger minus global residual accuracy
- game-clustered 95% CI for that paired difference

Secondary:
- challenger minus V1
- sportsbook price-direction accuracy on informative rows
- challenger accuracy on the same informative rows
- Brier score
- log loss
- by-family accuracy
- fitted intercept and residual beta by family

Bootstrap:
- cluster = game_id
- deterministic seed = 20260918
- 5,000 replicates in automated evaluation

## Preregistered development decision

The family-specific architecture is considered **development-improving** only if:
1. fixed-anchor challenger-minus-global point estimate > 0;
2. rolling-origin 2024 challenger-minus-global point estimate > 0; and
3. aggregate rolling-origin 2024–2025 challenger Brier score is no worse than the global model.

The confidence interval is reported but is not required to exclude zero at this development stage
because the model has only two parameters per family and this sample is limited. This decision does
not authorize production.

No post-hoc family exclusion, betting threshold, or coefficient clipping may be introduced after
results are observed.

## Promotion boundary

2023–2025 has already informed the Props 2.0 research program. Even a positive result is
retrospective development evidence only. Production promotion requires untouched prospective
immutable forecasts.
