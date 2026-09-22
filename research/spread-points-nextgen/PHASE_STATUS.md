# Spread & Points Next-Generation — Phase Status

**Program:** LevLine spread setting, team-point, margin, total, and joint-score research  
**Authority:** `MASTER_PLAN.md`  
**Last updated:** 2026-09-21 America/Los_Angeles  
**Phase-0 base main:** `536d6ab712028e374b42815db106f9fcb5d28053`  
**Phase-0 governance merge:** `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25` via PR #512

Only one phase should normally be `IN PROGRESS`. Parallel lanes are permitted only within the active phase. Phase 1 is now the single active program phase. Parallel analytical lanes are permitted within Phase 1 under the shared evaluation contract.

| Phase | Name | Status | Primary branch | Supporting PR(s) | Key evidence / artifacts | Entry criteria | Exit criteria | Last updated | Exact next action |
|---|---|---|---|---|---|---|---|---|---|
| 0 | Master Program Initialization | **COMPLETE** | `docs/spread-points-nextgen-phase0` — merged | **#512 — MERGED** | Five canonical control files under `research/spread-points-nextgen/`; research firewall run `35691355664` **SUCCESS**; research validation run `35691355478` **SUCCESS**; merge `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25` verified from `main` | Existing repo accessible; current main and production boundary inspectable | **SATISFIED:** canonical plan/status/handoff/log/index merged to `main`; production firewall documented; future-chat protocol documented; docs-only diff verified; existing research firewall and validation gate passed; merged files re-read from `main` | 2026-09-21 | **STOP in the Phase 0 chat. Do not begin Phase 1 here.** |
| 1 | Current LevLine Audit, Baseline Reproduction & Error Decomposition | **IN PROGRESS** | `research/spread-points-nextgen-phase1` | None | Phase 1 audit artifacts under `research/spread-points-nextgen/phase1/` | Phase 0 COMPLETE | Architecture documented; reproducible baseline; market baselines; residual decomposition; full data/API inventory; leakage/PIT risks; concrete hypotheses; no major baseline uncertainty | 2026-09-21 | Establish the canonical evaluation contract, audit architecture/data/PIT in parallel, reproduce baselines, and decompose errors. Do not implement challengers. |
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

## Phase 0 validation record

PR #512 changed exactly five files, all under `research/spread-points-nextgen/`:

- `MASTER_PLAN.md`
- `PHASE_STATUS.md`
- `CURRENT_STATE_AND_NEXT_STEPS.md`
- `DECISION_LOG.md`
- `RESEARCH_INDEX.md`

No production code, outputs, workflows, site files, or frozen-model artifacts were changed.

Validation:

- `LevLine research firewall` run `35691355664`: **SUCCESS**
- `LevLine research validation` run `35691355478`: **SUCCESS**
  - foundation: success
  - v0.8 isolated regeneration: success
  - Phase 2 market reliance and horizon study: success
  - paired statistical uncertainty audit: success
  - margin disagreement forensics: success
  - research validation gate: success

The merged canonical files were then verified directly from `main` at merge SHA `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25`.
