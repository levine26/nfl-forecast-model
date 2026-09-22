# LevLine Adaptive Weekly Learning — Research Plan & Execution Ledger

Status: ACTIVE RESEARCH GOVERNANCE  
Repository: `levine26/nfl-forecast-model`  
Authoritative branch for this plan: `main`  
Primary objective: determine whether leakage-safe weekly learning can improve LevLine straight-up NFL winner accuracy beyond frozen `F-ST-01-FROZEN-2026` without degrading calibration, robustness, or scientific validity.

## 0. Non-negotiable governance

1. **Frozen incumbent remains untouched.** `F-ST-01-FROZEN-2026` is the production control. No 2026 outcome may alter its frozen coefficients, feature contract, decision rule, or historical accuracy record.
2. **No same-week leakage.** For Week t, every adaptive state, fit, calibration object, threshold, or switch decision may use only information available before the relevant forecast lock for Week t.
3. **No retrospective 2026 tuning.** Completed 2026 games before a challenger is frozen may be used only for descriptive diagnostics. They may not be used to design, tune, rescue, or select a challenger that later claims prospective evidence. A new or materially modified challenger starts a new prospective clock.
4. **Historical evidence is chronology-clean but not automatically independent proof.** 2022–2025 has already informed prior LevLine research. It may be used for engineering and pre-registered historical comparison, but prospective 2026 evidence is required for any claim of production superiority.
5. **Champion/challenger discipline.** Every adaptive candidate receives a stable candidate ID, frozen specification, code SHA, feature/data provenance, and prospective eligibility date.
6. **No promotion from a single metric.** Winner accuracy is primary. Brier, log loss, calibration, margin behavior, disagreement topology, and sample-size uncertainty are mandatory guardrails.
7. **No automatic production promotion.** Research may recommend promotion, but production F-ST changes require an explicit later decision.
8. **All lanes must read this file before work.** If a later prompt conflicts with this plan, amend this file explicitly before changing scientific scope.

## 1. Core research question

Can a constrained weekly adaptive layer improve the decision quality of frozen F-ST by learning from previously completed games while avoiding the instability seen in naive accuracy-driven retraining?

Primary estimand:

`delta_accuracy = accuracy(adaptive_challenger) - accuracy(frozen_FST)`

on exactly paired, chronologically eligible games.

Mechanism decomposition:

`delta_accuracy = disagreement_rate × (2 × switch_win_rate - 1)`

The adaptive system is expected to add value mainly through **fewer, better switches**, not broad replacement of incumbent picks.

## 2. Pre-registered candidate families

The research must test these candidate classes separately before testing hybrids.

### A. State-only dynamic updater
Update latent/team state without changing frozen F-ST coefficients:
- dynamic Elo/team-strength state;
- rolling and exponentially weighted offense/defense efficiency;
- QB/player availability state where point-in-time data are valid;
- uncertainty that expands after personnel/regime shocks and contracts with stable evidence.

### B. Online calibration layer
Pick-preserving calibration by default:
- intercept-only or low-dimensional calibration drift;
- strong shrinkage toward frozen calibration;
- no boundary crossing unless registered as a separate candidate.

### C. Bayesian / shrinkage adaptive residual layer
Sequentially learn residual structure with strong priors:
- prior centered at zero residual correction;
- limited dimensionality;
- adaptive learning rate tied to evidence of genuine regime change;
- decay / forgetting factor selected only inside chronology-safe training.

### D. Selective switch gate
Adaptive information may change a winner only when a predeclared gate is satisfied:
- incumbent probability near decision boundary;
- corroborating component disagreement;
- qualified player/QB shock;
- market movement / breadth if strict PIT data exist;
- latent state surprise exceeding training-defined thresholds.

### E. Full constrained hybrid
Combine A–D only after component ablations establish incremental value.

### Explicit negative control
Naive weekly full retraining on all accumulated current-season results. This is included because prior LevLine evidence suggests it may underperform and provides a falsification/control benchmark.

## 3. Parallel execution lanes

### Lane 1 — Data chronology & weekly replay infrastructure
Deliverables:
- canonical week-by-week replay frame;
- availability timestamps / source contracts;
- outcome cutoffs;
- exact pregame feature snapshots;
- tests proving Week t cannot see Week t outcomes;
- historical replay manifest.

### Lane 2 — Dynamic state / Bayesian updater
Deliverables:
- state transition specification;
- shrinkage priors;
- learning-rate / process-noise candidates;
- regime-shock logic;
- state-only challenger implementation;
- ablation tests.

### Lane 3 — Error audit & adaptive calibration
Deliverables:
- weekly forecast-error decomposition;
- calibration drift diagnostics;
- team/QB/personnel/market/error attribution fields;
- pick-preserving online calibrator;
- dashboard/CSV research outputs.

### Lane 4 — Selective decision replacement
Deliverables:
- disagreement-set engine;
- switch-gate candidate family;
- frozen threshold provenance;
- negative-control full-retraining challenger;
- exact switch-win accounting.

### Lane 5 — Scientific evaluation & governance
Deliverables:
- paired accuracy/Brier/log-loss evaluation;
- week-clustered uncertainty;
- McNemar / paired bootstrap or equivalent matched comparison;
- per-season stability;
- early/mid/late-season splits;
- favorite-strength / boundary stratification;
- promotion/no-promotion memo.

### Lane 6 — Literature / professional-practice synthesis
Deliverables:
- peer-reviewed and professional sources on dynamic team strength, state-space models, Bayesian updating, online learning, calibration drift, concept drift, and sports forecasting;
- explicit mapping from each borrowed idea to a LevLine candidate;
- no production changes from literature alone.

## 4. Historical replay protocol

### Historical window
Use the broadest chronology-clean sample supported by the existing pipeline, prioritizing 2018–2025 where feature/data quality is adequate. Report exact usable seasons and exclusions.

### Weekly simulation
For each target week:
1. instantiate only prior information;
2. fit/update candidate state using games completed before that week's lock;
3. generate candidate forecasts;
4. freeze those forecasts;
5. reveal outcomes;
6. grade;
7. update state for the next week.

No candidate may train on the target week's result before forecasting that week.

### Evaluation hierarchy
1. paired straight-up winner accuracy;
2. net correct winners gained/lost vs F-ST;
3. disagreement rate and switch win rate;
4. Brier score;
5. log loss;
6. calibration slope/intercept and reliability;
7. margin/total diagnostics where relevant;
8. season-to-season stability.

## 5. Candidate tuning rules

- Hyperparameters must be selected using nested chronology, earlier seasons, or a predeclared fixed grid.
- No threshold may be selected because it looks good on the same target period used to report performance.
- Candidate complexity must earn its inclusion through ablation.
- Prefer shrinkage, hierarchical partial pooling, and conservative learning rates.
- Current-season sample size alone is never sufficient justification for aggressive refitting.
- A parameter that changes rapidly requires a football/statistical explanation and stability evidence.

## 6. Statistical decision rules

Primary comparison is paired on the same games.

Report:
- number of paired games;
- incumbent correct;
- challenger correct;
- challenger-only correct;
- incumbent-only correct;
- raw accuracy delta;
- switch win rate;
- confidence interval / week-block bootstrap interval;
- McNemar-style paired significance where assumptions are acceptable;
- per-season deltas.

### Research success bands
These are planning bands, not promotion guarantees:
- **< 0.0 pp:** reject candidate;
- **0.0 to +0.25 pp:** practically unresolved / likely noise;
- **+0.25 to +0.75 pp:** promising;
- **+0.75 to +1.25 pp:** strong historical signal;
- **> +1.25 pp:** require extra leakage/overfit audit before believing result.

Any unusually large improvement triggers an adversarial leakage audit before interpretation.

## 7. Prospective 2026 protocol

When a candidate is frozen:
- record candidate ID, commit SHA, code/config digest, and start week;
- do not count any earlier 2026 games toward prospective proof;
- generate immutable pregame locks;
- grade only after completion;
- compare against frozen F-ST on exact paired games;
- material redesign resets the prospective clock.

Existing completed 2026 outcomes remain descriptive only for any candidate created after them.

## 8. Promotion criteria

A challenger may be recommended for production consideration only if:
1. historical walk-forward evidence is positive and season-stable;
2. no leakage or retrospective threshold selection is found;
3. prospective 2026 paired accuracy point estimate is positive;
4. switch set shows coherent football/statistical mechanism;
5. probability quality does not materially deteriorate;
6. gains are not concentrated in one week, one team, or one pathological subgroup;
7. robustness survives reasonable alternative learning rates / priors;
8. code, data, and evaluation artifacts are reproducible.

No automatic merge into production probability logic.

## 9. Required ablations

At minimum compare:
- frozen F-ST;
- state-only adaptation;
- calibration-only adaptation;
- residual-only adaptation;
- switch-gate only;
- state + calibration;
- state + residual;
- state + switch gate;
- full constrained hybrid;
- naive weekly full retraining negative control.

## 10. Error-audit schema

Each graded forecast should support:
- game/week;
- incumbent probability/pick;
- challenger probability/pick;
- market probability / line and timestamp where valid;
- actual result;
- probability error;
- Brier contribution;
- log-loss contribution;
- margin error;
- team-strength prior and posterior;
- offense/defense state change;
- QB/player-state shock;
- injury/availability source timestamp;
- model-component dispersion;
- market movement / breadth if PIT-qualified;
- regime-change score;
- whether a switch occurred;
- whether switch helped or hurt;
- reason code for the switch.

## 11. Stop conditions

Stop or quarantine a lane if:
- chronology cannot be proven;
- required PIT source timestamps are unavailable;
- a result depends on postgame or later-horizon information;
- candidate performance cannot be reproduced from committed artifacts;
- a candidate was changed after seeing target-period results without resetting its evaluation period.

## 12. Execution phases

### Phase 0 — Governance & preregistration
This file committed to GitHub. Create lane branches from the resulting main SHA.

### Phase 1 — Infrastructure in parallel
Lane 1 replay infrastructure + Lane 3 audit schema + Lane 6 literature synthesis.

### Phase 2 — Candidate implementation in parallel
Lane 2 dynamic state + Lane 3 calibration + Lane 4 switch/negative control.

### Phase 3 — Historical walk-forward experiment
Run all ablations on the exact common chronology-safe sample.

### Phase 4 — Adversarial validation
Leakage audit, sensitivity analysis, season stability, subgroup stability, reproducibility.

### Phase 5 — Freeze prospective challenger
Select candidate only from predeclared evidence, assign ID, freeze configuration, record SHA/start week.

### Phase 6 — Prospective operation
Run incumbent and challenger side-by-side with immutable locks.

### Phase 7 — Decision memo
Recommend retain / continue shadow / consider promotion based on evidence.

## 13. Project ledger

- [x] Phase 0 plan authored
- [ ] Lane 1 replay infrastructure
- [ ] Lane 2 dynamic state updater
- [ ] Lane 3 error audit + calibration
- [ ] Lane 4 switch gate + negative control
- [ ] Lane 5 evaluation framework
- [ ] Lane 6 literature synthesis
- [ ] Phase 3 historical replay complete
- [ ] Phase 4 adversarial validation complete
- [ ] Phase 5 challenger frozen
- [ ] Phase 6 prospective evidence accumulating
- [ ] Phase 7 decision memo

## 14. Initial quantitative prior

Before historical replay, the research prior is:
- frozen F-ST long-run accuracy baseline: approximately 68.2% on the established chronology-clean benchmark;
- expected properly constrained adaptive uplift: approximately +0.6 percentage points;
- expected adaptive accuracy: approximately 68.8%;
- approximate prior probability of positive uplift: 72%;
- naive full weekly retraining is expected to have negative value on average.

These numbers are priors to be updated by the preregistered historical experiment, not targets to optimize toward.

## 15. Amendment rule

If scope, metrics, candidate definitions, thresholds, or evidence rules change, update this page first with:
- date/time;
- reason;
- exact amendment;
- whether any candidate's prospective clock must reset.

This file is the authoritative anti-drift reference for the LevLine Adaptive Weekly Learning project.


## 16. Execution log — 2026-09-22 initial build

The following work was created from governance commit `aea40328a19a1be7b5bb43057dd182c5bab870b3` and integrated only into the research integration branch:

- Integration branch: `research/adaptive-weekly-learning-integration`
- Lane 1 PR #514 — chronology-safe weekly replay + leakage tests
- Lane 2 PR #515 — Bayesian-shrinkage residual team-state challenger + chronology test
- Lane 3 PR #516 — weekly error audit + L2-shrunk online intercept calibration + pick-preservation test
- Lane 4 PR #517 — selective switch gate + chronology-safe naive weekly F-ST refit negative control
- Lane 5 PR #518 — paired accuracy/Brier/log-loss evaluation + disagreement/McNemar accounting
- Lane 6 PR #519 — professional/peer-reviewed literature synthesis
- Dedicated integration workflow: `.github/workflows/research_adaptive_weekly_learning_v1.yml`
- Integrated research head after initial six lanes: `8f409560a5c0e534a0371a355a46336e01620e29`

All six lane PRs were merged into the research integration branch. None was merged into production `main`.

Current validation state at this log entry:
- repository research firewalls passed on the active code lanes checked so far;
- combined adaptive integration workflow is executing against the integrated research head;
- Phase 3 historical results are not yet recorded here and must be written back to this ledger after the workflow artifacts are verified.

The first empirical comparisons are deliberately:
1. frozen chronology-clean F-ST;
2. naive weekly F-ST refit;
3. Bayesian residual-state adaptation;
4. pick-preserving online calibration;
5. residual-state + conservative selective switch gate.

No threshold or hyperparameter is to be changed in response to those first results without recording a new candidate/version and the evidence boundary here.


## 17. Pre-result robustness grid — frozen 2026-09-22

This grid was recorded before the first integrated historical adaptive workflow produced results.

### Residual-state sensitivity grid

The fixed V1 candidate remains the primary first candidate:
- initial variance: 0.20
- process variance/week: 0.03
- weekly mean reversion: 0.97
- offseason mean reversion: 0.50
- max absolute residual state: 1.00 logit

Robustness-only grid:
- process variance/week: [0.01, 0.03, 0.06]
- weekly mean reversion: [0.90, 0.97, 1.00]
- offseason mean reversion: [0.25, 0.50, 0.75]

The 27 combinations must be reported as sensitivity evidence. The best full-sample 2022–2025 combination may **not** be promoted as a new candidate merely because it wins retrospectively.

### Selective-gate sensitivity grid

Primary V1 gate remains:
- incumbent boundary distance: 0.075 probability
- minimum adaptive shift: 0.035 probability

Robustness-only grid:
- boundary distance: [0.05, 0.075, 0.10]
- minimum adaptive shift: [0.02, 0.035, 0.05]

Again, the full-sample best combination is descriptive only.

### Permitted nested selection diagnostic

A separate diagnostic may select among the predeclared grid using only chronologically earlier seasons and then score a later season. It must label the training seasons and target season explicitly. No target season may influence its own parameter choice.

This grid is a robustness / falsification device, not authorization for post-result parameter rescue.


## 18. Pre-result adversarial validation rules — frozen 2026-09-22

These checks were specified before the first integrated historical result was interpreted.

For any candidate with a positive full-sample accuracy delta:

1. **Season sign stability:** report the accuracy delta in every target season. A gain concentrated in one season is not sufficient evidence of a generally useful adaptive mechanism.
2. **Week concentration:** report net correct switches by season-week. If one week accounts for more than 50% of the total positive net gain, label the result concentration-sensitive.
3. **Team concentration:** attribute each switch to both participating teams. If a small set of teams dominates the gain, report that explicitly and do not generalize the mechanism without further validation.
4. **Probability guardrail:** positive winner accuracy may not hide a material deterioration in both Brier and log loss. Any such tradeoff requires a separate candidate rationale.
5. **Grid robustness:** report the complete preregistered residual-state and switch-gate grids. The primary V1 remains the primary candidate regardless of which retrospective cell is best.
6. **Nested chronology diagnostic:** parameter selection for a target season may use only earlier target seasons. The target season's outcomes may not choose its own configuration.
7. **Baseline reproduction:** the common frozen F-ST benchmark must reproduce 741/1,087 correct on the established 2022–2025 sample where applicable. Failure invalidates the comparison.
8. **Leakage assertions:** same-week outcome-use flags must remain false for every scored game.
9. **Large-gain skepticism:** any full-sample uplift above +1.25 percentage points receives an explicit leakage/selection audit before substantive interpretation.
10. **No hindsight rescue:** a failed V1 may motivate a newly registered V2 theory, but V1 parameters may not be edited and re-described as if they were the original candidate.

These are interpretation rules, not automatic production-promotion criteria.


## 19. Candidate 1 checkpoint — completed 2026-09-22

Validated workflow run: `35742825363`  
Validated integration SHA: `2bf1077a8adb5121aadf64b8f0bbfc7538fe00c4`  
Evidence artifact: `10699993670`  
Full receipt: `research/ADAPTIVE_WEEKLY_LEARNING_FIRST_RUN_RECEIPT.json`

### Incumbent benchmark
- Frozen F-ST: 741 / 1,087 correct
- Accuracy: 68.1693%
- Brier: 0.2106533
- Log loss: 0.6087126

### Candidate 1 — ADAPTIVE-RESIDUAL-STATE-V1
- Correct: 722 / 1,087
- Accuracy: 66.4213%
- Delta vs F-ST: **-1.7479 percentage points**
- Brier: 0.2163569 (worse)
- Log loss: 0.6226563 (worse)
- Winner switches vs F-ST: 121
- Candidate-only correct: 51
- F-ST-only correct: 70
- Switch win rate: 42.15%
- Exact paired McNemar diagnostic p: 0.1014

By-season accuracy delta:
- 2022: -1.8450 pp
- 2023: -3.6765 pp
- 2024: -2.5735 pp
- 2025: +1.1029 pp

**Disposition: REJECT Candidate 1.**

### Negative control — weekly full F-ST refit
- Correct: 739 / 1,087
- Accuracy: 67.9853%
- Delta vs frozen F-ST: **-0.1840 pp**
- Only 6 winner switches; weekly refit won 2 and F-ST won 4.

**Conclusion:** simple weekly retraining does not improve winner accuracy.

### Calibration ablation
The pick-preserving weekly calibration layer kept all 741 winners unchanged while slightly improving probability quality:
- Accuracy delta: 0.0000 pp
- Brier delta: -0.0000846
- Log-loss delta: -0.0000847

This is worth retaining as a probability-calibration research component, but it does not increase straight-up winner accuracy.

### Selective gate on Candidate 1
- Correct: 738 / 1,087
- Accuracy: 67.8933%
- Delta vs F-ST: -0.2760 pp
- 79 authorized switches
- Switch win rate: 48.10%

**Disposition: REJECT Candidate 1 gate.**

### Robustness result
The preregistered nested chronology-safe parameter-selection diagnostic also failed:
- F-ST: 559 / 816
- Adaptive: 549 / 816
- Delta: -1.2255 pp
- Switch win rate: 36.84%

This means the result is not credibly rescued by choosing different parameters from the preregistered residual-state grid.

### Scientific checkpoint
The initial research prior of approximately +0.6 pp for generic controlled weekly residual learning is **not supported by Candidate 1**. Candidate 1 is frozen as a failed experiment and must not be retuned and relabeled as the same candidate.

Any Candidate 2 must use a materially different pregame-observable information mechanism rather than simply retuning the residual-state learner.

### Ledger update
- [x] Candidate 1 historical walk-forward experiment
- [x] Candidate 1 preregistered robustness analysis
- [x] Candidate 1 rejected
- [ ] Candidate 2 theory/design — intentionally paused pending user direction

## 20. Candidate 2 Pre-Registration — frozen 2026-09-22

Status: **PRE-RESULT / RESEARCH ONLY / NO PRODUCTION CHANGE**

Candidate ID: `ADAPTIVE-REGIME-SHOCK-GATE-V1`

This section was frozen before Candidate 2 target-period winner results were inspected or generated. It is a materially different hypothesis from rejected `ADAPTIVE-RESIDUAL-STATE-V1`: Candidate 2 does not learn persistence from prior forecast errors and does not weekly-refit F-ST.

### 20.1 Hypothesis

Frozen F-ST may become locally stale when the pregame personnel state changes abruptly. A component-resolved football challenger may contain useful directional information on a small subset of near-boundary games, but prior LevLine research shows component disagreement alone is insufficient for promotion. Candidate 2 therefore asks whether a separately observed, point-in-time personnel regime shock can identify the subset of F-ST/component disagreements where preserving the frozen incumbent is less reliable.

The primary estimand remains paired straight-up winner accuracy versus frozen F-ST.

### 20.2 Primary architecture

Candidate 2 is an incumbent-preserving selective winner-switch gate.

For every eligible 2025 game:

1. reconstruct the chronology-clean frozen F-ST probability without changing F-ST coefficients or production code;
2. reconstruct the already-established component-resolved L2 challenger from market logit plus the four base-model logits (`logistic`, `extra_trees`, `xgboost`, `catboost`) using only seasons strictly before the 2025 target season;
3. preserve the F-ST winner unless all three conditions below are true:
   - **boundary condition:** `abs(P_FST - 0.5) <= 0.075`;
   - **directional disagreement:** the component-resolved challenger selects the opposite winner from F-ST;
   - **orthogonal regime-shock condition:** a qualified T-120 personnel-state signal indicates a material state discontinuity.
4. when all conditions are satisfied, use the component-resolved challenger probability/pick; otherwise retain the F-ST probability/pick.

The regime signal determines whether a switch is permitted, not the direction of the switch. Direction comes only from the separately reconstructed component-resolved challenger. This prevents arbitrary injury-point assignment.

### 20.3 Primary regime-shock definition

A game satisfies the primary strong-shock gate when, using only state known at or before T-120, at least one team has any of:

- `QB1 change == 1` relative to that team's prior game under the qualified 2025 depth-chart state contract;
- at least **2** new rank-1 offensive-line identities relative to that team's prior game;
- current rank-1 QB final-practice status equal to **DNP**, joined by stable GSIS identity to the qualified 2025 practice-state reconstruction.

Unknown, ambiguous, missing, or non-qualified state never becomes a shock by imputation. It simply cannot authorize a switch. Week-1/no-prior-team-state rows therefore default to F-ST unless another independently observable primary shock is valid.

The primary definition is intentionally sparse. Defensive churn, generic injury counts, RB/WR/TE injury counts, role-weighted player values, coaching/scheme labels, weather, rest, travel and reputation are not part of Candidate 2 V1.

### 20.4 Allowable data/features

Allowable V1 inputs are limited to:

- chronology-clean F-ST probability/pick from the established keyed provenance frame;
- historical base-model OOF probabilities from `challenger_outputs/fst/provenance/base_oof_keyed.csv`;
- the four component probabilities listed above and their predeclared L2 season-forward stack;
- 2025 T-120 depth-chart state under `DEPTH-STATE-01`: QB1 identity/change, rank-1 OL new-count/continuity, source timestamp, missingness and stable-ID coverage;
- qualified 2025 practice state from `availability_2025_composite_reconstruction`, restricted to practice status and stable identity proven known by T-120;
- game/season/week/team identity and kickoff clock needed for chronology;
- target outcome only after the candidate prediction for that row has been deterministically generated and frozen inside the historical replay.

### 20.5 Explicitly excluded from V1

The following may be studied descriptively or prospectively but may not enter Candidate 2 V1:

- completed 2026 outcomes of any kind;
- T-60/T-45/T-30 or closing-market information in a T-120 historical candidate;
- reconstructed historical market paths where exact PIT request state did not exist;
- 2026 prospective component, injury, depth-chart or beat-state captures;
- final game-day inactive status learned after T-120;
- actual snaps, participation, final starter identity learned after the decision horizon, or postgame roster knowledge;
- unqualified 2022-2024 injury/availability reconstructions;
- numeric editorial injury points or hand-assigned player values;
- generic PURE upset overrides or football unanimity overrides;
- score/margin disagreement as an independent corroborating channel;
- team identity, team reputation, prior Candidate 1 residual state, prior forecast errors, or weekly F-ST refit state;
- coaching/scheme/news-text labels without an equivalent frozen PIT historical contract;
- rest, travel, circadian and weather features in V1.

### 20.6 Historical sample and missingness

Primary target season: **2025 only**.

Reason: the repository currently qualifies equivalent T-120 depth-chart and practice-state evidence for 2025, but does not authorize a unified 2022-2025 availability reconstruction or retrospective strict multi-horizon market path. Candidate 2 will not manufacture cross-season state merely to preserve the 1,087-game sample.

The candidate is scored on every 2025 row for which the frozen F-ST and component-resolved probabilities can be reconstructed. Missing/ambiguous personnel evidence is fail-closed: Candidate 2 equals F-ST on that row. Reports must separately disclose:

- exact total paired games;
- games with both-team depth state;
- games with evaluable QB-change state;
- games with evaluable OL-change state;
- games with qualified QB practice-state join;
- games satisfying the strong-shock gate;
- rows preserved solely because state was unknown.

F-ST, market, Candidate 1, weekly-refit control, component-only control and Candidate 2 must be compared on the exact same Candidate 2 paired rows when a row-level comparator exists. No full-1,087 benchmark may be presented as the causal comparator to a smaller Candidate 2 sample.

### 20.7 Frozen parameter / robustness grid

**Primary V1**:
- F-ST boundary distance: **0.075**;
- OL new rank-1 threshold: **2**;
- QB practice shock: **DNP only**;
- component stack L2 logistic: `C=1.0`, `lbfgs`, same four component logits plus market logit, season-forward fit;
- no learned cross-channel shock weight;
- no tree search;
- no target-period threshold optimization.

**Preregistered robustness-only grid**:
- boundary distance: `[0.05, 0.075, 0.10]`;
- OL new rank-1 threshold: `[1, 2, 3]`;
- QB practice definition: `[DNP_only, DNP_or_limited]`.

The full grid is descriptive falsification evidence only. The primary V1 remains the primary candidate regardless of which retrospective cell is best. No best 2025 cell may be promoted or relabeled as V1.

### 20.8 Controls / ablations

Mandatory 2025 paired controls:

- frozen F-ST;
- raw market;
- Candidate 1 `ADAPTIVE-RESIDUAL-STATE-V1` unchanged;
- `NAIVE-WEEKLY-FST-REFIT-CONTROL-V1` unchanged;
- component-resolved challenger without the regime gate;
- boundary + component disagreement without a regime-shock requirement;
- shock gate with QB-change channel removed;
- shock gate with OL-churn channel removed;
- shock gate with QB-practice channel removed, if the qualified join is available.

Ablations diagnose mechanism. They may not be used to rewrite V1 after target outcomes are seen.

### 20.9 Evaluation metrics

Primary:
- straight-up winner accuracy;
- absolute correct winners;
- accuracy delta versus F-ST on identical rows.

Mandatory secondary:
- Brier score and delta;
- log loss and delta;
- calibration/reliability summary;
- disagreements and disagreement rate;
- candidate-only correct;
- incumbent-only correct;
- net winners gained;
- switch win rate;
- exact paired McNemar diagnostic;
- week-block bootstrap interval;
- week-by-week results;
- regular-season/postseason split if sample permits;
- F-ST confidence/boundary buckets;
- market-probability buckets;
- shock-channel attribution.

Because Candidate 2 V1 has one historical target season, "season stability" is structurally not estimable for the regime features. This limitation must be explicit and materially lowers evidentiary weight even if the point estimate is positive.

### 20.10 Adversarial validation

If V1 is positive, attempt to falsify it by checking:

- source timestamp leakage and any post-T120 state;
- dependence on one week;
- dependence on one team;
- dependence on one switch;
- dependence on QB-only, OL-only or practice-only shocks;
- boundary sensitivity across the preregistered grid;
- OL-threshold sensitivity across the preregistered grid;
- DNP-only versus DNP-or-limited sensitivity;
- component-only versus shock-gated contribution;
- early/mid/late 2025;
- favorites versus underdogs;
- F-ST confidence and market-probability buckets;
- regular season versus postseason;
- missingness/coverage topology.

A positive result that vanishes under reasonable preregistered perturbation is not robust.

### 20.11 Success and stop criteria

Interpret the primary V1 accuracy delta using the project bands:
- <= 0 pp: **REJECT**;
- >0 to +0.25 pp: **INCONCLUSIVE**;
- +0.25 to +0.75 pp: **PROMISING** only if switch mechanism is coherent;
- +0.75 to +1.25 pp: **strong historical point signal**, still limited by one-season regime-data coverage;
- > +1.25 pp: trigger aggressive leakage/selection audit before substantive belief.

Regardless of point estimate, Candidate 2 cannot be called historically season-stable because its qualified regime-state sample is 2025-only. Prospective shadow testing may be recommended only if V1 is positive, PIT-clean, mechanism-coherent and not concentrated in a pathological subgroup.

Stop immediately if source chronology cannot be proven, the component reconstruction fails to reproduce the registered historical component result within deterministic tolerance, stable-ID practice joins are ambiguous, or any 2026 completed outcome enters feature/threshold/candidate selection.

### 20.12 Lane assignments

- **Lane A — evidence/mechanism:** update literature/professional-practice synthesis for event-driven state change, market information incorporation, QB leverage, sparse dynamic models and David Sasser; distinguish conceptual support from implementation evidence.
- **Lane B — PIT audit:** create a feature-availability matrix classifying every requested signal family as fully PIT valid, partially PIT valid, unavailable historically, or prospective-only; verify exact source hashes/timestamps and common-sample eligibility.
- **Lane C — model:** implement `ADAPTIVE-REGIME-SHOCK-GATE-V1` and deterministic component reconstruction, with tests for fail-closed missingness and no target leakage.
- **Lane D — evaluation:** reuse the established paired adaptive framework and add exact Candidate 2 controls/coverage/shock attribution.
- **Lane E — adversarial:** execute the frozen robustness grid, concentration diagnostics, channel ablations and reproducibility receipt.

### 20.13 Branch / production policy

Candidate 2 implementation must live on a dedicated Candidate 2 research integration branch plus lane branches created from the synchronized Candidate 2 preregistration base. Production F-ST, production probabilities, site outputs and production workflows remain unchanged. Candidate 2 may not be prospectively deployed or merged into production without a separate user decision after the completed report.

### 20.14 External-evidence rationale frozen with this preregistration

External evidence is supportive but not outcome-selective:

- dynamic sports models justify time-varying latent strength and stronger adaptation around real structural changes, but Candidate 1 directly rejects generic outcome-residual adaptation for LevLine;
- recent sparse Bayesian dynamic Bradley-Terry work supports strong shrinkage in stable periods and diffuse innovation only around credible changes;
- NFL player-value research using sportsbook point-spread values finds QB value dominates other player positions, supporting QB state as a high-leverage regime indicator rather than arbitrary injury points;
- NFL betting-line research indicates information content generally increases during the week, supporting market movement as a plausible information channel, but the repository lacks an equivalent historical strict-PIT multi-book path for Candidate 2 V1;
- David Sasser's public board exposes model projection beside open/current market state, supporting disciplined model-versus-market comparison, but does not disclose a weekly update algorithm and is not treated as evidence for one.

### 20.15 Candidate 2 execution ledger

- [x] Candidate 2 theory materially separated from Candidate 1
- [x] Candidate 2 pre-registration frozen before target-result generation
- [ ] Candidate 2 synchronized research integration base created
- [ ] Lane A evidence complete
- [ ] Lane B PIT audit complete
- [ ] Lane C implementation complete
- [ ] Lane D historical evaluation complete
- [ ] Lane E adversarial validation complete
- [ ] Candidate 2 final receipt and disposition recorded

