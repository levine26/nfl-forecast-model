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

## D016 — Free historical M1 fails the Phase-3 reconstruction gate
**Decision:** Set historical `FRONTIER-M1-DYNAMIC-MARKET-STATE` to `BLOCKED_PENDING_PAID_SOURCE`; retain a prospective identity only.  
**Reason:** Genuine free/public data exist, but the 2020–2024 bulk cache is sparse and has a documented fixed-time contamination defect, while 2025 has only four fixed captures/day and the required season×game×book×horizon row panel could not be reproducibly materialized. Open/close and older Wayback data cannot be relabeled/stitched into a coherent modern fixed-horizon panel.

## D017 — Do not preserve M1 with a one-season 2025 historical candidate
**Decision:** Reject `PARTIAL_HISTORICAL` as the Phase-3 M1 disposition.  
**Reason:** A 2025-only, four-capture/day candidate would be cadence/source-specific, weak at near-kick horizons, and scientifically different from the intended multi-season dynamic-state mechanism. A smaller sample is not accepted merely to keep M1 alive.

## D018 — Historical M2 excluded; QB-only prospective identity retained
**Decision:** Freeze `FV2-PROS-M2-QBDELTA-01` at T-120 and exclude historical M2 from Phase 4.  
**Reason:** Broad 2022–2025 PIT personnel state is not qualified. The legitimate mechanism is a timestamped expected-QB-value information delta, not an injury flag or final-starter backfill.

## D019 — M3 final architecture is a market-centered dynamic state-space correction
**Decision:** Freeze `FV2-HIST-M3-DSSM-01`: offense, defense and QB random-walk states with partial pooling/season carryover, expressed only as a ridge-shrunk correction around the historical market benchmark.  
**Reason:** This is the smallest data-qualified architecture materially different from fixed rolling state. Additional pass/rush/unit latent dimensions would add weakly identified complexity and are not preregistered.

## D020 — M4 final architecture is a Student-t tail-safe discrete PMF
**Decision:** Freeze `FV2-HIST-M4-DMARGIN-01`: market-centered Student-t base, exact integer-bin integration, compact conditional scale, and training-only mass offsets only at 0/|3|/|7|.  
**Reason:** It directly fixes Q2 V1's support failure while keeping the comparison set small. The strong null is a constant-scale Student-t integer PMF, not an artificially weak Gaussian.

## D021 — Two historical candidates are enough
**Decision:** Phase 4 receives exactly two historical candidates: M3 and M4.  
**Reason:** M1/M2 failed historical data scope. Creating another model to reach an approximate target count would contradict the research-first program and reintroduce algorithm search.

## D022 — No historical selectivity search
**Decision:** Phase-4 primary evaluation uses all eligible common rows; no edge/confidence/key-number/favorite/underdog/top-percentile betting filters are allowed.  
**Reason:** The program must first establish incremental probability information. Where actual price is unavailable, only a clearly labeled `REFERENCE_MINUS110` sensitivity may be shown, never claimed as actual ROI.

## D023 — Freeze chronology, uncertainty and prospective capture before results
**Decision:** Historical outer development is 2022–2025 regular season with 2010+ prior history, nested chronological weekly updates, strong paired market nulls, 10,000+ week-block bootstrap, no post-hoc calibration rescue, and explicit pre-result leakage tests. Prospective market capture is frozen to increasingly dense cadence approaching kickoff with immutable raw hashes/timestamps and failed-capture logging.  
**Reason:** These contracts prevent result-driven rescue and ensure future market-state research has the PIT data Phase 3 found missing.

## D024 — Phase 3 closes with two historical candidates and no performance look
**Decision:** Mark Phase 3 `COMPLETE` after exact-head validation/firewall success and merge of PR `#574`; keep Phase 4 `NOT_STARTED`.  
**Reason:** The architecture, data, chronology, null, metric, ablation, selectivity, uncertainty, leakage and prospective-capture contracts were frozen before candidate fitting. Exact validated head `8ddad2d6cb40e4296a394b9192bd110f23ba9773` merged at `fd44e51c412f8d242b54de989e29b550f0e67255`. Phase 3 inspected no candidate performance and used zero completed-2026 outcomes.

## D025 — Supersede the first Phase-4 execution before accepting its evidence
**Decision:** Mark workflow run `36023376614` `INVALID / NOT ACCEPTED` and exclude all of its metrics from the scientific record.  
**Reason:** Pre-acceptance contract audit found three implementation/reporting compliance defects: the static M3 ablation did not match the frozen prior-only exponentially pooled/static definition; M3 state history needed to update from all completed prior regular-season football games even when the historical market benchmark row was missing; and M4 did not emit all required secondary ranked-probability/tail diagnostics. The defects were classified as engineering/contract-compliance issues, not evidence-driven scientific redesign. No candidate family, feature channel, state dimension, hyperparameter grid, distribution, key number, market horizon or selective subset was changed.

## D026 — Accept the corrected Phase-4 execution as the canonical evidence package
**Decision:** Accept workflow run `36025306390` and artifact `10820230932` as the canonical Phase-4 execution after corrected result-blind gate success.  
**Reason:** Validated scientific head `c1eead294c5ac897041fc35f628b2fec393ab064` passed compilation, the original and added contract tests, preflight numerical/leakage checks, the literal completed-2026 firewall, and protected-production diff before accepted scoring. The accepted run then completed M3/M4 OOF generation, frozen ablations, calibration, 10,000 week-block bootstrap, ATS diagnostics, red-team audit, evidence verification and immutable preservation. Completed-2026 outcomes used: `0`; production changed: `NO`.

## D027 — Preserve the Phase-4 result pattern without rescue or Phase-5 disposition
**Decision:** Record M3 as `NEGATIVE_PRIMARY_EVIDENCE` and M4 as `POSITIVE_PRIMARY_EVIDENCE`, preserve all ablation/stability/calibration/ATS caveats, and leave formal survivor classification to Phase 5.  
**Reason:** M3 is worse than its market null on the pooled primary proper score (`+0.0006706` candidate-minus-null) and is unfavorable in every outer season. M4 improves the strong Student-t null by `-0.0826717` with a 95% week-block interval wholly below zero and favorable effects in every outer season, but its preregistered ablation shows essentially the entire gain is reproduced by `CONSTANT_SCALE_KEY`; conditional scale alone is slightly worse than the null and the full model is slightly worse than the simpler key-mass ablation. No M3+M4 combination, calibration rescue, threshold search, historical M1/M2 resurrection or production promotion is authorized in Phase 4.
