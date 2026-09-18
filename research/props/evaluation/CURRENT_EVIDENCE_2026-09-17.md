# LevLine Props Accuracy — Current Evidence

Status: **EMPIRICAL EVIDENCE AUDIT COMPLETE; PREDICTIVE SAMPLE NOT YET AVAILABLE IN REPOSITORY**
Evaluation contract: levline-props-eval-v1.0
Frozen model: research/props-integration@db5478fd735ef0cad8fd1215e8b1fb6a96a3a21d
Preregistration: research/props/evaluation/PROPS_ACCURACY_EVALUATION_PREREGISTRATION.md

## Plain-English result

The scientifically defensible answer today is **LevLine Props' real predictive accuracy is not yet measurable from the immutable evidence available in this repository**.

The evaluated research/props-integration branch contains the complete research-beta forecasting, market, publication, immutable-history, closing-market, and grading machinery, but it does not contain a committed real prospective forecast ledger, closing-market ledger, or grade ledger. The source audit therefore yields **N=0 graded frozen real forecasts**. Synthetic fixtures and software tests were deliberately excluded from predictive-accuracy calculations.

This is not a finding that the model is inaccurate. It is a finding that there is not yet an admissible empirical sample from which to estimate accuracy.

## Required questions

- **How accurate are its Fair Lines?** Not yet empirically measurable. There are zero graded immutable real forecast receipts in the evaluated repository evidence.
- **How well calibrated are its probabilities?** Not yet empirically measurable. Brier score, log loss, reliability, ECE, PIT, and calibration curves require realized frozen forecasts.
- **How does it compare with sportsbook markets?** Not yet measurable. The repository does not contain a matched graded set of real point-in-time player-prop markets.
- **What is the MODEL EDGE record?** Not measurable; N=0 eligible real MODEL EDGE bets in the evaluated history. In addition, the frozen integrated coordinator currently emits WATCH for valid forecasts and NO SIGNAL otherwise; it does not retrospectively turn numerical disagreement into MODEL EDGE.
- **What is its ROI?** Not measurable.
- **Does it demonstrate positive CLV?** Not measurable.
- **Which prop families look strongest and weakest?** No empirical ranking is supportable.
- **How large is the sample?** 0 committed immutable real forecast originals, 0 committed close events, and 0 committed grades were available at the audited paths on research/props-integration.
- **How uncertain are these conclusions?** Predictive performance is essentially unidentified at N=0. No confidence interval around accuracy is meaningful.
- **What can we currently claim?** The Props system has research-governance, point-in-time, simulation, market-comparison, immutable-receipt, closing-overlay, grading, and evaluation infrastructure designed to support a defensible prospective accuracy study.
- **What can we NOT currently claim?** Any empirical hit rate, Fair-Line MAE, calibration quality, sportsbook superiority, positive CLV, profitable ROI, or strongest/weakest prop family.

## Evidence inventory

The following expected real-evidence paths were queried on research/props-integration after the evaluation contract was preregistered:

| Evidence | Repository path | Audited state |
| --- | --- | --- |
| Prospective forecasts | outputs/props/forecasts.json | Not committed / unavailable |
| Public Props payload | outputs/props/public_props.json | Not committed / unavailable |
| Immutable originals | outputs/props/history/forecast_originals.jsonl | Not committed / unavailable |
| Closing market events | outputs/props/history/market_closes.jsonl | Not committed / unavailable |
| Result/grade events | outputs/props/history/grades.jsonl | Not committed / unavailable |

This means the empirical evaluation sample from accessible repository history is:

- prop forecasts: **0**
- unique players: **0**
- unique games: **0**
- unique weeks: **0**
- graded forecasts: **0**
- matched original-market observations: **0**
- matched closing-market observations: **0**
- eligible MODEL EDGE bets: **0**

No missing sportsbook line, close, result, player availability, or route evidence was imputed.

## What the software tests do and do not prove

The integrated branch has extensive deterministic unit/integration validation, including coherent football accounting, leakage guards, immutable history behavior, market-time firewalls, and publication contracts. Those tests demonstrate implementation correctness relative to the specified contracts.

They are **not observations of future NFL player outcomes** and therefore count as **zero predictive-accuracy evidence** in this evaluation.

## Frozen signal-state implication

The integrated forecast constructor currently assigns WATCH when the forecast/market/data-quality path is valid, otherwise NO SIGNAL.

The product schema allows MODEL EDGE, and fixture tests exercise that display state, but the current integrated coordinator does not create MODEL EDGE by optimizing a numerical threshold. Therefore this evaluation does not invent one after observing outcomes. Until a separately preregistered prospective signal rule exists and produces original MODEL EDGE receipts, MODEL EDGE betting record and ROI remain N=0/not measurable.

## Historical rolling-origin conclusion

A direct historical replay of the current frozen 2026 model would be scientifically invalid because current efficiency/scoring priors are fit through 2025. Using those values to forecast 2024 or earlier would leak future seasons.

The repository does contain strong strictly lagged PBP reconstruction machinery and can refit many structural priors using an earlier training horizon. However, the default source loader obtains a season roster rather than a validated week-specific historical roster snapshot, route data are deliberately absent by default, and the qualified timestamped primary-QB depth-chart resolver is documented for 2025+ only. Historical availability also must not be inferred from eventual participation.

Accordingly, no historical replay was admitted into headline current-model accuracy. A structural replay that substitutes later roster knowledge or eventual participation would create a larger number but weaker science; the preregistration explicitly forbids that.

See research/props/evaluation/HISTORICAL_RECONSTRUCTION_AUDIT.md.

## Evaluation framework now implemented

The research branch adds:

- research/props/evaluation/PROPS_ACCURACY_EVALUATION_PREREGISTRATION.md
- src/nfl_forecast/props_evaluation.py
- scripts/evaluate_props_accuracy.py
- tests/test_props_evaluation.py

When immutable real receipts accumulate, the evaluator calculates:

- mean/Fair-Line MAE, RMSE, median absolute error, bias, interval coverage and width;
- Brier score, log loss, reliability/calibration bins and ECE;
- matched LevLine-vs-market and LevLine-vs-close paired errors;
- game-clustered bootstrap uncertainty;
- threshold CLV;
- price-aware 1-unit-risk MODEL EDGE record and ROI using only original signal states;
- per-prop, position, signal, data-quality, edge-bin and horizon subgroup results;
- sample counts and machine-readable exclusion reasons.

CRPS and PIT are intentionally withheld unless the exact frozen forecast distribution is preserved or losslessly reproducible. They are not fabricated from a normal approximation.

## Current scientific conclusion

**There is presently no defensible empirical basis to describe LevLine Props as excellent, market-level, miscalibrated, profitable, or unprofitable.**

The correct current state is: **research-beta engine built; evaluation protocol frozen; real prospective evidence sample not yet available in repository history.**

The next genuinely informative observation is not another synthetic test. It is the first immutable pre-kickoff real forecast receipt, followed after the game by a genuine close and official result, repeated prospectively without changing the model in response to evaluation outcomes.
