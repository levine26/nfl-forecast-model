# ATS Next-Generation — Q2 Stage B Exact-Head Execution Authorization

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** B — Q2 only  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Status:** **PRE-RESULT; CLEAN EXECUTION AUTHORIZED ONLY AFTER EXACT-HEAD CONTRACT SUCCESS**  
**Branch:** `research/ats-nextgen-phase2-q2`  
**Stage-B base:** `a2581a62e3797a6ac466d614326bc72b7d5a1c57`  
**Clean pre-authorization parent:** `5c67c0c55f6f8a23a9036866075209f083f04981`

## Purpose

This receipt does not alter the scientific model, search surface, scoring rules, or reporting contract frozen in the Stage-B opening, implementation, and scoring receipts. It exists solely to establish a clean evidentiary head after removal of an unused exploratory runtime module that was never part of the frozen Q2 scientific implementation and was never called by the accepted Q2 runner or workflow.

At this receipt boundary:

- accepted Q2 historical result: **NONE**;
- Q2 result interpretation/classification: **NONE**;
- Q2 rescue or redesign: **NONE**;
- Q3 started: **NO**;
- completed-2026 outcomes used: **0**;
- production F-ST/Sunday Signal behavior changed: **NO**.

## Frozen scientific identities remain unchanged

The authoritative Stage-B implementation remains exactly the blobs frozen by `Q2_STAGE_B_IMPLEMENTATION_RECEIPT.md`:

- distribution core: `d551c4d3dbaa808556e3183fd65d6d20e8e92212`;
- nested experiment driver: `9249b39ebc2c42e4013a13b763d010c75939bd74`;
- reporting contract: `f7bc779e402b2d05230008b1779665484e9f11a6`;
- historical runner: `36612cdb6517b1a3f2c777720fc7aa0458ec99f7`;
- core tests: `4a691a354b1e577fb64ae66767bee6eb2e985fc2`;
- experiment/reporting tests: `943dba552d61165fb8f196582cd31af1585ab281`;
- dedicated Stage-B workflow: `d261d6d92a25aaedf477e99bdde939ed1727a04f`.

Upstream identities that must reproduce before the first Q2 fit remain:

- Phase-2 gate SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- Stage-A Q1 OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- exact Stage-A Q1 median predictions by `game_id` for outer seasons 2022–2025.

## Evidentiary rule

Every Q2 historical workflow run whose PR head predates this authorization commit is superseded for Stage-B evidentiary purposes, regardless of whether it later completes successfully. The first potentially acceptable Q2 historical result is the dedicated Stage-B workflow triggered by this authorization (or a later non-scientific receipt-only head) where:

1. the exact-head Q2 contract job succeeds;
2. the historical job begins only through `needs: contract`;
3. all frozen upstream identities reproduce before the first Q2 fit;
4. the frozen 12-arm experiment completes without endpoint/chronology failure;
5. protected production surfaces remain unchanged; and
6. the complete immutable Q2 evidence artifact is uploaded.

No result from an earlier head may be used to alter, rescue, or tune Q2 V1.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.
