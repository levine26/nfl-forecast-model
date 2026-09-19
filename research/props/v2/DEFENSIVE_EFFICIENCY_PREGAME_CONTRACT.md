# LevLine Props 2.0 — Defensive Efficiency True-Pregame Ablation Contract

Status: **PREREGISTERED RETROSPECTIVE DEVELOPMENT**  
Candidates: `P2-EFF-RUSH-PREGAME-V01`, `P2-EFF-REC-PREGAME-V01`  
Version: `levline-props-v2-defensive-efficiency-pregame-v0.1.0`

## Motivation

The component-isolation study in PR #391 passed its frozen gate independently for rushing and
receiving. It conditioned on actual event count and therefore did not establish a pregame prop gain.

This follow-up removes that conditioning.

## Frozen design

Rushing and receiving remain separate hypotheses.

For every target game:
1. build and simulate the frozen V1 pregame state;
2. copy the V1 simulation result;
3. preserve all sampled opportunity counts exactly;
4. calculate the target opponent's event-type defensive state using weeks strictly before the target
   week;
5. apply the season-forward coefficient fitted only through S−1 to the V1 player efficiency mean;
6. regenerate only the relevant yardage array from the existing V1 Gamma family.

Rushing mode changes only rushing-yards/carry mean and rushing-yard samples.  
Receiving mode changes only receiving-yards/reception mean and receiving-yard samples.

The adjusted mean is floored at 0.05 yards/event as a fixed numerical safeguard, not tuned from prop
outcomes.

## Defense state and coefficients

The V1 forecast baseline retains its existing historical input window. The challenger defense-state/coefficient source separately uses **2019 through S** PBP so the PR #391 component specification is inherited rather than silently refit on a shorter history.

The defense feature and fixed ridge specification are inherited unchanged from PR #391:
- opponent prior 8 defensive games;
- shrink toward prior league event mean with 80 pseudo-events;
- feature = opponent prior yards/event − prior league yards/event;
- residual coefficient fit with ridge alpha 25 through S−1.

Target-week outcomes do not update the defense state.

## Population

Primary genuine Action Network book-30 OPEN:
- rushing-yards props for the rushing candidate;
- receiving-yards props for the receiving candidate;
- regular seasons 2023–2025.

This historical population has been inspected during V1 development; results are retrospective
development evidence only.

## Metrics and separate gates

Primary: empirical CRPS.

Secondary:
- Fair-Line MAE;
- 80% interval score and coverage;
- directional accuracy versus the same market line;
- game-clustered paired CRPS and Fair-Line-error confidence intervals.

Each event-type candidate advances separately only if:
1. pooled CRPS improves;
2. pooled Fair-Line MAE improves;
3. CRPS improves in at least two of three seasons;
4. pooled game-clustered CRPS-difference 95% CI upper bound <= 0;
5. 80% coverage deteriorates by no more than 1.5 percentage points.

One event type cannot rescue the other. Directional accuracy cannot rescue a failed proper-score
gate.

No completed 2026 outcome is allowed. Retrospective success cannot authorize production.
