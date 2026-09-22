# Phase 2 Synthesis — Deep External Research & Challenger Design

**Status:** analytically complete after red-team hardening; pending current-main synchronization and exact-head CI/firewall verification  
**Production change:** none  
**Primary branch:** `research/spread-points-nextgen-phase2`  
**Draft PR:** #520

## What Phase 2 answered

Phase 2 translated the Phase 1 residual audit into a deliberately limited research program rather than a large feature/model search.

The external evidence supports three ideas strongly enough to implement:

1. dynamic, partially pooled offense/defense strength;
2. explicit possession / scoring-process decomposition;
3. market-residual prediction around a strong sportsbook prior.

Everything else is conditional.

## Red-team hardening result

The hostile methodology review did **not** invalidate A/B/C, but it did identify excess discretion in the earlier implementation wording.

Phase 2 therefore tightened the design before any Phase 3 result exists:

- initial implementation is **A0 + B0 + C0 only**;
- explicit state-space A1 and nonlinear residual C1 are deferred rather than activated from qualitative development diagnostics;
- lagged process summaries use a fixed 8-team-game EWMA;
- training begins at 2016;
- outer development targets are exactly 2022, 2023 and 2024;
- inner tuning targets begin in 2019 and are strictly prior-time;
- candidate-specific tuning objectives and tie-breaks are frozen;
- A0/B0/C0 reference identities receive one Phase 4 2025 score if implementation/PIT-valid even when development is negative;
- D has an explicit numeric eligibility gate and is not forced.

This reduces researcher degrees of freedom and prevents Phase 3 from becoming a rescue search.

---

## Evidence synthesis

### Strongest peer-reviewed statistical foundation

**Glickman & Stern (1998)** directly model NFL scores with time-varying team strength in a state-space model. This is the strongest statistical precedent for replacing LevLine's duplicated rolling windows with a coherent dynamic team-strength process.

**Harville (1977, 1980)** shows that simple linear/mixed team-strength models remain competitive forecasting baselines. This supports Phase 1's empirical finding that the current ElasticNet can beat the current equal-ish four-model regression blend.

### Strongest NFL exact-score precedent

**Baker & McHale (2013)** build an exact NFL score point-process model, evaluate genuine OOS forecasts, and explicitly account for the unusual scoring distribution produced by touchdowns and field goals. This strongly supports a bounded discrete scoring-process challenger rather than another continuous direct-total regression.

### Strongest market lesson

Peer-reviewed NFL forecasting/market work repeatedly finds the betting market difficult to beat and often superior to objective ratings.

That external evidence agrees with Phase 1's modern internal result:

- market spread MAE 9.494 vs current LevLine margin 9.962;
- market total MAE 10.189 vs current LevLine total 10.854.

Therefore market residualization is a core scientific challenger, not a betting afterthought.

### Proper forecasting methodology

Gneiting & Raftery's proper-scoring framework and rolling-origin forecast-evaluation literature reinforce two Phase 2 rules:

- evaluate full predictive distributions honestly;
- every tuning/stacking decision must be nested inside earlier-time data.

### Public/open-source evidence

**nfelo** is the strongest transparent public model comparator reviewed. Its useful transferable ideas are:

- raw football model separate from market regression;
- dynamic rating;
- opponent / efficiency information;
- QB/context adjustments;
- explicit recognition that market-aware optimization can collapse toward the market.

LevLine does not copy nfelo's parameters, ATS objectives or current nonlinear market-regression rule.

**Open Source Football / nflverse** supports opponent-adjusted EPA and multilevel shrinkage using the same free ecosystem already available to LevLine.

**davidsasser.com**, included explicitly at the user's request, is useful as a product architecture comparator because the public board clearly separates projected team scores, model projected line, market opening/current line and selection. The public material inspected does not disclose enough methodology, data chronology or frozen historical forecasts to treat its record as reproducible validation evidence.

---

# Frozen Phase 3 shortlist

## Challenger A — Dynamic Opponent-Adjusted Joint Score

**Football-only.**

Purpose:

- reduce stale/duplicated rolling-form behavior;
- model offense and defense separately;
- regularize small samples;
- adjust for opponent quality;
- generate coherent home/away score expectations.

Start simple. Nonlinear expansion, pass/rush substates and advanced charting are ablations, not defaults.

## Challenger B — Possession / Drive Score Process

**Football-only and structurally distinct.**

Purpose:

- attack total regression-to-the-middle;
- explicitly model scoring opportunity volume and drive efficiency;
- preserve discrete 3/7-style scoring structure;
- emit a coherent score distribution.

The first build is bounded to expected possessions/drives plus TD/FG/empty-like outcomes. No full play-sequence simulator.

## Challenger C — Market Residual Margin / Total

**Market-aware.**

Purpose:

- test whether football information adds incremental information beyond the market;
- predict actual-minus-market residual rather than reconstruct the entire line.

Reference learner is regularized and simple.

Historical nflverse market results remain closing/late benchmark research, never T-120.

## Challenger D — conditional ensemble

No ensemble is guaranteed.

It becomes eligible only if A/B/C produce genuinely complementary OOS residuals. Combination weights must use nested OOF predictions.

---

# Player / personnel decision

QB/personnel is scientifically plausible but **not forced into the initial three challengers**.

Why:

- Phase 1 one-season 2025 availability effects are suggestive but uncertain;
- final historical starter identity is not automatically decision-time safe;
- 2022–2025 does not yet have one qualified fixed-horizon starter/injury history;
- market prices may already contain much of the player information.

The player layer is therefore:

- a conditional historical sensitivity when PIT-safe;
- or a prospective shadow layer.

It cannot rescue a failing core architecture with hindsight state.

---

# Weather / travel decision

Rest/home context remains.

Weather is blocked from initial historical challenger selection until exact venue and forecast-as-of state are qualified. Realized temperature/wind will never substitute for a pregame forecast.

---

# Paid-data decision

**No paid dependency is requested.**

The initial three challengers are fully testable under the $0 policy.

Paid player/injury/charting data is reconsidered only if a later residual failure points to a specific unique field and a bounded incremental-value test can justify the cost.

---

# Frozen evaluation design

## Final historical challenger holdout

**2025** is frozen for final historical challenger evaluation.

Caveat: Phase 1 already inspected baseline 2025 errors, so it is not philosophically pristine. But after this Phase 2 freeze:

- no Challenger A/B/C 2025 metrics may be inspected in Phase 3;
- no parameter may be selected from 2025 challenger performance;
- final candidate identities are frozen before Phase 4 scores 2025.

## Development

Use rolling-origin outer evaluation through 2024 with every tuning decision nested inside prior-time data.

## 2026

Completed 2026 outcomes remain entirely unavailable for:

- architecture;
- features;
- hyperparameters;
- thresholds;
- stacking;
- model selection.

2026 remains forward/prospective evidence only.

## Primary metrics

- home/away points MAE and RMSE;
- margin MAE/RMSE;
- total MAE/RMSE;
- signed bias;
- residual dispersion.

For predictive distributions:

- coverage + interval width;
- CRPS where feasible;
- proper log/energy scores where the candidate distribution supports them.

ATS/O-U remains secondary and cannot select a model.

---

# Phase 3 implementation order

To avoid branch/model sprawl:

1. implement shared chronology/data/evaluation scaffolding using the frozen 2016 training floor and deterministic nested folds;
2. implement **A0** only;
3. implement **B0** only;
4. implement **C0** only, including the four mandatory market-null comparisons;
5. run only 2022–2024 development OOS evaluation;
6. freeze A0/B0/C0 candidate identities and preserve negative outputs;
7. evaluate D eligibility using the exact numeric development gate; build it only if every gate is satisfied;
8. do not score any 2025 challenger output until Phase 4;
9. leave A1/C1/player/weather extensions unimplemented absent a new pre-result preregistration.

---

# Phase 2 exit-criteria mapping

| Exit criterion | Evidence |
|---|---|
| literature review | `phase2/LITERATURE_REVIEW.md` |
| external-model review | `phase2/EXTERNAL_MODEL_REVIEW.md` |
| candidate architectures | `phase2/CHALLENGER_PREREGISTRATION.md` |
| feature hypotheses | `phase2/FEATURE_HYPOTHESES_AND_PLAYER_POLICY.md` |
| player-model policy | same feature/player policy |
| market-residual specification | `phase2/MARKET_RESIDUAL_SPECIFICATION.md` |
| preregistered evaluation | `phase2/EVALUATION_HOLDOUT_PROTOCOL.md` |
| frozen holdout | same protocol; 2025 |
| data-gap report | `phase2/DATA_GAPS_AND_SOURCE_POLICY.md` |
| paid-data decision | `phase2/PAID_DATA_DECISION.md` |
| deliberately limited shortlist | A/B/C; D conditional |
| davidsasser.com included | external review + literature/external inventory |

Before Phase 2 can be marked **COMPLETE**, the branch must first be synchronized to the then-current `main`, fresh exact-head firewall and full research-validation checks must pass, PR #520 must be reviewable and merged, merged artifacts must be re-read from `main`, and the control files must record the exact Phase 3 start state.

Phase 3 remains **NOT STARTED** in this chat.

## Red-team closeout findings

The final Phase 2 hostile review attempted to invalidate the shortlist and produced the following conclusions.

### A and B are sufficiently distinct — after hardening

A forecasts team scoring from dynamic, partially pooled offense/defense strength.

B forecasts scoring through **possession count plus discrete drive outcomes**. To prevent hidden convergence, the independent B0 reference is now required to run without A0 predictions. Only one labeled OOF A-state sensitivity is permitted afterward.

### A is not allowed to become an open-ended state-space search

A0 is the initial A identity. Explicit A1 state-space variants are deferred behind a new preregistration amendment. This avoids using a weak A0 result as permission to search transition equations.

### B is identifiable with current free data

nflverse PBP provides enough historical game/drive structure to construct the bounded drive process, subject to drive-taxonomy QA. B does not require proprietary tracking data or a play-sequence simulator.

### C may simply learn zero — and that is acceptable

Residual sportsbook error is noisy and plausibly close to unpredictable. C therefore retains the exact market-only null and now has a fixed M0/M1/M2/M3 hierarchy separating market calibration from football information. C0 is Ridge-only.

### Development sample size argues for less complexity, not more

The mandatory modern OOS target seasons are only 2022–2024 before the 2025 holdout. That sample does not justify a large learner/feature tournament. The closeout specification removes the ElasticNet bake-off, tree fallback, automatic A1 search, and B estimator bake-off.

### 2025 remains a transparent imperfect holdout

Phase 1 inspected baseline 2025 failures, so 2025 is not philosophically pristine. No A/B/C output existed at that time. Phase 2 found no superior historical alternative that would both remain recent and avoid prior architecture exposure. The protection is therefore candidate freeze now, zero Phase 3 2025 challenger inspection, one Phase 4 opening, and required Phase 5 prospective evidence.

### Player/weather deferral is methodological, not convenience

The reason QB/personnel/weather are conditional is source chronology: the repository lacks a uniform 2022–2025 fixed-horizon starter/availability history and qualified historical forecast-weather archive. Hindsight states are not permitted to rescue a challenger.

### Final shortlist

No challenger is removed.

- **A — IMPLEMENT reference only**
- **B — IMPLEMENT independent bounded reference**
- **C — IMPLEMENT Ridge residual reference with mandatory market nulls**
- **D — CONDITIONAL; do not force**

The shortlist remains three initial challengers because they answer genuinely different scientific questions with data that can be constructed under legal chronology.
