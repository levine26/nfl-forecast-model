# ATS Next-Generation — Phase 2 Stage B Q2 Result Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Stage:** B — Q2  
**Candidate:** `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`  
**Classification:** **STRUCTURALLY INVALID UNDER FROZEN V1 SUPPORT CONTRACT**  
**Branch:** `research/ats-nextgen-phase2-q2`  
**Controlling pre-result head:** `8503dbf250c97b0520cec30f985e9981fce83767`  
**PR:** #561  
**Date:** 2026-09-23 America/Los_Angeles

## 1. Result boundary

Q2 V1 did **not** produce an accepted historical performance artifact. The exact-head Stage-B workflow passed its pre-result contract and then failed closed during chronology-clean historical execution because the frozen integer support `[-75,+75]` was numerically inadequate under the preregistered endpoint-mass rule.

This is a structural/numerical invalidation of Q2 V1, not a statement that Q2 beat or lost to M1 on proper scoring rules.

At this result boundary:

- accepted Q2 outer OOF artifact: **NONE**;
- accepted Q2 primary discrete-CRPS comparison: **NONE**;
- accepted Q2 cover/push/loss performance comparison: **NONE**;
- Q2 rescue/redesign after the failure: **NONE**;
- support widening after inspection: **NOT PERFORMED / NOT AUTHORIZED**;
- completed-2026 outcomes used: **0**;
- production F-ST/Sunday Signal forecasting changed: **NO**;
- Q3 started before this receipt: **NO**.

## 2. Controlling exact-head validation

The controlling scientific head is:

`8503dbf250c97b0520cec30f985e9981fce83767`

On that head:

- LevLine research firewall `35927280868`: **SUCCESS**;
- ATS NextGen Phase-2 opening gate `35927280994`: **SUCCESS**;
- ATS NextGen Q1 Stage A reproducibility `35927280912`: **SUCCESS**;
- Daily NFL model refresh / full repository validation `35927281014`: **SUCCESS**;
- LevLine research validation `35927280856`: **SUCCESS**;
- ATS NextGen Q2 Stage B `35927280982`: **FAILURE**, solely in the historical execution job after the contract job passed.

Inside Q2 run `35927280982`:

- Q2 pre-result contract job `107405457674`: **SUCCESS**;
- Q2 chronology-clean 2022–2025 OOF job `107405820497`: **FAILURE**;
- protected-production-surface verification and artifact upload did not run because historical execution failed first.

## 3. Exact frozen failure

Historical execution reached the preregistered endpoint-mass guard before completing the historical experiment.

The failing candidate state was:

- family: generalized normal;
- shape `beta=1.0`;
- ablation: `no_key_conditional_scale`;
- key penalty: none.

The observed maximum folded endpoint probability was:

`0.0033487075822347966`

The frozen V1 material boundary-mass threshold was:

`0.001`

Because:

`0.0033487075822347966 > 0.001`

execution correctly raised:

`RuntimeError: Q2 candidate CandidateSpec(family='gennorm', shape=1.0, ablation='no_key_conditional_scale', key_penalty=None) exceeded frozen endpoint-mass threshold`

The failure arose during inner rolling-origin candidate qualification, before a complete Stage-B OOF package was produced or uploaded.

## 4. Why V1 is closed rather than repaired

`Q2_STAGE_B_OPENING_RECEIPT.md` froze the following rule before Q2 historical performance existed:

- support is exactly `-75..+75`;
- endpoint tails are folded into `-75/+75`;
- maximum endpoint mass above `1e-3` is a material support failure;
- the historical result must fail closed rather than widen support after inspection.

That rule is now binding. Therefore Stage B may not respond to this observed failure by:

- widening support;
- weakening the `1e-3` threshold;
- dropping the failing generalized-normal shape;
- removing the no-key ablation;
- changing scale guards;
- changing the distribution family/grid;
- changing the key-number machinery;
- using a different target slice;
- inspecting target scores to choose a replacement.

Any future wider-support Q2 variant would be a **new experiment/version**, not a continuation or rescue of Q2 V1.

## 5. Scientific interpretation

The valid conclusion from Stage B is narrow but important:

> `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` is not a valid Phase-2 candidate under its own frozen support/truncation contract because at least one preregistered chronology-clean candidate state assigns material probability outside the representable interior support.

No claim is made here about whether the underlying continuous-family idea would outperform M1 under a different support specification. That question was not validly tested by Q2 V1 and may not be answered by post-hoc repair inside this stage.

The negative/invalid result is preserved rather than hidden.

## 6. Stage-B closeout and handoff

Stage B is **COMPLETE — INVALID / NO ACCEPTED PERFORMANCE RESULT**.

The preregistered Phase-2 sequence now advances to:

**Stage C — `ATS-Q3-DIRECT-CPL-HURDLE-V1`.**

Before Q3 historical execution:

1. branch from the verified Q2 Stage-B merge;
2. read the frozen Q3 preregistration and evaluation protocol;
3. freeze any implementation details left open by Phase 1 before results;
4. prove half-point structural zero-push behavior;
5. prove three-outcome cover/push/loss normalization;
6. preserve the completed-2026 firewall and research-only production boundary;
7. generate no Q3 historical result until its exact-head contract passes.

Stage D remains unopened until Q3 is completed.

> 2022–2025 remains chronology-clean development evidence and is not pristine independent confirmation because those seasons have informed prior LevLine research.