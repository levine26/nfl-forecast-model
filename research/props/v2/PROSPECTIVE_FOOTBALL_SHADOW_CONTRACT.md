# LevLine Props 2.0 — Prospective Football Shadow A/B Contract

Status: **FROZEN BEFORE FIRST SHADOW A/B RECEIPT**  
Version: `levline-props-v2-football-shadow-v0.1.0`  
Production authorization: **NONE**

## Candidates

### Shadow A — `P2-SHADOW-A-DEFENSE-v0.1.0`

Frozen V1 plus only the two opponent defensive-efficiency mechanisms that passed the independent
true-pregame gates:
- rushing yards/carry defense residual;
- receiving yards/reception defense residual.

All V1 opportunity arrays are preserved exactly.

### Shadow B — `P2-SHADOW-B-DEFENSE-ROLE-v0.1.0`

Shadow A plus Dynamic Role V0.1 **full**:
- route participation level from strictly lagged snap share;
- recent-vs-long target trend;
- recent-vs-long RB carry trend.

No Dynamic Role V2 behavior is allowed.

## Frozen football parameters

Defensive-efficiency coefficients are the PR #396 pre-2026 freeze, trained through 2025 football
events only. They may not change because of 2026 outcomes.

Dynamic Role V0.1 uses the already-frozen implementation:
- prior-equivalent games 2;
- short half-life 2 games;
- long half-life 8 games;
- multiplier bounds 0.20–2.00;
- mode `full`.

## Live source

The recorder consumes the exact audit artifact emitted by a successful
`LevLine Props live refresh` on `main`.

It must use:
- the immutable integration manifest used to generate published V1;
- the exact player-state snapshot used by V1;
- the exact market artifact used by V1;
- V1's simulation count and seed;
- strictly lagged nflverse football history only for the additional defense/role state.

No second sportsbook fetch is permitted.

## Shadow A isolation

For each game:
1. simulate the immutable V1 manifest;
2. deepcopy the V1 simulation;
3. calculate opponent defense state from weeks strictly before the target week;
4. regenerate only rushing/receiving yardage arrays with the frozen defense residual.

All sampled V1 opportunity arrays must remain byte-identical.

## Shadow B reconciliation firewall

Shadow B may be recorded only if the recorder first reconstructs the unmodified V1 opportunity model
from:
- immutable current player state;
- strictly lagged football history;
- frozen route/availability priors;
- the V1 primary-QB identity preserved in the manifest.

The reconstructed unmodified simulation must reproduce V1's opportunity arrays exactly for:
`active, pass_attempts, routes, targets, receptions, carries`.

If any opportunity array differs, Shadow B fails closed for that game. No approximate reconstruction
is allowed.

After reconciliation, apply Dynamic Role V0.1 full, simulate with the manifest's frozen seed/count,
then apply the frozen defensive-efficiency overlay.

## Immutable distributions

For each eligible rushing-yards or receiving-yards V1 forecast, preserve:
- source V1 forecast ID and SHA-256;
- source live workflow run;
- source forecast/market timestamps and kickoff;
- market line/prices when present in the source forecast;
- V1 fair line / P(over);
- Shadow A fair line / P(over);
- Shadow B fair line / P(over), if reconciliation passed;
- exact empirical integer distribution histogram for V1 / A / B;
- candidate versions and coefficient provenance;
- all reconciliation/audit states.

The histogram is part of the immutable original receipt so future CRPS can be graded without
post-kickoff forecast reconstruction.

## Eligibility

Fail closed when:
- the live workflow was not successful on main;
- the source forecast or market capture is at/after kickoff;
- the shadow receipt is at/after kickoff;
- the manifest/source forecast cannot be uniquely paired;
- defense state is unavailable;
- Shadow B V1 reconstruction does not reconcile exactly.

## Contamination firewall

Completed 2026 outcomes may be used only for later grading. They may not change:
- candidate membership;
- coefficients;
- role parameters;
- market horizons;
- simulation settings;
- calibration;
- thresholds.

## Evaluation hierarchy

1. Shadow A vs V1 — primary;
2. Shadow B vs Shadow A — secondary prespecified ablation;
3. Shadow B vs V1 — supporting context.

Minimum promotion-discussion evidence remains:
- 300 paired decided props;
- 100 unique games;
- at least 8 NFL weeks;
- no unresolved PIT/provenance failures.

No retrospective or prospective success automatically authorizes production.
