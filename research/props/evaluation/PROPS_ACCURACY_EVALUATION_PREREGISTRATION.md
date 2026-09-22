# LevLine Props Accuracy Evaluation — Preregistration

Status: **FROZEN BEFORE EMPIRICAL OUTCOME INSPECTION**  
Evaluation contract version: `levline-props-eval-v1.0`  
Frozen model branch: `research/props-integration`  
Frozen integration merge SHA: `db5478fd735ef0cad8fd1215e8b1fb6a96a3a21d`  
Evaluation branch: `research/props-accuracy-evaluation`  
Research purpose: empirical validation only; no winner/F-ST changes and no retrospective Props tuning.

## 1. Scientific question

Estimate how accurately the frozen LevLine Props Research Beta predicts offensive player outcomes and probabilities, how well calibrated those probabilities are, whether it improves on point-in-time baselines and sportsbook markets when matched market data exist, and what—if anything—can legitimately be claimed about signal performance.

Software/unit/integration test pass rates are not predictive-accuracy evidence.

## 2. Governance freeze

Completed 2026 outcomes may be used only for evaluation of forecasts that were frozen before kickoff. They may not be used by this project to change architecture, features, hyperparameters, priors, coefficients, shrinkage strengths, simulation settings, calibration, signal rules, or selection thresholds.

No evaluation result may cause this contract to be edited. Any proposed model improvement discovered during analysis must be recorded as a future hypothesis requiring a separately preregistered experiment.

The official LevLine/F-ST winner model is out of scope and must not be modified.

## 3. Two evaluation programs

### A. Prospective 2026 frozen-receipt evaluation — primary current-model evidence

Gold-standard population: immutable `FORECAST_ORIGINAL` receipts produced by the frozen integration system before kickoff, joined only afterward to immutable market-close and grade/result events.

Inclusion requires:
- exact original forecast receipt with valid immutable hash;
- forecast and data-horizon timestamps before kickoff;
- stable game/player identity;
- supported position/market;
- postgame actual result for outcome metrics;
- for market-relative metrics, a genuine timestamped market observation captured before the original forecast;
- for closing/CLV metrics, a genuine separately appended closing observation timestamped before kickoff.

Original forecasts are never rewritten.

All supported original signal states, including `NO SIGNAL`, remain in projection/calibration analyses whenever the required model quantity exists. Signal-performance analyses use only the original signal state and never reclassify observations retrospectively.

### B. Historical rolling-origin reconstruction — secondary structural evidence

Historical evaluation is permitted only when every model input can be reconstructed with information genuinely available before the game.

The current frozen engine contains priors fit through 2025. Therefore those current fitted values may **not** be used to claim leakage-free performance in earlier seasons.

Historical work will be classified as one of:
1. **Leakage-free rolling-origin reconstruction**: every fitted prior/parameter is refit using only data available before the evaluation horizon, with the same structural formula and no outcome-informed tuning.
2. **Structural reconstruction only**: useful for engineering/process diagnostics but not counted as current frozen-model accuracy.
3. **Unavailable**: required point-in-time inputs cannot be reconstructed without future knowledge.

Preferred candidate evaluation seasons are 2024 and 2025, with 2023 allowed only if source coverage supports the identical reconstruction rules. A season enters the leakage-free program only if all required source and prior-horizon checks pass before metrics are calculated.

Historical availability may never be inferred from whether the player ultimately played. Historical route/snap/injury information absent from a trustworthy point-in-time source is marked unavailable or handled only by a fallback that was fixed in advance and could have been used at that time.

## 4. Evaluation unit and deduplication

Canonical observation key:
`(forecast_id, game_id, player_id, prop_type)`.

Only one original forecast per `forecast_id` is allowed. Duplicate immutable-identical rows collapse to one observation; conflicting duplicates are a hard evaluation failure.

Report:
- number of prop forecasts;
- unique players;
- unique games;
- unique weeks;
- number with actual outcomes;
- number with original market benchmark;
- number with closing market;
- number by signal and quality state.

Correlated player props are not treated as independent for uncertainty estimation.

## 5. Outcome definitions

For continuous/count markets, `actual_result` is the official realized player statistic corresponding to the original normalized prop type.

For an Over/Under threshold:
- OVER if actual > original line;
- UNDER if actual < original line;
- PUSH if actual == original line.

For binary TD:
- event = 1 if actual TD count >= 1;
- event = 0 otherwise.

Pushes are retained and counted. They are excluded from two-class Over-vs-Under Brier/log-loss unless otherwise stated, because the two-class realized event is undefined on a push. A three-outcome score may be reported only when the frozen forecast contains explicit push mass.

## 6. Continuous projection metrics

For passing yards, rushing yards, receiving yards, receptions, and passing-TD count where applicable, calculate:
- MAE of model mean;
- RMSE of model mean;
- median absolute error of model mean;
- signed error/bias of model mean;
- mean forecast and mean actual;
- MAE and signed error of LevLine Fair Line separately;
- Pearson correlation as descriptive context only;
- prediction-interval empirical coverage;
- mean/median prediction-interval width.

CRPS and PIT diagnostics are calculated only when the exact frozen forecast distribution or a lossless reproducible representation of it is available from preserved inputs/seed. They will not be approximated from mean/SD solely to manufacture a score.

Prediction-interval calibration is assessed against the interval coverage level stored in the original forecast.

## 7. Probability metrics

At the original sportsbook threshold, and for binary TD events:
- Brier score;
- log loss with probabilities clipped only numerically to ([10^{-12},1-10^{-12}]);
- calibration error;
- reliability table;
- discrimination/resolution summaries when sample size permits.

For non-push O/U outcomes, model probabilities are renormalized over Over/Under only when the original forecast has positive explicit push probability:
[
p^*_{over}=p_{over}/(p_{over}+p_{under})
]
and the same for Under.

Market probability comparisons use the point-in-time no-vig probability at the identical threshold only.

## 8. Calibration plan

Primary fixed probability bins:
- [0.50, 0.55)
- [0.55, 0.60)
- [0.60, 0.65)
- [0.65, 0.70)
- [0.70, 1.00]

These bins apply to the probability assigned to the model-favored side/event.

A fixed-bin row is inferentially reported only with at least 25 observations and at least 10 unique games. Sparse fixed bins remain visible but are labeled descriptive-only.

Adaptive fallback:
- total N >= 250: 5 equal-frequency bins;
- 100 <= N < 250: 3 equal-frequency bins;
- N < 100: no aggregate calibration curve claim; individual probabilities and overall proper scores may still be reported descriptively.

For each supported bin report N, unique games, mean predicted probability, observed frequency, calibration gap, and game-clustered 95% interval for observed frequency.

Overall calibration metrics:
- mean calibration error / calibration-in-the-large;
- expected calibration error using the preregistered applicable bins;
- Brier decomposition when mathematically supported by the sample.

## 9. Market-relative evaluation

Matched original-market observations:
- Fair Line minus original market line;
- absolute error of Fair Line vs realized statistic;
- absolute error of original market line vs realized statistic;
- paired Fair-Line-vs-market absolute-error difference;
- model vs original no-vig market Brier score;
- model vs original no-vig market log loss.

Matched closing observations:
- Fair Line minus closing line;
- absolute error of closing line vs realized statistic;
- paired Fair-Line-vs-closing-line absolute-error difference;
- side-aware threshold CLV;
- same-threshold price CLV where comparable;
- fraction of observations whose close moved in LevLine's indicated direction.

Market comparisons require like-for-like player, prop, threshold, and valid timestamp provenance. No synthetic or guessed sportsbook line is allowed.

Primary paired market inference uses a game-clustered paired bootstrap of the metric difference. Report both the point estimate and 95% interval; do not reduce the result to a significance label.

## 10. Baselines

Baselines obey identical point-in-time rules.

Primary market baselines, when available:
- original consensus market line;
- original consensus no-vig probability;
- closing consensus line/no-vig probability only as an evaluation benchmark, never as a pregame input.

Non-market baselines:
1. trailing-5-game player average for continuous/count statistics;
2. season-to-date player average with no future games;
3. position/league shrinkage baseline using only prior games;
4. simple rolling usage baseline mapped through observed prior efficiency where the required point-in-time inputs exist.

Because recent-window choice is inherently arbitrary, trailing-3 and trailing-8 variants are preregistered sensitivity analyses; all variants must be reported together if calculated. None may be selected after results are seen as “the” winning baseline.

TD probability baselines use prior-only event frequencies with fixed Beta(1,1) smoothing, plus a position/league prior-only shrinkage comparator if source coverage permits.

## 11. Frozen signal evaluation

The evaluator must preserve original signal state exactly:
- `MODEL EDGE`
- `WATCH`
- `NO SIGNAL`

No retrospective edge threshold may create a `MODEL EDGE`.

If the frozen integration emitted zero `MODEL EDGE` observations, the record and ROI are reported as **not measurable / N=0**, not replaced by a backfit threshold.

For original `MODEL EDGE` observations only, the selected side is determined mechanically from original forecast data:
- line markets: side with larger positive model-minus-no-vig probability edge; ties excluded;
- binary TD: TD if model TD probability exceeds original no-vig TD probability, otherwise NO TD if the reverse; ties excluded.

Betting convention: 1.0 unit risked per eligible original `MODEL EDGE` at the original recorded price for the selected side.
- win profit = decimal odds - 1;
- loss = -1;
- push = 0;
- ROI = total net units / number of units risked.

Report wins, losses, pushes, average American/decimal price, break-even probability implied by realized prices, net units, ROI, game-clustered bootstrap interval for ROI when N permits, and Wilson 95% interval for non-push win rate.

ROI is diagnostic only and is never a tuning target.

## 12. Subgroups

Predeclared subgroup dimensions:
- exact prop family;
- position: QB/RB/WR/TE;
- original signal state;
- original data-quality state;
- forecast horizon;
- edge magnitude.

Edge-magnitude bins, computed from absolute original model-minus-market probability edge:
- [0, 0.025)
- [0.025, 0.05)
- [0.05, 0.075)
- [0.075, 0.10)
- [0.10, 1.00]

Fair-line magnitude sensitivity for line markets, absolute Fair-Line-minus-market difference standardized by the model SD when available:
- [0, 0.25)
- [0.25, 0.50)
- [0.50, 1.00)
- [1.00, infinity)

Forecast-horizon bins:
- < 6 hours;
- 6 to < 24 hours;
- 24 to < 48 hours;
- 48+ hours.

Season/week results are descriptive diagnostics only.

## 13. Minimum sample rules

No subgroup receives a strong performance characterization unless it has at least:
- 50 graded forecasts,
- 20 unique games, and
- 3 distinct weeks.

For market-relative paired claims, require at least 50 matched forecasts and 20 unique games.

For betting/ROI language beyond raw descriptive record, require at least 100 eligible `MODEL EDGE` bets and 30 unique games.

Smaller samples are reported numerically with an explicit “insufficient for stable conclusion” label.

Headline current-model conclusions must display N and unique games next to every major estimate.

## 14. Uncertainty

Primary uncertainty method: nonparametric game-clustered bootstrap, resampling games with replacement and retaining all prop observations within sampled games.

Settings:
- 5,000 bootstrap replicates;
- deterministic random seed: `20260917`;
- percentile 95% intervals.

Paired LevLine-vs-market differences are bootstrapped by game on matched pairs.

Binary win-rate intervals use Wilson 95% intervals; exact Clopper-Pearson may be shown as a sensitivity check.

If fewer than 20 unique games exist, bootstrap intervals are labeled unstable and no strong inferential conclusion is drawn.

## 15. Missingness and exclusions

Never impute:
- sportsbook prices;
- closing lines;
- player availability from eventual participation;
- route/snap evidence from final outcomes;
- missing actual results.

Rows excluded from a metric remain in an audit table with a machine-readable exclusion reason.

`NO SIGNAL` rows are not dropped from projection accuracy merely because they were not bettable; they are excluded only when the metric-specific required forecast field is absent.

Unavailable/cancelled/void player props are not treated as wins or losses. If the player has no valid official statistic for the market, the row is excluded from outcome scoring with a recorded reason.

## 16. Multiple-comparison discipline

All preregistered subgroups are reported, not only favorable ones. No “best prop” claim is made from a small subgroup merely because it has the highest point estimate.

Subgroup results are descriptive/heterogeneity analysis. The primary comparison is overall frozen-model performance and matched overall LevLine-vs-market performance.

## 17. Reproducible outputs

The evaluation runner must write:
- evaluation metadata and contract version;
- forecast-level joined evaluation table;
- overall metrics;
- per-prop metrics;
- per-position metrics;
- per-signal metrics;
- per-quality metrics;
- calibration tables;
- market-comparison tables;
- betting/signal diagnostics;
- sample counts and exclusion counts;
- uncertainty intervals;
- source-provenance/fingerprint fields.

No credentials or proprietary raw sportsbook payloads are committed.

## 18. Claim language

Permitted claim categories:
- projection error estimates with N/uncertainty;
- probability-score/calibration estimates with N/uncertainty;
- paired market-relative differences with matched N/uncertainty;
- raw prospective signal record/ROI only when original eligible signals exist.

Not permitted from this evaluation alone:
- claiming profitable betting skill from tiny samples;
- claiming market superiority without matched sportsbook evidence;
- claiming historical current-model accuracy from reconstructions that use future-fitted priors;
- claiming calibration from synthetic tests;
- treating integration/unit-test success as predictive accuracy.

The scientifically valid final conclusion may be positive, neutral, negative, mixed by family, or insufficient-data.
