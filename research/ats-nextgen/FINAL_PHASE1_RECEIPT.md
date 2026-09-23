# ATS Next-Generation — Final Phase 1 Receipt

**Program:** LEVLINE ATS NEXT-GENERATION RESEARCH PROGRAM  
**Phase:** 1 — Deep ATS Research, Problem Reformulation & Preregistration  
**Status:** **COMPLETE**  
**Primary branch:** `research/ats-nextgen-phase1`  
**Primary PR:** `#556`  
**Exact validated PR head:** `c1397729b7f973169ef6fda700f481a91ad25538`  
**Primary merge SHA:** `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`  
**Production model:** `F-ST-01-FROZEN-2026` — unchanged  
**Phase 2:** **NOT STARTED**

This is the immutable Phase-1 scientific closeout receipt. The scientific design below was frozen before any Q1/Q2/Q3 historical candidate output existed. The only post-freeze changes recorded here are integration/validation metadata and final phase status.

## Integration and exact-head validation receipt

- primary branch: `research/ats-nextgen-phase1`
- PR: `#556`
- exact validated PR head: `c1397729b7f973169ef6fda700f481a91ad25538`
- research validation: run `35902704158`, run number `1535`, conclusion **SUCCESS**
- research firewall: run `35902704358`, run number `1952`, conclusion **SUCCESS**
- full pull-request test/model-refresh workflow: run `35902704146`, run number `1086`, conclusion **SUCCESS**
- primary merge SHA: `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`
- merged-main verification: immediately after merge, `main` resolved to `80f84dc8282205c48dbfd8ca7e9e31c4be663bb6`
- merge preserved concurrent main work: the merge commit parents are contemporaneous main `ea9d175c7bee67b666766606fa445903cbb9d1a0` and exact validated research head `c1397729b7f973169ef6fda700f481a91ad25538`
- no Q1/Q2/Q3 training, candidate ATS performance, threshold tuning, ROI optimization, or completed-2026 outcome use occurred in Phase 1

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

The payout-motivated quantiles `10/21`, `1/2`, and `11/21` are reference decision quantiles for standard -110/no-push economics. They do **not** replace exact discrete push-aware wager economics on whole-number NFL spreads.

## Frozen candidates

### Q1 — Quantile market-residual model

Candidate ID: `ATS-Q1-QUANTILE-MARKET-RESIDUAL-V1`

- target: `R=M+L`;
- quantiles exactly `10/21`, `1/2`, `11/21`;
- learner: sklearn `QuantileRegressor` with L1 penalty;
- alpha grid `{0.001,0.01,0.1,1.0}`;
- alpha selection only through inner rolling-origin mean pinball loss;
- compact market + PIT-safe football state only;
- no nonlinear rescue learner or expanded quantile grid.

### Q2 — Discrete NFL margin distribution

Candidate ID: `ATS-Q2-DISCRETE-KEY-MARGIN-DISTRIBUTION-V1`

- integer PMF on `M=-75,...,+75`;
- main center `-L + q0.5_Q1(R|X)` using chronology-clean Q1 output;
- exactly four bounded distribution arms: generalized normal primary, Gaussian, Student-t, empirical discrete residual reference;
- generalized-normal beta grid `{1.0,1.25,1.5,1.75,2.0}`;
- Student-t df grid `{4,6,10}`;
- conditional scale uses only favorite size, centered market total, and their fixed interaction;
- explicit key-number excess only at `|k| in {3,6,7,10,14}` with training-only shrinkage;
- key-distance bands fixed at `[0,3.5)`, `[3.5,7.5)`, and `>=7.5`;
- key shrinkage grid `{1,10,100}`;
- whole-number push mass modeled directly; half-point push probability exactly zero;
- no post-result mixture/skew/density-family rescue.

### Q3 — Direct cover/push/loss probability head

Candidate ID: `ATS-Q3-DIRECT-CPL-HURDLE-V1`

- structural two-head L2-logistic hurdle model;
- Head A estimates push probability on whole-number spread rows and sets push=0 on half-lines;
- Head B estimates `P(cover | nonpush,X)`;
- C grid `{0.01,0.1,1.0,10.0}` selected by inner chronology / multinomial log loss;
- no class reweighting;
- no LightGBM/XGBoost/GAM/neural/isotonic/Platt rescue layer in V1.

## Q2/Q3 blend

Authorized before results:

`P_final = w*P_Q2 + (1-w)*P_Q3`

with frozen grid `w in {0,0.25,0.50,0.75,1.0}` selected only on inner prior-time OOF rows by multinomial log loss. No outer-row ATS/ROI tuning or bucket-specific weights.

## Market null hierarchy

- M0 — quoted spread, no LevLine adjustment;
- M1 — market-derived distribution, no football information;
- M2 — market + simple line-level calibration only, no football information.

Incremental football claims must beat the relevant market null on exact common chronology-clean rows. A candidate may be useful for calibration without being useful as a betting selector; those claims must remain separate.

## Evidence boundary

- 2022–2025 are development/non-pristine evidence for this new ATS family;
- historical positive results cannot authorize production;
- completed 2026 outcomes are prohibited from architecture, features, quantiles, distribution selection, key-mass choices, learner selection, thresholds, calibration, blend selection, rescue, and survival;
- outcome-blind prospective 2026 inputs may be inspected only for source qualification.

Any candidate that survives historical development and Phase-3 synthesis can earn only `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`; it cannot be promoted to production from 2022–2025 evidence alone.

## Chronology

Outer development targets are 2022–2025. For target season `s`, fit only prior seasons. Inner targets begin in 2019 and are themselves rolling-origin. Random K-fold is prohibited. Q1/Q2/Q3 preprocessing, shape/scale/key parameters and blend selection are all prior-time only.

Q2 may consume only chronology-clean Q1 median residual predictions for target rows. Same-row fitting or target-season fitted key-number/scale parameters are prohibited.

## Economics / price boundary

Standard -110 implies a no-push break-even of `110/210 = 52.38095%` and motivates `10/21`, `1/2`, `11/21` reference quantiles. Exact EV uses actual side price when available and explicitly accounts for push:

`EV = P(win)*W - P(loss)*R`.

Historical side price may not be fabricated. A `REFERENCE_MINUS110` sensitivity must be labeled hypothetical/reference rather than actual quoted-price ROI.

## Data / market boundary

Historical nflverse spread fields remain labeled `historical_closing_late_benchmark_exact_horizon_opaque`; they are not T-120. The repository has a PIT-safe T-120 selector for stored prospective run history, but current historical game-spread data do not establish complete side-price/book/timestamp coverage.

Therefore:

- historical line-based Q1/Q2/Q3 development is feasible under the documented benchmark limitations;
- exact historical juice-aware EV is allowed only where the actual side price is verified;
- multi-book latent fair-line work remains a prospective/later extension unless a historical source is separately qualified outcome-blind;
- player-state expansion is reserved for later and is not part of Q1–Q3 V1.

## External research conclusion

Peer-reviewed work supports the median/quantile decision framing and shows that market information evolves through the betting week. NFL scoring margins require discrete treatment because key-number and push mass are structurally relevant.

`nfelo` / `nfelotranslation` provide transferable architecture for separating a market/football center from a discrete key-number-aware margin distribution, but their fitted parameters are not copied. `nfl-bet-engine` provides useful simulator/direct-head/blend architecture but its reported performance remains third-party evidence and its broad iterative feature/tuning surface is not imported. David Sasser remains a useful observable product-semantic comparator; no reconstructable public methodology was located.

## Evaluation / power

Primary evidence is proper probability/distribution/quantile quality, not hit rate or ROI alone. Required metrics and frozen slices are in `EVALUATION_PROTOCOL.md`.

Pre-result power planning records the following approximate independent-decision requirements at one-sided alpha .05 and 80% power:

- against 50%: 53% ≈ 1,734; 54% ≈ 979; 55% ≈ 620;
- against standard -110 no-push break-even 52.38095%: 53% ≈ 40,243; 54% ≈ 5,879; 55% ≈ 2,248.

These calculations are optimistic because game dependence and selective-subset construction reduce effective information. One NFL season is not sufficient confirmation of a modest ATS edge.

## Selective evaluation freeze

Only these reporting subsets are authorized in V1:

1. all eligible games;
2. qualified positive-EV games when real quoted side price exists;
3. top fixed 20% by pre-outcome edge/EV score;
4. top fixed 10% by the same score.

No post-result percentile/threshold search is authorized.

Key-number reporting buckets are frozen at:

- K3: `2.5/3/3.5`;
- K6: `5.5/6/6.5`;
- K7: `6.5/7/7.5`;
- K10: `9.5/10/10.5`;
- K14: `13.5/14/14.5`.

## Production firewall

No Phase-1 scientific file changes production F-ST coefficients/artifacts, production winner selection, Sunday Signal forecasting behavior, public fair-spread semantics, official prediction history, forecast locks, or grading.

The exact-head research firewall succeeded, and the primary merge preserved unrelated concurrent `main` work rather than overwriting it.

## Final Phase-1 state

- Phase 1: **COMPLETE**
- Phase 2: **NOT STARTED**
- Q1/Q2/Q3 candidate performance: **DOES NOT EXIST FROM PHASE 1**
- completed-2026 outcome firewall: **INTACT**
- production: **UNCHANGED**

## Exact Phase-2 starting action

When Phase 2 is explicitly begun, create a dedicated research branch from the then-current `main`. Before fitting Q1:

1. implement canonical sign/ATS grading helpers under research-only surfaces;
2. add the frozen synthetic sign tests;
3. assert whole-/half-line push logic;
4. build the row-level provenance manifest for market and football features;
5. assert outer/inner expanding-window chronology and no random K-fold;
6. assert completed 2026 outcomes are absent;
7. freeze code/config digests and write the Phase-2 opening receipt;
8. only then implement and run frozen Q1.

Do not begin Q2 or Q3 before the required Q1 interface and chronology-clean OOF handoff exist. Do not modify production.