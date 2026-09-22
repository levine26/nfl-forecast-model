# Phase 1 Canonical Evaluation Contract

**Program:** LevLine Spread & Points Next-Generation Research Program  
**Phase:** 1 — Current LevLine Audit, Baseline Reproduction & Error Decomposition  
**Status:** active contract; research-only  
**Canonical branch:** `research/spread-points-nextgen-phase1`  
**Production behavior changed:** no

This contract freezes the definitions used by every Phase 1 lane. It is an audit contract, not a challenger preregistration.

## 1. Canonical orientation and targets

All game-level score targets are expressed from the **home-team orientation** used by the current repository.

- `home_win = 1(home_score > away_score)`.
- `margin = home_score - away_score`.
- `game_total = home_score + away_score`.
- projected home points = `(expected_total + expected_margin) / 2`.
- projected away points = `(expected_total - expected_margin) / 2`.

The independent score/margin model and the official F-ST winner probability are distinct forecast objects and must be evaluated separately.

## 2. Market spread convention

Despite the column name `spread_line`, the repository treats this historical field as a **market-implied home margin**:

- positive `spread_line` = home team favored by that many points;
- negative `spread_line` = home team is the underdog by that many points;
- conventional displayed home betting spread = `-spread_line`.

Therefore:

- market margin error = `actual_margin - spread_line`;
- home covers when `actual_margin > spread_line`;
- away covers when `actual_margin < spread_line`;
- ATS push when `actual_margin == spread_line`;
- model edge = `model_margin - spread_line`;
- model ATS side is home when model edge > 0 and away when model edge < 0.

Do not reverse this convention in any lane.

## 3. Canonical historical universe

Primary current-model validation universe:

- regular-season NFL games only;
- target seasons **2022–2025**, because the current 2026 pipeline defines `validation_start = season_to_predict - 4 = 2022` and `validation_end = 2025`;
- historical training data before each target season is allowed only under the current walk-forward implementation;
- postseason is excluded because `aggregate_team_games()` and `build_matchup_features()` explicitly restrict the modeled feature scaffold to regular-season games.

The modern emphasis requested by the program is additionally summarized for **2023–2025** where useful, but that subset must never silently replace the 2022–2025 current-validation universe.

## 4. 2026 treatment

Completed 2026 games may be used only for:

- grading forecasts that were actually produced and locked before kickoff;
- descriptive current-season error diagnostics;
- validating current operational behavior.

They may not choose model architecture, features, thresholds, weights, calibration rules, or Phase 2 challengers.

2026 results are reported separately from the 2022–2025 historical audit.

## 5. Tie treatment

Current repository compatibility is preserved explicitly:

- `features.py` encodes an NFL tie as `home_win = 0`, i.e. a home non-win.
- Current historical F-ST accuracy artifacts therefore use that repository target unless explicitly labeled otherwise.

Phase 1 must also report a **tie-excluded straight-up sensitivity** where practical so that human winner accuracy is not obscured by this target encoding.

Margin and total metrics retain tied games normally.

## 6. ATS push handling

ATS pushes are retained in sample accounting but excluded from ATS hit-rate denominators.

If `model_margin == spread_line` exactly, the model has no ATS side and that game is also excluded from ATS decision accuracy. Push and no-edge counts must be reported separately.

No ATS threshold may be tuned in Phase 1.

## 7. Market pairing rules

Market comparisons use exact paired games only.

- spread comparison requires nonmissing `spread_line` and realized margin;
- total comparison requires nonmissing `total_line` and realized total;
- moneyline probability comparison requires both home and away moneylines sufficient to build the current no-vig `market_home_prob`;
- model-vs-market differences are calculated only on the same games.

Historical nflverse schedule market fields are treated as a **closing/historical schedule benchmark with opaque exact capture timing** unless a timestamped repository receipt proves otherwise. They must not be relabeled as a T-minus horizon.

Prospective T-120 data from `market_t120.py` is a separate timestamped research surface.

## 8. Missing data

Phase 1 fails closed:

- do not impute missing market lines merely to increase paired sample size;
- do not infer a player was healthy because historical injury data are missing;
- do not infer a stable QB because no QB-state record exists;
- do not substitute later depth charts, later injury designations, realized snaps, or postgame information for missing pregame state;
- explicitly label subgroup tests impossible or incomplete when point-in-time coverage is inadequate.

The production regressors' internal median feature imputation remains part of the architecture being audited; Phase 1 does not change it.

## 9. Chronology and OOS labels

Use these labels precisely:

### Season-held-out base prediction
A target-season prediction is produced from a base model fitted only on prior seasons.

### Current-validation descriptive ensemble
The current regression implementation derives inverse-MAE ensemble weights from the combined 2022–2025 season-held-out block and applies those weights back across that same block. Base predictions are season-held-out, but final weights use the evaluation block. This is valid for reproducing current validation behavior and diagnostics, **not** chronology-clean challenger selection.

### Chronology-clean F-ST architecture estimate
Use the existing season-forward F-ST audit in which each target season's meta-stack is fitted on earlier-season OOF rows only.

### Frozen final-coefficient backscore
Useful for exact production-identity reconstruction, but not a clean out-of-sample estimate because the final frozen coefficients were ultimately fitted using the full eligible pre-2026 training frame.

Every numerical headline must state which category applies.

## 10. Metric formulas

For actual value `y`, prediction `p`, and N paired games:

- MAE = `mean(abs(y - p))`.
- RMSE = `sqrt(mean((y - p)^2))`.
- mean signed error = `mean(y - p)` unless a table explicitly labels the opposite orientation.
- residual SD = sample standard deviation of `y - p`.
- winner accuracy = mean of correct 0.5-threshold picks under the stated tie rule.
- Brier = mean squared probability error.
- log loss = binary cross entropy with probabilities clipped only as required for numerical stability.
- 80% Normal interval = prediction ± `1.2815515655 * sigma`.
- empirical 80% coverage = fraction of realized targets inside that interval, inclusive.
- ATS hit rate = correct ATS-side decisions / non-push, non-zero-edge decisions.
- market spread MAE = MAE of `spread_line` against realized home margin.
- market total MAE = MAE of `total_line` against realized total.

## 11. Uncertainty

Important paired model-vs-market comparisons should use season/week-aware or game/week-block resampling where practical.

Report sample size and represented seasons with every major comparison. Do not interpret small point differences as meaningful without uncertainty support.

## 12. Failure-mode thresholds fixed for Phase 1 diagnostics

To avoid post-hoc threshold hunting:

- realized blowout thresholds: absolute realized margin >= 14, >= 21, and >= 28 points;
- market favorite-size buckets by absolute market home margin: [0,3), [3,7), [7,10), [10,14), and >=14;
- model-market disagreement buckets: <2, 2–4, 4–6, 6–8, and >=8 points, matching the existing margin-forensics artifact.

These are diagnostic slices only and cannot define a future betting or promotion rule.

## 13. Source-of-truth hierarchy

1. current repository code on the audited main SHA;
2. reproducible committed data/receipts and preserved GitHub Actions artifacts;
3. prior research documents whose target/universe/chronology are verified compatible;
4. external research sources used only as context unless their methods/data are independently reproducible.

External sources, including **davidsasser.com**, may inform Phase 1 research inventory or Phase 2 questions but do not override repository evidence and are not treated as LevLine validation data.

## 14. Canonical sample accounting

At contract creation, the preserved 2022–2025 margin OOF ledger contains **1,087 regular-season games**, including **3 tied games**. Exact paired counts for each metric are written by the Phase 1 audit script and control the final reports.

If later reproducible evidence changes a count, update this contract with the reason rather than silently changing a lane's denominator.
