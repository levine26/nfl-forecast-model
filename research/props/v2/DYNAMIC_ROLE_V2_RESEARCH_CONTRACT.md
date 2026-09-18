# Props 2.0 Dynamic Role V2 Research Contract

Status: **PREREGISTERED BEFORE V2 OUTCOME EVALUATION**  
Candidate: `P2-ROLE-V2`  
Contract: `levline-props-v2-dynamic-role-development-v0.2.0`

## Hypothesis

A latent time-varying role state estimated from strictly lagged offensive participation will improve
Fair-Line accuracy and/or directional accuracy relative to frozen V1 and the existing V0.1
fixed-half-life snap proxy.

## What changes

V0.1 uses fixed short/long exponentially weighted snap shares. V2 uses a random-walk state model on
logit snap share. Position-level process/observation variances are estimated from **snap-share
trajectories only**, through the prior season.

No prop outcome, Fair-Line error, betting result, sportsbook movement, or completed 2026 outcome may
be used to estimate the role-state dynamics.

## State model

```
x_t = x_(t-1) + w_t
logit(observed snap share_t) = x_t + e_t
```

The next-game role state is the one-step-ahead posterior prediction. Player state starts from a
position prior and remains shrunk when evidence is sparse.

The long-run player baseline is the all-history shrunk mean, not a last-3/last-5 window. The
posterior-vs-long-run ratio supplies target/carry trend adjustments; posterior participation level
supplies route-role level.

## Frozen ablations

- `route_only`: latent participation level adjusts route role only.
- `full`: route level plus posterior-vs-long-run target/carry role trend.

Both are reported. Retrospective results may not select a winner for production.

## Chronology

For evaluation season S:
- state-dynamics variances are fit only through season S−1;
- player filtering may use games before the target week in S;
- target-week/future snap rows are prohibited;
- game/prop outcomes are grading-only.

## Metrics

Primary football-process metrics:
- paired Fair-Line MAE;
- paired directional accuracy.

Also report:
- N / games / players;
- game-clustered 95% intervals;
- by season/prop/position;
- sportsbook line MAE and price-direction accuracy for context.

## Decision boundary

Retrospective 2023–2025 evidence may justify including V2 in a frozen prospective candidate if:
- aggregate Fair-Line MAE improves versus V1;
- directional accuracy does not materially degrade;
- evidence is not isolated to one small prop/position subgroup;
- chronology and identity gates pass.

It cannot authorize production. No 2026 result may be used to rescue the specification.
