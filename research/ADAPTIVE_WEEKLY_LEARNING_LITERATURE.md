# Adaptive Weekly Learning — Literature & Professional Practice Synthesis

Status: research support for `research/ADAPTIVE_WEEKLY_LEARNING_RESEARCH_PLAN.md`  
Lane: 6 — literature / professional practice  
Production impact: none

## Executive conclusion

The strongest external evidence supports **controlled sequential updating with shrinkage**, not indiscriminate weekly full retraining.

Professional systems and peer-reviewed methods repeatedly use the same pattern:

1. begin from a strong prior;
2. update after new games;
3. limit the learning rate so one result cannot dominate;
4. preserve older information when the process appears stable;
5. allow faster adaptation only when evidence suggests a genuine change in team state;
6. evaluate forecasts prospectively rather than retrofitting after outcomes.

That pattern maps directly to LevLine's proposed architecture:

`frozen F-ST prior -> constrained residual state -> optional calibration -> selective switch gate`.

## 1. FiveThirtyEight NFL Elo

Source:
https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work/

Relevant practices:

- Team Elo is updated after every game.
- The NFL K-factor was selected to balance responsiveness against weekly noise; FiveThirtyEight reports K=20 as large enough to use new evidence without allowing ratings to bounce excessively.
- Updates scale with forecast surprise and margin of victory.
- Quarterback ratings are explicitly rolling rather than reset from the latest game.
- Team and quarterback ratings regress toward broader priors across seasons.
- QB changes can create a large pregame adjustment before game outcomes reveal the effect.
- FiveThirtyEight reports that weather and coaching adjustments were tested but did not add enough predictive value to retain.

LevLine mapping:

- supports a small dynamic residual state;
- supports mean reversion and conservative process variance;
- supports explicit QB/personnel shock handling;
- argues against adding every plausible context variable;
- does **not** support retraining the entire F-ST architecture after each week.

## 2. ESPN Football Power Index

NFL methodology:
https://www.espn.com/nfl/story/_/id/13539793/espn-nfl-football-power-index-debuts
https://www.espn.com/nfl/story/_/id/13539941/how-espn-nfl-football-power-index-was-developed-implemented
https://www.espn.com/blog/statsinfo/post/_/id/123048/a-guide-to-nfl-fpi

Related detailed Bayesian FPI description:
https://www.espn.com/blog/statsinfo/post/_/id/109828/reintroducing-espns-college-football-power-index

Relevant practices:

- Preseason priors establish early-season team strength.
- In-season EPA/per-play information increasingly informs team strength.
- ESPN describes Bayesian regression for updating offensive, defensive and special-teams components.
- Prior-season information declines in influence but does not necessarily disappear.
- NFL FPI incorporates QB state and other personnel/context information.
- ESPN states the model learns quickly early in the season when observed performance disagrees with the prior.
- Development relied on historical cross-validation and explicit uncertainty/covariance treatment.

LevLine mapping:

- the model should learn current team state faster than it learns global model coefficients;
- prior information should remain active after Week 1 rather than being discarded;
- offense/defense/QB state should be separable where data support it;
- adaptive parameters must be validated chronologically.

## 3. Massey Ratings

Source:
https://masseyratings.com/faq.php

Relevant practice:

- ratings are recomputed as new games arrive;
- early-season games are slightly down-weighted rather than deleted;
- opponent strength is implicit in the fitted system;
- well-matched games naturally carry more information.

LevLine mapping:

- supports declining influence / forgetting rather than hard resets;
- supports opponent-adjusted state;
- supports giving decision-boundary games special analytical attention.

## 4. David Sasser

Current public board:
https://www.davidsasser.com/cfb

Observed public characteristics:

- publishes model-projected scores/lines alongside opening and current market lines;
- exposes model-versus-market disagreement rather than hiding the market benchmark;
- maintains an ongoing performance record.

Important limitation:

The public page does not disclose enough implementation detail to establish the exact weekly training/update mechanism. Therefore Sasser is useful as a **professional product and market-comparison reference**, but not as evidence for a specific retraining algorithm.

LevLine mapping:

- keep independent model projection and market state visible at the same time;
- preserve an immutable performance ledger;
- do not infer undisclosed methodology from public records.

## 5. Glickman & Stern — NFL state-space model

Mark E. Glickman and Hal S. Stern, "A State-Space Model for National Football League Scores," Journal of the American Statistical Association 93(441), 1998.
DOI: 10.1080/01621459.1998.10474084
https://www.tandfonline.com/doi/abs/10.1080/01621459.1998.10474084

Contribution:

- models NFL team strength as a latent quantity that changes over time;
- state-space structure provides a formal mechanism for sequential updating;
- recognizes that true team ability is not stationary across a season.

LevLine mapping:

- dynamic team residuals are theoretically justified;
- update uncertainty should be explicit;
- current ability should not be represented solely by a static full-history fit.

## 6. Cattelan, Varin & Firth — dynamic Bradley–Terry

Manuela Cattelan, Cristiano Varin and David Firth, "Dynamic Bradley–Terry modelling of sports tournaments," Journal of the Royal Statistical Society: Series C, 2013.
DOI: 10.1111/j.1467-9876.2012.01046.x
https://rss.onlinelibrary.wiley.com/doi/full/10.1111/j.1467-9876.2012.01046.x

Contribution:

- explicitly models sports-team abilities as time varying;
- uses exponentially weighted moving-average processes to connect present strength with past results.

LevLine mapping:

- supports decayed state rather than equal weighting of every historical game;
- supports the existing EWMA idea;
- does not imply that global F-ST coefficients should change weekly.

## 7. McCormick et al. — dynamic logistic regression / model averaging

"Dynamic Logistic Regression and Dynamic Model Averaging for Binary Classification," Biometrics 68(1), 2012.
DOI: 10.1111/j.1541-0420.2011.01645.x
https://academic.oup.com/biometrics/article/68/1/23/7390679

Contribution:

- online Bayesian binary classification;
- time-varying coefficients through a state-space formulation;
- forgetting factor controls the amount of adaptation;
- Bayesian model averaging addresses model uncertainty;
- stable periods borrow more heavily from prior information while volatile periods permit faster adaptation.

LevLine mapping:

- directly supports a residual-logit adaptive layer;
- motivates a later dynamic-model-averaging challenger only after simple residual state is understood;
- supports explicit process variance / forgetting controls.

## 8. Macrì-Demartino, Egidi & Torelli — adaptive Bayesian team strength

"Bayesian dynamic Bradley-Terry model with commensurate spike-and-slab priors," Journal of Big Data, 2026.
DOI: 10.1186/s40537-026-01486-6
https://doi.org/10.1186/s40537-026-01486-6

Contribution:

- team- and time-specific adaptive borrowing;
- strong shrinkage to historical state when performance is stable;
- more diffuse innovation prior when evidence suggests sudden change;
- reported out-of-sample Brier improvements over simpler dynamic comparators in NBA data;
- identified changes that aligned with roster changes and injuries.

LevLine mapping:

This is the closest conceptual match to the intended LevLine adaptive layer:
- normal week -> strong shrinkage toward F-ST/current state;
- credible regime change -> allow larger state movement;
- regime-change detection must be based on pregame/previous-game information, never target outcomes.

## 9. Song, Boulier & Stekler — NFL forecast comparison

"The comparative accuracy of judgmental and model forecasts of American football games," International Journal of Forecasting 23(3), 2007.
DOI: 10.1016/j.ijforecast.2007.05.003
https://www.sciencedirect.com/science/article/pii/S0169207007000672

Evidence:

- compared 31 statistical systems and 70 experts over 496 NFL games;
- the betting line was an exceptionally strong benchmark and outperformed both broad groups in the reported comparison.

LevLine mapping:

- expected incremental gains should be modest;
- claims of +2 to +5 percentage points over a strong incumbent/market benchmark should trigger leakage and selection audits;
- market comparison must remain a first-class control.

## 10. Boulier & Stekler — NFL prediction

"Predicting the outcomes of National Football League games," International Journal of Forecasting 19(2), 2003.
DOI: 10.1016/S0169-2070(01)00144-3
https://www.sciencedirect.com/science/article/pii/S0169207001001443

Contribution:

- evaluates power-score probability forecasts against a naive model, market, and expert forecast;
- reinforces the difficulty of beating the betting-market benchmark.

LevLine mapping:

- adaptive value should be measured through paired incremental performance, not standalone accuracy alone.

## 11. Forecast-process discipline

H.O. Stekler, "The future of macroeconomic forecasting: Understanding the forecasting process," International Journal of Forecasting 23(2), 2007.
https://www.sciencedirect.com/science/article/pii/S0169207007000039

Relevant recommendation:

- analyze past forecast errors carefully;
- maintain records explaining forecast adjustments;
- use quality-control methods to monitor forecasts.

LevLine mapping:

This directly supports the weekly error-audit ledger. Error analysis is useful even when it does not immediately justify a model update.

## 12. Implications for the current sprint

### Supported now

1. **Residual state around F-ST**, not replacement of F-ST.
2. **Strong shrinkage / mean reversion.**
3. **Week-frozen updates**: all games in Week t are predicted before Week t outcomes update state.
4. **Pick-preserving calibration** as a separate probability-quality experiment.
5. **Selective decision replacement** concentrated near the 50% boundary.
6. **Explicit QB/personnel regime-shock research** when strict point-in-time evidence exists.
7. **Prospective champion/challenger evaluation.**

### Not supported as default

1. weekly full refit of all F-ST coefficients;
2. aggressive current-season-only weighting;
3. automatic reaction to every wrong pick;
4. broad upset overrides against strong market favorites;
5. hidden discretionary/manual adjustments;
6. treating a single hot season as proof.

## 13. Current quantitative expectation

External evidence supports the direction of adaptation but does **not** justify a large assumed uplift. Combined with LevLine's own historical evidence:

- frozen chronology-clean F-ST: ~68.17%;
- prior generic dynamic Elo residual: 739/1087, two fewer winners than F-ST;
- prior accuracy-optimized adaptive global weights: materially worse than F-ST;
- component-resolved boundary-local challenger: modest positive point estimate but not proven.

Therefore the research prior remains:

- **expected constrained adaptive uplift: about +0.6 percentage points**;
- **plausible success range: roughly +0.25 to +1.25 pp**;
- **large > +1.25 pp historical improvement: adversarially audit before believing**;
- **naive weekly full retraining: expected negative value**.

The sprint must now replace this prior with measured chronology-safe evidence.
