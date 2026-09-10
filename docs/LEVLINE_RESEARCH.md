# LevLine Research Architecture

## Production firewall

Beginning with production version `0.9.0-fst`, official LevLine winner probability is `F-ST-01-FROZEN-2026`. Production computes a dedicated `fst_pure_home_prob` through a production-safe reproduction of the validated nested base-model/meta-model process and then combines `logit(fst_pure_home_prob)` with the current vig-free moneyline probability using the frozen F-ST coefficients. Production modules do not import challenger/research modules.

The pre-F-ST 75% legacy PURE / 25% MARKET model remains an exact prospective counterfactual: `pure_home_prob` retains its legacy meaning and `legacy_final_home_prob` is preserved on every new production prediction. Research code may not silently modify the F-ST artifact, official `final_home_prob`, locking, official prediction history or grading, `outputs/`, `site/`, or Sunday Signal publication. Research workflows remain separate from normal forecast workflows and write only to challenger/research surfaces except for explicitly reviewed production-promotion changes.

Research branches are checked by `scripts/check_research_firewall.py`. The policy remains fail-closed: production model/data/publish/lock surfaces and undeclared repository surfaces are protected. 2026 outcomes are prohibited from F-ST feature-architecture, hyperparameter, coefficient, weighting, threshold, and candidate selection. A separately registered future candidate may later test forward-only 2026 updating; F-ST-01 itself is immutable.

## Historical benchmark and completed evidence

The paired 2022-2025 comparison contains 1,087 games. The production-like 75% PURE / 25% MARKET benchmark was 65.8694% winner accuracy, Brier 0.218592, log loss 0.627402. Market was 67.6173%, 0.210199, and 0.607647. The v0.8 opponent-adjusted + QB adaptive-Brier research benchmark was 67.8933%, 0.211764, and 0.611748.

Completed v0.9 / Track F dispositions are recorded in `research/experiments.json`:

- `V09A-PLAYER-VALUE-001`: rejected. The original lagged target/rush player-value formulation did not improve v0.8; it will not be rescued through post-result tuning.
- `V09B-AVAILABILITY-001`: source-qualification blocked/rejected for historical probability testing because the current source stack has no qualifying 2025 official timestamped injury/practice-report rows. Depth charts and retrospective actual snaps are not substitutes.
- `V09C-UNIT-STATE-001`: rejected. Its small point-estimate probability gain over v0.8 was not established under paired uncertainty and it was materially worse than market on Brier/log loss.
- `V09D-MATCHUP-INTERACTIONS-001`: dependency-blocked, not an empirical failure. This exact registered design required validated v0.9C unit state; because v0.9C failed qualification, the registered v0.9D design was not historically executed.
- `V09D-EWMA-INTERACTIONS-002`: rejected. The fixed four-interaction EWMA ablation did not establish incremental value and was significantly worse than market on probability quality.
- `F-MR-01`, `F-MI-01`, and `F-LS-01`: rejected. Their registered market-residual, margin-informed, and latent-state hypotheses failed; no post-result parameter or architecture search is authorized to rescue them.
- `F-ST-01`: selected frozen production candidate. It reached 68.0773% winner accuracy, Brier 0.210774, and log loss 0.608977 on the registered paired historical set. That compared with 65.8694% / 0.218592 / 0.627402 for the production-like legacy 75/25 benchmark and 67.6173% / 0.210199 / 0.607647 for market. Historical probability-quality superiority over market was not established under the registered gate; the explicit 2026 production authorization was a separate deployment decision and did not authorize retuning.

## F-ST-01 frozen production architecture

`F-ST-01-FROZEN-2026` is immutable. Exactly `logit(market_home_prob)` and `logit(fst_pure_home_prob)` feed one frozen logistic-regression scoring layer with intercept, L2 regularization, `C=1.0`, `lbfgs`, and `max_iter=3000`. There are no interactions, splines, season indicators, coefficient/C grids, alternate model families, or post-result tuning. The production artifact records the exact coefficients, 1,615 training games from 2020-2025, and training digest `6a26713b636a98298bb619982bb38b2e5dbb78816e093e6f910c1cee32ab5aa0`.

The football-only F-ST input is not legacy `pure_home_prob`. It is reproduced with season-forward base-model OOF construction using the same four base-model templates, the same preprocessing, deterministic seed 26, the same nested meta-model, the production-compatible core feature set, and the same future/live inference semantics as the validated research implementation. F-ST architecture/coefficient fitting is hard-cut at 2025. Completed 2026 games may update ordinary pregame rolling football state only where already supported by the production feature pipeline; they do not enter F-ST coefficient or architecture fitting.

For a missing/non-finite current market probability, F-ST is ineligible and production falls back per game to exact legacy behavior. No spread-derived or synthetic moneyline probability is substituted.

## T-120 shadow semantics

The pre-deployment F-ST shadow ledger remains immutable historical evidence. It is not rewritten merely because the same frozen candidate became production. Shadow infrastructure retains candidate identity by `(game_id, challenger_version, research_candidate)`, authoritative alignment to FINAL production T-120 locks, rejection of challenger forecasts generated after the authoritative production lock, grading without mutating locked forecasts, and selected/non-selected candidate markers.

After promotion, prospective evaluation compares official F-ST against the separately persisted legacy 75/25 counterfactual and the same locked market snapshot. It must not compare F-ST to `production_final_home_prob` after production itself is F-ST and then treat a zero delta as evidence.

For each official post-promotion lock, the production ledger retains enough information to reproduce the regime: official F-ST probability, F-ST nested PURE, current vig-free market probability, exact legacy PURE and legacy 75/25 counterfactual, strategy/model version, artifact identity, generation/lock/kickoff timestamps, and eventual outcome. Late or historical rows are not backfilled.

## Prospective evaluation

Primary metric remains Brier score. Secondary evidence includes log loss, winner accuracy, calibration intercept/slope, week-block paired bootstrap, season/week-aware uncertainty where appropriate, disagreement-game performance, high-confidence calibration, market disagreement, and legacy-LevLine disagreement.

The post-promotion review asks: (A) how official frozen F-ST performs versus the preserved legacy LevLine counterfactual, (B) how it performs versus the matched market snapshot, and (C) whether differences are coherent across weeks rather than concentrated in a few games. These comparisons are diagnostic for future candidates; early 2026 results may not mutate F-ST-01 in place.

## Player Impact Engine

The player program continues as research/explainability infrastructure rather than a forced probability feature. Stable IDs, chronological prior-game state, player-game-role observations, snap/depth foundations, observed-vs-modeled separation, and player-impact card schemas remain useful even though V09A failed.

Next work should estimate expected lineup value lost/gained, QB state and downgrade/upgrade, skill-player workload/value, OL continuity/availability, defensive-front contribution, secondary burden, replacement quality, uncertainty, and matchup-specific risk. Observed source statistics must remain explicitly separate from modeled LevLine impact.

Player impact should first power research cards, Sunday Signal explanatory context, lineup-change diagnostics, injury/availability summaries, market-disagreement analysis, and “why the model moved” analysis. It may affect an official probability only through a separately pre-registered future candidate testing whether leakage-safe expected-lineup impact adds incremental Brier signal beyond frozen F-ST.

## Availability qualification

Historical availability is the main player-modeling bottleneck. The current source stack has historical official injury coverage through 2024 but zero qualifying 2025 rows. Any new source must have defensible timestamp semantics and stable IDs or a safe crosswalk. Do not fabricate 2025 injury state, infer final inactives from actual snaps, or treat depth charts as official pregame availability. If complete historical qualification remains impossible, availability can still be used prospectively from a later explicit freeze date but cannot be represented as historically validated.
