# Evaluation Protocol

Status: FROZEN BEFORE Q1/Q2/Q3 RESULTS

## 1. Evaluation philosophy

Probability quality is primary. ATS win rate and realized return are secondary consequences of a probability model and cannot select Q1/Q2/Q3, hyperparameters, calibration, blend weights or selective thresholds.

All comparisons are paired on the same eligible outer rows wherever mathematically possible.

## 2. Outer development panel

Outer seasons: exactly 2022, 2023, 2024, 2025.

These are non-pristine development seasons. Report every outer season separately and pooled. No positive pooled result may hide a materially contradictory season pattern.

## 3. Distribution/probability metrics

Required:

- cover Brier score;
- binary cover log loss on no-push/decisive representation where defined;
- multinomial cover/push/loss log loss;
- discrete margin negative log likelihood for Q2;
- ranked probability score / discrete CRPS-equivalent for the full integer-margin PMF;
- calibration intercept and slope;
- reliability curves with predeclared equal-frequency bins (10 bins when N permits, otherwise report the largest bin count with >=20 observations/bin); bins are visualization only, not model-selection objects;
- calibration by outer season;
- calibration by frozen spread/key-number buckets;
- empirical versus predicted push probability.

For calibration regression, decisive cover probabilities are evaluated after conditioning out pushes when required: `p_decisive_home_cover = p_cover/(p_cover+p_loss)` when the denominator is positive.

## 4. Spread/location metrics

Required:

- median absolute error;
- MAE;
- RMSE;
- Q1 pinball loss at 10/21, 1/2 and 11/21;
- pooled three-quantile pinball score;
- market-relative residual error;
- fair-line/median error where a model fair line is defined.

Continuous-margin accuracy remains secondary to probability scoring for Q2/Q3, but must be reported to detect pathological probability improvements obtained by distorting the margin model.

## 5. ATS reporting

For every frozen evaluated decision set report:

- N eligible games;
- N wagers/decisions;
- wins;
- losses;
- pushes;
- hit rate excluding pushes;
- exact two-sided binomial 95% interval on decisive win rate;
- model expected edge/probability advantage under the applicable price contract;
- realized return and ROI only when a valid price convention/source is explicitly identified;
- outer-season concentration of the result.

No raw percentage may be called validated without uncertainty and N.

## 6. Selective evaluation — frozen subsets only

Exactly these subsets are authorized:

### A. All eligible games

No abstention.

### B. Positive-EV at quoted price

Only where an auditable two-sided or otherwise valid actual spread price exists at the declared market horizon. A game is selected if the model's best-side EV is strictly >0 under the frozen economics contract. No positive-EV subset is reported from fabricated price.

### C. Top fixed 20%

If actual prices exist, rank by maximum best-side model EV. Without actual spread price, rank by `probability_advantage`, defined as the larger of:

- model home-cover probability minus the corresponding M1 market-distribution home-cover probability;
- model home-loss/away-cover probability minus the corresponding M1 market-distribution home-loss probability.

Select the corresponding side. Rank within each outer season, not globally, to prevent one season from monopolizing the subset. Include the ceiling of 20% of eligible rows, with deterministic game-ID tie break.

### D. Top fixed 10%

Same ranking/side rule as top 20%, using the ceiling of 10% within each outer season.

No 1/2/3/4/5% or alternate cutoff search is allowed after seeing results.

### Standard -110 sensitivity

If actual historical spread price is absent, a standardized -110 economic sensitivity may be reported on the frozen decisions, clearly labeled **NOT OBSERVED QUOTED-PRICE ROI**. It cannot define the primary positive-EV subset and cannot select a model.

## 7. Key-number validation — frozen buckets

Evaluate quoted market-implied home margin `S=-L` by absolute key neighborhood. The following diagnostic buckets are frozen:

- 2.5 / 3.0 / 3.5;
- 5.5 / 6.0 / 6.5;
- 6.5 / 7.0 / 7.5;
- 9.5 / 10.0 / 10.5;
- 13.5 / 14.0 / 14.5.

The 6.5 line intentionally appears in both the 6 and 7 neighborhoods; these are overlapping mechanism diagnostics and must never be summed as mutually exclusive categories.

Within each bucket report:

- N;
- predicted versus empirical push probability for the whole-number key;
- cover calibration;
- distribution/log score;
- model probability change when crossing the key (e.g. 2.5 to 3 to 3.5) where the PMF allows synthetic alternate-line translation;
- price-versus-number diagnostics only when actual side price exists.

Do not invent new key buckets after results.

## 8. Primary null comparisons

Required paired comparisons:

- Q1 versus M0 and Q1-M2;
- Q2/M1/M2 versus current/fixed-Normal-style bridge where reproducibly available;
- Q2 full versus M2;
- Q3 versus Q2 full and M2;
- selected Q2/Q3 blend versus Q2 and Q3 components.

A football-incremental claim requires beating the corresponding market-only calibrated null, not just the raw quoted-line null.

## 9. Proper-score model-selection hierarchy

- Q1 hyperparameter: pooled inner OOF pinball loss, season-equal.
- Q2 family/key shrinkage: pooled inner OOF discrete margin NLL, season-equal.
- Q3 learner: pooled inner OOF multinomial log loss, season-equal.
- Q3 temperature: pooled prior inner OOF multinomial log loss.
- Q2/Q3 blend weight: pooled prior inner OOF multinomial log loss.

Outer ATS hit rate, ROI and selective subsets cannot alter any choice.

## 10. Uncertainty

Required:

### Exact/binomial

For ATS decisive wins, use exact Clopper-Pearson 95% intervals and an exact/binomial test against relevant descriptive nulls where useful. Do not confuse >50% with profitability at a priced market.

### Block bootstrap

For paired metric differences and selective ATS/economic summaries, perform a season/week block bootstrap preserving all games within a `(season, week)` block. Use at least 5,000 bootstrap replicates with deterministic seed `20260923` in the final Phase-2 evidence package.

Report median/mean paired difference and 95% percentile interval. If the metric is undefined for a bootstrap sample (e.g. no priced wagers), report the valid-replicate count rather than silently filling zero.

### Season robustness

Always report per-season metric deltas. A pooled effect driven nearly entirely by one season is labeled concentration risk, not stable evidence.

## 11. Power context

Under an idealized independent Bernoulli model with one-sided alpha=.05 and 80% power:

Against 50%:

- detect 53%: about 1,734 decisive bets;
- detect 54%: about 979;
- detect 55%: about 620.

Against standard -110 break-even `11/21 = 52.38095%`:

- detect 53%: about 40,243 decisive bets;
- detect 54%: about 5,879;
- detect 55%: about 2,248.

For only 272 independent games, approximate exact-binomial power against the -110 null is roughly:

- true 53%: 6.7%;
- true 54%: 12.1%;
- true 55%: 20.0%.

A 22-18 record (55% on 40 decisive bets) has a very wide 95% exact interval (approximately 38.5%–70.7%). It is not validation.

These are optimistic independence calculations; week/season dependence and selective betting reduce effective information. This is why Phase 3 can only grant `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`, never historical production promotion.

## 12. CLV

CLV is reported only if the candidate decision snapshot legitimately precedes a separately captured later market snapshot with explicit timestamp/provenance. A historical schedule line cannot serve simultaneously as both decision line and later close.

CLV is a market-information diagnostic, not a substitute for outcome probability calibration.

## 13. Missing metrics

If a metric cannot be computed under the source contract (e.g. actual-price ROI without price), mark it `NOT_AVAILABLE_SOURCE_BOUNDARY`. Do not impute a favorable convention.

## 14. Phase-3 classification standard

Phase 3 will synthesize Q1-Q3 as one of:

- `REJECTED` — primary proper-score evidence does not support the mechanism or is materially worse than the relevant market null;
- `INCONCLUSIVE` — estimates/uncertainty are insufficient, contradictory or too concentrated to support a prospective claim;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` — preregistered proper-score/calibration evidence is directionally consistent, not dependent on outcome mining, and survives relevant market-only nulls strongly enough to justify a future shadow test.

No historical result can skip the prospective gate.