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
- Market implied-probability conversion
- Prediction snapshot history
- GitHub Actions weekly and Sunday jobs
- Leakage unit test
- Future-game schedule scaffold so upcoming games inherit latest completed rolling state
- Next-unresolved-week publication filter
- Standalone-game FINAL refresh cadence (Mon/Wed/Thu) plus Sunday slate refresh

## Intentionally versioned for V0.2+
These were identified as useful but should not enter the live model until they beat V0.1 out of sample:
- opponent-adjusted EPA iterations
- returning-snap / OL continuity priors
- NGS QB composite
- PFR/FTN pressure matchup
- FTN motion/play-action/RPO/blitz features
- weather
- travel/timezone/altitude
- special-teams rating
- empirical score/margin prediction intervals

This separation is deliberate: the project keeps a stable baseline so every added complexity must prove incremental predictive value.
