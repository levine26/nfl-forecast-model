import {canonicalReportLink} from './editorialSourceLinks.mjs'

/**
 * Visible HUMAN Read authority requires independent full-slate acceptance.
 * Provider-written prose and direct URL shapes are NOT article or claim proof.
 * The canonical production audit is generated separately from provider input.
 * Missing/stale audits fail closed; model forecasts remain visible.
 */
export function hasPublishedHumanRead(preview, acceptance, expectedGames) {
  if (!acceptance || typeof acceptance !== 'object' || !Number.isInteger(expectedGames) || expectedGames <= 0) return false
  if (acceptance.status !== 'healthy' || acceptance.article_resolution_verified !== true || acceptance.claim_support_verified !== true) return false
  if (acceptance.games_expected !== expectedGames || acceptance.games_with_structurally_eligible_human_reads !== expectedGames || acceptance.games_rejected !== 0) return false
  if (acceptance.issues && Object.keys(acceptance.issues).length > 0) return false
  if (!preview || typeof preview !== 'object') return false
  const voice = preview.editorial_voice || {}
  if (voice.copilot_researched !== true || voice.two_paragraph_contract !== true) return false
  if (typeof preview.headline !== 'string' || !preview.headline.trim()) return false
  const paragraphs = preview.paragraphs
  if (!Array.isArray(paragraphs) || paragraphs.length !== 2 ||
      !paragraphs.every(p=>typeof p === 'string' && p.trim())) return false

  const sources = preview.reported_sources || []
  if (!Array.isArray(sources)) return false
  const independent = new Set()
  for (const source of sources) {
    if (!source || typeof source !== 'object') continue
    const direct = canonicalReportLink(source.source_url || source.url)
    if (!direct) continue
    try {
      const host = new URL(direct).hostname.toLowerCase().replace(/^www\./, '')
      independent.add(host === 'sports.yahoo.com' ? 'yahoo.com' : host)
    } catch { /* No synthetic publisher identity for a bad URL. */ }
  }
  return independent.size >= 2
}
