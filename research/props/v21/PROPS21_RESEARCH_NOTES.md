# Props 2.1 targeted research decisions

Status: frozen implementation rationale for `levline-props-2.1-sunday-v0.1`.

## Decisions used for the Sunday challenger

- Evaluate probabilistic forecasts with proper scores and calibration, rather than treating directional accuracy or realized ROI as sufficient. Gneiting and Raftery (2007) supports CRPS for full distributions and Brier/log loss for event probabilities.
- Treat the sportsbook as a strong benchmark. The frozen LevLine evidence shows the market-only probability beat V1 on Brier/log loss, and the market plus V1 residual did not establish incremental information over price direction.
- Reconstruct a market survival curve only from observed, paired, de-vigged thresholds. Enforce monotonicity, deduplicate bookmakers, and avoid tail extrapolation. Integer lines with unknown push mass remain conditional observations.
- Treat availability, role, and normal workload as separate states. An active or expected-to-play report never becomes a normal-workload assertion.
- Convert reporting to structured, subject-bound evidence with publication and capture times. Unqualified, future, stale, conflicting, or unresolved evidence fails closed.
- Model touchdown opportunity as context-specific scoring chances with hierarchical shrinkage. TD debt remains a diagnostic because conversion residual persistence has not been established.
- Preserve the existing simulator TD distribution for the live challenger until qualified pre-2026 opportunity-context training and projected live event contexts are available. The current xTD adapter labels aggregate simulator expectations as diagnostics.
- Use model/market disagreement only as research context. Monte Carlo standard error excludes model, role, parameter, and market-state uncertainty and cannot justify a high-confidence label.

## Source constraints

- nflverse play-by-play is the principal reproducible football history source.
- nflverse participation data from 2023 onward is published after the postseason; it cannot be described as live, same-season route evidence.
- Public NFL Next Gen Stats methodology motivates event-context modeling but does not provide LevLine raw tracking access.
- Current multi-book Props data remains Propline through the existing qualified live pipeline. Book reliability weights are descriptive only and are not outcome-fitted.

## References

- Gneiting, T. and Raftery, A. E. (2007), “Strictly Proper Scoring Rules, Prediction, and Estimation,” *JASA* 102(477), 359–378.
- nflverse/nflreadr, `load_participation` documentation and release-latency notes.
- NFL Next Gen Stats public methodology for Completion Probability and Expected Rushing Yards.

Commercial products including Venom, THE BLITZ, Unabated, Dimers, FantasyPoints, SIS, and PFF informed the product scan. No proprietary formula, arbitrary “due” bonus, or marketing claim is implemented.
