# M1 Prospective Phase 2 Opening Receipt

Program: `FV2-PROS-M1-MARKETSTATE-01`

Phase: `PROSPECTIVE PHASE 2 — LIVE ACCUMULATION AND OPERATIONAL QUALIFICATION`

Status: `OPEN — ACTIVE`

Phase-2 opening merged: `3434f34f1b8760334e457e0a701eca031224871f`

Opening PR: `#597`

Activated at: `2026-09-25T16:35:06Z`

Completed-2026 outcomes used to open Phase 2: `0`

Production changes authorized: `NO`

## Activation evidence

The Phase-2 opening head cleared the M1 contract workflow, research firewall, Frontier-V2 pre-result gate, and full repository research-validation matrix before PR #597 merged. The first scheduled M1 run after activation was workflow run `36161906799`; its local horizon gate returned `due=false`, so all provider/capture steps were correctly skipped and no external market request was made.

That first run is operational evidence only. It is not predictive-performance evidence and does not inspect any completed-game ATS result.

## Purpose

Phase 2 converts the Phase-1-tested M1 contract into prospective evidence accumulation. The objective is to prove that the frozen capture system can repeatedly obtain, persist, join, and derive valid point-in-time market-state evidence on future NFL games without leakage, silent horizon repair, identity drift, or dependence on completed-game outcomes.

This is an operational/data-quality phase, not a predictive-performance phase.

## Authorized live evidence

The scheduled M1 workflow may prospectively collect and persist:

### Predictor-context captures

- `T-2160m`
- `T-720m`
- `T-360m`
- `T-120m`

Only information available no later than each frozen cutoff is admissible. Later requests cannot repair missed horizons.

### Diagnostic-only captures

- `T-60m`
- `T-30m`
- `LATEST_PREKICK`

These may support later-market intermediate evaluation only after a future evaluation phase is separately opened. They remain mechanically excluded from the T-120 predictor registry during Phase 2.

Existing `T-45m` infrastructure remains outside M1.

## Authorized Phase-2 activities

Phase 2 may:

1. run the scheduled research-only M1 collector on future games;
2. append immutable raw market observations to `research-data/m1-market-state-v1`;
3. materialize frozen T-120 predictor rows when the preregistered information boundary is satisfied;
4. materialize T-60/T-30/latest-pre-kick diagnostic rows separately;
5. audit horizon coverage, timing error, book completeness, common-book overlap, quote age, stale share, provider identity, event identity, kickoff identity, duplicate handling, quota status, and missingness reasons;
6. repair operational bugs only when the repair is outcome-blind and preserves the frozen scientific identity;
7. record every operational amendment explicitly before it can affect subsequent captures.

## Explicitly prohibited during Phase 2

Phase 2 may not:

- read completed-2026 ATS outcomes for M1 evaluation or tuning;
- fit the ridge later-market model;
- fit the ridge multinomial cover/push/loss correction;
- select between regularization values `{10, 100}`;
- calculate M1 cover/push/loss log loss, Brier score, calibration, hit rate, CLV-conditioned ATS performance, or ROI as a performance conclusion;
- use T-60/T-30/latest-pre-kick state as T-120 predictor input;
- retroactively reconstruct a missed predictor horizon from a later quote;
- weaken the two-complete-book or two-common-book eligibility rules based on observed outcomes;
- change the frozen 12-feature family based on prospective game results;
- modify or deploy the production LevLine/F-ST model.

## Operational qualification ledger

Each prospective capture attempt should preserve enough evidence to distinguish at minimum:

- no horizon due;
- quota reserve reached;
- provider/API failure;
- event identity unresolved;
- kickoff identity outside tolerance;
- insufficient complete books;
- insufficient common T-360/T-120 books;
- qualifying predictor row created;
- diagnostic-only row created;
- horizon missed because the no-later-than-cutoff window elapsed.

Missing data are evidence. Phase 2 must not convert missingness into an imputed successful capture merely to improve apparent coverage.

## Phase-2 qualification questions

Before any later performance phase can be proposed, Phase 2 must be able to answer outcome-blind questions including:

1. Does the scheduled job actually fire at every frozen horizon on real future slates?
2. Are event/team/kickoff identities stable across the path?
3. Are at least two complete books commonly available at the required predictor horizons?
4. Is T-360→T-120 common-book overlap sufficient to derive the frozen path features without ad hoc repair?
5. Are request timestamps and timing errors preserved so the strict no-later-than-cutoff rule is auditable?
6. Are diagnostic horizons physically separated from predictor artifacts?
7. Are provider/quota failures distinguishable from scientific missingness?
8. Can the ledger be replayed deterministically into the same predictor rows without completed-game outcomes?

## Phase-2 exit rule

Phase 2 does not end merely because one capture succeeds. A later closeout must provide a prospective, outcome-blind operational qualification receipt based on real future-game evidence showing that the capture/derivative pipeline is functioning as frozen, or it must document the blocker and remain in accumulation.

The size/duration of a future training window and the opening of any Phase 3 modeling/evaluation stage must be governed separately before M1 outcome inspection. This receipt intentionally does not set a result-driven sample threshold.

## Active boundary

Phase 2 is now the active M1 phase. The scheduled workflow may accumulate prospective research evidence under the frozen contract.

No M1 predictive-performance evaluation is authorized by this receipt.
