# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `PHASE2_OPENING_RECEIPT.md`, `PHASE2_Q1_IMPLEMENTATION_RECEIPT.md`, `PHASE2_Q1_RESULT_RECEIPT.md`, and `PHASE2_Q2_RESULT_RECEIPT.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` / PR #556 merged | design frozen | closed |
| 2 | Controlled Implementation & Historical Development | **IN PROGRESS — STAGE A Q1 COMPLETE (NEGATIVE); STAGE B Q2 COMPLETE (STRUCTURALLY INVALID); STAGE C Q3 NEXT** | `research/ats-nextgen-phase2-q2` / PR #561 | Q1 valid negative incremental result; Q2 V1 failed frozen support guard before accepted performance artifact | validate/merge Stage-B result receipt head, then open Stage C and implement Q3 exactly as preregistered |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **NOT STARTED** | none | unavailable | only after Phase 2 completes |
| 4 | Prospective Shadow Validation | **CONDITIONAL / NOT STARTED** | none | unavailable | only if Phase 3 earns eligibility and continuation is explicitly authorized |

## Phase-1 integration

- PR: #556
- exact validated head: `c1397729b7f973169ef6fda700f481a91ad25538`
- merge SHA: `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`
- research firewall `35902704358`: SUCCESS
- research validation `35902704158`: SUCCESS
- Daily NFL model refresh/full pytest `35902704146`: SUCCESS

## Phase-2 opening integration

PR #559 exact validated head: `446b8f963c4125bad972f79a793035d0a9a777e0`.  
Opening merge / verified Stage-A base: `f43e17ba783e3e389969cd1649889b37bd91afe9`.

Frozen historical gate:

- 2,895 rows / 2,895 ATS eligible / 73 pushes / 0 completed-2026 outcomes;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- market evidence class `historical_closing_late_benchmark_exact_horizon_opaque`.

## Stage A — Q1 result

Branch: `research/ats-nextgen-phase2-q1`.  
PR: #560.  
Stage-A merge / Stage-B base: `a2581a62e3797a6ac466d614326bc72b7d5a1c57`.  
Accepted exact result head: `f14e2fa3ec78bf95578b4a5030fb66e94cd12cd0`.

Accepted evidence:

- workflow `35920622523`: SUCCESS;
- artifact ID `10776898518`;
- artifact digest `sha256:b544a4928a3e2ab80861b7b3fcf581a6b51355961b80aa05ddc5e4a0554d0c36`;
- 1,087 outer-OOF rows, seasons 2022–2025;
- Q1 OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- completed-2026 outcomes used: 0;
- production changed: no.

Scientific classification: **Q1 V1 is not incremental relative to market-only M2**.

Primary aggregate evidence:

- M0 mean pinball: `4.747240`;
- M2 mean pinball: `4.749986`;
- Q1 mean pinball: `4.750117`;
- Q1 minus M2: `+0.000131` (worse).

No Q1 rescue or redesign is authorized.

## Stage B — Q2 result

Branch: `research/ats-nextgen-phase2-q2`.  
PR: #561.  
Controlling pre-result head: `8503dbf250c97b0520cec30f985e9981fce83767`.

Exact-head validation:

- research firewall `35927280868`: **SUCCESS**;
- Phase-2 opening gate `35927280994`: **SUCCESS**;
- Q1 Stage-A reproducibility `35927280912`: **SUCCESS**;
- full repository validation `35927281014`: **SUCCESS**;
- research validation `35927280856`: **SUCCESS**;
- Q2 Stage B `35927280982`: **FAILURE after contract success**.

Inside Q2 run `35927280982`:

- contract job `107405457674`: **SUCCESS**;
- historical job `107405820497`: **FAILURE** before complete OOF/artifact upload.

Frozen failure:

- candidate state: generalized normal `beta=1.0`, `no_key_conditional_scale`, no key penalty;
- observed maximum folded endpoint mass: `0.0033487075822347966`;
- frozen material endpoint-mass threshold: `0.001`;
- frozen support: `[-75,+75]`.

Scientific classification: **Q2 V1 is structurally invalid under its frozen support/truncation contract.**

No accepted Q2 proper-score comparison exists. No complete Q2 OOF artifact was uploaded. The Stage-B opening receipt expressly requires fail-closed behavior rather than widening support after historical inspection, so Q2 V1 may not be rescued by changing support, threshold, arm set, family/grid, scale machinery, or key-number design.

The result is frozen in:

- `PHASE2_Q2_RESULT_RECEIPT.md`;
- `phase2_q2_result_registry.json`.

## Q2-to-Q3 handoff

The preregistered next stage is Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1`.

Stage C must begin only after the Stage-B result receipt head passes exact-head validation and PR #561 is merged. Q3 must then branch from the verified Stage-B merge and preserve the completed-2026 and production firewalls. Before historical execution it must prove half-point structural zero-push behavior and normalized cover/push/loss probabilities exactly as preregistered.

## Source-sign contract

The nflverse source field `spread_line` is a home-margin center: positive means home favored. Canonical ATS notation remains:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `ats_residual = (home_score-away_score) + home_spread`.

## Fixed prior evidence and firewalls

The completed Spread & Points program remains authoritative negative evidence and is not reopened. A0/B0/C0, generic residual stacking, large-disagreement heuristics and Candidate 5 may not be rescued by renaming them inside this program.

Frozen candidate IDs:

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` — valid negative incremental result;
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` — structurally invalid under frozen V1 support contract;
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1` — next / not started.

The completed-2026 outcome firewall remains active. Historical 2022–2025 evidence is development/non-pristine. Production remains unchanged.
