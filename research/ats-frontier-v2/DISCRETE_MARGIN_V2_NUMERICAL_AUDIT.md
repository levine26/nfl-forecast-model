# DISCRETE MARGIN V2 NUMERICAL AUDIT

## M4 status

`DATA_QUALIFIED` for **numerical/data feasibility only**. This is not evidence of predictive alpha.

## Available historical fields

The nflverse schedule table supplies historical final margin (`result`), final total, `spread_line` and `total_line` across the historical era. These fields are sufficient for Phase-3 training-era structural diagnostics without needing completed-2026 outcomes.

Canonical schedule convention observed in nflverse: `result = home_score - away_score`; historical `spread_line` is the home-team spread convention used by the schedule source. Phase 3 must freeze a single transformed model-margin sign and unit-test it before any fit.

## Frozen numerical representation

1. Use a continuous latent margin law with unbounded or adaptively safe support.
2. Convert to integer final-margin mass through bin integration: `P(M=m)=F(m+0.5)-F(m-0.5)`.
3. A push on an integer betting spread is structural probability mass at the corresponding integer margin; non-integer spread has zero exact push mass.
4. Cover/push/fail probabilities must be summed from the integer PMF, not approximated by clipping a continuous prediction.
5. If any finite numerical grid is used, endpoint/tail mass must be shown negligible before evaluation. The prior Q2-V1 hard/folded support failure may not be repeated.

## Structural-frequency audit boundary

Historical score margins, key-number frequencies and era shifts are available for a dedicated Phase-3 preregistered representation diagnostic. Phase 2 does not use their relationship to candidate errors or returns, and does not choose a model family or threshold from outcomes.

## Market conditioning availability

Schedule-level spread/total values exist as a horizon-opaque benchmark. Exact PIT market conditioning at frozen horizons depends on the M1 access decision.