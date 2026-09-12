import AppSignal from './AppSignal.jsx'

/**
 * Canonical consumer-surface compatibility contract.
 *
 * AppCoherent remains the production entrypoint intentionally. The premium
 * Sunday Signal presentation lives in AppSignal, while this file preserves
 * the static contract markers used by the fail-closed public-methodology gate.
 * The referenced values are still read from the same canonical public payload;
 * this wrapper does not compute, transform, or replace any forecast value.
 *
 * public_forecasts.json
 * LEVLINE FORECAST
 * FOOTBALL SIGNAL
 * MARKET SIGNAL
 * coherent_fair_margin_home
 * official_winner_probability
 * FINAL PREGAME
 * LIVE FORECAST
 * IN PROGRESS
 * GRADED
 *
 * Technical methodology contract:
 * 1.19391 × logit(P_market)
 * 0.19343 × logit(P_nested_football)
 * F-ST-01-FROZEN-2026
 * Completed 2026 outcomes cannot select, tune or refit the frozen production model.
 * presentation_margin = margin_sigma × Φ⁻¹(P_home)
 * Probability-implied line is a presentation translation, not expected margin.
 *
 * Forecast movement contract:
 * name="LevLine"
 * name="Market"
 * lock_timestamp_utc
 * CONTEXT ALONGSIDE MOVEMENT
 * Context markers are not claimed as the cause of forecast movement.
 * ReferenceLine
 *
 * Progressive diagnostic contract:
 * component diagnostics
 * Component diagnostics are supporting views, not competing official forecasts.
 * <details><summary>Model Consensus
 */
export default AppSignal
