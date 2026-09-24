# ATS Next-Generation — Phase 3 Opening Receipt

**Program:** `LEVLINE_ATS_NEXTGEN`  
**Phase:** 3 — Scientific Synthesis, Candidate Selection & Freeze  
**Status:** OPEN — CLASSIFICATION ONLY  
**Branch:** `research/ats-nextgen-phase3`  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes authorized/used:** `0` / `0`

## Immutable opening identity

Phase 3 was opened only after the final Phase-2 governance closeout merged and was verified as current `main`.

- Phase-3 base / verified current `main`: `a5c7bf6c37b9d1b385bfe88bd1a329ddd3bb63f0`;
- Phase-2 governance closeout: PR #567;
- Phase-2 governance closeout validated head: `ee056a281303f2b5e60e7652fb2c45d85337a116`;
- Phase-2 governance closeout merge: `a5c7bf6c37b9d1b385bfe88bd1a329ddd3bb63f0`;
- authoritative Phase-2 scientific closeout merge: PR #566 / `89f8b4fa48e22554029392b303225e4665b4b673`;
- authoritative corrected Stage-D scientific origin: PR #564 / accepted head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- Stage-D workflow: `35938628588`;
- Stage-D artifact: `10783982962`;
- Stage-D artifact digest: `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`.

All seven exact-head workflows on governance head `ee056a281303f2b5e60e7652fb2c45d85337a116` were `SUCCESS` before PR #567 merged: research firewall, Phase-2 opening gate, Q1 Stage A, Q2 Stage B, Q3 Stage C, Stage-D closeout, and repository research validation.

## Frozen evidence entering Phase 3

Phase 3 consumes only the immutable Phase-2 receipts/registries and accepted artifacts already recorded in the repository.

### Q1 — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`

- accepted OOF rows: 1,087;
- accepted OOF SHA-256: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 − M2 mean-three-quantile pinball: `+0.0001307887665715768`;
- paired 95% CI: `[-0.002378435765685505, +0.002555544033066125]`;
- bootstrap probability Q1 better: `0.4554`;
- Phase-2 state: `VALID_NEGATIVE_INCREMENTAL_RESULT`.

### Q2 — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

- frozen support: `[-75,+75]`;
- frozen material endpoint-mass threshold: `0.001`;
- observed maximum folded endpoint mass: `0.0033487075822347966`;
- accepted complete Q2 OOF: none;
- accepted primary Q2 proper-score result: none;
- Phase-2 state: `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`.

### Q3 — `ATS-Q3-DIRECT-CPL-HURDLE-V1`

- accepted OOF rows: 1,087;
- accepted OOF SHA-256: `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- Q3 − Q3-M2 multinomial CPL log-loss: `+0.0013157418572419255`;
- paired 95% CI: `[-0.0015590942193462521, +0.004336647782633088]`;
- bootstrap probability Q3 better: `0.1842`;
- non-push Brier delta: `+0.0006716459171549338`;
- Phase-2 state: `NOT_INCREMENTAL_VS_Q3_M2`.

Q2 complementarity and Q2/Q3 blending are unavailable because no valid accepted Q2 OOF distribution exists.

## Classification contract

Phase 3 may assign each frozen architecture exactly one status:

- `REJECTED`;
- `INCONCLUSIVE`;
- `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`.

Under the frozen Evaluation Protocol, prospective-shadow eligibility requires the candidate's primary proper/quantile metric to improve on the relevant market null on exact common OOF rows, without material calibration failure, concentration-only improvement, leakage/red-team failure, or model-identity drift.

A confidence interval crossing zero does not convert an adverse point result into a passed incremental test. It limits claims about the magnitude/sign of harm. Structural invalidity is not ordinary statistical uncertainty.

## Prohibitions

Phase 3 will not:

- refit or rerun Q1/Q2/Q3;
- generate new 2022–2025 candidate predictions;
- inspect completed-2026 outcomes;
- redesign, rescue, recalibrate or retune a candidate;
- widen Q2 support or reconstruct a substitute Q2 distribution;
- create a new learner, feature, threshold, slice, blend weight or candidate;
- use ATS hit rate, ROI or favorable subsets to override failed primary proper-score evidence;
- modify production F-ST or Sunday Signal numerical forecasting behavior;
- promote any model to production.

## Evidence boundary

2022–2025 remains chronology-clean but development/non-pristine evidence. Phase 3 is classification and freeze only. Even an eligible candidate could authorize at most a later prospective shadow stage, and Phase 4 would still require explicit user authorization.

This receipt is the immutable opening boundary for Phase 3. All subsequent Phase-3 classifications must be derivable from the frozen evidence above and the authoritative Phase-1/Phase-2 control files.