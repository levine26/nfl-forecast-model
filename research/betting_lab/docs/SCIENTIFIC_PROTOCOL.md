# Betting Lab Scientific Contract (research only)

## Identity and boundaries

- New program: `LEVLINE-BETTING-LAB-RESEARCH-V02`.
- Do **not** mutate `outputs/this_week.csv`, `outputs/prediction_history.csv`, F-ST training artifacts, official locks, Sunday Signal site, production workflows, or frozen ATS/LevLine 4 candidates.
- No spending, bets, account access, production promotion, or scheduled jobs are authorized.
- The 2022–2025 NFL outcomes have been repeatedly used for LevLine development; they are NOT untouched confirmation evidence for another post-hoc strategy.
- All newly imported research results must maintain as-of provenance and source hashes. No backdating or reconstructed quote-timestamps.
- Injury-report integration is explicitly excluded by user direction. This limits predictive completeness; it does not allow fabricated assertions that injuries were checked.

## Data schema

Required per quote: provider/book, market, game/player identity, selection, American odds, line, quote-capture timestamp, kickoff timestamp, decision timestamp, source, model version. Require both sides to estimate vig-free market probabilities; otherwise report only quoted payoff economics. Distinguish truly timestamped quotes from screenshots and from historical *closing* lines. Source capture can be manual or connected Alexandria where permitted, never imply book quotes have per-book timestamps if not published.

Required per prediction: immutable model version, feature as-of time strictly before kickoff, prediction time, decision time, and full probability vector including pushes for integer spread/total markets. Results are grade-only and cannot enter feature computation.

Player-history features include last completed game values **only after** documented publication time. Current-game realized targets, redzone touches, yards, and TDs cannot enter same-game features. Missing source fields remain missing with indicators.

## Research evaluation

Primary: calibrated win/push/loss probabilities (proper log score and relevant Brier/CRPS); market-only comparator on identical observations, identical horizon. Secondary: flat-stake realized ROI on actual recorded book/price/selection, sensitivity to vig, sourced closing-line value, positive share over multiple seasons; bootstrap resampling by season/week groups. A model-side ATS >52.38% at -110 is not sufficient without unbiased prices and confidence intervals.

Compare: odds-only baseline; current F-ST game win probability where applicable; market-only margin/total distribution; shadow model with football features; player TD baseline; player TD trained candidates. No claims of added value unless paired heldout/forward tests exceed market-only with uncertainty.

Qualify moneylines separately from spread-cover probabilities. Do not transform F-ST win confidence to tease probabilities. Model margins must not be treated as fair spreads without calibration.

## Bet construction

For correlated same-game bets, price all legs from a *shared score/player-outcome scenario*; no independent multiplication. For cross-game parlays, independently simulated games are a provisional assumption and must be stress tested for slate-level common factors. Full bookmaker parlay price and settlement determine return. Push rules unknown => fail closed. Never decompose same-game parlays into independent legs when they were priced as a package.

Teaser bookmaker point increments, reprice/void/lose-on-push treatment, and minimum leg requirements are explicit external contracts. Avoid treating the synthetic 3/7 behavior as estimated empirical key mass. Do not assert a positive EV merely because teased lines cross 3 and 7.

## Portfolio selection

Use quote-specific win/push/loss plus probability uncertainty (lower bound), and positive expected return *after vig* as gates. Control team/game/slate concentration and $45 user total session risk. No action when evidence is incomplete. Allow paper-stake recommendations only; automation places no bets.

## Promotion gate

No transfer into LevLine unless user separately approves after immutable prospective validation, independently qualified price feed, no-leak provenance, market-only superiority on proper scoring, economic results with week-block confidence intervals, stable CLV, robust cross-period coverage, implementation CI, and red-team review. Any new predictive candidate needs its own preregistration/freeze **before** opening new holdout results.