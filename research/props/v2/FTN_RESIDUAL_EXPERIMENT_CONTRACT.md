# LevLine Props 2.0 — FTN Matchup Market-Residual Experiment Contract

Status: **FROZEN BEFORE EMPIRICAL FTN-RESIDUAL EVALUATION**  
Created: 2026-09-18  
Branch: `research/props-v2-ftn-residual`  
Parent research boundary: `research/props/v2/PROPS_V2_RESEARCH_PREREGISTRATION.md`

## Question

Do strictly lagged, live-capable FTN team scheme/matchup features add incremental prop-direction
information beyond a sportsbook no-vig prior and the frozen LevLine V1 probability gap?

This is retrospective development evidence only. The 2023–2025 outcomes were already inspected
during V1 diagnosis, so even a positive result cannot authorize production.

## Fixed model form

Fit one regularized Bernoulli residual model per prop family:

```
logit(P_over)
  = logit(P_over_market)
  + intercept
  + beta_v1 * standardized(logit(P_over_v1) - logit(P_over_market))
  + beta_ftn * standardized(FTN matchup state)
  + beta_missing * FTN-missing indicators
```

The sportsbook coefficient is fixed at 1.0 and is not estimated.

Training-block transformations only:
- median imputation learned from the training block;
- mean/standard-deviation scaling learned from the training block;
- missing FTN evidence gets an explicit missing indicator and is never treated as zero performance.

Fixed penalties:
- all residual coefficients L2 = 10.0;
- intercept L2 = 1.0;
- no hyperparameter search.

Minimum training sample:
- 75 decided non-push rows per prop family.

No abstention, edge threshold, subgroup selection, or MODEL EDGE rule is allowed.

## Frozen FTN state

The already coverage-qualified state uses a six-game exponential half-life and only target-prior
games. Historical exact publication timestamps are not claimed; the historical experiment is
therefore development-only. The source is live-capable in season and prospective use must preserve
the real capture timestamp.

For a forecasted player's team, `own_off_*` features are the strictly lagged offense profile.
`opp_def_*` features are the strictly lagged defensive profile for that game's opponent.

### Passing yards
- own motion rate
- own play-action rate
- own no-huddle rate
- own QB-out-of-pocket rate
- own shotgun rate
- own catchable rate
- own drop rate
- opponent blitz-play rate
- opponent mean blitzers
- opponent mean pass rushers
- opponent contested-ball rate
- opponent catchable-allowed rate
- opponent created-reception-allowed rate

### Passing TDs
- own motion rate
- own play-action rate
- own RPO rate
- own QB-out-of-pocket rate
- opponent blitz-play rate
- opponent mean pass rushers
- opponent contested-ball rate
- opponent catchable-allowed rate

### Receiving yards
- own motion rate
- own play-action rate
- own screen rate
- own catchable rate
- own drop rate
- opponent blitz-play rate
- opponent contested-ball rate
- opponent catchable-allowed rate
- opponent created-reception-allowed rate

### Receptions
- own motion rate
- own screen rate
- own catchable rate
- own drop rate
- opponent contested-ball rate
- opponent catchable-allowed rate

### Rushing yards
- own motion rate
- own RPO rate
- own shotgun rate
- own pistol rate
- own mean offensive backfield count
- opponent mean defenders in box
- opponent blitz-play rate
- opponent mean blitzers

These feature sets are frozen before empirical evaluation. No feature may be added/removed because
of the observed challenger result.

## Matched incremental baseline

The primary comparator is a matched **market + V1 residual** model:
- same prop-family partition;
- same training rows;
- same sportsbook offset;
- same L2 penalties;
- same train-only transformation machinery;
- only the V1-market logit gap, with no FTN features.

Primary incremental statistic:

```
FTN challenger accuracy - matched market+V1 residual accuracy
```

Also report raw frozen-V1 direction and sportsbook price-direction accuracy.

## Chronological evaluations

### Fixed-anchor
Train once:
- 2023 Weeks 1–9.

Evaluate without refitting:
- 2023 Weeks 10–18;
- all qualified 2024 rows;
- all qualified 2025 rows.

### Rolling-origin
- 2024 evaluation: train on qualified 2023 rows only.
- 2025 evaluation: train on qualified 2023–2024 rows only.

At every target week, FTN state itself is recomputed from rows strictly before that week.
Completed 2026 outcomes are prohibited from all fitting and selection.

## Metrics

Report:
- decided non-push N;
- unique games and players;
- FTN challenger accuracy;
- matched residual baseline accuracy;
- frozen V1 accuracy;
- sportsbook price-direction accuracy;
- FTN minus matched baseline;
- FTN minus V1;
- FTN minus sportsbook;
- Brier score and log loss for FTN, matched residual, V1, and sportsbook;
- game-clustered 95% CI for FTN accuracy;
- game-clustered 95% CI for FTN-minus-matched-baseline;
- by-prop results;
- source/state coverage.

Bootstrap:
- cluster = game_id;
- seed = 20260918;
- 3,000 replicates in automated evaluation.

## Decision rule

This experiment is **incremental-signal positive** only if:
1. the aggregate FTN-minus-matched-baseline point estimate is positive in the fixed-anchor test;
2. the aggregate fixed-anchor game-clustered 95% interval excludes 0 on the positive side; and
3. the 2024 rolling-origin point estimate is also positive.

This decision rule does not authorize production. It only determines whether FTN matchup state
deserves inclusion in the frozen prospective Props 2.0 candidate.

## Interpretation boundary

2023–2025 has already informed this research program. A positive result is hypothesis-generating
and may justify freezing a prospective challenger, but promotion requires untouched immutable
future forecasts. A negative result must be preserved; no post-hoc subgroup threshold may rescue it.
