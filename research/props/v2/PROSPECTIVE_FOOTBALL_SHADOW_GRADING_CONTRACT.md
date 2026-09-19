# LevLine Props 2.0 — Prospective Football Shadow A Grading Contract

Status: **FROZEN BEFORE FIRST SHADOW A OUTCOME IS GRADED**  
Version: `levline-props-v2-football-shadow-grading-v0.1.0`  
Candidate: `P2-SHADOW-A-DEFENSE-v0.1.0`  
Automatic production authorization: **NONE**

## Input boundary

The grader reads only:
1. immutable pregame Shadow A receipts created under
   `levline-props-v2-football-shadow-a-v0.1.0`; and
2. finalized football outcomes after kickoff.

The receipt must already contain lossless empirical V1 and Shadow A yardage distributions,
source season/week, market line, Fair Lines, probabilities, intervals and point-in-time provenance.

The grader may not recreate a missing pregame forecast after kickoff.

## Outcome definition

Rushing yards:
- official rush-attempt rows by stable rusher ID;
- sum target-game rushing yards;
- a finalized game with no qualifying rush for the player grades as 0.

Receiving yards:
- completed-pass rows by stable receiver ID;
- sum target-game receiving yards;
- a finalized game with no qualifying reception grades as 0.

Only games identified as finalized by the schedule source are graded.

Participation / void policy:
- stable player identity must resolve in the canonical snap-count source;
- offense snaps must be **> 0**;
- zero offensive snaps are excluded as void;
- missing snap participation remains ungraded until the source is available;
- a positive-snap player with no qualifying rush/reception grades as 0 yards.

## Frozen metrics

For rushing yards and receiving yards separately, plus pooled descriptive results:

Primary:
- empirical CRPS from the immutable support/count distribution;
- Fair-Line MAE.

Secondary:
- Over-probability Brier score;
- Over-probability log loss;
- fixed-decile reliability table with edges 0.0, 0.1, ..., 1.0;
- 80% interval coverage;
- 80% interval score;
- directional accuracy.

Push policy:
- pushes remain in CRPS, Fair-Line MAE and interval metrics;
- pushes are excluded from Brier, log loss and directional accuracy.

Paired Shadow A minus V1 differences use a **5,000-replicate game-cluster bootstrap** with frozen
seed `20260919` plus deterministic metric/family offsets.

## Minimum evidence before promotion discussion

The grader reports whether the master minimum discussion thresholds are reached:
- at least **300 paired decided props**;
- at least **100 unique games**;
- at least **8 NFL weeks**.

These are sample-size gates only. They are **not automatic promotion criteria**.

The grader also reports concentration by week, player and prop family. Production promotion remains
a separate governed decision and is never authorized by this script.

## No adaptive scoring

Do not change after observing prospective outcomes:
- push policy;
- calibration bins;
- bootstrap unit/replicates/seeds;
- minimum evidence thresholds;
- metric definitions;
- family pooling;
- outcome construction.

Engineering corrections require a new version and must not be chosen because they improve the
candidate's observed result.
