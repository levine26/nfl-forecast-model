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
