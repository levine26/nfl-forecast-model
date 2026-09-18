# LevLine Props 2.0 — NGS Market-Residual Experiment Contract

Status: **FROZEN BEFORE EMPIRICAL NGS-RESIDUAL EVALUATION**  
Created: 2026-09-18  
Branch: `research/props-v2-ngs-residual`  
Parent research boundary: `research/props/v2/PROPS_V2_RESEARCH_PREREGISTRATION.md`

## Question

Do strictly lagged Next Gen Stats player-efficiency features add incremental directional
information beyond a sportsbook no-vig prior and the frozen LevLine V1 probability gap?

This is a retrospective development experiment. 2023–2025 was previously inspected when
diagnosing V1, so a positive result cannot authorize production.

## Fixed model form

For each prop family separately:

```
logit(P_over)
  = logit(P_over_market)
  + intercept
  + beta_v1 * standardized(logit(P_over_v1) - logit(P_over_market))
  + beta_ngs * standardized(NGS state)
  + beta_missing * NGS-missing indicators
```

The sportsbook coefficient is fixed at 1.0 and is not estimated.

All continuous features are transformed from the training block only:
- median imputation from training data only;
- mean/standard-deviation scaling from training data only;
- missing NGS evidence gets an explicit missing indicator and is never interpreted as zero performance.

Fixed penalties:
- residual coefficient L2 = 10.0;
- intercept L2 = 1.0;
- no hyperparameter search.

Minimum training sample:
- 75 decided non-push rows per prop family.

No abstention or MODEL EDGE threshold is permitted in this experiment.

## Fixed prop features

### Passing yards
- average time to throw
- average completed air yards
- average intended air yards
- air-yards differential
- aggressiveness
- air yards to sticks
- completion percentage above expectation

### Passing TDs
- average intended air yards
- aggressiveness
- air yards to sticks
- completion percentage above expectation

### Receiving yards
- average air distance
- cushion
- separation
- intended-air-yards share
- catch percentage
- YAC
- expected YAC
- YAC above expectation

### Receptions
- cushion
- separation
- intended-air-yards share
- catch percentage

### Rushing yards
- NGS efficiency
- percent of attempts against 8+ defenders
- average time to line of scrimmage
- average rush yards
- rush yards over expected per attempt
- rush percentage over expected

## NGS chronology

NGS state for target season/week may use only observations strictly before the target week.
Week-0 season-summary rows are excluded.

The state builder uses an 8-game exponential half-life and opportunity weighting. This was
already implemented and source-coverage validated before this experiment.

Missing weekly NGS publication is missing evidence, not zero performance.

## Matched incremental baseline

The primary comparator is not raw V1. It is a **matched market+V1 residual model** fit:
- separately by the same prop family;
- on the same training rows;
- with the same market offset;
- with the same L2 penalties;
- with the same train-only standardization;
- but with no NGS features.

Primary incremental statistic:

```
NGS challenger accuracy - matched market+V1 residual accuracy
```

Also report raw V1 direction and sportsbook price-direction accuracy.

## Chronological evaluations

### Fixed-anchor stability
Train:
- 2023 Weeks 1–9 only.

Evaluate without refitting:
- 2023 Weeks 10–18;
- all qualified 2024 rows;
- all qualified 2025 rows.

### Rolling-origin
- 2024 evaluation: train on qualified 2023 rows only.
- 2025 evaluation: train on qualified 2023–2024 rows only.

No completed 2026 result may enter any fit.

## Metrics

Report:
- decided non-push N;
- unique games and players;
- NGS challenger directional accuracy;
- matched baseline directional accuracy;
- V1 directional accuracy;
- sportsbook no-vig price-direction accuracy;
- NGS minus matched-baseline percentage points;
- NGS minus V1;
- NGS minus sportsbook;
- game-clustered 95% bootstrap interval for NGS accuracy;
- game-clustered 95% bootstrap interval for NGS-minus-matched-baseline;
- by-prop breakdown;
- NGS source coverage.

Bootstrap:
- cluster = game_id;
- deterministic seed = 20260918;
- 3,000 replicates in the automated workflow.

## Interpretation boundary

A positive retrospective result is hypothesis-generating only because V1's 2023–2025 outcomes
were already inspected before this architecture was proposed. Promotion requires untouched,
immutable prospective evidence under the parent Props 2.0 promotion gate.

No result from this experiment may be used to choose a post-hoc selective threshold and then
present that threshold as prospectively validated.
