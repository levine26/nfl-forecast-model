# PHASE 5 HANDOFF

**Program:** `LEVLINE_ATS_FRONTIER_V2`  
**Phase 4 state:** `EVIDENCE_COMPLETE__PENDING_REPOSITORY_MERGE`  
**Phase 5:** `NOT_STARTED`

## Canonical Phase-4 evidence

Use only the accepted Phase-4 evidence package preserved from workflow run `36025306390`, artifact `10820230932` (`ats-frontier-v2-phase4-36025306390`, digest `sha256:c31c5c324db4e56f63488c883252ca2601f39aecf2989d645790aa21704f4fcf`).

Execution head: `4fce9805c2ba9ed9dc6de388600fe40787605720`.

Validated pre-result scientific head: `c1eead294c5ac897041fc35f628b2fec393ab064`.

Accepted code SHA-256: `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`.

Config SHA-256: `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`.

Dataset identity SHA-256: `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`.

M3 accepted OOF SHA-256: `f15bb97c9947bffb123f70658b2b75ebd900a341b9aefe680fbe86beaaf30c40`.

M4 accepted OOF SHA-256: `2653434b7264a73166429f6702f83a4da87f2d59eb023c3839d3222afff18190`.

The earlier execution run `36023376614` is `INVALID / NOT ACCEPTED`; do not use its metrics or conclusions.

## Phase-4 evidence carried forward

### M3 — `FV2-HIST-M3-DSSM-01`

Phase-4 technical evidence label: `NEGATIVE_PRIMARY_EVIDENCE`.

- OOF/common rows: `1087`.
- candidate CPL log loss: `0.7811502028797036`.
- market-null CPL log loss: `0.7804795705044401`.
- paired candidate-minus-null delta: `+0.0006706323752636537`.
- 10,000-resample week-block 95% interval: `[-0.00031937461835433695, +0.001655686764502027]`.
- outer-season delta is unfavorable in 2022, 2023, 2024 and 2025.
- full dynamic model improves the frozen static ablation slightly but still loses to the market null.
- adding the QB component is worse than the preregistered `DYNAMIC_NO_QB` ablation on the primary score.
- candidate calibration intercept/slope: `-0.0008002656550696445 / -1.4064471514780372`.

### M4 — `FV2-HIST-M4-DMARGIN-01`

Phase-4 technical evidence label: `POSITIVE_PRIMARY_EVIDENCE`.

- OOF/common rows: `1087`.
- candidate integer-margin log score: `3.85297516860494`.
- strong-null integer-margin log score: `3.9356468604011363`.
- paired candidate-minus-null delta: `-0.08267169179619614`.
- 10,000-resample week-block 95% interval: `[-0.10748699203380639, -0.057962887776498655]`.
- outer-season delta is favorable in 2022, 2023, 2024 and 2025.
- conditional-scale-only contribution versus null: `+0.0001250552561666556`.
- key-mass contribution versus null: `-0.08271837498276481`.
- full minus `CONSTANT_SCALE_KEY`: `+0.0000466831865686729`; essentially all primary-score improvement is reproduced by the preregistered key-mass component.
- candidate calibration intercept/slope: `0.014770139195534758 / 0.43665842195187754`.
- PMF/tail audit: `PASS`; no finite-support clipping or endpoint folding.

## Firewalls

- completed-2026 outcomes used: `0`.
- production model: `F-ST-01-FROZEN-2026`, unchanged.
- Sunday Signal numerical forecasts/official fair spread/score projections/ATS logic/history/grading/deployment: unchanged.
- market input remains labeled `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`.
- red-team audit: `PASS`.
- ATS and `REFERENCE_MINUS110` calculations are diagnostics only and do not determine survivor status.
- 2022–2025 are development/non-pristine evidence, not a pristine prospective holdout.

## Exact Phase-5 first action

After the Phase-4 primary and closeout PRs are merged and Phase 4 is formally marked `COMPLETE`, read the immutable accepted evidence/hashes and apply the frozen `EVALUATION_PROTOCOL.md` classifications independently to M3 and M4.

Before applying the calibration-relative eligibility clause, derive the corresponding null-side calibration intercept/slope from the already preserved candidate/null OOF probabilities if not already materialized. This is a reporting/synthesis calculation only: no refitting, recalibration, changed probabilities, new model, or target-dependent transformation is authorized.

Then classify each historical candidate exactly one of:

- `REJECTED`
- `INCONCLUSIVE`
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`

Do not redesign either candidate. Do not introduce a rescue feature, hyperparameter, key number, threshold, subset, calibration method, M1/M2 historical candidate, or M3+M4 combination. Do not start prospective shadowing until the Phase-5 classification is complete.
