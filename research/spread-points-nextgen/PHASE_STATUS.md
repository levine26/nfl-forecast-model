# Spread & Points Next-Generation — Phase Status

**Program:** LevLine spread setting, team-point, margin, total, and joint-score research  
**Authority:** `MASTER_PLAN.md`  
**Last updated:** 2026-09-22 America/Los_Angeles  
**Phase-0 base main:** `536d6ab712028e374b42815db106f9fcb5d28053`  
**Phase-0 governance merge:** `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25` via PR #512

Phase 2 is **COMPLETE**. Phase 3 is **NOT STARTED**. The next chat must begin from the merged Phase 2 contract; no Phase 3 implementation occurred during Phase 2.

| Phase | Name | Status | Primary branch | Supporting PR(s) | Key evidence / artifacts | Entry criteria | Exit criteria | Last updated | Exact next action |
|---|---|---|---|---|---|---|---|---|---|
| 0 | Master Program Initialization | **COMPLETE** | `docs/spread-points-nextgen-phase0` — merged | **#512 — MERGED** | Five canonical control files under `research/spread-points-nextgen/`; research firewall run `35691355664` **SUCCESS**; research validation run `35691355478` **SUCCESS**; merge `7a1dc92d7b79eba9e6e77edf097ff05e3de15c25` verified from `main` | Existing repo accessible; current main and production boundary inspectable | **SATISFIED:** canonical plan/status/handoff/log/index merged to `main`; production firewall documented; future-chat protocol documented; docs-only diff verified; existing research firewall and validation gate passed; merged files re-read from `main` | 2026-09-21 | **STOP in the Phase 0 chat. Do not begin Phase 1 here.** |
| 1 | Current LevLine Audit, Baseline Reproduction & Error Decomposition | **COMPLETE** | `research/spread-points-nextgen-phase1` — merged | **#513 — MERGED** | `phase1/EVALUATION_CONTRACT.md`; architecture, baseline, error, data/API, PIT and synthesis reports; final audit artifact `10699778876`; merge `a4f7172c0c4ff82b1689411181e7a9042a1628a8` | Phase 0 COMPLETE | **SATISFIED:** architecture documented; reproducible 2022–2025 baseline; market baselines and paired uncertainty; residual decomposition; data/API inventory; leakage/PIT register; Phase 2 hypotheses; final post-sync firewall/validation/audit all green | 2026-09-22 | **STOP Phase 1.** Phase 2 must continue from merged Phase 1 evidence; do not rerun the audit. |
| 2 | Deep External Research & Challenger Design | **COMPLETE** | `research/spread-points-nextgen-phase2` — merged | **#520 — MERGED** | Phase 2 canonical package; bounded A0/B0/C0 preregistration; deterministic nested protocol; PIT source matrix; red-team closeout; exact-head firewall `35751402751`; exact-head validation `35751402726`; merge `405906942013252c158244c9b033a3240baa37f8` | Phase 1 COMPLETE | **SATISFIED:** research questions translated; literature/external-model/Sasser review complete; evidence quality classified; A0/B0/C0 bounded; D conditional; 2025 holdout and 2026 firewall frozen; data/PIT/paid-data policies recorded; production unchanged; synchronized head `076dc9d6f6c052eec4744a155070c42c1b99ae82`; exact-head CI green; PR merged; all canonical artifacts re-read from `main` | 2026-09-22 | **STOP Phase 2. Phase 3 remains NOT STARTED.** Next chat must read the merged control files and execute the frozen Phase 3 handoff without reopening Phase 1/2. |
| 3 | Controlled Challenger Implementation | **NOT STARTED** | TBD | None | Future candidate implementations/tests/contracts | **Phase 2 COMPLETE** | Selected challengers implemented; tests pass; provenance/as-of semantics intact; explicit versions; reproducible research outputs; production unchanged | 2026-09-22 | Begin only in the next Phase 3 execution chat from the frozen A0/B0/C0 contract; do not score 2025. |
| 4 | Historical Validation, Ablation & Model Selection | **NOT STARTED** | TBD | None | Future holdout/ablation/uncertainty reports | Phase 3 COMPLETE | All preregistered challengers evaluated; holdout clean; ablations/uncertainty/robustness/market comparison complete; finalist or no-finalist determination documented | 2026-09-21 | Await Phase 3 completion |
| 5 | Historical F-ST-Anchored Winner Integration (Candidate 5) | **NOT STARTED** | TBD | None | Future `LEVLINE-HISTORICAL-RESIDUAL-STACK-V1` charter, OOF stacking/evidence-boundary contracts, ablations, historical results and freeze receipt | Phase 4 COMPLETE; underlying A0/B0/C0/D dispositions frozen; 2022-2024 OOF component surfaces preserved; Candidate 5 evidence boundary and preregistration frozen | OOF provenance proven; mandatory ablations/guardrails complete; truthful evidence boundary; Candidate 5 rejected/inconclusive/eligible for prospective shadow; production unchanged | 2026-09-22 | Await Phase 4 completion; do not start Candidate 5 early. |
| 6 | Prospective Shadow Validation & Operational Hardening | **NOT STARTED** | TBD | None | Future immutable receipts, Candidate 5/Next-Gen shadow evidence, grading and operational evidence | Phase 5 COMPLETE and at least one credible finalist is eligible | Preregistered prospective evidence threshold satisfied; operational reliability demonstrated | 2026-09-22 | Await Phase 5 completion. Candidate 4 continues independently in the Adaptive program. |
| 7 | Final Synthesis & Promotion Package | **NOT STARTED** | TBD | None | Future final synthesis, migration, rollback, monitoring package | Phase 6 COMPLETE | Full promotion package complete and presented; then STOP for explicit user green light | 2026-09-22 | Await Phase 6 completion |

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

## Phase 1 validation record

Final post-sync Phase 1 candidate head: `b6b831fd1a77180e8dc97a0eb17495bbdee44ba5`.

- `LevLine research firewall` run `35741337735`: **SUCCESS**
- `LevLine research validation` run `35741337942`: **SUCCESS**
- `Spread points Phase 1 audit` run `35741337832`: **SUCCESS**
- Dedicated Phase 1 evidence artifact: `10699778876`
- artifact digest: `sha256:c85bc49458631c6f9b9a14e0a21f1eb213b527017e20ddcc125e9e23b484e0e1`
- PR #513 merge commit: `a4f7172c0c4ff82b1689411181e7a9042a1628a8`

The final exact-head audit regenerated the canonical 1,087-game 2022–2025 baseline, passed helper tests, generated error/structural/team-points evidence, and verified protected production surfaces were unchanged. The merged package was then re-read from `main`.

## Phase 2 final validation and merge record

- primary branch: `research/spread-points-nextgen-phase2` — merged
- primary PR: **#520 — MERGED**
- final synchronized pre-merge `main`: `e93127963c76cd309cdddf17d91291c04a60a659`
- final validated Phase 2 head: `076dc9d6f6c052eec4744a155070c42c1b99ae82`
- final exact-head research firewall run `35751402751`: **SUCCESS**
- final exact-head research validation run `35751402726`: **SUCCESS**
  - foundation: success
  - v0.8 isolated regeneration: success
  - Phase 2 market reliance and horizon study: success
  - paired statistical uncertainty audit: success
  - margin disagreement forensics: success
  - research validation gate: success
- PR #520 merge commit: `405906942013252c158244c9b033a3240baa37f8`
- all eleven canonical Phase 2 artifacts plus the four control files were re-read successfully from `main` after merge
- production forecast code/model behavior: **UNCHANGED**
- 2025 A0/B0/C0 challenger outcomes inspected in Phase 2: **NO**
- completed-2026 outcomes used for candidate selection: **NO**
- paid-data dependency requested: **NO**
- Phase 3: **NOT STARTED**

## Candidate 5 roadmap amendment record

Governance-only amendment:

- amendment branch: `docs/spread-points-candidate5-program-amendment`
- PR: **#545 — MERGED**
- validated head: `86bc790a47573833b3ede934784d5997c26f571d`
- research firewall run `35795292921`: **SUCCESS**
- full research validation run `35795292923`: **SUCCESS**
- merge commit: `e51a066edfb17b292e4823a8f4696470b2da7703`
- changed surface: five canonical `research/spread-points-nextgen/` control files only
- Phase 3 implementation: **NOT STARTED**
- Candidate 5 implementation/training: **NOT STARTED**
- production F-ST / Sunday Signal behavior: **UNCHANGED**

This amendment inserts Phase 5 Candidate 5 historical F-ST-anchored integration, renumbers prospective shadow validation to Phase 6, and renumbers final synthesis/promotion to Phase 7. It does not alter the immediate Phase 3 next action.
