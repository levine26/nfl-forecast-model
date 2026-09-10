# Implementation Status

## Built now
- Google-Sheets-ready output schema
- Current free nflverse loader layer
- Sequential pregame Elo
- PBP team-game EPA aggregation
- Leakage-safe rolling/EWMA features
- Sujar baseline feature set
- Core Sujar+ feature set
- Walk-forward season stacking
- Margin and total ensembles
- Projected score calculation
- Vig-free market implied-probability conversion
- Prediction snapshot history
- GitHub Actions weekly and Sunday jobs
- Leakage unit test
- Future-game schedule scaffold so upcoming games inherit latest completed rolling state
- Next-unresolved-week publication filter
- Standalone-game FINAL refresh cadence (Mon/Wed/Thu) plus Sunday slate refresh
- Frozen F-ST-01 production winner-probability artifact and fail-closed identity checks
- Production-safe fully nested F-ST PURE inference with no challenger/research imports
- Same-snapshot research→production F-ST parity canary
- Exact legacy 75/25 LevLine counterfactual retained prospectively
- Per-game missing/non-finite market fallback to exact legacy behavior
- Append-only F-ST strategy/artifact/accountability fields for future official locks
- One-line probability-regime rollback switch that does not rewrite historical locks

## Production winner-probability regime

`F-ST-01-FROZEN-2026` is the intended official production winner-probability strategy for version `0.9.0-fst`. It uses current vig-free MARKET plus the validated fully nested F-ST PURE probability in the pinned frozen logit model. F-ST coefficient/architecture fitting is capped at 2025; zero 2026 outcomes enter that fit or deployment selection.

The previous `0.75 * pure_home_prob + 0.25 * market_home_prob` rule remains computed as `legacy_final_home_prob` for every future prediction, and historical production locks remain immutable.

## Separately versioned research

These remain research-only until separately validated and authorized. They are not part of the F-ST-01 production promotion:
- sharper/multi-book market source or timing changes
- timestamped player availability / Sportradar qualification
- player-impact adjustments
- a separately registered forward-only candidate trained with completed 2026 outcomes
- opponent-adjusted EPA iterations beyond the frozen F-ST architecture
- returning-snap / OL continuity priors
- NGS QB composite changes
- PFR/FTN pressure matchup changes
- FTN motion/play-action/RPO/blitz features
- weather
- travel/timezone/altitude
- special-teams rating
- empirical score/margin prediction intervals

This separation is deliberate: the frozen production model remains reproducible while new accuracy work must prove incremental predictive value under a separately registered candidate.
