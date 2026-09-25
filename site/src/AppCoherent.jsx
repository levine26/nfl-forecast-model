import AppSignal from './AppSignal.jsx'
import SignalEnhancements from './SignalEnhancements.jsx'
import ForecastClarity from './ForecastClarity.jsx'
import ForecastHelp from './ForecastHelp.jsx'
import ExperienceLayer from './ExperienceLayer.jsx'
import ExperienceDomFixes from './ExperienceDomFixes.jsx'
import HistoryReceiptDetails from './HistoryReceiptDetails.jsx'
import HistoryEditorialGuard from './HistoryEditorialGuard.jsx'
import BetTracker from './BetTracker.jsx'
import AtsValueLayer from './AtsValueLayer.jsx'
import './signal-polish.css'

/**
 * Canonical consumer-surface compatibility contract.
 *
 * AppCoherent remains the production entrypoint intentionally. The premium
 * Sunday Signal presentation lives in AppSignal, while the adjacent helpers add
 * presentation-only affordances around the same canonical game data.
 *
 * Props was intentionally removed from the production surface in the September
 * 2026 reset. Any future player-prop product must re-enter through a separately
 * validated research program rather than being mounted into Sunday Signal by
 * default.
 *
 * public_forecasts.json
 * LEVLINE FORECAST
 * FOOTBALL SIGNAL
 * MARKET SIGNAL
 * coherent_fair_margin_home
 * official_winner_probability
 * ats_model_margin_home
 * ats_market_margin_home
 * ats_pick_team
 * ats_pick_market_spread
 * Winner and ATS spread value are separate forecasts.
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
 * ATS value uses the independent expected-margin forecast versus the sportsbook spread.
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
export default function AppCoherent() {
  return <>
    <AppSignal/>
    <SignalEnhancements/>
    <ForecastClarity/>
    <AtsValueLayer/>
    <ForecastHelp/>
    <ExperienceDomFixes/>
    <ExperienceLayer/>
    <HistoryReceiptDetails/>
    <HistoryEditorialGuard/>
    <BetTracker/>
  </>
}
