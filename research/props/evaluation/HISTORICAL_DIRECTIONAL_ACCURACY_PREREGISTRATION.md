# LevLine Props Historical Directional Accuracy — Preregistration

Status: **FROZEN BEFORE HISTORICAL OUTCOME SCORING**  
Contract version: `levline-props-historical-directional-v1.0`  
Parent evaluation contract: `levline-props-eval-v1.0`  
Frozen Props architecture: `research/props-integration@db5478fd735ef0cad8fd1215e8b1fb6a96a3a21d`

## 1. Primary question and headline number

This experiment exists to produce the simple historical number requested for LevLine Props:

**X = correct directional prop calls / (correct + incorrect directional prop calls)**

Pushes, voids, and exact model/market ties are reported but are not in the denominator.

The primary result will be written as:

> LevLine Props directional accuracy: **X% (W / (W+L))** over the 2023–2025 NFL regular seasons.

This does not replace MAE, calibration, market-relative scoring, or uncertainty analysis. It is the simple headline accuracy statistic.

## 2. Evaluation seasons

Primary:
- 2023 regular season, Weeks 1–18
- 2024 regular season, Weeks 1–18
- 2025 regular season, Weeks 1–18

The three seasons are fixed before scoring.

Secondary sensitivity:
- 2024–2025 regular seasons only
- postseason observations where source and schedule mapping qualify

The 2024–2025 sensitivity may not replace the three-season primary simply because its accuracy is higher.

## 3. Historical market source

Source repository:
- `gcampb41/nfl_data-`, forked from `theedgepredictor/odds-data-pump`

Documented upstream player-prop source:
- Action Network historical player props

Season files:
- `data/processed/football/nfl/player_props/2023.parquet`
- `data/processed/football/nfl/player_props/2024.parquet`
- `data/processed/football/nfl/player_props/2025.parquet`

The raw dataset is downloaded transiently during research evaluation. It is not vendored into LevLine.

### Primary market threshold

Use only rows with:
- `book_id == 30` (OPEN);
- `open_inferred == False`;
- stable `player_id`;
- supported offensive position;
- a valid Over and Under pair at the same threshold;
- the same event/player/prop identity.

Synthetic/fallback OPEN rows are excluded from the primary result.

### Market-source sensitivity analyses

Report the same metric separately, where valid paired rows exist, for:
- Action Network consensus: `book_id == 15`
- DraftKings: `book_id == 68`
- FanDuel: `book_id == 69`

These are sensitivity analyses and may not be selected after scoring to maximize accuracy.

## 4. Headline prop families

Primary directional accuracy includes only conventional two-way line markets supported by the frozen LevLine Props engine:

- QB passing yards
- QB rushing yards
- QB passing TD count
- RB rushing yards
- RB receiving yards
- RB receptions
- WR receiving yards
- WR receptions
- TE receiving yards
- TE receptions

Source bet types:
- `passing_yards`
- `passing_tds`
- `rushing_yards`
- `receiving_yards`
- `receptions`

Position determines the public family.

Anytime-TD and other one-sided/milestone markets are excluded from the headline X because their historical source shape does not provide the same clean two-way threshold interpretation. TD-event performance may be reported separately if legitimately reconstructable.

## 5. Historical point-in-time player-state adapter

No season-end roster or eventual box-score participation may be used as a model input.

For a target historical event, the current modeled player population is constructed solely from pregame market metadata:
- stable player ID;
- player name token;
- supported offensive position;
- team;
- event identity;
- existence of a historical pregame player-prop market.

No sportsbook line value or odds are supplied to the football model.

Market-listed players are treated as the pregame modeled player set. Players without a market are represented implicitly by the simulator's residual team bucket.

This is a **market-listed population reconstruction**, not a claim that the complete historical roster has been reconstructed.

### Pre-outcome source clarification — opening-snapshot player population

Recorded before the first historical outcome-scoring run completed.

For the primary genuine-OPEN experiment, the modeled player population and QB-market existence evidence are restricted to genuine OPEN rows (`book_id == 30`, `open_inferred == False`). Later consensus/book listings may not add players to an opening-line forecast.

For a preregistered book-specific sensitivity analysis, player-population/QB evidence is restricted to that book's rows.

This clarification narrows the information set to the same market horizon being evaluated and is not outcome-driven.

## 6. Availability rule

A market-listed offensive player is supplied to the football model as available because the sportsbook had published a pregame player market for that player.

For grading only:
- if postgame snap data show zero offensive snaps, the prop is classified as void/non-participation and excluded;
- if the player logged positive offensive snaps, an actual value of zero is a valid realized statistic and is retained;
- if participation cannot be established from a stable-ID snap source, the observation is excluded rather than guessed.

Postgame snaps are never provided to the forecast model.

## 7. Historical primary-QB rule

QB identity is derived only from pregame market existence.

For each team/event:
1. if exactly one stable-ID QB has a `passing_yards` market at any qualified source, designate that player QB1;
2. otherwise, if exactly one stable-ID QB has a `passing_tds` market, designate that player QB1;
3. otherwise the team's primary QB is ambiguous and the entire game is excluded from the coherent simulation.

Line magnitude, closing outcome, final starter, snaps, pass attempts, or game result may not break a QB tie.

## 8. Game mapping

Each Action Network event must map uniquely to one nflverse schedule game using:
- season;
- canonical week;
- exactly two valid NFL team codes represented by the event;
- unique schedule team pair.

Rows with free-agent/invalid team codes or ambiguous event-to-game mapping are excluded.

Kickoff comes only from the nflverse schedule.

### Pre-outcome nflverse scramble normalization

Recorded after the first pilot failed during input validation and before any historical outcome was scored.

The frozen upstream contract requires every `qb_scramble == 1` row to also be a rushing attempt. Where the nflverse source has `qb_scramble == 1` and `rush_attempt != 1`, the historical source adapter sets `rush_attempt = 1` before constructing lagged opportunity history.

This is a deterministic event-schema normalization: a QB scramble is a rushing play. It does not inspect player totals, market outcomes, forecast errors, or evaluation results. The number of normalized source rows must be reported.

### Engineering-pilot source amendments

The 2025 Week-1 reduced-simulation engineering pilot is permanently excluded from threshold/rule selection and from the reported X. Its only purpose is validating source joins and executable contracts.

Two source-compatibility amendments are fixed before the full 2023–2025 run:

1. **Event identity:** Action Network event-to-NFL-game mapping uses the companion historical game-lines dataset's `event_id` and team metadata, not the subset of player-prop rows. This avoids falsely requiring both teams to have a particular player-prop book listing.
2. **Negative cumulative yard sufficient statistics:** if a player's strictly prior-game passing, QB-rushing, non-QB rushing, or receiving yard total is negative, that affected efficiency channel is marked unavailable by zeroing that channel's historical sufficient statistics (including the associated sub-counts needed for contract consistency). Negative NFL yardage is legitimate, but the frozen efficiency input validator requires non-negative historical yard totals. This fallback therefore reverts the affected channel to the fixed prior rather than clipping the observed mean or altering the model.

Neither amendment depends on whether the pilot predictions won or lost. The full three-season scoring rules, books, prop families, simulation size, and directional rule remain unchanged.

## 9. Forecast chronology

For every target week:
- opportunity and efficiency sufficient statistics use only games from prior weeks;
- target-week PBP is excluded in full;
- position-level efficiency/scoring priors are fit only through the **previous season**;
- prior games from the current season may update chronological player/team state exactly as the frozen 2026 architecture allows.

Training horizons:
- 2023 forecasts: priors through 2022
- 2024 forecasts: priors through 2023
- 2025 forecasts: priors through 2024

Historical state coverage begins in 2021 so the first evaluation season has prior evidence.

Completed target-season outcomes may never update the structural prior fit, but prior weeks may update the frozen engine's rolling opportunity/player/team sufficient statistics.

## 10. Route prior rule

Because the frozen Research Beta requires explicit route-participation priors when point-in-time routes are unavailable, use the already integration-tested structural values:

- RB: 0.55
- WR: 0.90
- TE: 0.75

These values are frozen before scoring and may not be changed based on historical results.

No role multipliers or retrospective injury adjustments are applied.

## 11. Simulation

Use the frozen coherent Props simulator:
- 20,000 simulations per game;
- market-agnostic simulation;
- deterministic seed derived from SHA-256 of canonical game ID;
- 80% prediction interval;
- no sportsbook threshold supplied until after simulation.

No model parameter is tuned on 2023–2025 evaluation results.

## 12. Directional prediction rule

For each qualifying two-way market:

- if LevLine Fair Line > market line: **OVER**
- if LevLine Fair Line < market line: **UNDER**
- if equal: **NO CALL**

No minimum edge threshold is imposed on the primary directional-accuracy statistic.

This is deliberately analogous to winner-pick accuracy: every non-tied model direction counts.

## 13. Outcome grading

Official actuals are derived from nflverse game/PBP evidence using stable player IDs.

For a market line L and actual result A:
- A > L: OVER wins
- A < L: UNDER wins
- A == L: PUSH

A LevLine call is correct when its direction equals the realized side.

Primary headline:
`accuracy = wins / (wins + losses)`

Always report:
- wins;
- losses;
- pushes;
- no-calls;
- excluded/void;
- total qualified forecasts;
- unique players;
- unique games;
- unique weeks.

## 14. Multiple books and duplicate observations

The primary X uses exactly one genuine OPEN threshold per event/player/prop identity.

Over/Under rows are paired into one forecast observation. They are not counted as two observations.

Book-specific sensitivity analyses are kept separate and never pooled into the headline denominator.

## 15. Statistical uncertainty

For the headline X report:
- Wilson 95% interval for win rate;
- game-clustered bootstrap 95% interval;
- N forecasts;
- unique games.

Dependence between props in the same game is therefore not treated as independent for the clustered interval.

## 16. Baselines

Report alongside X:
- observed OVER frequency;
- observed UNDER frequency;
- majority-side naive accuracy;
- trailing-5 player-stat directional baseline where prior history exists;
- Fair-Line MAE versus actual;
- market-line MAE versus actual.

The baseline cannot use target-game or future outcomes.

## 17. Subgroups

Report, without cherry-picking:
- by season;
- by exact prop family;
- by position;
- by forecasted side;
- by available history depth;
- by Fair-Line minus market-line magnitude using the previously preregistered standardized bins where model SD exists.

A subgroup does not replace the overall result merely because it has the highest accuracy.

## 18. Coverage rule for the headline market source

The genuine-OPEN primary result is considered sufficiently broad if it produces at least:
- 1,000 non-push directional calls;
- 100 unique games;
- all three primary seasons represented.

If genuine OPEN fails this coverage rule, the report must say so. The consensus (`book_id=15`) result may then be shown as the **coverage fallback**, but it must be explicitly labeled as such and genuine OPEN must still be displayed.

This switch is based only on source coverage, never on which source yields the higher accuracy.

## 19. Interpretation

The result may legitimately be:
- above 50%;
- near 50%;
- below 50%;
- mixed by family;
- unstable despite a large raw prop count because of game-level dependence.

No post-hoc threshold, subgroup, season window, route prior, bookmaker, or filtering rule may be introduced to improve X after outcomes are scored.
