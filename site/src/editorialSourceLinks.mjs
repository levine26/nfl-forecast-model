/** Display only attribution links that identify an original publisher report.
 *
 * This intentionally does not claim that the article resolves, that a publisher
 * is independent, or that the article supports the surrounding editorial claim.
 * That requires separate server-side retrieval and fact-to-passage evidence.
 */
const DIRECT = [
  [/^(?:www\.)?nfl\.com$/, /^\/news\/[^/]+/],
  [/^(?:www\.)?espn\.com$/, /^\/nfl\/story\/_\/id\/\d+/],
  [/^(?:www\.)?cbssports\.com$/, /^\/nfl\/news\/[^/]+/],
  [/^(?:www\.)?apnews\.com$/, /^\/article\/[^/]+/],
  [/^(?:www\.)?foxsports\.com$/, /^\/stories\/nfl\/[^/]+/],
  [/^(?:www\.)?nbcsports\.com$/, /^\/nfl\/news\/[^/]+/],
  [/^(?:www\.)?sports\.yahoo\.com$/, /^\/(?:articles\/|nfl\/(?:article|news)\/)[^/]+/],
  [/^(?:www\.)?(?:theathletic|nytimes)\.com$/, /^\/(?:athletic\/|article\/|interactive\/|2026\/)[^/]+/],
  [/^(?:www\.)?si\.com$/, /^\/nfl\/[^/]+/],
]
const TEAM_HOSTS = new Set([
  'arizonacardinals.com','atlantafalcons.com','baltimoreravens.com','buffalobills.com',
  'panthers.com','chicagobears.com','bengals.com','clevelandbrowns.com',
  'dallascowboys.com','denverbroncos.com','detroitlions.com','packers.com',
  'houstontexans.com','colts.com','jaguars.com','chiefs.com','therams.com',
  'chargers.com','raiders.com','miamidolphins.com','vikings.com','patriots.com',
  'neworleanssaints.com','giants.com','newyorkjets.com','philadelphiaeagles.com',
  'steelers.com','seahawks.com','49ers.com','buccaneers.com','titansonline.com',
  'tennesseetitans.com','commanders.com',
])

function direct(url) {
  try {
    const u = new URL(url)
    if (u.protocol !== 'https:') return null
    const host = u.hostname.toLowerCase()
    if (DIRECT.some(([h,p]) => h.test(host) && p.test(u.pathname))) return u.href
    const teamHost = host.replace(/^www\./, '')
    if (TEAM_HOSTS.has(teamHost) && /^\/news\/[^/]+/.test(u.pathname)) return u.href
    return null
  } catch { return null }
}

export function canonicalReportLink(raw) {
  try {
    const u = new URL(String(raw || ''))
    const host = u.hostname.toLowerCase()
    if (host === 'bing.com' || host === 'www.bing.com') {
      // Bing encodes original publisher URL as a query parameter. Do not link
      // to MSN copies or redirect trackers masquerading as independent sources.
      const target = u.searchParams.get('url')
      return target ? direct(target) : null
    }
    if (host === 'news.google.com' || host.endsWith('.news.google.com')) return null
    return direct(u.href)
  } catch { return null }
}
