# MARKET SOURCE QUALIFICATION REPORT

**Evidence cutoff:** 2026-09-23

## The Odds API

**Classification:** strongest historical M1 candidate, but historical empirical coverage remains access-gated.

First-party documentation states that featured-market historical snapshots are available from 2020-06-06; cadence is 10 minutes initially and 5 minutes from September 2022; a historical request returns the closest snapshot **equal to or earlier than** the requested timestamp. Featured NFL markets include moneyline, spreads and totals. The response preserves bookmaker identity and outcome `price` / `point`. Historical endpoints require a paid plan.

Sources:
- https://the-odds-api.com/historical-odds-data/
- https://the-odds-api.com/liveapi/guides/v4/
- https://the-odds-api.com/

**Phase-2 conclusion:** semantics satisfy the PIT direction required by M1, but no purchase was authorized, so season × horizon × book historical coverage and missingness could not be measured across the full research sample. Do not call M1 fully data-qualified from documentation alone.

## SportsDataIO

**Classification:** credible alternative historical/line-movement provider; access/licensing still material.

First-party NFL data dictionaries expose `GameOdd` records from 2018 with `Sportsbook`, `Created`, `Updated`, home/away moneyline, home/away point spread, point-spread payout, total and over/under payout. The NFL workflow guide describes pre-game line movement with opening price, all line changes and closing price. Historical/Vault access is a distinct product/access path.

Sources:
- https://discoverylab.sportsdata.io/developers/data-dictionary/nfl
- https://sportsdata.io/developers/workflow-guide/nfl
- https://sportsdata.io/historical-odds
- https://sportsdata.io/help/historical-data-integration-guide

**Phase-2 conclusion:** schema and documented line-movement semantics are suitable for M1 evaluation, but real historical revision coverage was not exhaustively audited under the no-purchase rule.

## PropLine

**Classification:** `PROSPECTIVE_ONLY` for the Frontier historical program.

First-party documentation provides per-event odds history, change-only history, opening/closing helpers, `recorded_at`, book-level fields, and Pinnacle-specific version metadata. The archive starts in April 2026; current historical depth depends on tier, with a two-year backfill product for bulk history.

Source: https://prop-line.com/docs

**Phase-2 conclusion:** useful for prospective capture and future PIT studies; not a legitimate substitute for pre-2026 historical M1 reconstruction.

## Existing nflverse schedule odds

Retain classification: `historical_closing_late_benchmark_exact_horizon_opaque`. The schedule `spread_line` / `total_line` fields are not relabeled as exact T-120/T-60/open/close observations.

## M1 gate

`PARTIALLY_QUALIFIED`.

The required data shape and PIT semantics exist commercially, most clearly through The Odds API and SportsDataIO, but Phase 2 does not possess enough authorized historical real-data access to establish empirical book/horizon completeness over the intended training period.