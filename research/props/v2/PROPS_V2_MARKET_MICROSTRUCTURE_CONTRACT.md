# Props 2.0 Market Microstructure / CLV Contract

Status: **FROZEN OUTCOME-FREE FEATURE CONTRACT**  
Candidate: `P2-MICRO-V2` / `P2-CLV-V1`  
Version: `levline-props-v2-market-microstructure-v0.1.0`

## Purpose

Turn successive immutable multi-book player-prop captures into a real market state without
pretending one sportsbook quote at one timestamp is "the market."

This stage uses **no game outcomes**. Its first validation target is subsequent market movement.

## Point-in-time inputs

At capture t only:
- consensus line / no-vig probability;
- sportsbook count;
- line range and standard deviation;
- same-threshold price dispersion;
- sportsbook quote age;
- movement since the previous observed capture;
- movement velocity;
- dispersion change / convergence rate;
- which books changed line or same-threshold probability.

Price dispersion is never compared across different prop thresholds. A 50% probability at 64.5 and
a 50% probability at 65.5 are not treated as directly comparable prices.

## Evaluation-only future-market targets

For each capture, later fields are isolated under `evaluation_only_targets`:
- final observed pregame capture timestamp;
- line movement to final observed capture;
- probability movement to final observed capture.

These fields may be labels for CLV/price-discovery evaluation. They may not enter features at time t.

"Final observed" is not called "closing" unless the source contract independently proves that the
capture is a qualified close.

## Horizon rule

No capture is retrospectively called OPEN, T−48h, T−24h, T−12h, T−6h, T−90m, T−30m, or close
merely because it is nearby. The archive preserves exact minutes to kickoff. Horizon tolerances
must be preregistered in a separate contract after capture cadence and source coverage are known and
before any game-outcome evaluation.

## Primary no-outcome questions

1. Does LevLine disagreement at t predict the sign of subsequent market movement?
2. Does higher dispersion/staleness identify states with larger subsequent movement?
3. Does convergence increase as kickoff approaches?
4. Do line changes or same-threshold price changes propagate across books in repeatable order?

Book-leader/follower claims require enough repeated captures to establish ordering. The current
feature layer records movers but does not invent "sharp" labels.

## Governance

- no completed 2026 game outcome is read;
- no outcome-derived horizon or threshold;
- no sportsbook is declared sharp/recreational without independent evidence;
- no production signal or betting recommendation;
- official V1/F-ST unchanged.
