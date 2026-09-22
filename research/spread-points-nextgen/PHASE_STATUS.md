# Spread & Points Next-Generation — Phase Status

**Program:** LevLine spread setting, team-point, margin, total, and joint-score research  
**Authority:** `MASTER_PLAN.md`  
**Last updated:** 2026-09-21 America/Los_Angeles  
**Phase-0 base main:** `536d6ab712028e374b42815db106f9fcb5d28053`

Only one phase should normally be `IN PROGRESS`. Parallel lanes are permitted only within the active phase.

| Phase | Name | Status | Primary branch | Supporting PR(s) | Key evidence / artifacts | Entry criteria | Exit criteria | Last updated | Exact next action |
|---|---|---|---|---|---|---|---|---|---|
| 0 | Master Program Initialization | **IN PROGRESS** | `docs/spread-points-nextgen-phase0` | Pending docs/governance PR | `MASTER_PLAN.md`; this registry; current-state handoff; decision log; research index; verified F-ST/Props/firewall evidence | Existing repo accessible; current main and production boundary inspectable | Canonical files merged to `main`; docs-only checks pass; production unchanged; final handoff marks Phase 0 complete | 2026-09-21 | Finish remaining control files, open/validate/merge docs-governance PR, verify from `main`, then mark Phase 0 COMPLETE and Phase 1 NOT STARTED |
| 1 | Current LevLine Audit, Baseline Reproduction & Error Decomposition | **NOT STARTED** | TBD | None | Future architecture/baseline/error/API reports | Phase 0 COMPLETE | Architecture documented; reproducible baseline; market baselines; residual decomposition; full data/API inventory; leakage/PIT risks; concrete hypotheses; no major baseline uncertainty | 2026-09-21 | Do not start until Phase 0 exit criteria are satisfied |
| 2 | Deep External Research & Challenger Design | **NOT STARTED** | TBD | None | Future literature/external-model reviews and preregistration | Phase 1 COMPLETE | Literature/external-model review; limited challenger shortlist; feature hypotheses; player/market-residual specs; preregistered evaluation and frozen holdout rules; data gaps identified | 2026-09-21 | Await Phase 1 completion |
| 3 | Controlled Challenger Implementation | **NOT STARTED** | TBD | None | Future candidate implementations/tests/contracts | Phase 2 COMPLETE | Selected challengers implemented; tests pass; provenance/as-of semantics intact; explicit versions; reproducible research outputs; production unchanged | 2026-09-21 | Await Phase 2 completion |
| 4 | Historical Validation, Ablation & Model Selection | **NOT STARTED** | TBD | None | Future holdout/ablation/uncertainty reports | Phase 3 COMPLETE | All preregistered challengers evaluated; holdout clean; ablations/uncertainty/robustness/market comparison complete; finalist or no-finalist determination documented | 2026-09-21 | Await Phase 3 completion |
| 5 | Prospective Shadow Validation & Operational Hardening | **NOT STARTED** | TBD | None | Future immutable receipts, grading, operational evidence | Phase 4 COMPLETE and credible finalist exists | Preregistered prospective evidence threshold satisfied; operational reliability demonstrated | 2026-09-21 | Await Phase 4 completion |
| 6 | Final Synthesis & Promotion Package | **NOT STARTED** | TBD | None | Future final synthesis, migration, rollback, monitoring package | Phase 5 COMPLETE | Full promotion package complete and presented; then STOP for explicit user green light | 2026-09-21 | Await Phase 5 completion |

## Status semantics

- `NOT STARTED`: entry criteria are not yet satisfied or work has not begun.
- `IN PROGRESS`: this is the single active program phase.
- `BLOCKED`: a genuine external or scientific blocker prevents exit criteria from being satisfied.
- `COMPLETE`: all exit criteria are satisfied, evidence is committed, and handoff/status files are updated.

## Phase transition rule

A phase transition is not justified by code existing. The phase’s stated exit criteria must be satisfied and recorded in this file plus `CURRENT_STATE_AND_NEXT_STEPS.md`.

Material reordering, collapsing, skipping, or redefining phases requires documented empirical necessity in `DECISION_LOG.md` and explicit user approval when it materially changes the program.
