# PRODUCTION FIREWALL

## Protected production identity

`F-ST-01-FROZEN-2026`

Phase 1 is research and documentation only. It does not change production forecasting behavior.

Protected areas include the frozen F-ST model, Sunday Signal numerical forecasts, official probabilities, public fair spread, official score projection, ATS selections, grading/history, and deployment configuration.

## Phase-1 change scope

Frontier changes are limited to:

- `research/ats-frontier-v2/` research and governance artifacts; and
- research-only tests that validate those artifacts.

No Frontier research module is imported by the production forecasting application.

## Completed-2026 evidence boundary

Completed 2026 game outcomes are excluded from candidate selection, feature design, source selection based on performance, model-family choice, priors, distribution choice, thresholds, calibration, and architecture.

Outcome-blind inspection of source schemas, timestamps, and data-availability mechanics is permitted. Historical candidate evaluation is not part of Phase 1.

## Integration check

Before integration, compare the Frontier branch with its base and confirm that Frontier-authored changes are confined to research documentation and research tests. Unrelated automated forecast-refresh commits on `main` may advance independently; they do not become Phase-1 scientific evidence.

## Promotion gate

No future research result automatically changes production. Any production promotion requires the explicit Phase-7 human authorization defined in `MASTER_PLAN.md`.