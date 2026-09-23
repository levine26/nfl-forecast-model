# ATS Next-Generation Phase 2 — Stage D Execution Authorization

**Status:** AUTHORIZED; NO STAGE-D RESULT EXISTS AT THIS RECEIPT  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Stage:** D — final evidence synthesis and uncertainty

## Contract evidence

The contract-only Stage-D head `67fcd04688dea3d5ec9400d4590dd8c7da5dad23` passed the dedicated Stage-D contract workflow:

- workflow run: `35935482365`
- contract job: `107431443312`
- conclusion: `success`
- frozen tests: passed
- accepted Q1/Q2/Q3 evidence-boundary checks: passed
- protected production-surface diff proof: passed
- historical Stage-D synthesis was **not reachable** on that validated head.

## Authorized execution

The workflow may now expose exactly one synthesis job behind `needs: contract`. On every execution head, the contract must pass again before synthesis begins. The synthesis job must verify the frozen Stage-D engine, runner, tests, and opening receipt/registry blob identities before invoking the runner.

The authorized runner may only:

1. regenerate the already accepted Q1 and Q3 evidence through their frozen runners;
2. require exact accepted evidence-file SHA-256 matches;
3. preserve Q2 as structurally invalid/unavailable;
4. compute the frozen 10,000-draw `(season, week)` paired uncertainty diagnostics and fixed simple hit-rate interval;
5. emit/upload the Stage-D evidence package.

It may not change the candidate set, bootstrap design, features, slices, thresholds, seed, comparison nulls, historical support, juice assumptions, candidate classifications, completed-2026 firewall, or production forecasting.

Any synthesis run from a head that does not independently re-pass the Stage-D contract is invalid and must not be accepted.
