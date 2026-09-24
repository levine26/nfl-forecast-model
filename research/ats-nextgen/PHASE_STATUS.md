# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `FINAL_PHASE2_RECEIPT.md`, candidate result receipts/registries, and `PHASE2_STAGE_D_RESULT_RECEIPT.md` / `phase2_stage_d_result_registry.json`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Authoritative identity | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | PR #556 / merge `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6` | design frozen | closed |
| 2 | Controlled Implementation & Historical Development | **COMPLETE — SCIENTIFIC CLOSEOUT MERGED** | corrective PR #566 / merge `89f8b4fa48e22554029392b303225e4665b4b673` | Q1 negative; Q2 structurally invalid; Q3 negative; Stage-D uncertainty complete | merge this governance-only closeout, verify `main`, then open Phase 3 from that exact head |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **NOT STARTED / READY AFTER GOVERNANCE CLOSEOUT** | none | frozen Phase-2 evidence available | create immutable Phase-3 opening receipt from verified final `main`; classify only, no rescue/redesign |
| 4 | Prospective Shadow Validation | **CONDITIONAL / NOT STARTED** | none | unavailable | only if Phase 3 earns eligibility and continuation is explicitly authorized |

## Phase-2 scientific closeout identity

- corrective merge vehicle PR #566;
- validated corrective head `0ceae72f2643cc9b10a6cf35181576d52bb2fdf7`;
- scientific closeout merge `89f8b4fa48e22554029392b303225e4665b4b673`;
- merged tree `97086a3e35c6e4c4275662e9ab437cd46a883d2b`;
- all eight exact-head validation workflows succeeded before merge;
- completed-2026 outcomes used: `0`;
- production forecasting changed: `no`.

## Stage-D provenance authority

The scientific origin of the accepted Stage-D result remains PR #564 / branch `research/ats-nextgen-phase2-stage-d-accepted-artifacts`:

- accepted evidence head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588` — SUCCESS;
- artifact `10783982962`;
- digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`;
- 10,000 paired `(season, week)` bootstrap draws, seed 26, 72 blocks.

PR #563's regeneration-based Stage-D evidence-loading path is superseded for provenance. PR #564 was closed unmerged only as a merge vehicle after divergence. PR #565 was closed unmerged and is not authoritative. PR #566 carried the corrected already-validated Stage-D closeout onto current `main`.

## Frozen Phase-2 candidate state

### Q1 — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`

- accepted OOF rows: 1,087 (2022–2025);
- Q1 minus M2 mean-three-quantile pinball `+0.0001307887665715768`;
- paired 95% CI `[-0.002378435765685505, +0.002555544033066125]`;
- probability Q1 better `0.4554`;
- Phase-2 state: **valid negative incremental result**.

### Q2 — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

- frozen support `[-75,+75]`;
- endpoint-mass threshold `0.001`;
- observed maximum folded endpoint mass `0.0033487075822347966`;
- no valid accepted OOF or proper-score result;
- complementarity and Q2/Q3 blend unavailable;
- Phase-2 state: **structurally invalid under frozen V1 support/truncation contract**.

### Q3 — `ATS-Q3-DIRECT-CPL-HURDLE-V1`

- accepted OOF rows: 1,087 (2022–2025);
- Q3 minus Q3-M2 CPL log loss `+0.0013157418572419255`;
- paired 95% CI `[-0.0015590942193462521, +0.004336647782633088]`;
- probability Q3 better `0.1842`;
- non-push Brier delta `+0.0006716459171549338`;
- Phase-2 state: **valid negative incremental result — not incremental versus Q3-M2**.

## Interpretation boundary

Phase 2 produced no positive historical-development candidate under the preregistered incremental tests. The Q1/Q3 uncertainty intervals crossing zero show uncertainty about effects of very small magnitude; they do not transform adverse point results into passed incremental tests and do not prove large harmful effects.

Phase 3 owns the formal `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` labels. The Evaluation Protocol requires primary proper/quantile improvement over the relevant market null for prospective-shadow eligibility.

No completed-2026 outcome signal has been used. Historical 2022–2025 evidence remains development/non-pristine. Production remains unchanged.
