# ATS Next-Generation — Q2 Stage B Final Exact-Head Execution Authorization

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** B — Q2 only  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Status:** **PRE-RESULT; FINAL CLEAN EXECUTION AUTHORIZED ONLY AFTER EXACT-HEAD CONTRACT SUCCESS**  
**Branch:** `research/ats-nextgen-phase2-q2`  
**Stage-B base:** `a2581a62e3797a6ac466d614326bc72b7d5a1c57`  
**Final pre-authorization parent:** `646177f2d6fa718a4af7eba591c142229db2d40f`

## Purpose

This receipt is the final Stage-B pre-result mutation. It changes no model family, feature, fit, hyperparameter grid, chronology rule, selection objective, reporting bucket, or production behavior. It exists only to authorize one clean exact-head execution after the reporting-complete implementation and final machine registry were frozen.

At this boundary:

- accepted Q2 historical result: **NONE**;
- Q2 result interpretation/classification: **NONE**;
- Q2 rescue or redesign: **NONE**;
- Q3 started: **NO**;
- completed-2026 outcomes used: **0**;
- production F-ST/Sunday Signal behavior changed: **NO**.

Every Q2 workflow run from a head before this authorization is superseded for Stage-B evidence, whether successful, cancelled, or incomplete.

## Final frozen scientific identities

The final machine registry is `research/ats-nextgen/phase2_q2_final_preresult_registry.json`, created at parent `646177f2d6fa718a4af7eba591c142229db2d40f` and bound to reporting-complete parent `71aeb5734ceaf2b6c384f88f68314442b205272e`.

Scientific implementation blobs are:

- distribution core: `d551c4d3dbaa808556e3183fd65d6d20e8e92212`;
- nested experiment driver: `9249b39ebc2c42e4013a13b763d010c75939bd74`;
- reporting contract: `596b9ede2c5c1f15bcac440d07dd8cb80e03339e`;
- historical runner: `af73910ce78c51e18b879d6175a8873f11bae40e`;
- core tests: `4a691a354b1e577fb64ae66767bee6eb2e985fc2`;
- experiment/reporting tests: `339fc5d8d315767d860f4d079a9c43a0304ba6d0`;
- dedicated Stage-B workflow: `1c5c000ada73cfe458c69a1e440bafbbb1a2ca75`;
- opening receipt: `548c60fbaf44cb10fb47bfed3255ed30feb1cbae`;
- reporting/scoring receipt: `23a595ed7bbab8ff7eabd59225bc533d2230b85f`;
- implementation receipt after reporting completion: `19b12517fc5d22ae14f479d9c3014e1d111b08fa`;
- final pre-result machine registry: `151feaec8922d226d9da5dd45716503d596416de`.

The reporting contract now includes, before results, all required primary/secondary evidence: discrete CRPS/RPS, multinomial CPL log loss, non-push cover Brier/log loss, cover calibration intercept/slope where estimable, fixed-decile cover reliability, push calibration, expected/median margin error, equal-tailed 50/80/90% interval coverage and width, fixed slices, and direct key-margin mass calibration at `|M|={3,6,7,10,14}`.

## Mandatory upstream proofs before first Q2 fit

The runner must reproduce, before Q2 fitting:

- Phase-2 gate SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- Stage-A Q1 OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- exact Stage-A Q1 median predictions by `game_id` for outer seasons 2022–2025.

## Evidentiary rule

The first potentially acceptable Q2 historical result is the dedicated Stage-B workflow triggered by **this authorization commit**, and only if:

1. the exact-head Q2 contract job succeeds;
2. the historical job begins only through `needs: contract`;
3. all frozen upstream identities reproduce before the first Q2 fit;
4. the frozen 12-arm experiment completes without endpoint/chronology failure;
5. all frozen proper-score, calibration, interval, fixed-slice, reliability and key-mass evidence is emitted;
6. protected production surfaces remain unchanged; and
7. the complete immutable Q2 artifact is uploaded.

The branch must remain unchanged while that workflow runs. No result from an earlier head may be interpreted, combined with, or used to alter Q2 V1.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
