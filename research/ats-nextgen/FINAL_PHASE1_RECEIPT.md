# ATS Next-Generation — Final Phase 1 Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 1 — Deep ATS Research, Problem Reformulation & Preregistration  
**Status:** **COMPLETE**  
**Primary branch:** `research/ats-nextgen-phase1`  
**Primary PR:** #556 — **MERGED**  
**Exact validated PR head:** `c1397729b7f973169ef6fda700f481a91ad25538`  
**Primary merge SHA:** `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged  
**Phase 2:** **NOT STARTED**

This receipt closes Phase 1 after exact-head validation and merged-main verification. It records integration metadata only; the scientific specification was frozen before any Q1/Q2/Q3 historical candidate output existed.

## Exact-head validation

All required checks on `c1397729b7f973169ef6fda700f481a91ad25538` passed:

- LevLine research firewall — run `35902704358` (#1952): **SUCCESS**;
- LevLine research validation — run `35902704158` (#1535): **SUCCESS**;
- Daily NFL model refresh / full pytest and PR-output validation — run `35902704146` (#1086): **SUCCESS**.

The research-validation foundation included `tests/test_challenger_ats_nextgen_phase1.py`, which freezes candidate IDs, sign semantics, chronology, key-number set, blend grid, production firewall, completed-2026 firewall, and required Phase-1 artifacts. Protected production-surface diff checks passed.

## Fixed prior evidence accepted

The completed Spread & Points Next-Generation program remains fixed negative evidence. This program does not reopen A0/B0/C0, generic historical residual stacking, large-disagreement heuristics, or Candidate 5 under new names.

Accepted prior facts include approximately 9.962 independent margin MAE, approximately 9.494 historical market spread MAE, approximately 48.77% raw LevLine model-side ATS hit rate, no validated large-disagreement edge, no A0/B0/C0 incremental market-relative claim, and no Candidate-5 improvement to F-ST.

## Canonical ATS contract

- `M = home_score - away_score`;
- `L = sportsbook_home_spread`, with home favorite -3 represented as `L=-3`;
- `R = M + L`;
- cover iff `R>0`, push iff `R=0`, loss iff `R<0`.

ATS is modeled as conditional margin-distribution / cover-probability estimation around the quoted market threshold rather than unconditional mean-margin MAE alone.

## Frozen Q1

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`

- target `R=M+L`;
- quantiles exactly `10/21`, `1/2`, `11/21`;
- sklearn `QuantileRegressor`, L1 penalty;
- alpha grid `{0.001,0.01,0.1,1.0}`;
- inner rolling-origin selection by pinball loss;
- compact market + PIT-safe football state;
- no nonlinear rescue learner.

## Frozen Q2

`ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

- integer PMF on `M=-75,...,+75`;
- main center `-L + q0.5_Q1(R|X)` using chronology-clean Q1 output;
- four bounded arms: generalized normal primary, Gaussian, Student-t, empirical discrete residual;
- generalized-normal beta grid `{1.0,1.25,1.5,1.75,2.0}`;
- Student-t df grid `{4,6,10}`;
- conditional scale terms fixed to favorite size, centered total, and their interaction;
- training-only key-number excess at `|k|={3,6,7,10,14}` with frozen shrinkage grid;
- whole-number push mass modeled directly; half-point push probability exactly zero.

## Frozen Q3

`ATS-Q3-DIRECT-CPL-HURDLE-V1`

- two-head L2-logistic hurdle;
- Head A models push probability on whole-number spread rows, with structural `P(push)=0` on half-lines;
- Head B models `P(cover | nonpush,X)`;
- C grid `{0.01,0.1,1.0,10.0}` selected by prior-time multinomial log loss;
- no class reweighting, post-hoc calibration, LightGBM/XGBoost/GAM/neural rescue in V1.

## Q2/Q3 blend

Authorized before results:

`P_final = w*P_Q2 + (1-w)*P_Q3`

with `w ∈ {0,0.25,0.50,0.75,1.0}`, selected only inside prior-time inner validation by multinomial log loss. No outer-row ATS/ROI tuning or slice-specific weights.

## Market nulls and economics

M0 is the quoted spread with no LevLine adjustment. M1 is a market-derived distribution without football information. M2 is market + simple line-level calibration only, again without football information. Incremental football claims require improvement over the relevant market null on exact common chronology-clean rows.

Standard -110 implies no-push break-even `110/210 = 52.38095%` and motivates the `10/21`, `1/2`, `11/21` reference quantiles. Exact EV is push-aware: `EV=P(win)*W-P(loss)*R`. Historical spread-side prices may not be fabricated; `REFERENCE_MINUS110` is sensitivity only when actual price is unavailable.

## Evidence and chronology boundary

- 2022–2025 are development/non-pristine for this ATS family;
- outer targets are 2022–2025; target-season parameters use prior seasons only;
- inner targets begin in 2019 and are rolling-origin;
- random K-fold is prohibited;
- historical nflverse spread fields remain `historical_closing_late_benchmark_exact_horizon_opaque`, not T-120;
- multi-book latent fair-line work remains prospective/later-extension unless a historical source is separately qualified outcome-blind;
- player-state expansion is reserved for a later extension.

Completed 2026 outcomes are prohibited from architecture, features, quantile/distribution/key-number choices, learner selection, thresholds, calibration, blend selection, rescue, fitting, or historical survival decisions. Outcome-blind prospective 2026 inputs may be inspected only for source qualification.

## Research conclusion

The external evidence supports testing the new family: conditional quantiles around the market threshold, a discrete key-number-aware margin PMF, explicit push mass, heteroskedasticity, and a bounded direct probability head. It does not justify copying external fitted parameters, an unrestricted feature/learner tournament, fabricated historical juice, or treating third-party reported betting records as LevLine evidence.

Power remains a central constraint: under the preregistered one-sided alpha .05 / 80% calculation, approximately 2,248 independent decisions are needed to distinguish a true 55% ATS rate from 52.38095%; one 272-game season is not strong confirmation of a modest edge.

## Production firewall and stop

Phase 1 did not modify production F-ST coefficients/artifacts, production winner selection, Sunday Signal numerical forecasting, public fair-spread semantics, official prediction history, forecast locks, or grading. Q1/Q2/Q3 remain untrained and no new candidate-specific historical performance was inspected.

**Phase 1 is COMPLETE. Phase 2 is NOT STARTED. STOP.**
