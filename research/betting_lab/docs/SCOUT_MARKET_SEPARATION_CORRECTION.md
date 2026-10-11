# B07D — Correct separation of moneyline and against-the-spread modeling

**Date:** 2026-10-10 PDT  
**Classification:** Research-only methodological correction; prior B07C report superseded, never silently overwritten.  
**Relevant source:** `outputs/this_week.csv`, GitHub blob `81351dd037e2608c230d248961ae26f0cff3d859` (historic as captured; re-check latest for actual decisions).  
**External odds status:** Unqualified; embedded spread and total timestamps unknown.  
**Production changes:** None.  
**2026 outcome fitting:** None.

## Problem and correction

The B07C scout conflated the direction of an outright-winner model with the side favored by a separate point-margin model and treated the resulting difference as a `WINNER_MARGIN_DISAGREEMENT`. That was a conceptual error, not evidence of model inconsistency. `final_home_prob` is an official F-ST **moneyline (outright winner)** probability; it is **not** a spread-cover probability. A model may assign home 56.4% likelihood of winning outright and also assign the away team a 64.6% exploratory probability of covering a positive spread. Both may be legitimate because those markets represent different events.

The replacement:

1. **Moneyline:** reports official F-ST home/away win probabilities and identifies its favorite. A *relative ML shade* against the archived market may be a less-likely outright winner; it is a separate pricing hypothesis.
2. **Spread:** compares the home-minus-away expected margin against an actual *side-specific handicap*. An exploratory discrete-integer normal converts expected margin and `margin_sigma` into cover/push/noncover probabilities. **The F-ST moneyline probability is never read by the ATS calculation.** Historic raw model ATS accuracy is not a calibration guarantee.
3. **Total:** uses expected total and `total_sigma` with integer-score push probabilities independently of both ML and ATS.
4. **Book quote board:** applies exactly those independent market models to real, timestamp-qualified bookmaker lines. It now models whole-point pushes and uses push-aware theoretical return under explicitly unvalidated sensitivity assumptions. Two-sided de-vigged spread/total probabilities are conditional on nonpush, not unconditional win rates.
5. `WINNER_MARGIN_DISAGREEMENT` is **eliminated**. Do not relabel old rows; their immutable artifact is superseded by the new `LEVLINE-SCOUT-THREE-MARKETS-V02-2026-10-10` ID.

### Example (illustrative existing LevLine reference; NOT verified current bookmaker price)

Jets ML: F-ST P(Win) = 56.4%; Browns ML P(Win) = 43.6%. Separately, Browns **+2.5** against Jets has an exploratory ATS cover estimate about **64.6%** from an uncalibrated margin distribution. These numbers are not contradictory. They represent different outcomes. **No wager follows from either number without a current price and validation.**

### Assumptions and limitations

- Rounded latent normal over integer final margins / points; cannot reproduce observed NFL key-margin excess (3 and 7), sport-specific dispersion, distribution tails or true score-count dependence. Not a fully calibrated margin distribution.
- Moneyline F-ST binary-probability complement does not separately allocate NFL regulation/overtime tie mass; two-way push settlement must eventually model tie probability separately.
- The archived `spread_line` is encoded as *home implied margin*, the negative of the home team's listed spread. Actual sportsbook `BookQuote.line` is the signed **side-specific** handicap. These fields are not interchangeable. Only qualified current price/handicap inputs can support a bet quotation.
- All pro forma payout/EV columns remain scenario analyses and every result retains `NO_BET_UNVALIDATED_PROBABILITY_AND_PROSPECTIVE_EDGE`.
- Historical research remains negative or non-conclusive for ATS model incremental value. No survivor tuning, false win rates, or promotion implied.

### Validation and deployment

- `python -m unittest discover -s tests -q`: 59 passing tests.
- New tests demonstrate that changing `final_home_prob` leaves ATS estimates unchanged, changing `expected_margin` leaves ML probabilities unchanged, and whole-line/half-line push behavior follows integer outcome grading.
- Regenerated Sunday scout using the prior B07C reduced-column source snapshot. Replaced reports are **new immutable files**. Do not claim the reduced CSV represents a fresh bookmaker market update.
- Research-only PR #697; commit and full-CI acceptance to be recorded separately.