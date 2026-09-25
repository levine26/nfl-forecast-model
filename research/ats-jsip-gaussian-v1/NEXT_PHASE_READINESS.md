# ATS-JSIP-GAUSSIAN-V1 — Next-Phase Readiness

**Status:** READY FOR IMPLEMENTATION AFTER PREREGISTRATION MERGE  
**Candidate:** `ATS-JSIP-GAUSSIAN-V1`  
**Production authorization:** NONE  
**Completed-2026 outcomes permitted:** 0

## Frozen successor decision

The immediate successor to failed `ATS-JSIP-V1` is `ATS-JSIP-GAUSSIAN-V1`.

The successor retains the original scientific hypothesis—joint home/away score geometry conditioned on spread, total, football score-lattice structure, and qualified moneyline information—but replaces the structurally infeasible Student-t kernel with a discretized Gaussian kernel.

This decision was made before implementation and before any 2022–2025 target candidate probability or proper score was generated.

## What is frozen

- target seasons: `2022–2025`;
- training chronology: seasons `2015..S-1` with rolling-origin inner validation;
- minimum eligible inner-training rows: `100`;
- Gaussian scale grid: `{8,10,12,14}`;
- lattice pseudocount grid: `{25,100,400}`;
- score support start: `0..80`;
- support increment: `20`;
- omitted-tail tolerance: `<1e-12` per team marginal;
- hard support ceiling: `200`;
- qualified paired-moneyline sign-mass I-projection with tie-mass preservation;
- primary null: `KMASS-MARKETML-IPROJ`;
- primary selector: paired multinomial CPL log loss;
- uncertainty: 10,000 season-stratified NFL-week block bootstrap resamples, seed `20260924`;
- advancement gate: exactly as specified in the preregistration;
- completed-2026 outcomes: forbidden;
- production changes: forbidden.

## Mandatory implementation sequence

The next phase must proceed in this order:

1. identify and reproduce the canonical primary-null data path and exact common-row identity;
2. implement the discretized nonnegative Gaussian score kernel;
3. implement adaptive non-folded support;
4. run the **all-legal-scale support-feasibility sweep** on canonical target inputs before any candidate target score is generated;
5. implement chronology-clean lattice multiplier fitting and `(sigma, alpha)` selection;
6. implement the qualified paired-moneyline projection;
7. implement exact score-pair-to-margin marginalization and CPL probabilities;
8. implement outcome-mutation, normalization, support, moneyline, push, chronology, identity, and production-firewall tests;
9. freeze the full scientific implementation commit;
10. only after every preflight invariant passes, generate 2022–2025 OOF candidate forecasts and frozen evidence.

If any preflight invariant fails, target scoring stops and the candidate is `FAILED` under this ID.

## Required implementation artifacts

The implementation/execution phase should leave immutable:

- research-only candidate source;
- unit and invariance tests;
- dedicated research workflow;
- primary-null reproduction receipt;
- Gaussian support-feasibility receipt;
- chronology/nuisance-selection receipt;
- preflight receipt identifying the controlling preregistration commit;
- exact-row OOF predictions with hash;
- primary and secondary metrics;
- deterministic bootstrap evidence;
- per-season and preregistered bucket diagnostics;
- final scientific classification and closeout receipt.

## Explicit stop point

This readiness document does **not** authorize implementation before the preregistration PR is canonical on `main`.

Once the preregistration PR is merged, the current phase is complete. The next phase is:

**IMPLEMENT THE FROZEN `ATS-JSIP-GAUSSIAN-V1` CANDIDATE, PASS PREFLIGHT, THEN RUN THE CHRONOLOGY-CORRECT 2022–2025 HISTORICAL EVALUATION.**
