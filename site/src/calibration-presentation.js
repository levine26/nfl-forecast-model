const TARGET_MODEL = 'Final Ensemble'

function parseCsvRow(line) {
  const cells = []
  let cell = ''
  let quoted = false
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i]
    if (quoted) {
      if (char === '"' && line[i + 1] === '"') { cell += '"'; i += 1 }
      else if (char === '"') quoted = false
      else cell += char
    } else if (char === '"') quoted = true
    else if (char === ',') { cells.push(cell); cell = '' }
    else cell += char
  }
  cells.push(cell)
  return cells
}

function encodeCsvCell(value) {
  const text = String(value ?? '')
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text
}

function encodeCsvRow(cells) {
  return cells.map(encodeCsvCell).join(',')
}

export function polishCalibrationCsv(text) {
  const lines = String(text || '').trim().split(/\r?\n/).filter(Boolean)
  if (!lines.length) return text

  const header = parseCsvRow(lines[0])
  const modelIndex = header.indexOf('model')
  const observedIndex = header.indexOf('observed_home_win')
  if (modelIndex < 0 || observedIndex < 0) return text

  const rows = lines.slice(1).map(parseCsvRow).filter(row => row[modelIndex] === TARGET_MODEL)
  if (!rows.length) return text

  const polished = rows.map(row => {
    const copy = [...row]
    const observed = Number(copy[observedIndex])
    if (Number.isFinite(observed)) copy[observedIndex] = `${(observed * 100).toFixed(1)}%`
    return copy
  })

  return [header, ...polished].map(encodeCsvRow).join('\n') + '\n'
}

function isCalibrationRequest(input) {
  const url = typeof input === 'string' ? input : input?.url || ''
  return /(?:^|\/)data\/calibration\.csv(?:[?#]|$)/.test(String(url))
}

export function installCalibrationPresentationAdapter() {
  if (typeof window === 'undefined' || window.__sundaySignalCalibrationAdapterInstalled) return
  window.__sundaySignalCalibrationAdapterInstalled = true
  const nativeFetch = window.fetch.bind(window)

  window.fetch = async (input, init) => {
    const response = await nativeFetch(input, init)
    if (!response.ok || !isCalibrationRequest(input)) return response

    try {
      const polished = polishCalibrationCsv(await response.clone().text())
      const headers = new Headers(response.headers)
      headers.delete('content-length')
      headers.delete('content-encoding')
      return new Response(polished, {
        status: response.status,
        statusText: response.statusText,
        headers,
      })
    } catch {
      return response
    }
  }
}
