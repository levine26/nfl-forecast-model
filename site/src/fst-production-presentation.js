const FST_FORMULA = 'Frozen F-ST-01: logit(final) = -0.06954 + 1.19391 × logit(MARKET) − 0.19343 × logit(F-ST NESTED PURE).'

function replaceExactText(root, from, to) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const nodes = []
  while (walker.nextNode()) nodes.push(walker.currentNode)
  for (const node of nodes) {
    if (node.nodeValue?.trim() === from) node.nodeValue = node.nodeValue.replace(from, to)
  }
}

function patchMethodology(root) {
  replaceExactText(root, '75% PURE + 25% MARKET', 'Frozen F-ST-01 market + nested-PURE logit stack')
  replaceExactText(
    root,
    'Build the football probability first. Let the market contribute information without taking over. Lock the answer before kickoff. Then grade the probability honestly.',
    'Build the leakage-safe nested football probability first. Combine it with the current vig-free market through frozen F-ST-01. Lock that exact probability before kickoff, preserve the legacy counterfactual, then grade both honestly.',
  )
  replaceExactText(
    root,
    '2026 results are for measurement, not for choosing the architecture. Any upgrade has to prove itself on earlier held-out data first.',
    'Completed 2026 games may update ordinary rolling pregame football state, but 2026 outcomes do not refit or select F-ST-01 coefficients or architecture. Any successor requires a new registered candidate.',
  )
  replaceExactText(
    root,
    'PURE is the football-only forecast. LevLine blends 75% PURE with 25% market signal. Big disagreements stay visible.',
    'Official LevLine uses frozen F-ST-01: current vig-free MARKET and a separately generated nested PURE enter a fixed two-input logit model. If MARKET is unavailable, that game falls back to the exact legacy 75/25 rule.',
  )
  replaceExactText(root, 'LEVLINE F-ST', 'LEVLINE')
}

function patchConsensus(root) {
  for (const block of root.querySelectorAll('.vnext-consensus-output')) {
    if (block.dataset.fstPresentation === '1') continue
    const spans = block.querySelectorAll(':scope > span')
    if (spans.length < 3) continue
    const legacyValue = spans[0].querySelector('b')?.textContent || '—'
    const marketValue = spans[1].querySelector('b')?.textContent || '—'
    const finalValue = spans[2].querySelector('b')?.textContent || '—'
    block.innerHTML = `
      <span><small>LEGACY PURE</small><b>${legacyValue}</b><em>preserved counterfactual input</em></span>
      <i>compare</i>
      <span><small>MARKET</small><b>${marketValue}</b><em>vig-free F-ST input</em></span>
      <i>→</i>
      <span class="final"><small>LEVLINE</small><b>${finalValue}</b><em>official published probability</em></span>
    `
    block.dataset.fstPresentation = '1'
    const section = block.closest('.vnext-consensus')
    const note = section?.querySelector('.vnext-consensus-note')
    if (note) note.textContent = `${FST_FORMULA} The legacy PURE shown above is retained for accountability; it is not the F-ST nested PURE input.`
  }
}

function patchLegacyDiagnosticLabels(root) {
  for (const stat of root.querySelectorAll('.vnext-advanced-grid .pub-stat')) {
    const label = stat.querySelector('span')
    if (label?.textContent?.trim() === 'PURE') label.textContent = 'Legacy PURE'
  }
}

function pickTeamFromText(text) {
  const match = String(text || '').trim().match(/^([A-Z]{2,3})\b/)
  return match?.[1] || null
}

function scoreWinnerFromText(text) {
  const match = String(text || '').trim().match(/^([A-Z]{2,3})\s+(-?\d+(?:\.\d+)?)\s+[–-]\s+([A-Z]{2,3})\s+(-?\d+(?:\.\d+)?)$/)
  if (!match) return null
  const first = Number(match[2])
  const second = Number(match[4])
  if (!Number.isFinite(first) || !Number.isFinite(second) || Math.abs(first - second) < 0.05) return null
  return first > second ? match[1] : match[3]
}

function patchWinnerMarginConsistency(root) {
  for (const card of root.querySelectorAll('.vnext-game-card')) {
    const pick = pickTeamFromText(card.querySelector('.pub-pick strong')?.textContent)
    const scoreNode = card.querySelector('.pub-pick small')
    if (!pick || !scoreNode) continue
    if (!scoreNode.dataset.originalMarginScore) scoreNode.dataset.originalMarginScore = scoreNode.textContent?.trim() || ''
    const marginWinner = scoreWinnerFromText(scoreNode.dataset.originalMarginScore)
    if (!marginWinner || marginWinner === pick) continue
    const replacement = `Official pick ${pick} · separate margin model favors ${marginWinner}`
    if (scoreNode.textContent !== replacement) scoreNode.textContent = replacement
    scoreNode.dataset.winnerMarginSplit = '1'
  }

  for (const verdict of root.querySelectorAll('.vnext-verdict')) {
    const official = verdict.querySelector(':scope > div:first-child > strong')
    const marginBlock = verdict.querySelector(':scope > div:last-child')
    const scoreNode = marginBlock?.querySelector('b')
    const detailNode = marginBlock?.querySelector('small')
    const pick = pickTeamFromText(official?.textContent)
    if (!pick || !scoreNode) continue
    if (!scoreNode.dataset.originalMarginScore) scoreNode.dataset.originalMarginScore = scoreNode.textContent?.trim() || ''
    const marginWinner = scoreWinnerFromText(scoreNode.dataset.originalMarginScore)
    if (!marginWinner || marginWinner === pick) continue
    const replacement = `Separate margin model favors ${marginWinner}`
    if (scoreNode.textContent !== replacement) scoreNode.textContent = replacement
    if (detailNode && !detailNode.dataset.marginSplitLabeled) {
      detailNode.textContent = `Winner probability and margin projection disagree · ${detailNode.textContent}`
      detailNode.dataset.marginSplitLabeled = '1'
    }
    verdict.dataset.winnerMarginSplit = '1'
  }

  for (const quick of root.querySelectorAll('.vnext-quick')) {
    const cells = [...quick.querySelectorAll('.vnext-quick-grid > div')]
    const projectedScore = cells.find(cell => cell.querySelector('span')?.textContent?.trim() === 'Projected score')
    const modelSpread = cells.find(cell => cell.querySelector('span')?.textContent?.trim() === 'Model spread')
    if (projectedScore) projectedScore.querySelector('span').textContent = 'Margin-model score'
    if (modelSpread) modelSpread.querySelector('span').textContent = 'Margin-model spread'

    const split = quick.closest('.vnext-modal')?.querySelector('.vnext-verdict')?.dataset.winnerMarginSplit === '1'
    const existing = quick.querySelector('.fst-margin-split-note')
    if (split && !existing) {
      const note = document.createElement('p')
      note.className = 'vnext-consensus-note fst-margin-split-note'
      note.textContent = 'Winner probability and margin projection are separate models and disagree on this game. The official Sunday Signal pick is the LevLine win probability shown above.'
      quick.appendChild(note)
    }
  }
}

function patch(root = document.body) {
  patchMethodology(root)
  patchConsensus(root)
  patchLegacyDiagnosticLabels(root)
  patchWinnerMarginConsistency(root)
}

export function installFstProductionPresentationAdapter() {
  if (typeof window === 'undefined' || window.__fstProductionPresentationInstalled) return
  window.__fstProductionPresentationInstalled = true
  const run = () => patch(document.body)
  const observer = new MutationObserver(run)
  observer.observe(document.documentElement, { childList:true, subtree:true })
  queueMicrotask(run)
}
