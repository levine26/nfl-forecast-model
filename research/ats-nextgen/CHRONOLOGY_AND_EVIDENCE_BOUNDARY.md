# Chronology & Evidence Boundary

## 1. Historical evidence classification

Seasons 2022–2025 are **development / non-pristine** for this ATS family because LevLine has already inspected them repeatedly in prior score, margin, market and winner research.

They remain useful for:

- chronology-clean OOF comparison;
- representation/mechanism tests;
- probability calibration diagnostics;
- key-number/distribution diagnostics;
- bounded candidate comparison.

They are not untouched confirmation and cannot by themselves authorize production.

## 2. Completed-2026 firewall

Completed 2026 outcomes are prohibited from:

- Q1/Q2/Q3 architecture;
- feature inclusion/exclusion;
- quantile choice;
- distribution-family choice;
- base-shape selection outside frozen grids;
- key-number choice/parameter fitting for historical targets;
- direct-ATS learner choice;
- probability calibration;
- ATS threshold/selectivity choice;
- Q2/Q3 blend grid or weight selection;
- retrospective rescue/survival decisions.

Outcome-blind live 2026 inputs may be inspected to determine whether a market/data provider exposes a field with adequate timestamp/provenance. That source qualification is not performance evidence.

## 3. Primary historical training floor

Q1–Q3 V1 use **2015** as the primary training floor. Rationale:

- preserves a substantial sample before 2022 outer evaluation;
- aligns the main distribution estimation with the modern extra-point era;
- reduces avoidable key-number/scoring-regime nonstationarity.

Older seasons may be used only in an explicitly labeled structural sensitivity that does not change V1 parameters or survival decisions.

## 4. Outer expanding-window evaluation

Outer target seasons are exactly:

`2022, 2023, 2024, 2025`.

For outer target season `s`:

- eligible training rows are seasons 2015 through `s-1`;
- no target-season outcome contributes to model coefficients, hyperparameters, key mass, scale, preprocessing or blend selection;
- the full target season is scored from the frozen prior-time fit.

This season-level contract is the primary Phase-2 historical development protocol. Random K-fold is prohibited.

## 5. Inner rolling-origin tuning

For each outer target season `s`, inner validation targets are prior seasons from `2019` through `s-1`.

For each inner target `t`, fit only 2015 through `t-1` and score `t`.

Use these inner OOF rows for:

- Q1 alpha selection by pinball loss;
- Q2 distribution-shape/scale/key shrinkage selection by proper distribution score;
- Q3 L2 C selection by multinomial log loss;
- Q2/Q3 blend weight selection by multinomial log loss.

If an inner target lacks enough eligible rows for a submodel, fail closed and record it; do not replace the fold with random CV.

## 6. Preprocessing chronology

For every fit:

- medians/imputation values are derived only from training rows;
- scalers are fit only on training rows;
- optional missingness indicators are determined by the frozen feature contract, not target-period performance;
- no same-row or same-target-season calibration is allowed.

## 7. Football-state chronology

Existing core team-state values must remain shifted before rolling so the target game's PBP/result never enters its pregame row. Elo must remain pregame/sequential.

Final historical QB IDs, realized snaps, final inactives, realized weather and later-corrected roster/depth information are prohibited from V1.

## 8. Market chronology

Historical schedule market fields retain the fixed label:

`historical_closing_late_benchmark_exact_horizon_opaque`.

They may not be relabeled T-120/open/close/book-specific.

Prospective T-120 evidence must come from timestamped LevLine snapshots selected by the existing <= kickoff-minus-120 rule. Later market snapshots may not define earlier consensus/price.

## 9. Probability calibration chronology

V1 authorizes no post-hoc calibrator. If a future version adds one, it must be fit only on earlier OOF probabilities and frozen before scoring the next target period.

## 10. Prospective requirement

A Phase-3 survivor starts a new prospective shadow clock. Only forecasts frozen after the candidate identity/config/code hash is recorded count as prospective evidence. Earlier completed 2026 games cannot be backfilled into that proof.

## 11. Repeated-use disclosure

Every Phase-2/3 report must state prominently:

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.

This sentence may not be removed to make a result appear stronger.