# Phase 4 Holdout Failure Log

**Program:** LevLine Spread & Points Next-Generation Research Program  
**Phase:** 4 — Historical Validation, Ablation & Model Selection  
**Purpose:** preserve failed execution attempts and make the 2025 evidence boundary auditable.

## Holdout state before the successful preflight

The machine-readable opening receipt was committed at `362af7af7db43a715b9ab9537a52d2749c37e7a6` with `holdout_state_at_receipt = UNOPENED` before any A0/B0/C0 2025 scoring.

### Attempt 1 — run 35818155884

- head: `872101230002a40636f44db50cb07a59ab93f229`
- workflow: `Spread & Points Phase 4 holdout validation`
- outcome: **FAILURE BEFORE HOLDOUT EXECUTION**
- frozen Phase 3 contract tests: **24 passed**
- Phase 4 test collection: **failed**
- defect: pytest loaded `phase4/test_phase4.py` as a standalone test module, so its package-relative import (`from ..phase3 ...`) had no known parent package.
- preflight hash step: skipped after the test failure.
- protected-production diff step: skipped after the test failure.
- 2025 holdout job: **SKIPPED; no steps executed**.
- 2025 challenger predictions/metrics inspected: **NO**.

This was a pure test-import/infrastructure defect. It did not change any frozen candidate estimator, feature, transformation, tuning, market, simulation, or source contract.

### Attempt 2 — run 35818294820

- head: `338c8c26e808549d3b464ed7bb076c0abbaf947b`
- workflow: `Spread & Points Phase 4 holdout validation`
- outcome: **CANCELLED AFTER THE SAME PRE-HOLDOUT TEST FAILURE**
- frozen Phase 3 contract tests: **24 passed**
- Phase 4 test collection: **failed with the same package-relative pytest import error**
- 2025 holdout job: **cancelled with no steps executed**.
- 2025 challenger predictions/metrics inspected: **NO**.

The workflow concurrency policy cancelled this obsolete attempt as a newer corrected head was pushed. The holdout remained unopened by these two attempts.

## Correction

The correction changed only the Phase 4 test import mechanism so pytest imports the hyphenated research package through `importlib`. It did not modify A0, B0, C0, the frozen Phase 3 implementation/config hashes, the holdout contract, the game-inclusion policy, or any scientific decision rule.

Corrected head entering the first successful pre-holdout gate:

`f0b92217488a1a000bee74a903a9437931a53230`

The one-time 2025 holdout is considered opened only after that corrected head passes the complete pre-holdout gate and begins the `Frozen one-time 2025 A0/B0/C0 package` job.
