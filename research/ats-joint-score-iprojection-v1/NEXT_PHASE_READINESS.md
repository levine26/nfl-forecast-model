# ATS-JSIP-V1 — Next-Phase Readiness Receipt

**Status:** READY FOR IMPLEMENTATION / HISTORICAL EXECUTION PHASE  
**Candidate:** `ATS-JSIP-V1`  
**Branch:** `research/ats-joint-score-iprojection-v1`  
**Base main SHA:** `5c2ce8a966449836b4e434ecedd6f6ea01d9622c`  
**Production changed:** NO  
**Completed-2026 outcomes used:** 0

## Pre-result controlling history

The candidate was frozen before implementation or target-season scoring through:

1. `930320c94ffc1d554f72589328b48a98a3373662` — initial frozen preregistration;
2. `f67cd216b73ee1861e8019c2eb6553438c3aeb64` — pre-result Amendment 001 freezing the inherited 100-row inner-training floor;
3. `50264684a74b34dbb1d9fa3b4c6c4455c6e111d3` — novelty/research audit documenting why the candidate is not Q2 rescue or Market Manifold V2 repetition.

The preregistration plus Amendment 001 are jointly controlling. No target-season candidate probability, CPL score, hit rate, ROI, or completed-2026 outcome was inspected to make either freeze decision.

## Resolved blocking issue

The previously identified Q2 overlap is resolved.

Authoritative repository history establishes that Q2 was a **one-dimensional margin-distribution** candidate on hard folded support `[-75,+75]` and failed structurally before accepted complete outer OOF scoring. `ATS-JSIP-V1` is a **two-dimensional home/away final-score** model with adaptive non-folded numerical support. It uses market total in team-score location, applies qualified paired-moneyline information in score-pair space, then marginalizes to the exact margin/CPL distribution.

Merely widening Q2 support remains forbidden.

## Frozen scientific target

Primary question: whether joint score geometry adds distributional ATS information beyond the canonical `KMASS-MARKETML-IPROJ` null.

Primary target seasons: `2022–2025`.

Primary selector: paired multinomial Cover/Push/Loss log loss on exact common rows.

Training chronology: expanding historical seasons from 2015 through `S-1` for target season `S`; nuisance selection uses only still-earlier inner validation seasons.

Primary null: `KMASS-MARKETML-IPROJ` with its accepted nuisance freeze and canonical row identity.

## Frozen input semantics

- spread line: qualified historical benchmark, exact horizon opaque;
- market total: qualified under the same historical semantics;
- paired moneylines: use only where populated and convert through the already-qualified no-vig procedure;
- historical spread-side juice: **not qualified**;
- missing side price: never replace with `-110` for probability construction;
- `REFERENCE_MINUS110`: allowed only as the already-defined labeled reporting sensitivity, never as the primary model probability or primary selector.

## Implementation checklist for the next phase

The next phase is authorized to add research-only implementation/tests/workflow for the frozen candidate and then execute the chronological historical experiment. Before target scoring, it must:

1. implement the adaptive nonnegative joint score grid with no endpoint folding;
2. implement the discretized Student-t team-score kernels and frozen `(df, scale)` grid;
3. implement prior-only league score-cell multipliers and frozen `alpha` grid;
4. implement expanding rolling-origin nuisance selection with minimum 100 eligible inner-training rows;
5. implement the qualified paired-ML minimum-KL sign projection while preserving tie mass;
6. marginalize score pairs to exact integer margin and CPL probabilities;
7. reproduce the canonical primary-null rows/hashes before candidate scoring;
8. implement all preregistered leakage, support, normalization, push, chronology, and production-firewall tests;
9. fail closed if any preflight invariant fails;
10. only after all preflight checks pass, generate 2022–2025 OOF target predictions and the frozen evidence package.

## Required next-phase artifacts

At minimum, the implementation/execution phase should leave immutable:

- research-only model source;
- unit/invariance tests;
- research-only GitHub Actions workflow;
- preflight receipt identifying the controlling preregistration commits;
- exact-row OOF prediction artifact with hash;
- primary-null reproduction receipt;
- primary and secondary metrics;
- deterministic paired week-block bootstrap evidence;
- per-season and preregistered diagnostic tables;
- result registry and classification receipt.

## Production firewall

Nothing in this readiness receipt authorizes production modification. F-ST / LevLine / Sunday Signal forecasting behavior, probabilities, fair lines, signals, and published outputs remain outside the candidate branch.

## Phase decision

The overlap/data/governance ambiguities that blocked implementation are resolved. The program is now ready to enter the next phase: **implement the frozen `ATS-JSIP-V1` challenger and run its chronology-correct historical 2022–2025 evaluation without redesigning the candidate after results are visible.**
