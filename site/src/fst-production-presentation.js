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
      <span class="final"><small>LEVLINE F-ST</small><b>${finalValue}</b><em>official published probability</em></span>
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

function patch(root = document.body) {
  patchMethodology(root)
  patchConsensus(root)
  patchLegacyDiagnosticLabels(root)
}

export function installFstProductionPresentationAdapter() {
  if (typeof window === 'undefined' || window.__fstProductionPresentationInstalled) return
  window.__fstProductionPresentationInstalled = true
  const run = () => patch(document.body)
  const observer = new MutationObserver(run)
  observer.observe(document.documentElement, { childList:true, subtree:true })
  queueMicrotask(run)
}
