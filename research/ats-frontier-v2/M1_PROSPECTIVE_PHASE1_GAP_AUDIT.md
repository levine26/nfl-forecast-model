# M1 Prospective Phase 1 — Implementation Gap Audit

Audit class: `OUTCOME_BLIND_INFRASTRUCTURE_AND_CONTRACT_REVIEW`

Candidate identity: `FV2-PROS-M1-MARKETSTATE-01`

Completed-2026 outcomes used: `0`

Production changes authorized: `NO`

## Authoritative target state

M1 is a T-120 prospective market-state experiment. Its predictor may use only information available at or before T-2160, T-720, T-360, and T-120. T-60, T-30, and latest-pre-kick exist only for later-market intermediate evaluation and calibration diagnostics.

The frozen M1 feature family at T-120 is:

1. consensus spread median;
2. consensus no-vig spread-side probability;
3. consensus no-vig moneyline probability;
4. consensus total;
5. cross-book spread dispersion;
6. active-book count / breadth;
7. median quote age and stale-book share;
8. T-360 to T-120 consensus number movement;
9. T-360 to T-120 price movement conditional on unchanged number;
10. T-360 to T-120 movement breadth;
11. key-number crossing indicator for 3 or 7;
12. spread/moneyline consistency residual.

## Existing infrastructure that can be reused

### `research_market_capture_v2.yml`

Useful and already governed behaviors:

- scheduled every five minutes;
- cheap local due gate before external requests;
- research-only provider credentials;
- append-style ledger restoration/persistence on `research-data/market-capture-v2` rather than `main`;
- explicit failure preservation;
- automatic downstream shadow/derivative hooks;
- no production authorization.

### `research/market_capture_v2.py` and capture contract

Useful existing concepts include provider normalization, event/kickoff identity fields, per-book plus consensus rows, quote freshness, spreads, moneylines, totals, no-vig probability construction, strict point-in-time timing fields, and research/production flags.

### `research_market_state_v1.yml` / `research/market_state_v1.py`

Useful existing concepts include:

- selecting only qualifying at-or-before rows;
- preserving missing horizons without imputation;
- exact request-level book pairing;
- rejecting cross-horizon identity disagreement;
- movement breadth and book-overlap features;
- immutable audit output with `completed_2026_outcomes_used = 0` and `production_authorized = false`.

These components should be reused where semantics match. They are not, by themselves, an M1 implementation.

## Material gaps

### GAP 1 — predictor-horizon mismatch — `BLOCKING`

Current generic due logic defines only:

- T-120;
- T-60;
- T-45;
- T-30.

Frozen M1 predictor context requires:

- T-2160;
- T-720;
- T-360;
- T-120.

Therefore the existing collector cannot currently construct the frozen pre-decision M1 path. T-60/T-45/T-30 may not be used as substitutes.

Required disposition: add or isolate exact pre-decision M1 horizon capture with the same fail-closed at-or-before semantics.

### GAP 2 — derived-state direction is wrong for the M1 predictor — `BLOCKING`

Current `market_state_v1.py` derives movement pairs such as T-60 minus T-120, T-45 minus T-120, and T-30 minus T-120. Those are post-decision information relative to the M1 T-120 decision state.

Frozen M1 requires the predictor path term T-360 to T-120. Existing post-T-120 pairs may remain as diagnostics but must never enter M1 predictor construction.

Required disposition: create an M1-specific derivative or a mechanically separated M1 mode whose predictor fields are built exclusively from allowed pre-decision horizons.

### GAP 3 — latest-pre-kick is not certified in the same M1 ledger contract — `NONBLOCKING_FOR_PREDICTOR / BLOCKING_FOR_FULL_DIAGNOSTIC_CONTRACT`

The frozen M1 preregistration requests latest-pre-kick for later-market diagnostics. The audited generic due logic does not define that horizon. Other repository workflows may collect near-kick state, but this audit does not treat a different research identity/ledger as an automatic substitute.

Required disposition: either materialize latest-pre-kick under the M1-qualified ledger contract or document a deterministic, provenance-safe join to an existing append-only source before using it in M1 diagnostics.

### GAP 4 — exact 12-feature materialization is not yet certified — `BLOCKING`

The generic market-state derivative exposes market probability, spread, total, probability range, book counts/freshness, and several movement breadth fields. It does not presently constitute an explicit one-to-one implementation of the frozen M1 feature registry.

In particular, Phase 1 must explicitly certify/source:

- spread-side no-vig probability separately from moneyline no-vig probability;
- cross-book spread dispersion under one fixed definition;
- stale-book share under one fixed threshold/definition;
- T-360→T-120 spread-price movement conditional on unchanged spread number;
- T-360→T-120 movement breadth;
- key-number crossing at 3 or 7;
- spread/moneyline consistency residual.

Required disposition: publish a field provenance matrix and tests before any live M1 training row is considered eligible.

### GAP 5 — book-count eligibility is not self-contained for M1 — `BLOCKING_FOR_REPRODUCIBILITY`

The generic capture contract exposes `MIN_CONSENSUS_BOOKS = 2`, while the scheduled observability workflow invokes capture with `--min-close-books 5` for its close-oriented qualification path.

This audit does not infer which generic value should become M1's rule. The M1 execution contract needs one explicit eligibility definition tied to the frozen prospective identity, including what happens when spread, side price, moneyline, or total have different book availability.

Required disposition: freeze M1-specific book-count/completeness semantics before eligible prospective rows are accumulated for model training/evaluation. This is an implementation/provenance detail and may not be tuned using outcomes.

### GAP 6 — event identity failed on the latest preserved due attempt — `BLOCKING_OPERATIONAL_DEFECT`

The latest preserved `research-data/market-capture-v2` status at opening reports:

- due pair count: 1;
- external request made: true;
- rows added: 0;
- status: skipped;
- reason: `no_qualified_market_rows`;
- missed: `2026_03_ATL_GB:T-45m:event_identity_unresolved`.

This does not invalidate M1 scientifically, but an unresolved provider↔schedule event identity can cause irreversible prospective missingness.

Required disposition: test and harden deterministic event resolution and kickoff-revision handling. Any unresolved case must continue to fail closed; no later quote may repair an earlier missed horizon.

### GAP 7 — no current derived market-state artifact on the data branch — `OPERATIONAL_READINESS`

At audit time, `research-data/market-capture-v2` contains `research_outputs/market_capture_v2` but no `research_outputs/market_state_v1` artifact. The state workflow is designed to derive only after a successful qualifying capture.

Required disposition: do not fabricate a derivative from failed/missing rows. Phase 1 should first make the capture contract M1-complete and validate the derivative with fixtures; future eligible live rows can then create immutable prospective evidence.

## Non-gaps / preserved strengths

The following do not need reinvention:

- five-minute scheduler cadence for near-horizon attempts;
- append-only off-main research persistence pattern;
- research/production firewall flags;
- no-later-than-cutoff semantics;
- per-book identity fields;
- missingness preservation;
- same-request book pairing;
- use of The Odds API / PropLine as prospective sources subject to the existing provider and quota controls.

## Minimum implementation strategy

Phase 1 should prefer additive isolation over rewiring generic research identities:

1. define an M1-specific horizon/eligibility contract that imports shared normalization utilities where safe;
2. add M1 predictor horizons T-2160/T-720/T-360/T-120;
3. add diagnostic T-60/T-30/latest-pre-kick with explicit `diagnostic_only` semantics;
4. create an M1-specific derivative/feature registry that cannot reference post-T-120 fields during predictor construction;
5. reuse the append-only data-branch pattern, with M1-specific audit metadata and immutable row identity;
6. test with synthetic fixtures and no game outcomes;
7. only after exact-head validation permit prospective accumulation of eligible M1 rows.

The existing T-45 infrastructure may continue for other research programs but is outside M1's frozen scientific identity.

## Phase-1 pass/fail rule

`PASS` requires code-level proof that the exact frozen information boundary can be captured and transformed reproducibly without future information or outcomes.

`FAIL/BLOCKED` applies if any required frozen predictor field cannot be reconstructed point-in-time from the prospective sources under a deterministic rule, or if satisfying it would require changing the preregistered hypothesis after outcome inspection.

No predictive performance result is valid or expected in this phase.
