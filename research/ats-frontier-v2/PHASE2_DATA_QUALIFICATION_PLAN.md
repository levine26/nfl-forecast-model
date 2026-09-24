# PHASE 2 DATA QUALIFICATION PLAN

**Program:** `LEVLINE_ATS_FRONTIER_V2`  
**Phase:** 2 — Data Qualification, PIT Reconstruction & Mechanism Feasibility  
**Evidence cutoff:** 2026-09-23

## Governing question

For every field, the test is whether it could be reconstructed from information genuinely available at the prediction timestamp. Phase 2 does not test whether any field predicts ATS outcomes.

## Lanes

1. **M1 market state:** verify provider timestamps, book identity, spread number and side price, moneyline, total, snapshot/line-change semantics, fixed-horizon reconstructability and historical access.
2. **M2 personnel state:** separate lagged ability from same-game PIT participation/role/replacement/announcement state; fail closed when historical revisions are unavailable.
3. **M3 hierarchical state:** verify chronology-safe lagged team/QB inputs from prior-game PBP and related data; rich unit state inherits M2 limitations.
4. **M4 discrete margin V2:** verify historical score/spread/total fields and the numerical representation required for a tail-safe integer-margin PMF; do not fit a model.

## Fixed market horizons

`T-2160`, `T-720`, `T-360`, `T-120`, `T-60`, `T-30`, and latest pre-kick.

For a target horizon `H`, select the latest quote satisfying `quote_timestamp_utc <= kickoff_timestamp_utc - H`. Never select a nearest quote that occurs after the target horizon.

## Outcome firewall

Allowed: schema, counts, coverage, timestamps, missingness, joins, revision behavior, quote density, source cadence and numerical representation diagnostics. Prohibited: ATS hit rate, ROI, proper-score performance, margin error, candidate-vs-market results, outcome-conditioned feature importance, completed-2026 result inspection, and threshold optimization.

## Production firewall

All work is research-only. `F-ST-01-FROZEN-2026` and Sunday Signal production forecasting behavior are outside this phase.