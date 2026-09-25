# M1 Prospective Phase 2 Operational Hardening Diff Audit

Program: `FV2-PROS-M1-MARKETSTATE-01`

Branch: `research/ats-m1-phase2-operational-qualification`

Completed-2026 outcomes used: `0`

Production changes authorized: `NO`

## Intended changed surfaces

This work unit is limited to:

- the M1 research-only scheduled workflow;
- M1 Phase-2 operational qualification/status persistence code;
- M1 outcome-blind fixture tests;
- M1 research governance receipts.

It does not intentionally alter:

- production LevLine/F-ST forecasting code;
- production model artifacts;
- public forecast semantics;
- ATS model fitting or scoring;
- any completed-game outcome dataset.

## Scientific-identity audit

The branch does not change the frozen M1 predictor horizons, diagnostic horizons, capture tolerance, minimum-book rule, staleness threshold, common-book path rule, predictor feature registry, provider order, or T-120 information boundary.

The added code is operational observability only: it records whether prospective horizons are future/open/captured/missed and makes collector exit causes durable.

## Merge requirement

The final merge decision must use the exact PR diff against current `main`, not this prose assertion alone. Any unexpected production-surface file in the PR diff is a hard stop until reconciled.
