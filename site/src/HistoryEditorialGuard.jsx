import React, { useLayoutEffect } from 'react'

import { canUseCurrentPreviewForReceipt } from './historyEditorialSafety.js'

const BASE = import.meta.env.BASE_URL
const FALLBACK_ID = 'ss-history-editorial-safety-fallback'

function receiptGameId() {
  const parts = window.location.hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  return parts[0] === 'receipt' && parts[1] ? decodeURIComponent(parts.slice(1).join('/')) : null
}

function signalSection() {
  return [...document.querySelectorAll('.ss-exp-receipt-analysis')].find(section =>
    section.querySelector(':scope > span')?.textContent?.trim() === 'THE SIGNAL'
  ) || null
}

function removeFallback() {
  document.getElementById(FALLBACK_ID)?.remove()
}

function showSignal(section) {
  if (section) section.hidden = false
  removeFallback()
}

function suppressMutableSignal(section) {
  if (!section) return
  // ReceiptPage already renders a fail-closed notice when no preview exists.
  // Only replace a section that actually contains preview prose.
  if (!section.querySelector(':scope > h2')) {
    showSignal(section)
    return
  }

  section.hidden = true
  let fallback = document.getElementById(FALLBACK_ID)
  if (!fallback) {
    fallback = document.createElement('section')
    fallback.id = FALLBACK_ID
    fallback.className = 'ss-exp-receipt-analysis'
    const label = document.createElement('span')
    label.textContent = 'THE SIGNAL'
    const empty = document.createElement('div')
    empty.className = 'ss-exp-empty'
    const title = document.createElement('b')
    title.textContent = 'The immutable forecast receipt is available.'
    const detail = document.createElement('span')
    detail.textContent = 'Archived pregame editorial is not published for this game artifact. Postgame analysis remains separate below.'
    empty.append(title, detail)
    fallback.append(label, empty)
    section.insertAdjacentElement('afterend', fallback)
  }
}

async function fetchJSON(name, fallback) {
  try {
    const response = await fetch(`${BASE}data/${name}`, { cache: 'no-store' })
    return response.ok ? await response.json() : fallback
  } catch {
    return fallback
  }
}

export default function HistoryEditorialGuard() {
  useLayoutEffect(() => {
    let disposed = false
    let loaded = false
    let forecasts = { games: [] }
    let previews = {}

    const enforce = () => {
      const gameId = receiptGameId()
      if (!gameId) {
        showSignal(signalSection())
        return
      }

      const section = signalSection()
      if (!section) return

      const currentGame = loaded && Array.isArray(forecasts?.games)
        ? forecasts.games.find(game => String(game?.game_id || '') === gameId)
        : null
      const permitted = loaded && canUseCurrentPreviewForReceipt({
        gameId,
        currentGame,
        preview: previews?.[gameId],
      })

      if (permitted) showSignal(section)
      else suppressMutableSignal(section)
    }

    // Install the guard once for the whole SPA session. Route changes are hash
    // changes, so every historical receipt is protected even when opened after
    // the initial app mount.
    enforce()
    const observer = new MutationObserver(enforce)
    observer.observe(document.getElementById('root') || document.body, { childList: true, subtree: true })
    window.addEventListener('hashchange', enforce)

    Promise.all([
      fetchJSON('public_forecasts.json', { games: [] }),
      fetchJSON('game_previews.json', {}),
    ]).then(([nextForecasts, nextPreviews]) => {
      if (disposed) return
      forecasts = nextForecasts
      previews = nextPreviews
      loaded = true
      enforce()
    })

    return () => {
      disposed = true
      observer.disconnect()
      window.removeEventListener('hashchange', enforce)
      showSignal(signalSection())
    }
  }, [])

  return null
}
