# FREE M1 RECONSTRUCTION AUDIT

**Program:** `LEVLINE_ATS_FRONTIER_V2`  
**Phase:** 3 — Final Architecture Design & Preregistration  
**Audit class:** outcome-blind market-data reconstruction / provenance only  
**Completed-2026 outcomes used:** `0`  
**Candidate performance inspected:** `NO`

## Executive decision

The free-source audit does **not** establish a coherent multi-season historical implementation of `FRONTIER-M1-DYNAMIC-MARKET-STATE` at the frozen fixed horizons. The historical M1 state is therefore:

`BLOCKED_PENDING_PAID_SOURCE`

This is a data/provenance decision, not a forecasting result. No historical odds purchase is authorized by this audit.

The mechanism remains scientifically viable prospectively, and the 2025 public corpus remains useful for schema/cadence validation. It does not qualify as a substitute for the required 2020–2025 fixed-horizon path.

## Frozen selector

For horizon `H`:

`target_timestamp = kickoff_timestamp_utc - H`

A quote is eligible only when:

`quote_timestamp_utc <= target_timestamp`

Selection is the latest eligible quote separately by provider, bookmaker, market and side. Equal-kick and post-kick quotes are rejected. Future-nearest-neighbor matching, interpolation from future quotes, closing-line backfill and opener/close relabeling are prohibited.

## Sources audited

### 1. `bsr-0/nfl-player-projections` public The Odds API cache

The public repository contains provider-origin historical cache payloads with provider `timestamp`, `previous_timestamp`, `next_timestamp`, event commence time, bookmaker identity, and `h2h`, `spreads`, and `totals` markets including line/price fields.

The repository's own scraper establishes the critical limitation. Its historical game-level bulk sweep used one fixed UTC snapshot per gameday. The older `17:00 UTC` setting was explicitly recognized as unsafe: during EDT it equals the standard 1 p.m. ET kickoff and is after earlier international kickoffs. The code records a measured contamination example of 11 of 2,293 game-odds events with `fetched_at > commence_time`, worst by 205 minutes. The later setting moved the bulk sweep to `12:00 UTC`, which is pre-kick but deliberately a gameday-morning line rather than a near-close path.

**Qualification:** genuine provider-origin evidence, but the bulk historical structure is sparse. It can supply valid pre-kick observations when row timestamps pass, but it cannot by itself reconstruct a dense modern multi-book path at T-720/T-360/T-120/T-60/T-30 across 2020–2024. Equal/post-kick rows must fail closed.

**Temporal class:** `PREKICK_TIMESTAMPED_NONHORIZON` unless an individual row independently satisfies a frozen target.  
**Rights class:** `LICENSE_REVIEW_REQUIRED` unless a more permissive artifact-specific license is proven.

### 2. `bobby-king3/nfl-market-movement-tracker` 2025 DuckDB release

The public project documents:

- full 2025–2026 NFL season;
- The Odds API historical endpoint;
- four captures per day at 02:00, 14:00, 18:00 and 22:00 UTC;
- 636 total snapshots;
- 1.8M+ rows;
- 30+ operators;
- spreads, totals and head-to-head markets;
- line and price fields;
- `captured_at` and `game_start_time` in its transformed line-movement model.

The latest public release asset inspected in this audit is `v1.1.1`, `nfl_odds.duckdb`, 137,375,744 bytes, published 2026-02-24, with published SHA-256 `b03c4e7f1cf885e9f20ea808ee538c26c21df4065b342fe04c50d09b808c344c`.

The cadence is scientifically important. Four fixed captures per day are enough to validate canonical schemas, bookmaker continuity and coarse market movement, but they do not produce a fresh quote at every frozen near-kick horizon. T-120, T-60 and T-30 can legitimately select the same stale capture; absence of a later capture may not be silently repaired. That is not the intended dynamic near-kick M1 path.

The raw binary release could not be row-scanned by the connected execution environment in this Phase-3 run. Therefore the audit **does not claim** season×game×book×horizon coverage percentages from that asset. Repository-level counts/cadence are accepted as source metadata only. The absence of a row-level panel is itself a failure of the Phase-3 historical qualification gate rather than a license to infer completeness.

**Temporal class:** `EXACT_TIMESTAMPED_MULTI_BOOK` for rows that pass the at-or-before selector; corpus cadence remains coarse.  
**Rights class:** `LICENSE_REVIEW_REQUIRED`; no repository license was identified by the GitHub search used in this audit. Raw redistribution is not authorized.

### 3. Open/close archives

Australia Sports Betting, SportsbookReviewsOnline/SBR mirrors, and the independently documented open/close sample are useful for sign, join and broad market-consistency checks. They do not provide quote-time paths and are retained only as `OPEN_ONLY` and/or `CLOSE_ONLY` evidence.

They are never T-2160/T-720/T-360/T-120/T-60/T-30 substitutes.

### 4. VegasInsider / Wayback reconstruction

Older archived multi-book observations remain legitimate where archive timestamps prove point-in-time availability. Phase-2 evidence was strongest in the older 2005–2016 era. This source does not solve the coherent 2020–2025 modern-panel requirement and is not pooled across eras merely to increase sample size.

### 5. nflverse schedule odds

Retained exactly as:

`HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`

They are useful for market-null compatibility but are not fixed-horizon M1 history.

### 6. PropLine / current public endpoints

PropLine's relevant archive begins in 2026 and remains prospective-only for the pre-2026 historical program. Action Network/ESPN-style current endpoints are prospective/corroborative unless concrete same-book historical time series prove otherwise.

## Frozen horizon findings

See `M1_HORIZON_COVERAGE.csv`. The critical finding is not that no free quote ever exists at a target. It is that the audit cannot demonstrate a coherent 2020–2025 season×game×book panel with the required fields and sufficient temporal freshness at the complete frozen horizon grid.

- T-2160: public sources can contain eligible observations, but continuity by game/book/season is not demonstrated.
- T-720: same limitation.
- T-360: same limitation; 2025 four-per-day cadence can support some at-or-before observations but freshness varies materially.
- T-120: modern multi-book path is not demonstrated across 2020–2025; 2025 may carry a stale prior capture.
- T-60: same deficiency, stronger freshness concern.
- T-30: same deficiency, strongest freshness concern.
- latest pre-kick: sparse bulk archives cannot be relabeled as latest pre-kick; a row must actually be the latest observed pre-kick quote within a sufficiently dense source.

## Field findings

### Spread line
Present in the qualified public The Odds API structures and 2025 corpus metadata.

### Spread side price
Present in the provider-origin structures; historical row-level completeness over the intended panel is not demonstrated.

### Moneyline
Present in the provider-origin `h2h` structures and 2025 corpus metadata; row-level completeness over the intended panel is not demonstrated.

### Total
Present in the provider-origin structures and 2025 corpus metadata; row-level completeness over the intended panel is not demonstrated.

### Book identity
Present in the provider-origin structures. Cross-season stable continuity and rename normalization over a complete 2020–2025 panel are not demonstrated by the free audit.

## Rejection / uncertainty findings

- Equal/post-kick rejection is mandatory. The BSR scraper itself documents a nonzero historical contamination problem under the earlier fixed-time configuration.
- Four-capture/day 2025 data are exact timestamps, but exact timestamp validity is not the same as near-horizon freshness.
- Duplicate/conflicting quotes and bookmaker rename conflicts require row-level normalization before historical use; this audit does not pretend those counts were measured without ingesting the raw asset.
- Rights uncertainty is tracked independently of temporal validity.

## Why the free data fail the historical M1 gate

M1 is not generic line movement. It requires dynamic information within the market process after conditioning on contemporaneous market level. A coherent historical candidate therefore needs a comparable multi-season panel of identifiable books, spread line + side price, moneyline and total at reproducible at-or-before horizons.

The free evidence is fragmented:

1. 2020–2024 provider caches are genuine but largely one-snapshot-per-gameday in the bulk path and include a documented timing defect in the older configuration.
2. 2025 is much denser and genuinely multi-book, but four fixed captures/day are too coarse to represent the full frozen near-kick path and the row-level coverage panel was not reproducibly materialized in this execution.
3. opener/close files are horizon-opaque by construction.
4. older Wayback PIT data are from a different, heterogeneous era and do not establish a modern 2020–2025 panel.

Broadening eras, carrying stale observations, or mapping opener/close to fixed horizons would solve sample size by violating the scientific contract.

## Paid-data deficiency statement

The missing object is:

> A reproducible 2020–2025 NFL multi-book quote panel with provider/book/event identity, spread line and side price, moneyline, total, quote timestamp and kickoff timestamp, dense enough to reconstruct the frozen at-or-before horizons—especially T-360/T-120/T-60/T-30 and latest-pre-kick—without future interpolation or stale-source relabeling.

### First fallback: The Odds API

The documented historical endpoint directly matches the at-or-before selector and provides bookmaker-level spreads/prices, h2h and totals. A commercial qualification pull should be bounded to the exact seasons, horizons and markets above. **No purchase is authorized in Phase 3.**

### Second fallback: SportsDataIO

Use only if a concrete historical line-movement sample proves the required bookmaker, line, price and revision timestamps. Commercial licensing/export semantics must be confirmed before qualification.

## Audit conclusion

Historical M1 is `BLOCKED_PENDING_PAID_SOURCE`. It is **excluded from Phase-4 historical candidate fitting** unless a new, explicitly governed data-qualification amendment is completed before any M1 target performance is viewed.

Prospective M1 remains viable and is protected by `PROSPECTIVE_MARKET_CAPTURE_SPEC.md` so this data deficiency is not repeated.

No model outcomes were used to reach this decision.