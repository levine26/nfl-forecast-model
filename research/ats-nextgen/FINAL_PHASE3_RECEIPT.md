# ATS Next-Generation — Final Phase 3 Receipt

**Program:** `LEVLINE_ATS_NEXTGEN`  
**Phase:** 3 — Scientific Synthesis, Candidate Selection & Freeze  
**Scientific status:** **COMPLETE — ALL THREE V1 CANDIDATES REJECTED**  
**Prospective-shadow survivors:** `0`  
**Phase 4:** **NOT AUTHORIZED / NOT STARTED**  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes used:** `0`

## 1. Immutable phase boundary

Phase 3 began only after the final Phase-2 governance closeout merged and was verified as current `main`.

- Phase-3 branch: `research/ats-nextgen-phase3`;
- verified Phase-3 base / Phase-2 governance merge: `a5c7bf6c37b9d1b385bfe88bd1a329ddd3bb63f0`;
- Phase-2 governance closeout: PR #567, validated head `ee056a281303f2b5e60e7652fb2c45d85337a116`;
- authoritative Phase-2 scientific closeout: PR #566 / merge `89f8b4fa48e22554029392b303225e4665b4b673`;
- immutable Phase-3 opening receipt commit: `d2be05c3f74e5b6095a9714bd58e7f0984c59276`;
- classification package pre-final-receipt head: `ceea34d421426703cf222a5d00376ad950290a65`.

No Phase-3 historical candidate fit, prediction generation, threshold search, support repair, calibration rescue, candidate redesign, Q2 reconstruction, completed-2026 outcome inspection or production mutation occurred.

## 2. Frozen Phase-3 document identities

The scientific classification is bound to these exact repository blobs:

- `PHASE3_OPENING_RECEIPT.md`: `de77f326289f6e325732472f9cfcb582d4869063`;
- `PHASE3_EVIDENCE_SYNTHESIS.md`: `16297723b9b223eae5708078c384935d9adbfc6c`;
- `phase3_candidate_registry.json`: `49258fb88ec21852feb9028fddb825b800640b26`;
- `PHASE_STATUS.md`: `5fbf46629ade7dff3522949cfcf2560b03ca5dc3`;
- `CURRENT_STATE_AND_NEXT_STEPS.md`: `aa32172f2dd34242f1690caf199ff4d6ae904aab`.

The machine registry is the canonical machine-readable Phase-3 classification map. The evidence synthesis is the canonical human-readable rationale.

## 3. Authoritative Phase-2 evidence consumed

Phase 3 used no newly generated candidate evidence. It consumed only the frozen Phase-2 records.

### Stage D

- scientific origin: PR #564 / head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588` — SUCCESS;
- artifact `10783982962`;
- digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`;
- 10,000 paired `(season, week)` bootstrap draws, seed 26, 72 blocks.

### Q1

- accepted OOF rows: 1,087;
- OOF SHA: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 − M2 mean-three-quantile pinball: `+0.0001307887665715768`;
- paired 95% CI: `[-0.002378435765685505, +0.002555544033066125]`;
- P(Q1 better): `0.4554`.

### Q2

- frozen support: `[-75,+75]`;
- frozen endpoint-mass threshold: `0.001`;
- observed maximum folded endpoint mass: `0.0033487075822347966`;
- valid complete accepted Q2 OOF: none;
- accepted Q2 primary performance: none.

### Q3

- accepted OOF rows: 1,087;
- OOF SHA: `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- Q3 − Q3-M2 multinomial CPL log-loss: `+0.0013157418572419255`;
- paired 95% CI: `[-0.0015590942193462521, +0.004336647782633088]`;
- P(Q3 better): `0.1842`;
- non-push Brier delta: `+0.0006716459171549338`.

## 4. Final classifications

| Candidate | Final Phase-3 status | Binding reason |
|---|---|---|
| `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` | **REJECTED** | `FAILED_PRIMARY_INCREMENTAL_QUANTILE_GATE` |
| `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` | **REJECTED** | `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT` |
| `ATS-Q3-DIRECT-CPL-HURDLE-V1` | **REJECTED** | `FAILED_PRIMARY_INCREMENTAL_PROPER_SCORE_GATE` |

Classification totals:

- `REJECTED`: **3**;
- `INCONCLUSIVE`: **0**;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`: **0**.

## 5. Classification rationale

### Q1

Q1 is a valid experiment but did not improve its required primary quantile objective over M2. The paired interval crossing zero means a material detrimental effect is not established; it does not supply the positive primary improvement required for survival. Favorable slices cannot rescue the failed pooled incremental gate.

### Q2

Q2 V1 is structurally invalid under its own frozen support/truncation specification. This is not ordinary statistical uncertainty and there is no valid accepted primary Q2 performance result to promote. A wider-support future version would be a new experiment, not a rescue of V1.

### Q3

Q3 is a valid experiment but its primary proper score is worse than Q3-M2, and its preregistration explicitly requires rejection if that comparison fails. Supporting non-push Brier/calibration evidence does not reverse that result. The paired interval crossing zero limits claims of harm but does not establish incremental value.

## 6. Prospective and production disposition

No candidate earned `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`; therefore:

- no prospective-shadow specification is created;
- Phase 4 is not authorized and must not start;
- no candidate is promoted to production;
- no production model/parameter/path is changed;
- `F-ST-01-FROZEN-2026` remains the production control.

Any future ATS research must be explicitly authorized as a new program amendment/version with a new pre-result contract. It may not reuse this Phase-3 closeout as permission to repair or relabel Q1/Q2/Q3 V1.

## 7. Interpretation boundary

The final V1 conclusion is deliberately narrow. The development evidence does not demonstrate incremental value for Q1 or Q3 relative to their market-only nulls, and Q2 V1 is invalid under its frozen numerical support contract. Because 2022–2025 is development/non-pristine and Q1/Q3 uncertainty intervals cross zero, this receipt does not claim broad proof that the candidate ideas are materially harmful or that future genuinely different architectures cannot improve on the market.

The scientifically valid action for this frozen program is to preserve the negative/invalid results and stop rather than rescue them after inspection.