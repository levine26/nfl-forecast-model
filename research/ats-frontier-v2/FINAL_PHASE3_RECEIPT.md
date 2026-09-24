# FINAL PHASE 3 RECEIPT

**Program:** `LEVLINE_ATS_FRONTIER_V2`  
**Phase:** 3 — Final Architecture Design & Preregistration  
**Status:** `COMPLETE`  
**Phase 4:** `NOT_STARTED`  
**Closeout date:** 2026-09-24

## Immutable repository identity

- Phase-3 opening `main`: `5d4312bd36e1083d88ae6ac910703d08384088aa`
- Phase-3 working branch: `research/ats-frontier-v2-phase3`
- Exact validated Phase-3 research head: `8ddad2d6cb40e4296a394b9192bd110f23ba9773`
- Phase-3 primary PR: `#574` — `Freeze ATS Frontier V2 Phase 3 architecture and preregistration`
- Phase-3 primary merge SHA: `fd44e51c412f8d242b54de989e29b550f0e67255`
- Primary merge timestamp: `2026-09-24T15:21:31Z`
- Phase-3 closeout branch base: `fd44e51c412f8d242b54de989e29b550f0e67255`
- Phase-3 closeout branch: `research/ats-frontier-v2-phase3-closeout`

`main` advanced once during Phase 3 for an unrelated automated NFL market refresh. That commit descended directly from the Phase-3 opening main and had no overlap with `research/ats-frontier-v2/`. PR #574 remained mergeable and was merged with the exact validated research head pinned.

## Exact-head CI evidence

Both required research workflows completed successfully on `8ddad2d6cb40e4296a394b9192bd110f23ba9773`:

- LevLine research validation — run `36018189302`, run number `#1677`, conclusion `SUCCESS`.
- LevLine research firewall — run `36018189349`, run number `#2095`, conclusion `SUCCESS`.

The primary PR changed only research/governance artifacts under `research/ats-frontier-v2/`. Production forecasting behavior was not modified.

## Free-first M1 reconstruction result

The required outcome-blind free-source audit did not establish a coherent historical 2020–2025 multi-book fixed-horizon market path sufficient for the intended dynamic-market-state mechanism.

Frozen historical horizons audited:

- T-2160
- T-720
- T-360
- T-120
- T-60
- T-30
- latest-pre-kick

### 2020–2024

Public provider-origin The Odds API cache material exposes the needed schema classes — spread line, side price, moneyline, total, timestamps and bookmaker identity — but the bulk reconstruction path is largely one fixed gameday snapshot. Game-level, book-level and quote-age coverage at the frozen horizons was not demonstrated. Rows equal to or after the target timestamp are rejected. The source therefore does not qualify historical M1.

### 2025

The public multi-book DuckDB source documents a full-season corpus with 1.8M+ rows, 636 fixed captures and 30+ operators, with spread/price/ML/total schema present. Its cadence is only four fixed captures per day. The connected execution environment could not reproducibly materialize the raw binary into the mandatory row-level season×game×book×horizon panel. Near-kick horizons carry coarse/stale-carry risk, and true latest-pre-kick cannot be asserted. It therefore also fails the historical M1 gate.

### Other free sources

- opener/close archives remain opener/close only and cannot be relabeled as exact frozen horizons;
- older Wayback PIT material does not create a coherent modern multi-season panel;
- nflverse historical schedule odds remain exact-horizon opaque.

### Historical M1 disposition

`FRONTIER-M1-DYNAMIC-MARKET-STATE = BLOCKED_PENDING_PAID_SOURCE`.

The mechanism is retained prospectively as `FV2-PROS-M1-MARKETSTATE-01` at T-120. No historical M1 candidate enters Phase 4 from the presently qualified free data.

## Paid-data decision

No historical odds purchase was made or authorized.

The bounded fallback order is:

1. The Odds API historical archive, subject to a data-only qualification pull proving the frozen at-or-before timestamp contract and required season×game×book×horizon coverage.
2. SportsDataIO historical odds/line movement, only if a concrete sample proves the same revision-time/book/line/price requirements.

Any paid acquisition requires explicit authorization and a pre-result governance amendment. It may not be chosen or expanded from candidate performance.

## Final mechanism disposition

| Mechanism | Phase-3 disposition | Frozen identity |
|---|---|---|
| M1 — dynamic market state | historical `BLOCKED_PENDING_PAID_SOURCE`; prospective only | `FV2-PROS-M1-MARKETSTATE-01` |
| M2 — player-state delta | broad historical candidate excluded; QB-only prospective | `FV2-PROS-M2-QBDELTA-01` |
| M3 — hierarchical state | historical Phase-4 candidate | `FV2-HIST-M3-DSSM-01` |
| M4 — discrete margin V2 | historical Phase-4 candidate | `FV2-HIST-M4-DMARGIN-01` |

No third historical candidate was manufactured to fill a quota. Forecast combination remains closed.

## Frozen historical candidate portfolio

### `FV2-HIST-M3-DSSM-01`

Purpose: test whether compact chronology-safe dynamic football state contains incremental information after conditioning on the sportsbook market.

Frozen architecture:

- linear-Gaussian hierarchical dynamic state-space correction;
- latent team offense, team defense and QB states;
- within-season random-walk evolution and partial-pooling/season carryover;
- prior-game nflverse PBP observation channels including offensive EPA/play, defensive EPA/play allowed and QB EPA/dropback;
- market-centered location: `mu = M_market + delta_football`;
- ridge-shrunk correction coefficients;
- market-only null: `M3-NULL-MARKET-NORMAL-01` with `delta_football = 0` and the same distributional translator.

Historical state/training history begins in 2010. Outer development seasons are 2022–2025 regular seasons. Historical market timing remains explicitly `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`; M3 makes no historical T-120/T-60 operating claim.

Primary metric: paired multinomial cover/push/loss log loss versus the market-only null on exact common rows.

Preregistered M3 ablations:

1. `MARKET_ONLY`
2. `STATIC_FOOTBALL_STATE`
3. `DYNAMIC_NO_QB`
4. `DYNAMIC_FULL`

### `FV2-HIST-M4-DMARGIN-01`

Purpose: test whether a numerically valid tail-safe integer-margin representation improves probability quality around NFL betting lines versus a strong distributional market null. M4 is a representation experiment, not presumed independent football alpha.

Frozen architecture:

- Student-t latent home-margin law centered on the market-implied home margin;
- exact integer-bin integration;
- conditional scale using total and absolute spread only;
- finite training-only log-mass offsets only at 0, |3| and |7|;
- no hard-support clipping/folding;
- strong null `M4-NULL-STUDENTT-CONSTANT-01`: same market center and integer integration, chronology-clean Student-t choice, constant scale, no key-mass offsets.

Historical training begins in 2010. Outer development seasons are 2022–2025 regular seasons. Completed-2026 outcomes are prohibited.

Primary metric: integer-margin logarithmic score.

Preregistered M4 ablations:

1. `CONSTANT_SCALE_NO_KEY`
2. `CONDITIONAL_SCALE_NO_KEY`
3. `CONSTANT_SCALE_KEY`
4. `FULL_CONDITIONAL_SCALE_KEY`

## Frozen chronology and evaluation contract

- no random K-fold;
- nested chronological weekly walk-forward;
- every scaler/state/distribution parameter/hyperparameter learned from information available strictly before the target prediction time;
- 2010+ prior history, with 2022–2025 as explicitly non-pristine outer development evidence;
- target-week predictions freeze before outcomes are scored;
- candidate-v-null comparisons use exact common rows;
- primary selection/tuning uses preregistered proper scores, never ATS hit rate or ROI;
- no post-hoc calibration rescue;
- completed-2026 outcomes remain sealed.

## Selectivity and economics contract

No selective historical betting rule is authorized in Phase 4. No search over edge thresholds, confidence cutoffs, model-market gaps, key-number subsets, favorite/underdog subsets or top-percentile rules is permitted.

ATS hit rate is diagnostic only. When actual historical side prices are absent, no actual ROI claim is allowed. Only a clearly labeled `REFERENCE_MINUS110` sensitivity may be reported, explicitly as hypothetical arithmetic rather than a quoted-price profitability estimate.

## Uncertainty contract

Final Phase-4 candidate-v-null evidence must use at least 10,000 paired bootstrap resamples with NFL week blocks within season and explicit season strata. Report per-season and pooled effects, 2.5/97.5 percentile intervals, descriptive `P(delta < 0)`, common-row/week counts and concentration diagnostics. Improvement concentrated entirely in one season or fewer than 10 rows cannot qualify a candidate for prospective shadow.

## Prospective capture plan

Phase 3 froze prospective-only M1/M2 identities at T-120 and a future capture framework that preserves immutable raw timestamps/hashes, bookmaker identity, prices and failed-capture logs with increasingly dense collection approaching kickoff. Future market data may not substitute after-horizon or closing information for an earlier quote.

Historical M1 may reopen only through a pre-result governance amendment demonstrating the required season×game×book×horizon coverage, side-price/ML/total completeness, quote-age distribution, book continuity, no post-target leakage, rights class and exact fields supported.

## Negative-result and leakage firewall

Phase 3 deliberately preserves the following facts:

- historical candidates trained: `0`;
- candidate OOF predictions generated: `0`;
- candidate ATS/ROI/proper-score performance inspected: `NO`;
- completed-2026 outcomes used for fitting/design/tuning: `0`;
- post-hoc threshold fishing: `NO`;
- historical odds purchased: `NO`;
- production model changed: `NO`.

Production remains `F-ST-01-FROZEN-2026`; Sunday Signal forecasting behavior, forecasts, grading, history and deployment are unchanged.

## Phase-4 entry condition

Phase 4 is `NOT_STARTED`.

Its first authorized action is to implement and pass the preregistered synthetic leakage/sign/tail/push tests before fitting either historical candidate. M4 numerical tests include PMF normalization, nonnegative/finite mass, cover+push+fail conservation, integer/non-integer push handling, absence of endpoint accumulation, extreme-input finiteness and sign reversal. Comparable chronology/sign/leakage tests must gate M3 data construction and state updates.

If a pre-result implementation contract fails, repair it without inspecting candidate target performance, rerun the gate, and only then proceed to chronology-safe fitting. No architecture expansion or result-driven rescue is authorized.

## Closeout assertion

Phase 3 is complete. The final historical portfolio, prospective-only identities, data gates, chronology, nulls, metrics, ablations, selectivity rules, economics labeling, uncertainty protocol, leakage tests and prospective capture contracts were frozen before candidate fitting or performance inspection. Phase 4 has not begun.