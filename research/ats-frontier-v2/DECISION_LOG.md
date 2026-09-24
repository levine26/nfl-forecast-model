# DECISION LOG

## D001 — Research-first reset
**Decision:** Do not create Candidate 4/5/6/Q4 merely because prior candidates failed. Require a mechanism with plausible incremental information conditional on market state.  
**Reason:** A0/B0/C0/Candidate5/Q1/Q3 and adaptive evidence show repeated failure of generic football-state/residual augmentation.

## D002 — Completed 2026 sealed
**Decision:** Completed 2026 outcomes are unavailable to Phase-1 design.  
**Reason:** Preserve prospective validity and prevent outcome-driven architecture selection.

## D003 — Market is a dynamic state, not one number
**Decision:** Advance dynamic multi-book market state to the shortlist.  
**Evidence:** Betting-market literature repeatedly finds information content increasing from earlier to later lines; line/price movement may encode informed activity. LevLine's historical schedule spread has opaque exact horizon and discards book dispersion, side price and path structure.

## D004 — Static market-path rules are insufficient
**Decision:** M1 must explicitly test information beyond contemporaneous market level.  
**Reason:** Adaptive Candidate 3's 2025 +1 winner was duplicated by a level-only market update; path independence was not established.

## D005 — Player state must be an information delta
**Decision:** Advance player/QB state only in the form `change in expected lineup value - market-implied change`, not injury flags.  
**Evidence:** Player-absence literature shows opening-line bias can be removed by the close; QB has disproportionate point-spread value; nflWAR supports hierarchical player effects. The plausible edge is timing/uncertainty, not the fact of an injury itself.

## D006 — QB is a separately modeled component
**Decision:** M2 requires dynamic QB ability, starter probability and backup/replacement quality.  
**Reason:** Public professional systems explicitly identify QB injury adjustment as a major NFL modeling problem; player-value research finds quarterbacks dominate spread value.

## D007 — Fixed rolling windows are a live weakness
**Decision:** Advance hierarchical latent team/unit state.  
**Reason:** State-space sports literature directly models week-to-week and season-to-season strength changes, whereas fixed windows smear regime changes and express no coherent uncertainty.

## D008 — Q2 V1 is not a negative result
**Decision:** A new discrete margin experiment is scientifically permitted only if numerically redesigned.  
**Reason:** Q2 failed its finite-support/truncation contract before valid performance evaluation. V2 must use adaptive/unbounded/tail-safe support and direct whole-number mass handling.

## D009 — Key numbers are representation, not presumed alpha
**Decision:** Retain conditional key-number mass in M4 but do not treat 3/7 discontinuities as a betting edge.  
**Evidence:** 2026 Finance Research Letters evidence finds strong betting-demand discontinuities around 3 and 7 but no corresponding realized-return discontinuity.

## D010 — Distributional methods are tools, not hypotheses
**Decision:** GAMLSS, NGBoost, distributional forests, Student-t/skew families and Bayesian distributional regression remain implementation options only after Phase-2 data qualification and Phase-3 preregistration.  
**Reason:** Algorithm novelty is not information novelty; NFL samples are small.

## D011 — Forecast combination deferred
**Decision:** Do not shortlist stacking/model averaging as an independent candidate.  
**Reason:** Combination is justified only after complementary residual information exists. Candidate5 and prior model families provide no such evidence; forecast-combination literature warns estimated optimal weights can add variance.

## D012 — Game-state/backdoor-cover candidate killed pre-implementation
**Decision:** Do not advance a separate possession/garbage-time candidate in V2 Phase 1.  
**Reason:** B0 already implemented a materially different-but-related possession architecture and lost to market; no new PIT information source was identified that would make a game-path simulator independently informative. Reconsider only if M4 diagnostics later isolate systematic tail/game-state misspecification.

## D013 — Generic matchup interaction expansion killed
**Decision:** Do not create a large OL×pass-rush / man-zone / style interaction ML tournament.  
**Reason:** plausible football relationships are not enough; sample size and multiple testing are severe, and no credible mechanism was found for consistent information beyond market state.

## D014 — Deep learning killed as a default
**Decision:** No transformer/neural candidate absent a uniquely high-dimensional PIT data source whose structure requires it.  
**Reason:** sample efficiency and leakage risk dominate novelty benefits in NFL game-level forecasting.

## D015 — Paid data decision postponed
**Decision:** Do not purchase data in Phase 1.  
**Reason:** The Odds API and SportsDataIO appear materially capable of unlocking M1, but Phase 2 must first validate sample schemas and PIT semantics. Historical odds is the one paid-data category with a credible direct scientific benefit.