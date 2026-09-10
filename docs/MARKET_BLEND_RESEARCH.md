# Market blend research — Sunday Signal / LevLine

## Purpose

LevLine should use the betting market as an external information source without becoming a market clone. The market is unusually strong in the NFL because it aggregates injuries, quarterback news, weather, matchup opinions and professional trading. The right question is therefore not whether to use the market, but how to measure whether football-only PURE adds information that survives after the market is known, and how to use that information without erasing real independent signal.

**Production status:** beginning with version `0.9.0-fst`, the official winner probability is frozen `F-ST-01-FROZEN-2026`, not the former fixed 75% PURE / 25% MARKET blend. F-ST combines current vig-free market log-odds with the separately materialized nested `fst_pure_home_prob` using pinned coefficients. The former 75/25 rule remains computed and locked as `legacy_final_home_prob` for a clean counterfactual. Nothing in this research document authorizes changing the frozen F-ST coefficients or using 2026 outcomes to select a replacement architecture.

## What other public forecasting systems do

### nfelo

nfelo explicitly treats market regression as an accuracy-versus-alpha problem. Its public methodology says that a model generally improves by moving toward market prices, but excessive regression can erase useful independent opinions. The current implementation is more sophisticated than a fixed average: it uses a disagreement-dependent logistic regression factor on the opening line, then modifies that factor using open-to-close market movement. Small model-market disagreements can collapse almost completely to the market; large disagreements preserve more model signal, subject to a residual cap. Current configuration parameters include a minimum market-regression floor of about 40%, a disagreement midpoint in Elo space, and additional sensitivity to closing-line movement.

Sources:
- https://www.nfeloapp.com/analysis/using-market-regression-to-improve-prediction-accuracy-in-the-nfl/
- https://github.com/greerreNFL/nfelo/tree/main/nfelo/Utilities/MarketRegression
- https://github.com/greerreNFL/nfelo/blob/main/config.json

The useful lesson for LevLine is not to copy nfelo's fitted parameters. Their raw model, target scale, line data, timing and optimization sample differ from ours. The useful lesson is the architecture: **market trust can be conditional rather than flat**, and disagreement/movement should be measured explicitly.

### FiveThirtyEight NFL Elo

FiveThirtyEight's NFL system did not simply insert the weekly Vegas spread into every game probability. It used football/Elo/QB/rest/travel inputs for game forecasts, while using Vegas season win totals heavily in preseason team initialization: two-thirds Vegas-wins Elo and one-third regressed prior Elo. Their methodology also notes that large model-versus-Vegas gaps often reflect information the market knows about personnel that an Elo model does not.

Source:
- https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work/

The lesson is that market information can be most valuable where the football model is structurally weak, especially preseason/offseason and news-heavy situations.

### NoPunt

NoPunt takes the opposite product stance: the market is **not** an input to the win probability. Its football ensemble remains independent, and the live market is compared afterward to identify potential value. This preserves maximum opinionatedness and makes model-vs-market disagreement easy to interpret, but sacrifices the accuracy gain that can come from combining two informative forecasts.

Source:
- https://www.nopunt.com/methodology

This is a useful benchmark for Sunday Signal: both legacy production PURE and F-ST nested PURE should remain visible as diagnostics even though official F-ST includes market information.

### Forecast-combination research

Probability-forecasting literature supports testing combination methods beyond arithmetic averaging. In particular, logit-space pooling and fitted forecast-combination models can outperform simple averages when component forecasts contain complementary information. The core requirement is strict out-of-sample fitting; fitted combination weights evaluated on the same observations used to choose them are not credible evidence.

References:
- Satopää et al., *Combining multiple probability predictions using a simple logit model*, International Journal of Forecasting (2014), DOI 10.1016/j.ijforecast.2013.09.009
- Lessmann et al., *A new methodology for generating and combining statistical forecasting models to enhance competitive event prediction*, European Journal of Operational Research (2012)

## LevLine measurement framework

Sunday Signal should permanently report four separate questions:

1. **Independence** — How correlated are F-ST nested PURE and the market? What is the average absolute probability gap? How often do their implied winners differ?
2. **Accuracy** — On the exact same games and market snapshot, what are official F-ST, legacy 75/25, MARKET and, where useful, F-ST nested PURE Brier score, log loss and winner accuracy?
3. **Incremental value** — When F-ST differs materially from the market or from legacy LevLine, does the difference improve or degrade probability accuracy? Which model wins when implied winners differ?
4. **Future candidate selection** — Can a separately registered, chronology-safe candidate improve on frozen F-ST without using its evaluation games for its own selection?

Historical research tested both linear probability pooling and logit pooling, including expanding-season walk-forward selection. Those experiments remain historical evidence; they are not runtime parameter searches for F-ST.

## Critical timing limitation

Historical `market_home_prob` in the current nflverse schedule feed is effectively a closing-line benchmark. Sunday Signal's official forecast locks at **T-120**. A closing price contains information that may arrive after our lock, so a closing-market optimum is not a fair production selector.

Starting with 2026, Sunday Signal's append-only run history and immutable prediction history preserve contemporaneous market probabilities. Post-promotion official locks therefore retain the exact market probability used by F-ST and compute the legacy counterfactual from that same snapshot. When an upstream source does not expose an independent quote timestamp, LevLine records the forecast/lock snapshot time rather than inventing bookmaker freshness metadata.

A future market-quality/timing track may test sharper multi-book consensus or a different pregame horizon. Such work must be a separately registered research change and must not ad hoc alter F-ST-01 coefficients.

## Current policy

- Official winner probability is `F-ST-01-FROZEN-2026` whenever a usable current vig-free moneyline probability exists.
- If market is missing/non-finite, use exact legacy production behavior for that game and record an explicit fallback reason; do not synthesize a moneyline probability or substitute a spread.
- Keep `pure_home_prob`, `fst_pure_home_prob`, market, and exact legacy 75/25 counterfactual separately visible for evaluation.
- Do not select or refit F-ST coefficients/architecture from 2026 outcomes.
- Track matched-horizon official F-ST versus legacy LevLine and market automatically throughout 2026.
- Research sharper market source/timing, availability, forward-only 2026 updating, and disagreement behavior only as separately registered follow-ups.
