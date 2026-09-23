# Chronology and Evidence Boundary

Status: FROZEN BEFORE RESULTS

## 1. Evidence classes inside LevLine

### Fixed prior evidence

All Spread & Points Next-Generation findings through Phase 5 are accepted as prior evidence. They constrain this program and cannot be rescued/reopened by relabeling.

### Development evidence

Seasons 2022–2025 are development/non-pristine for the ATS family because LevLine has already inspected them repeatedly in adjacent research. They may reject mechanisms and quantify calibration, but a positive result cannot authorize production.

### Future confirmation

A candidate classified `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` in Phase 3 requires a separately authorized future Phase 4 using frozen prospective predictions. Phase 4 does not start automatically.

## 2. Modern-era data floor

V1 uses regular seasons 2015 onward. The 2015 extra-point rule change is the preregistered scoring-regime boundary because Q2 models discrete key-number mass.

Pre-2015 observations are excluded from V1 fitting/evaluation. This exclusion is fixed before Q1-Q3 performance exists.

## 3. Outer development folds

Exactly four outer folds:

- train/tune on prior history -> evaluate 2022;
- prior history -> evaluate 2023;
- prior history -> evaluate 2024;
- prior history -> evaluate 2025.

The outer season is never used to select features, hyperparameters, distribution family, calibration, blend weights or thresholds.

## 4. Inner rolling-origin folds

For outer season Y, inner validation seasons are every season `t` from 2019 through `Y-1`.

Each inner fold:

- trains on 2015 through `t-1`;
- computes all train-derived preprocessing/parameters using only that history;
- predicts season `t` once;
- saves OOF predictions and scores.

Configuration selection pools those inner OOF predictions with **equal weight per validation season**, not proportional weight by game count.

After selection, the chosen specification is refit on 2015 through `Y-1` and applied once to outer Y.

## 5. Nested dependency rule

Later models cannot consume in-sample upstream predictions.

- Q2 may consume only Q1 predictions generated OOF/forward for the same row.
- Q3 may consume only Q1/Q2 predictions generated OOF/forward for the same row.
- Q3 calibration may use only prior inner OOF logits/probabilities.
- Q2/Q3 blend selection may use only prior inner OOF component probabilities.

When refitting for an outer season, upstream models are fit on all prior eligible data under their already-selected prior-time specification, then predict the outer rows. No outer labels flow upstream.

## 6. Probability calibration chronology

Calibration is itself model fitting.

For outer Y, a calibrator may only be learned from OOF predictions/labels belonging to seasons earlier than Y. Same-row or outer-season calibration is prohibited.

No target-season calibration intercept/slope may be used to adjust predictions; those quantities are evaluation diagnostics only.

## 7. Distribution/key-mass chronology

For a row in season Y:

- base-distribution parameters;
- conditional scale coefficients;
- key-number excess-mass parameters;
- empirical residual benchmark frequencies

must be estimated entirely from eligible history before Y in outer evaluation, or before the inner validation season in inner folds.

No target-season residual sigma or target-season margin-frequency table is allowed.

## 8. Market-horizon boundary

A later market is not an earlier feature.

Historical schedule spread fields are labeled a generic late/closing benchmark unless exact timestamp provenance exists. They cannot be called T-120.

The prospective T-120 selector may use only market observations timestamped at or before kickoff minus 120 minutes. Later observations can be used only as later comparison/CLV data, never as T-120 inputs.

## 9. Completed-2026 firewall

Completed 2026 outcomes are prohibited from:

- candidate architecture;
- feature inclusion/exclusion;
- feature transformations/interactions;
- quantile choice;
- Q1 alpha selection;
- Q2 family/scale/key-mass decisions;
- Q3 learner/hyperparameters;
- probability calibration;
- blend weights;
- selective subset thresholds/rules;
- any retrospective rescue.

This includes indirect leakage: a current-season feature builder must not use completed 2026 outcomes to construct a retrospective candidate that later claims to have been frozen before those games.

Outcome-blind 2026 inputs may be inspected solely to verify source availability, field semantics, timestamp cadence and prospective collector operation.

## 10. Randomization prohibition

Random K-fold, shuffled train/test split and any CV method that permits future games to train a model predicting earlier games are prohibited.

Randomness inside an algorithm (e.g. XGBoost subsampling/bootstrap) is permitted only with the fixed seed and chronological training set.

## 11. Repeated-use boundary

Outer 2022–2025 results are not a renewable holdout. Once generated in Phase 2 they are interpreted under this preregistration; they cannot be repeatedly reused to modify Q1-Q3 and then re-presented as fresh confirmation.

If a Phase-2 implementation defect invalidates a result, correction requires:

1. documenting the defect before re-running;
2. distinguishing a bug fix from a model-design change;
3. preserving the invalidated result/receipt where feasible;
4. no opportunistic architecture change under the guise of a bug fix.

## 12. Production boundary

Research code/data/results have no authority to modify:

- official F-ST production identity/weights;
- Sunday Signal forecast probabilities/picks;
- production publication behavior;
- production market lock logic.

Any future production proposal would require a separate governance decision after prospective evidence.

## 13. Phase-transition boundary

Phase 1 freezes the scientific specification only.

Phase 2 may begin only after:

- Phase-1 spec PR exact-head CI passes;
- the package is merged;
- immutable Phase-1 receipt is recorded on main;
- `PHASE_STATUS.md` says Phase 1 COMPLETE and Phase 2 NOT STARTED.

Phase 2's first action is implementation of the shared research-only data/chronology/grading harness, not candidate training.