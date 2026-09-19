# LevLine Props 2.0 — Prospective Validation Plan

Status: **FROZEN PRINCIPLES / CANDIDATES VERSIONED SEPARATELY**

## Objective

Create untouched evidence capable of answering whether any Props 2.0 component improves:
1. the independent football Fair Line / distribution; and
2. final probability relative to the sportsbook market.

## Immutable receipt requirements

Before kickoff preserve:
- source forecast ID;
- forecast timestamp;
- market capture timestamp;
- kickoff;
- sportsbook/book set;
- line and prices;
- no-vig market probability;
- pure LevLine distribution probability;
- market-anchored probability;
- fair line;
- model/version IDs;
- feature-state version;
- source-quality state;
- input hashes where available.

Receipts are append-only. Later grading may add result records but may never rewrite originals.

## Candidate versioning

Any change to features, coefficients, priors, thresholds, data source, source-quality rule, horizon,
distribution family, or calibration creates a new candidate ID and a new prospective ledger.

Completed 2026 outcomes from candidate A may not be used to modify candidate A. If they inspire a new
candidate B, B starts a new untouched evaluation period.

## Horizons

Research contracts may use OPEN, T−48h, T−24h, T−12h, T−6h, T−90m, T−30m and near-close only when
the source actually captures those states. Missing horizons remain missing. Do not interpolate a
historical market state and call it observed.

## Metrics

For every serious candidate report:
- N, unique games, unique players;
- accuracy + Wilson interval;
- game-clustered bootstrap interval;
- paired accuracy difference;
- Brier and log loss;
- calibration intercept/slope and reliability curve;
- Fair-Line MAE / median absolute error;
- CRPS for full distributions;
- interval / quantile / tail coverage;
- edge-bucket reliability;
- CLV and subsequent line/price movement where qualified.

## Promotion logic

A final market-residual candidate must demonstrate on untouched data:
- incremental performance versus market-only probability;
- no meaningful degradation in Brier/log loss;
- acceptable calibration;
- edge magnitude related monotonically or directionally to realized correctness;
- positive CLV evidence when available;
- no leakage;
- adequate sample size and clustered stability.

Football-side components may be promoted into a frozen candidate when they improve Fair-Line or
distribution quality consistently enough to justify prospective testing; retrospective improvement
alone never authorizes production.

## Selective MODEL EDGE

No retrospective 2023–2025 threshold may be presented as validation. First establish prospective
residual calibration, preregister edge buckets, test monotonicity, then freeze a threshold and start
a new prospective test.

## Current prospective candidate

PR #379 implements the first clean market-anchor shadow candidate:
- market-only comparator;
- market + frozen pre-2026 global V1 residual.

It consumes current published pregame V1 forecasts only and persists immutable receipts on
`research-data/props-v2-prospective-shadow`, separate from production outputs.
