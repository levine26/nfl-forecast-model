# Spread & Points Next-Generation — Final Phase 5 Receipt

**Phase:** 5 — Historical F-ST-Anchored Winner Integration  
**Candidate:** `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`  
**Final scientific disposition:** **`REJECTED`**  
**Phase 6 eligibility:** **NO**  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged  
**Receipt date:** 2026-09-23 America/Los_Angeles

## 1. Final state

Phase 5 is scientifically and operationally closed for `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1`.

The candidate did not improve frozen F-ST winner accuracy, made no winner changes on the primary historical surface, and produced microscopically worse proper-score point estimates. The preregistered eligibility rule therefore classifies the candidate `REJECTED` and does not authorize Phase 6 prospective shadow validation for this identity.

No completed-2026 outcome participated in Candidate 5 design, fitting, tuning, historical evaluation, rescue or survival. No production F-ST coefficient, winner-selection rule, public forecast, Sunday Signal behavior, official history, lock, grading path or protected production surface was changed.

## 2. Scientific freeze and provenance

Candidate 5's evidence boundary, component policy, feature sets, OOF chronology, F-ST anchor, residual-logistic learner, regularization grid, tuning rule, winner threshold, mandatory ablations, uncertainty procedure, 2025 diagnostic policy and final classification rule were frozen before Candidate-5-specific results at:

`df14e51d73aad96899d3ba4364cbb76989f0d2bf`

Phase 5 branch base:

`d9302207c3dd0a82c89fadd2cd5adc52f6541bd0`

Primary preserved component surface:

`research/spread-points-nextgen/phase3/evidence/FUTURE_CANDIDATE5_OOF_SURFACES_2022_2024.csv`

Frozen Phase 3 implementation/config identities:

- implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`

Candidate 5 run identities:

- Candidate 5 code SHA-256: `55f62f9de44e853f820016c893c6d94a9a2226f7c08e412260a7cf5d10c9b4c2`
- Candidate 5 config SHA-256: `5762ac921519e594412d0dbcc6ced49d8fb332672e83bb0c5e54cd53d04299ce`
- F-ST historical reproduction: 741/1,087 correct across 2022–2025
- interpretation of F-ST history: chronology-clean historical reproduction, not original prospective locks

## 3. Execution chronology

First Phase 5 workflow attempt:

- run `35827845845`
- stopped in the pre-result synthetic unit-test gate
- Candidate-5-specific historical metrics generated: **NO**

Engineering-only correction:

`b86b7c98b40a3b68e6fb4e42f9aeb6592554065a`

The correction changed only the synthetic test expectation and did not alter any scientific term.

First successful frozen Candidate 5 execution:

- workflow `35828122187` — SUCCESS
- evidence preservation commit `8fce0be359d93d68bc2c4bba852ede4181a38368`

Final Phase 5 integration PR:

- PR #552 — **MERGED**
- exact validated head: `a4f892d64ab163a421eed203d9b50983e5bbd04b`
- merge commit: `a68afb1e1cf9675a7ff9e0e0af1f52343546f029`
- merged-main first parent preserved concurrent market-refresh state `4d2358d47bc82fa333172b17a803dd222f9b5047`

Exact-head closeout validation on `a4f892d64ab163a421eed203d9b50983e5bbd04b`:

- dedicated Phase 5 validation `35875417408` — **SUCCESS**
- research firewall `35875417416` — **SUCCESS**
- full LevLine research validation `35875417452` — **SUCCESS**
- Phase 4 frozen-evidence regression `35875417543` — **SUCCESS**

## 4. Primary Candidate 5 result

Exact paired 2022–2024 primary surface:

- games: **815**
- F-ST correct: **562/815 = 68.9571%**
- Candidate 5 correct: **562/815 = 68.9571%**
- accuracy delta: **0.0000 percentage points**
- changed winners: **0 / 815**
- Candidate-5-only correct: **0**
- F-ST-only correct: **0**
- changed-winner accuracy: **undefined because no winner changed**
- Candidate 5 Brier: **0.21035034**
- F-ST Brier: **0.21034462**
- Brier delta: **+0.00000573**
- Candidate 5 log loss: **0.60909083**
- F-ST log loss: **0.60907731**
- log-loss delta: **+0.00001352**
- Candidate 5 calibration intercept/slope: **0.09794 / 1.12581**
- F-ST calibration intercept/slope: **0.09772 / 1.12626**
- 10,000-resample season+week block-bootstrap accuracy-delta interval: **0.0000 to 0.0000**

Every preregistered Candidate 5 residual ablation also produced zero winner switches. D remained `ENSEMBLE_NOT_ELIGIBLE` and was not reconstructed.

## 5. Fixed 2025 diagnostic

The only Candidate-5-specific 2025 use was the frozen post-conception diagnostic labeled:

`POST_CONCEPTION_NON_PRISTINE_2025_DIAGNOSTIC`

On 272 games:

- F-ST: **179/272 = 65.8088%**
- Candidate 5 primary: **179/272 = 65.8088%**
- winner changes: **0**
- proper-score point estimates were nominally slightly worse for Candidate 5

This diagnostic did not select, tune, redesign or rescue Candidate 5. It is not described as a pristine Candidate 5 holdout.

## 6. Phase 4 reproducibility CI hardening during closeout

The first PR-head Phase 4 regression run `35873546260` regenerated and validated the frozen Phase 4 scientific package but failed its final byte-for-byte file comparison because machine-level floating-point serialization differed at approximately numerical-noise scale.

This was treated as an operational CI defect, not as scientific drift. No Phase 4 evidence file, Candidate 5 model, feature, threshold, coefficient, tuning rule or conclusion was changed.

Engineering-only hardening commit:

`a4f892d64ab163a421eed203d9b50983e5bbd04b`

The Phase 4 comparator now requires exact file structure, exact nonnumeric values and numeric agreement at `rtol=1e-12`, `atol=1e-12`. The repaired exact-head run `35875417543` regenerated the complete 2025 package and confirmed semantic identity for:

- `A0_HOLDOUT_2025.csv`
- `B0_HOLDOUT_2025.csv`
- `C0_HOLDOUT_2025.csv`
- `BASELINES_HOLDOUT_2025.csv`
- `DIAGNOSTIC_SLICES_2025.csv`
- `HOLDOUT_SUMMARY.json`

The protected-production-surface diff also passed. The regenerated Phase 4 artifact was preserved as artifact `10757547981`, ZIP SHA-256 `dff940f9b18b43944426dca5f61197b697fde83b3748f019e69b493874148320`.

## 7. Merged-main verification

After PR #552 merged, `main` resolved to:

`a68afb1e1cf9675a7ff9e0e0af1f52343546f029`

The merged Phase 5 synthesis and run manifest were re-read from `main` and confirmed:

- Candidate 5 scientific disposition `REJECTED`;
- Phase 6 eligibility `false` / NO;
- 815-game primary result 562/815 for both F-ST and Candidate 5;
- zero winner switches;
- completed-2026 outcomes used: `false`;
- production changed: `false`;
- market diagnostic retains the label `historical_closing_late_benchmark_exact_horizon_opaque`.

## 8. Final program consequence

`LEVLINE-HISTORICAL-RESIDUAL-STACK-V1` is closed and may not be rescued under the same identity by loosening regularization, changing features/interactions, adding a nonlinear learner, recalibrating, changing the 0.5 winner threshold, mining 2025, or using completed-2026 outcomes.

**Do not start Phase 6 for Candidate 5 V1.**

A future materially different hypothesis requires a separately preregistered candidate identity and a new evidence clock. The spent 2022–2025 evidence may not be recharacterized as untouched confirmation.

Production remains `F-ST-01-FROZEN-2026`. No production promotion is authorized by this receipt.
