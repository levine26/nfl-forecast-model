# LevLine Props Historical Rolling-Origin Reconstruction Audit

Status: **NOT ADMITTED AS CURRENT-MODEL ACCURACY EVIDENCE**
Evaluation contract: levline-props-eval-v1.0

## Question

Can the current frozen LevLine Props engine be run backward over prior NFL seasons in a way that is genuinely point-in-time and free of future-data leakage?

## Finding

**Not with the currently qualified default source path.**

Several important components are historically reconstructable, but the complete current-model state is not yet reconstructable without source assumptions that the preregistration forbids.

## Components that are reconstructable under chronological cutoffs

src/nfl_forecast/props_upstream.py and the opportunity layer support:

- strictly prior-week PBP history;
- team offensive plays, dropbacks, pass attempts, sacks, QB scrambles, designed rushes and targets;
- stable-ID player carries, targets, receptions and scoring-area opportunity counts;
- chronological team scoring-volume state;
- rolling opportunity posteriors;
- efficiency sufficient statistics;
- refitting efficiency/scoring priors at a declared training horizon.

The engine explicitly rejects training-horizon declarations above 2025 in the frozen 2026 path.

## Components that block a fully qualified historical current-model replay

### 1. Frozen 2026 priors cannot simply be reused earlier

The current frozen empirical efficiency/scoring priors use evidence through 2025. Applying those values to a 2024 or 2025 evaluation game would expose the forecast to future games.

A legitimate historical backtest would need to refit structurally equivalent priors using only seasons available before each evaluation horizon. Such a reconstruction would be a historical analogue, not literally the current 2026 fitted model.

### 2. Default roster loading is season-level, not a proven weekly point-in-time snapshot

load_offensive_props_sources() calls nflverse load_rosters(current_season) and then maps that roster to the target slate.

For a live current-week forecast this is appropriate current state. For a retrospective early-season week, using a later/final season roster state could encode transactions, releases, or team membership that were not known at the target forecast horizon.

Until a historical roster source is explicitly timestamp-qualified by week/as-of time, it is not admissible for a leakage-free historical replay.

### 3. Primary-QB depth-chart qualification is 2025+

resolve_primary_qbs_from_depth_charts() is explicitly designed for timestamped 2025+ nflverse depth-chart rows and discards future snapshots.

This can potentially support 2025 reconstruction where source coverage is verified, but it does not by itself create a complete point-in-time offensive roster and does not qualify earlier seasons.

### 4. Historical availability may not be inferred from playing

The player-state contract correctly forbids deriving pregame availability from final participation, snaps, carries, targets, or box-score presence.

The current live path consumes timestamped prospective injury evidence. Without a separately qualified historical injury-report snapshot for the target horizon, a historical replay cannot silently declare a player available because he eventually played.

### 5. Route data are intentionally fail-closed

The default source bundle sets routes to missing because a trustworthy point-in-time route source is not guaranteed.

The opportunity model permits preregistered route-participation priors, but using such a fallback for a historical experiment must be specified before outcomes are inspected and must match what could have been known at the time.

## Season qualification

| Candidate season | Current qualification | Reason |
| --- | --- | --- |
| 2023 | **Unavailable for current-model accuracy** | current default roster/availability path is not verified point-in-time; QB depth-chart qualification is 2025+ |
| 2024 | **Unavailable for current-model accuracy** | same roster/availability problem; current QB depth-chart qualification does not cover 2024 |
| 2025 | **Potentially reconstructable, not yet qualified** | timestamped QB depth charts may exist, but a complete point-in-time roster/availability reconstruction still must be proven |
| 2026 | **Prospective-only primary program** | immutable original forecast receipts are the gold standard; completed games may evaluate but never tune the frozen model |

## Why no structural-only score is reported

It would be possible to create retrospective player lists using final participation or season-end roster knowledge and then compute plausible-looking MAE/hit rates.

That would answer a different question: “How does this architecture behave when we give it information that may not have been known pregame?”

The requested question is how accurate LevLine Props actually is. A contaminated replay would therefore be more misleading than an N=0 current answer.

## Promotion requirement for a historical backtest

Before a historical season can enter the headline evaluation, a separate source-qualification artifact must establish:

1. week/as-of timestamped offensive roster membership;
2. primary-QB identity known at the forecast horizon;
3. injury/availability status known at the forecast horizon or a preregistered uncertainty fallback that does not use eventual participation;
4. no target-week/current-game PBP, snaps or route outcomes;
5. priors trained only through a horizon preceding the evaluation period;
6. exact source provenance and deterministic reconstruction.

Only after those conditions are satisfied should rolling-origin forecasts be generated and scored.
