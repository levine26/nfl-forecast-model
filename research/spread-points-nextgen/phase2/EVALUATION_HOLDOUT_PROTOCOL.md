# Phase 2 — Frozen Evaluation and Holdout Protocol

**Status:** FROZEN before Phase 3 challenger results  
**Purpose:** prevent hindsight, fold contamination and post-hoc model rescue.

---

# 1. Targets and orientation

Use Phase 1 canonical conventions:

- actual margin = home score - away score;
- actual total = home score + away score;
- positive historical `spread_line` = market-implied home margin;
- projected home points = (total + margin)/2;
- projected away points = (total - margin)/2.

Market and football-only models remain separate labeled families.

---

# 2. Historical information firewall

## Completed 2026 outcomes

**Zero completed-2026 outcomes may be used for:**

- challenger architecture selection;
- feature selection;
- hyperparameter selection;
- threshold selection;
- ensemble weights;
- error-bucket rule design.

2026 is forward/prospective evidence only.

## 2025 final challenger holdout

2025 is frozen as the final historical challenger holdout.

Important limitation: Phase 1 already inspected **baseline** 2025 errors and used those failures to formulate broad research questions. Therefore 2025 is not a pristine never-seen season in the philosophical sense.

Nevertheless, from this Phase 2 freeze forward:

- no Challenger A/B/C 2025 outputs may be inspected during Phase 3 development;
- no challenger parameter may be chosen using 2025 challenger performance;
- the final 2025 challenger evaluation occurs only in Phase 4 after candidate identities are frozen.

The distinction must be disclosed in every final report.

---

# 3. Development chronology

## Core development target seasons

Phase 3 development comparisons should use rolling-origin outer forecasts ending no later than 2024.

For modern-feature families whose data begin in 2022:

- outer target 2022: train only on earlier qualified seasons;
- outer target 2023: train through 2022;
- outer target 2024: train through 2023.

For Core/history-only structures with older coverage, earlier target seasons may be added to stabilize inner selection, but the modern 2022–2024 summary remains mandatory.

## Deterministic inner tuning

Every hyperparameter, regularization strength, decay parameter and combination weight must be selected using data **strictly earlier than the outer test season**.

For each outer target season `Y` in **2022, 2023, 2024**:

1. determine the candidate's earliest season with complete required feature coverage;
2. create expanding-window inner folds with validation season `V < Y` and training seasons strictly before `V`;
3. an inner fold is valid only when at least **two complete prior training seasons** exist;
4. use the **latest four valid inner validation seasons**, or all valid seasons when fewer than three exist;
5. if fewer than **two** valid inner validation seasons exist, do not tune from data; use the fixed candidate fallback in `BOUNDED_IMPLEMENTATION_SPEC.md`;
6. fit every scaler, imputer, latent-state initialization, residual variance/covariance estimate and other learned preprocessing object on the inner training portion only;
7. after choosing the hyperparameter setting, refit on all eligible data strictly before `Y` and emit the outer `Y` predictions.

No meta-model may be trained on the same OOF rows on which it is reported. No later season may be borrowed to make an early-season tuning problem easier.

### Frozen tuning objectives

Hyperparameter choice is lexicographic and candidate-specific:

- **A:** minimize average team-points MAE, `(home_MAE + away_MAE)/2`; tie-break by margin MAE, then total MAE.
- **B drive-count component:** minimize mean inner-fold Poisson deviance.
- **B drive-outcome component:** minimize mean inner-fold multinomial log loss. The simulator has no additional free tuning parameter.
- **C-margin:** minimize hybrid margin MAE.
- **C-total:** minimize hybrid total MAE.
- **D:** no free hyperparameter search beyond the convex weights and the explicit eligibility gate.

For an exact tie at displayed precision, select the more regularized/simpler setting. Metric switching after seeing results is prohibited.

---

# 4. Candidate identity freeze

Before the 2025 holdout is scored, each surviving candidate must have a frozen identity containing:

- feature schema;
- data-source contract;
- transformation code;
- hyperparameters;
- training-window policy;
- missingness behavior;
- probability/distribution transform;
- market horizon family;
- source-code commit SHA.

Any material change after 2025 is first inspected creates a **new candidate identity** and cannot reuse the old holdout result as if it were untouched.

---

# 5. Primary football metrics

For every exact paired game:

## Team scores

- home points MAE;
- home points RMSE;
- away points MAE;
- away points RMSE.

## Margin

- MAE;
- RMSE;
- mean signed error;
- residual SD.

## Total

- MAE;
- RMSE;
- mean signed error;
- residual SD.

Football-only challengers are selected primarily on these football metrics, not ATS.

---

# 6. Distribution metrics

When a candidate emits a predictive distribution, report:

- 50% and 80% interval coverage;
- average interval width;
- CRPS for univariate margin and total when feasible;
- log score / likelihood only where the distribution is sufficiently specified and numerically stable;
- joint energy score or an explicitly justified equivalent for home/away score simulations where feasible.

Calibration and sharpness must be reported together.

A narrow but under-covering distribution is not considered superior.

---

# 7. Winner/probability metrics

Secondary score-model outputs:

- home-win probability Brier;
- log loss;
- straight-up accuracy;
- tie-excluded sensitivity.

These do not replace the official frozen F-ST production accountability record and cannot be used to quietly redefine the score-model objective.

---

# 8. Market-relative metrics

On exact paired rows:

- model margin MAE versus market spread MAE;
- model total MAE versus market total MAE;
- paired per-game absolute-error delta;
- mean residual around market;
- residual variance;
- model-vs-market closer rate.

Use season+week block bootstrap for important paired differences.

Historical schedule market results are labeled **closing/late benchmark** unless a timestamped horizon is proven.

T-120 comparison requires T-120 market receipts.

---

# 9. ATS / O-U policy

ATS and O/U are secondary diagnostics only.

Report:

- ATS hit rate excluding pushes/no-edge;
- cover-probability Brier;
- over-probability Brier;
- fixed predeclared edge buckets if relevant.

Do not:

- tune edge thresholds on the evaluation sample;
- select a challenger solely because ATS > 50%;
- use a tiny high-edge slice to override worse continuous error.

---

# 10. Predeclared diagnostic slices

Use fixed Phase 1-compatible bins:

### Favorite size, absolute market home margin
- [0,3)
- [3,7)
- [7,10)
- [10,14)
- 14+

### Market total
- <42
- 42–45
- 45–48
- 48+

### Season segment
- Weeks 1–4
- Weeks 5–9
- Weeks 10–14
- Weeks 15+

### Model-market disagreement
- <2
- 2–4
- 4–6
- 6–8
- 8+

### Realized blowout diagnostics only
- abs margin >=14
- >=21
- >=28

Realized blowout groups are descriptive failure analysis, not pregame selection gates.

---

# 11. Missing-data policy

Fail closed for externally sourced state:

- missing injury != healthy;
- missing starter != stable;
- missing weather forecast != normal weather;
- failed market collector != no movement.

Model-internal numeric imputation must be fixed in candidate identity and cannot vary from test row to test row based on future data.

---

# 12. Statistical uncertainty

Primary paired comparisons use:

- exact common games;
- season+week block bootstrap;
- at least 10,000 resamples for final Phase 4 comparisons unless computationally prohibitive;
- confidence intervals for paired MAE/RMSE or proper-score differences.

Report seasonal signs separately.

A tiny average improvement driven by one season is not robust evidence. Energy score is supplementary for the joint distribution and is not a sole selector because multivariate proper scores can have limited finite-sample discrimination for some dependency errors.

---

# 13. Complexity gate

The mandatory reference identities are A0, B0 and C0 only. A1/C1 are deferred and cannot be activated as outcome-dependent rescues.

For any future preregistered extension, if a simple regularized model ties a complex model within uncertainty, prefer the simpler model.

---

# 14. Phase 3 -> Phase 4 gate

A/B/C are a small preregistered confirmatory set. **Weak 2022–2024 development performance alone does not authorize deleting a valid A/B/C candidate before the holdout.** This prevents a second layer of candidate shopping after the shortlist is already frozen.

Before final 2025 scoring, each A/B/C candidate must:

1. be reproducible;
2. pass PIT/source checks;
3. conform to the bounded implementation specification;
4. have a frozen identity;
5. preserve the 2026 selection firewall;
6. emit finite, valid predictions on its required development universe.

A candidate may be declared **invalid** before Phase 4 only for a methodological/engineering defect such as PIT failure, unreproducible identity, specification violation, irreparable numerical failure, or inability to produce the preregistered target. Invalidity must be logged with the defect; it may not be a euphemism for poor MAE.

All valid A/B/C candidates proceed to the one-time 2025 Phase 4 evaluation.

D is the only component whose existence is development-gated; its objective gate is frozen in `BOUNDED_IMPLEMENTATION_SPEC.md`.

---

# 15. Paired-comparison discipline

All development and holdout comparisons use exact common games for the models being compared.

- A football-only candidate versus the current football-only baseline uses the common score-model game set.
- C0 versus market uses only rows with the same historical market field present.
- Missing external state is never imputed to enlarge a paired benchmark.
- The game inclusion ledger is frozen before metrics are summarized.

# 15A. Objective D eligibility gate

D is target-specific. Margin and total are evaluated independently.

D exists for a target only if all four conditions hold on common 2022–2024 outer-OOF rows:

1. at least two eligible component error series have **absolute Pearson correlation <= 0.90**;
2. the nested nonnegative convex blend has lower pooled target MAE than the best single component;
3. the blend's MAE improvement has the same sign in at least **two of the three** outer seasons;
4. season+week block-bootstrap probability that the blend has lower MAE than the best component is **>= 0.75**.

If any condition fails, record `ENSEMBLE_NOT_ELIGIBLE` for that target. No alternate stacker or gate may be searched.


# 16. Phase 4 final-holdout interpretation

The 2025 result is the final historical challenger holdout under this program.

It must be reported even if unfavorable.

No 2025-based rescue retuning is permitted under the same candidate identity.

After Phase 4, any surviving candidate still requires prospective Phase 5 evidence before production consideration.

# 17. Holdout red-team decision

No more defensible pre-2026 historical holdout is available without either reusing seasons already central to architecture development or abandoning the historical holdout and waiting exclusively for future prospective evidence.

Keeping 2025 is therefore the least-bad transparent design because no A/B/C challenger outputs have been inspected yet. The limitation that Phase 1 inspected baseline 2025 errors remains mandatory disclosure. This design is **not** equivalent to a philosophically pristine untouched season, and Phase 5 prospective evidence remains necessary before promotion.
