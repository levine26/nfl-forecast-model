# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `PHASE2_OPENING_RECEIPT.md`, `PHASE2_Q1_RESULT_RECEIPT.md`, `PHASE2_Q2_RESULT_RECEIPT.md`, and `PHASE2_Q3_RESULT_RECEIPT.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` / PR #556 merged | design frozen | closed |
| 2 | Controlled Implementation & Historical Development | **IN PROGRESS — STAGES A/B/C COMPLETE; STAGE D NEXT** | Stage C `research/ats-nextgen-phase2-q3` / PR #562 | Q1 negative; Q2 structurally invalid; Q3 negative | validate/merge Stage-C closeout, then run only final evidence synthesis/uncertainty in Stage D |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **NOT STARTED** | none | unavailable | only after Phase 2 Stage D completes |
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
PR #560; Stage-A merge / Stage-B base `a2581a62e3797a6ac466d614326bc72b7d5a1c57`.  
Accepted result head `f14e2fa3ec78bf95578b4a5030fb66e94cd12cd0`; workflow `35920622523`; artifact `10776898518`.

- 1,087 outer-OOF rows, 2022–2025;
- Q1 OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- M2 mean pinball `4.749986`;
- Q1 mean pinball `4.750117`;
- Q1 minus M2 `+0.000131` (worse).

Scientific classification: **valid negative incremental result**. No Q1 rescue is authorized.

## Stage B — Q2

Candidate: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`.  
PR #561; controlling pre-result head `8503dbf250c97b0520cec30f985e9981fce83767`; merged Stage-B closeout `16859845573c3344ed82ae0b9bd27fa8b891eee4`.

The Q2 contract passed, but historical execution failed closed before a complete OOF artifact because a frozen generalized-normal state produced maximum folded endpoint mass `0.0033487075822347966` above the frozen `0.001` threshold on support `[-75,+75]`.

Scientific classification: **structurally invalid under frozen support/truncation contract**. No accepted Q2 proper-score result or valid Q2 OOF exists. No support/grid/model rescue is authorized.

## Stage C — Q3

Candidate: `ATS-Q3-DIRECT-CPL-HURDLE-V1`.  
Branch `research/ats-nextgen-phase2-q3`; PR #562.  
Verified Stage-B base `16859845573c3344ed82ae0b9bd27fa8b891eee4`.  
Frozen scientific surface `d9dbfe24af7fd19f5b22e76fd5f57dd83c606a60`.  
Accepted historical authorization/result head `891d921c24bc045dd58de3b2dd05871f12d09183`.

Accepted evidence:

- workflow `35931071604`: **SUCCESS**;
- contract job `107417650978`: **SUCCESS**;
- historical job `107418004469`: **SUCCESS**;
- artifact ID `10781521222`;
- artifact digest `sha256:6062472dce30fddfcc6ad16d1d5c29203491f6e77d893aa673cc20bbb29a1bfa`;
- 1,087 exact-row outer OOF games, 2022–2025;
- Q3 OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- completed-2026 outcomes used: 0;
- production changed: no.

Primary proper-score evidence:

- Q3-M2 multinomial CPL log loss: `0.7716887205239867`;
- Q3 multinomial CPL log loss: `0.7730044623812287`;
- Q3 minus Q3-M2: `+0.0013157418572419255` (worse).

Secondary evidence points the same direction: Q3 non-push cover Brier `0.2504715666095457` versus Q3-M2 `0.24979992069239074`, and Q3 aggregate cover-calibration slope `0.27094382668690847` versus Q3-M2 `0.8130523437112027`.

Q3 is worse in 3 of 4 outer seasons and 10 of 14 frozen reporting slices. The shared push head produces identical push probabilities in Q3 and Q3-M2, isolating the failed incremental contribution to the football-augmented conditional-cover head.

Scientific classification: **valid negative incremental result — not incremental vs Q3-M2**. No Q3 rescue or redesign is authorized.

The result is frozen in:

- `PHASE2_Q3_RESULT_RECEIPT.md`;
- `phase2_q3_result_registry.json`.

## Stage D handoff

After the Stage-C closeout head passes exact-head validation and PR #562 merges, create Stage D only from the verified Stage-C merge.

Stage D is evidence synthesis, not a new candidate search. It must:

- preserve Q1 as negative;
- preserve Q2 as structurally invalid with no valid OOF;
- preserve Q3 as negative;
- mark Q2 complementarity and Q2/Q3 blend evidence **unavailable** rather than substituting another distribution;
- run the preregistered paired season+week block-bootstrap uncertainty with at least 10,000 resamples on accepted evidence where defined;
- report exact common-row/per-season/fixed-slice/calibration evidence without threshold or subset mining;
- preserve the completed-2026 and production firewalls;
- produce the final Phase-2 evidence package and Phase-3 handoff.

## Source-sign contract

The nflverse source field `spread_line` is a home-margin center: positive means home favored. Canonical ATS notation remains:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `ats_residual = (home_score-away_score) + home_spread`.

## Fixed candidate state

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` — negative incremental result;
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` — structurally invalid under frozen V1 support contract;
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1` — negative incremental result.

No completed-2026 outcome signal has been used. Historical 2022–2025 evidence remains development/non-pristine. Production remains unchanged.
