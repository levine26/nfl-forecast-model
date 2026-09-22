# Phase 2 Synthesis — Deep External Research & Challenger Design

**Status:** **COMPLETE** — red-team hardened, exact-head validated, merged, and verified from `main`  
**Production change:** none  
**Primary branch:** `research/spread-points-nextgen-phase2`  
**PR:** #520 — **MERGED** at `405906942013252c158244c9b033a3240baa37f8`

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
- B0 lagged process summaries use fixed 8-team-game EWMAs; A0 retains only its preregistered observation half-life grid `[4,8,16,32]`; C0 has no independent rolling-window search;
- outer development targets are exactly 2022, 2023 and 2024;
- inner folds are deterministic expanding prior-time folds using the latest four valid validation seasons, with fixed fallbacks when fewer than two valid folds exist;
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

Process-feature evidence is deliberately weaker and narrower: peer-reviewed turnover research supports treating turnovers as rare but conditionally predictable events while also emphasizing noise/regression concerns; red-zone finishing and explosive-play evidence is primarily technical/practitioner and supports only bounded, shrinkage-aware B0 components rather than independent challenger families or threshold searches.

**davidsasser.com**, included explicitly at the user's request, is useful as a product architecture comparator because the public board clearly separates projected team scores, model projected line, market opening/current line and selection. A final targeted site/web/GitHub search found no reproducible current model specification, source repository, immutable PIT forecast archive or independent validation protocol. Its current record therefore remains product-level/opaque evidence, not scientific validation.

The final evidence hierarchy is explicit: peer-reviewed work supports general statistical/football methodology; reproducible open-source systems support implementation ideas; practitioner systems do not become peer-reviewed evidence; and opaque performance claims are not imported into LevLine validation. Brill et al. (2024) remains classified as a strong technical preprint rather than peer-reviewed literature.

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

A0 is the only initial A implementation. Explicit state-space A1, pass/rush substates, nonlinear expansion and advanced-charting variants are deferred behind a new preregistration.

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

Reference learner is Ridge-only under the frozen alpha grid.

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

1. implement shared chronology/data/evaluation scaffolding using the frozen 2016 training floor, 2019+ inner validation targets and deterministic nested folds;
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

Phase 2 exit criteria are **SATISFIED**. Final synchronized head `076dc9d6f6c052eec4744a155070c42c1b99ae82` passed research firewall `35751402751` and full research validation `35751402726`; PR #520 merged at `405906942013252c158244c9b033a3240baa37f8`; every canonical Phase 2 artifact and control file was re-read from `main` after merge. Production remained unchanged, no 2025 challenger result was inspected, and completed 2026 outcomes were not used for selection.

Phase 3 remains **NOT STARTED**. **STOP Phase 2.**

## Red-team closeout findings

The final Phase 2 hostile review attempted to invalidate the shortlist and produced the following conclusions.

### A and B are sufficiently distinct — after hardening

A forecasts team scoring from dynamic, partially pooled offense/defense strength.

B forecasts scoring through **possession count plus discrete drive outcomes**. To prevent hidden convergence, B0 is required to run without A0 predictions. No B+A sensitivity is part of the initial Phase 3 search.

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

## Final pre-result chronology and D gate

The closeout contract is fully deterministic:

- reference training begins in **2016**;
- inner validation targets begin in **2019** and use expanding prior-only history;
- outer development targets are exactly **2022, 2023, 2024**;
- A0 retains only the bounded half-life grid `[4,8,16,32]`;
- B0 process states use fixed **8-team-game** EWMAs and remain independent of A0;
- C0 is Ridge-only on frozen A0 plus the fixed M0/M1/M2/M3 market-null hierarchy;
- every methodologically valid A0/B0/C0 reference receives the one-time Phase 4 2025 evaluation;
- D is built for a target only if residual correlation is <0.90, pooled MAE improves by >=0.10 points, both 2023 and 2024 improve, and paired block-bootstrap P(improvement) is >=0.75.

No Phase 3 challenger result existed when these constraints were frozen.


---

## Final completion receipt

- final synchronized pre-merge main: `e93127963c76cd309cdddf17d91291c04a60a659`
- final validated Phase 2 head: `076dc9d6f6c052eec4744a155070c42c1b99ae82`
- compatibility sync PR #541: merged into the Phase 2 branch; adaptive Candidate 2 state preserved but not used as challenger evidence
- exact-head research firewall `35751402751`: **SUCCESS**
- exact-head full research validation `35751402726`: **SUCCESS**
- primary PR #520: **MERGED**
- primary merge commit: `405906942013252c158244c9b033a3240baa37f8`
- merged canonical artifacts verified directly from `main`: **YES**
- production change: **NONE**
- paid-data dependency: **NONE**
- 2025 challenger inspection during Phase 2: **NONE**
- completed-2026 selection contamination: **NONE**
- Phase 3 implementation: **NOT STARTED**

### DO NOT REPEAT

Do not rerun Phase 1; do not redo the Phase 2 literature/external-model review; do not broaden the frozen A0/B0/C0 search after observing results; do not inspect 2025 challenger outcomes in Phase 3; do not use completed 2026 outcomes for candidate selection; do not relabel closing/late historical market data as T-120; do not use hindsight starter/injury/weather state; do not force D or player features; do not add paid data without escalation; do not revive retired Props orchestration; and do not weaken F-ST production safeguards.
