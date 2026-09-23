# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `PHASE2_OPENING_RECEIPT.md`, `PHASE2_Q1_IMPLEMENTATION_RECEIPT.md`, and `PHASE2_Q1_RESULT_RECEIPT.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` / PR #556 merged | design frozen | closed |
| 2 | Controlled Implementation & Historical Development | **IN PROGRESS — STAGE A Q1 COMPLETE (NEGATIVE); STAGE B Q2 NEXT** | `research/ats-nextgen-phase2-q1` / PR #560 | Q1 valid chronology-clean 2022–2025 OOF frozen; Q1 not incremental vs M2 | validate/merge Stage-A receipt head, then open Stage B and implement Q2 exactly as preregistered |
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
Accepted exact result head: `f14e2fa3ec78bf95578b4a5030fb66e94cd12cd0`.

Accepted exact-head workflows:

- ATS NextGen Q1 Stage A `35920622523` (#7): **SUCCESS**;
- LevLine research firewall `35920622410`: **SUCCESS**;
- ATS NextGen Phase 2 opening gate `35920622392`: **SUCCESS**;
- LevLine research validation `35920622570`: **SUCCESS**;
- Daily NFL model refresh/full pytest + regenerated-output validation `35920622374`: **SUCCESS**.

Accepted evidence:

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

By frozen quantile:

- 10/21: Q1 equals M2 on pinball and calibration;
- 1/2: Q1 is worse than M2 on pinball and absolute calibration error;
- 11/21: Q1 is modestly better than M2, but not enough to produce overall incremental evidence.

Season mean-pinball Q1 minus M2: 2022 `-0.004140`, 2023 `0.000000`, 2024 `+0.003698`, 2025 `+0.000950`.

The result is frozen in:

- `PHASE2_Q1_RESULT_RECEIPT.md`;
- `phase2_q1_result_registry.json`.

No Q1 rescue or redesign is authorized.

## Q1-to-Q2 handoff

Q2 remains the preregistered next scientific stage. Its center may consume only the chronology-clean Q1 median residual predictions from the frozen Stage-A interface. Stage B must reproduce the frozen Q1 OOF identity before Q2 fitting, or fail closed.

Before any Q2 historical score exists, Stage B must freeze and synthetically test implementation details left open by the preregistration, including continuous-to-integer bin integration and deterministic Q2-EMP smoothing. No target-period result may choose those details.

## Source-sign contract

The nflverse source field `spread_line` is a home-margin center: positive means home favored. Canonical ATS notation remains:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `ats_residual = (home_score-away_score) + home_spread`.

## Fixed prior evidence and firewalls

The completed Spread & Points program remains authoritative negative evidence and is not reopened. A0/B0/C0, generic residual stacking, large-disagreement heuristics and Candidate 5 may not be rescued by renaming them inside this program.

Frozen candidate IDs:

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1` — Stage A negative incremental result;
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1` — next;
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1` — not started.

The completed-2026 outcome firewall remains active. Historical 2022–2025 evidence is development/non-pristine. Production remains unchanged.
