# ATS Next-Generation — Final Phase 1 Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 1 — Deep ATS Research, Problem Reformulation & Preregistration  
**Status:** **PRE-MERGE FREEZE COMPLETE — EXACT-HEAD VALIDATION PENDING**  
**Primary branch:** `research/ats-nextgen-phase1`  
**Scientific package freeze head before this receipt:** `b523ce382077184a97e107bf80c6a298def8c2ce`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged  
**Phase 2:** **NOT STARTED**

This receipt records the Phase-1 scientific freeze before any Q1/Q2/Q3 historical candidate output exists. After the primary Phase-1 PR is validated and merged, this receipt may be amended only with immutable integration metadata (validated PR head, PR number, CI runs, merge SHA, merged-main verification, and final status). Scientific design fields may not be changed in that closeout amendment.

## Fixed prior evidence accepted

The completed Spread & Points Next-Generation program remains fixed negative evidence. The ATS program does not reopen A0/B0/C0, generic historical residual stacking, large-disagreement heuristics, or Candidate 5 under new names.

Prior authoritative facts include:

- independent margin MAE approximately 9.962;
- historical market spread MAE approximately 9.494;
- raw LevLine model-side ATS hit rate approximately 48.77%;
- market beat LevLine on margin MAE;
- large disagreement was not a validated edge;
- A0/B0/C0 did not establish standalone/incremental market-relative superiority;
- Candidate 5 did not improve F-ST.

## Frozen new scientific formulation

The canonical home-oriented contract is:

- `M = home_score - away_score`;
- `L = sportsbook_home_spread` with home favorite -3 represented as `L=-3`;
- `R = M + L`;
- cover iff `R>0`, push iff `R=0`, loss iff `R<0`.

ATS is treated as conditional margin-distribution / cover-probability estimation around the quoted market threshold, not merely unconditional mean-margin MAE minimization.

## Frozen candidates

### Q1

`ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`

- target: `R=M+L`;
- quantiles exactly `10/21`, `1/2`, `11/21`;
- learner: sklearn `QuantileRegressor` with L1 penalty;
- alpha grid `{0.001,0.01,0.1,1.0}`;
- inner rolling-origin selection by pinball loss;
- compact market + PIT-safe football state only;
- no nonlinear rescue learner.

### Q2

`ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

- integer PMF on `M=-75,...,+75`;
- main center `-L + q0.5_Q1(R|X)` using chronology-clean Q1 output;
- exactly four bounded distribution arms: generalized normal primary, Gaussian, Student-t, empirical discrete residual reference;
- generalized-normal beta grid `{1.0,1.25,1.5,1.75,2.0}`;
- Student-t df grid `{4,6,10}`;
- conditional scale uses only favorite size, centered market total, and their fixed interaction;
- explicit key-number excess only at `|k| in {3,6,7,10,14}` with training-only shrinkage;
- whole-number push mass modeled directly; half-point push probability exactly zero.

### Q3

`ATS-Q3-DIRECT-CPL-HURDLE-V1`

- structural two-head L2-logistic hurdle model;
- Head A estimates push probability on whole-number spread rows and sets push=0 on half-lines;
- Head B estimates `P(cover | nonpush,X)`;
- C grid `{0.01,0.1,1.0,10.0}` selected by inner chronology / multinomial log loss;
- no LightGBM/XGBoost/GAM/neural/isotonic/Platt rescue layer in V1.

## Q2/Q3 blend

Authorized before results:

`P_final = w*P_Q2 + (1-w)*P_Q3`

with frozen grid `w in {0,0.25,0.50,0.75,1.0}` selected only on inner prior-time OOF rows by multinomial log loss. No outer-row ATS/ROI tuning or bucket-specific weights.

## Market null hierarchy

- M0 — quoted spread, no LevLine adjustment;
- M1 — market-derived distribution, no football information;
- M2 — market + simple line-level calibration only, no football information.

Incremental football claims must beat the relevant market null on exact common chronology-clean rows.

## Evidence boundary

- 2022–2025 are development/non-pristine evidence for this new ATS family;
- historical positive results cannot authorize production;
- completed 2026 outcomes are prohibited from architecture, features, quantiles, distribution selection, key-mass choices, learner selection, thresholds, calibration, blend selection, rescue, and survival;
- outcome-blind prospective 2026 inputs may be inspected only for source qualification.

## Chronology

Outer development targets are 2022–2025. For target season `s`, fit only prior seasons. Inner targets begin in 2019 and are themselves rolling-origin. Random K-fold is prohibited. Q1/Q2/Q3 preprocessing, shape/scale/key parameters, calibration and blend selection are all prior-time only.

## Economics / price boundary

Standard -110 implies a no-push break-even of `110/210 = 52.38095%` and motivates `10/21`, `1/2`, `11/21` reference quantiles. Exact EV uses actual side price when available and explicitly accounts for push:

`EV = P(win)*W - P(loss)*R`.

Historical side price may not be fabricated. A `REFERENCE_MINUS110` sensitivity must be labeled hypothetical/reference rather than actual quoted-price ROI.

## Data / market boundary

Historical nflverse spread fields remain labeled `historical_closing_late_benchmark_exact_horizon_opaque`; they are not T-120. The repository has a PIT-safe T-120 selector for stored prospective run history, but current historical game-spread data do not establish complete side-price/book/timestamp coverage. Multi-book latent fair-line work therefore remains prospective/later-extension unless a historical source is separately qualified outcome-blind.

## External research conclusion

Peer-reviewed work supports the median/quantile decision framing and shows that market information evolves through the betting week. `nfelo`/`nfelotranslation` provide transferable architecture for market separation and discrete key-number-aware margin distributions. `nfl-bet-engine` provides useful simulator/direct-head/blend architecture but its reported performance is third-party evidence and its broad iterative feature/tuning surface is not imported. David Sasser remains a useful observable product-semantic comparator; no reconstructable public methodology was located.

## Evaluation / power

Primary evidence is proper probability/distribution/quantile quality, not hit rate or ROI alone. Required metrics and fixed slices are in `EVALUATION_PROTOCOL.md`. Pre-result exact-binomial power planning shows approximately 2,248 independent decisions are required for 80% power at one-sided alpha .05 to detect a true 55% rate against 52.38095%; a single 272-game season is inadequate confirmation of modest ATS edge.

## Production firewall

No Phase-1 file modifies production F-ST coefficients/artifacts, production winner selection, Sunday Signal forecasting behavior, public fair-spread semantics, official prediction history, forecast locks, or grading.

## Stop condition

No Q1/Q2/Q3 training or candidate-specific historical performance is authorized in Phase 1. Phase 2 remains **NOT STARTED** until this package is exact-head validated, merged, and the merged-main closeout metadata is recorded.
