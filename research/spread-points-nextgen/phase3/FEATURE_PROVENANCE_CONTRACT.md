# Phase 3 Feature & Provenance Contract

**Frozen before first development output:** yes  
**Research gate:** `KEEP_FROZEN_PHASE3_CONTRACT`

## Shared data universe

- regular-season NFL games only;
- model-building history begins in 2016;
- Phase 3 emitted development rows are 2022–2024 only;
- 2025 is not loaded into the Phase 3 runner and any request for target season >=2025 fails closed;
- completed-2026 outcomes are not loaded or available to selection code;
- play-by-play foundation: nflverse/nflreadpy historical PBP;
- schedule/results/market foundation: nflverse games schedule;
- historical `spread_line` and `total_line` are labeled **historical closing/late benchmark; exact horizon opaque**.

## Identity and target contract

- `actual_margin = home_score - away_score`;
- `actual_total = home_score + away_score`;
- positive historical `spread_line` = market-implied home margin;
- `home_points = (total + margin)/2`;
- `away_points = (total - margin)/2`.

Game identity is `game_id`; season/week/home/away must be unique and consistent with the schedule scaffold.

## Chronology

Outer Phase 3 development targets: 2022, 2023, 2024.

For outer season Y:

- fit only on seasons `< Y`;
- inner validation seasons are `< Y` and `>=2019`;
- each inner training block begins in 2016;
- use the latest four eligible inner validation seasons;
- when fewer than two eligible inner folds exist, use the frozen fallback and record `DEFAULT_INSUFFICIENT_INNER_HISTORY`;
- imputation, scaling, team effects, covariance, dispersion and any empirical simulation distribution are estimated from the training block only.

## Fixed pregame state construction

For lagged process summaries, a team's observed game metric is shifted by one completed game before an exponentially weighted mean is calculated.

Fixed EWMA half-life: **8 team games**.

No current-game PBP contributes to its own forecast state. States carry across season boundaries within the 2016+ history; there is no target-season normalization.

## A0 exact feature schema

Categorical team effects:

- offense team;
- opponent defense team.

Numeric features:

1. offense EPA/play EWMA8;
2. opponent defense EPA/play allowed EWMA8;
3. offense pass EPA/play EWMA8;
4. opponent defense pass EPA/play allowed EWMA8;
5. offense success rate EWMA8;
6. opponent defense success rate allowed EWMA8;
7. team-perspective rest differential;
8. home indicator.

Training-row observation weights use only the frozen A0 half-life grid and each offense team's prior game index. No feature-window sweep is permitted.

A0 residual home/away covariance for outer Y is calculated from games in the outer training block only after fitting the selected outer model. It never includes target-Y residuals.

## B0 drive taxonomy

A drive is identified using nflverse `fixed_drive` where available, otherwise `drive`, within `game_id` and offense (`posteam`). Only regular-season drives with a known offense and at least one offensive PBP row are used.

Outcome mapping is frozen:

- **TD** — drive result identifies touchdown;
- **FG** — drive result identifies a successful field goal and does not identify missed/blocked/no-good field goal;
- **EMPTY** — every other offensive drive result, including punt, turnover, downs, missed FG, end of half/game and other zero-point offensive result.

This compact taxonomy deliberately does not create separate turnover/punt/missed-FG outcome classes.

## B0 play/process definitions

- play count: PBP rows on the drive with finite EPA;
- success: nflverse `success` when available, otherwise `epa > 0`;
- turnover drive: any interception or lost fumble on the drive;
- explosive play: an offensive play with `yards_gained >= 20`;
- red-zone opportunity drive: any offensive PBP row on the drive with `yardline_100 <= 20`;
- red-zone TD: a red-zone opportunity drive classified TD.

### Frozen red-zone shrinkage

Red-zone states use **prior completed games only** and empirical-Bayes shrinkage toward the expanding league red-zone TD rate available before that game.

Prior strength: **20 red-zone drives**.

For offense before game g:

`rz_td_state = (prior_team_rz_td + 20 * prior_league_rz_td_rate) / (prior_team_rz_drives + 20)`

Defense uses the same formula with prior red-zone TDs/drives allowed.

The league prior is calculated from complete games strictly before g. If no earlier league red-zone drive exists, the deterministic initialization is `0.50`. No target-season data is borrowed.

## B0 expected-drive schema

Exactly:

1. offense drive-count EWMA8;
2. opponent drive-count-allowed EWMA8;
3. offense plays-per-drive EWMA8;
4. opponent plays-per-drive-allowed EWMA8;
5. home indicator;
6. team-perspective rest differential.

No A0 output or state enters B0.

## B0 drive-outcome schema

Categorical:

- offense team;
- defense team.

Numeric:

- home indicator;
- rest differential;
- offense EPA/play EWMA8;
- defense EPA/play allowed EWMA8;
- offense success-rate EWMA8;
- defense success-rate allowed EWMA8;
- offense turnover-per-drive EWMA8;
- defense takeaway-per-drive EWMA8;
- offense explosive-rate EWMA8;
- defense explosive-rate-allowed EWMA8;
- offense red-zone TD conversion state;
- defense red-zone TD allowed state.

## B0 touchdown-point mechanism

For each outer/inner fit, the TD point distribution is estimated from **training drives only**.

For TD drives with an observed same-possession score increment of 6, 7 or 8 points, empirical frequencies determine the 6/7/8 draw probabilities. If no qualifying training TD drive exists, deterministic fallback is 7 points. No target-season conversion outcome enters the distribution.

## B0 shared volume variation

After the training-only expected-drive model is fitted, calculate for each training game the mean of the two team drive-count residuals (`actual drives - expected drives`). Final simulation samples this empirical game-level residual with replacement and adds the same draw to both teams' Poisson means, with only a lower numerical bound of 1.0 drive. This provides shared game-volume variation without an additional fitted parameter.

## B0 rare-score tail

The frozen low-frequency tail is training-only and nonselective.

For each team-game, derive `rare_points` from identifiable non-offensive scoring events in PBP:

- safety credited to the defending team: 2 points;
- touchdown for a `td_team` different from the offensive `posteam`: 7-point empirical rare-score event.

The simulator samples the full empirical training team-game rare-points distribution, including zeros, independently for each team. If source columns do not permit identification, the deterministic fallback distribution is `[0]` and the fallback is recorded. The mechanism is never changed because of development accuracy.

## C0 source and horizon contract

C0 uses only A0 football representations that were generated out of sample for their game. Earlier OOF A0 rows may be generated internally to train C0; committed future-stack surfaces remain 2022–2024.

Historical market fields are labeled exactly:

`historical_closing_late_benchmark_exact_horizon_opaque`

They may not be called T-120, T-60, live or real-time.

Margin M3 predictors exactly:

- market home margin;
- A0 expected margin;
- A0 minus market margin disagreement;
- A0 offense-strength difference;
- A0 defense-strength difference;
- rest differential.

Total M3 predictors exactly:

- market total;
- A0 expected total;
- A0 minus market total disagreement;
- summed A0 offense strength;
- summed A0 defense strength;
- rest differential.

M1 uses market line level only. M2 uses the A0 football forecast/disagreement/strength terms plus rest context but omits the separate market-line calibration term. M0 is exactly the raw market.

## A0 compact strength semantics

For each fitted A0 Ridge model:

- offense strength is the fitted coefficient associated with the offense-team indicator;
- defense strength is the negative of the fitted coefficient associated with the defense-team indicator, so larger values consistently mean stronger point suppression.

Per-game derived summaries:

- offense-strength difference = home offense strength - away offense strength;
- defense-strength difference = home defense strength - away defense strength;
- summed offense strength = home offense + away offense;
- summed defense strength = home defense + away defense.

These coefficients are training-only fit objects; target-season outcomes never affect them.

## Missingness

Numeric model-internal state is median-imputed by an imputer fit only on the training block. Externally sourced missingness is not interpreted as a healthy/normal state. The Phase 3 reference models intentionally avoid unqualified injury, starter and forecast-weather fields.

## Provenance on every emitted prediction

Every emitted OOF row must include at minimum:

- candidate ID;
- game ID;
- season/week;
- home/away;
- training-through boundary;
- outer target season;
- selected hyperparameters;
- source contract version;
- code/config identity;
- fallback state;
- random seed for stochastic simulation where applicable;
- market-horizon label where applicable.

## Production firewall

No code in Phase 3 may be imported by the production weekly pipeline. No Phase 3 output is written to `outputs/`, `site/`, production artifacts or official history.