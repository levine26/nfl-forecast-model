# LevLine Props 2.0 — Architecture

Status: **RESEARCH ARCHITECTURE / NO PRODUCTION PROMOTION**

## Causal simulation graph

```
game spread + total + team state
  -> drives / plays / evolving script
  -> dropbacks / designed rushes
  -> player availability-state mixture
  -> snap + route + carry participation
  -> route / target / carry opportunity
  -> contextual completion / rush / YAC efficiency
  -> red-zone and TD allocation
  -> coherent joint Monte Carlo outcomes
  -> PURE LEVLINE distribution + Fair Line

PURE LEVLINE distribution + timestamp-matched sportsbook state
  -> market-residual model
  -> calibrated final probability

timestamp t disagreement
  -> later market / close
  -> CLV and price-discovery evaluation
```

## Architectural rules

### Game environment

Raw observed pass rate is not a sufficient state. Prefer situation-adjusted tendencies conditional
on down, distance, score, time, field position, and relevant personnel when available. Target-game
script is never used.

### Dynamic role

Role is a latent time-varying state. Current snap-share EWMA is a V1.5 proxy, not the final model.
V2 should estimate state uncertainty and allow rapid transitions after depth-chart/injury/personnel
events while retaining hierarchical shrinkage.

### Availability

Do not equate P(active) with P(normal workload). Simulate discrete workload states such as OUT,
ACTIVE_LIMITED, ACTIVE_NORMAL, and ACTIVE_ELEVATED, each with conditional distributions of snaps,
routes, carries, targets and red-zone work.

### Receiving process

Use:
```
team plays -> dropbacks -> route probability -> target probability | route
-> target depth -> completion -> air yards + YAC
```

Raw target share may be an input/state measurement, not the whole receiving model.

### Rushing process

Use contextual expected carry outcome plus a shrunk player residual. Event distributions must admit
losses, ordinary gains, and explosive tails.

### Passing process

Use dropback → pressure/sack/scramble/attempt → target-depth → completion → air yards + YAC.

### Touchdowns

Treat touchdowns as allocation of team scoring opportunities:
drives → red-zone trips → TD probability → pass/rush split → player opportunity → player allocation.

### Distribution layer

The simulator must reconcile:
- QB passing yards with receiver receiving yards;
- team targets with player targets;
- team carries with player carries;
- team TD opportunities with player TD allocations.

Model selection must consider CRPS, calibration, quantile/tail coverage, Brier/log loss and
line-crossing probability—not in-sample likelihood alone.

## Market-residual layer

The sportsbook is a strong prior. Candidate football features enter the final residual layer only
after standalone football-process validation. Low-dimensional ridge/Bayesian shrinkage is preferred
before high-dimensional boosting.

## Scientific basis

- Gneiting, Balabdaoui & Raftery (2007), *Probabilistic forecasts, calibration and sharpness*:
  maximize sharpness subject to calibration; use proper scoring and time-aware validation.
- Gneiting & Raftery (2007), *Strictly Proper Scoring Rules, Prediction, and Estimation*:
  proper scores incentivize truthful probabilistic forecasts.
- NFL Next Gen Stats Expected Rushing Yards: full outcome distributions from tracking context support
  mechanism-level rushing distributions rather than generic YPC.
- NFL Next Gen Stats Completion Probability: completion depends on air distance, target separation,
  pass-rush separation, passer movement and time to throw.
- NFL tracking systems generate position/speed/acceleration data at high frequency and power route
  detection and expected-outcome metrics.

These references motivate architecture; they do not substitute for LevLine-specific out-of-sample
validation.
