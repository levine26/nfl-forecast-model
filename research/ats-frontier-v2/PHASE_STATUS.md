# PHASE STATUS

Program: `LEVLINE_ATS_FRONTIER_V2`

| Phase | State | Notes |
|---|---|---|
| Phase 1 — Failure synthesis & deep research | `COMPLETE` | Research program, failure atlas, source review and mechanism shortlist merged. |
| Phase 2 — Data qualification | `COMPLETE` | Historical/prospective data feasibility and source qualification frozen. |
| Phase 3 — Final architecture design & preregistration | `COMPLETE` | M3/M4 historical identities, nulls, chronology, grids, ablations, evaluation and prospective M1/M2 identities frozen before fitting. |
| Phase 4 — Controlled historical development, ablation & empirical validation | `EVIDENCE_COMPLETE__PENDING_REPOSITORY_MERGE` | Final canonical chronology-clean M3/M4 evidence package exists; primary PR/merge and immutable post-merge receipt remain. |
| Phase 5 — Scientific synthesis & survivor freeze | `NOT_STARTED` | Do not classify survivors until Phase 4 is fully merged and closed. |
| Phase 6 — Prospective shadow validation | `NOT_STARTED` | No Phase-4 result authorizes shadowing by itself. |
| Phase 7 — Production decision | `NOT_STARTED` | Production remains frozen. |

## Phase-4 accepted evidence state

Final canonical execution: workflow run `36025444929`, artifact `10820397832`.

Canonical execution commit: `7eda9cacd471a3161424699958509c02a260fc05`.

Validated scientific head: `c1eead294c5ac897041fc35f628b2fec393ab064`.

- M3 `FV2-HIST-M3-DSSM-01`: `NEGATIVE_PRIMARY_EVIDENCE` versus `M3-NULL-MARKET-NORMAL-01`.
- M4 `FV2-HIST-M4-DMARGIN-01`: `POSITIVE_PRIMARY_EVIDENCE` versus `M4-NULL-STUDENTT-CONSTANT-01`, with the preregistered ablation showing essentially all improvement is reproduced by the key-mass component rather than conditional scale.
- formal Phase-5 disposition: `NOT_APPLIED`.
- completed-2026 outcomes used: `0`.
- production changed: `NO`.
- red-team audit: `PASS`.

Corrected workflow run `36025306390` remains preserved as a successful reproducibility execution. It is scientifically consistent with the canonical package but not byte-identical; the M4 primary paired delta differs by approximately `7.35e-9`, with no change in selected hyperparameters, per-season direction, uncertainty conclusion, ablation attribution or Phase-4 evidence labels. See `PHASE4_REPRODUCIBILITY_NOTE.md`.

Workflow run `36023376614` remains explicitly invalid/unaccepted; its metrics are not part of the scientific record.

## Current repository action

Reconcile current `main`, validate the Phase-4 branch through exact-head research firewall/validation, merge the Phase-4 research package if clean, verify merged `main`, then create and merge the immutable Phase-4 closeout receipt. Only after that may Phase 5 begin.
