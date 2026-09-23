# Literature Review

Research date: 2026-09-23

Evidence classes: **1** peer-reviewed; **2** reproducible open source; **3** strong technical practitioner evidence; **4** opaque product/system; **5** speculative hypothesis.

## 1. Quantiles and spread wagering

### Dmochowski (2023), PLOS ONE — class 1

J. P. Dmochowski, *A statistical theory of optimal decision-making in sports betting*, PLOS ONE 18(6), 2023. DOI: https://doi.org/10.1371/journal.pone.0287601 . Reproduction code is linked by the paper at `dmochow/optimal_betting_theory`.

Directly verified findings relevant to LevLine:

- The point-spread problem is naturally written in terms of the conditional outcome distribution.
- The conditional median determines the optimal side when forced to choose a side under symmetric payoff assumptions.
- Lower/upper quantiles are needed to decide whether a wager has positive expected profit.
- For a standard payout ratio `100/110`, the critical quantiles are approximately 0.476 and 0.524.
- The paper explicitly assumes `P(push)=0` by treating the margin continuously for the theory; this is not appropriate as the complete NFL wager model at whole-number spreads.
- Its NFL empirical study spans 2002–2022 and reports that sportsbook spread explains most variation in the estimated conditional median.
- The paper argues for quantile regression because mean regression targets a different statistical functional.

Important caution: the PLOS peer review notes the danger of identifying profitable spread strata after observing sample outcomes. LevLine therefore freezes quantiles, chronology, subsets and selection rules before Q1/Q2/Q3 results.

**Transfer:** Q1 target/loss reformulation and market-as-null. **Do not transfer:** continuous push assumption or post-hoc profitable-bin interpretation.

## 2. NFL margin distributions and exact scores

### Baker & McHale (2013), International Journal of Forecasting — class 1

Rose D. Baker and Ian G. McHale, *Forecasting exact scores in National Football League games*, International Journal of Forecasting 29(1), 122–130. DOI: https://doi.org/10.1016/j.ijforecast.2012.07.002 .

Relevant findings:

- NFL scoring is structurally non-standard because common scoring events generate clustered team scores and margins.
- Their point-process score model uses prior team statistics and/or bookmaker spread/total.
- Genuine out-of-sample forecasts were used.
- Their model was marginally outperformed by the market on game results but competitive for exact-score forecasting.

**Transfer:** exact/discrete score structure is real and market inputs are powerful. **Do not transfer:** exact-score point-process complexity into Q2 V1; the sprint asks first whether a much simpler discrete margin PMF is enough.

### Mohsin & Gebhardt (2022/2024), Journal of Applied Statistics — class 1

Muhammad Mohsin and Albrecht Gebhardt, *A stochastic model for NFL games and point spread assessment*, Journal of Applied Statistics 51(2), 216–229. DOI: https://doi.org/10.1080/02664763.2022.2120973 .

The paper derives a distribution for score difference from a bivariate affine-linear exponential construction, fits NFL data, compares distributional alternatives, and uses model quantiles to assess point spreads.

**Transfer:** margin distributions/quantiles are legitimate modeling objects and Normality should be treated as a hypothesis, not an axiom. **Do not transfer:** the BALE difference distribution as a new primary family; adding it would expand the tournament without evidence that it addresses the key discrete-mass problem better than the bounded Q2 comparison.

## 3. Market efficiency as prior

The NFL forecasting literature repeatedly finds that sportsbook markets are difficult to outperform. Baker & McHale summarize earlier work where the market generally performs at least as well as statistical models for ordinary game outcomes. This agrees with LevLine's own prior evidence: the market beat the independent mean-margin model and prior residual challengers did not establish incremental information.

**Implication:** any ATS architecture must be evaluated as an incremental model around the market, not as an isolated football predictor.

## 4. Key numbers and market microstructure

### Fodor, Onuk & Shank (2026), Finance Research Letters — class 1

Andy Fodor, Cagri Berk Onuk and Corey A. Shank, *Do economically meaningful quote differences convey private information?*, Finance Research Letters, 2026. DOI: https://doi.org/10.1016/j.frl.2026.110193 .

The authors exploit spread crossings at key numbers 3 and 7 as payoff discontinuities. They find large bettor-demand discontinuities but no corresponding discontinuity in realized returns; Bayesian evidence strongly favors no return predictability at the threshold.

**Transfer:** key-number mass has first-order wager economics and must be modeled. **Do not infer:** crossing a key number itself is predictive alpha or evidence of bookmaker private information.

### Historical key-number frequency studies — class 3

Serious practitioner analyses using thousands of NFL games consistently show concentrated exact-margin mass at 3 and 7 and meaningful secondary mass at 6, 10 and 14. These are used only to freeze a *diagnostic/key set*, not to import frequencies or edge claims.

The Phase-2 excess-mass parameters are learned entirely from prior eligible LevLine training history.

## 5. Heteroskedasticity and distributional prediction

### Romano, Patterson & Candès (2019), NeurIPS — class 1 conference evidence

*Conformalized Quantile Regression*, NeurIPS 2019: https://proceedings.neurips.cc/paper/2019/hash/5103c3584b063c431bd1268e9b5e76fb-Abstract.html .

The paper combines quantile regression with conformal prediction to obtain intervals adaptive to heteroskedasticity.

### Chernozhukov, Wüthrich & Zhu (2021), PNAS — class 1

*Distributional conformal prediction*, PNAS 118(48), e2107794118. DOI: https://doi.org/10.1073/pnas.2107794118 .

The paper constructs prediction intervals from conditional-distribution estimators and specifically addresses heteroskedasticity and time-series settings.

**Transfer:** modeling only a constant residual sigma is statistically restrictive; conditional distribution/scale is scientifically justified. **Decision:** conformal methods are not a Phase-2 primary betting head because the primary estimand is calibrated discrete cover/push/loss probability rather than interval coverage. They are reserved for later uncertainty diagnostics if Q1/Q2 survive.

## 6. Conditional variance hypotheses

The external literature supports treating heteroskedasticity as a general possibility, while NFL score/margin research supports nonstandard distributional structure. It does **not** establish that every candidate variance feature listed in the motivating prompt is independently predictive after the market.

Therefore V1 freezes a deliberately compact variance contract:

- absolute market-implied margin `|S|`;
- market total;
- one interaction `|S| x centered_total`.

Pace, explosiveness, QB uncertainty, injury state, OL continuity, weather and season/week regime remain plausible mechanisms but are not added to V1 conditional scale without a separate PIT reconstruction/preregistration. This prevents an interaction/variance-feature fishing expedition.

## 7. Direct ATS probability estimation

Binary logistic regression, multinomial logistic regression and gradient boosting are standard probability estimators. Direct ATS classification targets the actual decision boundary rather than reconstructing it from mean scores. But flexible learners require calibration and chronology discipline.

The open-source `ShamgarBN/nfl-bet-engine` provides an implementation example combining score simulation and direct ATS classification, but its reported betting performance is not treated as peer-reviewed evidence and its implementation has methodological limitations documented in `OPEN_SOURCE_MODEL_REVIEW.md`.

**Decision:** Q3 uses multinomial cover/push/loss modeling with a simple regularized logistic reference and exactly one shallow XGBoost challenger; no unrestricted classifier tournament.

## 8. Price, vig and pushes

The PLOS theory's `.476/.524` formulation assumes a standard commission and zero push mass. Real spread prices vary and whole-number NFL spreads push. Accordingly, the ATS economics contract derives break-even from actual American odds and computes EV using separate win/loss/push probabilities.

When historical side price is absent, LevLine will not manufacture it. Standard -110 calculations are sensitivity analyses only.

## 9. Literature-driven Phase-1 decisions

Accepted into V1:

- quantile residual estimation around the quoted market;
- discrete integer margin PMF;
- explicit push probability;
- key-number excess mass;
- bounded heavy-tail base comparison;
- conditional scale from spread/total state;
- direct cover/push/loss probability head;
- proper-score calibration/selection;
- market-first nulls;
- future prospective confirmation requirement.

Excluded/deferred before results:

- BALE as an extra primary family;
- arbitrary score-process simulation complexity;
- unrestricted mixtures;
- conformal method as a fourth candidate;
- broad variance-feature search;
- key-crossing alpha assumption;
- historical ROI threshold optimization.

This review justifies testing the ATS formulation; it does not predict that it will beat the market.