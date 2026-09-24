# PLAYER STATE RESEARCH

## Mechanism

The only player-state hypothesis that survives Phase 1 is not “injured players make teams worse.” Markets know that. The proposed signal is the **difference between a timestamped model estimate of the change in expected lineup value and the change already implied by the market**.

For player `i` at time `t`:

`expected_value_i,t = ability_i,t × P(active_i,t) × expected_role_i,t + replacement_value_i,t × (1 - participation_role_weight_i,t)`

Team lineup state is the sum of player/unit contributions with shrinkage and role constraints. The candidate information delta is approximately:

`Δlineup_value_model - Δmarket_fair_line`.

## Evidence

- nflWAR demonstrates a reproducible multilevel framework for isolating offensive skill-player contributions from public PBP and quantifying uncertainty.
- Hoffer & Pincin's sportsbook point-spread-value work finds quarterbacks dominate player point values; passing/rushing contribution predicts those values.
- Player-absence betting research in the NBA finds meaningful absences bias opening lines but that the bias is largely removed by close. This is evidence for timing/assimilation, not static absence alpha.
- Professional systems such as ESPN FPI publicly describe starter/back-up QB and non-QB personnel adjustments.

## Required state decomposition

Always distinguish:

1. **ability** — latent player quality estimated only from information available before the game;
2. **participation probability** — probability of dressing/playing at the prediction timestamp;
3. **role** — expected snaps/routes/carries/pass-block reps, not realized final snaps;
4. **replacement quality** — who actually inherits the role if the player is limited/out;
5. **market assimilation** — contemporaneous line/price reaction to the same information.

## Position/unit priorities

1. QB — separate model; disproportionate point value and replacement variance.
2. Offensive line — continuity and starter availability may matter collectively; individual public valuation is noisy.
3. WR/TE/RB — expected role, route/carry share, concentration and replacement depth.
4. Secondary / pass rush — snap-weighted unit availability, especially clustered absences.
5. Special teams/kicker — potentially relevant near key-number outcomes but sample/role impact likely small.

## PIT risks

- Final inactive lists are only usable at horizons when they had actually been published.
- Realized snap counts are ex-post labels for training ability/role models, not pregame features for the same game.
- Depth charts can be retroactively corrected; historical file existence does not prove as-of availability.
- nflverse injury data currently has a source break after 2024, so 2025+ injury continuity cannot be assumed.
- From 2025 nflverse depth-chart updates carry timestamps rather than weeks; this is promising prospectively but must be archived as-of for historical use.

## Falsification

M2 dies if (a) usable PIT player-state history cannot be reconstructed, (b) the model's lineup delta merely reproduces the contemporaneous market move, or (c) proper-score incrementality disappears after controlling for market level/path. A good football player-value model that does not beat those nulls is still a failed ATS candidate.

## Phase-1 status

`FRONTIER-M2-PLAYER-STATE-DELTA`: **SURVIVES** with high priority, subject to Phase-2 PIT feasibility.