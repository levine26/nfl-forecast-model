# LevLine Post-Week-4 Model Improvement — Phases 1–2 Findings

**Status:** COMPLETE for chat scope — forensic diagnosis + external research + hypothesis synthesis  
**Production changes:** NONE  
**Incumbent preserved:** `F-ST-01-FROZEN-2026`  
**Outcome firewall:** completed 2026 outcomes were used only for diagnosis/hypothesis generation, never to fit/tune/select a candidate.

## Executive conclusion

The evidence does **not** support a global increase in PURE/football weight.

The strongest direction is a **market-prior architecture with sparse, chronologically trained football residual corrections**. The correction should be able to use component topology, independent expected-margin information, explicit structural state (especially QB/player changes), and market-quality state. It should be deliberately low-dimensional and heavily shrunk toward the market.

The second major finding is architectural rather than statistical: the live football feature path carries rolling EPA state continuously across the offseason, while the configuration fields intended to govern rolling windows / EWMA / minimum form / early-season prior are not wired into the feature builder. This is not a leakage bug, but it means early-season adaptation is an implicit consequence of fixed rolling mechanics rather than an explicit, roster-aware prior/state-transition design.

## Phase 1 — Forensic diagnosis

### 1. F-ST is operating as designed

Existing audit evidence remains authoritative:

- frozen F-ST historical reconstruction: 740/1087 = 68.08%;
- chronology-clean F-ST architecture: 741/1087 = 68.17%;
- market: 735/1087 = 67.62%;
- historical F-ST/market side disagreements are rare and concentrated near the 50/50 boundary;
- 2026 Weeks 3–4 slump was statistically notable but showed no production corruption, fallback event, artifact swap, or retraining fault.

This program therefore treats F-ST as a sound incumbent whose **conditional correction mechanism may be improvable**, not a broken implementation.

### 2. Unconditional football overrides are historically wrong

On the frozen 2022–2025 OOS universe:

- market: 735/1087 = 67.62%;
- aggregate PURE: 701/1087 = 64.49%;
- PURE/market disagreements: 178;
- PURE won only 72/178 = 40.45% of those switches.

By market-favorite strength, unconditional football disagreement became worse, not better, for clear favorites.

By PURE-market disagreement magnitude:

| Absolute PURE-market gap | Disagreements | PURE wins | Market wins | PURE switch rate |
|---|---:|---:|---:|---:|
| <5 pp | 20 | 10 | 10 | 50.0% |
| 5–10 pp | 40 | 15 | 25 | 37.5% |
| 10–15 pp | 54 | 24 | 30 | 44.4% |
| >=15 pp | 64 | 23 | 41 | 35.9% |

**Conclusion:** large football disagreement is not evidence that football should receive more weight.

### 3. Component topology contains some information, but not a simple consensus rule

Historical individual component performance versus market:

| Model | Accuracy | Market disagreements | Switch win rate vs market |
|---|---:|---:|---:|
| Logistic | 63.66% | 167 | 37.1% |
| Extra Trees | 63.66% | 193 | 38.9% |
| XGBoost | 61.18% | 222 | 34.2% |
| CatBoost | 62.83% | 200 | 37.0% |
| Market | 67.62% | — | — |

The previously tested component-resolved stack reached 744/1087 = 68.45%, +3 correct vs chronology-clean F-ST, but its gain was not season-stable: the net edge was +4 in 2022, 0 in 2023, -1 in 2024, 0 in 2025.

Unanimous football opposition to the market was actively weak:

- 96 games where all four components opposed market;
- football side correct 38/96 = 39.6%;
- market side correct 58/96 = 60.4%.

When the two tree models (XGBoost + CatBoost) agreed with each other and opposed a consensus of Logistic + Extra Trees, there were only 27 games:

- tree side correct: 10;
- linear/Extra-Trees side correct: 17;
- market correct: 17.

**Conclusion:** component identity/topology may be useful as inputs to a regularized residual model, but no component family or unanimity rule earns override authority.

### 4. Early-season football is not uniformly better or worse

Historical 2022–2025 slices:

- Weeks 1–4: market 63.28%, PURE 63.67%, frozen-coefficient F-ST 64.06%;
- Weeks 1–6: market 64.25%, PURE 62.10%, F-ST 64.78%;
- Week 7+: market 69.37%, PURE 65.73%, F-ST 69.79%.

Individual weeks vary sharply; e.g. PURE beat market in historical Weeks 2–3 but lost in Week 4 and several later weeks.

**Conclusion:** “trust football more early” is not a valid candidate. Early-season adaptation requires a structural state model, not a week-number switch.

### 5. Important feature-state implementation finding

Current `src/nfl_forecast/features.py`:

- creates pregame EWMA with `alpha=0.15`;
- creates rolling windows of 3, 5, and 8;
- groups by team, **not team-season**, so rolling state crosses the offseason;
- shifts one game correctly, so same-game leakage is prevented;
- does not explicitly regress team EPA state toward league average at the season boundary;
- does not explicitly reweight for coaching/roster/QB turnover at the season boundary.

With EWMA alpha 0.15, the carryover weight on the prior end-of-season state is approximately:

- after 1 new game: 85.0%;
- after 2: 72.3%;
- after 3: 61.4%;
- after 4: 52.2%;
- after 5: 44.4%;
- after 6: 37.7%.

The rolling-8 feature entering Week 4 still contains five prior-season games.

Also, repository search finds no live code use of these config keys:

- `features.rolling_windows`
- `features.ewma_alpha`
- `features.min_games_for_team_form`
- `features.early_season_prior_games`

The feature builder currently uses its function defaults instead.

**Interpretation:** this is not evidence that the current model is wrong, and it must not be “fixed” from the 2026 slump. It is, however, a strong Phase 3 candidate mechanism: make early-season carryover explicit, shrinkable, and structurally aware, then test it chronologically.

### 6. Opponent adjustment and QB features are unstable alone

Existing season-forward PURE feature-set ablations:

| Season | Production-compatible | Opp-adjusted | QB-aware | Opp-adjusted + QB |
|---|---:|---:|---:|---:|
| 2022 | 64.21% | 64.94% | 63.84% | 64.94% |
| 2023 | 63.24% | 62.50% | 61.40% | 62.87% |
| 2024 | 67.28% | 68.01% | 69.85% | 70.22% |
| 2025 | 63.24% | 61.76% | 61.76% | 62.50% |

The combined opponent-adjusted/QB feature family can help in a favorable season but is not consistently better.

**Conclusion:** QB/opponent adjustment should be treated as structural state inputs or residual channels, not assumed globally superior.

### 7. Generic dynamic-strength adaptation has already failed

Prior LevLine 4 test:

- standalone dynamic Elo: 664/1087;
- F-ST + dynamic Elo: 739/1087;
- incumbent F-ST: 741/1087;
- switches vs F-ST: 12, challenger went 5–7.

**Rejected:** generic dynamic Elo residual.

### 8. Naive adaptive refitting has already failed

Prior adaptive research found:

- naive weekly refit: 739/1087 = 67.99%;
- frozen F-ST: 741/1087 = 68.17%.

Candidate 1 adaptive residual state also failed full-sample despite looking good on one season.

**Rejected:** ordinary weekly coefficient refitting as the main solution.

### 9. Market path alone has not established incremental winner information

Candidate 3 historical 2025 market-path innovation:

- F-ST: 179/272;
- candidate: 180/272;
- only 3 winner switches, 2–1;
- Brier/log loss worsened;
- a level-only control reproduced the same +1 net winner gain.

**Conclusion:** later market **level** is valuable; path shape must prove incremental value conditional on same-horizon level.

### 10. Margin/winner relationship deserves a new, correctly oriented test

Known historical evidence:

- the production margin model is competitive with the market spread on MAE;
- standalone large model-vs-market margin disagreement was previously rejected as a generic upset corroborator;
- a previous *probability-to-margin* bridge failed qualification and must not be recycled.

Fresh 2026 diagnostic on the official 63 locked games shows no broad margin supremacy overall, but an interesting error pattern:

- all games: model margin MAE ~9.62, market spread MAE ~9.61;
- among the 24 games where F-ST selected the wrong winner:
  - model margin MAE ~11.21;
  - market spread MAE ~12.60;
  - model margin was closer than market in 16/24 = 66.7%.

This is **hypothesis-generating only**. It does not prove that margin direction should override F-ST.

The correct Phase 3 question is the reverse of the failed prior bridge:

> Can a chronology-clean expected-margin distribution produce an independent home-win probability that adds residual binary winner information beyond the moneyline market and F-ST?

That has not yet been answered by the existing probability-to-margin bridge.

### 11. Output-level 2026 drift is modest, not a regime-break signature

Using the frozen 2022–2025 OOS universe as reference and the 63 official 2026 locks:

| Output | Standardized mean shift | PSI (decile) | 2022–25 mean | 2026 mean |
|---|---:|---:|---:|---:|
| Market home probability | +0.11 SD | 0.108 | 0.547 | 0.568 |
| Nested PURE probability | +0.15 SD | 0.092 | 0.530 | 0.551 |
| Component dispersion | -0.20 SD | 0.099 | 0.0381 | 0.0344 |
| Component mean probability | +0.09 SD | 0.151 | 0.555 | 0.572 |
| abs(PURE-market) | -0.09 SD | 0.150 | 0.0776 | 0.0722 |

These diagnostics show mild/moderate distribution movement but no obvious wholesale output shift.

**Important limitation:** this is an **output drift audit**, not a full raw-feature drift audit. The repository does not currently commit a directly comparable full historical feature matrix for all frozen/live raw features. A Phase 3 infrastructure task should persist a chronology-safe feature snapshot specifically for PSI/Wasserstein/quantile drift.

### 12. Confidence should be separated from pick identity

The Week 3–4 collapse was concentrated in lower-actionability buckets while High remained strong. Existing selective-prediction literature provides a principled framework for separating prediction from coverage/actionability.

Research implication:

- preserve an official most-likely winner for accountability if desired;
- separately define actionability/coverage;
- do not let presentation abstention silently change the winner model;
- evaluate risk-versus-coverage on chronologically held-out data.

## Phase 2 — External research synthesis

### A. Forecast combination and dynamic weighting

Relevant literature:

1. McAlinn & West (2019), *Dynamic Bayesian Predictive Synthesis in Time Series Forecasting*, Journal of Econometrics.  
   DOI: 10.1016/j.jeconom.2018.11.010  
   Key relevance: dynamic combination can adapt to time-varying bias, miscalibration, and dependence among forecasters.

2. Li, Kang & Li (2023), *Bayesian forecast combination using time-varying features*, International Journal of Forecasting.  
   DOI: 10.1016/j.ijforecast.2022.06.002  
   Key relevance: forecast weights can depend on observable state features rather than being globally fixed.

3. Tian & Anderson (2014), *Forecast combinations under structural break uncertainty*, International Journal of Forecasting.  
   DOI: 10.1016/j.ijforecast.2013.06.003  
   Key relevance: combine across plausible state/estimation windows instead of hard-selecting an uncertain break date.

4. Sun, Chen & Gao (2026), *Model averaging for time-varying vector autoregressions*, Journal of Econometrics.  
   DOI: 10.1016/j.jeconom.2026.106308  
   Key relevance: time-varying weights can improve forecasting under structural shifts when regularized.

5. Clements & Harvey (2011), *Combining probability forecasts*, International Journal of Forecasting.  
   DOI: 10.1016/j.ijforecast.2009.12.016  
   Key relevance: no single combination form is optimal across plausible DGPs; encompassing conclusions depend on combination form.

**LevLine implication:** conditional weighting is scientifically plausible, but the NFL sample is too small for a flexible neural gating network. Use a low-dimensional regularized gate or residual model.

### B. Forecast diversity and dependence

Relevant literature:

- Batchelor & Dua (1995), *Forecaster Diversity and the Benefits of Combining Forecasts*, Management Science. DOI: 10.1287/mnsc.41.1.68.
- Lichtendahl & Winkler (2020), *Why do some combinations perform better than others?*, International Journal of Forecasting. DOI: 10.1016/j.ijforecast.2019.03.027.
- Lee & Seregina (2026), *Combining forecasts under structural breaks using Graphical LASSO*, International Journal of Forecasting. DOI: 10.1016/j.ijforecast.2025.04.003.

**LevLine implication:** the four football models are highly related and should not be treated as four independent votes. Component residual covariance/diversity may be useful, but multiple transforms of the same football signal do not create multiple independent evidence channels.

### C. Betting-market efficiency

Relevant NFL evidence:

- Cain, Law & Peel (2000), *Testing for statistical and market efficiency when forecast errors are non-normal: the NFL betting market revisited*, Journal of Forecasting. DOI: 10.1002/1099-131X(200012)19:7<575::AID-FOR765>3.0.CO;2-U.
- Miller & Rapach (2013), *An intra-week efficiency analysis of bookie-quoted NFL betting lines in NYC*, Journal of Empirical Finance. DOI: 10.1016/j.jempfin.2013.07.002.
- Krieger & Shank (2026), *Do Sportsbooks Accurately Price Money Line Odds?*, Journal of Prediction Markets. DOI: 10.5750/jpm.v19i2.2325.
- Simon (2024), *Inefficient Forecasts at the Sportsbook: An Analysis of Real-Time Betting Line Movement*, Management Science. DOI: 10.1287/mnsc.2022.00456.

**LevLine implication:** market is an extremely strong prior and later information usually improves it, but it is not a mathematical oracle. The target should be conditional residual information, not generic anti-market prediction.

### D. Margin-to-win modeling

Relevant literature:

- Stern (1991), *On the Probability of Winning a Football Game*, The American Statistician. DOI: 10.1080/00031305.1991.10475798.
- Huggins, Bailey & Guardiola (2020), *Converting NFL Point Spreads into Probabilities*, INFORMS Transactions on Education. DOI: 10.1287/ited.2019.0230ca.
- Cain et al. (2000), above.
- *Forecasting exact scores in National Football League games* (2013), International Journal of Forecasting.

Stern's classic result supports mapping an expected margin through a residual distribution to a win probability. Modern implementations should not assume a fixed normal sigma without OOS validation.

A current open-source NFL model (`Damepivot/nfl-game-model`) independently reports that a regularized margin-first model with opponent-adjusted EPA, QB form, and smooth prior-season blending beat its direct winner classifier on its own held-out design. This is not peer-reviewed LevLine evidence, but it is a useful reproducible engineering hypothesis.

**LevLine implication:** test an independently trained margin-derived winner probability, not the already-rejected inverse probability-to-margin presentation bridge.

### E. Player-state models

Holmes & McHale (2024), *Forecasting football match results using a player rating based model*, International Journal of Forecasting. DOI: 10.1016/j.ijforecast.2023.03.002.

The work supports the general principle that player-level state can capture dynamic team strength more directly than aggregate team form.

**LevLine implication:** QB/OL/secondary state has a stronger causal story than generic week-based reweighting, but point-in-time data provenance is the binding constraint. The existing Candidate 2 QB-shock result remains only one switch and is not validation.

### F. Selective prediction / confidence

- Geifman & El-Yaniv (2019), *SelectiveNet*, ICML/PMLR 97.
- Gangrade, Kag & Saligrama (2021), *Selective Classification via One-Sided Prediction*, AISTATS/PMLR 130.

**LevLine implication:** confidence/actionability can be modeled as a separate risk-coverage decision without changing the official pick. This is primarily a product layer unless a separately trained gate is shown to improve winner decisions.

## Ranked mechanisms

### Tier 1 — strongest immediate historical candidates

1. **Market-prior component residual stack**
   - strong rationale: existing component-resolved stack already produced the best historical point estimate among nearby architectures;
   - improvement must come from regularization and better use of residual structure, not component majority voting.

2. **Expected-margin-derived winner residual**
   - strong rationale: margin engine remains independently useful and is not fully represented in F-ST;
   - prior failed bridge tested the opposite mapping.

3. **Explicit early-season hierarchical state**
   - strong rationale: current cross-offseason rolling is implicit, fixed, and not roster/state aware;
   - can be tested entirely on pre-2026 seasons.

### Tier 2 — strong theory but data-limited

4. **Robust same-horizon market-quality prior**
   - multi-book consensus, freshness, dispersion, moneyline/spread consistency;
   - likely valuable as a better prior;
   - full multi-season PIT archive may not exist.

5. **QB/player structural-shock residual**
   - causally coherent and orthogonal;
   - historical PIT coverage is limited, so likely requires prospective shadow evidence.

### Tier 3 — lower-priority / high-overfit risk

6. **Dynamic online expert aggregation**
   - theoretically sound, but prior LevLine weekly adaptation was weak and NFL effective sample size is small.

7. **High-capacity neural mixture-of-experts**
   - rejected for Phase 3 unless a much larger compatible historical corpus is constructed; current sample does not justify the capacity.

## Phase 3 candidate slate — freeze before testing

### Candidate A — MKT-COMP-RESIDUAL-V1

**Hypothesis:** individual football component residuals contain small incremental information that aggregate PURE discards.

**Architecture:** market-logit offset + regularized logistic residual using:
- component logits minus market logit for Logistic / Extra Trees / XGBoost / CatBoost;
- component mean;
- component dispersion/range;
- market distance from 0.5.

No team identity. No thresholds selected from outcomes.

**Training:** season-forward regularized logistic; penalty fixed from an earlier development window or nested pre-target chronology.

**Expected uplift vs F-ST:** +0.2 to +0.6 pp.

**Research probability of beating F-ST:** ~55%.

**Failure mode:** reproduces 2022-only component-stack gain and is neutral/negative thereafter.

**Immediate testability:** YES.

### Candidate B — MARGIN-RESIDUAL-WIN-V1

**Hypothesis:** chronology-clean expected margin contains independent winner information not fully captured by moneyline/F-ST.

**Architecture:**
1. train margin model strictly chronologically;
2. estimate pre-target residual distribution using training-only games;
3. convert expected margin to `P(home win)` by empirical/parametric residual CDF;
4. combine market logit + margin-derived logit through a regularized residual model.

Primary ablations:
- margin probability alone;
- market alone;
- F-ST;
- market + margin;
- F-ST + margin residual.

**Expected uplift:** +0.2 to +0.7 pp.

**Research probability of beating F-ST:** ~50–55%.

**Failure mode:** margin signal is already subsumed by market, or probability conversion is unstable near zero.

**Immediate testability:** YES if chronology-clean margin OOF is regenerated from historical source data.

### Candidate C — EARLY-STATE-SHRINKAGE-V1

**Hypothesis:** explicit season-boundary shrinkage and state-transition logic improves Weeks 1–6 without harming later games.

**Architecture:** replace implicit offseason carryover in a research-only feature path with:
- prior-season team/unit state regressed toward league mean;
- smooth sample-size update `w=n/(n+k)` or Bayesian equivalent;
- separate offensive/defensive carryover rates;
- QB continuity/starter state;
- opponent adjustment activated/shrunk according to evidence depth rather than globally;
- no week-specific outcome-tuned weights.

**Training:** choose hyperparameter policy on seasons before the OOS target; test 2022–2025 season-forward.

**Expected uplift overall:** +0.2 to +0.7 pp, with most effect early season.

**Research probability of beating F-ST:** ~50%.

**Failure mode:** market already handles offseason turnover better; added state model only increases variance.

**Immediate testability:** YES, but requires feature rebuild.

### Candidate D — CONSTRAINED-GATE-V1

**Hypothesis:** market/football reliability varies with observable pregame state, but the relationship is simple enough for a low-dimensional gate.

**Architecture:** two-expert mixture:
- expert 1 = market prior;
- expert 2 = football residual candidate (prefer Candidate A or a frozen PURE variant);
- gate uses only a small preregistered set: market boundary distance, component dispersion, component-market residual magnitude, early-season state uncertainty, margin corroboration.

Gate must be regularized and shrink strongly toward market. No neural net.

**Expected uplift:** +0.3 to +0.8 pp if a real conditional regime exists.

**Research probability of beating F-ST:** ~45–55%.

**Failure mode:** gate learns noise because switch events are sparse.

**Immediate testability:** YES after A/B/C inputs are defined; should not be the first experiment.

### Candidate E — MARKET-QUALITY-PRIOR-V1

**Hypothesis:** a better same-horizon market prior improves both baseline probability and the residual architecture.

**Architecture:**
- robust multi-book median-logit / trimmed consensus;
- bookmaker freshness;
- dispersion and stale-book flags;
- spread-moneyline consistency;
- market level always included; path variables tested only conditional on level.

**Expected uplift:** +0.1 to +0.5 pp.

**Research probability of beating current market/F-ST:** ~50%, but uncertainty is high.

**Failure mode:** consensus differences are too small, or historical PIT coverage is inadequate.

**Immediate testability:** PARTIAL; broad proof likely requires prospective data.

### Candidate F — PLAYER-STATE-EVENT-V1

**Hypothesis:** discrete structural changes, especially QB starter/replacement state and major OL/secondary changes, contain residual information before the market fully digests them.

**Architecture:** event-driven residual correction over market/F-ST, not an always-on player model.

**Inputs:** only timestamp-qualified point-in-time events and pre-event baseline state.

**Expected uplift overall:** +0.1 to +0.4 pp; conditional effect could be larger on rare events.

**Research probability of beating F-ST:** ~40–50% because events are sparse.

**Failure mode:** market incorporates the event immediately; insufficient PIT history.

**Immediate testability:** LIMITED; requires prospective shadow or qualified historical archive.

## Explicit rejected ideas

Do not revive without a genuinely new preregistration:

- globally increase PURE weight;
- fixed 75/25 or similar PURE-heavy blend;
- unconditional PURE override;
- component unanimity override;
- XGBoost override because of 2026 Weeks 3–4;
- generic large-margin-disagreement override;
- generic super-team/favorite fade;
- generic dynamic Elo residual;
- ordinary weekly F-ST coefficient refit;
- Candidate 3 path-only update;
- team-specific ATL/NO patch;
- week-number-only early-season switch;
- high-capacity neural gate on the 1,087-game OOS universe.

## Unresolved questions / data requirements

1. Persist a full chronology-safe historical feature snapshot for raw-feature drift audit.
2. Regenerate and persist chronology-clean expected-margin OOF predictions for 2022–2025.
3. Audit offseason carryover semantics by feature family; quantify how much each rolling window/EWMA is prior-season vs current-season in Weeks 1–8.
4. Determine whether old config feature controls are dead by design or stale configuration debt; do not change production during research.
5. Determine availability of multi-season same-horizon multi-book moneyline/spread snapshots.
6. Continue prospective QB/player-state capture; do not reconstruct unavailable PIT states.
7. For all switch/gate candidates, report switch count and effective sample size explicitly; overall 1,087 games exaggerates information when only ~20–50 games can change the official winner.

## Exact Phase 3 handoff

A new chat should:

1. read this file and `LEVLINE_POST_WEEK4_MODEL_IMPROVEMENT_PLAN.md`;
2. create preregistrations for Candidates A, B, and C **before** viewing their candidate test outcomes;
3. build common chronological evaluation infrastructure once;
4. execute A first, B second, C third;
5. only design Candidate D after A/B/C identities are frozen, so the gate cannot cherry-pick whichever base candidate wins;
6. keep E/F as separate PIT/prospective programs if historical data is insufficient;
7. use 2026 outcomes only for the already-existing prospective contracts, never for Phase 3 candidate selection;
8. leave production untouched until explicit final user authorization.

## Bottom-line recommendation

The highest-value next test is **not “more PURE.”** It is:

> market prior + small, regularized, independently interpretable football residual channels, with an explicit test of margin-derived winner information and an explicit rebuild of early-season state handling.

That path best matches the historical LevLine evidence, the current failure mode, and the external forecast-combination literature while minimizing the risk of fitting two bad weeks.


## Phase 1–2 closure addendum — coefficient interpretation, drift caution, and source verification

### Frozen negative PURE coefficient is a conditional/suppressor coefficient, not a verdict against football

On the 1,087-game 2022–2025 frozen-fit frame, market and nested-PURE forecasts are strongly collinear:

- probability correlation: **0.841**;
- logit correlation: **0.838**.

Descriptively, large PURE deviations from market are mean-reverting on this same frame. For example, when PURE is at least 10 percentage points more home-favorable than market, mean market home probability is ~34.8%, mean PURE home probability ~50.3%, and realized home win rate ~34.2%. When PURE is at least 10 points less home-favorable than market, mean market home probability is ~69.2%, mean PURE ~54.0%, and realized home win rate ~74.2%.

Because this is the same historical frame from which the frozen relationship was learned, it is **explanatory, not independent validation**. The correct interpretation is that the negative PURE coefficient can be statistically coherent after conditioning on a highly correlated market signal. Phase 3 must not force football coefficients positive; it should test **football residuals relative to market** under chronological validation.

### Drift metric caution

The output-drift section is diagnostic only. In particular, **PSI values from a 63–64 game live sample must not be compared mechanically with universal cutoffs such as 0.1/0.25**. Recent methodological work shows PSI thresholds depend materially on sample size. For Phase 3 governance, standardized shifts, Wasserstein distance, quantiles, and direct distribution plots should accompany any PSI calculation; raw-feature drift claims require a persisted PIT feature snapshot.

### Current persisted history versus audit population

The current `outputs/prediction_history.csv` contains **64 completed rows** through ATL–NO, including two early `0.4.0-accountability` rows before the `0.9.0-fst` path. Those 64 rows grade 40–24 as stored; the 62 rows explicitly tagged `0.9.0-fst` grade 39–23. The formal Week-4 audit used its immutable-lock accountability population and reported **39–24 on 63 locks**. These population definitions must not be silently mixed.

Accordingly, the fresh 2026 margin-error slice in this file remains **hypothesis-generating only** and is not candidate-selection evidence. Phase 3 historical candidate selection must use the frozen 2022–2025 chronological universe; prospective 2026 grading must use the predeclared contract population.

### External open-source margin/early-state hypothesis verified

The public `Damepivot/nfl-game-model` repository was inspected directly. Its README documents:

- a write-once 2023–2025 holdout;
- opponent-adjusted EPA ratings with ridge shrinkage;
- smooth prior-season/current-season blending `n/(n+6)`;
- separate offensive/defensive carryover behavior;
- quarterback rolling form;
- margin-first probability mapping `Phi(margin/sigma)`;
- a reported direct classifier challenger that lost on both accuracy and Brier score.

Its reported holdout win accuracy is **65.3%**, well below LevLine's incumbent benchmark, so it is **not evidence that the external model is superior**. It is useful only as independent support for two Phase 3 mechanisms already justified internally: explicit early-season shrinkage and testing a chronology-clean margin-derived win-probability channel.

### Final Phase 1–2 scientific judgment

The central mechanism is now frozen for Phase 3 design:

> **Treat the market as the prior/offset; preserve football information as residual structure; make state-dependent corrections only through low-capacity, chronology-valid mechanisms with explicit ablations.**

The first three candidates to preregister are:
1. `MKT-COMP-RESIDUAL-V1`;
2. `MARGIN-RESIDUAL-WIN-V1`;
3. `EARLY-STATE-SHRINKAGE-V1`.

`CONSTRAINED-GATE-V1` must be designed only after A/B/C identities are frozen. Market-quality and player-state candidates remain separate PIT/prospective lanes where historical source coverage is inadequate.
