# LevLine Research Architecture

> **Archived historical research record — superseded for current-state guidance.**  
> This document preserves the wording and evidence from an earlier research phase. It is **not** the current production architecture or active LevLine 4 roadmap. Current production uses `F-ST-01-FROZEN-2026`; it is **not** a fixed 75% PURE / 25% MARKET arithmetic blend. Current production/release status is governed by `docs/LEVLINE_3_RELEASE.md` and `IMPLEMENTATION_STATUS.md`. The active research program is `research/LEVLINE_4_RESEARCH_SPEC.md` plus `research/levline4_prereg_v1.json`. Statements below about former production-like blends, F-ST being research-only, or old availability status are retained solely as historical evidence.

## Production firewall

Production LevLine remains the official engine. Research code may not modify production `final_home_prob`, the 75% PURE / 25% MARKET production blend, T-120 locking, official prediction history or grading, `outputs/`, `site/`, or Sunday Signal publication. Research modules are not imported by the production prediction path. Research workflows are separate from normal forecast workflows and write only to `challenger_outputs/` or `research_outputs/`.

Research branches are checked by `scripts/check_research_firewall.py`. The policy is fail-closed: core model/data/publish/lock files, `outputs/`, `site/`, and undeclared repository surfaces remain protected. 2026 outcomes are prospective-only and are prohibited from feature, architecture, hyperparameter, coefficient, weighting, threshold, and candidate selection.

## Historical benchmark and completed evidence

The paired 2022-2025 comparison contains 1,087 games. The production-like 75% PURE / 25% MARKET benchmark was 65.8694% winner accuracy, Brier 0.218592, log loss 0.627402. Market was 67.6173%, 0.210199, and 0.607647. The v0.8 opponent-adjusted + QB adaptive-Brier research benchmark was 67.8933%, 0.211764, and 0.611748.

Completed v0.9 / Track F dispositions are recorded in `research/experiments.json`:

- `V09A-PLAYER-VALUE-001`: rejected. The original lagged target/rush player-value formulation did not improve v0.8; it will not be rescued through post-result tuning.
- `V09B-AVAILABILITY-001`: historically source-qualification blocked/rejected at execution time because the then-current source stack had no qualifying 2025 official timestamped injury/practice-report rows. That historical disposition is preserved. PR #142 later qualified a separate 2025-only reconstruction; `research/availability/V09B_source_blocker_resolution_v1.json` records that source-blocker resolution without retroactively running or rewriting V09B.
- `V09C-UNIT-STATE-001`: rejected. Its small point-estimate probability gain over v0.8 was not established under paired uncertainty and it was materially worse than market on Brier/log loss.
- `V09D-MATCHUP-INTERACTIONS-001`: dependency-blocked, not an empirical failure. This exact registered design required validated v0.9C unit state; because v0.9C failed qualification, the registered v0.9D design was not historically executed.
- `V09D-EWMA-INTERACTIONS-002`: rejected. The fixed four-interaction EWMA ablation did not establish incremental value and was significantly worse than market on probability quality.
- `F-MR-01`, `F-MI-01`, and `F-LS-01`: rejected. Their registered market-residual, margin-informed, and latent-state hypotheses failed; no post-result parameter or architecture search is authorized to rescue them.
- `F-ST-01`: leading historical next-generation candidate. It reached 68.0773% winner accuracy, Brier 0.210774, and log loss 0.608977. It clearly improved over production-like LevLine historically and largely closed the probability-quality gap to market. Its incremental probability-quality superiority over market was not established under the predeclared week-block gate, so this evidence is not a production-promotion claim.

## F-ST-01 frozen prospective direction

The next research-only candidate is a frozen F-ST stack. Its architecture is immutable: exactly `logit(market_home_prob)` and `logit(v0.8 PURE)` feed one logistic regression with intercept, L2 regularization, `C=1.0`, `lbfgs`, and `max_iter=3000`. There are no interactions, splines, season indicators, coefficient/C grids, alternate model families, or post-result tuning. Historical meta-model fitting for a scored season uses only earlier-season OOF rows; 2026 outcomes may never enter training or selection.

The explicit prospective research-shadow authorization is separate from the original historical qualification decision. It does not authorize production promotion. Any architectural change must receive a new candidate/version identifier rather than silently modifying the frozen candidate.

## T-120 shadow semantics

Current-main research shadow infrastructure supports immutable multi-candidate identity by `(game_id, challenger_version, research_candidate)`, authoritative alignment to FINAL production T-120 locks, rejection of challenger forecasts generated after the authoritative production lock, grading without mutating the locked forecast, and selected/non-selected research candidate markers. F-ST work extends this existing infrastructure rather than replacing production locking.

For the frozen F-ST shadow, each prospective row must retain enough information to reproduce the probability: official production probability, market probability, v0.8 PURE probability, F-ST probability, generation/lock/kickoff timestamps, source SHA, training cutoff, applicable coefficients, candidate version, selection marker, and eventual outcome. A late challenger row is rejected for prospective scoring rather than backfilled.

## Predeclared prospective evaluation

Primary metric: Brier score. Secondary evidence: log loss, winner accuracy, calibration intercept/slope, week-block paired bootstrap, season/week-aware uncertainty where appropriate, disagreement-game performance, high-confidence calibration, market disagreement, and production-LevLine disagreement.

The prospective review asks three distinct questions: (A) does frozen F-ST materially outperform current production LevLine, (B) is its probability quality at least competitive with market, and (C) is any improvement coherent across weeks rather than concentrated in a few games? The evaluation policy must remain fixed before prospective outcomes accumulate; no threshold may be invented after observing results.

## Player Impact Engine

The player program continues as research/explainability infrastructure rather than a forced probability feature. Stable IDs, chronological prior-game state, player-game-role observations, snap/depth foundations, observed-vs-modeled separation, and player-impact card schemas remain useful even though V09A failed.

Next work should estimate expected lineup value lost/gained, QB state and downgrade/upgrade, skill-player workload/value, OL continuity/availability, defensive-front contribution, secondary burden, replacement quality, uncertainty, and matchup-specific risk. Observed source statistics must remain explicitly separate from modeled LevLine impact.

Player impact should first power research cards, Sunday Signal explanatory context, lineup-change diagnostics, injury/availability summaries, market-disagreement analysis, and “why the model moved” analysis. It may affect an official probability only through a separately pre-registered future candidate testing whether leakage-safe expected-lineup impact adds incremental Brier signal beyond frozen F-ST.

## Availability qualification

The former **2025 source-coverage gap is now resolved for a narrow research scope**. PR #142 qualified `availability_2025_composite_reconstruction` for 2025 Weeks 1-22 using the pinned nflverse 2025 injury asset for stable GSIS identity, all 22 official NFL historical injury pages as the primary independent cross-check, conservative official filing-day chronology before T-120, and a commit-pinned FootballDB-derived mirror as supplemental evidence only. The exact qualification receipt is `research/availability/2025_reconstruction_qualification_v1.json`.

The qualified historical target is injury listing plus final practice-report state demonstrably known before T-120. Of 6,068 canonical player-week rows, 6,064 resolve cleanly; practice-state agreement and matched-row T-120 chronology are 100%. Four rows remain deliberately unresolved rather than guessed. Actual current-game snaps, postgame participation, and completed-2026 outcomes were not used. Final game designation remains diagnostic-only because the reconstruction does not authorize a fully revision-aware historical game-status feature.

This does **not** authorize V09B, a new probability feature, or production use. Before any 2022-2025 availability experiment runs, LevLine must prove one harmonized cross-season contract for chronology, stable identity, missingness semantics, status normalization, and feature construction across all four validation seasons. The existing 2022-2024 source history and the newly qualified 2025 reconstruction cannot simply be concatenated and treated as equivalent without that audit.

The verified Sleeper archive remains a separate 2026-only source beginning February 1, 2026. It continues to support point-in-time/shadow research under its own qualification gates, and completed-2026 outcomes remain prohibited for model or threshold selection.