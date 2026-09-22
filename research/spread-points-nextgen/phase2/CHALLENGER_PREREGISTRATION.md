# Phase 2 — Challenger Preregistration

**Status:** FROZEN DESIGN SPECIFICATION before Phase 3 challenger results  
**Production authorization:** none  
**Completed-2026 outcomes allowed for selection:** no

This document defines the only initial model families authorized for Phase 3 implementation. Any material expansion requires a new Phase 2 decision entry before results from the proposed expansion are inspected.

---

# 1. Research questions

Phase 3 will answer four separate questions:

1. Can a better football-only model reduce team-point, margin and total error?
2. Can a football-process decomposition reduce the Phase 1 compression failure?
3. Can football information predict residual error around a strong sportsbook prior?
4. If distinct models add complementary OOS information, can a nested ensemble improve the predictive distribution?

Questions 1–3 define initial challengers. Question 4 is conditional and cannot be activated merely because stacking is available.

---

# 2. Challenger A — Dynamic Opponent-Adjusted Joint Score Model

**Class:** football-only  
**Priority:** primary

## Hypothesis

A partially pooled dynamic offense/defense model will outperform the current direct rolling-feature regressions by:

- adapting team strength more coherently over time;
- separating offense and defense;
- adjusting for opponent quality;
- shrinking noisy short samples;
- avoiding arbitrary duplicated 3/5/8/EWMA feature families;
- producing internally coherent home and away score expectations.

## Core structure

At forecast time each team has latent states such as:

- offensive strength;
- defensive strength;
- optionally passing and rushing subcomponents only if preregistered ablation shows they are estimable without feature explosion.

States evolve over time using a simple autoregressive/state-space or discounted hierarchical update.

Expected home and away scoring are functions of:

- league scoring environment known before the game;
- home offense state vs away defense state;
- away offense state vs home defense state;
- home-field effect;
- rest differential;
- a bounded set of lagged opponent-adjusted efficiency summaries.

## Allowed data families

- prior completed-game nflverse PBP;
- lagged EPA/success measures;
- sequential Elo or a preregistered initialization prior;
- schedule/home/away/rest;
- season/week;
- static venue/roof only if truly static and chronology-safe.

## Forbidden initial inputs

- market spread, total or moneyline;
- final historical QB starter ID unless separately PIT-qualified;
- hindsight injury/inactive status;
- realized weather;
- news text;
- completed 2026 outcomes;
- current-game PBP;
- unconstrained team-name fixed adjustments.

## Distribution

At minimum emit:

- expected home points;
- expected away points;
- expected margin;
- expected total.

Preferred implementation emits a joint predictive score distribution using residual/latent uncertainty. A Normal-only distribution is permitted as a baseline but cannot be the only distribution if Challenger B supplies discrete scoring structure.

## Complexity rule

Start with the smallest dynamic offense/defense specification, A0. Explicit state-space A1, passing/rushing sub-states, or nonlinear learners are **not automatic Phase 3 extensions**; any such expansion requires a preregistration amendment before its predictions are inspected.

---

# 3. Challenger B — Possession / Drive Score-Process Model

**Class:** football-only  
**Priority:** structurally distinct challenger

## Hypothesis

The current total model is too compressed because it predicts final total directly from team-form features. Explicitly modeling expected game volume and scoring efficiency may better distinguish low- and high-scoring environments.

## Core hierarchy

`expected possessions / drives`  
-> `team drive scoring distribution`  
-> `TD / FG / empty / turnover-like outcome probabilities`  
-> `home and away scoring distribution`  
-> `margin / total / win / cover / over probabilities`

## Bounded design

The first implementation may model:

- expected possessions or drives per team;
- probability of TD;
- probability of FG;
- probability of zero-point offensive outcome;
- optional safety/defensive-score tail only through a low-frequency residual component rather than a large classifier.

No play-by-play sequence simulator is authorized.

## Allowed football predictors

- lagged offensive/defensive EPA and success;
- lagged plays/drives/pace;
- red-zone opportunity and conversion measures if derivable from prior completed games;
- explosive-play rates;
- sack/turnover rates;
- opponent context only through B0's own training-fold team indicators and lagged offense/defense process states; **no A0 output enters B0**;
- home/rest context.

## Failure test

Challenger B must specifically be checked for:

- reduced low/high-total bias;
- broader but calibrated predictive variance;
- late-season robustness;
- no degradation masked by a small ATS subgroup.

If it adds complexity without improving scoring/distribution metrics, it fails.

---

# 4. Challenger C — Market-Residual Margin and Total Model

**Class:** market-aware  
**Priority:** mandatory benchmark challenger

## Hypothesis

Because the sportsbook market beats current LevLine on margin and total, LevLine may add more value by predicting **residual error around the market** than by independently reconstructing the entire line.

## Targets

Where exact paired market data exist:

`margin_residual = actual_home_margin - market_home_margin`

`total_residual = actual_total - market_total`

Prediction:

`LevLine_hybrid_margin = market_home_margin + predicted_margin_residual`

`LevLine_hybrid_total = market_total + predicted_total_residual`

## Initial model class

Use one simple, regularized and auditable reference:

- **Ridge regression** under the fixed alpha grid in `BOUNDED_IMPLEMENTATION_SPEC.md`.

No GAM, spline, ElasticNet or tree residual sensitivity is part of the initial Phase 3 candidate.

## Predictors

Football-only features available before the market horizon, such as:

- A0 dynamic team-strength deltas and A0 football-only forecast outputs;
- rest/home context;
- model-market discrepancy only if constructed from a truly football-only forecast;
- market level itself as the prespecified line-level calibration term.

## Market timing rule

Historical nflverse lines are a closing/late benchmark with opaque exact horizon. Results using those lines are labeled **historical closing-like residual research**.

No result from that family may be called T-120.

Prospective T-120 testing requires actual timestamped T-120 receipts.

## No adaptive-disagreement rule by default

Phase 1 showed larger current LevLine-market disagreement has worse continuous margin error. Therefore no rule that automatically trusts LevLine more as disagreement grows is authorized initially.

---

# 5. Conditional Challenger D — Ensemble / Joint Reconciliation

**Class:** conditional combination policy, not an initial standalone model

Challenger D becomes eligible only under the exact numeric development gate frozen in `EVALUATION_HOLDOUT_PROTOCOL.md`.

Any combination weights must be produced from **nested OOF predictions only**.

No full-block weight fitting is permitted, and no alternate stacker is tried if the gate fails.

If complementarity is weak, no ensemble is built.

---

# 6. Player / QB / personnel policy

Player modeling is **not** an initial required challenger.

A QB/personnel overlay may be added only when the historical or prospective input satisfies an explicit point-in-time contract.

## Allowed evidence

- lagged player performance with stable identity;
- pregame expected starter identity with timestamp <= decision time;
- qualified practice/depth state;
- replacement-quality estimate built only from information known before the game.

## Prohibited evidence

- actual starter inferred from final box score;
- final inactive list used at an earlier simulated horizon;
- current-game snaps;
- hindsight injury resolution;
- current roster projected backward.

## Historical selection rule

The 2025 availability composite may support a **2025 diagnostic or prespecified sensitivity**, but a one-season effect cannot select the core architecture.

No 2022–2025 unified player-state feature is permitted until the underlying source history is qualified.

---

# 7. Weather / travel / coaching policy

- rest remains allowed;
- richer travel/time-zone variables must be deterministic from schedule/venue and fixed before results;
- static roof can be studied if venue mapping is reliable;
- weather requires archived/prospective forecast state, never realized weather;
- coaching/scheme changes require timestamped roster/staff history and a preregistered representation.

These are extensions, not initial mandatory features.

---

# 8. Feature-selection policy

No broad automated feature search.

Every new feature family must have:

1. football mechanism;
2. PIT-safe source;
3. expected direction or structural role;
4. missingness behavior;
5. ablation plan.

Correlated variants of the same quantity are not all admitted merely because they exist.

---

# 9. Initial shortlist

| Candidate | Football-only? | Market-aware? | Initial Phase 3 status |
|---|---:|---:|---|
| A Dynamic opponent-adjusted joint score | yes | no | **IMPLEMENT** |
| B Possession/drive score process | yes | no | **IMPLEMENT** |
| C Market residual margin/total | no | yes | **IMPLEMENT** |
| D Nested ensemble | depends | depends | **CONDITIONAL ONLY** |
| QB/personnel overlay | can be | can be | **BLOCKED/CONDITIONAL ON PIT COVERAGE** |
| Weather extension | yes | no | **BLOCKED/CONDITIONAL ON PIT WEATHER** |

This is the deliberately limited Phase 2 challenger set.

## 10. Closeout authority

Where earlier wording in this file is more permissive than the final Phase 2 hardening, the following documents control:

1. \`BOUNDED_IMPLEMENTATION_SPEC.md\`;
2. \`EVALUATION_HOLDOUT_PROTOCOL.md\`;
3. \`MARKET_RESIDUAL_SPECIFICATION.md\`.

Those closeout restrictions were recorded before Phase 3 implementation/results and therefore narrow, rather than expand, researcher degrees of freedom.


## 11. Confirmatory holdout rule

A/B/C are the deliberately small preregistered set. All methodologically valid A/B/C candidate identities proceed to the one-time 2025 Phase 4 holdout even if their 2022–2024 development metrics are weak. Development may document failure, but it may not delete a valid preregistered family before the holdout.

A candidate can be invalidated only for PIT/source failure, specification violation, irreproducibility, irreparable numerical failure, or inability to emit the preregistered target. Poor MAE is not an invalidation category.

D remains the only development-gated component.
