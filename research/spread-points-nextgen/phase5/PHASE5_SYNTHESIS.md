# Phase 5 Synthesis — Historical F-ST-Anchored Winner Integration

**Candidate:** `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`  
**Scientific disposition:** **`REJECTED`**  
**Phase 6 eligibility:** **NO**  
**Production:** `F-ST-01-FROZEN-2026` unchanged

## Scientific chronology

The Candidate 5 evidence boundary, component contract, chronology, learner, regularization grid, ablations, metrics, 2025 policy and classification rule were frozen before Candidate-5-specific performance at preregistration commit:

`df14e51d73aad96899d3ba4364cbb76989f0d2bf`

The historical incumbent is the accepted chronology-clean F-ST reproduction from `challenger_outputs/fst/provenance/training_frame_keyed.csv` through `build_chronological_logit_stack`, hard-checked at 741/1,087 correct across 2022–2025. It is a historical reproduction, not a claim of original prospective forecast locks.

The primary Candidate 5 historical development/evaluation surface contains 815 exact-paired 2022–2024 games. The 2022 meta-layer deterministically falls back to F-ST because no earlier Candidate 5 component surface exists. 2023 is fit only from 2022; 2024 is tuned only through 2023 and then fit through 2023.

## Primary result

On the exact 815-game primary surface:

- F-ST: **562/815 = 68.9571%**
- Candidate 5 primary: **562/815 = 68.9571%**
- accuracy delta: **0.0000 percentage points**
- winner switches: **0 / 815 = 0.0000%**
- Candidate-5-only correct: **0**
- F-ST-only correct: **0**
- changed-winner accuracy: **not defined because there were no switches**
- Brier: **0.21035034** vs F-ST **0.21034462**; delta **+0.00000573**
- log loss: **0.60909083** vs F-ST **0.60907731**; delta **+0.00001352**
- calibration intercept/slope: Candidate 5 **0.09794 / 1.12581** vs F-ST **0.09772 / 1.12626**

The required mechanism identity is exactly satisfied:

`DeltaAccuracy = 0 = 0 × (2 × changed_winner_accuracy - 1)`

The result is scientifically informative: under the preregistered strong-shrinkage contract, A0/B0 compact component information did not earn any winner change around F-ST. Probability quality was nominally, though only microscopically, worse.

## Mandatory ablations

Every preregistered residual arm also made zero winner switches over 2022–2024:

- F-ST + A0: 68.9571%; Brier delta +0.00000064; log-loss delta +0.00000163
- F-ST + B0: 68.9571%; Brier delta +0.00000268; log-loss delta +0.00000632
- F-ST + A0 + B0: 68.9571%; Brier delta +0.00000332; log-loss delta +0.00000796
- primary compact football: 68.9571%; Brier delta +0.00000573; log-loss delta +0.00001352
- market-aware diagnostic: 68.9571%; Brier delta +0.00001110; log-loss delta +0.00002544

Raw A0 accuracy was 62.9448%, raw B0 60.4908%, and the compatible historical late-market benchmark 68.5890% on these 815 rows. The late-market benchmark had slightly better proper scores than F-ST but lower straight-up accuracy; it remains a horizon-opaque diagnostic, not a production-horizon input.

D remains `ENSEMBLE_NOT_ELIGIBLE` and was not reconstructed.

## Uncertainty

The frozen 10,000-resample season+week block bootstrap returns an accuracy-delta interval of exactly **0.0000 to 0.0000**, because the primary model never changed a winner. Candidate 5 proper-score deltas are centered slightly above zero and their bootstrap intervals straddle zero; this does not rescue the absent winner mechanism.

## 2025 diagnostic

The fixed post-freeze run is labeled exactly:

`POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`

On 272 games, F-ST and every frozen Candidate 5 residual arm were **179/272 = 65.8088%**, again with **zero winner changes**. The primary Candidate 5 Brier delta was approximately **+0.000003** and log-loss delta approximately **+0.000006** versus F-ST. This evidence did not select, tune, redesign or rescue Candidate 5.

## Adversarial audit

The red-team audit found no same-row base leakage, future meta-training, outcome-derived feature use, post-result feature/component choice, 2025 tuning, completed-2026 contamination, closing-line-as-T-120 contamination, F-ST surface mismatch, duplicate/mismatched game IDs, future-fit scaling, hyperparameter leakage, threshold fishing, outcome-dependent filtering, production mutation, or post-result model rescue.

The first Phase 5 CI attempt failed before historical scoring because a synthetic test fixture expected the wrong discordant-count split. The fixture was corrected without altering the scientific contract; the first Candidate-5-specific historical execution then completed successfully under workflow `35828122187`.

## Final classification and program consequence

The preregistered classification rule requires a positive paired accuracy delta and changed-winner accuracy above 0.50 for Phase 6 eligibility. Candidate 5 produced neither a positive accuracy delta nor any winner changes. Therefore the only defensible classification is:

**`REJECTED`**

Phase 6 prospective shadow validation is **not justified for this Candidate 5 identity**. No Phase 6 handoff is created. A future materially different hypothesis would require a new separately preregistered identity and may not reinterpret the spent historical evidence as untouched confirmation.

Production `F-ST-01-FROZEN-2026` and Sunday Signal forecasting behavior remain unchanged.
