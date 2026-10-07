# LevLine Post-Week-4 Model Improvement Plan

**Program:** LevLine post-Week-4 straight-up winner architecture research  
**Repository:** `levine26/nfl-forecast-model`  
**Scope of this chat:** Phase 1 (forensic diagnosis) and Phase 2 (external research + hypothesis synthesis) only  
**Production changes authorized:** NO  
**Production benchmark:** `F-ST-01-FROZEN-2026`  
**2026 outcome policy:** completed 2026 outcomes may generate/diagnose hypotheses but may not fit, tune, select thresholds, select hyperparameters, or rescue a candidate.

## 1. Current problem

LevLine's Weeks 3-4 straight-up performance materially under-ran its own locked probabilities while the independent margin/ATS signal remained competitive. The production winner stack is intentionally market-heavy and historically gained only a small number of additional winners through selective near-50/50 boundary corrections. The research question is therefore not whether to abandon the market, but whether LevLine can identify chronologically valid states in which independent football information should alter the market prior more strongly.

## 2. Known evidence carried forward

- Frozen historical F-ST reconstruction: 740/1087 (68.08%) vs market 735/1087 (67.62%).
- Chronology-clean F-ST architecture: 741/1087 (68.17%).
- Frozen F-ST/market disagreements were rare and concentrated near 50/50.
- Fixed PURE-heavy blends and unconditional PURE overrides lost historically.
- Component-resolved market + individual football logits reached 744/1087 (68.45%) season-forward, a promising but not established improvement.
- Football-component unanimity alone was not a valid upset-override rule.
- Weeks 3-4 2026 produced a statistically notable winner shortfall without evidence of production corruption.
- Margin/ATS performance did not collapse with straight-up accuracy.
- Existing LevLine 4 contracts already prioritize point-in-time market path, lineup/QB state, component structure, uncertainty-aware shrinkage, and prospective selective switching.

## 3. Research hypotheses

### H1 — Market prior is correct globally but misweighted conditionally
A single global market/PURE relationship may be too rigid. Market reliance may need to vary with decision-boundary distance, football-component consensus/dispersion, game-state uncertainty, market dispersion/path, and player-state information.

### H2 — Aggregate PURE is lossy
The nested PURE compression may discard useful interaction structure among logistic, Extra Trees, XGBoost, CatBoost, Elo, and margin signals. Component-level residual stacking or gating may outperform a single PURE probability.

### H3 — Margin contains underused winner information
Expected margin, margin uncertainty, and winner/margin disagreement may contain incremental binary winner information not fully represented in F-ST.

### H4 — Early-season state adaptation is imperfect
Rolling EPA/EWMA, prior-season carryover, opponent adjustment, preseason priors, QB/starter changes, coaching changes, and roster continuity may adapt at the wrong speed in Weeks 1-6.

### H5 — Market quality is heterogeneous
The market prior may improve through robust multi-book consensus, freshness, dispersion, path shape, stale-book detection, and moneyline/spread consistency.

### H6 — Discrete player/lineup state is underrepresented
Starting-QB probability, backup quality, OL continuity/injuries, pass-rush/secondary availability, role changes, and snap-share transitions may explain some residual errors if captured strictly point-in-time.

### H7 — Regime/structural breaks justify faster shrinkage or gating
New QB/coordinator/coach, major personnel turnover, and abrupt EPA changes may call for faster state transitions than the frozen feature representation supplies.

### H8 — Confidence is partly a decision-layer problem
Coin Flip/Solid labels may overstate actionability even when underlying probability ranking remains reasonable. Prediction, pick selection, and presentation confidence should be evaluated separately.

### H9 — 2026 feature/output drift may be material
Feature distributions, missingness, component disagreement, market probabilities, and output residuals may have shifted relative to the 2022-25 frozen universe.

## 4. Phase structure

### Phase 1 — Forensic diagnosis
Required outputs:
- F-ST vs market vs PURE/component errors.
- Probability/confidence slices.
- Decision-boundary and disagreement analysis.
- Early-season and market-confidence slices.
- Margin/winner relationship diagnostics.
- Team residual/error clustering (diagnostic only).
- 2026 feature/output drift audit using only features recoverable under the frozen/live contracts.
- Inventory of what cannot be reconstructed honestly (especially closing market and historical point-in-time lineup states).

### Phase 2 — External research and synthesis
Review:
- probabilistic forecast combination and stacking;
- Bayesian/market-prior residual learning;
- mixture-of-experts/gating;
- dynamic model averaging / online learning;
- regime-switching and structural-break models;
- bookmaker efficiency and line-path research;
- NFL-specific player/QB and EPA modeling;
- reproducible open-source NFL forecasting systems.

For each technique assess incremental information beyond market, data availability, chronology/leakage risk, effective sample size, expected overfit risk, implementation cost, interpretability, and realistic winner-accuracy upside.

### Phase 3 — Candidate architecture preregistration (next chat)
Freeze at least five meaningfully distinct candidates before testing them. No large-scale candidate implementation occurs in this chat.

### Phase 4 — Historical implementation
Research-only paths. No production mutation.

### Phase 5 — Walk-forward evaluation
Primary: paired straight-up winner accuracy. Secondary: Brier, log loss, calibration. Compare against F-ST, market, PURE, and relevant components.

### Phase 6 — Robustness
Season deletion, week-block uncertainty, disagreement-set tests, early-season slices, favorite-strength slices, market/PURE disagreement, component-consensus slices.

### Phase 7 — Prospective recommendation
Classify each candidate: REJECT / HISTORICALLY PROMISING / PROSPECTIVE SHADOW REQUIRED / READY FOR FINAL PROMOTION REVIEW.

## 5. Evaluation methodology

- Target historical OOS universe: 2022-2025 where compatible inputs exist.
- Prefer season-forward or rolling-origin evaluation.
- Identical-game paired comparisons.
- Zero-one winner accuracy is primary for this program.
- Brier/log loss/calibration are secondary diagnostics and safety checks.
- Dependence-aware uncertainty via week blocks; season sensitivity mandatory.
- Candidate architecture, features, thresholds, and hyperparameter policy frozen before candidate result inspection.
- No 2026 completed outcome may select a candidate identity or threshold.

## 6. Leakage firewall

Forbidden:
- post-kickoff information;
- closing snapshots reconstructed from later data;
- retrospective injury/inactive labels presented as point-in-time;
- 2026 outcome-derived thresholds, weights, feature subsets, or hyperparameters;
- team-specific patches based on recent misses;
- arbitrary PURE-weight grids selected by best retrospective hit rate.

Required:
- timestamped point-in-time state;
- chronology-clean feature construction;
- immutable candidate IDs;
- recorded failures;
- paired-game evaluation.

## 7. Stopping rules

- Reject an architecture if gains are one-season dependent, arise from threshold fishing, or are contradicted by paired disagreement performance.
- Do not promote a model because it wins one recent slice.
- Small sustainable gains (roughly 0.5-1.0 pp) are meaningful only if season-stable and leakage-free.
- If evidence cannot distinguish candidate from incumbent, preserve F-ST and move to prospective shadow testing.

## 8. Artifacts to produce in Phases 1-2

- This plan, updated with findings and handoff.
- Forensic diagnosis summary and quantitative tables.
- External-research evidence ledger with sources and applicability.
- Ranked mechanism/hypothesis table.
- Ranked Phase 3 candidate slate with expected upside and failure modes.
- Explicit rejected ideas and unresolved data requirements.

## 9. Decision criteria for Phase 3 entry

A candidate family proceeds only if:
1. it has a concrete mechanism for information incremental to the market;
2. its required inputs exist historically or are explicitly prospective-only;
3. chronology can be enforced;
4. sample size is plausibly adequate for the model complexity;
5. it is meaningfully distinct from already rejected fixed-weight/PURE-override ideas;
6. its architecture can be frozen before outcome evaluation.

## 10. Production firewall

No change in this program to F-ST production scoring, Sunday Signal winner logic, official historical locks, grading semantics, public outputs, or production market weighting without explicit final authorization.


## 11. Phase 1–2 completion update — 2026-10-06

Phases 1–2 are complete for this research chat.

Authoritative detailed findings:
- `research/LEVLINE_POST_WEEK4_PHASE1_2_FINDINGS.md`

### Decisions recorded

- Preserve F-ST as the production benchmark.
- Reject any global increase in PURE weight as the default next move.
- Treat the market as prior/default; search for sparse residual football information.
- Prioritize component-residual, margin-derived winner, and explicit early-season-state candidates for immediate historical testing.
- Treat robust market-quality and player/QB event models as high-value but PIT-data-limited.
- Keep confidence/actionability separate from official pick identity.
- Do not use high-capacity neural gating on the current OOS sample.

### Newly identified architectural issue

The current football feature builder carries rolling/EWMA state continuously across seasons and does not consume the declared `features.*` configuration controls. This is not a production-corruption finding and authorizes no immediate change. It creates a specific research hypothesis: an explicit season-boundary shrinkage/state-transition model may improve early-season football estimates.

### Drift finding

Output-level 2026 distributions show only modest movement relative to 2022–2025; no broad regime break is established. Full raw-feature drift remains unresolved because a directly comparable historical frozen/live feature matrix is not currently persisted.

### Next-chat Phase 3 order

1. preregister `MKT-COMP-RESIDUAL-V1`;
2. preregister `MARGIN-RESIDUAL-WIN-V1`;
3. preregister `EARLY-STATE-SHRINKAGE-V1`;
4. build common walk-forward evaluation infrastructure;
5. execute A/B/C without 2026 selection/tuning;
6. only then preregister the constrained conditional gate so it cannot choose its base expert post-result;
7. keep market-quality/player-state candidates prospective where PIT history is insufficient.

No production promotion is authorized.


## Phase 1–2 completion status — 2026-10-06

**Phases 1–2 are complete. Do not repeat them in the Phase 3 continuation.**

Authoritative findings:
- `research/LEVLINE_POST_WEEK4_PHASE1_2_FINDINGS.md`

### Findings carried into Phase 3

1. **No global PURE reweighting.** PURE loses market disagreements historically and fixed PURE-heavy blends are rejected.
2. **Use market-offset residual parameterization.** The frozen negative PURE coefficient is coherent as a conditional suppressor in a highly collinear market/PURE system; do not force a positive football weight.
3. **Preserve component structure, but do not vote.** Component resolution has some boundary information; unanimity and majority-based upset rules are rejected.
4. **Do not use a calendar-only early-season rule.** Early-season performance is unstable by season.
5. **Explicit offseason state is a real architecture question.** The live rolling/EWMA path groups by team across seasons; fixed defaults are used and feature-config controls are not wired into the live builder. This is not a leakage/production defect, but it motivates a research-only hierarchical season-boundary shrinkage candidate.
6. **Raw margin-gap override is rejected.** A distinct margin-derived winner-probability residual remains eligible because the prior failed bridge tested probability-to-margin, not margin-to-win.
7. **Generic dynamic Elo, naive weekly refitting, and path-only market innovation are rejected/inconclusive.**
8. **No broad persisted-output regime break is evident in 2026.** Raw-feature drift remains unresolved because an immutable historical/live feature snapshot is not yet persisted.
9. **Confidence/actionability is separate from pick identity.** Presentation abstention cannot silently alter official winner grading.
10. **2026 populations must remain contract-specific.** Do not mix the formal 63-lock Week-4 audit population with the current 64-row persisted history or other diagnostic subsets.

### Phase 3 preregistration order

Freeze candidate identities before target-season results are inspected:

1. `MKT-COMP-RESIDUAL-V1`
2. `MARGIN-RESIDUAL-WIN-V1`
3. `EARLY-STATE-SHRINKAGE-V1`
4. Design `CONSTRAINED-GATE-V1` only after 1–3 are frozen.
5. Keep `MARKET-QUALITY-PRIOR-V1` and `PLAYER-STATE-EVENT-V1` as separate PIT/prospective lanes if compatible historical coverage is insufficient.

### Required common evaluation

- exact paired 2022–2025 games;
- season-forward / rolling-origin construction;
- winner accuracy primary;
- Brier, log loss and calibration as guardrails;
- switch count, challenger-only correct, incumbent-only correct, switch win rate;
- by-season and early-season slices;
- market-confidence and component-topology slices;
- week-block uncertainty;
- leave-one-season-out sensitivity;
- no completed 2026 outcome in fitting, model selection, thresholding or hyperparameter choice.

### Phase 3 stopping rule

If A/B/C do not produce season-stable paired improvement, do **not** rescue them with 2026-driven thresholds or combine them post hoc. Record the failure. F-ST remains the production incumbent unless a separately frozen candidate earns promotion and the user gives explicit final authorization.

## 12. Alexandria PIT feasibility addendum — 2026-10-07

**Separate workstream, not a Phase 3 candidate and not new Phase 1–2 modeling.** A connected Firecrawl Alexandria catalogue audit identified StartWho weekly sportsbook-backed player projections and NFL.com official injury/practice reports as *potential* future player-state and market-quality inputs.

Authoritative scope/evidence/gating ledger: [LEVLINE_ALEXANDRIA_PIT_FEASIBILITY_2026_10_07.md](LEVLINE_ALEXANDRIA_PIT_FEASIBILITY_2026_10_07.md).

- Catalogue identifies four relevant 5-credit-per-call tools; only the small StartWho Week-5 payload was successfully smoke-tested; an NFL injury live call was rate-limited. No historical PIT qualification exists.
- `observed_at_ms` is a fetch clock; StartWho `last_updated` and NFL `report_date` do not prove a specific sportsbook quote or final injury designation was available at the earlier historical cutoff. Do not reconstruct old PIT states from today's historical-week result.
- Alexandria is **prospective feasibility only**. The snapshot schema and low-rate ingestion strategy are design artifacts, not active collectors. Retention/license/quote timestamp/history coverage remain unresolved.
- Preserve the existing Phase 3 2022–2025 paired evaluation contract and candidate order. **No modification to Candidate A's frozen identity, features, architecture, training or evaluation. No automatic Alexandria inclusion in Candidates B/C; independent prior preregistration + historical coverage required.**
- One experimental candidate per chat, Candidate A first; separately scoped research-only GitHub PR for this Alexandria ledger; production F-ST/Sunday Signal untouched.

## 13. Phase 3 A/B/C results — 2026-10-07

**Historical model work complete, no production change.** Preregistration was frozen before evaluation in [PR #627](https://github.com/levine26/nfl-forecast-model/pull/627). The separate research-only implementation/evidence is [PR #628](https://github.com/levine26/nfl-forecast-model/pull/628). Full report: [post_week4_phase3/EVALUATION_REPORT.md](post_week4_phase3/EVALUATION_REPORT.md), with exact 1,087-game OOF CSVs, manifest SHA256s, and result JSON under `research/post_week4_phase3/evidence/`.

- Incumbent chronology-clean F-ST: **741/1087** (68.17%).
- **A `MKT-COMP-RESIDUAL-V1`: REJECT**, **730/1087** (−11 vs F-ST); lost in all four seasons.
- **B `MARGIN-RESIDUAL-WIN-V1`: REJECT**, **737/1087** (−4); slightly better probability scores but fewer correctly picked winners.
- **C `EARLY-STATE-SHRINKAGE-V1`: INCONCLUSIVE**, **749/1087** (+8; 68.91%); gains +6/+3 in 2022/2024, −1 in 2023, 0 in 2025; season-week 95% interval includes zero, proper scoring worse, and only +2 of the gain comes in Weeks 1–6. **No promotion.**

All candidate fits and shrinkage policy were frozen before looking at the 2022–2025 candidate results; completed 2026 outcomes never trained/tuned them. The historical football feature rebuild matched all 1,615 frozen 2020–2025 training-game IDs/targets. Candidate C excludes unqualified retrospective starter states, and its historical evidence remains insufficient for production. An earlier early-season F-ST slice count in Phase 1–2 differs from this exact-key reconstruction; do not make a new early-week gating claim until reconciled.

**Next:** preserve frozen F-ST/Sunday Signal. A/B cannot be retuned under the same identifiers to chase this outcome. If desired, formulate a wholly separate **prospective** research-only C shadow protocol with immutable pre-kickoff snapshots, independent source/timestamp auditing and decision thresholds frozen before results; no automatic gate or combined model. Alexandria remains its own PIT feasibility lane, outside A/B/C. Any production promotion still requires the user's explicit final authorization.

## 14. Phase 3 binary-tie-label qualification — 2026-10-07

A/B/C legacy historical results are retained unmodified at **741/1087 F-ST**, A **730**, B **737**, C **749** (A REJECT, B REJECT, C INCONCLUSIVE). The paired legacy panel includes three 2022–2025 regular-season ties encoded as `home_win=0`/away wins. This is an *estimand limitation* versus the existing strict tie-exclusion governance contract. [Read the audit](post_week4_phase3/TIE_LABEL_CONTRACT_AUDIT.md) before comparing model accuracy. Static exclusion of the three tied rows retains the pairwise winner differences, but **does not repair training labels or qualify a new OOS result**. Any strict-tie refit needs its own prior protocol. Preserve production F-ST and Sunday Signal unchanged. Candidate C remains research-only and inconclusive; no post-hoc rescues.

## 15. Phase 4 prospective Candidate C preparation — 2026-10-07

**Three parallel research-only tracks:**

- [Phase 4 preregistration](post_week4_phase4/C_PROSPECTIVE_PREREG_2026_10_07.md) (PR #629): immutable Candidate C prospective architecture, same-horizon official locked F-ST comparison, primary paired winner accuracy, 200 non-tie games/14 weeks earliest formal review, week-block inference; no retrospective retuning or automatic production promotion.
- [Baseline/tie audit](post_week4_phase4/BASELINE_AUDIT.md) (PR #630): independent exact-game reproduction shows season-forward F-ST 741/1087, Weeks 1–4 167/256, Weeks 1–6 243/372; frozen-final-coefficient F-ST 740/1087, 164/256, 241/372. Three 2022–2025 ties improperly labeled as away wins in the legacy panel. Distinct comparator methods explain the previous early-week count discrepancy. Tie-exclusion without a full historical refit remains descriptive only.
- [Research-only Candidate C shadow preflight](post_week4_phase4/SHADOW_READINESS.md) (PR #631): isolated offline strict-PIT snapshot scorer, outcome-only paired evaluator, immutable research evidence and fixed 2020–2025 trained Candidate C coefficients saved in `post_week4_phase4/artifacts/C_SHADOW_FROZEN_2026.json`. One-time fit passed, **no 2026 outcomes** fitted. Synthetic gateway/unit tests passed, but there is **no independent official-lock-aligned live source adapter or verified prospective eligible capture yet**.

**Completion boundary:** C model/scorer preflight is `INFRASTRUCTURE_READY / AWAITING_ELIGIBLE_LOCKS`, **not** Phase 4 prospective validation complete. No automation to scrape, refit or publish unverified 2026 records. Prospective statistical claims require strictly pre-lock captured, source-validated game snapshots, then >=200 non-tie games and >=14 weeks, paired week-block inference, probability checks, and final user approval. Until that independent data accumulates, F-ST and Sunday Signal remain unchanged. Alexandria remains separate and source/license-limited; A/B rejected, C still inconclusive.
