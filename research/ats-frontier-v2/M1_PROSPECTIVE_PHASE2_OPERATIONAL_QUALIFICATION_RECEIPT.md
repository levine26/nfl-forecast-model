# M1 Prospective Phase 2 Operational Qualification Receipt

Program: `FV2-PROS-M1-MARKETSTATE-01`

Phase: `PROSPECTIVE PHASE 2 — LIVE ACCUMULATION AND OPERATIONAL QUALIFICATION`

Work unit: `PHASE-2 OPERATIONAL HARDENING — HORIZON STATE + FAILURE CAUSE DURABILITY`

Status: `IMPLEMENTED — PENDING EXACT-HEAD VALIDATION`

Completed-2026 outcomes used: `0`

Production changes authorized: `NO`

Production changed: `NO`

## Why this work was necessary

The Phase-2 opening merged in PR #597 and activated prospective accumulation at `2026-09-25T16:35:06Z`. The first scheduled M1 run after activation, workflow run `36161906799`, completed successfully with the local horizon gate reporting `due=false`; no provider request was made.

That run exposed two operational observability gaps in the otherwise-frozen Phase-1 capture implementation:

1. **Elapsed-horizon observability:** when a scheduled run occurred after a frozen cutoff, the cheap `due=false` path did not persist whether the state meant “nothing is due yet” or “a Phase-2 horizon has elapsed without a valid capture.” Phase 2 requires those states to remain distinguishable without reconstructing a late quote.
2. **Early-exit cause durability:** outcome-blind collector exits such as `missing_market_api_key` and `free_quota_reserve_reached` were returned to the workflow but were not guaranteed to be written to the durable M1 `status.json`. An all-provider failure could likewise terminate before a durable M1 status existed.

These are evidence/observability defects, not modeling defects. Repairing them is explicitly authorized by Phase 2 because the repair is outcome-blind and leaves the frozen scientific identity unchanged.

## Implemented repair A — deterministic horizon qualification ledger

`research/m1_operational_qualification_v1.py` adds a stdlib-only, outcome-blind operational state derivation.

For each fixed M1 horizon it records one of:

- `pre_phase2_boundary`
- `future`
- `capture_window_open`
- `captured`
- `missed_no_valid_capture`

`LATEST_PREKICK` is tracked separately with the same operational distinction and remains `diagnostic_only`.

The audit consumes only schedule/identity fields from the slate plus qualifying M1 consensus capture evidence. It does not read ATS outcomes, scores, margins, cover labels, or completed-game performance.

Durable artifacts:

- `research_outputs/m1_market_state_v1/horizon_qualification.csv`
- `research_outputs/m1_market_state_v1/operational_qualification.json`

The Phase-2 activation timestamp is used only to distinguish horizons that were impossible to capture prospectively before Phase 2 existed. It does not modify the M1 timing contract, feature registry, or eligibility rules.

## Implemented repair B — durable collector status on every exit

`research/run_m1_market_capture_phase2_v1.py` wraps the frozen Phase-1 collector without changing its scientific behavior.

The wrapper persists `status.json` for:

- successful captures;
- ordinary no-capture returns;
- missing provider credentials;
- quota-reserve protection;
- all-provider API failure;
- unexpected capture exceptions.

Provider failures are persisted and then re-raised, so a workflow remains visibly failed after its evidence is preserved.

The wrapper does **not** change:

- due-horizon selection;
- the 7.5-minute no-later-than-cutoff window;
- provider preference/failover order;
- event matching;
- minimum complete-book eligibility;
- common-book path requirements;
- quote staleness semantics;
- market-row normalization;
- consensus construction;
- predictor features;
- diagnostic-only separation.

## Workflow integration

The M1 scheduled workflow is amended to:

1. restore the prior append-only M1 data/qualification state on every scheduled run;
2. derive the outcome-blind horizon qualification state before any provider request;
3. execute the same cheap due-horizon gate;
4. make provider calls only when the frozen due gate says a horizon is due (or on explicit workflow dispatch);
5. use the status-persisting Phase-2 wrapper for the otherwise-frozen collector;
6. derive predictor/diagnostic artifacts only after a successful capture;
7. refresh the operational qualification state after a successful capture;
8. persist M1 research evidence off `main` even when no market request is due, but commit only when the durable state actually changes;
9. surface capture failure after evidence persistence.

The research data branch remains:

`research-data/m1-market-state-v1`

No production surface is an intended output of this work.

## Test coverage added

The new fixture tests prove that:

- fixed horizons transition deterministically from future → open → missed when no qualifying capture exists;
- a qualifying two-book consensus closes a fixed horizon as captured;
- horizons whose targets predate Phase-2 activation are not mislabeled as prospective misses;
- outcome-bearing source columns are ignored and never enter the qualification artifact;
- `LATEST_PREKICK` remains diagnostic-only;
- early collector skips are durably persisted;
- provider failures are durably persisted and still raised;
- successful base collector results retain their scientific fields while receiving Phase-2 governance metadata.

## Frozen scientific identity after this repair

Unchanged:

- predictor horizons: `T-2160m`, `T-720m`, `T-360m`, `T-120m`;
- diagnostic-only horizons: `T-60m`, `T-30m`, `LATEST_PREKICK`;
- fixed-horizon tolerance: `7.5 minutes`, no later than cutoff;
- minimum complete books: `2`;
- T-360→T-120 common-book requirement: unchanged;
- stale quote threshold: `15 minutes`;
- frozen M1 feature registry: unchanged;
- completed-2026 outcomes used: `0`;
- production LevLine/F-ST: unchanged and unauthorized for modification.

## Exact-head merge gate

This work unit is not PASS until its exact PR head clears:

- the M1-specific contract/fixture workflow including the new Phase-2 tests;
- the LevLine research firewall;
- repository-wide research validation;
- the applicable Frontier-V2 pre-result gate;
- a diff audit confirming research/workflow/docs-only changes;
- completed-2026 outcomes used = `0`.

## Phase status after this work

This is **not** the Phase-2 closeout and does not open Phase 3.

After merge, Phase 2 remains `OPEN — ACTIVE / ACCUMULATING`. The next scientific evidence must come from real future-game prospective captures under the frozen horizons. No late reconstruction is permitted merely to accelerate the program.

No M1 predictive-performance evaluation, model fitting, lambda selection, ATS hit-rate inspection, calibration scoring, ROI analysis, or production deployment is authorized by this receipt.
