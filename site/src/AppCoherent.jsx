import { useEffect, useState } from 'react'
import AppSignal from './AppSignal.jsx'
import SignalEnhancements from './SignalEnhancements.jsx'
import ForecastClarity from './ForecastClarity.jsx'
import ForecastHelp from './ForecastHelp.jsx'
import ExperienceLayer from './ExperienceLayer.jsx'
import ExperienceDomFixes from './ExperienceDomFixes.jsx'
import HistoryReceiptDetails from './HistoryReceiptDetails.jsx'
import HistoryEditorialGuard from './HistoryEditorialGuard.jsx'
import BetTracker from './BetTracker.jsx'
import PropsResearchBeta from './PropsResearchBeta.jsx'
import './signal-polish.css'

/**
 * Canonical consumer-surface compatibility contract.
 *
 * AppCoherent remains the production entrypoint intentionally. The premium
 * Sunday Signal presentation lives in AppSignal, while the adjacent helpers add
 * presentation-only affordances around the same canonical game data. The Props
 * Research Beta is isolated behind its own hash namespace and consumes only the
 * separate Props public contract; it does not recompute or mutate winner-model
 * forecasts, picks, locks, grading, governance, or probabilities.
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
function onPropsRoute() {
  const raw = window.location.hash.replace(/^#\/?/, '')
  return raw === 'props' || raw.startsWith('props/')
}

export default function AppCoherent() {
  const [propsRoute, setPropsRoute] = useState(onPropsRoute)
  useEffect(() => {
    const update = () => setPropsRoute(onPropsRoute())
    window.addEventListener('hashchange', update)
    return () => window.removeEventListener('hashchange', update)
  }, [])
  if (propsRoute) return <PropsResearchBeta/>
  return <>
    <AppSignal/>
    <SignalEnhancements/>
    <ForecastClarity/>
    <ForecastHelp/>
    <ExperienceDomFixes/>
    <ExperienceLayer/>
    <HistoryReceiptDetails/>
    <HistoryEditorialGuard/>
    <BetTracker/>
    <PropsResearchBeta/>
  </>
}
