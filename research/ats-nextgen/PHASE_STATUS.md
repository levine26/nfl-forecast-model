# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `FINAL_PHASE2_RECEIPT.md`, `PHASE3_OPENING_RECEIPT.md`, `PHASE3_EVIDENCE_SYNTHESIS.md`, `phase3_candidate_registry.json`, `FINAL_PHASE3_RECEIPT.md`, `PHASE3_POST_MERGE_CLOSEOUT.md`, candidate result receipts/registries, and `PHASE2_STAGE_D_RESULT_RECEIPT.md` / `phase2_stage_d_result_registry.json`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Authoritative identity | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | PR #556 / merge `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6` | design frozen | closed |
| 2 | Controlled Implementation & Historical Development | **COMPLETE — SCIENTIFIC + GOVERNANCE CLOSEOUT MERGED** | scientific PR #566 / `89f8b4fa48e22554029392b303225e4665b4b673`; governance PR #567 / `a5c7bf6c37b9d1b385bfe88bd1a329ddd3bb63f0` | Q1 negative; Q2 structurally invalid; Q3 negative; Stage-D uncertainty complete | closed |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **COMPLETE — MERGED TERMINAL V1 CLASSIFICATION** | PR #568 / validated head `2fa575f8d570d025d55395ac9951390ab6910a01` / merge `1dff4e9c9a3960dd79610b5b1d22c13f991f9dc5` | 3 REJECTED / 0 INCONCLUSIVE / 0 ELIGIBLE; no new predictions/refits | closed |
| 4 | Prospective Shadow Validation | **NOT AUTHORIZED / NOT STARTED** | none | no eligible candidate | do not start; requires a future eligible candidate under a new explicitly authorized research amendment/version |

## Phase-3 merged identity

- verified Phase-3 base / Phase-2 governance merge: `a5c7bf6c37b9d1b385bfe88bd1a329ddd3bb63f0`;
- Phase-3 branch: `research/ats-nextgen-phase3`;
- immutable opening-receipt commit: `d2be05c3f74e5b6095a9714bd58e7f0984c59276`;
- validated Phase-3 head: `2fa575f8d570d025d55395ac9951390ab6910a01`;
- PR #568 merge: `1dff4e9c9a3960dd79610b5b1d22c13f991f9dc5`;
- completed-2026 outcomes used: `0`;
- production forecasting changed: `no`.

## Final V1 classifications

### Q1 — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`: **REJECTED**

Reason: `FAILED_PRIMARY_INCREMENTAL_QUANTILE_GATE`.

- valid chronology-clean V1 execution;
- accepted OOF rows: 1,087;
- Q1 − M2 mean-three-quantile pinball: `+0.0001307887665715768` (lower is better; adverse);
- paired 95% CI: `[-0.002378435765685505, +0.002555544033066125]`;
- P(Q1 better): `0.4554`;
- interval crossing zero limits claims of harm but does not satisfy the required positive incremental gate.

### Q2 — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`: **REJECTED**

Reason: `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`.

- frozen support `[-75,+75]`;
- endpoint-mass threshold `0.001`;
- observed maximum folded endpoint mass `0.0033487075822347966`;
- no complete valid accepted Q2 OOF or primary proper-score result exists;
- Q2 complementarity and Q2/Q3 blend remain unavailable;
- no support widening/reconstruction/rescue is authorized.

### Q3 — `ATS-Q3-DIRECT-CPL-HURDLE-V1`: **REJECTED**

Reason: `FAILED_PRIMARY_INCREMENTAL_PROPER_SCORE_GATE`.

- valid chronology-clean V1 execution;
- accepted OOF rows: 1,087;
- Q3 − Q3-M2 CPL log-loss: `+0.0013157418572419255` (lower is better; adverse);
- paired 95% CI: `[-0.0015590942193462521, +0.004336647782633088]`;
- P(Q3 better): `0.1842`;
- non-push Brier delta: `+0.0006716459171549338`;
- Q3 cover-calibration slope `0.27094382668690847` vs Q3-M2 `0.8130523437112027`;
- interval crossing zero limits claims of harm but cannot override the preregistered proper-score failure rule.

## Program-level selection result

- `REJECTED`: 3;
- `INCONCLUSIVE`: 0;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`: 0;
- prospective-shadow specification created: `no`;
- Phase 4 authorized: `no`.

No ATS hit-rate, ROI, selected subset, favorable season/slice, post-hoc calibration, support repair or candidate redesign was used to alter these classifications.

## Terminal disposition

The V1 ATS Next-Generation program is scientifically closed through Phase 3. There is no authorized next phase under the current program because no candidate survived the frozen selection gates.

Any future ATS architecture must begin as a new explicitly authorized research amendment/version with a new pre-result contract. It may not be treated as a continuation or rescue of Q1/Q2/Q3 V1.

## Evidence boundary

The accepted 2022–2025 evidence is chronology-clean but development/non-pristine. Q1/Q3 uncertainty intervals crossing zero mean effects of the observed tiny magnitude are not sharply resolved; they do not convert adverse primary point results into passed incremental tests and do not establish large harmful effects. Q2 is structurally invalid rather than statistically inconclusive.

No completed-2026 outcome signal has been used. Production remains `F-ST-01-FROZEN-2026`.
