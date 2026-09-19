# LevLine Props 2.0 — Team Offensive TD Count Distribution Contract

Status: **PREREGISTERED COMPONENT ISOLATION**  
Candidate: `P2-TD-COUNT-V01`  
Version: `levline-props-v2-team-td-count-v0.1.0`

## Question

Does an overdispersed Gamma-Poisson / negative-binomial count distribution improve team offensive
touchdown uncertainty relative to Poisson when **both models receive the exact same pregame mean**?

This isolates count-distribution shape from mean forecasting.

## Target

Regular-season team offensive touchdowns per game:
- passing touchdowns;
- rushing touchdowns;
- excludes defensive and special-teams return touchdowns.

No player-prop result, sportsbook line, price, or cover result is used.

## Shared expected mean

For every team-game:
- use team offensive TD history strictly before the target week;
- retain the prior 16 team games;
- shrink to the strictly prior league offensive-TD mean with 8 pseudo-games;
- same-week outcomes do not update any target-week forecast.

The Poisson baseline and negative-binomial challenger use **the same expected mean**.

## Challenger dispersion

For evaluation season S:
- estimate a single overdispersion alpha using team-game rows through S−1;
- Pearson/method-of-moments:
  `alpha = max(0, sum((y-mu)^2-y) / sum(mu^2))`;
- no hyperparameter search;
- alpha = 0 collapses exactly to Poisson.

## Frozen evaluation

Evaluation seasons: **2023, 2024, 2025**.

Primary:
- discrete CRPS.

Secondary:
- log loss;
- 80% central interval coverage;
- fitted dispersion alpha;
- game-clustered 95% CI for challenger-minus-Poisson CRPS.

## Advance gate

The negative-binomial count mechanism advances only if:
1. pooled 2023–2025 CRPS improves;
2. at least two of three evaluation seasons improve CRPS;
3. pooled game-clustered 95% CI upper bound for CRPS difference is <= 0;
4. pooled log loss does not worsen.

A positive result only justifies a new full Props simulator experiment. It does not authorize
production and does not prove anytime-TD betting edge.

Completed 2026 outcomes are prohibited.
