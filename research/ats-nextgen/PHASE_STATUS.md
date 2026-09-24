# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `PHASE2_OPENING_RECEIPT.md`, `PHASE2_Q1_RESULT_RECEIPT.md`, `PHASE2_Q2_RESULT_RECEIPT.md`, `PHASE2_Q3_RESULT_RECEIPT.md`, and `PHASE2_STAGE_D_RESULT_RECEIPT.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` / PR #556 merged | design frozen | closed |
| 2 | Controlled Implementation & Historical Development | **COMPLETE — CLOSEOUT VALIDATION/MERGE PENDING** | `research/ats-nextgen-phase2-stage-d-accepted-artifacts` / PR #564 | Q1 negative; Q2 structurally invalid; Q3 negative; Stage-D uncertainty complete | validate immutable closeout records, merge #564, verify merged `main` |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **NOT STARTED** | none | Phase-2 evidence ready after closeout merge | start only from verified Phase-2 merge; classify frozen candidates without rescue/redesign |
| 4 | Prospective Shadow Validation | **CONDITIONAL / NOT STARTED** | none | unavailable | only if Phase 3 earns eligibility and continuation is explicitly authorized |

## Phase-1 integration

- PR #556;
- exact validated head `c1397729b7f973169ef6fda700f481a91ad25538`;
- merge SHA `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`.

## Phase-2 opening gate

- PR #559 merge `f43e17ba783e3e389969cd1649889b37bd91afe9`;
- 2,895 historical rows / 2,895 ATS eligible / 73 pushes / 0 completed-2026 outcomes;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- market evidence class `historical_closing_late_benchmark_exact_horizon_opaque`.

## Stage A — Q1

Candidate: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`.  
PR #560; merge / Stage-B base `a2581a62e3797a6ac466d614326bc72b7d5a1c57`.  
Accepted workflow `35920622523`; artifact `10776898518`; OOF SHA `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`.

- 1,087 outer-OOF rows, 2022–2025;
- Q1 minus M2 mean-three-quantile pinball `+0.0001307887665715768` (worse).

Stage-D paired uncertainty: 95% CI `[-0.002378435765685505, +0.002555544033066125]`, probability Q1 better `0.4554`.

Scientific Phase-2 state: **valid negative incremental result**. No Q1 rescue is authorized.

## Stage B — Q2

Candidate: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`.  
PR #561 merged Stage-B closeout `16859845573c3344ed82ae0b9bd27fa8b891eee4`.

Historical execution failed closed before complete OOF scoring because a frozen generalized-normal state produced maximum folded endpoint mass `0.0033487075822347966` above the frozen `0.001` threshold on support `[-75,+75]`.

Scientific Phase-2 state: **structurally invalid under frozen support/truncation contract**. No accepted Q2 OOF, primary proper-score result, complementarity evidence, or Q2/Q3 blend exists. No rescue is authorized.

## Stage C — Q3

Candidate: `ATS-Q3-DIRECT-CPL-HURDLE-V1`.  
PR #562 merged at `539081c59e62a5d4dbc0a8f849d8a332424ea06e`.  
Accepted workflow `35931071604`; artifact `10781521222`; OOF SHA `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`.

- 1,087 outer-OOF rows, 2022–2025;
- Q3 minus Q3-M2 multinomial CPL log loss `+0.0013157418572419255` (worse);
- Q3 minus Q3-M2 non-push conditional-cover Brier `+0.0006716459171549338` (worse).

Stage-D paired uncertainty:

- log-loss 95% CI `[-0.0015590942193462521, +0.004336647782633088]`, probability Q3 better `0.1842`;
- Brier 95% CI `[-0.0007977772384239724, +0.002212922097716785]`, probability Q3 better `0.1851`.

Scientific Phase-2 state: **valid negative incremental result — not incremental vs Q3-M2**. No Q3 rescue is authorized.

## Stage D — final evidence synthesis and uncertainty

Authoritative branch `research/ats-nextgen-phase2-stage-d-accepted-artifacts`, PR #564.

Accepted exact-head evidence:

- result head `d9a416ff17e2692b1ed86c461b4bd87f5a6cb8ba`;
- workflow `35938628588`: **SUCCESS**;
- contract job `107441314608`: **SUCCESS**;
- synthesis job `107441551438`: **SUCCESS**;
- artifact ID `10783982962`;
- artifact digest `sha256:a7386fdb000e3dd17ee44563762e8cdb5c9423e62467f41138419978c4a75d7c`;
- 10,000 paired `(season, week)` bootstrap draws, seed 26, 72 blocks;
- completed-2026 outcomes used: `0`;
- production changed: `no`;
- new candidate fitting/selection: `no`.

The Stage-D runner consumed the immutable accepted Q1/Q3 artifacts directly and verified every frozen file SHA before computing uncertainty. Q2 remained unavailable rather than being reconstructed.

Accepted artifact-file hashes:

- paired uncertainty `c6680a25bc6acc17a6b552bd6c9593df166d17c5e2e750e1ebffa7d538ed6f1e`;
- hit-rate intervals `885c4627c814286b76e6ba3e91c34bafd97b2079f4937448b385e7220df720b3`;
- season deltas `28316ccf2e7009f0a9a9f1fe1a5e2f127a7f449dfb5cd04a15e506c7dd15f0bc`;
- summary `d78dcf91965bdb71bea8fbcf0261bbe5ff629e28b0a7538e12ac20e07c1766a9`.

The authoritative result is frozen in `PHASE2_STAGE_D_RESULT_RECEIPT.md` and `phase2_stage_d_result_registry.json`.

## Phase-2 conclusion

Phase 2 produced no positive historical-development candidate result under the preregistered incremental tests:

- Q1: negative vs M2;
- Q2: structurally invalid before valid OOF performance;
- Q3: negative vs Q3-M2;
- Q2 complementarity / Q2-Q3 blend: unavailable.

All defined Q1/Q3 Stage-D 95% bootstrap intervals cross zero, so the development sample does not sharply identify the very small incremental deltas. That uncertainty does not authorize reversing the frozen adverse point-result classifications or performing model rescue.

Phase 3, not Phase 2, owns the formal `REJECTED` / `INCONCLUSIVE` / `ELIGIBLE_FOR_PROSPECTIVE_SHADOW` classification.

## Source-sign contract

The nflverse source field `spread_line` is a home-margin center: positive means home favored. Canonical ATS notation remains:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `ats_residual = (home_score-away_score) + home_spread`.

## Fixed candidate state entering Phase 3

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` — valid negative incremental result;
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` — structurally invalid under frozen V1 support contract;
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1` — valid negative incremental result;
- Q2 complementarity and Q2/Q3 blend — unavailable.

No completed-2026 outcome signal has been used. Historical 2022–2025 evidence remains development/non-pristine. Production remains unchanged.
