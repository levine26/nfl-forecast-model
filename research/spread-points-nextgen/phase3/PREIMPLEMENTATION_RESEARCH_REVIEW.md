# Phase 3 — Preimplementation Research Review

**Program:** LevLine Spread & Points Next-Generation Research Program  
**Phase:** 3 — Controlled Challenger Implementation  
**Research gate timestamp:** 2026-09-22 America/Los_Angeles  
**Development outputs inspected before this review:** **NONE**  
**2025 challenger outputs inspected:** **NONE**  
**Completed-2026 outcomes used:** **NONE**  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged

## Purpose

This is the bounded **pre-implementation research delta** required before A0/B0/C0 development results exist. It supplements Phase 2; it does not reopen Phase 1 or redo the Phase 2 literature review.

The question is deliberately narrow: does credible new evidence justify changing the already frozen A0/B0/C0 implementation before the first development metric is emitted?

## Evidence tiers

- **Tier 1** — peer-reviewed forecasting research with defensible evaluation.
- **Tier 2** — strong technical/preprint research with reproducible methodology.
- **Tier 3** — reproducible open-source implementation.
- **Tier 4** — practitioner/industry methodology with meaningful disclosure.
- **Tier 5** — opaque performance claim, anecdote, or marketing.

Tier 5 performance claims do not override stronger evidence.

---

## 1. Machine Learning Model for NFL Betting — Model 5.0

**Source:** https://medium.com/@bravenewworld21/machine-learning-model-for-nfl-betting-model-5-0-8e916428c330  
**Evidence tier:** 4 for disclosed workflow/features; 5 for headline performance claims.  
**Target:** betting-side / cover classification and related game prediction.  
**Architecture:** multiple regression/classification learners, including logistic-regression-style models and XGBoost, following a broad model-comparison workflow.  
**Inputs:** team metrics, Elo, QB Elo, stadium/context, referee information, time/date fields, market fields, and other engineered variables.  
**Market use:** sportsbook/betting variables are part of the modeling environment.  
**Validation method:** published code uses `train_test_split(..., test_size=0.2, random_state=1234)` and explicitly describes random shuffling rather than a forward temporal split.  
**Chronology:** **not acceptable for LevLine confirmatory evidence**. Randomly shuffled NFL games allow later football environments to inform evaluation of earlier games.  
**Reproducibility:** partial; enough implementation detail exists to audit important methodological choices, but the full historical data/timestamp contract is not equivalent to a PIT-safe LevLine dataset.  
**Leakage / researcher-degree risks:** non-temporal split; broad model comparison; repeated feature selection; repeated hyperparameter selection; unclear market-horizon semantics; potential use of state that is only known late in the week; threshold/model-selection multiplicity.  
**Useful idea:** Elo/QB context, stadium/referee/context features can be legitimate hypotheses when PIT history exists. XGBoost is a useful exploratory comparator in unconstrained research.  
**Negative evidence:** the validation design is exactly the type of random-split performance inflation Phase 3 prohibits. Useful features cannot validate the claimed edge.  
**Applicability to A0/B0/C0:** no amendment. Elo/QB/personnel/referee additions would expand the frozen schema and QB/personnel lacks the required multi-season PIT contract.  
**Applicability to future Candidate 5:** possibly as a source of future feature hypotheses only, never as validation evidence.  
**Disposition:** **FEATURE-BRAINSTORMING ONLY; PERFORMANCE CLAIMS REJECTED AS PHASE-3 EVIDENCE.**

---

## 2. nfelo

**Sources:**  
- https://www.nfeloapp.com/games/nfl-model-performance/  
- https://www.nfeloapp.com/analysis/weighted-EPA-methodology-and-performance/  
- https://www.nfeloapp.com/analysis/using-market-regression-to-improve-prediction-accuracy-in-the-nfl/  
- https://www.nfeloapp.com/analysis/margin-probabilities-from-nfl-spreads  
- https://www.nfeloapp.com/about/  

**Evidence tier:** 3–4 for public/open methodology and code-linked architecture; public performance board is practitioner evidence, not a LevLine-equivalent confirmatory test.  
**Target:** NFL margin/side prediction, ratings, win/spread probability and market-relative prediction.  
**Architecture:** modified Elo + efficiency/EPA information + contextual adjustments + explicit regression/reconciliation toward sportsbook markets. Separate work models margin distributions and key-number behavior.  
**Inputs:** Elo-like dynamic team rating, EPA/WEPA, HFA/rest, QB adjustments, market line, context.  
**Market use:** explicit. The central transferable design is **independent football opinion -> explicit market reconciliation**, rather than pretending market information is football-only signal.  
**Validation / chronology:** nfelo's WEPA write-up is unusually valuable negative evidence: the author explicitly documents that an earlier WEPA version overfit and used forward-looking data, then reworked the method to use backward-looking evaluation. The market-regression article demonstrates the conceptual benefit of shrinking an independent football model toward a strong market prior, but its published coefficients/optimization are not copied here.  
**Reported performance:** public pages report competitive historical performance. These are not imported as LevLine scientific truth because the full forecast/market/PIT ledger is not reconstructed in this program.  
**Reproducibility:** meaningful public disclosure and open-source ecosystem; still not identical to the Phase 3 frozen evidence contract.  
**Leakage risks:** the historical WEPA post itself documents a prior forward-looking optimization failure; this is a reason to preserve strict chronology, not a reason to weaken it.  
**Useful idea:** dynamic ratings; backward-only efficiency states; explicit market shrinkage; treating key-number margin distributions separately from point estimates.  
**Negative evidence:** sophisticated football models can still be worse than the market alone; added features can overfit; prior published WEPA feature weighting required correction after forward-looking contamination was recognized.  
**Applicability to A0:** supports dynamic/shrunk opponent-adjusted state already frozen.  
**Applicability to B0:** only general support for EPA/process information; no reason to alter the bounded possession/drive design.  
**Applicability to C0:** strongly supports the already frozen market-residual architecture and M0/M1/M2/M3 null hierarchy.  
**Applicability to future Candidate 5:** conceptual support for combining independent model opinions while preserving a strong anchor; coefficients and switching logic must be learned under Candidate 5's own chronology.  
**Disposition:** **SUPPORTS CURRENT CONTRACT; NO COEFFICIENT OR FEATURE COPYING.**

---

## 3. Quinnipiac NFL Total Score / Point Spread Project

**Source:** https://www.qu.edu/academics/experiential-learning/course-projects-and-capstones/student-projects/predicting-nfl-total-score-and-point-spread-bets/  
**Evidence tier:** 4.  
**Target:** total score and point spread; betting decisions derived from model-vs-line disagreement.  
**Architecture:** linear regression, gradient boosting and feed-forward neural networks across all-feature / forward-selected / lasso-selected inputs.  
**Inputs:** 1,560 games from 2018–2023, PFF game information, pregame player projections, sportsbook lines, stadium and weather.  
**Market use:** direct sportsbook comparison and thresholded betting decisions.  
**Validation:** K-fold cross-validation is described, but the public summary does not establish season-blocked/rolling chronology. Multiple feature-selection schemes, three learner families and betting thresholds are compared.  
**Chronology:** **insufficiently documented for confirmatory use**. Random/mixed-season K-fold would be invalid for LevLine's time-dependent target.  
**Reproducibility:** project methodology is described, but full PIT source snapshots and a deterministic end-to-end code/data archive were not established from the public page.  
**Leakage risks:** possible mixed-season K-fold; player projections/weather require precise as-of timestamps; repeated learner/feature/threshold comparisons create selection multiplicity.  
**Useful idea:** player projections and forecast-time weather can be plausible scoring inputs if exact PIT history exists.  
**Negative evidence:** an apparently sophisticated learner tournament does not establish sportsbook-beating ability without temporal validation and untouched threshold evaluation.  
**Applicability to A0/B0/C0:** no amendment. Player/weather sources remain blocked by the frozen PIT policy.  
**Applicability to future Candidate 5:** none directly; may motivate separately versioned PIT-safe future overlays.  
**Disposition:** **NO PHASE-3 AMENDMENT.**

---

## 4. BlairCurrey / `nfl-analytics`

**Source:** https://github.com/BlairCurrey/nfl-analytics  
**Key files reviewed:** `nfl_analytics/docs/model.md`, `nfl_analytics/docs/training-data.md`.  
**Evidence tier:** 3.  
**Target:** game spread / margin.  
**Architecture:** deliberately simple linear regression on pregame team-state features.  
**Inputs:** nflverse play-by-play aggregated into running pregame team statistics. Early-season values blend a prior of pseudo-games at the previous-season mean.  
**Market use:** Vegas closing spread is an explicit benchmark, not silently merged into the football-only model.  
**Validation:** author reports training on seasons before 2023 and testing on 2023+ games.  
**Reported performance:** approximately 10.3 MAE for the simple model, 11.2 for naive HFA, and 9.8 for the Vegas closing spread on the reported test universe; ATS performance is below betting breakeven.  
**Reproducibility:** strong relative to practitioner projects; source code, data pipeline and documentation are public.  
**Leakage risks:** fewer than the random-split examples, but the reported figures remain an external implementation rather than LevLine's frozen paired universe.  
**Useful idea:** previous-season pseudo-game shrinkage for early-season states; explicit artifacts/manifests; simple baseline discipline; recent-season held-out evaluation.  
**Negative evidence:** a reasonable football model can show real signal and still fail to beat the closing market or ATS breakeven.  
**Applicability to A0:** early-season shrinkage is mechanistically aligned with partial pooling, but adding a new pseudo-game hyperparameter now would create an extra degree of freedom. A0 already regularizes team effects and time weights.  
**Applicability to B0:** supports prior-state shrinkage conceptually; B0's red-zone shrinkage is fixed separately.  
**Applicability to C0:** reinforces the market as mandatory null.  
**Applicability to future Candidate 5:** useful reproducibility pattern, not a new predictive component.  
**Disposition:** **SUPPORTS SIMPLICITY / SHRINKAGE; KEEP FROZEN CONTRACT.**

---

## 5. Dilligaf78 / `NFL-model`

**Source:** https://github.com/Dilligaf78/NFL-model  
**Code reviewed:** `NFL_Betting_Spread_Prediction_LR.py`.  
**Evidence tier:** 3 for inspectable code; reported performance is not valid confirmatory evidence.  
**Target:** spread and team/game scoring targets.  
**Architecture:** ElasticNet experiments and referenced Random Forest experiments; power-rating, weather and team-stat feature construction.  
**Validation:** code uses random `train_test_split`. It searches alpha/l1 ratio on the same test block, searches intercept/normalization settings on that block, then searches the **test size itself** for best score. The scaler is fit before the split, and prediction features are independently `fit_transform`ed rather than transformed with the training scaler.  
**Chronology:** invalid for LevLine confirmatory use.  
**Reproducibility:** source is available, which makes the validation anti-patterns directly auditable.  
**Leakage / selection risks:** full-data scaling before split; random time mixing; test-set hyperparameter optimization; test-size search; repeated reuse of the evaluation sample; inconsistent prediction scaling.  
**Useful idea:** weather, power ratings and regularized linear models are legitimate exploratory concepts.  
**Negative evidence:** this repository is a concrete example of why impressive held-out scores can be meaningless after evaluation-set optimization.  
**Applicability to A0/B0/C0:** no amendment; Ridge already covers the justified regularized-linear idea, while weather remains PIT-blocked.  
**Applicability to future Candidate 5:** none beyond methodological caution.  
**Disposition:** **VALIDATION ANTI-PATTERN EVIDENCE; PERFORMANCE CLAIMS EXCLUDED.**

---

## 6. slieb74 / `NFL-Betting-Data`

**Source:** https://github.com/slieb74/NFL-Betting-Data  
**Evidence tier:** 3 for inspectable project; historical betting accuracy claim is not chronology-clean enough for confirmatory use.  
**Target:** NFL totals / over-under.  
**Architecture:** linear/log-linear/log-log regression exploration with Box-Cox transforms; offensive/defensive scoring states, Pythagorean strength, recent-form window, weather; a clustering experiment.  
**Market use:** total line is the betting benchmark.  
**Validation / chronology:** project spans games since 1979 and reports a broad historical backtest; the public documentation does not establish the nested rolling-origin protocol required here.  
**Useful idea:** simple scoring/allowed states and transformations can be competitive; scoring discreteness matters.  
**Negative result:** the attempted four-cluster matchup decomposition was **less accurate** than the overall regression. This is useful evidence against adding complexity merely because it is football-intuitive.  
**Transfer risk:** era mixing since 1979 and realized-weather provenance limit direct relevance to modern NFL Phase 3.  
**Applicability to A0/B0/C0:** supports simple baselines and negative-result preservation; no amendment.  
**Applicability to future Candidate 5:** none directly.  
**Disposition:** **NEGATIVE-COMPLEXITY EVIDENCE; NO AMENDMENT.**

---

## 7. David Sasser

**Source:** https://www.davidsasser.com/cfb and related publicly discoverable pages/material.  
**Evidence tier:** 4 for observable product architecture; 5 for public performance claims absent reconstructable methodology.  
**Target:** publicly visible current college-football score/line predictions; no reproducible current NFL methodology was established in this delta.  
**Observable architecture:** projected team scores, projected/model line, sportsbook opening/current line and ATS selection are presented as separate product concepts.  
**Validation / chronology:** no public current model specification, immutable historical PIT forecast archive, deterministic training procedure, source-code implementation or same-horizon audit sufficient for scientific reconstruction was located.  
**Useful idea:** keep football score projection, model line, market line and betting decision as separate surfaces.  
**Negative / limitation:** a public win/loss record cannot substitute for a chronology-safe paired forecast archive.  
**Applicability to A0/B0/C0:** reinforces the existing separation of football-only A/B and market-aware C; no implementation change.  
**Applicability to future Candidate 5:** interface/separation lesson only.  
**Disposition:** **PRODUCT COMPARATOR ONLY; PUBLIC RECORD NOT SCIENTIFIC VALIDATION.**

---

## 8. Peer-reviewed dynamic-score evidence — Glickman & Stern

**Source:** Mark E. Glickman & Hal S. Stern, “A State-Space Model for National Football League Scores,” *Journal of the American Statistical Association* 93(441), 1998. DOI: 10.1080/01621459.1998.10474084.  
**Evidence tier:** 1.  
**Target:** NFL game scores.  
**Architecture:** time-varying team strength under a first-order autoregressive state-space model, addressing week-to-week and season-to-season strength changes.  
**Useful idea:** coherent dynamic offense/team strength is statistically well founded.  
**Limitation:** old NFL era and different data environment; it does not prove that an expanded modern state-space implementation will beat a simpler regularized model.  
**Applicability to A0:** supports the hypothesis A0 is testing. It does **not** justify opening deferred A1 before A0 exists; Phase 2 intentionally bounded A0 to prevent a state-space model zoo.  
**Applicability to B0/C0:** indirect only.  
**Disposition:** **STRONG SUPPORT FOR A FAMILY; NO PRE-RESULT A1 EXPANSION.**

---

## 9. Peer-reviewed exact-score evidence — Baker & McHale

**Source:** Rose D. Baker & Ian G. McHale, “Forecasting exact scores in National Football League games,” *International Journal of Forecasting* 29(1), 2013, 122–130. DOI: 10.1016/j.ijforecast.2012.07.002.  
**Evidence tier:** 1.  
**Target:** exact NFL scores / game result.  
**Architecture:** scoring point process with hazards informed by previous-game team statistics and/or bookmaker spread/total.  
**Validation:** out-of-sample forecasts using several criteria.  
**Key negative finding:** for predicting game results, the model was marginally outperformed by the betting market, even though it was competitive for exact-score forecasting.  
**Useful idea:** discrete football scoring processes and full score distributions deserve direct evaluation.  
**Applicability to B0:** strongly supports the scientific question, while the frozen B0 possession/drive multinomial simulator is a deliberately simpler implementation appropriate to the limited modern sample.  
**Applicability to C0:** reinforces the market as a strong null.  
**Disposition:** **SUPPORTS B0 + MARKET NULL; NO EXPANSION.**

---

## 10. Turnover predictability evidence

**Source:** “Empirical Prediction of Turnovers in NFL Football,” peer-reviewed/public full text at https://pmc.ncbi.nlm.nih.gov/articles/PMC5969004/  
**Evidence tier:** 1.  
**Target:** next-play turnover probability.  
**Finding:** turnovers are rare and apparently random at aggregate level, but conditional models can identify some high-risk contexts.  
**Useful idea:** turnover rate can carry conditional information.  
**Negative / limitation:** rarity and high variance make turnover outcomes unstable; game-level turnover differentials should not be treated as persistent team skill without shrinkage.  
**Applicability to B0:** supports retaining the already frozen turnover-per-drive / takeaway-per-drive states as compact, lagged predictors rather than creating a standalone turnover learner.  
**Disposition:** **KEEP B0 TURNOVER STATE; NO NEW MODEL.**

---

## 11. Time-series / validation synthesis

The new-source audit strengthens rather than weakens the Phase 2 evaluation contract:

- NFL games are temporally ordered and team state evolves; random K-fold/random train-test splits are not acceptable evidence for a prospective model.
- preprocessing, state construction, hyperparameter selection, covariance/dispersion estimation and stacking must be fit only on prior-time data.
- repeated model/feature/threshold comparisons on the same evaluation set are a form of test-set optimization.
- same-horizon market comparisons are mandatory; a closing/late line cannot be relabeled T-120.
- simple regularized models remain credible at NFL sample sizes; deep/boosted models do not earn entry merely from flexibility.
- market residuals can legitimately shrink toward zero; `NO_INCREMENTAL_FOOTBALL_EDGE` is an acceptable scientific outcome.

---

# Negative-evidence ledger

| Negative finding | Source | Phase 3 consequence |
|---|---|---|
| Random train/test shuffling in a time-dependent NFL problem | Model 5.0; Dilligaf78 | Exclude headline performance from confirmatory evidence; preserve rolling chronology. |
| Test-set hyperparameter/test-size search | Dilligaf78 code | No grid expansion, metric switching or test-size search. |
| Forward-looking weighting can materially overstate EPA model quality | nfelo WEPA retrospective | Preserve backward-only state/tuning; no whole-sample feature weighting. |
| A simple football model can remain meaningfully worse than Vegas | BlairCurrey | Keep market null and simple baselines; negative results survive. |
| Exact-score model can be marginally worse than betting market for game result | Baker & McHale | Do not presume B0 beats market; evaluate distribution separately from market-relative point accuracy. |
| Added matchup clustering reduced accuracy | slieb74 | Complexity must earn its place; do not add intuitive clusters/interactions post hoc. |
| Player/weather sophistication is not enough without timestamp legality | Quinnipiac + Phase 2 source audit | Keep player/weather blocked absent PIT proof. |
| Public records without reconstructable methodology are not validation | David Sasser | Product lessons only; no performance import. |
| Turnovers are rare/noisy even if some conditional signal exists | turnover literature | Use compact shrunk lagged state only; no turnover-result chasing. |

---

# Pre-result research gate

## Decision: `KEEP_FROZEN_PHASE3_CONTRACT`

This decision was made **before any A0/B0/C0 development metric or 2022–2024 challenger output existed**.

No source reviewed in this delta satisfies all requirements needed to justify a preregistration amendment:

1. credible external evidence;
2. direct mechanistic fit to a Phase 1 failure;
3. chronology-safe source availability in LevLine;
4. bounded complexity;
5. low additional research degrees of freedom;
6. a clear reason the already frozen A0/B0/C0 design is scientifically inadequate.

Instead, the delta predominantly **confirms** the frozen choices:

- A0 tests dynamic, opponent-adjusted, regularized football strength without opening a state-space search.
- B0 tests possession plus discrete drive outcomes while remaining independent of A0.
- C0 tests whether A0 football information explains residual error beyond a strong market prior.
- D remains conditional under its exact gate.
- player/QB/injury/weather remain deferred until PIT-safe historical/prospective contracts exist.
- no XGBoost, Random Forest, neural net, GAM, Negative Binomial, threshold search or new feature family is opened.

**No `PRE_RESULT_PREREGISTRATION_AMENDMENT.md` is created because no amendment is justified.**

The first development output freezes these candidate identities exactly as specified in the Phase 2 contract and the user-authorized Phase 3 execution prompt.

---

## Research-gate red team

Before closing the gate, the following failure questions were asked explicitly:

- Does a strong-looking model use a random split? **Yes in multiple practitioner examples; those results were down-weighted.**
- Does it use closing lines while implying an earlier forecast horizon? **Often unclear; no such claim is imported.**
- Does it use final injury/starter/weather information? **Possible in several public projects; not imported without PIT proof.**
- Are betting thresholds selected after seeing results? **Yes/unclear in several practitioner projects; threshold evidence is not used.**
- Is the sample small relative to model complexity? **Often yes; this argues for bounded regularization.**
- Were many models tried and only a winner highlighted? **Yes in several examples; no model-zoo inference is accepted.**
- Does sophistication reliably beat a simple baseline or market? **No; several sources provide direct contrary evidence.**
- Is reported improvement economically/statistically meaningful and reproducible? **Frequently not established.**
- Is code/data/PIT provenance sufficient for exact reconstruction? **Only some open-source projects are meaningfully reproducible, and none justifies changing the frozen A0/B0/C0 contract.**

## Final disposition

**Research delta COMPLETE.**  
**Frozen Phase 3 contract retained unchanged.**  
**Next permitted action:** implement the shared chronology/evaluation scaffold and frozen A0/B0/C0 candidates.  
**Still prohibited:** 2025 scoring, completed-2026 selection, Phase 4, Candidate 5 training, production changes.