# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, `PHASE2_OPENING_RECEIPT.md`, and `PHASE2_Q1_IMPLEMENTATION_RECEIPT.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` / PR #556 merged | design frozen; no Phase-1 Q1/Q2/Q3 performance | closed |
| 2 | Controlled Implementation & Historical Development | **IN PROGRESS — STAGE A Q1 IMPLEMENTATION FROZEN** | `research/ats-nextgen-phase2-q1` | opening gate merged; Q1 pre-result implementation receipted; no Q1 historical performance yet | open Stage-A PR; require contract CI; only then execute frozen 2022–2025 Q1 OOF |
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

Exact-head validation:

- LevLine research firewall `35917266533` (#1969): **SUCCESS**
- ATS NextGen Phase 2 opening gate `35917266606` (#8): **SUCCESS**
- LevLine research validation `35917266598` (#1551): **SUCCESS**
- research-validation gate job `107376225489`: **SUCCESS**
- Daily NFL model refresh/full pytest + regenerated-output validation `35917266639` (#1104): **SUCCESS**

Frozen historical gate:

- 2,895 rows / 2,895 ATS eligible / 73 pushes / 0 completed-2026 outcomes;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- market evidence class `historical_closing_late_benchmark_exact_horizon_opaque`.

## Stage A — Q1 pre-result implementation

Branch: `research/ats-nextgen-phase2-q1`, created from the verified opening merge.  
Frozen pre-receipt implementation head: `6e9ad2eec0f4bc121f12a2133a85088df4a00d97`.

Receipts:

- `PHASE2_Q1_IMPLEMENTATION_RECEIPT.md`;
- `phase2_q1_registry.json`.

The frozen Stage-A implementation includes:

- exact Q1 quantiles `{10/21,1/2,11/21}`;
- exact alpha grid `{0.001,0.01,0.1,1.0}`;
- fold-local median imputation and scaling;
- fixed missingness indicators;
- frozen spread/total interactions;
- prior-only inner rolling-origin alpha selection by pinball loss;
- M0/M2/Q1 comparators;
- no quantile-crossing repair;
- preregistered key-number, favorite-size and total slices;
- a fail-closed opening-gate hash check before any fit;
- dedicated tests-before-results workflow dependency.

At this boundary:

- Q1 fitting performed: **NO**;
- Q1 historical performance generated: **NO**;
- Q2/Q3 started: **NO**;
- completed-2026 outcomes used: **0**;
- production changed: **NO**.

## Source-sign contract

The nflverse source field `spread_line` is a home-margin center: positive means home favored. Canonical ATS notation remains:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `ats_residual = (home_score-away_score) + home_spread`.

## Fixed prior evidence and firewalls

The completed Spread & Points program remains authoritative negative evidence and is not reopened. A0/B0/C0, generic residual stacking, large-disagreement heuristics and Candidate 5 may not be rescued by renaming them inside this program.

Frozen candidate IDs:

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1`

The completed-2026 outcome firewall remains active. Historical 2022–2025 evidence is development/non-pristine. Production remains unchanged.
