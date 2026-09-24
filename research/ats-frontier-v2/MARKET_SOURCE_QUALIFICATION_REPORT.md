# MARKET SOURCE QUALIFICATION REPORT

**Evidence cutoff:** 2026-09-23

## Revised Phase-2 access conclusion

The original commercial-provider qualification remains valid, but a subsequent free/open-source exhaustion search found enough real historical market evidence to require a free-first reconstruction audit before any purchase. `FRONTIER-M1-DYNAMIC-MARKET-STATE` remains `PARTIALLY_QUALIFIED`; the reason is now **unmeasured exact-horizon completeness**, not an assumption that historical data can only be obtained by paying.

See `FREE_MARKET_DATA_DEEP_DIVE.md` for the full evidence inventory.

## Public provider-origin historical cache — `bsr-0/nfl-player-projections`

**Classification:** `PREKICK_TIMESTAMPED_NONHORIZON` by default; individual observations may become exact-horizon evidence only if their real timestamp satisfies the frozen selector.

Publicly committed cache material contains genuine The Odds API historical NFL responses with verified examples in 2020, 2021, 2022, 2023 and 2024. Payloads preserve requested/returned historical timestamps, previous/next snapshot timestamps, event commence time, bookmaker identity, bookmaker last-update, h2h/spreads/totals, point and price.

The repository's bulk extraction code also reveals a material limitation: it generally requested one UTC snapshot per game date, and an older request time can equal kickoff for common early games or occur after earlier kickoffs. Therefore every observation must be joined to authoritative kickoff and fail closed if it is not strictly pre-kick. A daily snapshot cannot be relabeled as T-360/T-120/T-60/T-30 merely because it is historical.

**Rights:** repository has no clear data redistribution license. Treat as `LICENSE_REVIEW_REQUIRED`; public visibility is not a grant to redistribute the underlying commercial-origin cache.

## Public dense 2025 corpus — `bobby-king3/nfl-market-movement-tracker`

**Classification:** real timestamped multi-book 2025 validation corpus; per-horizon usability must still be measured with the frozen at-or-before selector.

The public release contains `nfl_odds.duckdb` (roughly 137 MB). The project documents 1.8M+ rows, 636 captures, four collection times per day, 30+ operators, and spreads/totals/head-to-head across the 2025 NFL season. It is useful for schema validation, book identity/continuity, dispersion and real timestamp-selector testing.

Four captures per day do not imply T-60/T-30 coverage. The repository does not declare a clear data redistribution license, so treat the raw release as `LICENSE_REVIEW_REQUIRED`.

## Free opener/close benchmarks

### Australia Sports Betting

A public GitHub mirror/parser/audit (`koltbern15/Sports-Betting`) confirms a historical NFL workbook with opening spread, opening total and opening home/away moneyline fields and broad coverage into 2025. This materially improves free opener coverage, including 2022–2024.

**Classification:** `OPEN_ONLY` for fixed-horizon purposes unless an independent timestamp proves otherwise.

### SportsbookReviewsOnline / SBR mirrors

Public archives and an MIT-licensed scraper preserve long-run NFL open/close data through approximately 2021. They are useful for independent sign/join/movement validation.

**Classification:** `OPEN_ONLY` / `CLOSE_ONLY`; never substitute them for an exact T-minus horizon without quote-time evidence.

## Older archived PIT — VegasInsider/Wayback reconstruction

The public `ryanpmcintire/nfl_py3` research artifacts document a large older Wayback reconstruction using archive timestamps with strict pre-kick logic and multiple books/markets, especially across the pre-JS era through 2016.

**Classification:** `EXACT_TIMESTAMPED_MULTI_BOOK` only for rows that independently pass the archive-time provenance and at-or-before rules. This is useful older-era PIT validation but does not by itself fill 2020–2024.

## Action Network

Public endpoints and open-source collectors expose real book-level current odds. Public repositories also contain 2016–2025 season/week parquets. However, one data-pump implementation stamps ingestion time at collection and deduplicates to the latest quote per book, while other open-source implementations warn that richer line history can be gated behind logged-in Pro/EDGE access.

**Classification:** `PROSPECTIVE_OR_HORIZON_OPAQUE` unless a concrete payload proves same-book, time-ordered historical revisions for the specific game/market.

## ESPN

Public/undocumented odds and movement endpoints are useful for live/prospective corroboration, but completed-game movement retention was not sufficiently verified to claim retroactive fixed-horizon history.

**Classification:** `PROSPECTIVE_ONLY` until historical retention is independently demonstrated.

## ParlayAPI

A free tier exists, but current free historical depth is too short to serve as a 2020–2025 backfill.

**Classification:** `PROSPECTIVE_ONLY` for this historical program.

## Betfair historical data

The BASIC historical tier is free, but higher temporal granularity belongs to paid historical packages and the exchange is not a multi-sportsbook consensus substitute. US account availability is also a practical limitation.

**Classification:** `SUPPLEMENTAL_NOT_M1_SUBSTITUTE`.

## The Odds API

**Classification:** strongest commercial fallback, not current purchase recommendation.

First-party documentation states that featured-market historical snapshots are available from 2020-06-06; cadence is 10 minutes initially and 5 minutes from September 2022; a historical request returns the closest snapshot **equal to or earlier than** the requested timestamp. Featured NFL markets include moneyline, spreads and totals. The response preserves bookmaker identity and outcome `price` / `point`.

Sources:
- https://the-odds-api.com/historical-odds-data/
- https://the-odds-api.com/liveapi/guides/v4/
- https://the-odds-api.com/

**Phase-2 conclusion:** provider semantics match the M1 PIT contract. No purchase is justified until the free-first reconstruction audit quantifies the residual gap.

## SportsDataIO

**Classification:** credible commercial alternative.

First-party NFL data dictionaries expose `GameOdd` records with `Sportsbook`, `Created`, `Updated`, moneyline, point spread/payout and total/over-under payout. Workflow documentation describes pre-game opening/change/closing behavior; historical access remains product/licensing dependent.

Sources:
- https://discoverylab.sportsdata.io/developers/data-dictionary/nfl
- https://sportsdata.io/developers/workflow-guide/nfl
- https://sportsdata.io/historical-odds
- https://sportsdata.io/help/historical-data-integration-guide

## PropLine

**Classification:** `PROSPECTIVE_ONLY` for the Frontier historical program.

First-party documentation provides per-event odds history, change-only history, opening/closing helpers, `recorded_at`, book-level fields and Pinnacle-related metadata. Its usable archive for this program begins in April 2026.

Source: https://prop-line.com/docs

## Existing nflverse schedule odds

Retain classification: `historical_closing_late_benchmark_exact_horizon_opaque`. Do not relabel schedule `spread_line` / `total_line` fields as exact T-120/T-60/open/close observations.

## Rights rule

Every free source receives a separate rights status: `LICENSE_CLEAR`, `LICENSE_REVIEW_REQUIRED`, or `NO_REDISTRIBUTION_ASSUMED`. Public GitHub visibility does not itself authorize redistribution or commercial reuse.

## M1 gate

`PARTIALLY_QUALIFIED__FREE_FIRST_RECONSTRUCTION_REQUIRED`.

The required PIT shape demonstrably exists, and meaningful pieces of the intended historical era are publicly observable. What remains unresolved is empirical **season × game × book × fixed-horizon** completeness under the frozen schema. Measure that free reconstruction before revisiting a commercial qualification pull.