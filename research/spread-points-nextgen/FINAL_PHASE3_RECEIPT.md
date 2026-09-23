# Spread & Points Phase 3 — Final Completion Receipt

**Recorded:** 2026-09-22 America/Los_Angeles  
**Program:** LevLine Spread & Points Next-Generation Research Program  
**Scope:** GitHub integration/governance closeout only; no Phase 4 work and no Candidate 5 training.

## Final status

- Phase 0 — **COMPLETE**
- Phase 1 — **COMPLETE**
- Phase 2 — **COMPLETE**
- Phase 3 — **COMPLETE**
- Phase 4 — **NOT STARTED**
- Phase 5 Candidate 5 — **NOT STARTED**
- Production — **F-ST-01-FROZEN-2026**, unchanged

This receipt supersedes any pre-merge Phase 3 control-file wording that still says `merge pending`, `PR pending`, or otherwise describes Phase 3 as not yet merged. It does not supersede the frozen scientific results, candidate identities, evidence, or governance constraints.

## Final synchronized Phase 3 integration

- Phase 3 branch: `research/spread-points-nextgen-phase3`
- current-main production/output refresh preserved before merge: `20c583224e6b1788387de7b02d7f6fb0e3eeeefd`
- final synchronized Phase 3 head: `8c061cd400a6bb52a037d5e98880efd19a451fcb`
- synchronization method: true merge of current `main` into the Phase 3 branch, preserving the newer `outputs/market_t120_research.csv`, `outputs/run_history.csv`, `outputs/status.json`, and `outputs/this_week.csv` blobs exactly from `main`
- Phase 3 PR: **#547 — MERGED**
- Phase 3 merge SHA: `d4d29d8c2340864e2d9e4bcd793852e8643be80c`

## Exact synchronized-head CI

All required checks passed on exact head `8c061cd400a6bb52a037d5e98880efd19a451fcb`:

- Spread & Points Phase 3 validation — run `35813365004`: **SUCCESS**
  - Phase 3 contract and firewall tests: success
  - 2022–2024 chronology-safe regeneration: success
  - regenerated evidence matched the frozen committed evidence: success
  - protected production surfaces unchanged: success
  - exact-run gate: success
- LevLine research firewall — run `35813364985`: **SUCCESS**
- LevLine research validation — run `35813364975`: **SUCCESS**

The older successful checks on pre-sync head `2de56362b199cc30cc0c067e9cde73332675bd0f` remain historical evidence only; the merge relied on the fresh synchronized-head checks above.

## Frozen Phase 3 scientific disposition

No scientific result was changed during synchronization or merge.

- A0 margin MAE: **9.8825**
- A0 total MAE: **10.3869**
- B0 margin MAE: **10.2132**
- B0 total MAE: **11.3044**
- exact market M0 margin MAE: **9.4184**
- exact market M0 total MAE: **10.1209**
- C0 M3 margin MAE: **9.4390**
- C0 M3 total MAE: **10.1376**
- C0 margin: **NO_INCREMENTAL_FOOTBALL_EDGE**
- C0 total: **NO_INCREMENTAL_FOOTBALL_EDGE**
- D margin: **ENSEMBLE_NOT_ELIGIBLE**
- D total: **ENSEMBLE_NOT_ELIGIBLE**

## Evidence and firewall confirmation from merged main

Post-merge verification from `main` confirmed the Phase 3 implementation and durable evidence package, including the candidate registry, development evaluation, D eligibility receipt, run manifest, OOF surfaces, and future Candidate 5 OOF component surface.

The frozen run manifest remains authoritative for the Phase 3 evidence boundary:

- loaded seasons: **2016–2024 only**
- development target seasons: **2022–2024 only**
- 2025 loaded: **false**
- 2025 challenger scored: **false**
- completed 2026 outcomes used for selection: **false**
- Candidate 5 trained: **false**
- production model: **F-ST-01-FROZEN-2026**, unchanged

No production forecasting code or Sunday Signal forecasting behavior was modified by the Phase 3 closeout.

## Exact next action

**STOP after this receipt is merged. Do not begin Phase 4 in the Phase 3 closeout task.**

The next program action, in a separate Phase 4 task, is to execute the frozen **Historical Validation, Ablation & Model Selection** phase. Phase 4 owns the one-time 2025 underlying-model holdout for the already-frozen, methodologically valid A0/B0/C0 references and the preregistered comparisons/ablations. It must preserve the existing evidence boundary and may not train Candidate 5.

Candidate 5 remains **NOT STARTED** until Phase 4 is complete and its separate Phase 5 entry criteria are satisfied.
