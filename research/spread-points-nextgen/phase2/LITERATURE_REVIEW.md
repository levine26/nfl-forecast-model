# Phase 2 — Literature Review

**Program:** LevLine Spread & Points Next-Generation Research  
**Phase:** 2 — Deep External Research & Challenger Design  
**Status:** research synthesis; no production change  
**Primary question:** Which model families have enough statistical, football, and forecasting evidence to justify controlled LevLine challengers?

## Evidence hierarchy

Phase 2 separates evidence into four classes:

1. **Peer-reviewed statistical / forecasting research** — strongest evidence for general methodology.
2. **Peer-reviewed football / sports-market research** — strongest domain-specific evidence, but often older and based on historical information environments.
3. **Transparent technical / open-source work** — useful for implementation ideas and reproducibility, but not equivalent to peer review.
4. **Opaque public model claims** — useful only as product/idea comparators unless data, chronology and evaluation can be independently reconstructed.

No external source is treated as proof that a LevLine implementation will improve accuracy. Transfer requires chronology-safe validation in this repository.

## Verified evidence ledger

The following classifications are frozen from the Phase 2 source audit:

| Source | Evidence class | What is actually supported | What is not supported |
|---|---|---|---|
| Glickman & Stern (1998), JASA | **peer reviewed** | NFL score forecasting with time-varying team strength under a first-order autoregressive state process | direct evidence that LevLine's exact A0 implementation will improve modern NFL forecasts |
| Harville football-rating work | **peer reviewed** | linear/mixed team-rating methodology and home-field/team-effect forecasting | a mandate to prefer a specific coefficient set or era-specific model |
| Baker & McHale (2013), IJF | **peer reviewed** | genuine OOS NFL exact-score point-process forecasts; discrete football scoring mechanism; market remained a very strong outcome benchmark | proof that a LevLine drive simulator will beat the market |
| Boulier & Stekler (2003); Boulier, Stekler & Amundson (2006); Lacey (1990); Gray & Gray (1997) | **peer reviewed** | NFL betting markets are difficult benchmarks; some historical inefficiencies exist but are unstable/era-sensitive | a durable modern betting rule or guaranteed market inefficiency |
| Gneiting & Raftery (2007), JASA | **peer reviewed** | proper scoring rules for honest distributional forecast evaluation | a particular NFL distribution |
| Yurko, Ventura & Horowitz (2019), JQAS | **peer reviewed** | reproducible public-PBP expected-points/player evaluation and multilevel shrinkage | proof that player variables improve next-game team score forecasts |
| Brill et al. (2024) expected-points paper | **strong technical preprint, not peer reviewed at Phase 2 audit** | concrete warnings about selection bias, overfit artifacts, dependence and uncertainty in flexible football EP models | peer-reviewed validation or direct score-forecast uplift |
| nfelo | **reproducible open source / practitioner technical evidence** | inspectable dynamic rating, QB/context and explicit market-regression architecture | peer-reviewed proof of its claimed accuracy or transferability to LevLine |
| Open Source Football / nflverse examples | **reproducible open source / technical evidence** | opponent adjustment, multilevel EPA shrinkage and lagged public-data implementations | guaranteed OOS benefit in LevLine |
| davidsasser.com | **product-design observation / opaque methodology** | current public board separates projected scores, projected line, opening/current market line and picks | reproducible model specification, PIT archive, independent validation, or scientific proof of self-reported records |

This hierarchy controls the language used elsewhere in Phase 2.

### Source-quality register

| Source / idea | Evidence class | What it can support here | What it cannot establish |
|---|---|---|---|
| Glickman & Stern (1998) NFL state-space scores | **peer reviewed** | dynamic latent team strength; time variation | that LevLine's specific implementation will improve |
| Harville football rating work | **peer reviewed** | strong simple linear/mixed baselines | superiority of any modern feature set |
| Baker & McHale (2013) exact NFL scores | **peer reviewed** | discrete score-process modeling; genuine OOS precedent | direct transfer of old-era coefficients |
| Boulier/Stekler market studies | **peer reviewed** | market as a difficult benchmark | current-market efficiency at a specific 2026 horizon |
| Gneiting & Raftery (2007) | **peer reviewed** | proper probabilistic scoring | which NFL distribution family is best |
| Gama et al. (2014) concept drift survey | **peer reviewed review** | temporal drift requires chronology-aware evaluation | a specific NFL decay rate |
| Bates & Granger (1969) forecast combination | **peer reviewed** | combinations can help when errors differ | that an ensemble should be forced |
| Diebold & Mariano (1995) | **peer reviewed** | paired predictive-accuracy comparison principles | immunity from small-sample uncertainty |
| nfelo | **reproducible open source / technical** | architecture, market-regression separation, implementation ideas | independent peer-reviewed accuracy claims |
| Open Source Football / nflverse technical work | **reproducible open source / technical** | opponent adjustment, shrinkage, public-data implementation | automatic OOS improvement |
| David Sasser public CFB board | **practitioner/product evidence; method opaque** | semantic separation of score, model line, market line and pick | scientific validation of the public record |

---

## 1. Dynamic team strength and score prediction

### Glickman & Stern (1998) — state-space NFL scores

**Source:** Mark E. Glickman and Hal S. Stern, *A State-Space Model for National Football League Scores*, Journal of the American Statistical Association 93(441), 25–35.  
DOI: https://doi.org/10.1080/01621459.1998.10474084

The model treats team strength as time-varying rather than fixed and lets latent strength evolve through a first-order autoregressive state process. The motivating sources of movement include week-to-week shocks and season-to-season personnel changes.

**LevLine implication:** Phase 1 found a stable but compressed model built from fixed-form rolling summaries. A dynamic latent offense/defense model is a better-motivated way to represent changing team quality than simply adding more rolling-window variants.

### Harville (1977; related NFL work 1980) — point-spread linear models

**Source:** David Harville, *The Use of Linear-Model Methodology to Rate High School or College Football Teams*, JASA 72(358), 278–289.  
DOI: https://doi.org/10.1080/01621459.1977.10480991

Harville models game point spread through team effects plus home field and shows how linear/mixed-model methods can produce forecasts comparable with human/bookmaker benchmarks. Later NFL work extended the idea with annual team strengths following an autoregressive process.

**LevLine implication:** simple regularized score models remain legitimate baselines. Phase 1 already found ElasticNet slightly better than the current equal-ish nonlinear ensemble, so complexity must beat a strong linear benchmark rather than be assumed superior.

### Broader dynamic-rating literature

Dynamic paired-comparison and sports-rating work, including random-walk / autoregressive latent ability models, supports the principle that team strength should be partially pooled and allowed to evolve over time rather than estimated independently from short rolling windows.

**Decision:** dynamic latent team strength is a high-priority architecture hypothesis.

---

## 2. Opponent adjustment and regularization of EPA

### Open Source Football — multilevel EPA team ability

**Source:** *Estimating Team Ability From EPA*  
https://opensourcefootball.com/posts/2021-06-27-estimating-team-ability-from-epa/

This public technical treatment emphasizes that raw EPA/play is noisy and schedules differ. It uses multilevel models to regularize team ability, adjust for opposing offense/defense and explicitly represent uncertainty.

### Open Source Football — opponent-adjusted EPA

**Source:** *Adjusting EPA for Strength of Opponent*  
https://opensourcefootball.com/posts/2020-08-20-adjusting-epa-for-strenght-of-opponent/

This implementation uses lagged opponent strength to adjust weekly offense/defense EPA. It is a useful reproducible demonstration, not proof that every opponent adjustment improves future prediction.

### Open Source Football — rolling EPA exploration

**Source:** *Exploring Rolling Averages of EPA*  
https://opensourcefootball.com/posts/2020-12-29-exploring-rolling-averages-of-epa/

This work explores lagged dynamic windows and predictive value. It reinforces the importance of chronology but also highlights the large design space created by arbitrary rolling-window choices.

**LevLine implication:** Phase 2 should prefer a regularized opponent-adjusted latent-strength formulation over an unconstrained search across many rolling-window transforms.

**Decision:** opponent adjustment belongs inside Challenger A; a broad feature-window sweep does not.

---

## 3. Market efficiency and the market as a prior

### Boulier & Stekler (2003)

**Source:** *Predicting the outcomes of National Football League games*, International Journal of Forecasting 19(2), 257–270.  
DOI: https://doi.org/10.1016/S0169-2070(01)00144-3

The study compared power-score forecasts, a naive forecast, an expert, and the betting market over 1994–2000. The betting market was the strongest predictor, followed by power-score forecasts.

### Boulier, Stekler & Amundson (2006)

**Source:** *Testing the efficiency of the National Football League betting market*, Applied Economics 38(3), 279–284.  
DOI: https://doi.org/10.1080/00036840500368904

Tests of weak-form efficiency, objective information and betting strategies did not provide conclusive evidence of broad market inefficiency over the sample.

### Lacey (1990)

**Source:** *An estimation of market efficiency in the NFL point spread betting market*, Applied Economics 22(1), 117–129.  
DOI: https://doi.org/10.1080/00036849000000056

The study largely supports market efficiency while identifying some historical trading-rule anomalies.

### Gray & Gray (1997)

**Source:** *Testing Market Efficiency: Evidence From The NFL Sports Betting Market*, Journal of Finance 52(4), 1725–1737.  
DOI: https://doi.org/10.1111/j.1540-6261.1997.tb01129.x

A probit-based approach studies market efficiency and selective betting decisions.

### Later efficiency studies

Some later studies report exploitable historical subgroups, including divisional/familiarity effects. These findings are useful hypothesis generators but are vulnerable to era drift, multiple testing and strategy-selection effects and therefore do not justify fixed LevLine rules.

**LevLine implication:** Phase 1 independently reproduced the same core empirical fact in modern data: the historical market has lower margin and total MAE than the current score model. The correct market-aware research question is therefore incremental residual prediction, not whether LevLine can ignore the market.

**Decision:** a market-residual challenger is mandatory; market-aware accuracy must be evaluated separately from football-only model quality.

---

## 4. Market regression as a technical architecture

### nfelo market regression

**Public/open-source sources:**
- https://www.nfeloapp.com/about/
- https://github.com/greerreNFL/nfelo
- repository module: `nfelo/Utilities/MarketRegression/README.md`

nfelo explicitly separates an unregressed football rating from market regression. Its current open-source implementation uses:

- a logistic pull toward the opening market based on model-market disagreement;
- an adjustment to that regression using open-to-close movement;
- a residual cap so posted opinions do not become arbitrarily extreme.

Its optimizer documentation also warns that a pure forecast-accuracy objective can degenerate into simply copying the market.

**LevLine implication:** the architectural separation is valuable. The exact nonlinear nfelo regression rule is **not** preregistered for LevLine. Phase 1 showed that large LevLine-market disagreement currently becomes less trustworthy, so LevLine will first test a simpler and easier-to-audit residual model.

**Decision:** use nfelo as a strong technical comparator, not as a template to copy blindly.

---

## 5. Score-process / drive decomposition

### Baker & McHale (2013) — exact NFL scores

**Source:** Rose D. Baker and Ian G. McHale, *Forecasting exact scores in National Football League games*, International Journal of Forecasting 29(1), 122–130.  
DOI: https://doi.org/10.1016/j.ijforecast.2012.07.002

This is the most directly relevant exact-score paper located in Phase 2. It builds a point-process model for NFL scoring, allows scoring hazards to vary using prior-game team statistics and/or sportsbook spread/total information, and evaluates genuine out-of-sample forecasts. The paper explicitly notes that NFL score distributions are unusual because touchdowns, field goals and other scoring events create repeated combinations of 3 and 7 rather than a smooth continuous score distribution.

The authors report that the betting market remains extremely strong for game outcomes, while their exact-score forecasts are competitive with the market.

**LevLine implication:** a joint-score challenger should model football scoring as discrete events or drives rather than rely only on a Normal margin/total error layer. It also reinforces the need to keep football-only and market-conditioned variants separately labeled.

### nflWAR / reproducible expected-points modeling

**Source:** Ronald Yurko, Samuel Ventura and Maksim Horowitz, *nflWAR: a reproducible method for offensive player evaluation in football*, Journal of Quantitative Analysis in Sports 15(3), 163–183 (2019).  
DOI: https://doi.org/10.1515/jqas-2018-0010

The framework uses public play-by-play, expected-points modeling, win probability and multilevel player evaluation. It demonstrates that football value can be modeled through coherent play-level outcomes and partial pooling rather than only box-score aggregates.

### Brill, Yee, Deshpande & Wyner (2024 preprint — not peer reviewed at Phase 2 audit)

**Source:** *Moving from Machine Learning to Statistics: the case of Expected Points in American football*  
arXiv: https://arxiv.org/abs/2409.04889

This work highlights selection bias, overfit artifacts, lack of uncertainty and dependence problems in flexible expected-points models and proposes statistically regularized alternatives.

**LevLine implication:** a drive/possession challenger should not be a giant black-box classifier over every play. It should model a small number of football processes with regularization and uncertainty.

### Public drive-model work

Open implementations such as drive-outcome or drive-score frameworks provide useful decomposition ideas: expected possessions, drive result probabilities and simulated score distributions. These are structurally different enough from current LevLine to merit one controlled challenger, provided complexity is bounded.

**Decision:** Challenger B will be a compact drive/possession score-process model, not a full play-sequence simulator.

---

## 5A. Red-zone finishing, explosive plays, and turnover variance

These process variables are mechanistically relevant to team scoring, but their **predictive persistence is not equally established**. Phase 2 therefore separates "important when realized" from "stable enough to forecast."

### Turnovers — peer-reviewed evidence, high impact but rare/noisy

Joel R. Bock, *Empirical Prediction of Turnovers in NFL Football*, Sports 5(1), 2017, DOI 10.3390/sports5010001, uses seven NFL seasons of play-by-play and reports that interceptions/fumbles can be predicted under some play-level conditions. The same paper emphasizes that turnovers are rare events, cites weak within-season persistence, and discusses regression-to-the-mean/chance components in turnover differential.

**LevLine implication:** turnovers belong, if used, as heavily regularized prior-game process rates inside B0 rather than as deterministic "turnover luck" adjustments. Realized same-game turnovers are never pregame features. A rare-event tail can materially affect score variance even when the conditional mean is hard to forecast.

**Evidence class:** peer-reviewed domain evidence for rare-event predictability; not direct evidence that a pregame team turnover-rate feature improves next-game margin/total forecasts.

### Red-zone finishing — strong mechanism, weaker forecast-persistence evidence

Public nflverse-based technical work consistently shows the scoring arithmetic: a red-zone trip ending in a touchdown produces materially more points than a field goal, while team red-zone TD rates are based on relatively small samples and regress substantially.

**LevLine implication:** B0 may use a shrinkage-smoothed prior-drive red-zone TD conversion state because it maps directly to TD-vs-FG drive outcomes, but raw recent red-zone percentage is not treated as a stable team "skill" or an independent candidate-selection signal. The shrinkage formula must be fixed before development metrics.

**Evidence class:** reproducible/practitioner technical evidence and football mechanism; insufficient peer-reviewed next-game forecast evidence to justify a broad red-zone feature search.

### Explosive plays — high scoring leverage, limited independent forecast evidence

Public play-by-play technical analyses show that drives containing large gains score at much higher rates and that explosive plays create score-distribution tails. However, a high realized explosive-play rate is partly a noisy efficiency outcome and is not by itself evidence of stable next-game predictability.

**LevLine implication:** B0 may include one fixed lagged explosive-play rate for offense and defense as a bounded drive-process state. Phase 3 may not search multiple yardage thresholds or rolling windows after seeing results; the definition must be frozen in code before the first output.

**Evidence class:** reproducible/practitioner technical evidence; not sufficient to create a separate challenger or unconstrained feature family.

### Combined decision

Red-zone, explosive-play, and turnover variables are **component-level hypotheses inside the bounded B0 process model**, not reasons to add candidates. Their forecast contribution must be assessed through the preregistered B0 identity and future ablation governance, with shrinkage appropriate to their variance.

---

## 6. Player, QB and personnel effects

### nflWAR

The multilevel-player framework demonstrates that public PBP can support shrinkage-based player value estimates with uncertainty, but it does not establish that player-level features improve next-game score prediction.

### nfelo QB / team-and-scheme analysis

**Source:** https://www.nfeloapp.com/analysis/team-and-scheme-nfl-qbs

The analysis argues that replacement-QB performance cannot be cleanly separated from surrounding team/scheme and that quarterback effects should not be treated as isolated deterministic point adjustments.

### Injury / information-market literature

Historical sports-market work shows that betting markets react to quarterback/key-player absence and can partially anticipate injury information. That makes player-state variables especially vulnerable to duplicated market signal.

**LevLine implication:** Phase 1's 2025 PIT-qualified availability slice was suggestive but not decisive, and 2022–2024 do not have a unified qualified starter/availability reconstruction.

**Decision:** QB/personnel is a conditional research overlay, not one of the three initial historical challengers. It may enter only after a multi-season PIT contract can be satisfied or in prospective shadow evaluation.

---

## 7. Home field, rest, travel and weather

The current model already includes rest differential and Elo home-field structure. Public research suggests home advantage is heterogeneous and can interact with divisional familiarity, surface, travel/time zone and environmental conditions.

Weather-market research has found historical effects in some extreme conditions, but those studies often use realized daily weather rather than the exact forecast known at a decision horizon.

**LevLine implication:** Phase 1 showed rest already has useful structure and found historical weather is not PIT-safe for direct use.

**Decision:** retain simple home/rest structure initially. Weather and richer travel interactions are conditional extensions only after source chronology is proven.

---

## 8. Predictive distributions and proper scoring

### Gneiting & Raftery (2007)

**Source:** *Strictly Proper Scoring Rules, Prediction, and Estimation*, JASA 102(477).  
DOI: https://doi.org/10.1198/016214506000001437

Proper scoring rules reward honest probabilistic forecasts and evaluate both calibration and sharpness. The logarithmic and quadratic/Brier scores are categorical examples; CRPS is appropriate for continuous predictive distributions.

### NFL key-number structure

**Technical source:** https://www.nfeloapp.com/analysis/margin-probabilities-from-nfl-spreads

Football margins are not exactly Normal because scoring increments create spikes at key margins. This matters for converting a predicted mean margin into cover/win probabilities.

**LevLine implication:** the current public probability-to-margin bridge uses a Normal approximation. A future joint-score challenger should preserve discrete football scoring structure rather than assuming that all uncertainty is Gaussian.

**Decision:** Phase 4 evaluation will include distributional scoring/coverage where a challenger emits a distribution. Challenger B's simulation distribution should naturally preserve scoring discreteness.

---

## 9. Forecast validation and chronology

**Sources:**
- Hyndman & Athanasopoulos, *Forecasting: Principles and Practice*, time-series cross-validation: https://otexts.com/fpp3/tscv.html
- Forecast-evaluation pitfalls review: https://pmc.ncbi.nlm.nih.gov/articles/PMC9718476/

The central requirement is rolling-origin evaluation: each test forecast is generated only from information available earlier in time. Any tuning, stacking or blend-weight selection must itself occur inside the prior-time training region.

**LevLine implication:** this directly addresses the Phase 1 finding that current regression weights and ordinary stack meta-weights reuse the same evaluation block they summarize.

**Decision:** nested rolling-origin selection is binding for all Phase 3 challengers.

---

## 10. Concept drift, forecast combination, and paired comparison

### Concept drift

**Source:** João Gama, Indrė Žliobaitė, Albert Bifet, Mykola Pechenizkiy and Abdelhamid Bouchachia (2014), *A Survey on Concept Drift Adaptation*, ACM Computing Surveys 46(4), Article 44. DOI: https://doi.org/10.1145/2523813

The general forecasting lesson is that the mapping from predictors to outcomes can change over time. In NFL terms, rules, pace, fourth-down strategy, roster construction and information markets can shift. This supports time-decay/dynamic-state hypotheses and chronological validation; it does **not** justify searching many decay rates until one fits the latest season.

**LevLine implication:** candidate tuning stays inside prior-time folds. Recent seasons receive an explicit modern summary, while older data may stabilize parameters only through the frozen candidate rules.

### Forecast combination

**Source:** J. M. Bates and C. W. J. Granger (1969), *The Combination of Forecasts*, Operational Research Quarterly / Journal of the Operational Research Society 20(4), 451–468. DOI: https://doi.org/10.1057/jors.1969.103

Forecast combinations can reduce error when component errors contain complementary information. The result does not imply that adding models is always beneficial; highly correlated errors add little.

**LevLine implication:** Challenger D remains conditional. Complementarity and nested OOF blend improvement must pass an objective Phase 3 gate; no ensemble is built for symmetry.

### Paired forecast comparison

**Source:** Francis X. Diebold and Roberto S. Mariano (1995), *Comparing Predictive Accuracy*, Journal of Business & Economic Statistics 13(3), 253–263. DOI: https://doi.org/10.1080/07350015.1995.10524599

Forecast comparisons should use paired loss differentials and account for dependence rather than comparing unrelated aggregate summaries.

**LevLine implication:** exact-common-game comparisons and season+week block resampling remain the primary uncertainty mechanism. Formal asymptotic tests are supplementary rather than a substitute for the preregistered paired bootstrap.

---

## 11. Research conclusions carried into challenger design

The strongest evidence supports:

1. **dynamic, partially pooled offense/defense team strength** rather than a large set of ad hoc rolling features;
2. **opponent adjustment** tested under strict chronology;
3. **market residual prediction** because the market is a strong prior and Phase 1 confirms it currently beats LevLine on continuous targets;
4. **one structurally distinct drive/possession model** to test whether football-process decomposition reduces total and favorite compression;
5. **proper probabilistic evaluation** when a predictive distribution exists;
6. **QB/personnel only under qualified point-in-time identity/availability**;
7. **rolling-origin nested validation** with an untouched challenger holdout.

The literature does **not** justify:

- automatic promotion of a complex joint simulator;
- a broad feature kitchen sink;
- betting-rule selection from ATS hit rate;
- copying a public model's weights;
- treating a closing-line backtest as a T-120 result;
- using hindsight player/weather states.

These conclusions define the Phase 2 preregistration.

## 11. Evidence-classification audit and anti-overfit addendum

The closeout red-team review rechecked the main sources and explicitly classifies what kind of evidence each can support.

| Source / family | Evidence class | Reproducible enough to transfer method? | What it can support here | What it cannot prove |
|---|---|---:|---|---|
| Glickman & Stern (1998), NFL score state-space model | **peer reviewed** | yes, methodologically | dynamic latent team strength; evolving offense/defense state | that the same specification beats a modern market or LevLine |
| Harville football/NFL linear mixed models | **peer reviewed** | yes, methodologically | strong simple team-effect baselines; partial pooling / temporal structure | that extra complexity is required |
| Baker & McHale (2013), exact NFL scores | **peer reviewed** | yes, methodologically | discrete scoring-process motivation; genuine OOS exact-score evaluation | that a LevLine drive model will improve modern NFL forecasts |
| Boulier/Stekler and related NFL market-efficiency work | **peer reviewed** | yes for historical samples | sportsbook market as a difficult baseline; separate forecast-vs-market question | present-day exploitable inefficiency |
| Gneiting & Raftery (2007) | **peer reviewed** | yes | proper scoring, calibration plus sharpness | any football-specific architecture |
| nflWAR / public expected-points work | **peer reviewed / reproducible research** | substantially | multilevel football-process modeling and uncertainty | direct next-game score lift |
| Brill et al. expected-points critique | **strong technical research / preprint** | methodologically | regularization, dependence, selection-bias and uncertainty cautions | settled peer-reviewed NFL forecasting evidence |
| Open Source Football opponent-adjusted / multilevel EPA | **reproducible open source / technical** | yes | implementable opponent-adjustment and shrinkage ideas | a guaranteed OOS score improvement |
| nfelo | **reproducible open source / practitioner technical** | high for architecture/code | separation of football signal and market regression; dynamic ratings; public caution about overfit | independent scientific proof of reported edge |
| davidsasser.com public board | **practitioner/product observation; methodology opaque** | no | semantic separation of projected scores, model line, and market line | model validity, PIT integrity, or claimed performance |

### Model-selection and concept-drift caution

The public nfelo WEPA methodology history is useful precisely because it documents a failure mode: a forward-looking feature-selection approach could look predictive while overfitting, motivating a backward-looking evaluation redesign. That is practitioner evidence, not a LevLine result, but it reinforces the Phase 1 leakage audit and supports a narrow preregistered search.

Sources:
- https://www.nfeloapp.com/analysis/weighted-EPA-methodology-and-performance
- https://scikit-learn.org/stable/modules/cross_validation.html
- https://otexts.com/fpp3/tscv.html

**Phase 2 consequence:** no additional model family or broad window/feature search is authorized. Hyperparameters, preprocessing, residual-variance estimation, stacking and any conditional extension must remain inside prior-time folds.


---

## 11. Evidence-quality ledger and red-team additions

The Phase 2 review uses the following explicit evidence classifications.

| Source / idea | Evidence class | Direct NFL score relevance | Validation / chronology strength | Transferable conclusion | Limitation |
|---|---|---:|---|---|---|
| Glickman & Stern (1998), JASA | **peer reviewed** | high | predictive historical study; older era | time-varying latent team strength is statistically well motivated | 1988–1993 football/data environment |
| Harville football rating work | **peer reviewed** | medium-high | classical predictive modeling | simple regularized team effects remain serious baselines | older era; not modern PBP |
| Baker & McHale (2013), IJF | **peer reviewed** | **very high** | explicit out-of-sample exact-score evaluation | NFL scoring discreteness and score-process modeling deserve a bounded test | older features/market environment |
| Cain, Law & Peel (2000), Journal of Forecasting | **peer reviewed** | high | market-efficiency study; score-distribution result | non-Gaussian/count-like score structure is plausible; market remains difficult to beat | older era; negative-binomial fit is not itself a modern challenger prescription |
| Boulier / Stekler / Amundson market studies | **peer reviewed** | medium | historical OOS/efficiency tests | market must be treated as a strong baseline/prior | historical market microstructure differs from 2020s |
| Gray & Gray (1997) and later Shank studies | **peer reviewed** | medium | some OOS strategy tests | apparent inefficiencies can be regime/subgroup dependent and may decay | not a license for LevLine subgroup mining |
| Gneiting & Raftery (2007), JASA | **peer reviewed** | general methodology | strong | proper scores are required for predictive distributions | not football-specific |
| Hyndman rolling-origin validation text | **strong technical/statistical reference** | general methodology | strong chronology guidance | train/tune only on earlier observations | textbook, not NFL-specific |
| Brill et al. expected-points work (2024 preprint) | **strong technical research / preprint** | high process relevance | methodological critique; not Phase 2 peer-reviewed evidence | regularization, dependence and uncertainty matter; flexible ML can overfit football states | preprint status; not a pregame game-score model |
| nflverse / Open Source Football opponent-adjustment work | **reproducible open source / technical** | high feature relevance | code/data inspectable | lagged opponent adjustment and multilevel shrinkage are implementable at $0 | technical posts, not peer-reviewed forecast superiority |
| nfelo | **reproducible open source / practitioner** | high | architecture/code inspectable; data-source PIT varies | separate football base from market regression; market-aware models can collapse to market | not independent scientific validation |
| davidsasser.com CFB board | **practitioner/product evidence; opaque methodology** | product-semantic relevance | public board timestamp and outputs visible; model internals/forecast archive not established | keep projected scores, model line and market comparison semantically separate | performance record is not reproducible scientific evidence |

### Modern market-efficiency caution

Later peer-reviewed NFL betting-market papers do report historical inefficiencies in selected regimes. Phase 2 does **not** convert those findings into LevLine rules. Their existence reinforces the need for:

- fixed hypotheses before evaluation;
- same-horizon lines;
- paired OOS testing;
- resistance to subgroup/threshold fishing;
- willingness to conclude that a reported historical inefficiency has decayed.

This is especially important because Phase 1 found that large LevLine-market disagreement was **worse**, not better, on continuous error.

### Score-distribution implication

Cain, Law & Peel's finding that NFL point scoring was well described by a negative-binomial framework is directionally consistent with Baker & McHale's broader point that NFL scores are not well represented by a featureless Gaussian story.

Phase 2 therefore keeps:

- A0's correlated-Gaussian residual distribution as a **reference**;
- B0's discrete drive-scoring simulation as the structurally football-like challenger;
- distributional scoring/coverage as a required evaluation layer.

It does **not** add a third negative-binomial candidate simply because an older paper found a good marginal fit.

## 12. Literature red-team conclusion

After the deeper review, no additional initial challenger family is justified.

The strongest correction to the earlier Phase 2 draft is methodological rather than architectural:

- freeze A0/B0/C0;
- defer A1/C1 instead of activating them from qualitative development diagnostics;
- make inner tuning deterministic;
- keep D behind an explicit complementarity/improvement gate.

This reduces researcher degrees of freedom while preserving the three genuinely distinct scientific questions.


---

## 11. Phase 2 source-verification note — 2026-09-22

The closeout audit re-verified the core sources against publisher, author, or current technical pages:

- Glickman & Stern: JASA state-space NFL score article and first-order autoregressive team-strength formulation.
- Baker & McHale: International Journal of Forecasting exact-score point-process paper with genuine out-of-sample forecasts; the betting market marginally outperformed the model on game-result forecasting.
- Boulier & Stekler: International Journal of Forecasting comparison in which the betting market was the strongest predictor in their 1994–2000 sample.
- Boulier, Stekler & Amundson; Lacey; Gray & Gray: peer-reviewed market-efficiency studies with mixed historical anomalies but no basis for assuming a persistent modern edge.
- Gneiting & Raftery: JASA proper-scoring-rule foundation.
- Yurko, Ventura & Horowitz: peer-reviewed JQAS reproducible public-data football evaluation.
- Brill et al.: current source remains a preprint; it is intentionally not labeled peer reviewed.
- nfelo: current public documentation and open-source MarketRegression code explicitly separate raw football rating from market regression and document the risk that accuracy optimization can collapse toward the market.
- David Sasser: targeted searches of the current site and broader web located the public projection/graphic boards but **no sufficiently detailed technical methodology page, interview, source repository, archived PIT forecast ledger, or independent validation protocol**. The evidence classification therefore remains opaque/product-level.

No source discovered in this verification justifies expanding the A0/B0/C0 shortlist.
