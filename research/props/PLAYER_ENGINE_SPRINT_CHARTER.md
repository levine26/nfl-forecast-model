# LevLine Props Sunday Sprint Charter

Status: preregistered research beta charter
Created: 2026-09-17
Target: research-beta readiness before Sunday, 2026-09-20 games

## Objective
Build a research-only offensive player-prop forecasting engine that produces coherent player-stat distributions, LevLine fair lines, fair probabilities, fair odds, market comparisons, and immutable prospective records without altering official LevLine winner probabilities.

## Sunday scope
Supported offensive markets only:
- QB: passing yards, rushing yards, passing TDs, rushing TDs / anytime TD.
- RB: rushing yards, receiving yards, receptions, rushing TDs, receiving TDs / anytime TD.
- WR/TE: receiving yards, receptions, receiving TDs / anytime TD.

Defensive information may be used only as explanatory/predictive input to offensive prop accuracy. No defensive prop product is authorized in this sprint.

## Required output contract
For yardage/reception markets, every eligible forecast should expose:
- player identity and stable player_id
- game_id, team, opponent, position
- prop_type
- forecast timestamp / data horizon
- model mean projection
- model median / LevLine fair line
- uncertainty interval(s)
- market line
- market over/under prices when available
- de-vigged market probabilities when available
- LevLine P(over) / P(under)
- probability edge vs market
- fair odds at the market line
- line edge = LevLine fair line - market line
- confidence/data-quality state
- model/version identifiers

For TD markets, every eligible forecast should expose:
- expected TDs where modeled
- P(1+ TD) or P(over listed TD line)
- LevLine fair odds
- market odds and no-vig market probability when available
- probability edge
- confidence/data-quality state

## Architecture
The intended causal/order hierarchy is:
Game environment -> team plays -> pass/rush split -> player participation/role -> attempts/carries/routes -> targets -> receptions -> yards -> TD opportunities/results.

Components should model shared latent game state so outputs are internally coherent rather than five unrelated regressions.

## Fair-line rule
For continuous yardage markets, the default LevLine fair line is the model distribution median (the approximately 50/50 threshold), not automatically the mean. Mean and median should both be retained. Integer markets such as receptions must handle discrete outcomes and push mass explicitly. TD markets should primarily express fair probability/fair odds; QB passing-TD O/U can also expose a fair threshold.

## Scientific guardrails
- Completed 2026 outcomes are prohibited from architecture, feature, hyperparameter, calibration, threshold, or weighting selection.
- No current-game or post-kickoff information may enter a pregame forecast.
- Stable player identity is required; ambiguous identity fails closed.
- Every live forecast must preserve the market line/price and model state that existed at prediction time.
- Existing failed v0.9A player-value and v0.9C continuity formulations must not be post-hoc rescued or relabeled as new evidence.
- Official LevLine/F-ST winner probabilities are untouched.
- Player-to-game integration is shadow/research only unless a separate future promotion gate is satisfied.
- Missing/uncertain source data must be represented explicitly; do not fabricate availability, routes, snaps, or market prices.
- A no-signal outcome is valid and preferable to unsupported confidence.

## Sunday beta standard
Sunday readiness does NOT require proven market superiority. It DOES require:
- deterministic/reproducible execution
- tested input validation
- coherent output schema
- leakage safeguards
- prospective timestamped/immutable predictions
- graceful fail-closed behavior
- clear RESEARCH BETA labeling
- no mutation of production winner probabilities

## Evaluation
Track separately by prop family:
- distribution quality: MAE/RMSE where useful, CRPS, interval coverage/PIT diagnostics when sample permits
- probability quality: Brier, log loss, calibration/reliability, resolution
- market-relative: probability delta vs no-vig market, fair-line delta, closing-line movement / CLV
- betting ROI is downstream evidence only and must not be the primary tuning objective

## Parallel lanes
- research/props-data: offensive player/role/current-slate data contract and source QA
- research/props-opportunity: plays, pass/rush, dropbacks, carries, routes/targets/receptions opportunity models
- research/props-efficiency-td: efficiency, matchup adjustments, TD opportunity/allocation models
- research/props-simulation: coherent joint Monte Carlo distributions and fair-line/fair-price calculations
- research/props-market: sportsbook ingestion, no-vig, consensus/market-CDF, line movement and market comparisons
- research/props-product-qa: research-beta publication/UI/history/grading/tests/fail-closed surfaces
- research/props-integration: coordinator-only integration staging branch
- research/props-governance: charter/contracts/evidence only

## Integration rule
Worker branches should not directly modify official production probability logic. Cross-lane assumptions should be expressed through explicit schemas/interfaces. Coordinator reviews and integrates validated pieces through research/props-integration before any main-branch merge decision.
