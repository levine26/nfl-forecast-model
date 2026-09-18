# Props 2.0 Touchdown Engine V2 — Count Distribution Contract

Status: **PREREGISTERED MECHANISM STUDY**  
Candidate: `P2-TD-V2-COUNT`  
Version: `levline-props-v2-td-count-distribution-v0.1.0`

## Scope

The existing Props TD engine already models:
- drives / red-zone trips;
- red-zone TD rate;
- pass/rush split;
- end-zone targets;
- red-zone targets;
- goal-line carries;
- hierarchical player TD allocation.

This experiment does not discard that structure. It isolates one upstream assumption:
**team offensive touchdown counts are currently Poisson unless shared scoring variance is supplied.**

## Frozen comparison

Both count families receive the exact same team expected TD mean.

Mean model:
- team historical offensive-TD mean from prior seasons;
- shrunk toward the league mean with 8 equivalent team-games.

Families:
1. Poisson baseline.
2. Negative binomial with one league-wide overdispersion parameter estimated by method of moments
   from the same historical training rows.

Chronology:
- train 2021–2023 → test 2024;
- train 2021–2024 → test 2025.

No random shuffle and no player prop outcomes.

## Metrics

- exact count log loss;
- multiclass Brier over counts 0..9 and 10+;
- discrete CRPS;
- per-season and weighted aggregate;
- fitted overdispersion.

## Gate

A non-Poisson count family proceeds to a coherent TD simulator challenger only if it improves
aggregate log loss and CRPS without material Brier degradation and the direction is reasonably
stable across 2024/2025.

If overdispersion collapses to zero or proper scores do not improve, retain Poisson.

Passing this gate does not authorize production and does not alter player TD allocation.

## Governance

No completed 2026 outcomes. No sportsbook inputs. No edge thresholds. No V1/F-ST mutation.
