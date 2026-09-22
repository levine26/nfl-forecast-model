# Phase 1 — Current LevLine Architecture Audit

**Status:** research audit / no production change  
**Audited main:** `e63fd396e1ae37fc63a4085e380ba52e0412dc74`  
**Primary branch:** `research/spread-points-nextgen-phase1`  
**Evaluation contract:** `research/spread-points-nextgen/phase1/EVALUATION_CONTRACT.md`

## Executive architecture map

Current LevLine is not one model. It is a set of distinct forecast surfaces:

1. **Independent football margin regression** -> `expected_margin`.
2. **Independent football total regression** -> `expected_total`.
3. **Independent score projection** -> `(expected_total ± expected_margin)/2`.
4. **Official winner probability** -> frozen `F-ST-01-FROZEN-2026` when a usable market probability exists.
5. **Public fair margin/spread** -> deterministic Normal bridge from the official winner probability and `margin_sigma`.
6. **Public displayed scores** -> probability-implied fair margin + independent expected total, not the independent expected margin.
7. **Market/ATS/over diagnostics** -> comparisons around the independent margin/total distributions.

These objects must not be evaluated or described as if they were one coherent fitted score model.

## 1. Raw-data to prediction trace

### Core data

`src/nfl_forecast/data.py`

- Schedules/results: nflverse `games.csv`.
- PBP: nflreadpy/nflverse, with a fail-closed fallback only for a not-yet-published newest-season PBP asset.
- Team stats: best effort.
- Advanced loaders: NGS passing, FTN charting, PFR passing, snap counts, depth charts; loader failure does not block the Core model.

The current score/winner feature builder does **not** consume those advanced bundle fields. Their presence in the bundle must not be confused with model use.

### Pregame Elo

`src/nfl_forecast/elo.py`

Sequential pregame Elo:

- initial = 1500;
- K = 20;
- home advantage = 45 Elo points;
- offseason regression = 0.33;
- margin-of-victory multiplier affects the rating update only after the game.

Each game row receives the ratings as they existed before that game result is applied.

### Team-game PBP aggregation

`src/nfl_forecast/features.py::aggregate_team_games`

Regular season only. Per team/game:

- offensive EPA/play;
- pass EPA;
- rush EPA;
- success rate;
- neutral-situation EPA for win probability between 0.05 and 0.95;
- offensive play count;
- defensive EPA/pass EPA/rush EPA/success allowed;
- defensive play count.

Play counts are aggregated but are **not** included in the current rolling feature list used by the score model.

### Leakage-shifted rolling state

`add_pregame_rolling()`

For each team, the following are shifted one completed game before rolling:

- offensive EPA;
- pass EPA;
- rush EPA;
- success rate;
- neutral EPA;
- defensive EPA allowed;
- defensive pass EPA allowed;
- defensive rush EPA allowed;
- defensive success allowed;
- win indicator.

For each field:

- EWMA with alpha 0.15;
- rolling mean over 3 games;
- rolling mean over 5 games;
- rolling mean over 8 games.

The team grouping is continuous across seasons; it does not reset at Week 1. That is point-in-time safe, but it means early-season state inherits prior-season games.

### Matchup features

`build_matchup_features()`

The feature scaffold is built before rolling so future games inherit the latest lagged state. Home-minus-away differences are constructed for all rolling fields.

Current Core score/winner features are:

- all `diff_*` rolling fields;
- home Elo;
- away Elo;
- Elo home probability;
- rest differential.

Current production-compatible research artifacts enumerate 44 such fields.

The direct score feature set does **not** include a sportsbook line, quarterback identity, injury designation, depth chart, player workload, weather, travel distance/time zone, coach identity, news, or a special-teams-specific feature.

## 2. Targets

`features.py`

- `home_win = 1(home_score > away_score)`;
- `margin = home_score - away_score`;
- `game_total = home_score + away_score`.

A tied NFL game is encoded as `home_win = 0` by this current target definition. Phase 1 separately reports a tie-excluded winner sensitivity.

## 3. Independent margin and total regressions

`src/nfl_forecast/models.py::fit_weighted_regression`

Each target uses four regressors:

- ElasticNet: median imputation, StandardScaler, alpha 0.08, l1_ratio 0.2;
- ExtraTreesRegressor: 500 trees, min leaf 6, max_features 0.75;
- XGBoost regressor: 450 trees, depth 3, learning rate 0.035, subsample 0.85, colsample_bytree 0.8, lambda 4.0, alpha 0.2;
- CatBoost regressor: 450 iterations, depth 5, learning rate 0.035, l2_leaf_reg 5, MAE loss.

For a 2026 run:

- OOF validation seasons = 2022–2025;
- each base OOF forecast is season-held-out using only earlier seasons;
- each base model's mean OOF MAE is computed across that block;
- inverse-MAE weights are then computed over the entire 2022–2025 OOF block;
- those same final weights are applied back to the combined OOF block to obtain the displayed validation MAE and residual sigma.

Accordingly, the base forecasts are season-held-out but the **final ensemble weighting is descriptive on the same OOF block**, not a fully nested chronology-clean model-selection estimate.

After validation, each regressor is fit on the full `historical` frame.

### Important 2026 refit boundary

`pipeline.run()` defines:

`historical = games[games["home_win"].notna()]`

without excluding the current season before fitting the ordinary Core stack, margin regression, or total regression. Therefore, as the 2026 season progresses:

- completed 2026 results can enter the final independent margin/total fits;
- completed 2026 results can enter the final legacy/core football base fits;
- 2026 does **not** enter the frozen F-ST training path, which is separately capped at 2025.

This is existing production behavior, not a Phase 1 modification.

## 4. Independent projected scores

`pipeline.projected_score()`

- home = (`expected_total + expected_margin`) / 2;
- away = (`expected_total - expected_margin`) / 2.

These floating-point independent scores are diagnostic forecast outputs. They are not the same scores ultimately presented by the public forecast contract.

## 5. Winner models and stacking semantics

### Ordinary Core/Sujar stack

`fit_season_stacked_classifier()`

Base classifiers:

- logistic regression;
- Extra Trees;
- XGBoost;
- CatBoost.

Each base OOF forecast is produced season-forward. However, the meta logistic regression is then:

1. fit on the combined OOF base predictions and their labels;
2. scored back on those same OOF rows to create `oof["stack"]`.

Therefore the displayed Core/Sujar `stack` OOF probability is **not fully nested at the meta layer**. It is suitable as a reproduction of current validation behavior, but should not be presented as a clean outer-holdout estimate.

This limitation does not redefine the separately audited frozen F-ST chronology.

### Frozen F-ST official winner

`src/nfl_forecast/fst_production.py`  
`src/nfl_forecast/fst_nested_pure.py`

The F-ST historical outcome cutoff is explicitly enforced at 2025.

When market probability is usable:

`logit(P_home) = intercept + b_market * logit(market) + b_pure * logit(frozen_nested_pure)`

Frozen artifact:

- ID: `F-ST-01-FROZEN-2026`;
- target season: 2026;
- training cutoff: 2025;
- frozen intercept/coefficients and training digest are identity-validated.

When market is unavailable/non-finite, `score_official_fst()` falls back to the exact legacy probability path. Because the legacy PURE base fit can include completed 2026 games, the **fallback path is not equivalent to a purely 2025-frozen football fit**, even though normal market-eligible F-ST scoring is frozen.

## 6. Historical market probability

`src/nfl_forecast/market.py`

American home/away moneylines are converted to raw implied probabilities and normalized pairwise to a no-vig `market_home_prob`.

Historical schedule market data are an opaque closing/late benchmark; bookmaker identity and exact horizon are not known from those rows.

`market_t120.py` is a separate research-only selector that uses append-only run history and chooses the latest valid market observation at or before kickoff minus 120 minutes.

## 7. Official public fair spread and public scores

`src/nfl_forecast/public_forecast.py`

The public fair margin is **not** `expected_margin`.

Under a Normal margin approximation:

`coherent_fair_margin_home = Phi^{-1}(official_home_win_probability) * margin_sigma`

and:

`coherent_fair_spread_home = -coherent_fair_margin_home`.

The public projected total remains `expected_total`.

Public raw team scores are then:

- home = (`expected_total + coherent_fair_margin_home`) / 2;
- away = (`expected_total - coherent_fair_margin_home`) / 2.

Whole-number displayed scores are rounded with an anti-tie rule so a non-50% official winner is not displayed as a tied projected score.

The independent margin and independently derived score pair are retained only in the public contract's `diagnostics` object.

## 8. Confidence and uncertainty

Independent regression uncertainty:

- `margin_sigma` = sample SD of the 2022–2025 descriptive weighted OOF residuals;
- `total_sigma` = analogous total residual SD;
- displayed 80% ranges use ±1.2815515655 sigma.

Cover/over probabilities assume Normal errors around the independent expected margin/total.

Confidence:

- official confidence is driven by the official F-ST probability;
- base-classifier disagreement can downgrade confidence;
- a sign split between official probability and independent margin can downgrade confidence;
- legacy confidence is retained only as a comparator.

## 9. Context-source classification

| Context | Current classification for score/margin/total | Current classification elsewhere |
|---|---|---|
| Lagged EPA/success | **Direct predictive feature** | — |
| Pass/rush splits | **Direct predictive feature** | — |
| Lagged team win form | **Direct predictive feature** | — |
| Elo/home field | **Direct predictive feature** | — |
| Rest differential | **Direct predictive feature** | — |
| Market moneyline | **Not in independent margin/total** | **Direct official F-ST winner input** |
| Market spread/total | **Not score features** | Diagnostic/ATS/OU comparison |
| QB identity/quality | Not in current score model | Research/explainability; prior challenger work |
| Injury/practice status | Not in current score model | Research/explainability |
| Personnel usage | Not in current score model | Explainability/research |
| NGS/PFR/FTN advanced player data | Loaded/probed but unused by current score features | Research/explainability |
| Depth charts | Unused by score model | Research-only source foundation |
| Weather | Unused by score model | Separate prospective research infrastructure |
| Travel/time zone | Unused by score model | No unified current score feature |
| Coaching | Unused by score model | Context only where surfaced |
| News/media | Unused by numeric score model | Editorial/context layer |
| Special teams | No dedicated direct feature | Indirectly reflected only through historical score/strength outcomes |
| Public probability-implied spread | Not a trained score target | Official public/market-facing presentation |
| Independent `expected_margin` | Trained football regression | Diagnostic / ATS comparison |
| Independent `expected_total` | Trained football regression | Also feeds public projected total |

## 10. Configuration-versus-implementation observations

`config/model.yaml` exposes:

- rolling windows [3,5,8];
- EWMA alpha 0.15;
- `min_games_for_team_form: 2`;
- `early_season_prior_games: 8`;
- `calibrate: true`.

The inspected current feature path calls `add_pregame_rolling()` through its defaults rather than passing the configured windows/alpha. The defaults currently match the YAML, so behavior is aligned today, but the values are not dynamically wired through that call.

The inspected Core stack path does not consume the `calibrate` flag as an explicit probability-calibration layer. The ordinary meta logistic stack itself is the final Core probability transform.

## 11. Production/publication boundary

`scripts/run_week.py`:

- runs `pipeline.run()`;
- writes forecast outputs;
- publishes accountability/calibration/confidence/editorial feeds.

Advanced player context and injury/personnel enrichment are separate scripts/modules and do not silently feed the numerical score model.

`publish.py` preserves immutable official pregame locks and appends grading after results. Ties are currently treated as a home non-win by the core target and, in the lock grader, an `actual_margin <= 0` game resolves the winner label to away. Phase 1 records this semantic edge case but does not alter production grading.

## 12. External comparator requested during Phase 1

The public college-football projection page at davidsasser.com exposes:

- projected team scores;
- a projected line;
- opening market line;
- current market line;
- model ATS pick;
- straight-up and ATS tracking.

This is a useful product-architecture comparator because it visibly separates score generation from market comparison. Its public page does not disclose enough model/data/chronology detail to use its performance record as reproducible scientific evidence for LevLine. Deeper methodology review belongs to Phase 2, not Phase 1.

## Audit conclusion

Current LevLine's central scoring limitation is architectural clarity, not merely one error number:

- independent margin and total are compressed football-only regressions;
- the official winner is a distinct market-conditioned frozen F-ST;
- public fair spread is a probability bridge, not the independent regression;
- public scores combine the bridged margin with the independent total;
- important player/weather/personnel context exists in the repository but does not enter the current score regressions;
- ordinary regression weights and the ordinary stack meta layer have less rigorous validation semantics than the frozen F-ST research path.

Phase 1 evaluates each surface under the canonical contract rather than collapsing them into a single “LevLine model.”
