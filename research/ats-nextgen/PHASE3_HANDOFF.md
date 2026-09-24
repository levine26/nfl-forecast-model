# ATS Next-Generation — Phase 3 Handoff

**Status:** FROZEN AFTER PHASE-2 STAGE-D SCIENTIFIC COMPLETION; PHASE-2 CLOSEOUT MERGE PENDING  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Next stage:** Phase 3 — Scientific Synthesis, Candidate Selection & Freeze  
**Production control:** `F-ST-01-FROZEN-2026` — unchanged

## 1. Purpose of Phase 3

Phase 3 is a bounded scientific-classification stage. It must classify each already-frozen architecture as exactly one of:

- `REJECTED`;
- `INCONCLUSIVE`;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.

Phase 3 is **not** a new modeling round. It must not train, retune, recalibrate, rescue, replace, blend, or redesign Q1, Q2, or Q3. It must not search new features, learners, hyperparameters, thresholds, slices, support widths, key-number rules, or calibration methods.

Completed-2026 outcomes remain firewalled. Production F-ST / Sunday Signal numerical forecasting must remain unchanged.

## 2. Required starting point

Do not begin Phase 3 from this branch head alone.

First:

1. complete exact-head validation of Phase-2 Stage-D closeout PR #563;
2. merge PR #563 only if those gates are green;
3. verify the resulting merge is current `main`;
4. create the Phase-3 branch from that exact verified merge SHA;
5. freeze a Phase-3 opening/classification receipt before recording any architecture classification.

## 3. Accepted Phase-2 evidence package

### Phase-2 historical gate

- 2,895 ATS-eligible historical games, 2015–2025;
- 73 pushes;
- completed-2026 outcomes used: 0;
- canonical game-keyed SHA-256: `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`.

### Q1 — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`

Frozen Phase-2 classification: **valid negative incremental result versus M2**.

- 1,087 exact chronology-clean outer-OOF rows, 2022–2025;
- accepted Q1 OOF SHA-256: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 minus M2 mean-three-quantile pinball: `+0.0001307888` — worse;
- Stage-D paired bootstrap 95% interval: `[-0.0023784358,+0.0025555440]`;
- Stage-D `P(Q1 better than M2) = 0.4554`.

The bootstrap interval includes zero. That does not erase the accepted negative observed result; Phase 3 must apply its frozen classification rule without inventing a rescue criterion.

### Q2 — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

Frozen Phase-2 classification: **structurally invalid under the frozen V1 support/truncation contract**.

- frozen support: `[-75,+75]`;
- maximum folded endpoint mass: `0.0033487075822347966`;
- frozen fail-closed threshold: `0.001`;
- accepted Q2 OOF artifact: none;
- accepted Q2 primary performance result: none;
- Q2 complementarity: unavailable;
- Q2/Q3 blend: unavailable.

Phase 3 must not widen support, reconstruct a Q2 distribution, substitute another distribution, or manufacture a blend.

### Q3 — `ATS-Q3-DIRECT-CPL-HURDLE-V1`

Frozen Phase-2 classification: **valid negative incremental result / not incremental versus Q3-M2**.

- 1,087 exact chronology-clean outer-OOF rows, 2022–2025;
- accepted Q3 OOF SHA-256: `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- Q3 minus Q3-M2 multinomial cover/push/loss log loss: `+0.0013157419` — worse;
- Stage-D paired bootstrap 95% interval: `[-0.0015590942,+0.0043366478]`;
- Stage-D `P(Q3 better than Q3-M2) = 0.1842`;
- non-push conditional-cover Brier delta: `+0.0006716459` — worse;
- Brier 95% interval: `[-0.0007977772,+0.0022129221]`;
- Stage-D `P(Q3 better on Brier) = 0.1851`.

Simple ATS hit-rate diagnostic:

- Q3-M2: `52.8355%` on 1,058 non-push rows, exact 95% CI `[49.7759%,55.8793%]`;
- Q3: `52.1739%`, exact 95% CI `[49.1142%,55.2215%]`.

The hit-rate diagnostic is non-selective and cannot rescue Q3 or overturn the proper-score evidence.

## 4. Stage-D accepted evidence identity

- accepted scientific execution head: `0030de3fcc3fd094f1ce28eb0ab1c20b748ca67a`;
- accepted scientific tree: `cf161bc7b47d8d138fd35dfe4889ccc215c91b5b`;
- workflow: `35936805090`;
- artifact ID: `10783239110`;
- artifact digest: `sha256:4a3bd19a48528a2772e69232ad10b959b1f66e3885e44b56772f0b379abbcdd2`;
- bootstrap: exactly 10,000 paired `(season, week)` draws across 72 blocks, seed 26;
- completed-2026 outcomes used: 0;
- production changed: no.

Authoritative Stage-D closeout files:

- `PHASE2_STAGE_D_RESULT_RECEIPT.md`;
- `phase2_stage_d_result_registry.json`.

## 5. Phase-3 evidence rules

Phase 3 must use the accepted Phase-2 package only. It may synthesize and classify; it may not create new historical candidate evidence.

The following are prohibited:

- new candidate families or challenger variants;
- Q1/Q2/Q3 refits, retuning, recalibration, rescue, or redesign;
- Q2 reconstruction or replacement;
- new Q2/Q3 blend cells;
- completed-2026 outcome inspection;
- post-hoc threshold, slice, subgroup, feature, learner, hyperparameter, or support searches;
- synthetic historical juice or unverifiable ROI/EV claims;
- use of simple ATS hit rate to overturn proper-score conclusions;
- production forecast changes.

Historical 2022–2025 evidence remains development/non-pristine evidence. Even a Phase-3 architecture classified `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` is **not production-approved**.

## 6. Maximum Phase-3 authority

The strongest result Phase 3 may assign is `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.

Production promotion is outside Phase 3. Phase 4 may begin only if:

1. Phase 3 earns prospective-shadow eligibility under the frozen evidence/classification rules; and
2. the user explicitly authorizes Phase 4 continuation.

If no architecture earns eligibility, the program should close with the negative/invalid evidence preserved rather than open another rescue loop.

## 7. Exact first Phase-3 actions

After the verified Phase-2 closeout merge:

1. read `MASTER_PLAN.md`, `PHASE_STATUS.md`, `CURRENT_STATE_AND_NEXT_STEPS.md`, `PHASE2_STAGE_D_RESULT_RECEIPT.md`, `phase2_stage_d_result_registry.json`, all Q1/Q2/Q3 result receipts/registries, `EVALUATION_PROTOCOL.md`, and `RED_TEAM_AND_LEAKAGE_CHECKLIST.md`;
2. locate any already-frozen architecture-classification rules in the Phase-1 program materials;
3. freeze a Phase-3 opening receipt that binds those rules and the exact Phase-2 evidence identities before classifying any architecture;
4. perform the classification mechanically and preserve negative/invalid evidence;
5. validate the Phase-3 package through research firewall / repository CI;
6. stop before Phase 4 unless explicit user authorization exists.
