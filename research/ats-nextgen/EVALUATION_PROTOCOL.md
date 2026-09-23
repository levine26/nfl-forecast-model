# ATS Next-Generation Evaluation Protocol

## 1. Evaluation hierarchy

The program evaluates **probability/distribution quality before realized betting outcomes**.

A candidate may not be selected because of ATS hit rate or ROI if it fails its primary proper-loss objective.

## 2. Required probability/distribution metrics

On exact common eligible rows report:

- cover Brier score;
- cover log loss;
- multinomial cover/push/loss log loss where a three-outcome vector exists;
- calibration intercept/slope for cover probability where estimable;
- reliability tables/curves using fixed bins `{[0,.1),...,[.9,1]}` plus sample counts;
- ranked probability score / discrete CRPS for Q2;
- empirical push calibration overall and by fixed key-number bucket;
- probability-mass normalization and boundary-mass diagnostics.

## 3. Quantile/location metrics

Q1 must report:

- pinball loss at τ=10/21, 1/2, 11/21;
- empirical quantile coverage;
- median absolute error;
- MAE;
- RMSE;
- market-relative residual error.

Q2 additionally reports expected/median margin error for interpretability, but those do not replace full-distribution scores.

## 4. ATS metrics

Report, without using them as the sole selector:

- eligible ATS decisions;
- wins;
- losses;
- pushes;
- hit rate excluding pushes;
- exact/binomial confidence interval for non-push hit rate;
- expected edge/EV where a qualified quote price exists;
- realized return where a qualified quote price exists;
- standardized `REFERENCE_MINUS110` return only as a clearly labeled sensitivity when historical side price is absent;
- CLV only if a genuine later same-market snapshot exists. Model-vs-close disagreement is **not** labeled CLV.

## 5. Market null hierarchy

Every candidate report must include the relevant exact-row market baselines:

- **M0:** quoted spread with no LevLine adjustment;
- **M1:** market-derived distribution using no football information;
- **M2:** market + simple line-level calibration only, no football information;
- Q1/Q2/Q3 and authorized Q2/Q3 blend.

Incremental-football claims are always stated relative to the corresponding market null.

## 6. Fixed key-number analyses

Use these non-exclusive quoted-spread buckets, based on `abs(L)`:

- K3: `{2.5, 3.0, 3.5}`;
- K6: `{5.5, 6.0, 6.5}`;
- K7: `{6.5, 7.0, 7.5}`;
- K10: `{9.5, 10.0, 10.5}`;
- K14: `{13.5, 14.0, 14.5}`.

The overlap at 6.5 is intentional because 6.5 is adjacent to both 6 and 7. Buckets are never summed as disjoint populations.

For each report:

- N;
- predicted and empirical push probability where whole-number lines are present;
- cover calibration;
- distribution/proper score;
- line-crossing direction/value when an eligible alternate quote exists;
- price-vs-number diagnostics only when actual side price exists.

No new key bucket may be created after seeing candidate results.

## 7. Fixed market-total / favorite-size analyses

Use training-independent reporting buckets:

Favorite size `abs(L)`:

- `<3`;
- `3–<7`;
- `7–<10`;
- `10–<14`;
- `>=14`.

Market total:

- `<42`;
- `42–<45`;
- `45–<48`;
- `>=48`.

These match prior LevLine diagnostics closely enough to preserve interpretability and prevent post-result bucket search.

## 8. Selective ATS evaluation

Abstention is allowed, but threshold fishing is prohibited.

Report exactly:

1. all eligible games;
2. qualified positive-EV games when real quoted side price exists;
3. top fixed 20% of games by pre-outcome model edge/EV score;
4. top fixed 10% by the same score.

Historical data without real side price uses a labeled `REFERENCE_MINUS110` score for selectivity only. It may not be presented as actual quoted-price profitability.

For every selective subset report:

- N, wins, losses, pushes, hit rate;
- mean predicted edge;
- realized return under the exact available price convention;
- calibration/proper score;
- season share and maximum single-season concentration;
- week-block uncertainty.

Do not search 1%, 2%, 5%, alternative cutoffs or dollar thresholds after results.

## 9. Uncertainty

Required:

- exact Clopper–Pearson/binomial interval for simple non-push hit-rate summaries;
- season+week block bootstrap for paired metric deltas and selected-subset uncertainty, at least 10,000 resamples in final Phase-2 evidence;
- paired differences on exact common rows;
- per-season point estimates;
- report of concentration by season/week.

## 10. Power reality check

Pre-result one-sided exact-binomial planning calculation, alpha 0.05 and power 0.80:

### Detecting against 50%

- 53% requires approximately **1,734** independent decisions;
- 54% requires approximately **979**;
- 55% requires approximately **620**.

### Detecting against standard -110 no-push break-even 52.38095%

- 53% requires approximately **40,243**;
- 54% requires approximately **5,879**;
- 55% requires approximately **2,248**.

These calculations ignore game dependence and selection effects, so they are optimistic for selective ATS subsets.

One 272-game NFL season is therefore incapable of tightly validating a modest ATS edge. For illustration, with 272 trials an observed rate near 53% has an exact 95% interval roughly spanning the high-40s to high-50s. A raw 55% on 40 games is descriptive, not validated.

## 11. Candidate interpretation gates

Phase 3 may classify a candidate `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` only if:

- its primary proper/quantile metric improves on the relevant market null on exact common OOF rows;
- calibration does not show a material systematic failure;
- improvement is not solely one season/week/key bucket;
- no leakage/red-team failure exists;
- the mechanism is consistent with the preregistered model identity.

Because 2022–2025 is non-pristine development evidence, even a strong historical result cannot authorize production.