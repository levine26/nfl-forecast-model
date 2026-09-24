# PHASE 5 NULL CALIBRATION REPORT

Program: `LEVLINE_ATS_FRONTIER_V2`

This report contains the one synthesis calculation explicitly authorized by `PHASE5_HANDOFF.md`: null-side calibration intercept/slope derived from already-preserved canonical OOF probabilities. No candidate was refit, recalibrated, retuned, regenerated, or transformed.

## Immutable provenance

- canonical workflow: `36025444929`
- canonical artifact: `10820397832`
- artifact digest independently verified: `sha256:d65adbc7bf0837ee2b5867b551af607549c1095182da1570085e2e50013fb60d`
- M3 OOF SHA-256 independently verified: `9ea3c9062f00518ee7b2535605509b40f817c31dd731e3d178916ae117eac4a1`
- M4 OOF SHA-256 independently verified: `71e7891d9b75622cbb48fb64912566f5cb57ad10959600bc25ecf74bd4bd46cb`
- completed-2026 outcomes used: `0`

## Frozen calculation

The calculation reproduces `phase4_core.py::calibration_report` exactly:

1. exclude push rows (`ats_class == 1`);
2. define binary target `1` for home cover and `0` for home fail;
3. condition cover probability on non-push outcome as `p_cover / (p_cover + p_loss)`;
4. clip only to the already-frozen numerical bounds `[1e-6, 1-1e-6]`;
5. regress the binary target on `logit(p)` using `sklearn.linear_model.LogisticRegression(C=1e6, solver="lbfgs")`;
6. report fitted intercept and slope only as diagnostics; do not feed them back into any probability.

Both candidate calculations were reproduced from the same canonical OOF files as a provenance check and match the preserved Phase-4 candidate calibration values to floating-point precision.

## M3 — `M3-NULL-MARKET-NORMAL-01`

Non-push calibration rows: `1058`.

Null calibration:

- intercept: `0.0`
- slope: `0.0`

Candidate `FV2-HIST-M3-DSSM-01` preserved calibration:

- intercept: `-0.0008002656550699535`
- slope: `-1.4064471514780361`

Relative frozen-rule diagnostics:

- null absolute intercept: `0.0`
- candidate absolute intercept: `0.0008002656550699535`
- intercept worsening: `0.0008002656550699535` — below the `0.03` material-degradation limit.
- null absolute slope departure from 1: `1.0`
- candidate absolute slope departure from 1: `2.406447151478036`
- slope-departure worsening: `1.406447151478036` — exceeds the `0.10` material-degradation limit.

Conclusion: M3 calibration is materially degraded versus its null under the frozen slope rule. The explicit exception is unavailable because M3 does not have a significant primary-score improvement under the frozen evidence.

## M4 — `M4-NULL-STUDENTT-CONSTANT-01`

Non-push calibration rows: `1058`.

Null calibration:

- intercept: `0.0`
- slope: `0.0`

Candidate `FV2-HIST-M4-DMARGIN-01` preserved calibration:

- intercept: `0.01477013532177962`
- slope: `0.4366590498000353`

Relative frozen-rule diagnostics:

- null absolute intercept: `0.0`
- candidate absolute intercept: `0.01477013532177962`
- intercept worsening: `0.01477013532177962` — below the `0.03` material-degradation limit.
- null absolute slope departure from 1: `1.0`
- candidate absolute slope departure from 1: `0.5633409501999647`
- slope-departure change: `-0.4366590498000353` — an improvement, not degradation.

Conclusion: M4 does not materially degrade calibration versus its null under the frozen Phase-5 rule. No exception is needed.

## Boundary

These diagnostics adjudicate only the frozen calibration-relative eligibility clause. They do not recalibrate either model, create a replacement candidate, alter the primary score, or override the preregistered ablation/rejection rules.