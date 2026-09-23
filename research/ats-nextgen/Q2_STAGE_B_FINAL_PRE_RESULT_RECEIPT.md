# ATS Next-Generation — Q2 Stage B Final Pre-Result Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** B — Q2  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Status:** **FINAL PRE-RESULT FREEZE; NO ACCEPTED Q2 HISTORICAL RESULT**  
**Branch:** `research/ats-nextgen-phase2-q2`  
**Stage-B base:** `a2581a62e3797a6ac466d614326bc72b7d5a1c57`  
**Final registry parent:** `646177f2d6fa718a4af7eba591c142229db2d40f`  
**Final pre-result registry blob:** `151feaec8922d226d9da5dd45716503d596416de`

## 1. Evidence boundary

This is the final Stage-B pre-result receipt. It supersedes every Q2 historical workflow run attached to an earlier branch head. No earlier Q2 result, even if its job later completes, is admissible for Stage-B classification or redesign.

At this boundary:

- accepted Q2 historical result: **NONE**;
- accepted Q2 performance inspected for candidate classification: **NONE**;
- Q2 rescue/redesign after an accepted result: **NONE**;
- Q3 started: **NO**;
- completed-2026 outcomes used: **0**;
- production F-ST/Sunday Signal forecasting changed: **NO**.

The only admissible Q2 result is an immutable artifact produced by the dedicated Stage-B workflow on this receipt's exact head (or an otherwise scientifically identical later receipt-only head explicitly superseding it), after its contract job succeeds.

## 2. Frozen upstream identities

Before the first Q2 fit, the runner must reproduce:

- Phase-2 gate canonical game-keyed SHA-256: `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- Stage-A Q1 OOF SHA-256: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365` on 1,087 outer OOF games;
- frozen Stage-A Q1 median predictions by `game_id` for every 2022–2025 outer season.

Any mismatch occurs before Q2 fitting and invalidates the execution.

## 3. Final frozen implementation identities

The final Stage-B scientific/reporting surface is:

- Q2 distribution core: `d551c4d3dbaa808556e3183fd65d6d20e8e92212`;
- nested rolling-origin experiment driver: `9249b39ebc2c42e4013a13b763d010c75939bd74`;
- reporting/calibration implementation: `596b9ede2c5c1f15bcac440d07dd8cb80e03339e`;
- fail-closed historical runner: `af73910ce78c51e18b879d6175a8873f11bae40e`;
- core contract tests: `4a691a354b1e577fb64ae66767bee6eb2e985fc2`;
- experiment/reporting contract tests: `339fc5d8d315767d860f4d079a9c43a0304ba6d0`;
- dedicated contract→historical workflow: `1c5c000ada73cfe458c69a1e440bafbbb1a2ca75`;
- opening scientific receipt: `548c60fbaf44cb10fb47bfed3255ed30feb1cbae`;
- scoring/reporting receipt: `23a595ed7bbab8ff7eabd59225bc533d2230b85f`;
- final machine pre-result registry: `151feaec8922d226d9da5dd45716503d596416de`.

The unused exploratory runtime path was removed before this freeze and is not part of the scientific implementation.

## 4. Frozen experiment and selection surface

Exactly 12 paired historical arms are allowed: six M1 market-centered arms and the corresponding six Q2 Q1-adjusted-centered arms. The bounded set is:

1. generalized normal, no-key + conditional scale;
2. generalized normal, key excess + constant scale;
3. generalized normal, key excess + conditional scale (`GN_FULL`, primary);
4. Gaussian, key excess + conditional scale;
5. Student-t, key excess + conditional scale;
6. empirical residual reference.

The primary incremental comparison is fixed to `Q2_GN_FULL` versus `M1_GN_FULL` on exact common OOF rows. Shape/key-penalty selection is prior-only pooled row-level discrete CRPS. The two GN ablations and all other families are diagnostic bounded references and cannot replace the primary arm after results.

No ATS hit rate, ROI, threshold, selective slice, calibration layer, new family, new key, new support, new scale predictor, new penalty, or new smoothing rule may rescue Q2 V1.

## 5. Frozen reporting surface

The accepted artifact must contain, at minimum:

- discrete CRPS/RPS;
- multinomial cover/push/loss log loss;
- binary cover Brier and log loss on non-push rows;
- cover calibration intercept/slope where estimable;
- fixed-decile cover reliability;
- push calibration;
- expected/median margin MAE and RMSE;
- equal-tailed 50%, 80%, and 90% interval coverage and mean width;
- frozen spread/favorite-size/market-total slices;
- direct final-margin key-mass calibration for `|M| in {3,6,7,10,14}`, overall and by outer season;
- maximum endpoint mass, subject to the frozen `1e-3` fail-closed threshold.

These reports are diagnostic unless the Phase-1 protocol explicitly identifies the metric as primary. They cannot reopen candidate design after inspection.

## 6. Exact-head execution rule

The dedicated Stage-B workflow must satisfy this chain on the exact receipt head:

1. contract job passes all gate/Q1/Q2 synthetic and chronology tests;
2. historical job starts only through `needs: contract`;
3. upstream gate/Q1 identities reproduce before the first Q2 fit;
4. all frozen outer OOF arms complete on exact common rows;
5. protected production surfaces remain unchanged;
6. all required evidence files exist, including `q2_key_mass_calibration.csv`;
7. the complete immutable artifact is uploaded.

Only after step 7 may the artifact be inspected and Q2 classified. If this branch changes before artifact acceptance, the run is superseded and must be repeated from the new exact head.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
