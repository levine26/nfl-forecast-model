# LEVLINE ATS FRONTIER V2 — MASTER PLAN

**Program:** `LEVLINE_ATS_FRONTIER_V2`  
**Opening main:** `7a37253d5dd392e68e7c3e0168e8a05e89b15029`  
**Production:** `F-ST-01-FROZEN-2026` — immutable during this program unless the user later gives the explicit Phase-7 promotion authorization.  
**Current phase:** Phase 1 — Massive Deep Research, Mechanism Discovery & Program Design.

## Governing question

The program is not a search for a more fashionable learner. It asks:

> What information, representation, timing advantage, market feature, player-state signal, uncertainty structure, or probabilistic architecture has a credible pathway to add predictive information after conditioning on an already highly efficient NFL sportsbook market?

The operative scientific object is `I(new_signal ; outcome | market_state)`. Any candidate that merely predicts football outcomes but cannot plausibly remain informative conditional on a contemporaneous market null is out of scope.

## Fixed prior evidence

ATS V1 is terminal historical evidence: Q1 and Q3 failed their preregistered incremental market comparisons; Q2 failed closed because its frozen finite support produced material endpoint mass before a valid performance evaluation. Spread & Points Next Generation produced no standalone historical finalist; A0/B0 lost materially to the market, C0 did not establish incremental football information, and Candidate 5 historical residual stacking changed zero F-ST winners. Adaptive candidates demonstrated the danger of tiny, event-concentrated improvements: Candidate 2 changed one 2025 winner; Candidate 3's +1 winner was reproduced by market level alone and did not establish independent path information.

These results rule out rescue-by-renaming. They do not rule out new information channels, genuinely dynamic market state, point-in-time player-state reconstruction, or a numerically valid new discrete distribution experiment.

## Phase-1 survivor mechanisms

1. `FRONTIER-M1-DYNAMIC-MARKET-STATE` — infer a latent fair spread / cover state from timestamped multi-book spread, side price, moneyline and total paths, including disagreement, breadth, velocity, key-number stickiness and lead/lag structure.
2. `FRONTIER-M2-PLAYER-STATE-DELTA` — model expected lineup value as player ability × participation probability × expected role, net of replacement quality, then test the change in that quantity relative to contemporaneous market-implied change; QB is a separately modeled high-value/uncertainty component.
3. `FRONTIER-M3-HIERARCHICAL-STATE` — replace fixed rolling summaries with sample-efficient hierarchical latent offense/defense/QB/unit states with process noise, partial pooling and explicit regime/changepoint capacity; any claim must be incremental to market state.
4. `FRONTIER-M4-DISCRETE-MARGIN-V2` — a tail-safe, integer-aware conditional margin representation with adaptive/unbounded support, whole-number push mass and conditionally varying key-number mass. This is a representation candidate, not an assumed information edge; it advances only if it improves proper scores against a strong market distribution null or makes an information-bearing M1–M3 signal usable.

Forecast combination is reserved as a downstream operation only if independently validated survivors show complementary residual information. It is not a Phase-1 candidate by itself.

## Roadmap

### Phase 1 — Deep research & mechanism discovery
Research only. Build evidence ledger, failure atlas, data matrices, candidate cards and shortlist. No new candidate fitting or historical target inspection.

### Phase 2 — Data qualification & PIT reconstruction
Prove the required market/player/team data can be reconstructed as-of prediction time. Build timestamped reusable research tables. Eliminate infeasible candidates. Still no candidate target-performance inspection.

### Phase 3 — Final architecture & preregistration
Freeze surviving candidate IDs, features, model family, hyperparameter grids, market nulls, chronology, metrics, uncertainty procedure, thresholds/selectivity and stopping rules before target results exist.

### Phase 4 — Historical development & ablation
Implement only frozen candidates; run chronology-clean OOF development, proper scores, calibration, market-relative tests, ATS diagnostics, ablations, robustness, uncertainty and leakage checks. No rescue.

### Phase 5 — Scientific synthesis & survivor freeze
Classify each candidate `REJECTED`, `INCONCLUSIVE`, or `ELIGIBLE_FOR_PROSPECTIVE_SHADOW`. No refitting or redesign. Stop if none survive.

### Phase 6 — Prospective shadow validation
Future games only, immutable pregame predictions. Evaluate proper scores, calibration, market-relative value, ATS, CLV and actual-price EV when prices are captured. No retrospective tuning.

### Phase 7 — Final synthesis & human promotion gate
Compare eligible candidate(s), market, F-ST and production evidence. No automatic production promotion. The user must explicitly authorize any production change.

## Non-negotiable firewalls

- Completed 2026 outcomes are sealed from candidate selection, feature/data selection based on outcomes, priors, distributions, architecture, calibration and thresholds.
- No candidate training, OOF generation, ATS hit-rate search, ROI search or threshold fishing in Phase 1.
- Historical schedule spread fields whose exact horizon is opaque remain `historical_closing_late_benchmark_exact_horizon_opaque` and may not be relabeled T-120/T-60/etc.
- Ex-post snap counts, realized starters, final inactives, corrected depth charts and realized weather cannot masquerade as pregame inputs.
- All incremental claims require a contemporaneous market null on identical chronology-clean rows.
- Production surfaces are protected; research is additive under `research/ats-frontier-v2/` plus research-only validation tests.

## Future-chat read order

Every future chat must read, in order: `MASTER_PLAN.md`, `PHASE_STATUS.md`, `CURRENT_STATE_AND_NEXT_STEPS.md`, `DECISION_LOG.md`, the previous phase final receipt, and the relevant data/scientific contract. Completed phases are not restarted.