# LevLine Props 2.0 — Signed Event-Yard Distribution Contract

Status: **PREREGISTERED COMPONENT ISOLATION / NOT A PREGAME PROP FORECAST**  
Candidate: `P2-DIST-SIGNED-V01`  
Version: `levline-props-v2-signed-event-distribution-v0.1.0`

## Structural problem

The current simulator compounds rushing and receiving yards with a nonnegative Gamma distribution and
then clips at zero. That distribution cannot generate a negative rushing or receiving event.

Negative plays are real football outcomes. This experiment tests whether preserving signed event
support and empirical tail shape improves conditional yardage-distribution quality.

## Isolation design

This first experiment deliberately conditions on the **realized event count** for each player-game.

That is postgame information and therefore this experiment is **not** a pregame player-prop forecast.
It exists only to isolate the conditional yardage distribution from opportunity-count error.

A positive result can justify integrating the distribution into the pregame simulator; it cannot be
reported as prop accuracy or production evidence.

## Baseline

For rushing and receiving separately:
- use the same style of pregame shrunken player mean-per-event;
- position prior fitted through the prior season;
- fixed prior strengths matching the existing efficiency layer:
  - rushing 65 events;
  - receiving 45 receptions;
- Gamma event/aggregate distribution using the training position event SD;
- nonnegative support.

## Challenger

For each event type × position:
- fit an empirical training event-yard distribution through season S−1;
- center it to zero residual mean;
- shift residuals by the player's pregame shrunken mean-per-event;
- bootstrap signed residual events with replacement;
- sum exactly the realized event count for component isolation.

No validation-period hyperparameter search is permitted.

## Chronology

For an evaluation player-game:
- position event distribution uses seasons <= S−1;
- player mean may use that player's games strictly before the target game;
- target-game yards are evaluation only;
- completed 2026 outcomes are prohibited.

## Metrics

Primary:
- empirical CRPS of aggregate yards.

Secondary:
- 80% interval score;
- 80% empirical coverage;
- interval width;
- rushing/receiving subgroup stability.

A signed distribution advances to full pregame simulation only if aggregate CRPS improves and the
gain is not purchased by pathological interval calibration.

Retrospective component success cannot authorize production.
