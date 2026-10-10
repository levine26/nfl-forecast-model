import {canonicalReportLink} from './editorialSourceLinks.mjs'

/**
 * A HUMAN Read must be accepted by the provider publication pipeline.
 * Headline+paragraph existence alone is NOT an editorial acceptance receipt.
 * This checks visible attribution structure, not article-content or claim support.
 */
export function hasPublishedHumanRead(preview) {
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
