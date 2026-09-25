# LevLine ATS Fair-Line Policy Audit — Frozen Preregistration

**Candidate / policy ID:** `ATS-FAIR-LINE-POLICY-V1`  
**Status:** FROZEN BEFORE HISTORICAL EXECUTION  
**Production authorization:** NONE  
**Completed-2026 outcomes permitted:** 0

## 1. Scientific question

Does the existing LevLine independent margin forecast, used exactly as a fair line against the sportsbook spread, identify the correct ATS side often enough to justify treating winner selection and spread selection as separate first-class outputs?

This is the exact decision logic used conceptually by many fair-line handicapping systems: the model can forecast Team A to win while selecting Team B against the spread if the market requires Team A to win by more points than the model's fair margin.

## 2. Frozen decision rule

Repository `spread_line` is expected home margin. The production independent margin model outputs `expected_margin` in the same sign convention.

For every eligible game:

`edge_home = expected_margin - spread_line`

- `edge_home > 0`: select the home team ATS;
- `edge_home < 0`: select the away team ATS;
- exact numerical equality within `1e-12`: no decision.

There is **no fitted edge threshold** in V1. All nonzero model-versus-market disagreements are decisions.

The selected side is independent of the outright win-probability model. No F-ST winner probability is needed to determine the ATS side.

## 3. Historical chronology

Outer target seasons are exactly:

`2022, 2023, 2024, 2025`.

For each outer target season `S`:

1. build the same pregame feature architecture used by the production margin model;
2. fit only on completed seasons `<S`;
3. use the production `fit_weighted_regression` architecture and model templates;
4. choose ensemble weights only from rolling season-held-out validation seasons strictly `<S`;
5. predict target season `S` once;
6. never fit on or tune against target-season ATS results.

The production model's four-year validation-window convention is retained: `validation_start=max(core_start+1, S-4)` and `validation_end=S-1`.

## 4. Eligible rows

A target game is eligible only if all of the following are finite and available under the historical data contract:

- realized home margin;
- sportsbook `spread_line`;
- all features required by the production margin model after its normal fold-local imputers;
- season and week identifiers.

Regular-season rows only where the existing feature/data pipeline supplies them. No completed-2026 game enters any fit, feature evaluation, or metric.

## 5. Primary descriptive ATS result

On all nonzero-edge eligible decisions, report:

- wins;
- losses;
- pushes;
- no-edge rows;
- hit rate excluding pushes;
- exact 95% Clopper-Pearson interval;
- `REFERENCE_MINUS110` net units and ROI-on-risk sensitivity.

The standard `-110` break-even rate `52.38095%` is a reference benchmark only because historical spread-side prices are not qualified.

## 6. Required model-vs-market margin diagnostics

Also report on the same exact outer OOF rows:

- LevLine margin MAE;
- sportsbook spread-center MAE;
- LevLine minus market MAE;
- mean and median absolute model edge;
- Pearson/Spearman relationship between signed model edge and realized ATS residual (`actual_margin - spread_line`).

These diagnose whether the model line contains directional information even when raw side hit rate is noisy.

## 7. Fixed selective diagnostics

Without changing the primary all-game policy, report the already-established ATS protocol subsets:

- top 20% of games by absolute pre-outcome model edge;
- top 10% by absolute pre-outcome model edge.

These are diagnostics only. Do not search alternate percentiles or point thresholds after results are visible.

## 8. Season stability

Report all-game W-L-P and hit rate separately for 2022, 2023, 2024, and 2025.

Also report the share of outer seasons at or above 50% ex-push hit rate.

## 9. Week-block uncertainty

Use 10,000 season-stratified NFL-week block bootstrap resamples with seed `20260925`.

For the all-game policy report:

- 95% percentile interval for hit rate;
- bootstrap probability hit rate exceeds 50%;
- bootstrap probability hit rate exceeds the `52.38095%` reference break-even rate.

No alternative bootstrap or seed may be substituted after results are visible.

## 10. Frozen interpretation gate

Classify the policy as `HISTORICALLY_INTERESTING` only if all hold:

1. aggregate ex-push hit rate is strictly above `52.38095%`;
2. bootstrap probability hit rate >50% is at least `0.80`;
3. at least 3 of 4 outer seasons are at or above 50% ex-push;
4. the result is not produced by any 2026 outcome or target-season fit contamination;
5. all exact-row and chronology checks pass.

Otherwise classify `NOT_ESTABLISHED`.

This classification does not authorize production wagering claims. The 2022–2025 sample is development/non-pristine evidence.

## 11. Explicit prohibitions

After this freeze, do not:

- add or tune an edge threshold;
- select only favorites or underdogs;
- choose different thresholds by total, spread size, team, season, or week;
- use F-ST winner agreement as a filter;
- use completed-2026 outcomes;
- change the regression architecture because of the audit result;
- optimize on the top-10% or top-20% diagnostic subsets;
- relabel `REFERENCE_MINUS110` as actual historical quoted-price ROI.

## 12. Next phase boundary

The next phase may implement and execute this exact 2022–2025 season-held-out audit. The implementation must be frozen before the result workflow is run.