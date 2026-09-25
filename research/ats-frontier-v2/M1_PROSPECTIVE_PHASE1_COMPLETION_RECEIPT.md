# M1 Prospective Phase 1 Completion Receipt

Program: `FV2-PROS-M1-MARKETSTATE-01`

Phase: `PROSPECTIVE PHASE 1 — CONTRACT ALIGNMENT AND CAPTURE QUALIFICATION`

Status: `PASS — MERGED`

Phase-1 implementation PR: `#596`

Validated implementation head: `4fefc53db96d9d48402e0023f013728cd9f7176e`

Merged main commit: `5b022b69b2b2a85fc37cfb829a5037c3f527f9fd`

Completed-2026 outcomes used: `0`

Production changes authorized: `NO`

## Implemented contract

Phase 1 now has an isolated research-only M1 stack:

- `research/m1_market_contract_v1.py` — frozen horizons, predictor/diagnostic roles, timing limits, book completeness, staleness, and feature registry;
- `research/m1_market_capture_due_v1.py` — stdlib-only schedule gate covering T-2160/T-720/T-360/T-120 plus T-60/T-30/latest-pre-kick diagnostic attempts;
- `research/run_m1_market_capture_v1.py` — append-only prospective collector using existing zero-cost provider infrastructure but M1-specific event identity and eligibility semantics;
- `research/m1_market_state_v1.py` — M1-specific point-in-time derivative with separate predictor and diagnostic artifacts;
- `research/test_m1_market_state_v1.py` and `research/test_run_m1_market_capture_v1.py` — synthetic, outcome-blind contract tests;
- `.github/workflows/research_m1_market_state_v1.yml` — PR validation plus scheduled off-main prospective capture;
- `M1_FEATURE_PROVENANCE_V1.md` — one-to-one frozen feature source and missingness registry.

## Blocking gaps closed in code

1. T-2160/T-720/T-360/T-120 predictor-context horizons are explicitly represented.
2. T-60/T-30/latest-pre-kick are mechanically diagnostic-only and emitted separately from the predictor artifact.
3. T-45 is outside the M1 identity and cannot enter the predictor registry.
4. All 12 frozen feature families have explicit field definitions, source horizons, and missingness semantics.
5. M1 book eligibility is frozen at two complete books per horizon and two common complete books for the T-360→T-120 path.
6. Quote staleness is frozen at >=15 minutes for V1.
7. Event matching accepts either provider full team names or schedule abbreviations, tolerates only bounded kickoff revisions, and fails closed on ambiguity.
8. Cross-horizon event ID or schedule-kickoff disagreement fails closed.
9. Later-than-cutoff observations are rejected rather than used to repair missed fixed horizons.
10. Completed-game outcome-bearing rows are rejected by the derivative.
11. Raw capture, predictor rows, diagnostic rows, status, and audit evidence persist on `research-data/m1-market-state-v1`, not production surfaces.

## Phase-1 exit evidence

All required gates passed on the exact implementation head before merge:

- M1-specific fixture/contract workflow: `SUCCESS`;
- research firewall: `SUCCESS`;
- repository-wide research validation: `SUCCESS`;
- Frontier-V2 pre-result gate: `SUCCESS`;
- diff audit: nine additive research/workflow files, zero deletions, no production-file changes;
- completed-2026 outcomes used: `0`.

The first M1-specific CI attempt exposed a fixture-expectation mismatch around kickoff-identity failure semantics. The implementation had already failed closed by making the predictor ineligible; the test was corrected to require that fail-closed behavior. The corrected exact head passed every gate above.

## Next phase boundary

Phase 1 is complete. The next phase is:

`M1 PROSPECTIVE PHASE 2 — LIVE ACCUMULATION AND OPERATIONAL QUALIFICATION`

Phase 2 is not a performance phase. It begins accumulating real immutable future-game T-2160/T-720/T-360/T-120 predictor-state captures and T-60/T-30/latest diagnostics under the frozen contract, and audits coverage/missingness/provider identity without looking at ATS outcome performance.

No ridge fitting, hyperparameter selection, CPL proper-score evaluation, ATS accuracy inspection, ROI analysis, retrospective reconstruction, or production deployment is authorized at the Phase-2 opening boundary.
