# M1 SOURCE DECISION

## Final Phase-3 disposition

`FRONTIER-M1-DYNAMIC-MARKET-STATE = BLOCKED_PENDING_PAID_SOURCE` for the historical 2020–2025 program.

The mechanism is retained as a prospective research program, but no historical M1 candidate enters Phase 4 from the free data presently qualified.

## Why `PARTIAL_HISTORICAL` is rejected

A narrower 2025-only candidate would create a one-season, cadence-specific experiment whose near-kick horizons frequently inherit stale fixed-time captures and whose operator/row-level coverage was not independently materialized in this execution. Combining that source with sparse 2020–2024 daily caches or older Wayback archives would change source semantics and temporal resolution across eras. That would test source artifacts as much as the intended market-state mechanism.

The program therefore does not broaden, stitch, or relabel free sources merely to preserve sample size.

## Exact deficiency

Missing: a coherent modern multi-season panel with identifiable books, spread line + side price, moneyline and total, quote timestamps, kickoff timestamps and adequate quote density to reconstruct T-2160/T-720/T-360/T-120/T-60/T-30/latest-pre-kick under the frozen at-or-before selector.

The most material gap is T-360 through latest-pre-kick, where dynamic price/path information is scientifically most relevant and the free cadence is least adequate.

## Commercial fallback order

1. **The Odds API historical archive** — first fallback because its documented historical snapshot semantics implement the required at-or-before contract and expose the needed game markets/book identities.
2. **SportsDataIO historical odds/line movement** — second fallback only after a concrete sample proves revision timestamps, bookmaker identity, line and price history at the required horizons.

No purchase is authorized.

## Current The Odds API semantics and cost check

Checked against the provider's public documentation/pricing on 2026-09-24:

- NFL featured-market historical snapshots are available from 2020-06-06;
- snapshot cadence is documented as 10 minutes historically and 5 minutes from September 2022 onward;
- the historical endpoint returns the closest available snapshot **equal to or earlier than** the requested `date`, matching the frozen at-or-before requirement;
- one historical featured-market request costs `10 × regions × markets` usage credits;
- the intended one-region request for `h2h,spreads,totals` therefore costs 30 credits per requested timestamp;
- publicly listed monthly plans at this check were 20,000 credits / $30, 100,000 / $59, 5M / $119, and 15M / $249.

The program does **not** assume a plan before generating a deduplicated request manifest. The 100K / $59 tier is the first listed tier that should be evaluated for a bounded multi-season qualification pull after timestamp deduplication, but this is neither a purchase authorization nor a guarantee that 100K credits are sufficient. Exact required credits must be computed as:

`30 × number_of_unique_historical_snapshot_timestamps_requested`

before any purchase decision.

SportsDataIO remains second fallback; a concrete historical-odds sample and current commercial quote are required before treating its product/cost as comparable. No unsupported price is recorded here.

## Minimum bounded qualification pull

If explicit user authorization is later granted, do not buy an open-ended dataset. First generate the unique requested timestamp set from the canonical NFL schedule and pull only:

- seasons 2020–2025;
- US region/bookmaker set sufficient for a stable multi-book panel;
- markets `spreads`, `h2h`, `totals`;
- frozen target timestamps T-2160, T-720, T-360, T-120, T-60, T-30 plus one latest-pre-kick qualification snapshot;
- provider metadata necessary to verify at-or-before semantics.

The qualification pull is data-only. It must not join game outcomes or candidate predictions.

## Gate to reopen historical M1

Historical M1 may reopen only through an explicit governance amendment that demonstrates, before any M1 target result is viewed:

- season×game×book×horizon coverage;
- side-price / ML / total completeness;
- quote-age distribution;
- book continuity/rename mapping;
- no post-target leakage;
- rights/license class;
- exact historical architecture fields supported by the acquired data.

Absent that amendment, Phase 4 must treat M1 as excluded historically.