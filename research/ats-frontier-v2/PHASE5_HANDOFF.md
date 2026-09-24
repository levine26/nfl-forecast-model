# PHASE 5 HANDOFF

**Program:** `LEVLINE_ATS_FRONTIER_V2`  
**Phase 4 state:** `EVIDENCE_COMPLETE__PENDING_REPOSITORY_MERGE`  
**Phase 5:** `NOT_STARTED`

## Canonical Phase-4 evidence

Use only the final branch-preserved accepted Phase-4 evidence package from workflow run `36025444929`, artifact `10820397832` (`ats-frontier-v2-phase4-36025444929`, digest `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`).

Execution head: `7eda9cacd471a3161424699958509c02a260fc05`.

Validated pre-result scientific head: `c1eead294c5ac897041fc35f628b2fec393ab064`.

Accepted code SHA-256: `155f5afeffe0ea71afdd204b7f7e602d29f1664bb27fab52506ba6df85ac858f`.

Config SHA-256: `ddc4abf966cbe15a865f4866b29ff76530f2449a07eca87b0ffee4ba07ec3284`.

Dataset identity SHA-256: `8a6d974306abd57ca8060ad3803c7e90ae52f3fbd2900dbb1599c77dbd858129`.

Game-ID SHA-256: `03156647fbed7dc936c953a2a6c3400b2423fc3c8ff245388261c9bddd3b2a4f`.

M3 canonical OOF SHA-256: `9ea3c9062f00518ee7b2535605509b40f817c31dd731e3d178916ae117eac4a1`.

M4 canonical OOF SHA-256: `71e7891d9b75622cbb48fb64912566f5cb57ad10959600bc25ecf74bd4bd46cb`.

Corrected workflow run `36025306390` / artifact `10820230932` is retained as a successful near-identical reproducibility execution from the same frozen scientific surface. It is not the canonical branch package. See `PHASE4_REPRODUCIBILITY_NOTE.md`.

Workflow run `36023376614` is `INVALID / NOT ACCEPTED`; do not use its metrics or conclusions.

## Phase-4 evidence carried forward

### M3 — `FV2-HIST-M3-DSSM-01`

Phase-4 technical evidence label: `NEGATIVE_PRIMARY_EVIDENCE`.

- OOF/common rows: `1087`.
- candidate CPL log loss: `0.7811502028797036`.
- market-null CPL log loss: `0.7804795705044401`.
- paired candidate-minus-null delta: `+0.0006706323752636532`.
- 10,000-resample week-block 95% interval: `[-0.00031937461835433245, +0.0016556867645020252]`.
- descriptive probability favorable: `0.0889`.
- outer-season delta is unfavorable in 2022, 2023, 2024 and 2025.
- full dynamic model improves the frozen static ablation slightly but still loses to the market null.
- adding the QB component is worse than the preregistered `DYNAMIC_NO_QB` ablation on the primary score.
- candidate calibration intercept/slope: `-0.0008002656550699535 / -1.4064471514780361`.
- ATS diagnostic: `518-540-29`; ex-push hit rate `48.96%`; `REFERENCE_MINUS110` sensitivity `-6.53%`; no actual historical ROI claim.

### M4 — `FV2-HIST-M4-DMARGIN-01`

Phase-4 technical evidence label: `POSITIVE_PRIMARY_EVIDENCE`.

- OOF/common rows: `1087`.
- candidate integer-margin log score: `3.852975162486858`.
- strong-null integer-margin log score: `3.935646861629811`.
- paired candidate-minus-null delta: `-0.08267169914295289`.
- 10,000-resample week-block 95% interval: `[-0.10748698706212485, -0.05796293485132338]`.
- descriptive probability favorable: `1.0`.
- outer-season delta is favorable in 2022, 2023, 2024 and 2025.
- conditional-scale-only contribution versus null: `+0.00012506107970626913`.
- key-mass contribution versus null: `-0.08271839184340689`.
- full minus `CONSTANT_SCALE_KEY`: `+0.00004669270045401389`; essentially all primary-score improvement is reproduced by the preregistered key-mass component.
- candidate calibration intercept/slope: `0.01477013532177962 / 0.4366590498000353`.
- ranked probability score: `6.9151235686363295`.
- ATS diagnostic: `540-518-29`; ex-push hit rate `51.04%`; `REFERENCE_MINUS110` sensitivity `-2.56%`; no actual historical ROI claim.
- PMF/tail audit: `PASS`; no finite-support clipping or endpoint folding.

## Reproducibility note

The two corrected runs are not byte-identical. M3's pooled primary delta differs by approximately `5e-19`; M4's differs by approximately `7.35e-9`. Selected hyperparameter identities, OOF row counts, evidence direction, per-season direction, bootstrap conclusion, ablation attribution and Phase-4 evidence labels are unchanged. The numerical drift is preserved transparently and is not used to select a favorable execution.

## Firewalls

- completed-2026 outcomes used: `0`.
- production model: `F-ST-01-FROZEN-2026`, unchanged.
- Sunday Signal numerical forecasts/official fair spread/score projections/ATS logic/history/grading/deployment: unchanged.
- market input remains labeled `HISTORICAL_CLOSING_LATE_BENCHMARK_EXACT_HORIZON_OPAQUE`.
- red-team audit: `PASS`.
- ATS and `REFERENCE_MINUS110` calculations are diagnostics only and do not determine survivor status.
- 2022–2025 are development/non-pristine evidence, not a pristine prospective holdout.

## Exact Phase-5 first action

After the Phase-4 primary and closeout PRs are merged and Phase 4 is formally marked `COMPLETE`, read the immutable canonical evidence/hashes and apply the frozen `EVALUATION_PROTOCOL.md` classifications independently to M3 and M4.

Before applying the calibration-relative eligibility clause, derive the corresponding null-side calibration intercept/slope from the already preserved candidate/null OOF probabilities if not already materialized. This is a reporting/synthesis calculation only: no refitting, recalibration, changed probabilities, new model, or target-dependent transformation is authorized.

Then classify each historical candidate exactly one of:

- `REJECTED`
- `INCONCLUSIVE`
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`

Do not redesign either candidate. Do not introduce a rescue feature, hyperparameter, key number, threshold, subset, calibration method, M1/M2 historical candidate, or M3+M4 combination. Do not start prospective shadowing until the Phase-5 classification is complete.
