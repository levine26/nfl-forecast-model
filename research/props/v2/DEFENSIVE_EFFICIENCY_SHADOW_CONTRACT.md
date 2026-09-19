# LevLine Props 2.0 — Defensive Efficiency Prospective Shadow Coefficient Freeze

Status: **FROZEN BEFORE 2026 PROSPECTIVE GRADING**  
Version: `levline-props-v2-defensive-efficiency-shadow-v0.1.0`

## Purpose

Fit the final season-forward opponent defensive-efficiency coefficients for 2026 prospective shadow
use after both rushing and receiving mechanisms passed their true-pregame retrospective gates.

## Allowed training data

Only regular-season football event data through **2025**:
- rushing-event yards;
- receiving-event yards;
- stable player position;
- strictly lagged player efficiency state;
- strictly lagged opponent defensive efficiency state.

No player-prop outcome, sportsbook result, 2026 game outcome, cover result, or prospective shadow
grade is permitted.

## Frozen specification

Inherited unchanged from the passed PR #391 / #394 mechanism:
- opponent prior 8 defensive games;
- shrink opponent yards/event toward prior league mean with 80 pseudo-events;
- feature = opponent prior yards/event − prior league yards/event;
- target residual = actual yards/event − player baseline yards/event;
- weighted ridge with alpha = 25;
- player baseline prior strengths:
  - rushing 65 events;
  - receiving 45 events.

The only new operation is the final refit through 2025 for use on future 2026 forecasts.

## Output

A frozen JSON artifact must include separately:
- rushing intercept, standardized beta, x mean, x sd;
- receiving intercept, standardized beta, x mean, x sd;
- row counts;
- trained-through season;
- contract/version;
- source audit;
- explicit zero use of completed 2026 outcomes, prop outcomes, and sportsbook results.

## Governance

After the coefficient JSON is frozen for prospective shadow use, it may not be modified because of
2026 results. Any future coefficient revision requires a new candidate version and a new untouched
prospective evidence window.

Production authorization remains false.
