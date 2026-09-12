# Market blend research — Sunday Signal / LevLine

> **Archived historical research record — not current production policy.**  
> This document predates the LevLine 3.0 F-ST release and preserves the original market-blend research rationale. Current production is `F-ST-01-FROZEN-2026`; it is **not** a fixed 75% PURE / 25% MARKET arithmetic blend. The current production contract is `docs/LEVLINE_3_RELEASE.md`, and the active forward research program is `research/LEVLINE_4_RESEARCH_SPEC.md` plus `research/levline4_prereg_v1.json`. Fixed-blend language below is retained only to document the historical baseline that later research replaced.

## Purpose

LevLine should use the betting market as an external information source without becoming a market clone. The market is unusually strong in the NFL because it aggregates injuries, quarterback news, weather, matchup opinions and professional trading. The right question is therefore not whether to use the market, but how to measure whether PURE adds information that survives after the market is known, and how aggressively to regress toward the market without erasing real independent signal.

This document is research guidance only. It does **not** change the production 75% PURE / 25% MARKET blend. Any numerical architecture change requires separate chronology-preserving validation and must never use 2026 outcomes for selection.

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

This is a useful benchmark for Sunday Signal: PURE should remain visible and independently scored even if LevLine continues to include market information.

### Forecast-combination research

Probability-forecasting literature supports testing combination methods beyond arithmetic averaging. In particular, logit-space pooling and fitted forecast-combination models can outperform simple averages when component forecasts contain complementary information. The core requirement is strict out-of-sample fitting; fitted combination weights evaluated on the same observations used to choose them are not credible evidence.

References:
- Satopää et al., *Combining multiple probability predictions using a simple logit model*, International Journal of Forecasting (2014), DOI 10.1016/j.ijforecast.2013.09.009
- Lessmann et al., *A new methodology for generating and combining statistical forecasting models to enhance competitive event prediction*, European Journal of Operational Research (2012)

## LevLine measurement framework

Sunday Signal should permanently report four separate questions:

1. **Independence** — How correlated are PURE and the market? What is the average absolute probability gap? How often do they pick different winners?
2. **Accuracy** — On the exact same games, what are PURE, MARKET and LEVLINE Brier score, log loss and winner accuracy?
3. **Incremental value** — When PURE differs from market by 3, 5 or 10+ percentage points, does PURE improve or degrade probability accuracy? When they pick opposite favorites, which side is right more often?
4. **Blend selection** — What market weight performs best when the weight is selected only from data available before the season being evaluated?

The research harness tests both:

- **Linear probability pooling:** `P = (1-w) * PURE + w * MARKET`
- **Logit pooling:** `logit(P) = (1-w) * logit(PURE) + w * logit(MARKET)`

It also records a descriptive full-sample optimum and an expanding-season walk-forward weight. The descriptive optimum is diagnostic only; the walk-forward result is the more credible architecture evidence.

## Critical timing limitation

Historical `market_home_prob` in the current nflverse schedule feed is effectively a closing-line benchmark. Sunday Signal's official forecast locks at **T-120**. A closing price contains information that may arrive after our lock, so a closing-market optimum is not a fair production-weight selector.

Starting with 2026, Sunday Signal's hourly `run_history.csv` and immutable `prediction_history.csv` preserve contemporaneous market probabilities. That means we can score **T-120 MARKET vs T-120 PURE vs T-120 LEVLINE** on a genuinely matched information horizon going forward.

Until a sufficient matched-horizon sample exists, closing-line diagnostics are an upper-bound market benchmark, not permission to increase the live market weight.

## Current policy

- Keep PURE separately visible and separately scored.
- Keep the current 75/25 production blend frozen unless a separate pre-2026 chronology-preserving study justifies a change.
- Do not select a new weight from 2026 outcomes.
- Track the matched T-120 market benchmark automatically throughout 2026.
- Research disagreement-dependent regression and market-movement conditioning as future candidates, inspired by nfelo, but fit them only on data that respects the information timestamp.