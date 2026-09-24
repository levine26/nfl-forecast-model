# PAID DATA RECOMMENDATION

No purchase was made in Phase 2.

## Current decision — DO NOT PURCHASE YET

A subsequent free/open-source exhaustion search materially changed the access recommendation. Phase 2 found genuine public historical market artifacts spanning the required era, including provider-origin The Odds API historical-cache payloads for 2020–2024 and a dense public 2025 multi-book release. These sources do not yet establish complete exact-horizon coverage, but they are sufficient to require an empirical **free-first reconstruction audit** before any paid acquisition is justified.

`FRONTIER-M1-DYNAMIC-MARKET-STATE` therefore remains `PARTIALLY_QUALIFIED`; it is not blocked solely because the canonical commercial archive is paid.

See `FREE_MARKET_DATA_DEEP_DIVE.md` for the source-by-source evidence and fail-closed rules.

## Free-first requirement

Before spending money, measure the free-source reconstruction outcome-blind across the intended research universe:

- book/game/market joins;
- quote timestamps versus authoritative kickoff;
- spread line **and side price** completeness;
- moneyline and total completeness;
- active-book count and book continuity;
- T-2160/T-720/T-360/T-120/T-60/T-30/latest-pre-kick coverage separately;
- quote age at each horizon;
- post-kick/equal-kick rejection counts;
- provenance and redistribution/license status.

Openers, closes, one-per-day snapshots and horizon-opaque schedule lines remain benchmarks only unless their timestamps actually satisfy the frozen horizon selector.

## Commercial fallback only if the free audit fails

### First fallback: The Odds API

The Odds API remains the strongest first commercial qualification source if the free audit demonstrates scientifically inadequate exact-horizon coverage.

Why:
- historical featured-market archive from 2020-06-06;
- NFL moneyline, spreads and totals;
- multi-book structure;
- snapshot timestamp returned at or before requested time;
- 10-minute archive cadence initially, 5-minute cadence from September 2022;
- public docs make the PIT selection semantics unusually explicit.

At the Phase-2 evidence cutoff, the public 20K plan was listed at approximately $30/month and included historical odds. Historical requests consume credits by regions/markets, so any later purchase should still begin with a bounded qualification pull rather than an indiscriminate full-archive extraction.

Sources:
- https://the-odds-api.com/historical-odds-data/
- https://the-odds-api.com/liveapi/guides/v4/
- https://the-odds-api.com/

### Alternative: SportsDataIO

SportsDataIO remains the alternative. Its NFL `GameOdd` schema contains sportsbook identity, Created/Updated timestamps, spread-side payouts, moneylines and totals, and its workflow documentation describes line movement. Historical/Vault/commercial access remains product/licensing dependent.

Sources:
- https://discoverylab.sportsdata.io/developers/data-dictionary/nfl
- https://sportsdata.io/developers/workflow-guide/nfl
- https://sportsdata.io/historical-odds

## Sources that do not eliminate the historical exact-horizon gap by themselves

- PropLine: valuable prospective history, but archive begins 2026-04 for this program's purposes.
- ParlayAPI free access: useful for recent/prospective testing, not a free 2020–2025 deep archive.
- Action Network anonymous public scoreboard: useful current/book-level evidence, but retroactive dense same-book quote history is not sufficiently established.
- ESPN movement endpoints: useful prospectively, but completed-game historical retention is not sufficiently established.
- nflverse schedule odds: closing/late benchmark with exact horizon opaque.
- Betfair BASIC: free historical package is lower-granularity and is not a substitute for the required dense multi-book sportsbook path; US account availability is also a practical limitation.

## What remains unresolved without the free reconstruction audit

- season × book × horizon coverage percentages;
- exact spread-side-price completeness at the frozen horizons;
- multi-book continuity over the intended training era;
- quote-age/path-density distributions;
- empirical leader/follower reconstruction coverage;
- whether a free-only M1 architecture can be frozen without distorting the Phase-1 mechanism.

Historical timestamped market data remains the only paid-data category that could eventually be justified by this program, but **no historical odds purchase is currently recommended or authorized**.