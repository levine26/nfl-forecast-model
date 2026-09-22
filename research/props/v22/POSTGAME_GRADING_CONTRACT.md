# LevLine Props 2.2 — Postgame Grading Contract

Status: **FROZEN BEFORE FIRST PROPS 2.2 FUTURE-HOLDOUT RECEIPT**  
Research-only: yes  
Production authorization: no  
Grade contract: `levline-props-2.2-grade-v0.1`

This contract governs how immutable Props 2.2 prospective forecasts become eligible for postgame evaluation. It does not change the frozen challenger grid or forecast values.

## 1. Separation of forecast and outcome evidence

Prospective challenger receipts remain immutable and must keep `outcome: null`.

Postgame outcomes are stored in a separate grade ledger keyed by the immutable Props 2.1 source forecast hash. All Props 2.2 challengers derived from the same source forecast share the same factual outcome grade.

A grade may never rewrite:
- a Props 2.1 source forecast;
- a Props 2.2 challenger receipt;
- a market timestamp, line, or probability;
- challenger coefficients;
- role/availability/workload state;
- forecast chronology.

## 2. Finalization requirement

A source forecast is not gradeable until its NFL game is finalized in the schedule source and complete final play-by-play is available.

If the game is not final, no grade record is written.

If the schedule says final but complete outcome PBP is unavailable, no grade record is written.

These states remain pending; they are not treated as losses, zeroes, voids, or missing-at-random observations.

## 3. Participation requirement

Stable player identity and offensive snap participation are required before a player prop is graded.

- positive offensive snaps -> eligible for factual stat grading;
- exactly zero offensive snaps -> immutable `VOID` grade with reason `ZERO_OFFENSE_SNAPS`;
- missing/unresolved participation -> pending, no grade record.

A player with positive participation and zero recorded production receives a legitimate numeric result of `0.0`. Zero production must not be conflated with zero participation.

## 4. Actual-stat source

Outcomes use the established nflverse play-by-play plus normalized snap-participation path already used by the frozen Props 2.1 evaluator.

Supported outcomes remain aligned with the frozen Props markets:
- passing yards;
- rushing yards;
- receiving yards;
- receptions;
- passing TDs;
- rushing TDs;
- receiving TDs;
- anytime TDs.

No sportsbook settlement result is used as the factual player-stat source.

## 5. Immutable grade identity

Each postgame grade preserves:
- source Props 2.1 forecast SHA-256;
- source Props 2.1 forecast ID;
- game ID;
- player ID;
- prop type;
- grade status;
- actual result when graded;
- offensive snaps;
- finalized flag;
- grade timestamp;
- result source;
- immutable grade SHA-256.

Once a source forecast has a grade, later workflow runs may replay it but may not replace it with a different result. Conflicting duplicate grades fail closed.

## 6. Challenger-set completeness

A source forecast is eligible for Props 2.2 grading only when its prospective ledger contains the complete frozen challenger set from `CHALLENGER_GRID.json`.

Partial challenger sets fail closed. This prevents differential missingness across candidates from being introduced during grading.

## 7. Probability-event semantics

The evaluator uses the original point-in-time market threshold as the event definition for line-market probabilities.

- actual > original market line -> OVER event occurred;
- actual < original market line -> OVER event did not occur;
- actual == original market line -> push and excluded from binary Brier/log-loss scoring.

For binary touchdown markets:
- actual TD count >= 1 -> event occurred;
- actual TD count == 0 -> event did not occur.

These rules are fixed before the future holdout.

## 8. Evaluation and selection boundary

Per-week evaluation remains descriptive.

The postgame grader does not:
- choose a challenger;
- alter Holm-Bonferroni families;
- change sample thresholds;
- create betting signals;
- authorize production;
- infer missing outcomes.

Promotion/model-selection remains governed exclusively by the frozen Props 2.2 preregistration and its terminal evidence thresholds.
