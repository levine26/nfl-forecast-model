# LevLine Post-100 Optimization & Maximization Plan

Status: research-only; activates only after the current implementation/validation roadmap reaches 100%.

## Objective

Maximize out-of-sample NFL pregame forecast quality without contaminating the frozen 2026 production model or using completed-2026 outcomes for model, feature, hyperparameter, architecture, calibration, threshold, or ensemble selection.

The optimization target is probabilistic forecast quality, not raw pick accuracy alone. Primary metrics are Brier score and log loss; secondary metrics are calibration error, sharpness subject to calibration, accuracy, market-relative skill, and stability across seasons, confidence bands, and game archetypes.

## Immutable guardrails

- Production F-ST-01 coefficients and architecture remain frozen unless separately authorized after prospective evidence.
- Completed-2026 outcomes are excluded from all candidate selection, tuning, feature selection, calibration fitting, stopping rules, and architecture choice.
- Historical optimization uses only point-in-time-safe information available before kickoff.
- Every experimental candidate is research-only until it passes preregistered retrospective and prospective gates.
- Market data is treated as a benchmark and potentially as a feature; evaluation must separately report model-only, market-only, and fused performance.
- No data source is accepted merely because it is convenient. Every source must satisfy chronology, identity, revision-awareness, availability-time, and reproducibility checks.
- Optimization must never weaken existing fail-closed integrity checks.

## Scientific basis

The program is grounded in several established ideas:

1. **Strictly proper scoring rules.** Gneiting & Raftery (JASA, 2007) show why probabilistic forecasts should be evaluated with proper scores such as Brier/log score and why sharpness is useful only subject to calibration.
2. **Stacked generalization.** Wolpert (Neural Networks, 1992) motivates out-of-fold stacking to reduce generalization error rather than winner-take-all model selection.
3. **Calibration as a separately validated layer.** Kull, Silva Filho & Flach (AISTATS, 2017) show beta calibration can improve on logistic calibration and avoid some of its failure modes; isotonic remains a nonparametric benchmark but is higher-variance on small samples.
4. **Chronological/season-held-out validation.** nflfastR's public EP/WP work uses leave-one-season-out calibration and explicit out-of-sample checking rather than random leakage-prone splits.
5. **Sports forecast compositing.** FiveThirtyEight's sports systems historically combine ratings, player/QB state, rest/travel, and simulation while continuously checking predictive value; importantly, they document rejecting variables that did not add enough value.

## Optimization tournament

### Stage A — Rebuild the benchmark ladder

Freeze a reproducible benchmark table before adding candidates:

- market de-vigged probability
- current production F-ST probability
- pure non-market model
- Elo/SRS-style baseline
- simple logistic baseline using only durable pregame team-strength features

For every benchmark, publish season-by-season and aggregate Brier, log loss, calibration slope/intercept, reliability bins, accuracy, and bootstrap confidence intervals.

### Stage B — Candidate model inventory

Run candidates only through nested chronological folds, with all tuning inside each training window.

Candidate families:

- regularized logistic / elastic-net generalized linear models
- XGBoost, LightGBM, CatBoost, HistGradientBoosting
- ExtraTrees / RandomForest as diversity models, not assumed leaders
- monotonic-constrained gradient boosting where domain directionality is known and defensible
- NGBoost or equivalent distributional boosting for score-margin / total distributions
- Bayesian or shrinkage rating models for team-strength priors
- Glicko-2 / dynamic rating challengers against Elo
- calibrated neural/MLP challenger only if tabular/tree baselines are already saturated
- sequence models only if strict chronology, sample size, and incremental skill justify the added variance/complexity

Do not optimize on a single season. Require improvement across rolling-origin folds and reject candidates whose gain is concentrated in one regime.

### Stage C — Feature-family ablation

Evaluate additive families independently and jointly, always against the frozen benchmark ladder:

1. team efficiency and opponent-adjusted EPA
2. QB strength and starter uncertainty
3. all-position availability / expected lineup state
4. OL continuity, pressure/pass-protection matchup, pass-rush disruption
5. pace, early-down pass rate, motion/play-action/RPO/blitz/process features
6. rest, travel, timezone, altitude, international/neutral-site effects
7. weather and roof state
8. coaching/staff lineage and tactical change signals
9. point-in-time market state and movement horizons
10. special teams and field-position quality

Every family must have a preregistered inclusion criterion and a negative-control check where feasible.

### Stage D — Probability calibration tournament

Compare calibration layers fitted only on historical out-of-fold predictions:

- identity/no recalibration
- Platt/logistic scaling
- beta calibration
- isotonic regression
- calibration trees only as an experimental challenger

Select by proper-score improvement plus calibration diagnostics, not by visual smoothness. Prefer the simplest map whose gain is stable across folds. Never recalibrate on completed-2026 outcomes.

### Stage E — Ensemble and market fusion tournament

Generate leakage-safe OOF predictions for every surviving base model, then compare:

- arithmetic and logit-space weighted averages
- non-negative simplex weights
- regularized logistic stacking
- constrained stacking with explicit market/pure caps
- Bayesian model averaging / shrinkage weighting as a challenger
- regime-aware mixture-of-experts only if the gating rule is trained entirely inside historical folds and proves robust

A candidate ensemble must beat both the best individual model and the market benchmark on preregistered proper-score criteria or provide a clearly documented calibration/robustness advantage.

### Stage F — Distributional modeling

Move beyond win probability when evidence supports it:

- model home margin and game total as predictive distributions rather than independent point estimates
- derive moneyline/spread/total probabilities coherently from the same joint distribution
- compare Gaussian, Student-t, quantile, NGBoost/distributional boosting, and empirical residual simulation approaches
- score with CRPS/interval score in addition to point-error metrics
- verify that derived win probabilities remain calibrated

### Stage G — Uncertainty and decision usefulness

Add uncertainty without pretending it is certainty:

- bootstrap or fold-to-fold uncertainty around forecast skill
- prediction intervals for margin/total
- conformal prediction experiments for interval/set coverage where assumptions and sample size are adequate
- explicit source-freshness and lineup-uncertainty propagation
- disagreement decomposition: model vs market, model-vs-model, and data-state uncertainty

Do not convert uncertainty intervals into fake precision. The front end should communicate both the central forecast and what could move it.

## Preregistered selection gates

A candidate can advance from research to prospective shadow only when all are true:

- no integrity/firewall failures
- no completed-2026 outcomes used in selection
- statistically and practically credible proper-score gain versus the relevant baseline
- no material calibration degradation
- improvement is not driven by one season, one team, or one probability bucket
- bootstrap / paired uncertainty does not indicate a fragile or obviously noisy win
- complexity cost is justified by incremental predictive value
- inference is deterministic/reproducible enough for production operations

Promotion to production remains a separate decision after prospective evidence; no automatic promotion.

## Research implementation order

1. benchmark/evaluation harness hardening
2. calibration tournament
3. market-fusion/stacking tournament
4. availability/player-state improvements
5. process/tactical features
6. distributional margin/total model
7. travel/weather/rest refinements
8. uncertainty quantification and conformal challengers
9. automated model-card / ablation / robustness reporting
10. prospective shadow bake-off

## Model and algorithm inventory to audit

Open-source references to inspect or borrow patterns from, not blindly copy:

- nflverse / nflfastR model and calibration methodology
- FiveThirtyEight NFL Elo evaluation repository
- XGBoost
- LightGBM
- CatBoost
- scikit-learn HistGradientBoosting / calibration stack
- NGBoost
- MAPIE or other conformal-prediction tooling
- Optuna only inside leakage-safe nested folds if hyperparameter search cost is justified
- MLflow/DVC-style experiment/provenance patterns where they improve traceability without unnecessary infrastructure

Third-party NFL repositories may be useful for architecture ideas, but their reported performance is not evidence until independently reproduced under LevLine's chronology and leakage rules.

## Definition of optimization success

The goal is not a one-time leaderboard win. Success is a reproducible system that:

- produces calibrated probabilities that outperform simple and market benchmarks where possible
- knows when the market is stronger and does not force model contrarianism
- improves all-position context without hindsight
- remains stable across seasons and regime changes
- reports uncertainty and provenance honestly
- can be audited from raw source state to published probability
- converts model sophistication into clearer user understanding rather than more interface clutter

## References

- Gneiting, T. & Raftery, A. E. (2007). Strictly Proper Scoring Rules, Prediction, and Estimation. Journal of the American Statistical Association, 102(477), 359-378. DOI: 10.1198/016214506000001437.
- Wolpert, D. H. (1992). Stacked Generalization. Neural Networks, 5(2), 241-259. DOI: 10.1016/S0893-6080(05)80023-1.
- Kull, M., Silva Filho, T., & Flach, P. (2017). Beta calibration: a well-founded and easily implemented improvement on logistic calibration for binary classifiers. AISTATS / PMLR 54, 623-631.
- nflverse/open-source-football. nflfastR EP, WP, CP, xYAC, and xPass model documentation and LOSO calibration methodology.
- FiveThirtyEight. How Our NFL Predictions Work; fivethirtyeight/nfl-elo-game evaluation repository.
