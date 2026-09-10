# LevLine Research Architecture

## Production firewall

Production LevLine remains the official engine. Research code may not modify production `final_home_prob`, the 75% PURE / 25% MARKET production blend, T-120 locking, official prediction history or grading, `outputs/`, `site/`, or Sunday Signal publication. Research modules are not imported by the production prediction path. Research workflows are separate from normal forecast workflows and write only to `challenger_outputs/` or `research_outputs/`.

Research branches are checked by `scripts/check_research_firewall.py`. The policy is fail-closed: core model/data/publish/lock files, `outputs/`, `site/`, and undeclared repository surfaces remain protected. 2026 outcomes are prospective-only and are prohibited from feature, architecture, hyperparameter, coefficient, weighting, threshold, and candidate selection.

## Historical benchmark and completed evidence

The paired 2022-2025 comparison contains 1,087 games. The production-like 75% PURE / 25% MARKET benchmark was 65.8694% winner accuracy, Brier 0.218592, log loss 0.627402. Market was 67.6173%, 0.210199, and 0.607647. The v0.8 opponent-adjusted + QB adaptive-Brier research benchmark was 67.8933%, 0.211764, and 0.611748.

Completed v0.9 / Track F dispositions are recorded in `research/experiments.json`:

- `V09A-PLAYER-VALUE-001`: rejected. The original lagged target/rush player-value formulation did not improve v0.8; it will not be rescued through post-result tuning.
- `V09B-AVAILABILITY-001`: source-qualification blocked/rejected for historical probability testing because the current source stack has no qualifying 2025 official timestamped injury/practice-report rows. Depth charts and retrospective actual snaps are not substitutes.
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

Historical availability is the main player-modeling bottleneck. The current source stack has historical official injury coverage through 2024 but zero qualifying 2025 rows. Any new source must have defensible timestamp semantics and stable IDs or a safe crosswalk. Do not fabricate 2025 injury state, infer final inactives from actual snaps, or treat depth charts as official pregame availability. If complete historical qualification remains impossible, availability can still be used prospectively from a later explicit freeze date but cannot be represented as historically validated.
