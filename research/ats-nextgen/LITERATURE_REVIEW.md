# Phase 1 Literature Review

**Evidence policy:** peer-reviewed work informs hypotheses and mathematical design; it does not authorize importing fitted parameters or claiming LevLine performance.

## 1. Quantiles, spreads and wager selection

### Dmochowski (2023) — PLOS ONE — evidence class 1

Jacek P. Dmochowski, *A statistical theory of optimal decision-making in sports betting*, PLOS ONE 18(6): e0287601. DOI: https://doi.org/10.1371/journal.pone.0287601

Direct source verified. The paper frames optimal decisions in terms of the conditional distribution of the outcome and sportsbook proposition. It establishes that the median is sufficient for the binary prediction decision, while additional quantiles are needed to identify wagers with positive expected profit. Its NFL empirical study uses more than 5,000 regular-season games and reports that point spreads explain a large share of the variability of the conditional median.

Transfer to LevLine:

- motivates Q1's market-relative median and adjacent payout quantiles;
- supports treating the posted line as a strong location benchmark rather than an ordinary feature;
- supports abstention/selective evaluation;
- does **not** remove the need to model pushes or actual quoted prices.

The `.476/.524` interpretation is therefore retained as a reference quantile identity, not a universal betting threshold.

### Bassett (2007) — Statistical Modelling — evidence class 1

Gilbert W. Bassett, *Quantile regression for rating teams*, Statistical Modelling 7(4), 301–313. DOI: https://doi.org/10.1177/1471082X0700700402

The paper proposes quantile regression for sports outcomes/team ratings and explicitly connects quantile-specific handicaps to point spreads. Transfer: use quantile loss directly rather than estimating a conditional mean and retrospectively slicing it into ATS decisions.

### Koenker & Bassett / standard quantile-regression theory — evidence class 1

Foundational quantile-regression results justify pinball loss as the proper objective for conditional quantiles and regularization when predictor dimension is nontrivial. Transfer: Q1's primary objective is pinball loss at preregistered quantiles.

## 2. Margin distributions and NFL score structure

### Mohsin & Gebhardt (2022/2024) — Journal of Applied Statistics — evidence class 1

Muhammad Mohsin and Albrecht Gebhardt, *A stochastic model for NFL games and point spread assessment*. DOI: https://doi.org/10.1080/02664763.2022.2120973

The paper models the distribution of score difference directly and uses its quantile function for point-spread assessment. It is useful as evidence that margin-distribution shape can be modeled as an object in its own right rather than treated as a fixed Normal residual.

Transfer: Q2 must compare bounded distribution families and evaluate full-distribution/proper scores, not only mean error.

### NFL Scores and Pointspreads (1997) — Journal of Statistics Education — evidence class 1

The paper/dataset discussion highlights discrete football scoring units and clustering of scores/margins around familiar values such as 3, 7 and 10. Transfer: explicit integer-margin diagnostics and preregistered key-number validation are scientifically justified.

### Scoring-era change

NFL scoring mechanics have changed, most notably the 2015 extra-point rule era. The program therefore must not assume a stationary all-history key-number distribution. Q2 uses a 2015 training floor for primary V1 and estimates every target season's key-number parameters from prior seasons only. Era sensitivity is descriptive/training-side and cannot use the target season to tune itself.

## 3. Market information and microstructure

### Levitt (2004) — Economic Journal — evidence class 1

Steven D. Levitt, *Why Are Gambling Markets Organised So Differently From Financial Markets?* DOI: https://doi.org/10.1111/j.1468-0297.2004.00207.x

The paper documents structural differences between bookmaker markets and conventional financial market making, including bookmaker price setting and bettor biases. It is evidence against treating posted lines as mechanically identical to a frictionless fair-value consensus.

Transfer: the sportsbook is the primary benchmark, but line/price/book/time remain distinct observables; no-vig transformations and consensus construction must be explicit.

### Moskowitz (2021) — Journal of Finance — evidence class 1

Tobias Moskowitz, *Asset Pricing and Sports Betting*, Journal of Finance 76(6). DOI: https://doi.org/10.1111/jofi.13082

This work places sports-betting returns in an asset-pricing/market-efficiency framework. Transfer: any claimed ATS edge should be evaluated with economic frictions and uncertainty, not raw classification accuracy alone.

## 4. Conditional variance / heteroskedasticity

The literature and open-source empirical evidence make a fixed unconditional variance assumption unnecessarily restrictive. Football game environment can plausibly affect variance through expected scoring opportunity, pace, favorite size and uncertainty.

Phase-1 conclusion: V1 should test heteroskedasticity conservatively rather than create a second large predictive model. Q2's conditional scale is restricted to:

`log(scale) = b0 + b1*favorite_size + b2*centered_total + b3*favorite_size*centered_total`.

QB/injury/weather-specific variance is reserved for later because multi-season PIT reconstruction is not sufficiently qualified for V1.

## 5. Direct classification and calibration

General statistical-learning literature supports logistic probability models as strong low-variance baselines and proper scoring rules (log loss/Brier) for probabilistic classification. Flexible boosted trees can be useful but also enlarge the search surface in a small NFL sample.

Phase-1 conclusion: Q3 uses only L2-regularized logistic heads. LightGBM/XGBoost are **not authorized** in V1. A later challenger would require a new preregistration.

Post-hoc isotonic or Platt rescue is also not authorized in V1. Raw out-of-fold calibration is part of the scientific result.

## 6. Conformal prediction

Conformal methods can provide finite-sample marginal coverage under exchangeability or suitable sequential adaptations, but they do not by themselves produce the discrete probability mass and side-price EV needed for ATS. Given NFL nonstationarity and the program's focus, conformal prediction is recorded as a later interval-calibration extension, not a Q1–Q3 primary component.

## 7. Main synthesis

The literature supports testing the new formulation because:

- the sportsbook spread is closer to a conditional median/handicap object than a generic mean-margin target;
- wager selection depends on more than the median;
- NFL margins are discrete and key-number-heavy;
- probability calibration and exact economics are more appropriate than ATS hit rate alone;
- market information is a powerful benchmark and should be treated as such.

The literature does **not** establish that LevLine can beat the market. That remains the empirical question for later phases.