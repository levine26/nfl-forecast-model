# ATS Next-Generation Phase 2 — Stage D Result Receipt

**Status:** COMPLETE — ACCEPTED FINAL PHASE-2 EVIDENCE SYNTHESIS  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Stage:** D — final evidence synthesis and uncertainty  
**Accepted scientific execution head:** `0030de3fcc3fd094f1ce28eb0ab1c20b748ca67a`  
**Accepted workflow:** `35936805090`  
**Artifact:** `10783239110`  
**Artifact digest:** `sha256:4a3bd19a48528a2772e69232ad10b959b1f66e3885e44b56772f0b379abbcdd2`  
**Production control:** `F-ST-01-FROZEN-2026` — unchanged

## 1. Scientific boundary

Stage D performed evidence synthesis only. It did not fit, retune, recalibrate, rescue, replace, select, or blend a new candidate. It used zero completed-2026 outcomes and made no production forecasting change.

The accepted execution followed `PHASE2_STAGE_D_OPENING_RECEIPT.md` exactly:

- paired resampling by full `(season, week)` blocks;
- target seasons 2022–2025;
- exactly 10,000 bootstrap draws;
- deterministic seed 26;
- percentile 95% intervals;
- candidate-minus-matching-market-null loss deltas on exact paired rows;
- no new slices, threshold search, subset search, synthetic historical juice, ATS/ROI rescue, or Q2 reconstruction.

The runner regenerated frozen Q1 and Q3 evidence at their canonical paths and verified every accepted evidence-file SHA-256 before synthesis. Q2 remained unavailable by construction because Stage B produced no valid accepted OOF artifact.

## 2. Accepted artifact files

| File | SHA-256 |
|---|---|
| `phase2_stage_d_summary.json` | `b6cb8e244d50e87d16c6da3356bcae6c0ee57bf63b9b809780e2e77cade144c2` |
| `phase2_stage_d_paired_uncertainty.csv` | `c6680a25bc6acc17a6b552bd6c9593df166d17c5e2e750e1ebffa7d538ed6f1e` |
| `phase2_stage_d_season_deltas.csv` | `28316ccf2e7009f0a9a9f1fe1a5e2f127a7f449dfb5cd04a15e506c7dd15f0bc` |
| `phase2_stage_d_hit_rate_intervals.csv` | `885c4627c814286b76e6ba3e91c34bafd97b2079f4937448b385e7220df720b3` |

## 3. Upstream reproducibility

The synthesis regenerated Q1 and Q3 under their frozen runners and reproduced every accepted file hash exactly.

- Q1 OOF SHA-256: `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365` — exact match.
- Q3 OOF SHA-256: `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04` — exact match.
- Q2 classification remains `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`.
- Q2 valid OOF available: **false**.
- Q2/Q3 blend available: **false**.

## 4. Paired bootstrap uncertainty

Lower loss is better, so negative candidate-minus-reference deltas favor the challenger.

| Metric | Comparison | Rows | Blocks | Observed delta | 95% bootstrap interval | P(candidate better) |
|---|---|---:|---:|---:|---:|---:|
| mean three-quantile pinball | Q1 − M2 | 1,087 | 72 | `+0.0001307888` | `[-0.0023784358, +0.0025555440]` | `0.4554` |
| multinomial cover/push/loss log loss | Q3 − Q3-M2 | 1,087 | 72 | `+0.0013157419` | `[-0.0015590942, +0.0043366478]` | `0.1842` |
| non-push conditional-cover Brier | Q3 − Q3-M2 | 1,058 | 72 | `+0.0006716459` | `[-0.0007977772, +0.0022129221]` | `0.1851` |

The intervals include zero, but Stage D does **not** reinterpret or erase the already accepted Stage-A/Stage-C negative results. Per the frozen opening receipt, those observed results remain evidence regardless of whether the uncertainty interval includes zero.

## 5. Season consistency

Frozen per-season primary deltas were preserved:

- 2022 Q1 − M2 pinball: `-0.00413986997`; Q3 − Q3-M2 log loss: `+0.00011298354`.
- 2023 Q1 − M2 pinball: `0.0`; Q3 − Q3-M2 log loss: `+0.00334784143`.
- 2024 Q1 − M2 pinball: `+0.00369778349`; Q3 − Q3-M2 log loss: `-0.00130926028`.
- 2025 Q1 − M2 pinball: `+0.00094954060`; Q3 − Q3-M2 log loss: `+0.00310698082`.

## 6. Simple ATS hit-rate diagnostic

This diagnostic is non-selective and cannot rescue a candidate.

- Q3-M2: 559 / 1,058 non-push rows = `52.8355%`; exact 95% Clopper-Pearson interval `[49.7759%, 55.8793%]`.
- Q3: 552 / 1,058 non-push rows = `52.1739%`; exact 95% Clopper-Pearson interval `[49.1142%, 55.2215%]`.

No historical juice/side-price provenance sufficient for a new ROI or EV claim was introduced.

## 7. Final Phase-2 candidate evidence state

- **Q1 — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`:** valid negative incremental result versus M2. Stage-D uncertainty does not overturn that classification.
- **Q2 — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`:** structurally invalid under the frozen V1 support/truncation contract. No valid Q2 OOF or primary performance result exists.
- **Q3 — `ATS-Q3-DIRECT-CPL-HURDLE-V1`:** valid negative incremental result / not incremental versus Q3-M2. Stage-D uncertainty does not overturn that classification.
- **Q2 complementarity and Q2/Q3 blend:** unavailable; no substitute was manufactured.

## 8. Post-result scientific-surface protection

A later post-result branch variant changed Stage-D evidence loading after artifact `10783239110` already existed. That variant is not accepted evidence and was removed during closeout. The branch scientific tree was restored byte-for-byte to the accepted execution tree `cf161bc7b47d8d138fd35dfe4889ccc215c91b5b` before this result receipt was added.

The accepted runner blob remains `7df0df371b93d50265c9061f4215753a87909b15`, exactly matching the runner used by workflow `35936805090`.

## 9. Phase boundary

**Phase 2 is scientifically complete once this closeout package passes exact-head repository validation and merges.**

Stage D does not perform the Phase-3 architecture classification. The next authorized program stage is:

`PHASE_3_SCIENTIFIC_SYNTHESIS_CANDIDATE_SELECTION_AND_FREEZE`

Phase 3 must classify the frozen architectures as `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` using only the accepted Phase-2 evidence. It may not reopen Q1/Q2/Q3 design, rescue a negative/invalid candidate, use completed-2026 outcomes, or promote anything directly to production.
