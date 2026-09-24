# EVALUATION PROTOCOL

## Governing principle

Proper probability/distribution scores decide the historical evidence. ATS hit rate and ROI are diagnostics and may not select candidates.

## Common-row rule

Every candidate-null comparison is paired on the exact intersection of valid rows. Report candidate-only/null-only missing rows separately. Never let a coverage difference masquerade as a score improvement.

## M3 primary evaluation

Candidate: `FV2-HIST-M3-DSSM-01`  
Null: `M3-NULL-MARKET-NORMAL-01`

Primary metric: multinomial cover/push/loss log loss at the historical quoted spread using integer-bin probabilities.

Secondary:

- Brier score;
- CRPS;
- calibration intercept/slope;
- reliability/resolution;
- margin MAE/RMSE;
- per-season paired differences;
- ATS hit rate with exact interval, diagnostic only.

## M4 primary evaluation

Candidate: `FV2-HIST-M4-DMARGIN-01`  
Null: `M4-NULL-STUDENTT-CONSTANT-01`

Primary metric: integer-margin logarithmic score `-log P(observed integer margin)`.

Secondary:

- CRPS / ranked probability score;
- cover/push/loss log loss;
- Brier;
- calibration intercept/slope;
- reliability;
- tail diagnostics;
- margin point errors as secondary only;
- ATS hit rate/ROI diagnostic only.

## Calibration

No post-hoc calibration rescue is permitted. If an explicitly preregistered model produces miscalibrated probabilities, report it. Phase 4 may not add Platt/isotonic/beta calibration after observing target results.

## Evidence classification for Phase 5

Phase 4 must deliver effect estimates and uncertainty; Phase 5 applies these frozen categories:

### `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`

Requires:

- candidate mean primary score better than its null on paired rows;
- paired 95% week-block-bootstrap interval for `candidate - null` lies entirely below 0;
- no numerical/leakage failure;
- calibration not materially degraded: absolute calibration slope departure from 1 may not worsen by more than 0.10 and absolute intercept may not worsen by more than 0.03 versus null, unless the candidate primary metric improvement remains significant under the calibration diagnostic with no post-hoc correction;
- improvement not wholly concentrated in one season or fewer than 10 game rows.

### `REJECTED`

Any of:

- candidate primary-score point estimate is worse than or equal to null and the paired interval excludes a practically meaningful improvement;
- numerical contract fails;
- leakage/chronology contract fails;
- candidate mechanism ablation shows the claimed mechanism contributes no improvement while a simpler preregistered component reproduces the result.

### `INCONCLUSIVE`

All other cases, including a favorable point estimate whose uncertainty crosses 0.

These categories prevent ATS headlines from overriding proper-score evidence.

## ATS/ROI diagnostics

- no historical selection based on ATS hit rate;
- pushes reported separately;
- exact ATS intervals required;
- no actual historical ROI when actual side price is absent;
- `REFERENCE_MINUS110` may appear only as a labeled sensitivity under `SELECTIVITY_AND_ECONOMICS_CONTRACT.md`.

## Stopping rule

Once all frozen candidates, nulls and preregistered ablations are evaluated, Phase 4 stops. It may not create a rescue candidate from observed failure patterns. New hypotheses go to a new version/program.