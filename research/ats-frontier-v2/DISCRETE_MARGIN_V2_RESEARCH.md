# DISCRETE MARGIN V2 RESEARCH

## Why a V2 experiment is scientifically allowed

ATS-Q2 V1 was not rejected on forecasting performance. Its preregistered finite support `[-75,+75]` generated maximum folded endpoint mass `0.0033487`, above the `0.001` structural-validity threshold, so execution failed closed before a valid complete OOF evaluation. A successor must be a new experiment with a new numerical contract; it may not reuse or reinterpret Q2 V1 results.

## Required numerical design changes

1. **Tail-safe support.** Prefer an unbounded/heavy-tailed parametric family or choose finite support by a preregistered negligible-tail-mass criterion derived only from training data. Never fold material mass into endpoints.
2. **Integer-bin integration.** A continuous latent margin distribution must map to integer final margins through bin probabilities, not point density evaluated at integers.
3. **Exact push mass.** Whole-number sportsbook spreads require explicit probability of `margin + home_spread == 0`.
4. **Key-number structure.** Permit conditional excess mass at football-relevant margins (especially ±3, ±6, ±7, ±10, ±14) only through a frozen, normalized mechanism.
5. **Conditioning.** Key mass and dispersion may plausibly vary with market spread, total, scoring environment and era; every degree of freedom must be preregistered to avoid key-number fishing.
6. **Tail validation before scoring.** Validate normalization, endpoint/tail mass, symmetry/asymmetry diagnostics and numerical stability without examining target-period candidate performance.

## Modern-era key-number evidence

Public descriptive analyses continue to show large mass around 3 and 7, while exact percentages vary by era/sample. More important scientifically, 2026 Finance Research Letters evidence finds that crossing 3/7 creates large betting-demand discontinuities without corresponding return predictability. Therefore M4 should model key mass for probability correctness, not presume that key-number crossing itself offers alpha.

## Candidate forms worth Phase-3 consideration

- market-centered empirical residual PMF with hierarchical/conditional smoothing;
- heavy-tailed continuous latent residual plus integer-bin integration and explicit key-mass adjustment;
- conditional discrete exponential-family/ordinal construction with adaptive support;
- joint home/away score simulation only if it passes a substantially higher complexity/data bar.

## Nulls

A valid M4 experiment must compare against a market-centered empirical distribution / strong market distribution null, not just a Normal with fixed sigma. Proper-score performance is primary; ATS decision value is downstream.

## Kill criteria

M4 should be rejected before expensive fitting if a numerically stable market null already captures push/key/tail calibration and no M1–M3 signal needs richer translation. Representation complexity without proper-score gain is not progress.

## Phase-1 status

`FRONTIER-M4-DISCRETE-MARGIN-V2`: **SURVIVES as a representation experiment**, with lower prior probability of independent ATS edge than M1/M2.