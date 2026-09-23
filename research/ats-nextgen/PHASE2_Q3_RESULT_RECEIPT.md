# ATS Next-Generation — Phase 2 Q3 Result Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** C — Q3  
**Candidate:** `ATS-Q3-DIRECT-CPL-HURDLE-V1`  
**Scientific classification:** **VALID NEGATIVE INCREMENTAL RESULT — NOT INCREMENTAL VS Q3-M2**  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

## 1. Accepted execution identity

- branch: `research/ats-nextgen-phase2-q3`;
- PR: #562;
- verified Stage-B base: `16859845573c3344ed82ae0b9bd27fa8b891eee4`;
- frozen full scientific-surface head: `d9dbfe24af7fd19f5b22e76fd5f57dd83c606a60`;
- historical authorization / accepted result head: `891d921c24bc045dd58de3b2dd05871f12d09183`;
- workflow: `35931071604`;
- contract job: `107417650978` — **SUCCESS**;
- chronology-clean historical job: `107418004469` — **SUCCESS**;
- completed-2026 outcomes used: **0**;
- production forecasting changed: **no**.

The historical job first re-verified the frozen Q3 model, reporting, runner, and test blob identities before the first fit, then regenerated the frozen Phase-2 gate and required canonical gate SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`.

## 2. Immutable evidence artifact

- artifact ID: `10781521222`;
- artifact name: `ats-nextgen-q3-35931071604`;
- artifact digest: `sha256:6062472dce30fddfcc6ad16d1d5c29203491f6e77d893aa673cc20bbb29a1bfa`;
- outer OOF rows: **1,087**;
- outer target seasons: **2022, 2023, 2024, 2025**.

Exact uploaded-file SHA-256 identities:

- `q3_outer_oof_2022_2025.csv`: `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- `q3_inner_c_pair_selections.csv`: `7164f804d3f0b2d240f538ef056c7e3c503a2994e092b14dbbe2db8f518b6e36`;
- `q3_probability_metrics.csv`: `722833d2f9bd3a972f755964aa6c9b5ce8ed05b62c3d280383974f434001ba92`;
- `q3_cover_reliability.csv`: `c32845d02c0e37724ca33a971a77748d60190c03124b55b89a6b3c3cf4c01993`;
- `q3_push_calibration.csv`: `375d2b2251c945d1582032d1ca9a0ef8fda2f1578b2d41ec68ad93668c6c9636`;
- `q3_fixed_slice_metrics.csv`: `518a3d9d7b575ce48151509e3e53c4e4790c3eb35fa09842a36ecac155870e99`;
- `q3_summary.json`: `ed9b30b9174bec553a599e099f938f90eadf6748b9818f69fae97889c7e64072`.

## 3. Preregistered primary result

Across all 1,087 OOF games:

- Q3-M2 multinomial CPL log loss: `0.7716887205239867`;
- Q3 multinomial CPL log loss: `0.7730044623812287`;
- Q3 minus Q3-M2: **`+0.0013157418572419255`**.

Lower is better. Q3 is worse on its preregistered primary proper-score objective and fails the incremental-information gate.

Supporting non-push cover metrics:

- Brier: Q3-M2 `0.24979992069239074`, Q3 `0.2504715666095457`;
- binary log loss: Q3-M2 `0.6927518077695590`, Q3 `0.6941036143847026`.

No ATS hit-rate, ROI, selected subset, key-number cell, or secondary outcome may override this failed proper-score objective.

## 4. Calibration and mechanism diagnostics

Aggregate conditional-cover calibration:

- Q3-M2 intercept/slope: `0.034453703165041635` / `0.8130523437112027`;
- Q3 intercept/slope: `0.010352055248903256` / `0.27094382668690847`.

The push head is shared by design between Q3-M2 and Q3, so both arms have identical push probabilities:

- mean predicted push: `0.023992664002116082`;
- empirical push rate: `0.02667893284268629`;
- aggregate push calibration error: `-0.0026862688405702093`.

This isolates the incremental failure to the added compact football information in the conditional-cover head rather than to a different push model.

## 5. Season and fixed-slice stability

Season-level Q3 minus Q3-M2 multinomial log-loss deltas:

- 2022: `+0.00011298354392952`;
- 2023: `+0.00334784143158218`;
- 2024: `-0.00130926027708478`;
- 2025: `+0.00310698082497762`.

Q3 is worse in **3 of 4** outer seasons. Across the **14 frozen fixed reporting slices**, Q3 has lower log loss in 4 and higher log loss in 10. Favorable seasons/slices are descriptive only and cannot rescue the failed pooled result.

## 6. Frozen tuning evidence

Both Q3 and Q3-M2 selected the same regularization pairs in every outer season:

- 2022: `C_push=0.01`, `C_cover=0.01`;
- 2023: `C_push=0.01`, `C_cover=0.01`;
- 2024: `C_push=0.1`, `C_cover=0.01`;
- 2025: `C_push=0.1`, `C_cover=0.01`.

Selection used only prior-time inner rolling-origin multinomial log loss over the frozen 16-pair grid. No class weighting or post-hoc probability calibration was used.

## 7. Q2 and blend status

Q2 V1 remains `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT` and has no valid Q2 OOF distribution. Therefore Q2 complementarity and Q2/Q3 blending are **unavailable**. No substitute Q2 distribution, widened support, reconstructed OOF, or replacement blend is authorized.

## 8. Scientific conclusion

`ATS-Q3-DIRECT-CPL-HURDLE-V1` is a valid chronology-clean historical experiment but **does not add incremental probability information over Q3-M2 under the frozen V1 contract**.

Q3 V1 is closed. No learner, feature, interaction, C grid, class weighting, calibration layer, threshold, or slice may be changed in response to this result and still be called the same experiment.

Stage D may now perform only the preregistered final evidence synthesis and uncertainty work on already-accepted evidence. It may not rescue Q1, Q2, or Q3.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
