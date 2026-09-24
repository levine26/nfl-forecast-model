# MARKET MICROSTRUCTURE REVIEW

## Research question

Should LevLine represent the sportsbook market as a dynamic latent information state rather than one static spread number?

**Phase-1 answer:** yes, this is the strongest new information-channel hypothesis, but it is completely conditional on Phase-2 historical PIT data qualification.

## Observable market state

A defensible market state should preserve, by book and timestamp where possible:

- spread point;
- home/away side price (juice);
- total and both side prices;
- moneyline both sides;
- book identity and market family;
- open/current/defined pregame-horizon snapshots;
- quote age/staleness;
- changes in price with unchanged line;
- changes through key numbers;
- cross-book dispersion;
- number/breadth of books moving;
- velocity and direction of movement;
- lead/lag between sharper and more recreational books where classification is defensible;
- spread–moneyline and spread–total internal consistency.

## Why this may be incremental

A single consensus/closing spread is a lossy compression of a market process. Finance and betting-market literatures both treat prices as information aggregation. Sequential betting lines gain information through time, and line changes can remove opening biases. Side price often moves before a half-point line change, so ignoring juice discards sub-line information. Multi-book disagreement can encode uncertainty or stale quotes that a single consensus cannot distinguish.

The novel object is not `line_move`. It is a latent state such as:

`fair_line_t ~ f(book_quotes_t, side_prices_t, moneyline_t, total_t, quote_age_t, book_reliability)`

with innovations evaluated only after conditioning on contemporaneous level:

`path_innovation_t = observed_market_path - E(path | current_market_level, prior_state)`.

## Why this may fail

- Later consensus may already be essentially sufficient.
- Historical book panels can be sparse, survivorship-biased, renamed or timestamp-inconsistent.
- Apparent sharp-book lead/lag can be mechanical feed latency.
- Using closing or future quotes to construct earlier state would be fatal leakage.
- Movement direction can be caused by balancing/risk management rather than private information.
- Adaptive Candidate 3 already showed that simple path movement can collapse to market-level information.

## Required falsification tests

1. M1 must beat a contemporaneous market-level-only null, not merely opening line.
2. Path terms must add proper-score information after the same-timestamp consensus line + juice + moneyline + total are included.
3. Results must survive leave-one-book, leave-one-season and event-time-block tests.
4. Apparent gains must survive removal of stale/outlier books and alternative consensus definitions fixed before evaluation.
5. The data pipeline must prove that every quote used existed no later than prediction timestamp.

## Candidate architecture guidance (not frozen implementation)

Phase 3 may consider a state-space/Kalman-style latent fair-line filter, robust weighted consensus, or small regularized model over pre-specified microstructure summaries. A large unrestricted gradient-boosting feature tournament is not authorized by Phase 1.

## Scientific status

`FRONTIER-M1-DYNAMIC-MARKET-STATE` survives Phase 1 with **highest priority**, because it targets information that prior LevLine models largely discarded rather than simply re-modeling football performance.