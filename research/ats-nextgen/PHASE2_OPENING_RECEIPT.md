# ATS Next-Generation — Phase 2 Opening Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Opening-gate status:** **COMPLETE — PRE-RESULT / PRE-FIT**  
**Phase-2 overall status:** **IN PROGRESS**  
**Primary branch:** `research/ats-nextgen-phase2`  
**Primary PR:** #559 — open at receipt creation  
**Base main SHA:** `ccccf37a74263a0a71cf3fecc198a61b163033bd`  
**Exact pre-receipt implementation head:** `961e486ee9747c69a4420373153adac5caa6d437`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged  
**Q1/Q2/Q3 fitting at receipt creation:** **NONE**

This receipt freezes the Phase-2 implementation/data-contract boundary before any Q1/Q2/Q3 candidate fitting or candidate-specific historical performance is generated. The receipt package itself must pass exact-head repository validation and be merged before Stage A Q1 execution is authorized.

## 1. Opening gate result

The dedicated real-data Phase-2 opening workflow passed on the pre-receipt implementation head:

- ATS NextGen Phase 2 opening gate — run `35916159139` (#4): **SUCCESS**;
- exact branch head recorded by the artifact: `961e486ee9747c69a4420373153adac5caa6d437`;
- invariant tests: **SUCCESS**;
- 2015–2025 real-data gate materialization: **SUCCESS**;
- protected production-surface diff proof: **SUCCESS**;
- immutable opening evidence upload: **SUCCESS**.

Opening artifact:

- artifact ID: `10774524253`;
- artifact name: `ats-nextgen-phase2-opening-7d5865e0a20aaeac579adf4db201054d0d7236a7`;
- artifact SHA-256: `71ffe60cb0e472bd311ead8eabb961afbca75a41f9f7eb04fb310a78800f4511`;
- artifact metadata head SHA: `961e486ee9747c69a4420373153adac5caa6d437`.

The artifact name contains GitHub's pull-request test-merge SHA for that run; the artifact metadata separately records the actual branch head above.

## 2. Exact historical gate identity

The pre-fit gate contains:

- seasons requested: 2015–2025 only;
- total rows: **2,895**;
- ATS-eligible rows: **2,895**;
- ineligible rows: **0**;
- pushes: **73**;
- completed-2026 outcomes used: **0**;
- candidate fitting performed: **false**;
- candidate performance generated: **false**;
- production changed: **false**.

Exact frame digests:

- raw serialized gate SHA-256: `0fabdc442e914ee9dc5cd501a728f1c1d69e11e01e44dd16ff800f46231fa20e`;
- canonical game-keyed gate SHA-256: `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`.

Historical market rows remain labeled exactly:

`historical_closing_late_benchmark_exact_horizon_opaque`

They are not relabeled T-120, open, close, or book-specific.

## 3. Source-sign correction frozen before results

A pre-result implementation audit identified a source-orientation mismatch in the first draft of the gate. The frozen Phase-1 scientific contract defines:

- `M = home_score - away_score`;
- `L = sportsbook_home_spread`, where a home favorite of 3 is `L=-3`;
- `R = M + L`.

The nflverse games data dictionary defines `spread_line` in the opposite source convention: a positive value means the home team was favored by that many points. Therefore the frozen Phase-2 source mapping is:

- source home-margin market center: `C = spread_line`;
- canonical sportsbook home spread: `L = -spread_line`;
- ATS residual: `R = M - spread_line = M + L`.

The correction was made before any Q1/Q2/Q3 fitting or candidate performance generation. It does not create a new candidate version; it makes the implementation conform to the already-frozen Phase-1 sign contract.

## 4. Chronology gate

The opening manifest freezes the exact chronology already preregistered in Phase 1:

- historical training floor: 2015;
- historical outcome ceiling: 2025;
- outer target seasons: 2022, 2023, 2024, 2025;
- for outer target season `s`, outer training is 2015 through `s-1`;
- inner rolling-origin targets begin in 2019 and stop at `s-1`;
- each inner target `t` is fit only on 2015 through `t-1`;
- random K-fold is prohibited;
- completed 2026 outcomes are prohibited.

The gate uses the repository's existing shifted alpha-0.15 team-state construction and sequential pregame Elo. Q1's centered-total features/interactions remain explicitly deferred to each training fold so no full-sample median can leak into target rows.

## 5. Frozen implementation identities

The opening registry binds the experiment to these exact blob identities from pre-receipt head `961e486ee9747c69a4420373153adac5caa6d437`:

- `src/nfl_forecast/challenger_ats_nextgen_gate.py` — `5be2162fbddf492b87b839b55397ca8cbb596b8a`;
- `scripts/run_challenger_ats_nextgen_phase2_gate.py` — `aca7fefe5abc12b91f64934c1f2c7e7b1f8689eb`;
- `tests/test_challenger_ats_nextgen_phase2_gate.py` — `10d741b14b869a87ff4bad572601524c645ff879`;
- `.github/workflows/research_ats_nextgen_phase2_gate.yml` — `8ea611cd7867b7dc707bdaf3517161cb3ca28819`;
- `.github/workflows/research_validation.yml` — `847b012a2b9779b88d37af9bb3e16bece51b99eb`;
- `config/model.yaml` — `c8db03a11c66254dc4ea897495c76b4152802bea`;
- `src/nfl_forecast/data.py` — `2fb21dd6b7254d4b1e7921ae33f77d4dd2578640`;
- `src/nfl_forecast/features.py` — `76c42479cb72ab38509e0b4bcee723eb638789d1`;
- `src/nfl_forecast/elo.py` — `a7e7ae9e312e188a8d8c751c8a65addaa19cfcfe`;
- `research/ats-nextgen/phase1_registry.json` — `7e47a10e27f278327e058ba4a64eb9c5310c4049`.

The machine-readable companion is `phase2_opening_registry.json`.

## 6. Pre-receipt validation

On the exact implementation head before this governance receipt was written:

- LevLine research firewall — run `35916158882` (#1965): **SUCCESS**;
- ATS NextGen Phase 2 opening gate — run `35916159139` (#4): **SUCCESS**;
- LevLine research validation run `35916158869` (#1547), foundation job `107368347650`: **SUCCESS**, including the new Phase-2 gate tests and protected-surface proof.

The full receipt/status head must now pass the repository's triggered checks. This receipt does not treat an in-progress or cancelled predecessor run as final evidence.

## 7. Production boundary

Phase 2 opening did not modify production F-ST coefficients/artifacts, production winner selection, Sunday Signal numerical forecasting, official public fair-spread behavior, prediction locks/history, or grading. All implementation lives on research-approved challenger/workflow/documentation surfaces.

## 8. Stage-A authorization boundary

Candidate identities remain exactly:

- Q1: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`;
- Q2: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`;
- Q3: `ATS-Q3-DIRECT-CPL-HURDLE-V1`.

At receipt creation, **Q1 fitting remains unauthorized**. Authorization occurs only after this opening receipt/registry/status package passes exact-head CI and is merged. The next scientific action after that integration point is Stage A Q1 only, implemented exactly from `Q1_QUANTILE_PREREGISTRATION.md`. Q2 and Q3 remain unopened until their preregistered sequence is reached.

> 2022–2025 is chronology-clean development evidence for this candidate execution but is not pristine independent confirmation because those seasons have informed prior LevLine research.

**Opening gate COMPLETE. Phase 2 IN PROGRESS. Q1/Q2/Q3 remain untrained at this receipt boundary.**
