import React, { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import './forecast-help.css'

const EXPLANATIONS = [
  {
    term: 'Win probability',
    text: 'LevLine’s estimate of how often the listed team would win in comparable games. A 64% forecast means roughly 64 wins out of 100 — not a guarantee.',
  },
  {
    term: 'LevLine fair spread',
    text: 'The point spread that roughly matches LevLine’s win forecast. “KC -3.5” means LevLine sees Kansas City as about a 3.5-point favorite.',
  },
  {
    term: 'Sportsbook spread',
    text: 'The current consensus market line. This is shown so you can compare LevLine’s view with the betting market’s view.',
  },
  {
    term: 'Edge vs market',
    text: 'The gap between LevLine’s win probability and the market-implied win probability. Example: 64% vs 59% = a +5 percentage-point edge.',
  },
  {
    term: 'Model score estimate',
    text: 'An approximate score that is consistent with the forecast. It is a useful translation of the model, not an exact-score prediction.',
  },
  {
    term: 'Forecast tier',
    text: 'A simple strength label based on the published win probability: Watch, Lean, Signal, or Strong signal. It is shorthand, not a second forecast.',
  },
  {
    term: 'Model agreement',
    text: 'How closely LevLine’s internal components agree with one another. Higher agreement means the supporting views are more closely aligned.',
  },
  {
    term: 'Since last forecast',
    text: 'How the published forecast has moved since the previous update. This shows direction and size of movement, not the cause of the move.',
  },
]

export default function ForecastHelp() {
  const [open, setOpen] = useState(false)
  const closeRef = useRef(null)

  useEffect(() => {
    const listeners = new Map()
    const bind = () => {
      for (const button of document.querySelectorAll('.ss-clarity-info')) {
        if (listeners.has(button)) continue
        const handler = event => {
          event.preventDefault()
          event.stopPropagation()
          setOpen(true)
        }
        button.addEventListener('click', handler)
        button.setAttribute('aria-haspopup', 'dialog')
        button.setAttribute('aria-controls', 'ss-forecast-help-dialog')
        button.setAttribute('aria-expanded', 'false')
        listeners.set(button, handler)
      }
      for (const [button, handler] of listeners) {
        if (button.isConnected) continue
        button.removeEventListener('click', handler)
        listeners.delete(button)
      }
    }

    bind()
    const observer = new MutationObserver(bind)
    observer.observe(document.getElementById('root') || document.body, { childList: true, subtree: true })
    return () => {
      observer.disconnect()
      for (const [button, handler] of listeners) button.removeEventListener('click', handler)
    }
  }, [])

  useEffect(() => {
    for (const button of document.querySelectorAll('.ss-clarity-info')) {
      button.setAttribute('aria-expanded', open ? 'true' : 'false')
    }
    if (!open) return undefined

    const previouslyFocused = document.activeElement
    const previousOverflow = document.body.style.overflow
    const onKeyDown = event => {
      if (event.key === 'Escape') setOpen(false)
    }

    document.body.style.overflow = 'hidden'
    document.addEventListener('keydown', onKeyDown)
    const frame = requestAnimationFrame(() => closeRef.current?.focus())

    return () => {
      cancelAnimationFrame(frame)
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', onKeyDown)
      previouslyFocused?.focus?.()
    }
  }, [open])

  if (!open || typeof document === 'undefined') return null

  return createPortal(
    <div
      className="ss-forecast-help-backdrop"
      role="presentation"
      onMouseDown={event => {
        if (event.target === event.currentTarget) setOpen(false)
      }}
    >
      <section
        id="ss-forecast-help-dialog"
        className="ss-forecast-help-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ss-forecast-help-title"
        aria-describedby="ss-forecast-help-intro"
      >
        <button ref={closeRef} className="ss-forecast-help-close" type="button" onClick={() => setOpen(false)} aria-label="Close forecast guide">×</button>

        <header className="ss-forecast-help-header">
          <span>HOW TO READ THIS FORECAST</span>
          <h2 id="ss-forecast-help-title">The 30-second version</h2>
          <p id="ss-forecast-help-intro">Start with the pick and win probability. Then compare LevLine’s fair spread with the sportsbook spread. The edge, tier, and agreement numbers tell you how different — and how internally consistent — the forecast is.</p>
        </header>

        <div className="ss-forecast-help-steps" aria-label="Three steps for reading a LevLine forecast">
          <article><b>1</b><div><strong>Who does LevLine pick?</strong><p>Look at the team and win probability first. That is the core forecast.</p></div></article>
          <article><b>2</b><div><strong>How does LevLine compare with the market?</strong><p>Compare the fair spread and sportsbook spread, then check Edge vs Market.</p></div></article>
          <article><b>3</b><div><strong>How strong is the signal?</strong><p>Use Forecast Tier and Model Agreement as supporting context — not separate predictions.</p></div></article>
        </div>

        <div className="ss-forecast-help-example">
          <span>SIMPLE EXAMPLE</span>
          <p>If LevLine says <b>Team A 64%</b> and the market implies <b>59%</b>, LevLine has a <b>+5 percentage-point edge</b> on Team A. That means LevLine is more confident than the market — it does not mean the result is certain.</p>
        </div>

        <div className="ss-forecast-help-glossary">
          {EXPLANATIONS.map(item => <article key={item.term}><strong>{item.term}</strong><p>{item.text}</p></article>)}
        </div>

        <footer className="ss-forecast-help-footer">
          <div><b>LIVE FORECAST</b><span>Can still update before lock.</span></div>
          <div><b>LOCKED / FINAL PREGAME</b><span>The official pregame forecast preserved for grading.</span></div>
          <div><b>FINAL</b><span>The game has been graded against that preserved forecast.</span></div>
        </footer>
      </section>
    </div>,
    document.body,
  )
}
