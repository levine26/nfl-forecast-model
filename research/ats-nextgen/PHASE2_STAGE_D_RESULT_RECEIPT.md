# ATS Next-Generation Phase 2 — Stage D Result Receipt

**Status:** COMPLETE — IMMUTABLE ACCEPTED EVIDENCE  
**Program:** `LEVLINE_ATS_NEXTGEN`  
**Stage:** D — final evidence synthesis and uncertainty  
**Evidence class:** 2022–2025 development / non-pristine  
**Production control:** `F-ST-01-FROZEN-2026` — unchanged

## Accepted execution

The authoritative Stage-D execution consumed the immutable Q1 and Q3 GitHub Actions artifacts directly. It did not refit, regenerate, retune, recalibrate, rescue, select, or replace any candidate.

- branch: `research/ats-nextgen-phase2-stage-d-accepted-artifacts`;
- PR: #564;
- exact accepted result head: `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow run: `35938628588` — **SUCCESS**;
- contract job: `107441314608` — **SUCCESS**;
- synthesis job: `107441551438` — **SUCCESS**;
- Stage-D artifact ID: `10783982962`;
- artifact name: `ats-nextgen-stage-d-35938628588`;
- artifact digest: `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`.

The contract, frozen-blob checks, accepted-artifact downloads, complete registered SHA checks, synthesis, protected-production diff proof, and artifact upload all passed.

## Accepted upstream evidence

Q1 was read directly from Stage-A workflow `35920622523`, artifact `10776898518`, artifact digest `sha256:b544a4928a3e2ab80861b7b3fcf581a6b51355961b80aa05ddc5e4a0554d0c36`, OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`.

Q3 was read directly from Stage-C workflow `35931071604`, artifact `10781521222`, artifact digest `sha256:6062472dce30fddfcc6ad16d1d5c29203491f6e77d893aa673cc20bbb29a1bfa`, OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`.

Every registered file in both accepted artifacts matched its frozen SHA-256 before uncertainty analysis began.

Q2 remains `STRUCTURALLY_INVALID_FROZEN_SUPPORT_CONTRACT`; no accepted Q2 OOF or primary performance artifact exists. Q2 complementarity and the Q2/Q3 blend remain unavailable and were not reconstructed or substituted.

## Frozen uncertainty contract

- 10,000 paired bootstrap draws;
- seed `26`;
- `(season, week)` block resampling;
- 72 blocks;
- two-sided 95% percentile intervals;
- candidate-minus-matching-null deltas, lower is better;
- probability-better = fraction of bootstrap deltas below zero;
- exact two-sided 95% Clopper-Pearson simple hit-rate diagnostic.

No new slices, thresholds, synthetic historical juice, ROI filters, or candidate rescue were introduced.

## Paired uncertainty results

### Q1 vs M2 — mean three-quantile pinball

- rows: `1,087`;
- observed Q1 − M2 delta: `+0.0001307887665715768`;
- 95% block-bootstrap CI: `[-0.002378435765685505, +0.002555544033066125]`;
- bootstrap probability Q1 better: `0.4554`.

The interval crosses zero. This does **not** reverse the frozen Stage-A classification. The observed point estimate remains adverse to Q1, and Q1 remains a valid negative incremental result without rescue.

### Q3 vs Q3-M2 — multinomial cover/push/loss log loss

- rows: `1,087`;
- observed Q3 − Q3-M2 delta: `+0.0013157418572419255`;
- 95% block-bootstrap CI: `[-0.0015590942193462521, +0.004336647782633088]`;
- bootstrap probability Q3 better: `0.1842`.

The interval crosses zero, but the observed point estimate remains adverse and the probability-better diagnostic is not evidence sufficient to rescue Q3. Q3 remains not incremental versus Q3-M2.

### Q3 vs Q3-M2 — non-push conditional-cover Brier

- rows: `1,058`;
- observed Q3 − Q3-M2 delta: `+0.0006716459171549338`;
- 95% block-bootstrap CI: `[-0.0007977772384239724, +0.002212922097716785]`;
- bootstrap probability Q3 better: `0.1851`.

Again the interval crosses zero while the point estimate is adverse to Q3.

## Simple hit-rate diagnostic

This is diagnostic only and cannot rescue candidate selection.

- Q3-M2: `559 / 1,058 = 0.5283553875236295`; exact 95% CI `[0.49775949333669123, 0.5587931509358325]`;
- Q3: `552 / 1,058 = 0.5217391304347826`; exact 95% CI `[0.49114173609938455, 0.5522152927898765]`.

## Descriptive season deltas

Candidate minus matching null, lower is better:

| Season | Q1 − M2 pinball | Q3 − Q3-M2 log loss |
|---|---:|---:|
| 2022 | `-0.0041398699701264974` | `+0.00011298354392952348` |
| 2023 | `0.0` | `+0.003347841431582066` |
| 2024 | `+0.0036977834889890815` | `-0.0013092602770847783` |
| 2025 | `+0.0009495405961912340` | `+0.0031069808249776232` |

These are descriptive frozen-season summaries, not a basis for threshold/subset selection.

## Artifact file identities

- `phase2_stage_d_paired_uncertainty.csv`: `c6680a25bc6acc17a6b552bd6c9593df166d17c5e2e750e1ebffa7d538ed6f1e`;
- `phase2_stage_d_hit_rate_intervals.csv`: `885c4627c814286b76e6ba3e91c34bafd97b2079f4937448b385e7220df720b3`;
- `phase2_stage_d_season_deltas.csv`: `28316ccf2e7009f0a9a9f1fe1a5e2f127a7f449dfb5cd04a15e506c7dd15f0bc`;
- `phase2_stage_d_summary.json`: `d78dcf91965bdb71bea8fbcf0261bbe5ff629e28b0a7538e12ac20e07c1766a9`.

## Phase-2 scientific conclusion

Phase 2 is complete as a historical-development program:

- **Q1:** valid negative incremental result versus M2;
- **Q2:** structurally invalid under its frozen V1 support/truncation contract; no valid Q2 OOF/performance result;
- **Q3:** valid negative incremental result versus Q3-M2;
- **Q2 complementarity / Q2-Q3 blend:** unavailable because no valid Q2 OOF exists;
- **uncertainty:** the paired intervals for the defined Q1/Q3 deltas cross zero, indicating the historical development evidence does not sharply identify tiny incremental effects, but it supplies no scientific basis to overturn the preregistered negative point-result classifications or rescue a candidate.

No Phase-2 candidate has demonstrated the preregistered historical incremental advantage required to be treated as a positive historical-development result.

Phase 2 itself does not perform the Phase-3 `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` classification. That classification belongs to Phase 3.

## Firewalls preserved

- completed-2026 outcomes used: `0`;
- production changed: `no`;
- new candidate fitting/selection in Stage D: `no`;
- Q1 rescue: `no`;
- Q2 reconstruction/rescue: `no`;
- Q3 rescue: `no`;
- ROI/ATS used to rescue a candidate: `no`.

**Next stage:** Phase 3 — Scientific Synthesis, Candidate Selection & Freeze.
