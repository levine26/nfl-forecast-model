# LevLine Props efficiency / TD handoff contract

Status: **RESEARCH BETA**  
Engine: `props-efficiency-td-research-beta-v1`  
Lane: `research/props-efficiency-td`

This lane converts upstream offensive opportunities into conditional efficiency and coherent touchdown parameters. It does **not** change official LevLine/F-ST winner probabilities and it does not make betting decisions.

## Entry point

```python
from nfl_forecast.props_efficiency_td import build_efficiency_td_parameters

build = build_efficiency_td_parameters(
    player_inputs,
    team_inputs,
    matchup_coefficients=validated_matchup_coefficients,  # optional
)
```

The return value has four fields:

- `player_parameters`: one row per offensive player/game/team.
- `team_td_parameters`: one row per team/game.
- `diagnostics`: TD reconciliation checks by team/game.
- `audit`: version/governance metadata.

`simulator_contract_columns()` returns the stable minimum columns the simulation lane may depend on.

## Upstream opportunity contract

`player_inputs` must include stable identity, timestamps, source state, opportunity forecasts, pregame historical sufficient statistics, and pre-2026 priors. Required opportunity forecasts are:

- `expected_pass_attempts`
- `expected_qb_rush_attempts`
- `expected_carries`
- `expected_routes`
- `expected_targets`

`team_inputs` must include:

- `expected_drives`
- `expected_red_zone_trips`
- `prior_red_zone_td_rate`
- `prior_pass_td_fraction`
- `expected_non_red_zone_pass_tds`
- `expected_non_red_zone_rush_tds`

The opportunity lane remains authoritative for volume. This lane does not independently refit attempts, carries, routes, targets, drives, or red-zone trips.

## Efficiency process

The simulator should preserve the football hierarchy instead of drawing a black-box final-stat total.

### QB passing

1. Draw/condition on upstream pass attempts.
2. Draw completion probability from `Beta(completion_alpha, completion_beta)`.
3. Draw completions conditional on attempts.
4. Convert completions to yards using `yards_per_completion_mean` plus `yards_per_completion_event_sd` and parameter uncertainty from `yards_per_completion_mean_se`.

### Rushing

For each player, use upstream rush opportunities and:

- `rushing_yards_per_attempt_mean`
- `rushing_yards_per_attempt_event_sd`
- `rushing_yards_per_attempt_mean_se`

QB rushing opportunities come from `expected_qb_rush_attempts`; non-QB rushing opportunities come from `expected_carries`.

### Receiving / receptions

1. Draw/condition on upstream targets.
2. Draw catch probability from `Beta(catch_alpha, catch_beta)`.
3. Draw receptions conditional on targets.
4. Convert receptions to yards using `receiving_yards_per_reception_mean` plus the event/parameter uncertainty fields.

## Shrinkage

Small samples are deliberately pulled toward pre-2026 role/position priors. Raw recent YPC, catch rate, yards/reception, completion rate, red-zone target rate, end-zone target rate, and goal-line carry rate are never treated as stable talent estimates.

The v1 research-beta pseudo-counts are structural defaults only; they were not selected using completed 2026 outcomes and are not production-authorized calibration parameters. Future calibration must be performed on data ending in 2025 or earlier before any change is accepted.

## Matchup interactions

Matchup effects are **neutral by default**. They activate only when `matchup_coefficients` is supplied and every coefficient declares a finite `trained_through_season <= 2025`; missing or non-numeric provenance fails closed.

Approved process-oriented feature families include:

- pressure / pass-rush mismatch
- offensive-line / pass-rush mismatch
- man/zone tendencies
- explosive-pass suppression
- slot/outside coverage mismatch
- RB vs linebacker coverage
- tackling/YAC suppression
- box/run tendency
- run-defense efficiency
- red-zone defense
- scrambling-QB × pressure/man interactions
- defensive availability impact

Crude opponent fantasy-points-allowed inputs are not an approved interface.

Player matchup coefficients can adjust completion rate, yards/completion, rushing YPC, catch rate, receiving YPR, red-zone target rate, end-zone target rate, and goal-line carry rate. Team matchup coefficients can adjust red-zone TD rate and pass-vs-rush TD fraction.

## Touchdown coherence

TDs are generated at the team level first:

- `expected_red_zone_tds = expected_red_zone_trips * red_zone_td_rate_mean`
- passing TD opportunities = red-zone TDs × pass-TD fraction + explicit non-red-zone pass-TD expectation
- rushing TD opportunities = red-zone TDs × rush-TD fraction + explicit non-red-zone rush-TD expectation

The v1 count family emitted to the simulator is `poisson_shared_team_baseline`. The simulation lane may replace that count family only through a separately validated contract change; the team means must remain the reconciliation anchors.

Player allocations are then normalized within the team:

- QB passing TD share: expected pass-attempt share.
- Receiving TD share: empirical-Bayes end-zone-target allocation, with red-zone-target/target opportunity fallback.
- Rushing TD share: empirical-Bayes goal-line-carry allocation, with rushing-opportunity fallback.
- `passing_td_share_sd`, `receiving_td_share_sd`, and `rushing_td_share_sd` are the exact marginal standard deviations implied by each allocation Dirichlet posterior. `td_allocation_uncertainty` is the maximum applicable share SD, a conservative dimensionless summary rather than the previous inverse-alpha heuristic.

The builder fails if a team has positive passing-TD expectation but no QB/receiving candidates, or positive rushing-TD expectation but no rushing candidates.

For every team/game, diagnostics enforce:

```text
sum(QB expected_passing_tds) == team expected_passing_td_opportunities
sum(receiver expected_receiving_tds) == team expected_passing_td_opportunities
sum(rusher expected_rushing_tds) == team expected_rushing_td_opportunities
```

A QB passing TD and a receiver receiving TD are two player views of the same simulated team passing-TD event, not two separate team touchdowns. The simulation lane should sample the shared team event count once and allocate it, rather than independently sampling QB and receiver TD totals.

## Anytime-TD interpretation

`expected_anytime_tds` excludes passing TDs because sportsbook anytime-TD markets score the player who possesses the ball in the end zone:

- QB: rushing TD expectation.
- RB: rushing + receiving TD expectation.
- WR/TE: receiving + rushing TD expectation when a rushing role exists.

Internal allocation may include offensive players in roles that are not a supported sportsbook prop family so team totals remain coherent.

## Leakage and fail-closed rules

The builder requires:

- stable `player_id`;
- explicit timezone-aware `feature_data_horizon <= forecast_timestamp < kickoff_timestamp`;
- player/team season, week, opponent, forecast timestamp, and kickoff timestamp alignment within each game/team;
- expected red-zone trips no greater than expected drives;
- versioned priors with `prior_model_trained_through_season <= 2025`;
- explicit `source_status`;
- no current-game/postgame outcome fields;
- finite integer `trained_through_season`, non-empty model provenance, and unique coefficient identity for any optional matchup adjustment.

Unknown or prospective-unqualified sources remain explicitly labeled in `confidence_state`; they are never silently converted into high confidence.

## Current simulation-lane mapping

For the current `props_simulation.py` research interface, integration can map this lane without guessing:

| Simulation field | Source |
| --- | --- |
| `TeamSimulationInput.expected_passing_tds` | `team_td_parameters.expected_passing_td_opportunities` |
| `TeamSimulationInput.expected_rushing_tds` | `team_td_parameters.expected_rushing_td_opportunities` |
| `PlayerSimulationInput.catch_rate` | `player_parameters.catch_rate_mean` |
| `PlayerSimulationInput.receiving_yards_per_reception` | `player_parameters.receiving_yards_per_reception_mean` |
| `PlayerSimulationInput.rushing_yards_per_carry` | `player_parameters.rushing_yards_per_attempt_mean` |
| `PlayerSimulationInput.receiving_td_share` | `player_parameters.receiving_td_share_mean` |
| `PlayerSimulationInput.rushing_td_share` | `player_parameters.rushing_td_share_mean` |
| `PlayerSimulationInput.data_quality_state` | `player_parameters.confidence_state` |

The remaining simulation fields are owned elsewhere: availability probability and pass/target/carry shares come from the opportunity/availability lane; team play volume and pass-rate state come from the opportunity/game-environment lane; residual-bucket efficiency requires an explicit integration prior.

The current simulator accepts point efficiency values. This lane also emits `completion_alpha/beta`, `catch_alpha/beta`, event standard deviations, parameter standard errors, and TD-allocation concentration parameters. Integration must not silently reinterpret those as already sampled outcomes. Either extend the simulator to sample the posterior parameters, or document that the Sunday beta uses posterior means while preserving the uncertainty fields for a subsequent coherent-simulation upgrade.

The current simulator reconciles QB passing yards to summed receiving yards by generating receiving production first. That is a coherent accounting choice, but it means this lane's QB `completion_rate_mean` and `yards_per_completion_mean` are not simultaneously independent yardage generators. If those QB parameters are activated, they must enter as a shared latent constraint/calibration on the same passing process; independently simulating QB passing yards and receiver receiving yards would violate the charter's coherence requirement.

## Downstream fair-line use

This lane does not calculate sportsbook fair lines itself. The simulation lane should use these parameters to generate full player-stat distributions, then expose the sprint-charter outputs:

- mean projection
- median / LevLine Fair Line
- prediction interval
- P(over) / P(under) at a sportsbook line
- fair odds
- push mass for discrete integer markets
- P(1+ TD) / fair TD odds

TD probability must be derived from the coherent simulated event process, not from independent Bernoulli player-TD classifiers.
