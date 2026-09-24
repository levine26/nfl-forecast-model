# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `PHASE2_OPENING_RECEIPT.md`, `PHASE2_Q1_RESULT_RECEIPT.md`, `PHASE2_Q2_RESULT_RECEIPT.md`, `PHASE2_Q3_RESULT_RECEIPT.md`, `PHASE2_STAGE_D_RESULT_RECEIPT.md`, and `FINAL_PHASE2_RECEIPT.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch / PR | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` / PR #556 merged | design frozen | closed |
| 2 | Controlled Implementation & Historical Development | **COMPLETE** | Stage-D PR #563 merged at `a9ba2a5759c1308e6a47e682240a4e79dd419726` | Q1 negative; Q2 structurally invalid; Q3 negative; Stage-D uncertainty accepted and reproduced | closed |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **NOT STARTED** | none | complete Phase-2 package frozen | begin from verified Phase-2 merge using `PHASE3_HANDOFF.md` |
| 4 | Prospective Shadow Validation | **CONDITIONAL / NOT STARTED** | none | unavailable | only if Phase 3 earns eligibility and continuation is explicitly authorized |

## Phase 1

- PR #556;
- validated head `c1397729b7f973169ef6fda700f481a91ad25538`;
- merge SHA `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`.

## Phase-2 opening gate

- PR #559 merge `f43e17ba783e3e389969cd1649889b37bd91afe9`;
- 2,895 historical rows / 2,895 ATS eligible / 73 pushes / 0 completed-2026 outcomes;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- market evidence class `historical_closing_late_benchmark_exact_horizon_opaque`.

## Stage A — Q1

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` is a **valid negative incremental result** versus M2.

- PR #560;
- 1,087 chronology-clean outer-OOF rows, 2022–2025;
- Q1 OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 minus M2 mean frozen-quantile pinball `+0.0001307888` (worse).

No Q1 rescue is authorized.

## Stage B — Q2

`ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` is **structurally invalid under its frozen support/truncation contract**.

- PR #561 closeout merge `16859845573c3344ed82ae0b9bd27fa8b891eee4`;
- frozen support `[-75,+75]`;
- observed maximum folded endpoint mass `0.0033487075822347966` exceeded frozen threshold `0.001`;
- no accepted Q2 OOF artifact or primary proper-score result exists.

No Q2 support/grid/model rescue is authorized. Q2 complementarity and Q2/Q3 blend evidence remain unavailable.

## Stage C — Q3

`ATS-Q3-DIRECT-CPL-HURDLE-V1` is a **valid negative incremental result / not incremental versus Q3-M2**.

- PR #562 merged; Stage-C merge / Stage-D base `539081c59e62a5d4dbc0a8f849d8a332424ea06e`;
- accepted workflow `35931071604`;
- artifact `10781521222`, digest `sha256:6062472dce30fddfcc6ad16d1d5c29203491f6e77d893aa673cc20bbb29a1bfa`;
- 1,087 exact-row OOF games, 2022–2025;
- Q3 OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- Q3 minus Q3-M2 multinomial cover/push/loss log loss `+0.0013157419` (worse).

No Q3 rescue or redesign is authorized.

## Stage D — final evidence synthesis and uncertainty

Stage D has a valid accepted result on the preregistered scientific surface and is merged through PR #563.

- accepted scientific execution head `0030de3fcc3fd094f1ce28eb0ab1c20b748ca67a`;
- accepted scientific tree `cf161bc7b47d8d138fd35dfe4889ccc215c91b5b`;
- workflow `35936805090`: **SUCCESS**;
- artifact ID `10783239110`;
- artifact digest `sha256:4a3bd19a48528a2772e69232ad10b959b1f66e3885e44b56772f0b379abbcdd2`;
- final closeout head `619959f50bb7f9cbbc1ed9fbc562547db7f17487`: all eight exact-head workflows **SUCCESS**;
- final Stage-D reproducibility run `35938454038`: all four evidence files matched the accepted artifact byte-for-byte by SHA-256;
- PR #563 merge / verified main `a9ba2a5759c1308e6a47e682240a4e79dd419726`;
- exactly 10,000 paired `(season, week)` bootstrap draws, 72 blocks, seed 26;
- completed-2026 outcomes used: 0;
- production changed: no.

Paired uncertainty:

- Q1 − M2 mean-three-quantile pinball: observed `+0.0001307888`, 95% interval `[-0.0023784358,+0.0025555440]`, `P(better)=0.4554`;
- Q3 − Q3-M2 multinomial CPL log loss: observed `+0.0013157419`, 95% interval `[-0.0015590942,+0.0043366478]`, `P(better)=0.1842`;
- Q3 − Q3-M2 non-push conditional-cover Brier: observed `+0.0006716459`, 95% interval `[-0.0007977772,+0.0022129221]`, `P(better)=0.1851`.

Simple hit-rate diagnostic, which cannot select or rescue a candidate:

- Q3-M2: 559/1,058 = `52.8355%`, exact 95% CI `[49.7759%,55.8793%]`;
- Q3: 552/1,058 = `52.1739%`, exact 95% CI `[49.1142%,55.2215%]`.

The intervals do not erase the accepted Phase-2 candidate classifications. Stage D makes no Phase-3 architecture classification.

## Source-sign contract

The nflverse source field `spread_line` is a home-margin center: positive means home favored. Canonical ATS notation remains:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `ats_residual = (home_score-away_score) + home_spread`.

## Next-stage boundary

Phase 2 is closed. Phase 3 may classify each frozen architecture as `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` using only accepted Phase-2 evidence.

Phase 3 may not reopen candidate design, use completed-2026 outcomes, rescue Q1/Q2/Q3, or authorize production promotion. Phase 4 remains conditional on Phase-3 eligibility plus explicit user authorization.
