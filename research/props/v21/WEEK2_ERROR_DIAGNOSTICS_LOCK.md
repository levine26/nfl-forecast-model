# Props 2.1 Week 2 Error Diagnostics — Analysis Lock

## Purpose

This lane is **diagnostic only**. It may describe where the frozen Week 2 Props 2.1 cohort missed, but it may not change model parameters, calibration transforms, signal thresholds, priors, personnel weights, opportunity assumptions, distribution widths, or publication logic.

Week 2 remains evaluation evidence. Any model change motivated by these diagnostics must be specified in a separate preregistered challenger before evaluation on a future holdout.

## Frozen input

Use only `forecast_level.csv` emitted by the frozen prospective evaluator tied to:

- live run `35477049179`
- publication commit `ba723255982c79ffe6072c714dd0ee2c37e1fa34`
- receipt blob `e89cdce268fb10c5107ba6db4087107fb213555f`

Do not regenerate forecasts.

## Primary diagnostic population

For line/probability diagnostics, require all of:

- `graded == True`
- non-null `actual_result`
- non-null `model_mean`
- non-null `fair_line`
- non-null `market_line`
- non-null `model_p_over`
- non-null `market_p_over`

Pushes are included in projection MAE but excluded from binary probability scores.

## Locked descriptive metrics

For each eligible grouping, report:

- N
- model-mean projection MAE
- LevLine Fair Line MAE
- original market line MAE
- primary paired MAE delta = Fair Line MAE minus market MAE
- secondary model-mean MAE delta = model-mean MAE minus market MAE
- non-push N
- model Brier
- market Brier
- paired Brier delta
- model log loss
- market log loss
- paired log-loss delta
- model selected-direction confidence = `max(p_over, 1-p_over)`
- model selected-direction accuracy
- model confidence gap = confidence minus accuracy
- market selected-direction confidence / accuracy / confidence gap

Positive paired deltas mean the corresponding LevLine central estimate was worse than the market. The Fair-Line paired delta is the preregistered primary market-relative projection diagnostic. Positive confidence gap means overconfidence.

## Locked groupings

Run the same descriptive table by:

1. `prop_type`
2. `position`
3. `role_state`
4. `availability_state`
5. `workload_state`
6. `market_liquidity_bucket`
7. `forecast_horizon_bin`

Suppress group rows with fewer than 10 projection observations or fewer than 10 non-push probability observations for the corresponding metric.

## Guardrails

- No optimization.
- No isotonic/Platt/beta calibration fit.
- No threshold search.
- No subgroup exclusion rule may be promoted from this cohort.
- No “best subgroup” may be presented as validated edge.
- No retrospective ROI construction.
- No changes to F-ST or any production winner-model path.

The output is hypothesis-generating evidence for a separately preregistered Week 3+ challenger.
