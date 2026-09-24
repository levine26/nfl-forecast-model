# MARKET SAMPLE AUDIT

## Audit status

No purchase was made. No paid historical endpoint was represented as newly sampled under LevLine credentials. After the initial qualification, Phase 2 performed a free/open-source exhaustion search and inspected public real-data artifacts. No candidate outcomes or performance metrics were used.

## Public real historical samples

### `bsr-0/nfl-player-projections` historical HTTP cache

Public repository material contains cached responses from The Odds API historical NFL endpoint with verified examples in 2020, 2021, 2022, 2023 and 2024.

Observed schema elements include:
- requested/returned historical timestamp;
- `previous_timestamp` and `next_timestamp`;
- event identity and commence time;
- bookmaker identity;
- bookmaker `last_update`;
- h2h, spread and total markets;
- point and price fields.

This establishes that provider-origin, timestamped, multi-book historical NFL market data for the intended era is publicly observable.

**Fail-closed timing rule:** the repository's backfill code generally requested one fixed UTC snapshot per game date. An older request time can equal kickoff for common 1 p.m. ET games and can be post-kick for earlier games. Therefore each cached observation must be joined to authoritative kickoff. Equal-to-kickoff and post-kick rows are rejected. A valid earlier daily snapshot remains `PREKICK_TIMESTAMPED_NONHORIZON` unless it actually satisfies a frozen horizon's at-or-before selector.

**Rights rule:** the repository has no clear data redistribution license. Record schema/provenance findings and citations; do not assume public hosting grants permission to redistribute raw commercial-origin cache data.

### `bobby-king3/nfl-market-movement-tracker`

The public GitHub release exposes a roughly 137 MB DuckDB historical-odds artifact. Project documentation states:
- 2025 NFL season;
- 1.8M+ rows;
- 636 snapshots;
- four captures per day;
- 30+ operators;
- spreads, totals and head-to-head.

This is a real multi-book timestamped validation corpus for canonicalization and selector testing. Four captures/day do not guarantee T-60/T-30 coverage; actual game × horizon coverage remains `UNMEASURED_FREE_RECONSTRUCTION_PENDING`.

The repository does not declare a clear data license, so raw redistribution is not assumed.

### Australia Sports Betting workbook

A public mirror/parser/audit confirms broad historical NFL opening-line data through recent seasons, including opening spread, total and recent home/away moneyline fields. This source is useful to validate joins/signs/openers but remains `OPEN_ONLY` for frozen-horizon purposes.

### SportsbookReviewsOnline

Public archives/mirrors expose historical NFL Open/Close fields through approximately 2021, with parsing quirks documented by open-source projects. This is an independent opener/close cross-check, not an exact-horizon substitute.

### Older VegasInsider Wayback reconstruction

Public research artifacts document thousands of archived historical pages with archive timestamps, multi-book markets and strict pre-kick filtering in the older era. Row-level exact-horizon use remains conditional on archive-time provenance; this source does not solve 2020–2024 by itself.

## Commercial source semantics retained as fallback evidence

### The Odds API
- Historical featured-market archive from 2020-06-06.
- Closest stored snapshot equal to or earlier than requested timestamp.
- 10-minute cadence initially; 5-minute cadence from September 2022.
- Multi-book h2h/spreads/totals with point/price.
- Commercial fallback only; no purchase made.

### SportsDataIO
- Public schema confirms sportsbook identity, Created/Updated timestamps, spread numbers, side payouts, moneylines and totals.
- Historical revision coverage not newly sampled under LevLine credentials.

### PropLine
- Public docs confirm timestamped line-history shape.
- Archive begins April 2026 for this program's purposes.
- Pre-2026 historical M1 suitability: `NO`.

## Scientific consequence

Phase 2 no longer supports the statement that empirical M1 work necessarily requires a purchase. It supports a narrower statement: **complete season × book × fixed-horizon coverage is still unmeasured**. A free-first reconstruction audit must measure that coverage before any commercial pull is reconsidered.