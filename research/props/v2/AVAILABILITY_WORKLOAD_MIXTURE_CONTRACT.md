# LevLine Props 2.0 — Availability / Workload Mixture Contract

Status: **PREREGISTERED BEFORE PROP-OUTCOME EVALUATION**  
Candidate: `P2-AVAIL-MIX-V01`  
Version: `levline-props-v2-availability-workload-v0.1.0`

## Problem

The current Props availability layer reduces QUESTIONABLE / DOUBTFUL uncertainty to
`P(any offensive snap)`. If active, the opportunity engine effectively treats the player as
normal-role unless a separate role adjustment exists.

That conflates two distinct questions:

1. Will the player play?
2. Conditional on playing, what workload state will the player have?

## Research target

Use historical injury designations and offensive participation only. No player-prop result,
sportsbook result, Fair-Line error, betting outcome, or completed 2026 outcome is used.

For each historical QUESTIONABLE / DOUBTFUL player-week:
- build a strictly prior baseline snap share from the previous four observed player games;
- require at least two prior games;
- exclude tiny baseline roles below 15% snap share;
- compare target-week snap share with the prior baseline.

## Frozen workload states

Let `r = current snap share / prior baseline snap share`, clipped only for modeling at 2.0.

- `OUT`: zero offensive participation;
- `ACTIVE_LIMITED`: active and r < 0.75;
- `ACTIVE_NORMAL`: 0.75 <= r <= 1.25;
- `ACTIVE_ELEVATED`: r > 1.25.

These thresholds are semantic preregistration choices. They may not be changed because a different
threshold improves prop accuracy.

## Model

For each designation × position with at least 40 training rows:
- Dirichlet(1,1,1,1)-smoothed workload-state probabilities;
- empirical mean/SD workload multiplier inside each active state.

Sparse designation × position cells fall back to the designation-pooled historical sample.

Comparator:
- season-forward Beta(1,1) `P(active)` for the designation;
- expected workload ratio = P(active) × 1.0.

Mixture expected workload:
- sum over workload states of P(state) × mean workload multiplier(state).

## Chronology

For evaluation season S:
- all parameters are fit using seasons <= S−1;
- the evaluated player-week baseline uses only games before that player-week;
- target-week snap share is evaluation target only;
- 2026 outcomes are prohibited.

The nflverse historical injury source is retrospective development evidence. Exact historical
publication timestamps are not claimed. Any production/prospective use still requires the existing
timestamped current-injury capture path.

## Evaluation

Primary component metric:
- workload-ratio MAE: mixture versus active-only comparator.

Secondary:
- active/inactive Brier score;
- four-state multiclass Brier score;
- four-state log loss;
- sample sizes by designation and position;
- season-forward stability.

This component can advance to prospective shadow testing only if workload MAE improves without a
material degradation in active/inactive probability quality. It cannot authorize production from
retrospective evidence.
