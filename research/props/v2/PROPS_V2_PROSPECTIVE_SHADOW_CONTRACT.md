# LevLine Props 2.0 — Prospective Shadow Contract

Status: **FROZEN BEFORE PROSPECTIVE GRADING**  
Date frozen: 2026-09-19 UTC  
Production authorization: **NONE**

## Objective

Determine whether the strongest surviving Props 2.0 football mechanisms improve genuinely
prospective player-prop forecasts and market-relative decision quality without using completed
future outcomes for tuning.

## Benchmarks

### V1 benchmark

The currently published/frozen Props V1 forecast remains the benchmark. It is not changed by this
shadow program.

### Shadow A — PRIMARY

`P2-SHADOW-A-DEFENSE`

V1 plus only the two mechanisms that independently passed their true-pregame retrospective gates:

- strictly lagged opponent defensive-efficiency residual for **rushing yards/carry**;
- strictly lagged opponent defensive-efficiency residual for **receiving yards/reception**.

All opportunity, availability, touchdown, calibration, pricing, market and product logic otherwise
remain V1.

This is the primary prospective Props 2.0 football challenger.

### Shadow B — SECONDARY PRESPECIFIED ABLATION

`P2-SHADOW-B-DEFENSE-ROLE`

Shadow A plus the previously frozen Dynamic Role V0.1 **full** role adjustment.

Dynamic Role V0.1 improved retrospective Fair-Line MAE but did not establish a directional gain.
Therefore Shadow B is secondary and cannot replace Shadow A merely because one small prospective
slice looks favorable.

## Explicit exclusions

The following evaluated mechanisms are excluded:

- Dynamic Role V2 V0.2 — rejected;
- Game Environment V0.1 — rejected;
- signed-rushing pregame overlay V0.1 — rejected;
- generic team-TD negative-binomial overdispersion V0.1 — rejected.

Availability/workload mixture remains prospective-data-only because historical chronology was
insufficient. It is not added to Shadow A or B until a separately frozen prospective test supports
it.

## Prospective evidence boundary

No completed game outcome observed before this contract may count as prospective validation.

A forecast qualifies only when:
- the forecast artifact is generated and immutably timestamped before kickoff;
- all player-state/news/market inputs satisfy the existing PIT provenance policy;
- the exact model/version and source timestamps are archived;
- the matching market snapshot/horizon is archived under the frozen market-horizon contract;
- no target-game outcome has been observed when the forecast is created.

Historical 2023–2025 rows may be shown only as retrospective context and never mixed into
prospective scoring.

## No adaptive tuning

During the prospective sample, do **not** change because of observed outcomes:

- defensive residual coefficients;
- role half-lives/weights;
- market horizons;
- probability blend weights;
- edge thresholds;
- candidate inclusion;
- sportsbook selection;
- calibration method;
- minimum sample rule.

Any necessary engineering bug fix must be documented, versioned and must not use outcome direction
to choose the fix.

## Primary forecast metrics

For each supported market separately and pooled where scientifically valid:

- empirical CRPS;
- Fair-Line MAE;
- calibration / reliability for Over probability;
- Brier score;
- log loss where defined;
- 80% interval coverage and interval score;
- directional accuracy on decided rows.

Report paired differences versus V1 with game-clustered uncertainty.

Directional accuracy is important but cannot override materially worse proper scoring.

## Market-relative metrics

Once sufficient archived multi-book states exist:

- line MAE versus qualified consensus/close;
- probability Brier/log loss versus no-vig market probability;
- LevLine disagreement versus subsequent line movement;
- CLV versus separately qualified near-close/close state;
- cross-book dispersion and staleness diagnostics.

Do not call `EARLIEST_OBSERVED` sportsbook OPEN unless the source independently qualifies it as
OPEN.

## Economic metrics

Economic evaluation is secondary to forecast validity and must use frozen decision rules:

- ROI;
- average price;
- number of decisions;
- realized edge bucket;
- maximum drawdown;
- bootstrap uncertainty;
- sensitivity to realistic price availability.

No threshold optimization on the prospective outcome sample.

## Minimum evidence before any promotion discussion

No production promotion discussion before all of the following:

1. at least **300 paired decided props** for the relevant candidate/market family;
2. at least **100 unique games**;
3. coverage across at least **8 NFL weeks**;
4. no unresolved PIT/provenance or identity failures;
5. no material proper-score degradation versus V1;
6. positive evidence is not driven by one week, one team, one player or one prop subtype.

These are minimum discussion thresholds, not automatic promotion criteria.

## Candidate comparison

Primary scientific order:

1. Shadow A vs V1;
2. Shadow B vs Shadow A;
3. Shadow B vs V1 as supporting context.

This hierarchy prevents the weaker Dynamic Role V0.1 hypothesis from obscuring whether the
defensive-efficiency mechanism itself works prospectively.

## Governance conclusion

Retrospective evidence has identified mechanisms worth testing, not a production Props 2.0 model.

The production Props model remains V1 until a prospectively frozen candidate survives this contract.
