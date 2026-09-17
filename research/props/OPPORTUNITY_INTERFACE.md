# LevLine Props Opportunity Interface

Status: RESEARCH BETA  
Engine: `props-opportunity-v1`

## Purpose

`nfl_forecast.props_opportunity` owns opportunity/volume only. It does **not** project yards per opportunity, touchdown conversion efficiency, sportsbook prices, or official LevLine winner probabilities.

The simulation lane should import exactly:

```python
from nfl_forecast.props_opportunity import ForecastContext
from nfl_forecast.props_opportunity_handoff import build_simulation_ready_opportunity_projection
```

Call `build_simulation_ready_opportunity_projection(...)` once per offense/game. The returned `OpportunityProjection` is JSON-serializable through `.to_dict()` and contains both the core volume hierarchy and any supported scoring-area opportunity shares.

If a caller already owns fully model-ready historical and current-player tables, it may instead import `build_opportunity_projection` directly from `nfl_forecast.props_opportunity`. The canonical handoff is preferred because it enforces the props-data availability/route boundaries and adds TD-opportunity channels.

## Canonical props-data handoff

The preferred handoff consumes the props-data lane's `levline_props_player_state.v1` current-slate contract:

```python
projection = build_simulation_ready_opportunity_projection(
    team_history,
    player_history,
    player_state,
    context,
    availability_priors=preregistered_availability_beta_priors,
    route_prior_means=preregistered_route_participation_prior_means,
    primary_qb_player_id=verified_starter_id,          # optional override
    primary_qb_provenance=verified_starter_source,     # required with override
    role_adjustments=point_in_time_role_adjustments,   # optional
    role_adjustments_provenance=role_source,           # required with adjustments
)
```

The canonical contract deliberately emits categorical availability rather than invented probabilities. The adapter treats explicit `OUT` as 0 and explicit `AVAILABLE` as 1, while `QUESTIONABLE`, `DOUBTFUL`, and `UNKNOWN` **require explicit caller-supplied Beta(alpha, beta) priors**. No default injury-status probability is hidden in this lane. The Beta mean becomes `availability_probability` and its posterior standard deviation becomes `availability_uncertainty`.

The canonical `expected_role == QB_PRIMARY` flag is the default QB resolver. A verified point-in-time starter source may override it through `primary_qb_player_id`, but the override fails unless provenance is supplied and the ID resolves to exactly one canonical QB row. This is important for promoted backups/rookies whose lagged role history may not identify the actual current starter.

Descriptive WR/RB/TE role labels are not silently converted into predictive coefficients. Point-in-time evidence of a limitation, promotion or demotion can instead provide non-negative `role_multiplier`, `carry_role_multiplier`, `target_role_multiplier`, and/or `route_role_multiplier` by player ID. Any such adjustment requires explicit provenance. The projection audit and player rows preserve availability-prior, QB-source and role-adjustment provenance.

## Required historical inputs

`team_history` is one row per completed team-game and must contain `game_id`, `season`, `week`, `team`, `pass_attempts`, and either explicit or derivable `dropbacks`, `offensive_plays`, `designed_rush_attempts`, plus `team_targets` (or player targets from which the team total can be reconstructed). If `dropbacks` is absent it is derived as pass attempts + sacks + QB scrambles. If `offensive_plays` is absent it is derived as dropbacks + designed rush attempts.

`player_history` is one row per player-game and must contain stable `player_id`, `position`, rushing volume, `targets`, and `receptions`. The core model requires `designed_carries`. The preferred handoff may derive non-QB designed carries from `rush_attempts`, but QB generic rush attempts include scrambles and therefore require player-level `qb_scrambles` or an unambiguous team-game `qb_scrambles` count to subtract. Ambiguous multi-QB histories fail closed. Routes may be supplied when a point-in-time-safe source exists. These are model-fitting count rows, not the canonical current-slate summary table, and should come from the same strictly lagged source history used by the props-data lane.

When route history is missing, the canonical handoff does **not** turn missing routes into observed zero routes. It requires explicit preregistered position-level route-participation prior means. Missing route rows carry zero historical route exposure plus an explicit per-player prior mean, so observed same-position teammates cannot silently replace the preregistered missing-route prior. The projection audit lists every prior-only player, the supplied prior means, and `fabricated_observed_routes=0`. If neither route evidence nor explicit route priors are available, the adapter fails closed.

The handoff also consumes `red_zone_carries`, `goal_line_carries`, `red_zone_targets`, and `end_zone_targets` when present. It emits separate Dirichlet share distributions for each channel. QB is eligible for red-zone/goal-line carry shares; RB/FB/WR/TE are eligible for receiving scoring-area target shares. If `first_read_targets` exists from a point-in-time-safe source, a first-read target-share distribution is emitted as well. Missing scoring-area columns remain explicitly unavailable; they are never fabricated.

The handoff records the designed-carry normalization source in the projection audit. This prevents the canonical data lane's aggregate QB rush attempts from being silently double-counted with the separately sampled scramble branch.

The forecast horizon is conservative at the NFL-week block level: any historical row from the forecast week or a future week is rejected. Earlier completed 2026 games may update chronological player/team state, but this module does not use completed 2026 results for architecture, feature, hyperparameter, threshold, or weight selection.

## Simulator contract

Use `projection.hierarchy`, not independent marginal draws, in this order:

1. Sample `team_offensive_plays` from the Gamma-Poisson posterior predictive.
2. Sample `dropback_rate_given_team_plays` from Beta; sample dropbacks with a Binomial.
3. Designed rushes = team plays - dropbacks.
4. Sample `dropback_outcome_given_dropback` from Dirichlet; allocate dropbacks by Multinomial to pass attempts, sacks, and QB scrambles.
5. Sample `designed_carry_share_given_designed_rush` from Dirichlet; allocate designed carries by Multinomial. Primary-QB rushing opportunities = primary-QB designed carries + scrambles.
6. Sample each active player's `route_participation_given_dropback` against dropbacks.
7. Sample `targetable_attempt_rate_given_pass_attempt`; sample team targets with a Binomial.
8. Sample `target_share_given_team_target` from Dirichlet; allocate team targets with a Multinomial.
9. Sample each player's `reception_probability_given_target`; sample receptions with a Binomial.
10. For TD simulation, sample any available scoring-area share distributions (`red_zone_carry_share`, `goal_line_carry_share`, `red_zone_target_share`, `end_zone_target_share`) and optional `first_read_target_share` from their Dirichlet parameters; the TD/efficiency lane remains responsible for scoring conversion conditional on those opportunities.

`projection.marginals` provides central estimates and moment-matched uncertainty for reporting/debugging, but those marginal count approximations are **not** the preferred simulation path because separate marginal draws would break shared-state coherence.

## Role redistribution

Carry and target shares are posterior role concentrations, not depth-chart winner-take-all rules. Availability and explicit role multipliers damp/remove a player's concentration, then the missing share is redistributed across every remaining eligible player in proportion to shrunk historical role evidence. Availability uncertainty reduces Dirichlet concentration, widening the simulated share distribution.

Routes are not a one-sum share, so the engine preserves expected route slots per dropback when capacity permits. Vacated route participation is spread across active pass catchers according to shrunk historical route participation and remaining capacity, capped at 1.0 per player. The output includes baseline values, post-availability values, deltas, and any route slots that could not be credibly reassigned.

Scoring-area shares reuse the same availability/role redistribution machinery. Missing goal-line carries, for example, are redistributed across all active carry-eligible players according to shrunk goal-line evidence rather than assigned wholesale to RB2. Receiving scoring-area shares behave analogously across eligible pass catchers.

## Context/game-environment adjustments

`ForecastContext` accepts explicit `play_volume_multiplier`, `play_volume_uncertainty_multiplier`, `dropback_logit_delta`, `scramble_logit_delta`, and `targetable_attempt_logit_delta`. These are intentionally transparent hook points for the integration lane's point-in-time game environment, pace, PROE/game-script, QB-style, opponent-tendency, coaching/system, and matchup signals. Defaults are neutral. Any non-neutral adjustment must provide `adjustments_provenance`; do not populate an adjustment unless the upstream feature is historically reconstructable or explicitly prospective-only and labeled as such.

## Diagnostics

`rolling_origin_team_diagnostics` performs one-step-ahead team-play/dropback-rate diagnostics and excludes 2026 by default. `diagnostics_summary` reports MAE/RMSE. This is a lightweight diagnostic surface, not an invitation to tune on 2026 outcomes.
