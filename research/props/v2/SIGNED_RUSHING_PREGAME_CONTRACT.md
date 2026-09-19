# LevLine Props 2.0 — Signed Rushing Pregame Ablation Contract

Status: **PREREGISTERED RETROSPECTIVE DEVELOPMENT / TRUE PREGAME DISTRIBUTION**  
Candidate: `P2-DIST-RUSH-PREGAME-V01`  
Version: `levline-props-v2-signed-rushing-pregame-v0.1.0`

## Motivation

The signed event-yard component study showed a stable CRPS gain for rushing and demonstrated that the
current nonnegative Gamma draw is structurally incapable of negative rushing events.

This follow-up removes the postgame event-count conditioning.

## Frozen isolation design

For every historical player-game:
- build the standard frozen V1 pregame upstream state;
- run the standard V1 simulator;
- preserve **exactly the same sampled carry array** for every player;
- preserve V1's pregame mean rushing yards/carry and mean uncertainty;
- replace only the conditional rushing-yard draw.

Baseline:
- current nonnegative Gamma aggregate.

Challenger:
- empirical signed rushing-event residuals by position;
- event pools fitted only through season S−1;
- residual pools are centered to zero before being shifted by the V1 player mean;
- position pools require 250 events, otherwise use a pooled-position fallback frozen before scoring;
- target-game carries and target-game yards are never used to fit or construct the forecast.

No receiving, passing, opportunity, availability, TD, or sportsbook input is changed.

## Historical population

Primary genuine Action Network book-30 OPEN rushing-yard props from the existing validated historical
reconstruction, regular seasons 2023–2025.

This population has already been used for V1 development, so any result is retrospective development
evidence only and cannot authorize production.

## Metrics

Primary:
- empirical CRPS of the full rushing-yard distribution.

Secondary:
- Fair-Line MAE;
- directional accuracy versus the same market line;
- 80% interval score and coverage;
- game-clustered confidence interval for challenger-minus-V1 CRPS;
- game-clustered confidence interval for challenger-minus-V1 Fair-Line absolute error.

## Frozen advance gate

Advance the signed-rushing pregame mechanism to prospective shadow only if:
1. pooled CRPS improves;
2. pooled Fair-Line MAE improves;
3. CRPS improves in at least two of three seasons;
4. pooled game-clustered CRPS-difference 95% CI upper bound <= 0;
5. 80% coverage does not deteriorate by more than 1.5 percentage points.

Directional accuracy is diagnostic and cannot rescue a failed proper-score gate.

Completed 2026 outcomes are prohibited.
