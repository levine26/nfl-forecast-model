# LevLine Phase 2 — market reliance, source breadth, and lock horizon

Status: **research only**. This document does not authorize any production probability,
market-source, refresh-cadence, or lock-window change.

## Questions

Phase 2 must answer four distinct empirical questions:

1. How much incremental information does the current football-only signal add once market
   information is known?
2. What market dependence produces the best chronology-preserving probability forecasts:
   football-heavy, balanced, market-heavy, or market-only?
3. Does the answer change when the market is a robust multi-book consensus rather than the
   current single upstream moneyline field?
4. Does a later final lock (especially T-25) materially improve Brier score, log loss,
   calibration, and winner accuracy enough to justify the operational tradeoff?

The pre-week forecast remains a permanent accountability snapshot even if a later official
lock is eventually selected.

## Current production market

Production currently receives `home_moneyline` and `away_moneyline` from nflverse's games
feed and converts the pair to a vig-free home probability. The feed does not provide LevLine
with per-book provenance in the production row. That is simple and reproducible, but it
prevents us from measuring cross-book dispersion, stale-book risk, or whether one provider
is driving an unusual move.

Phase 2 therefore leaves production untouched while introducing a provider-neutral research
schema with one row per game, source and timestamp.

## Sportsbook composite research

The preferred first prospective multi-book source is The Odds API because one US-region H2H
request can return current NFL moneylines for multiple books, including major US books such
as DraftKings, FanDuel and BetMGM. The current API pricing page advertises a free 500-credit
monthly tier; one `h2h` market request for one region costs one credit. Featured pre-match
odds are documented as updating approximately every 60 seconds.

References:
- https://the-odds-api.com/
- https://the-odds-api.com/liveapi/guides/v4/
- https://the-odds-api.com/sports-odds-data/update-intervals.html

Research transformations:

- de-vig every sportsbook independently before aggregation;
- preserve every individual book probability and timestamp;
- derive a robust sportsbook consensus using median logit probability by default;
- measure cross-book dispersion, missing books, stale sources, and consensus sensitivity;
- keep equal/robust weighting precommitted unless earlier-season evidence supports a
  different weighting rule;
- never tune source weights on 2026 outcomes.

A sportsbook consensus is not automatically superior to the current nflverse field. It must
win the same paired, chronology-aware evaluation.

## Prediction exchanges

Prediction exchanges are a separate source family, not interchangeable sportsbook rows.
Their probabilities can reflect different participants, liquidity and microstructure.
Accordingly, research must report sportsbook consensus, exchange consensus, and any combined
consensus separately before considering a mixed-source market feature.

### Polymarket

Public read APIs expose market metadata and CLOB price/history data without authentication.
It is a plausible research source if an exact NFL game market exists and passes identity,
liquidity, bid/ask and timestamp checks. Before persistent collection or public
redistribution, source terms and redistribution rights must receive a separate review.

Research requirements include stable event mapping, bid/ask midpoint rather than blindly
using a last trade, minimum liquidity/depth, and exclusion of ambiguous or non-equivalent
contracts.

Reference: https://institute.polymarket.com/data

### Kalshi

Do **not** ingest, cache, aggregate, store, or republish Kalshi API data for LevLine under the
current research plan. Kalshi's current developer agreement says API use is limited to
facilitating a member's own trading and expressly restricts collecting/caching/aggregating
API data for other purposes without authorization. Kalshi can be reconsidered only after a
separate rights review or written authorization.

References:
- https://help.kalshi.com/en/articles/13823854-kalshi-api
- https://kalshi-public-docs.s3.amazonaws.com/Kalshi-Developer-Agreement.pdf

## Refresh cadence and cost discipline

The repository is public, so standard GitHub-hosted Actions do not consume paid Actions
minutes. The expensive part is therefore external data quota and unnecessary full-model
recomputation, not the standard runner itself.

The football signal should not be refit every five minutes. Near kickoff, Phase 2 should
reuse the already-materialized football probability and cheaply refresh only market data,
then score the frozen F-ST formula in research mode.

Proposed no-paid-data cadence:

- keep the existing early/pre-week forecast;
- keep ordinary hourly production market refreshes unchanged during research;
- add research-only dense sportsbook capture from roughly T-65 through T-10;
- target a five-minute capture cadence inside that window when a game cluster is due;
- retain explicit T-120, T-90, T-60, T-45, T-30, T-25 and T-15 snapshots;
- use a quota reserve so the collector stops before exhausting a free API allowance;
- call the multi-book endpoint once per due time bucket, not once per game or bookmaker.

Because one NFL request returns the active slate, clustered polling is much cheaper than
per-game polling. The final schedule should be budgeted against observed monthly credit use,
including international, Saturday and holiday games.

## Lock-horizon experiment

T-25 is a hypothesis, not a foregone conclusion. Later locks can gain injury/inactive and
market information, but they also increase operational failure risk and reduce the buffer
for publication problems.

The prospective horizon ledger selects the latest snapshot **at or before** each target;
it never fills an earlier horizon with later information. The decision comparison is paired
by game and blocked by NFL week.

Primary decision metric: Brier score. Secondary metrics: log loss, calibration intercept and
slope, winner accuracy, missing/stale snapshot rate, and operational capture success.

A later lock can replace T-120 only if the improvement is material and uncertainty-supported,
not merely numerically smaller on a small sample. The final policy should also require an
operational fallback: if the later source is unavailable, the last valid earlier locked
forecast remains authoritative.

## Production firewall

During Phase 2:

- F-ST-01-FROZEN-2026 remains production;
- the official T-120 lock remains production policy;
- no 2026 outcome may select a new market weight, provider weighting, model coefficient, or
  architecture;
- 2026 outcomes may evaluate precommitted lock-horizon/source variants prospectively;
- all new source and horizon artifacts remain under research-only paths;
- any later production change requires its own frozen candidate, validation evidence and
  explicit authorization.
