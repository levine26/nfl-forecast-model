# LevLine Props 2.0 — Prospective Football Shadow B Grading Contract

Status: **FROZEN BEFORE FIRST SHADOW B RECEIPT / OUTCOME**  
Version: `levline-props-v2-football-shadow-b-grading-v0.1.0`  
Candidate: `P2-SHADOW-B-DEFENSE-ROLE-v0.1.0`  
Automatic production authorization: **NONE**

## Scientific hierarchy

The master prospective contract fixes the comparison order:

1. Shadow A vs V1 establishes whether opponent defensive efficiency works prospectively.
2. **Shadow B vs Shadow A is the primary Shadow B comparison** and isolates the incremental value of
   Dynamic Role V0.1 full.
3. Shadow B vs V1 is supporting context only.

Shadow B may not be promoted merely because it beats V1 if it does not add value over Shadow A.

## Inputs

The grader reads only:
- immutable Shadow A receipts under `levline-props-v2-football-shadow-a-v0.1.0`;
- immutable Shadow B receipts under `levline-props-v2-football-shadow-b-v0.1.0`;
- finalized postgame football outcomes.

Missing pregame forecasts are never reconstructed after kickoff.

The grader is locked to Shadow A grading contract
`levline-props-v2-football-shadow-grading-v0.1.0`; changing that dependency requires a new Shadow B
grading version.

## Pair identity

A Shadow B receipt is a valid B-vs-A pair only when the matching Shadow A receipt has the same:
- source forecast ID;
- source workflow run;
- source head SHA;
- source forecast SHA-256;
- source manifest SHA-256;
- game/player/prop identity;
- source season/week;
- kickoff;
- market line and no-vig Over probability;
- immutable V1 empirical-distribution SHA-256.

Any mismatch fails closed.

A B receipt without a matching A receipt may appear only in B-vs-V1 diagnostic reporting. It does
**not** count toward the B-vs-A prospective sample or the minimum evidence threshold.

## Receipt governance

Before grading, B receipts must prove:
- production_authorized=false;
- published_v1_props_mutated=false;
- winner_model_mutated=false;
- target_week_outcomes_used=0;
- completed_2026_outcomes_used_for_model_selection=0;
- captured V1 opportunity baseline reconstructed before the role transform;
- Dynamic Role mode is exactly `full`;
- Dynamic Role engine is `levline-props-dynamic-role-v0.1.0`;
- defensive-efficiency coefficients are from
  `levline-props-v2-defensive-efficiency-shadow-v0.1.0` and trained only through 2025.

The B receipt, V1 PMF and Shadow B PMF hashes must verify.

## Outcome policy

Identical to the frozen Shadow A grader:
- only finalized schedule games are graded;
- nflverse QB scramble normalization is retained;
- stable snap participation must resolve;
- offense snaps > 0 are required;
- zero offensive snaps are void;
- positive-snap players with no qualifying rush/reception grade as 0 yards;
- incomplete final-game PBP remains ungraded.

## Frozen metrics

For rushing yards and receiving yards separately, plus pooled descriptive reporting:

Primary B-vs-A:
- empirical CRPS;
- Fair-Line MAE;
- Over-probability Brier score;
- Over-probability log loss;
- fixed-decile reliability;
- 80% interval coverage and interval score;
- directional accuracy.

Supporting B-vs-V1 reports the same metrics.

Push policy:
- pushes remain in CRPS, Fair-Line MAE and interval metrics;
- pushes are excluded from Brier, log loss and directional accuracy.

Paired differences use a 5,000-replicate game-cluster bootstrap with frozen seed `20260919` plus
deterministic comparison/metric/family offsets.

## Minimum evidence before any Shadow B promotion discussion

Only the integrity-matched B-vs-A sample counts:

- at least **300 paired decided props**;
- at least **100 unique games**;
- at least **8 NFL weeks**;
- no unresolved PIT/provenance/identity failures;
- no material proper-score degradation versus Shadow A;
- positive evidence not driven by one week, team, player or prop subtype.

These are discussion thresholds, not automatic promotion rules.

## No adaptive scoring

Do not change after observing prospective outcomes:
- pairing rules;
- push policy;
- calibration bins;
- bootstrap unit/replicates/seeds;
- sample thresholds;
- metric definitions;
- family pooling;
- outcome construction;
- candidate identity.

Engineering corrections require a new version and may not be selected because they improve observed
Shadow B performance.
