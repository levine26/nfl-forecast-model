# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`, `FINAL_PHASE1_RECEIPT.md`, and `PHASE2_OPENING_RECEIPT.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` / PR #556 merged | design frozen; no Phase-1 Q1/Q2/Q3 performance | closed |
| 2 | Controlled Implementation & Historical Development | **IN PROGRESS — OPENING GATE COMPLETE** | `research/ats-nextgen-phase2` / PR #559 | 2015–2025 pre-fit gate validated; opening receipt frozen; Q1/Q2/Q3 remain untrained | validate and merge opening receipt/status package; then execute Stage A Q1 exactly as preregistered |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **NOT STARTED** | none | unavailable | only after Phase 2 completes |
| 4 | Prospective Shadow Validation | **CONDITIONAL / NOT STARTED** | none | unavailable | only if Phase 3 earns eligibility and continuation is explicitly authorized |

## Phase-1 integration

- PR: #556
- exact validated head: `c1397729b7f973169ef6fda700f481a91ad25538`
- merge SHA: `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`
- research firewall `35902704358`: SUCCESS
- research validation `35902704158`: SUCCESS
- Daily NFL model refresh/full pytest `35902704146`: SUCCESS

## Phase-2 opening gate

Pre-receipt implementation head: `961e486ee9747c69a4420373153adac5caa6d437`.

- ATS NextGen Phase 2 opening gate `35916159139` (#4): **SUCCESS**
- LevLine research firewall `35916158882` (#1965): **SUCCESS**
- research-validation foundation job `107368347650` in run `35916158869`: **SUCCESS**
- real historical gate: 2,895 rows / 2,895 ATS eligible / 73 pushes / 0 completed-2026 outcomes
- gate canonical game-keyed SHA-256: `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`
- opening artifact ID: `10774524253`
- opening artifact SHA-256: `71ffe60cb0e472bd311ead8eabb961afbca75a41f9f7eb04fb310a78800f4511`
- opening receipt: `PHASE2_OPENING_RECEIPT.md`
- machine registry: `phase2_opening_registry.json`

The opening receipt/status package itself must pass exact-head CI and merge before Q1 fitting is authorized.

## Source-sign engineering correction

The nflverse source field `spread_line` is a home-margin center: positive means the home team was favored. The frozen ATS contract uses sportsbook home-spread notation where a home favorite is negative. The Phase-2 gate therefore fixes:

- `market_home_margin_center = spread_line`;
- `home_spread = -spread_line`;
- `ats_residual = (home_score-away_score) + home_spread`.

This correction was completed before candidate fitting or candidate performance generation and implements, rather than changes, the frozen Phase-1 sign contract.

## Fixed prior evidence

The completed Spread & Points program remains authoritative negative evidence. It is not reopened. A0/B0/C0, generic residual stacking, large-disagreement heuristics, and Candidate 5 may not be rescued by renaming them inside this program.

## Frozen candidate IDs

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1`

The completed-2026 outcome firewall remains active. Historical 2022–2025 evidence is development/non-pristine. Production remains unchanged. Q1/Q2/Q3 are still untrained at the opening-receipt boundary.
