# Candidate 5 Evaluation Protocol

## Primary estimand
`accuracy(PRIMARY_COMPACT_FOOTBALL) - accuracy(FST)` on exact paired chronology-clean historical rows.

## Frozen metrics
For every modeled arm versus F-ST report: games; correct counts; candidate-only and F-ST-only correct; accuracy and delta; changed winners and rate; changed-winner accuracy; exact two-sided McNemar; Brier; log loss; calibration intercept and slope; fixed 10-bin reliability diagnostics; season results; week/team concentration; F-ST-confidence and component-disagreement slices.

Verify numerically:
`DeltaAccuracy = winner_change_rate * (2 * changed_winner_accuracy - 1)`.

## Uncertainty
Use a deterministic season+week block bootstrap with 10,000 resamples and seed `20260922`. Resample season-week blocks with replacement within the evaluated historical surface and report percentile 95% intervals for accuracy, accuracy delta, Brier delta and log-loss delta where finite.

No bootstrap result changes the frozen model specification.

## Calibration
Calibration intercept/slope are diagnostics from a two-parameter logistic calibration regression on the already-frozen probabilities. They do not alter predictions. Reliability bins are fixed equal-width probability bins: `[0,.1), ... ,[.9,1]`.

## Primary historical classification rule
After leakage/provenance audits:
- `ELIGIBLE_FOR_PROSPECTIVE_PHASE6_SHADOW_VALIDATION` only if the primary football arm has positive paired accuracy delta, changed-winner accuracy > 0.50, and both Brier and log-loss point estimates are no worse than F-ST on the same paired rows.
- `INCONCLUSIVE_BUT_COHERENT` if the primary mechanism is directionally positive/selective but fails one of the probability-quality conditions or evidence is too sparse/concentrated for Phase 6 eligibility without showing a clear negative mechanism.
- `REJECTED` if the primary paired accuracy delta is <= 0, changed-winner accuracy is <= 0.50 when switches occur, or a scientific/provenance defect invalidates the claimed mechanism.

No p-value threshold is used as an automatic promotion gate; uncertainty is reported because Phase 6 eligibility authorizes only prospective shadow testing, not production promotion.

## 2025
If executed, report separately as `POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`. It cannot change model identity or final historical selection logic; it is a fixed-model robustness diagnostic and must be preserved regardless of sign.
