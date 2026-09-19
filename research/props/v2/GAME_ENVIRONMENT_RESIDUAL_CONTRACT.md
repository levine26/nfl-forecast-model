# LevLine Props 2.0 — Game Environment Residual Contract

Status: **PREREGISTERED BEFORE PLAYER-PROP INTEGRATION**  
Candidate: `P2-GAME-ENV-V01`  
Version: `levline-props-v2-game-environment-v0.1.0`

## Question

Before altering any player projection, determine whether pregame game environment adds information to
the existing top-level opportunity engine.

The component is evaluated only on:
- team offensive plays;
- team dropback rate.

No player-prop outcome is used.

## Baseline

The existing V1 opportunity engine's one-step-ahead posterior:
- Gamma-Poisson team plays;
- Beta dropback rate;
- strictly prior team history;
- 8-game half-life and existing structural priors.

## Pregame context

Use source-qualified historical game-level sportsbook **OPEN** state from the same Action Network
research source already used by the Props reconstruction:
- game total;
- team spread.

Historical exact publication timestamps are not claimed; this remains retrospective development
evidence. The source's book-30 OPEN designation is used as supplied.

## Frozen residual models

Two fixed low-dimensional ridge models, L2 = 10, no hyperparameter search.

Team plays residual features:
- game total;
- absolute team spread;
- opponent baseline predicted plays.

Dropback-logit residual features:
- signed team spread (negative favorite / positive underdog);
- game total;
- absolute team spread.

Features are standardized using training rows only. The intercept is unpenalized.

## Chronology

For evaluation season S:
- ridge residual parameters are fit only through S−1;
- baseline opportunity predictions for every row use only games earlier than that row;
- 2026 results are prohibited.

## Decision gate

A game-environment component is considered development-improving only if:
1. aggregate season-forward team-plays MAE improves;
2. aggregate season-forward dropback-rate MAE does not materially worsen;
3. game-clustered uncertainty is reported;
4. no single season is required to manufacture the aggregate result.

Only after this component gate may the frozen context corrections be translated into the existing
`play_volume_multiplier` and `dropback_logit_delta` hooks for a player-prop ablation.

Retrospective success cannot authorize production.
