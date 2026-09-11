const DEFAULT_WEEK = 1

export function normalizeBase(base = '/') {
  const value = base || '/'
  return value === '/' ? '/' : `/${value.replace(/^\/+|\/+$/g, '')}/`
}

export function appPath(pathname, base = '/') {
  const normalizedBase = normalizeBase(base)
  if (normalizedBase === '/') return pathname || '/'
  if (!pathname?.startsWith(normalizedBase)) return '/'
  return `/${pathname.slice(normalizedBase.length).replace(/^\/+/, '')}`
}

export function parseRoute(pathname, base = '/') {
  const path = appPath(pathname, base).replace(/\/+$/g, '') || '/'
  let match = path.match(/^\/week\/(\d+)$/)
  if (match) return { name: 'week', week: Number(match[1]) }
  match = path.match(/^\/game\/([^/]+)$/)
  if (match) return { name: 'game', gameId: decodeURIComponent(match[1]) }
  match = path.match(/^\/team\/([A-Za-z0-9]+)$/)
  if (match) return { name: 'team', team: match[1].toUpperCase() }
  if (path === '/history') return { name: 'history' }
  if (path === '/methodology') return { name: 'methodology' }
  if (path === '/' || path === '') return { name: 'week', week: DEFAULT_WEEK }
  return { name: 'not-found', path }
}

export function routePath(route, base = '/') {
  const normalizedBase = normalizeBase(base)
  const prefix = normalizedBase === '/' ? '' : normalizedBase.slice(0, -1)
  switch (route.name) {
    case 'week': return `${prefix}/week/${route.week || DEFAULT_WEEK}`
    case 'game': return `${prefix}/game/${encodeURIComponent(route.gameId)}`
    case 'team': return `${prefix}/team/${encodeURIComponent(route.team)}`
    case 'history': return `${prefix}/history`
    case 'methodology': return `${prefix}/methodology`
    default: return `${prefix}/week/${DEFAULT_WEEK}`
  }
}

export function navigate(route, { base = '/', replace = false } = {}) {
  const path = routePath(route, base)
  const method = replace ? 'replaceState' : 'pushState'
  window.history[method]({ sundaySignalRoute: route }, '', path)
  window.dispatchEvent(new PopStateEvent('popstate'))
}
