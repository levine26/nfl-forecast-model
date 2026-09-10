# LevLine Research Architecture

## Production firewall

Production LevLine remains the official engine. Research code may not modify production `final_home_prob`, the 75% PURE / 25% MARKET production blend, T-120 locking, official prediction history or grading, `outputs/`, or `site/`. Research modules are not imported by the production prediction path. Research workflows are separate from normal forecast workflows and write only to `challenger_outputs/` or `research_outputs/`.

Research branches are checked by `scripts/check_research_firewall.py`. The policy is fail-closed: only explicitly isolated challenger/research source, scripts, tests, docs, and research workflows are permitted. Core model/data/publish/lock files, `outputs/`, `site/`, and undeclared repository surfaces are blocked.

## Current production and challenger architecture

Production remains the existing football model plus the fixed 75% PURE / 25% MARKET behavior. No work in the v0.9 program authorizes promotion.

The research stack already supports season-forward base-model OOF predictions, a nested stack, fixed and adaptive football/market blends, opponent-adjusted features, QB starter state, and immutable 2026 challenger shadow locking. v0.8 QB state uses schedule starter identity and only completed prior-start EPA/dropback, success, CPOE, experience, and continuity; rolling features are shifted before the current matchup.

## Historical benchmark evidence before v0.9

The fully nested 2022-2025 comparison contains 1,087 games. Current recorded v0.8 results are:

| Candidate | Winner accuracy | Brier | Log loss |
| --- | ---: | ---: | ---: |
| Market-only benchmark | 67.6173% | 0.210199 | 0.607647 |
| Production-compatible Nested PURE | 64.4894% | 0.223853 | 0.638946 |
| Production-like 75% PURE / 25% MARKET | 65.8694% | 0.218592 | 0.627402 |
| Production-compatible adaptive Brier | 67.5253% | 0.211765 | 0.611769 |
| Opponent-adjusted + QB-aware 75/25 | 66.0534% | 0.218343 | 0.626741 |
| Opponent-adjusted + QB-aware adaptive Brier | 67.8933% | 0.211764 | 0.611748 |

The current historical leader therefore has only a small accuracy edge over the market benchmark and remains worse than market on Brier and log loss. That is not sufficient evidence for promotion. v0.9 adds paired uncertainty analysis specifically so 0.2-0.3 percentage-point historical differences are not treated as deterministic superiority.

## Experiment registry

`research/experiments.json` pre-registers v0.9A through v0.9D before their results are known. Each record includes its hypothesis, feature family, historical seasons, timestamp policy, allowed and prohibited data, model family, tuning policy, metrics, creation SHA, status, historical result, and prospective shadow status.

2026 outcomes are prohibited from feature, architecture, hyperparameter, weight, and candidate selection. Candidates that qualify historically must be precommitted before grading in the immutable 2026 T-120 shadow system.

## v0.9 player-value methodology

The intended data flow is play/player history -> strongly shrunk player latent value -> compact unit/team state -> game-level challenger. Stable nflverse IDs are preferred; ambiguous identity fails closed. Small samples are regressed heavily toward role/position priors. Current-game realized snaps, postgame workload, future depth charts, and later injury information are prohibited from historical features.

v0.9A tests player value without hindsight availability. v0.9B may add probabilistic availability only where historical T-120 provenance can be reconstructed. v0.9C compresses validated player state into a modest number of unit features. v0.9D tests only predeclared opponent interactions rather than searching arbitrary interaction space.

## Statistical qualification

Serious candidates are evaluated on accuracy, Brier, log loss, calibration slope/intercept, probability bins, season and regime slices, paired IID bootstrap, paired week-block and season-block bootstrap, and supplemental paired loss-difference tests. A conservative multiple-model confidence-set approximation retains candidates that cannot be shown to be worse than the empirical leader under block resampling.

Historical qualification does not imply production promotion. Promotion requires a separate explicit decision after historical OOS evidence, calibration, uncertainty, prospective 2026 shadow results, operational reliability, data availability, interpretability, and site implications are reviewed.
