# Phase 1 — Leakage, Chronology, and Reproducibility Audit

**Status:** audit only; no production behavior changed  
**Audited main:** `e63fd396e1ae37fc63a4085e380ba52e0412dc74`

## Summary

The current LevLine Core feature construction is substantially chronology-aware: team performance is shifted before rolling, Elo is sequential, and future/unplayed rows do not contribute outcomes. The principal Phase 1 concerns are instead **evaluation leakage/optimism at ensemble layers**, ambiguous point-in-time semantics for some tempting external fields, and multiple forecast surfaces with different freeze boundaries.

## 1. Core team-form chronology

### PASS — lagged team performance

`aggregate_team_games()` uses completed-game PBP.  
`add_pregame_rolling()` shifts each team series by one before EWMA and rolling windows.

Result: the current game's EPA, success, win result, and related PBP fields do not enter that same game's pregame Core row.

### PASS — sequential Elo

`build_pregame_elo()` writes pregame ratings before applying the current game's result.

### PASS WITH NOTE — cross-season rolling history

Rolling team state does not reset at the season boundary. Early-season forecasts therefore inherit prior-season games. This is point-in-time valid, but it is a modeling assumption that can create stale-state error after large offseason changes.

## 2. Regression validation semantics

### MATERIAL LIMITATION — final ensemble weights are estimated on the same OOF block they summarize

For margin and total:

1. base regressors are fit only on seasons before each target season;
2. 2022–2025 base OOF predictions are therefore season-held-out;
3. mean MAE for each base model is calculated across that combined target block;
4. inverse-MAE weights are estimated from those same OOF errors;
5. those weights are applied back to the same rows to produce the reported ensemble validation MAE and residual sigma.

This is not catastrophic target leakage into the base predictions, but it is **evaluation-set reuse for ensemble weighting**. Phase 1 labels the result a *current-validation descriptive ensemble*, not a chronology-clean candidate-selection estimate.

### Phase 2 requirement

Any challenger comparison must nest weight/stack selection inside prior-time data or use a separately frozen development/holdout protocol.

## 3. Ordinary classifier stack validation

### MATERIAL LIMITATION — meta-model fit and score reuse the same OOF rows

`fit_season_stacked_classifier()` creates season-held-out base classifier predictions, then fits the logistic meta-model on the combined OOF matrix and scores that same matrix.

Therefore:

- base probabilities are season-held-out;
- final displayed `stack` OOF probabilities are not fully nested.

Do not use ordinary Core/Sujar stack OOF performance as equivalent to the more rigorously audited F-ST chronology.

## 4. Frozen F-ST chronology

### PASS — explicit 2025 cutoff for the official normal market-eligible path

The official F-ST artifact enforces:

- target season 2026;
- training cutoff 2025;
- zero 2026 outcomes in frozen coefficient fitting;
- frozen training digest and artifact identity.

Historical Phase 1 winner metrics use the existing season-forward F-ST analogue rather than blindly backscoring final frozen coefficients and calling that clean OOS evidence.

### IMPORTANT BOUNDARY — fallback is not the same freeze

When market probability is unavailable, F-ST falls back to the exact legacy path. The legacy PURE probability is produced by the ordinary Core stack, whose final live fit uses the current `historical` frame.

Because `historical` includes completed 2026 games, a market-missing fallback later in 2026 can indirectly incorporate earlier 2026 outcomes. That is valid prospective updating for a future game, but it means “F-ST is frozen” is only strictly true for the market-eligible frozen equation and its nested PURE input boundary—not every fallback component.

## 5. Current-season refitting

### CURRENT PRODUCTION BEHAVIOR — completed 2026 games enter ordinary final fits

`pipeline.run()` defines historical rows as all games with a known `home_win`, then fits:

- Sujar baseline;
- Core football classifier;
- margin regression;
- total regression

on that frame after the 2022–2025 validation procedure.

As 2026 games finish, they can update those final fits for later 2026 games.

This is not hindsight for a future matchup because only already-completed games are available. However:

- completed 2026 outcomes must not be used to choose Phase 2 architecture/features/thresholds;
- research reproduction must distinguish the frozen pre-2026 evaluation from live in-season refitting.

## 6. Market timing

### LIMITATION — historical schedule market lines are not horizon-matched

Historical `spread_line`, `total_line`, and moneyline fields are useful market benchmarks, but their exact bookmaker and capture horizon are opaque in the current schedule row.

They may be described as historical/closing-like market benchmarks. They may not be relabeled as T-120, opening, or a specific book without separate timestamped evidence.

### PASS — prospective T-120 selector

`market_t120.py` uses timestamped run history and chooses the latest usable market snapshot at or before kickoff minus 120 minutes, with staleness controls.

## 7. QB and starter identity

### HIGH-RISK IF REUSED NAIVELY — final schedule QB IDs

The schedule exposes `home_qb_id` / `away_qb_id`, and prior research code builds QB features from them. A final historical schedule row can reflect the starter who actually played.

Unless the repository proves that the historical starter identity was published and preserved at the tested decision horizon, it must not be treated as a T-120-safe feature merely because it exists in the schedule.

Phase 1 therefore does not use final historical QB identity for causal residual subgroup claims.

### Safer paths

- timestamped depth-chart snapshots;
- separately archived expected-lineup/start-state receipts;
- prior completed-game QB quality attached only after pregame starter identity is independently qualified.

## 8. Injury / availability

### PASS WITH NARROW SCOPE — 2025 composite

The 2025 composite qualifies injury listing plus final practice state known before T-120 for 2025 only.

It does **not** authorize:

- final game status as a model feature;
- realized active/inactive status learned later;
- actual snaps;
- 2022–2024 extrapolation;
- a unified multi-season availability experiment.

### FAIL-CLOSED RULE

Missing availability evidence is unknown, not healthy.

## 9. Weather

### HIGH-RISK — realized weather as historical pregame input

Historical schedule temperature/wind fields are not sufficient proof of what the forecast looked like before kickoff. Realized conditions must not be substituted for archived forecast state.

The dedicated weather research contract correctly requires immutable pregame forecast snapshots or archived model runs with public-availability lag.

## 10. Depth charts, rosters, and participation

- 2025+ timestamped depth-chart rows can be PIT-safe when snapshot time <= decision time.
- Current roster endpoints cannot be projected backward without a preserved historical snapshot.
- Realized current-game participation/snaps are prohibited.
- 2023+ participation publication timing can be too late for same-season historical decision reconstruction.

## 11. Advanced player data

NGS, PFR advanced, and FTN charting are observed-performance sources. They may enter only as **lagged prior-completed-game** features after publication timing and missingness are enforced.

Same-game advanced data are prohibited.

## 12. News and media

A current article can explain a current forecast, but a historical backtest can only consume news that has a preserved publication timestamp at or before the simulated forecast time.

Search-engine rediscovery of an old article is not, by itself, a complete historical as-of data pipeline.

## 13. Public probability-to-margin bridge

The public fair margin is a deterministic transform of official home-win probability using `margin_sigma`.

For current 2026 production, the sigma comes from the pre-2026 validation block. That is acceptable as a fixed bridge parameter.

For historical diagnostic reconstruction, Phase 1 labels any bridge using full-block residual sigma as a descriptive coherence test rather than chronology-clean margin OOS validation.

## 14. Tie semantics

Two current semantics deserve explicit treatment:

- Core target: tie -> `home_win = 0`.
- Publication grader: actual winner is home only if margin > 0, otherwise away; thus a tie is also resolved as away for the winner-correct field.

This affects only rare tied NFL games but should be normalized in a future accountability cleanup. Phase 1 keeps production untouched and reports tie-excluded sensitivity.

## 15. Configuration reproducibility

The YAML exposes rolling-window and EWMA settings, while the inspected feature-builder call currently relies on matching function defaults rather than passing those config values through explicitly.

Today the values agree. Future config edits could create a silent configuration/code mismatch unless this is hardened.

## 16. Research firewall status

The Phase 1 branch changes only research/docs/workflow surfaces. Existing research firewall checks passed on the initial Phase 1 PR head, and the dedicated Phase 1 workflow verifies protected production surfaces remain unchanged.

## 17. Required Phase 2 safeguards

1. Freeze a development/holdout chronology before challenger results are inspected.
2. Nest ensemble/meta weights inside prior-time folds.
3. Preserve a distinct untouched holdout for final model selection.
4. Continue the 2026-outcome selection firewall.
5. Require exact as-of contracts for starter, injury, depth, weather, market, and news features.
6. Fail closed on missing or ambiguous player identity.
7. Treat market timing families separately rather than mixing opaque closing lines with T-120 snapshots.
8. Report ties/pushes explicitly.
9. Keep direct football score forecasts separate from market-conditioned winner/public-spread outputs during evaluation.
