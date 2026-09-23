# Phase 4 — Red-Team Audit

**Scope:** one-time 2025 underlying-model historical holdout for frozen A0/B0/C0.  
**Disposition:** scientific execution valid; limitations documented; no rescue permitted.

## Evidence-boundary chronology

1. Phase 3 completed without loading or scoring 2025 challenger outputs.
2. Phase 4 opening receipt was committed at `362af7af7db43a715b9ab9537a52d2749c37e7a6` with `holdout_state_at_receipt = UNOPENED`.
3. Two initial workflow attempts failed before holdout execution because of a pytest package-import defect. The holdout jobs did not execute.
4. Corrected run `35818332253`, generator head `f0b92217488a1a000bee74a903a9437931a53230`, passed the complete pre-holdout gate and then opened the holdout once.
5. The entire A0/B0/C0 package, required evidence/firewall verification and protected-production diff completed successfully before any result interpretation.
6. Only the final bot persistence push failed because the branch advanced concurrently. The complete first-result package remained immutable in artifact `10732945725` and was subsequently committed byte-for-byte by the dedicated preservation workflow after hash verification.
7. Any later execution is explicitly a reproducibility run, not a new pristine holdout opening.

## Required red-team questions

| Question | Finding |
|---|---|
| Did any 2025 result enter tuning? | **NO.** Frozen nested selection uses prior seasons; emitted rows record fit through 2024. |
| Were hyperparameters selected from prior-time data only? | **YES.** A0 selected alpha 100 / half-life 8; B0 drive alpha 0 / outcome C 0.05; C0 arms selected alpha 100 from prior-time inner folds. |
| Did scaler/imputer/state/covariance use a game's own outcome? | **NO.** Model fit/covariance objects use <=2024; frozen shifted pregame state can update from prior completed 2025 games only. |
| Did B0 use current-game PBP or outcomes? | **NO.** Current-game drive/scoring outcomes are not features for their own forecast; simulation uses frozen pregame states and training-only empirical components. |
| Did C0 use the correct A0 representation? | **YES.** C0 consumes frozen genuine prior-time A0 OOF/holdout representation only. |
| Were C0 market rows exactly paired? | **YES.** 272 C0 rows; all 272 have the frozen market fields. |
| Was historical market mislabeled T-120? | **NO.** Label remains `historical_closing_late_benchmark_exact_horizon_opaque`. |
| Did a baseline use 2025 in-sample fitting and get presented as clean OOS evidence? | **NO.** Compact baselines use prior-time rules. Phase 1 current LevLine score context is explicitly not substituted for a clean exact-row 2025 comparator. |
| Did production F-ST contaminate an OOS comparison? | **NO.** No 2025 production artifact trained with 2025 outcomes is scored as out-of-sample. |
| Were models changed after partial 2025 results? | **NO.** The runner computes the complete package in memory before persisting outputs. The only post-result workflow edit addressed evidence-push concurrency and did not alter scientific code. |
| Did completed 2026 outcomes enter design/selection? | **NO.** Manifest records false. |
| Was Candidate 5 trained or evaluated? | **NO.** Candidate 5 remains NOT STARTED. |
| Were rows selectively dropped after metrics were seen? | **NO.** A0/B0/C0 each contain all 272 eligible regular-season games; common count = 272. |
| Were negative results preserved? | **YES.** Exact raw predictions, baselines, slices, summary, manifest, failed-run log and reports are durable. |
| Did D get resurrected? | **NO.** Margin and total remain `ENSEMBLE_NOT_ELIGIBLE`. |

## Hash and identity audit

- frozen implementation SHA-256: `5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579`
- frozen config SHA-256: `2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543`
- B0 final simulations/game: 10,000
- bootstrap resamples: 10,000
- exact first-run artifact metadata digest: `sha256:7e231406237dc0f27681cc974d07ba34a6fe3bb976bea42531bedc8166557671`
- preservation workflow run: `35819413238` — SUCCESS; provenance and every evidence SHA verified before commit.

## Limitations

2025 is not philosophically pristine because Phase 1 had inspected broad baseline 2025 errors and those failures informed earlier research questions. No A0/B0/C0 output existed at that time. The scientifically accurate description is therefore: **final historical challenger holdout, with the disclosed limitation that broad baseline 2025 errors informed earlier research questions.**

Inference is also limited by a single target season. Week-block bootstrap quantifies within-season uncertainty but cannot create between-season replication.

## Audit conclusion

The frozen Phase 4 experiment was executed as specified. The evidence boundary was not repaired or redefined after the result. The negative standalone result is scientifically valid and must be carried into Phase 5 unchanged.