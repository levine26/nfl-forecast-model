# ATS Next-Generation — Phase Status

**Authority:** `MASTER_PLAN.md`  
**Last updated:** 2026-09-23 America/Los_Angeles  
**Production:** `F-ST-01-FROZEN-2026` — unchanged

| Phase | Name | Status | Branch | Evidence state | Exact next action |
|---|---|---|---|---|---|
| 1 | Deep ATS Research, Problem Reformulation & Preregistration | **COMPLETE** | `research/ats-nextgen-phase1` | design/preregistration only; Q1/Q2/Q3 untrained | no further Phase-1 work |
| 2 | Controlled Implementation & Historical Development | **NOT STARTED** | none | no Q1/Q2/Q3 performance exists | create Phase-2 research branch from then-current `main`; implement sign/chronology/provenance gates and frozen Q1 only |
| 3 | Scientific Synthesis, Candidate Selection & Freeze | **NOT STARTED** | none | unavailable | only after Phase 2 completes |
| 4 | Prospective Shadow Validation | **CONDITIONAL / NOT STARTED** | none | unavailable | only if Phase 3 earns eligibility and user authorizes continuation |

## Phase-1 closeout provenance

- primary branch: `research/ats-nextgen-phase1`
- PR: `#556`
- exact validated PR head: `c1397729b7f973169ef6fda700f481a91ad25538`
- research validation: run `35902704158` / run number `1535` — **SUCCESS**
- research firewall: run `35902704358` / run number `1952` — **SUCCESS**
- full pull-request test/model-refresh workflow: run `35902704146` / run number `1086` — **SUCCESS**
- primary merge SHA: `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`
- merged-main verification: `main` resolved to that merge SHA immediately after merge

## Fixed prior evidence

The completed Spread & Points program remains authoritative negative evidence. It is not reopened. In particular, A0/B0/C0 and Candidate 5 may not be rescued by renaming them inside this program.

## Phase-1 forbidden actions respected

Phase 1 did not train or score Q1/Q2/Q3, inspect candidate-specific ATS performance, select thresholds from outcomes, optimize historical ROI, use completed 2026 outcomes, or alter production.

## Frozen candidate IDs

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1`

These identities are now frozen for Phase 2. Any scientific change requires an explicit preregistration amendment/version before new candidate performance is inspected.