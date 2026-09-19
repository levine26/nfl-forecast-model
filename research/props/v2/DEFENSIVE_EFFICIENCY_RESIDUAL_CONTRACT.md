# LevLine Props 2.0 — Defensive Efficiency Residual Contract

Status: **PREREGISTERED COMPONENT ISOLATION / NOT A PREGAME PROP FORECAST**  
Candidate IDs: `P2-EFF-RUSH-DEF-V01`, `P2-EFF-REC-DEF-V01`  
Version: `levline-props-v2-defensive-efficiency-v0.1.0`

## Question

Does a strictly lagged opponent defensive-efficiency residual improve the conditional yardage mean
beyond the player's own empirical-Bayes efficiency baseline?

Rushing and receiving are separate preregistered hypotheses. A favorable result in one does not
rescue the other.

## Baseline

For each target player-game:
- use the player's historical event yards strictly before the target week;
- shrink to a position/event-type prior fitted only from prior seasons;
- prior strengths match the current Props efficiency layer:
  - rushing: 65 events;
  - receiving yards/reception: 45 receptions.

## Challenger context

For the target opponent and event type:
- use only games before the target week;
- retain the most recent 8 defensive games;
- compute opponent yards allowed per event;
- shrink to the prior league event mean with 80 pseudo-events.

The single context feature is:

`opponent prior yards/event - prior league yards/event`

For each event type, fit a fixed one-feature weighted ridge residual model:
- target = actual yards/event − player baseline yards/event;
- weights = target event count;
- ridge alpha = 25;
- standardization uses training rows only;
- intercept is unpenalized;
- no hyperparameter search.

## Isolation boundary

Evaluation holds the **actual event count** fixed and compares predicted conditional total yards.

That postgame event count makes this a component-isolation study, not a pregame prop forecast.
A positive result can justify inserting the context residual into a new pregame simulator candidate;
it cannot be reported as betting accuracy or production evidence.

No sportsbook line or price is used anywhere.

## Chronology

For evaluation season S:
- residual coefficients train only through S−1;
- position priors use seasons before the row's season;
- player and opponent histories use weeks strictly before the target week;
- same-week outcomes are not used;
- completed 2026 outcomes are prohibited.

## Frozen evaluation

Evaluation seasons: **2023, 2024, 2025**.

Primary metric for each independent event-type candidate:
- conditional total-yard MAE.

Secondary:
- yards/event MAE;
- game-clustered 95% interval for challenger-minus-baseline total-yard MAE;
- sample size, games, players and coefficient audit.

## Advance gate — applied separately to rushing and receiving

An event-type candidate advances only if:
1. pooled 2023–2025 conditional total-yard MAE improves;
2. at least two of three season-level MAE differences are negative;
3. the pooled game-clustered 95% interval upper bound is <= 0.

Failure in one event type cannot be offset by the other. Retrospective success cannot authorize
production.
