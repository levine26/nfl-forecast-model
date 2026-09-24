# FREE MARKET DATA DEEP DIVE

**Program:** `LEVLINE_ATS_FRONTIER_V2`  
**Phase:** 2 — Data Qualification, PIT Reconstruction & Mechanism Feasibility  
**Evidence cutoff:** 2026-09-23  
**Outcome use:** none  
**Completed-2026 outcomes used:** 0  
**Candidate performance inspected:** no

## Decision

**DO NOT PURCHASE HISTORICAL ODDS DATA YET.**

The original Phase-2 source qualification correctly established that commercial products exist with the temporal semantics needed by `FRONTIER-M1-DYNAMIC-MARKET-STATE`. A subsequent free/open-source exhaustion search materially changed the access assessment. Public repositories, archival datasets and free source endpoints contain enough genuine historical market evidence to justify a dedicated free-first reconstruction audit before any paid acquisition is authorized.

This does **not** upgrade M1 to `DATA_QUALIFIED`. Dense, exact-horizon, multi-book coverage across the intended 2020–2025 research era has not yet been empirically established for free. M1 remains `PARTIALLY_QUALIFIED`.

## Frozen M1 requirement

The Phase-1 shortlist defines M1 as a latent fair market state derived from **multi-book line + juice + moneyline + total path**. The Phase-2 schema contract therefore still requires, at minimum, identifiable provider/book/event, market/side, line, price, quote timestamp, kickoff timestamp, and preserved raw provenance. For horizon `H`, only a quote with `quote_timestamp_utc <= kickoff-H` is admissible. An opener, a close, a daily snapshot, or a quote after the target cannot be relabeled as an exact fixed horizon.

## Search scope

The free-source search included:

- GitHub repositories and release assets containing historical NFL odds data;
- raw cached historical API responses committed to public repositories;
- open-source sportsbook/market scrapers and data pumps;
- SportsbookReview/SportsbookReviewsOnline archives and mirrors;
- Australia Sports Betting historical NFL workbooks and independent parsers/audits;
- Action Network public endpoints and repositories that persist their output;
- ESPN public/undocumented odds and movement endpoints;
- nflverse schedule odds;
- ParlayAPI and other free-tier historical offerings;
- Betfair historical-data tiers;
- VegasInsider/Wayback reconstructions;
- public The Odds API-derived historical datasets/caches;
- prospective free collectors that can prevent this problem from recurring.

A source was not credited merely because code existed to call a paid endpoint. The search required either actual public historical observations, a genuinely free retrievable historical source, or a useful reproducible prospective collection path.

## Source qualification matrix

| Source | Era observed/claimed | Temporal resolution | Book identity | Spread price | ML / total | Free role | Qualification |
|---|---:|---|---|---|---|---|---|
| `bsr-0/nfl-player-projections` public HTTP cache | verified examples 2020–2024 | genuine provider snapshot timestamps, but bulk backfill often one requested snapshot/game-date | yes | yes | yes | historical PIT evidence | `PREKICK_TIMESTAMPED_NONHORIZON` unless a row independently lands at a frozen horizon |
| `bobby-king3/nfl-market-movement-tracker` release | 2025 season | 4 captures/day; 636 snapshots | 30+ books | yes | yes | dense 2025 multi-book path audit | `EXACT_TIMESTAMPED_MULTI_BOOK`, subject to per-target at-or-before selection and rights review |
| Australia Sports Betting workbook mirrored/audited in `koltbern15/Sports-Betting` | ~2006–2025/26 | open/close fields, not quote-time path | source-level only | opening line; price fields in workbook | opening ML/total | opener benchmark | `OPEN_ONLY` for horizon purposes |
| SportsbookReviewsOnline / SBR mirrors | ~2007–2021 | open/close | source-level | open/close | total; ML semantics require field-specific care | independent opener/close benchmark | `OPEN_ONLY` / `CLOSE_ONLY`, never exact horizon |
| `ryanpmcintire/nfl_py3` VegasInsider Wayback reconstruction | strong archived PIT in older era, especially 2005–2016 | archived page timestamps; many kickoff-window captures | multiple books | yes where parsed | ML/total where parsed | older PIT validation/reconstruction | `EXACT_TIMESTAMPED_MULTI_BOOK` only for rows passing strict archive-time provenance |
| `theedgepredictor/odds-data-pump` / public fork | 2016–2025 | stored latest-per-book state; ingestion timestamp is not original quote timestamp | yes | yes | yes | book-level historical end-state benchmark | `HORIZON_OPAQUE` |
| Action Network anonymous public scoreboard | broad | current/latest; public historical line path not reliably preserved | yes | current | current | prospective collection / end-state cross-check | `PROSPECTIVE_OR_HORIZON_OPAQUE` |
| ESPN public odds/movement endpoints | current/broad event history | movement retention for completed games not sufficiently verified | provider-dependent | current | current | prospective/current corroboration | `PROSPECTIVE_ONLY` until historical retention is proven |
| nflverse schedule odds | long history | one late/closing-like game-level state; exact quote time opaque | no reliable multi-book path | line only/limited price semantics | total/ML fields vary | benchmark | `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE` |
| PropLine | archive starts 2026-04 | timestamped history | yes | yes | yes | prospective | `PROSPECTIVE_ONLY` for pre-2026 program |
| ParlayAPI free tier | current free historical window is short | recent history only | multi-book | yes | yes | prospective/testing | `PROSPECTIVE_ONLY` for 2020–2025 backfill |
| Betfair BASIC historical data | older archive available | free tier is lower granularity than the 1-minute ADVANCED product; US account availability is an additional blocker | exchange, not sportsbook consensus | exchange prices | market-dependent | supplemental only | `SUPPLEMENTAL_NOT_M1_SUBSTITUTE` |
| The Odds API paid archive | 2020-06-06+ | documented 10-min, then 5-min; at-or-before response semantics | yes | yes | yes | paid fallback | `COMMERCIAL_FALLBACK` |
| SportsDataIO historical odds | 2018 schema+ | documented revision/line-movement structure | yes | yes | yes | paid alternative | `COMMERCIAL_FALLBACK` |

## Most important discovery: public raw The Odds API historical caches

The repository `bsr-0/nfl-player-projections` publicly commits cached responses from requests to The Odds API historical NFL endpoint. Inspection found genuine payloads for 2020, 2021, 2022, 2023 and 2024 containing:

- requested historical timestamps;
- returned `timestamp`, `previous_timestamp`, and `next_timestamp` values;
- event/commence time;
- bookmaker identity;
- `h2h`, `spreads`, and `totals` markets;
- bookmaker `last_update` values;
- line/point and price fields.

This is materially stronger than a derived closing-line CSV because the cached payload preserves provider-origin temporal and bookmaker structure.

### Critical limitation

The same repository's extraction code shows that its bulk historical backfill generally requested one fixed UTC snapshot per game date. An older setting used approximately 17:00 UTC; the code comments recognize that this can equal kickoff for 1 p.m. ET games and fall after kickoff for earlier games, and a later setting moved the request earlier.

Therefore:

1. every cache observation must be joined to an authoritative kickoff timestamp;
2. `returned_timestamp < kickoff_timestamp` must be demonstrated before the observation can be used as pregame evidence;
3. equal-to-kickoff and post-kick observations are rejected;
4. a valid pre-kick daily snapshot is **not** called T-360/T-120/T-60/T-30 unless it actually satisfies the frozen at-or-before selector for that target;
5. sparse public-cache coverage may supplement, but cannot fabricate, a dense market path.

## 2025 dense free validation corpus

`bobby-king3/nfl-market-movement-tracker` publishes a GitHub release containing a roughly 137 MB DuckDB database generated from The Odds API historical endpoint. The project documents 1.8M+ rows, 636 captures and 30+ operators across the 2025 NFL season, with spreads, totals and head-to-head markets captured four times per day.

This is useful for:

- validating canonical book/market normalization;
- testing the at-or-before selector on real timestamped multi-book data;
- measuring book continuity and cross-book dispersion in a real season;
- testing whether sparse fixed collection times can support any frozen horizon without relabeling;
- cross-checking 2025 market-state schema behavior.

It does not by itself guarantee T-60/T-30 coverage, and the repository does not provide a clear data redistribution license. Raw data should therefore not be copied into LevLine as a distributable artifact without rights review.

## Open/close sources are still valuable

Australia Sports Betting and SportsbookReviewsOnline substantially improve free historical market context. They can validate:

- opener/late line sign conventions;
- game joins;
- broad line movement direction;
- moneyline/total consistency where fields are clear;
- whether a reconstructed timestamped quote is economically plausible.

They cannot replace exact quote timestamps. Phase 2 explicitly prohibits mapping `open`, `close`, or a late schedule line to a fixed T-minus horizon without timestamp evidence.

## Action Network finding

Public Action Network data is useful, but current open-source implementations expose a trap: some code describes `inserted` timestamps as line history, while other code in the same ecosystem ultimately retains one latest full-game quote per bookmaker or synthesizes an opener from different books' insertion times. Another implementation notes that richer historical line history can be gated behind a logged-in Pro/EDGE session.

Accordingly, anonymous/public Action Network output is not accepted as retroactive exact-horizon history unless a concrete payload independently demonstrates multiple time-ordered quotes for the same book/market/game with valid timestamps.

## Rights and provenance rule

Publicly accessible does not mean licensed for unrestricted redistribution or commercial reuse.

Every free-source record must receive both a temporal class and a rights class.

### Temporal class

- `EXACT_TIMESTAMPED_MULTI_BOOK`
- `EXACT_TIMESTAMPED_SINGLE_SOURCE`
- `PREKICK_TIMESTAMPED_NONHORIZON`
- `OPEN_ONLY`
- `CLOSE_ONLY`
- `HORIZON_OPAQUE`
- `POST_KICK_REJECTED`
- `UNRESOLVED`

### Rights class

- `LICENSE_CLEAR`
- `LICENSE_REVIEW_REQUIRED`
- `NO_REDISTRIBUTION_ASSUMED`

For repositories without an explicit license, the default is `LICENSE_REVIEW_REQUIRED`. LevLine may record citations, schema observations, hashes and qualification findings without treating public visibility as a license to redistribute the underlying dataset.

## Free-first empirical reconstruction gate

Before any paid historical odds purchase is reconsidered, the next M1 data audit must attempt a free reconstruction and publish, outcome-blind:

1. intended season/game universe;
2. source-specific game joins;
3. number of identifiable active books per game/market;
4. exact timestamp provenance;
5. quote age at each frozen horizon;
6. coverage for spread **line + side price**, moneyline and total separately;
7. coverage at T-2160/T-720/T-360/T-120/T-60/T-30/latest-pre-kick separately;
8. percentage rejected for post-kick/equal-kick timing;
9. source conflicts and sign/side mismatches;
10. rights class for each source/artifact.

No paid acquisition is justified merely because a free source is inconvenient. A paid qualification pull may be reconsidered only after the free audit demonstrates that M1's required multi-book timestamped path cannot be reconstructed with scientifically adequate support over the intended era.

The Phase-3 architecture may narrow M1 to the empirically supported free horizons/eras **only on coverage/provenance grounds fixed before any candidate performance is inspected**. It may not select horizons because historical ATS or ROI is favorable.

## Paid fallback if the free audit fails

If the free reconstruction fails the M1 data gate, The Odds API remains the first commercial fallback because its documentation directly matches the Phase-2 at-or-before horizon-selection rule and provides multi-book spread/price, moneyline and total snapshots. SportsDataIO remains the alternative.

This document does not authorize either purchase.

## Prospective prevention

Regardless of whether historical M1 ultimately survives, LevLine should maintain a free prospective market snapshot collector for future seasons using legally accessible current endpoints. The collector should persist raw payload hashes, provider/book IDs, provider quote timestamps, ingestion timestamps and kickoff timestamps at a cadence sufficient to reconstruct the frozen horizons. Prospective collection is separate from historical backfill and must not be used to rewrite prior seasons.

## Phase-2 conclusion

The free/open-source search materially weakens the case for paying immediately. It does **not** establish that the entire M1 historical path is already free and complete. The scientifically correct state is:

`FRONTIER-M1-DYNAMIC-MARKET-STATE = PARTIALLY_QUALIFIED__FREE_FIRST_RECONSTRUCTION_REQUIRED`

No purchase. No model training. No target-result inspection. No production change.