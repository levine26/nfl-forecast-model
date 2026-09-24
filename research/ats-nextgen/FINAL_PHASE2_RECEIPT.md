# ATS Next-Generation — Final Phase 2 Receipt

**Program:** `LEVLINE_ATS_NEXTGEN`  
**Phase:** 2 — Controlled Implementation & Historical Development  
**Status:** **COMPLETE**  
**Production:** `F-ST-01-FROZEN-2026` — unchanged  
**Completed-2026 outcomes used:** 0  
**Scientific closeout PR:** #563 — merged  
**Scientific closeout merge / verified main:** `a9ba2a5759c1308e6a47e682240a4e79dd419726`

This receipt closes Phase 2 after the full Q1/Q2/Q3 program and Stage-D uncertainty synthesis. It records integration/governance metadata only. It does not alter any accepted candidate evidence, train a model, inspect completed-2026 outcomes, or modify production forecasting behavior.

## 1. Final exact-head validation

Final Phase-2 Stage-D closeout head:

`619959f50bb7f9cbbc1ed9fbc562547db7f17487`

All eight pull-request workflows completed successfully on that exact head:

- LevLine research firewall — run `35938453981`: **SUCCESS**;
- ATS NextGen Phase-2 opening gate — run `35938454044`: **SUCCESS**;
- ATS NextGen Q1 Stage A — run `35938453917`: **SUCCESS**;
- ATS NextGen Q2 Stage B — run `35938453982`: **SUCCESS**;
- ATS NextGen Q3 Stage C — run `35938453947`: **SUCCESS**;
- ATS NextGen Phase-2 Stage D — run `35938454038`: **SUCCESS**;
- LevLine research validation — run `35938453967`: **SUCCESS**;
- Daily NFL model refresh / full pytest and regenerated-output validation — run `35938453954`: **SUCCESS**.

PR #563 merged with expected-head protection and `main` was then verified at:

`a9ba2a5759c1308e6a47e682240a4e79dd419726`

## 2. Historical gate identity

- 2,895 historical ATS-eligible games, 2015–2025;
- 73 pushes;
- completed-2026 outcomes: 0;
- canonical game-keyed SHA-256 `bc65419512759d296c98e3ac4e91ae89d32b544c262bcdd604de34bee61b1e6d`;
- historical line evidence remains `historical_closing_late_benchmark_exact_horizon_opaque`.

## 3. Final candidate evidence

### Q1 — `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`

**Phase-2 result:** valid negative incremental result versus M2.

- 1,087 chronology-clean OOF rows, 2022–2025;
- OOF SHA-256 `d82825c1e5f63d8e183960a931f402d2a776920f1c5d3b042a34d9c4896fa365`;
- Q1 − M2 mean-three-quantile pinball `+0.0001307888`;
- Stage-D 95% paired block-bootstrap interval `[-0.0023784358,+0.0025555440]`;
- `P(Q1 better than M2)=0.4554`.

No Q1 rescue is authorized.

### Q2 — `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

**Phase-2 result:** structurally invalid under the frozen V1 support/truncation contract.

- support `[-75,+75]`;
- observed maximum folded endpoint mass `0.0033487075822347966` exceeded threshold `0.001`;
- accepted Q2 OOF artifact: none;
- accepted Q2 primary performance: none;
- Q2 complementarity: unavailable;
- Q2/Q3 blend: unavailable.

No Q2 reconstruction or rescue is authorized.

### Q3 — `ATS-Q3-DIRECT-CPL-HURDLE-V1`

**Phase-2 result:** valid negative incremental result / not incremental versus Q3-M2.

- 1,087 chronology-clean OOF rows, 2022–2025;
- OOF SHA-256 `18610dfcfa9ffe71ed30259f9fef85a5655cefa68301f46fa1bb1950593dee04`;
- Q3 − Q3-M2 multinomial CPL log loss `+0.0013157419`;
- Stage-D 95% interval `[-0.0015590942,+0.0043366478]`;
- `P(Q3 better than Q3-M2)=0.1842`;
- non-push conditional-cover Brier delta `+0.0006716459`;
- `P(Q3 better on Brier)=0.1851`.

No Q3 rescue is authorized.

## 4. Accepted Stage-D synthesis

Original accepted scientific execution:

- head `0030de3fcc3fd094f1ce28eb0ab1c20b748ca67a`;
- tree `cf161bc7b47d8d138fd35dfe4889ccc215c91b5b`;
- workflow `35936805090`;
- artifact `10783239110`;
- artifact digest `sha256:4a3bd19a48528a2772e69232ad10b959b1f66e3885e44b56772f0b379abbcdd2`;
- 10,000 paired `(season, week)` bootstrap draws over 72 blocks, deterministic seed 26.

Final closeout reproduction:

- workflow `35938454038`: **SUCCESS**;
- artifact `10784362608`;
- the four scientific evidence files matched the original accepted artifact byte-for-byte by SHA-256:
  - `phase2_stage_d_summary.json` — `b6cb8e244d50e87d16c6da3356bcae6c0ee57bf63b9b809780e2e77cade144c2`;
  - `phase2_stage_d_paired_uncertainty.csv` — `c6680a25bc6acc17a6b552bd6c9593df166d17c5e2e750e1ebffa7d538ed6f1e`;
  - `phase2_stage_d_season_deltas.csv` — `28316ccf2e7009f0a9a9f1fe1a5e2f127a7f449dfb5cd04a15e506c7dd15f0bc`;
  - `phase2_stage_d_hit_rate_intervals.csv` — `885c4627c814286b76e6ba3e91c34bafd97b2079f4937448b385e7220df720b3`.

## 5. Production and evidence firewall

Phase 2 did not modify production F-ST coefficients/artifacts, production winner selection, Sunday Signal numerical forecasting, official prediction history, forecast locks, or grading behavior.

Historical 2022–2025 evidence remains development/non-pristine evidence. The program may not reinterpret simple ATS hit rate or hypothetical reference-juice economics as a rescue for a candidate that failed its primary proper/quantile objective.

## 6. Phase-3 handoff

Phase 2 is closed.

The next authorized stage is:

`PHASE_3_SCIENTIFIC_SYNTHESIS_CANDIDATE_SELECTION_AND_FREEZE`

Read `PHASE3_HANDOFF.md` before starting.

Phase 3 may classify each frozen architecture only as `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`. It may not reopen candidate development, inspect completed-2026 outcomes, rescue Q1/Q2/Q3, create Q2/blend evidence, or authorize production promotion.

Phase 4 remains conditional on Phase-3 prospective-shadow eligibility and explicit user authorization.
