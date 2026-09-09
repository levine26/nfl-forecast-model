import React, { useEffect, useMemo, useState } from 'react'
import { Area, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './publication.css'
import './publication-vnext.css'

const BASE = import.meta.env.BASE_URL

const TEAM = {
  ARI:['Arizona Cardinals','#97233F','ari'], ATL:['Atlanta Falcons','#A71930','atl'], BAL:['Baltimore Ravens','#241773','bal'], BUF:['Buffalo Bills','#00338D','buf'],
  CAR:['Carolina Panthers','#0085CA','car'], CHI:['Chicago Bears','#0B162A','chi'], CIN:['Cincinnati Bengals','#FB4F14','cin'], CLE:['Cleveland Browns','#311D00','cle'],
  DAL:['Dallas Cowboys','#003594','dal'], DEN:['Denver Broncos','#FB4F14','den'], DET:['Detroit Lions','#0076B6','det'], GB:['Green Bay Packers','#203731','gb'],
  HOU:['Houston Texans','#03202F','hou'], IND:['Indianapolis Colts','#002C5F','ind'], JAC:['Jacksonville Jaguars','#006778','jax'], JAX:['Jacksonville Jaguars','#006778','jax'],
  KC:['Kansas City Chiefs','#E31837','kc'], LAC:['Los Angeles Chargers','#0080C6','lac'], LA:['Los Angeles Rams','#003594','lar'], LV:['Las Vegas Raiders','#A5ACAF','lv'],
  MIA:['Miami Dolphins','#008E97','mia'], MIN:['Minnesota Vikings','#4F2683','min'], NE:['New England Patriots','#002244','ne'], NO:['New Orleans Saints','#D3BC8D','no'],
  NYG:['New York Giants','#0B2265','nyg'], NYJ:['New York Jets','#125740','nyj'], PHI:['Philadelphia Eagles','#004C54','phi'], PIT:['Pittsburgh Steelers','#FFB612','pit'],
  SEA:['Seattle Seahawks','#002244','sea'], SF:['San Francisco 49ers','#AA0000','sf'], TB:['Tampa Bay Buccaneers','#D50A0A','tb'], TEN:['Tennessee Titans','#0C2340','ten'],
  WAS:['Washington Commanders','#5A1414','wsh'],
}

const teamName = team => TEAM[team]?.[0] || team || '—'
const teamColor = team => TEAM[team]?.[1] || '#64748b'
const teamLogo = team => `https://a.espncdn.com/i/teamlogos/nfl/500/${TEAM[team]?.[2] || String(team || '').toLowerCase()}.png`
const num = value => {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}
const pct = (value, digits = 1) => num(value) == null ? '—' : `${(num(value) * 100).toFixed(digits)}%`
const signed = value => num(value) == null ? '—' : `${num(value) > 0 ? '+' : ''}${num(value).toFixed(1)}`
const one = value => num(value) == null ? '—' : num(value).toFixed(1)

function parseCSV(text) {
  const rows = []
  let row = [], cell = '', quoted = false
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i]
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i += 1 }
      else if (c === '"') quoted = false
      else cell += c
    } else if (c === '"') quoted = true
    else if (c === ',') { row.push(cell); cell = '' }
    else if (c === '\n') { row.push(cell); rows.push(row); row = []; cell = '' }
    else if (c !== '\r') cell += c
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row) }
  const headers = rows.shift() || []
  return rows.filter(r => r.some(Boolean)).map(r => Object.fromEntries(headers.map((key, i) => [key, r[i] ?? ''])))
}

async function fetchCSV(path) {
  try {
    const response = await fetch(`${BASE}data/${path}`, { cache:'no-store' })
    return response.ok ? parseCSV(await response.text()) : []
  } catch { return [] }
}
async function fetchJSON(path, fallback = {}) {
  try {
    const response = await fetch(`${BASE}data/${path}`, { cache:'no-store' })
    return response.ok ? await response.json() : fallback
  } catch { return fallback }
}

function easternKickoff(game) {
  if (!game?.gameday) return null
  const [year, month, day] = game.gameday.split('-').map(Number)
  const [hour = 0, minute = 0] = (game.gametime || '00:00').split(':').map(Number)
  if (!year || !month || !day) return null
  const nominal = Date.UTC(year, month - 1, day, hour, minute)
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone:'America/New_York', year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', hourCycle:'h23',
  }).formatToParts(new Date(nominal))
  const shown = Object.fromEntries(parts.map(part => [part.type, part.value]))
  const rendered = Date.UTC(+shown.year, +shown.month - 1, +shown.day, +shown.hour, +shown.minute)
  return new Date(nominal - (rendered - nominal))
}
function kickoffText(game) {
  const kickoff = easternKickoff(game)
  if (!kickoff || Number.isNaN(kickoff.getTime())) return game?.gameday || 'TBD'
  return new Intl.DateTimeFormat('en-US', {
    weekday:'short', month:'short', day:'numeric', hour:'numeric', minute:'2-digit', timeZone:'America/Los_Angeles',
  }).format(kickoff)
}
function age(timestamp) {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '—'
  const minutes = Math.max(0, Math.round((Date.now() - date) / 60000))
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  return hours < 48 ? `${hours}h ago` : `${Math.round(hours / 24)}d ago`
}
function modelLine(margin, home, away) {
  const value = num(margin)
  if (value == null) return '—'
  if (Math.abs(value) < .05) return 'PK'
  return value > 0 ? `${home} -${Math.abs(value).toFixed(1)}` : `${away} -${Math.abs(value).toFixed(1)}`
}
function normalizeGame(game) {
  const homeP = num(game.final_home_prob)
  const pick = game.pick || (homeP >= .5 ? game.home_team : game.away_team)
  const pickP = homeP == null ? null : pick === game.home_team ? homeP : 1 - homeP
  const marketHomeP = num(game.market_home_prob)
  const marketPickP = marketHomeP == null ? null : pick === game.home_team ? marketHomeP : 1 - marketHomeP
  const margin = num(game.expected_margin)
  const market = num(game.spread_line)
  const pickEdge = margin == null || market == null ? null : pick === game.home_team ? margin - market : market - margin
  return { ...game, homeP, pick, pickP, marketHomeP, marketPickP, margin, market, pickEdge }
}
function pickProbability(game, homeProbability) {
  const value = num(homeProbability)
  if (value == null) return null
  return game.pick === game.home_team ? value : 1 - value
}
function probabilityAxisPosition(probability) {
  const p = num(probability)
  if (p == null) return null
  return Math.max(0, Math.min(100, ((p * 100) - 40) / 40 * 100))
}
function publicSourceIssues(sources) {
  const critical = new Set(['schedule','pbp','injuries','coaching','depth_charts','evidence','previews'])
  return Object.entries(sources || {}).filter(([key,value]) => critical.has(key) && value && typeof value === 'object' && ['degraded','failed','error'].includes(String(value.status || '').toLowerCase()))
}

function TeamMark({ team, size = 'md' }) {
  const [failed, setFailed] = useState(false)
  return <span className={`pub-team ${size}`} style={{ '--team':teamColor(team) }}>
    {!failed && <img src={teamLogo(team)} alt="" onError={() => setFailed(true)} />}
    {failed && <b>{team}</b>}
  </span>
}
function StateBadge({ game, locked }) {
  const kickoff = easternKickoff(game)
  const minutes = kickoff ? (kickoff - new Date()) / 60000 : null
  if (locked) return <span className="pub-state locked">🔒 OFFICIAL · LOCKED</span>
  if (minutes != null && minutes <= 120 && minutes > 0) return <span className="pub-state window">LOCK WINDOW</span>
  if (minutes != null && minutes <= 0) return <span className="pub-state started">STARTED</span>
  return <span className="pub-state current">CURRENT</span>
}
function Stat({ label, value, sub }) {
  return <div className="pub-stat"><span>{label}</span><b>{value}</b>{sub && <small>{sub}</small>}</div>
}

function Header({ tab, setTab, status, history, sources, week }) {
  const tabs = [['week','Forecasts'],['teams','Teams'],['ratings','Power'],['history','History'],['method','Method']]
  const locked = history.filter(row => row.lock_status === 'LOCKED')
  const graded = locked.filter(row => ['true','false'].includes(String(row.winner_correct).toLowerCase()))
  const wins = graded.filter(row => String(row.winner_correct).toLowerCase() === 'true').length
  const issues = publicSourceIssues(sources)
  return <>
    <header className="pub-header vnext-header">
      <button className="pub-brand" onClick={() => setTab('week')}>
        <img className="vnext-logo" src={`${BASE}brand/sunday-signal-icon.svg`} alt="Sunday Signal" />
        <span><b>SUNDAY SIGNAL</b><small>powered by LevLine</small></span>
      </button>
      <div className="vnext-header-meta">
        <span>2026 · WEEK {week || '—'}</span>
        <b>{graded.length ? `${wins}-${graded.length-wins} official` : 'Forward test live'}</b>
      </div>
    </header>
    <nav className="pub-nav vnext-nav">{tabs.map(([key,label]) => <button key={key} className={tab===key?'active':''} onClick={() => setTab(key)}>{label}</button>)}</nav>
    {issues.length ? <div className="vnext-source-alert"><b>Data note</b><span>{issues.map(([key]) => key.replaceAll('_',' ')).join(', ')} source health is degraded. Forecasts remain visible, but affected context should be read with caution.</span></div> : <div className="vnext-update-line"><span>Updated {age(status?.generated_utc || status?.prediction_timestamp_utc)}</span><i>•</i><span>LevLine current</span></div>}
  </>
}

function CompactHero({ games, history, status, onPreviousWeek }) {
  const week = Number(games[0]?.week || 0)
  const next = [...games].filter(g => easternKickoff(g) > new Date()).sort((a,b) => easternKickoff(a)-easternKickoff(b))[0]
  const strongest = [...games].sort((a,b) => (b.pickP||0)-(a.pickP||0))[0]
  const locked = history.filter(row => row.lock_status === 'LOCKED').length
  const previousExists = history.some(row => Number(row.week) === week - 1)
  return <section className="vnext-hero">
    <div className="vnext-hero-copy">
      <img src={`${BASE}brand/sunday-signal-lockup.svg`} alt="Sunday Signal — powered by LevLine" />
      <div className="vnext-week-nav">
        <button disabled={!previousExists} onClick={() => onPreviousWeek(week-1)}>← Week {Math.max(1,week-1)}</button>
        <b>2026 · WEEK {week || '—'}</b>
        <button disabled>Week {week ? week+1 : '—'} →</button>
      </div>
      <h1>Week {week || '—'} NFL Forecasts</h1>
      <p>LevLine probabilities, market edges, and matchup analysis for every game.</p>
    </div>
    <div className="pub-hero-stats vnext-hero-stats">
      <Stat label="Next kickoff" value={next ? `${next.away_team} @ ${next.home_team}` : 'Slate complete'} sub={next ? kickoffText(next) : ''} />
      <Stat label="Top signal" value={strongest ? `${strongest.pick} ${pct(strongest.pickP)}` : '—'} sub={strongest?.confidence || 'Current forecast'} />
      <Stat label="Official locks" value={`${locked}/${games.length || 0}`} sub="Immutable after lock" />
      <Stat label="Model run" value={age(status?.generated_utc)} sub="Latest published forecast" />
    </div>
  </section>
}

function MarketGap({ game, compact = false }) {
  const model = probabilityAxisPosition(game.pickP) ?? 25
  const market = probabilityAxisPosition(game.marketPickP)
  const gap = game.marketPickP == null || game.pickP == null ? null : (game.pickP-game.marketPickP)*100
  return <div className={`pub-gap vnext-gap ${compact?'compact':''}`}>
    <div className="pub-gap-head"><span>LEVLINE vs MARKET</span><b>{gap == null ? 'Market unavailable' : `${gap>=0?'+':''}${gap.toFixed(1)} percentage points`}</b></div>
    <div className="pub-gap-track">
      <i className="mid" />
      {market != null && <i className="market" style={{ left:`${market}%` }}><em>Market</em></i>}
      <i className="model" style={{ left:`${model}%` }}><em>LevLine</em></i>
    </div>
    <div className="pub-gap-scale"><span>40%</span><span>50</span><span>60</span><span>70</span><span>80%+</span></div>
  </div>
}

function GameCard({ game, preview, evidence, locked, onOpen, compact = false }) {
  const teaser = preview?.headline || preview?.paragraphs?.[0] || `${game.pick} is the current side.`
  return <button className={`pub-game-card vnext-game-card ${compact?'vnext-game-card-compact':''} ${locked?'is-locked':''}`} onClick={onOpen} style={{ '--away':teamColor(game.away_team), '--home':teamColor(game.home_team) }}>
    <div className="pub-card-top"><span>{kickoffText(game)}</span><StateBadge game={game} locked={locked} /></div>
    <div className="pub-matchup">
      <span><TeamMark team={game.away_team} /><b>{game.away_team}</b></span><em>@</em><span><TeamMark team={game.home_team} /><b>{game.home_team}</b></span>
    </div>
    <div className="pub-pick"><span>LEVLINE</span><strong>{game.pick} <b>{pct(game.pickP)}</b></strong><small>{game.projected_score || 'Central score pending'}</small></div>
    {!compact && <MarketGap game={game} compact />}
    <div className="vnext-line-strip"><span><small>LevLine</small><b>{modelLine(game.margin,game.home_team,game.away_team)}</b></span><i /><span><small>Market</small><b>{modelLine(game.market,game.home_team,game.away_team)}</b></span><i /><span className="edge"><small>Edge</small><b>{signed(game.pickEdge)}</b></span></div>
    <p>{teaser}</p>
    <div className="pub-card-foot"><span>{preview?.key_factors?.length || evidence?.length || 0} matchup signals</span><b>Open game file →</b></div>
  </button>
}

function Spotlight({ game, preview, onOpen }) {
  if (!game) return null
  const marketGap = game.marketPickP == null ? null : (game.pickP-game.marketPickP)*100
  return <section className="pub-spotlight vnext-spotlight" style={{ '--away':teamColor(game.away_team), '--home':teamColor(game.home_team) }}>
    <div className="pub-spot-copy"><span>SIGNAL OF THE WEEK</span><h2>{preview?.headline || `${game.pick} ${pct(game.pickP)}`}</h2><p>{preview?.paragraphs?.[0] || 'The strongest current probability on the slate.'}</p><button onClick={() => onOpen(game)}>Open the full case →</button></div>
    <div className="pub-spot-board">
      <div><TeamMark team={game.away_team} size="lg" /><b>{game.away_team}</b><em>@</em><TeamMark team={game.home_team} size="lg" /><b>{game.home_team}</b></div>
      <strong>{game.pick} {pct(game.pickP)}</strong>
      <small>{marketGap == null ? 'No market probability attached' : `${marketGap>=0?'+':''}${marketGap.toFixed(1)} percentage points vs market`}</small>
      <MarketGap game={game} compact />
    </div>
  </section>
}

function GamesToWatch({ games, previews, locked, onOpen }) {
  if (!games.length) return null
  return <section className="vnext-watch-section">
    <div className="pub-section-head"><div><span>GAMES TO WATCH</span><h2>Three matchups with something worth arguing about.</h2></div></div>
    <div className="vnext-watch-grid">{games.map(game => <GameCard key={game.game_id} game={game} preview={previews[game.game_id]} evidence={[]} locked={locked.has(game.game_id)} onOpen={()=>onOpen(game)} compact />)}</div>
  </section>
}

function WeekPage({ games, evidence, previews, history, status, setSelected, onPreviousWeek }) {
  const [sortMode,setSortMode] = useState('kickoff')
  const locked = new Set(history.filter(row => row.lock_status==='LOCKED').map(row => row.game_id))
  const editorialScore = game => {
    const preview = previews[game.game_id] || {}
    const items = evidence[game.game_id] || []
    const marketGap = Math.abs((game.pickP ?? .5) - (game.marketPickP ?? game.pickP ?? .5)) * 100
    const closeness = (1 - Math.min(1, Math.abs((game.pickP ?? .5) - .5) * 2)) * 4
    const spreadEdge = Math.min(12, Math.abs(game.pickEdge || 0)) * .35
    const sourceDepth = Math.min(5, items.length * .3 + (preview.key_factors?.length || 0) * .35)
    const storyText = [preview.headline, ...(preview.paragraphs || []), ...(preview.notebook || []).flatMap(item => [item.title,item.summary]), ...items.flatMap(item => [item.title,item.summary])].join(' ').toLowerCase()
    const eventBonus = /rivalry|australia|melbourne|international|first-ever|record|milestone|reunion|revenge|return|debut/.test(storyText) ? 8 : 0
    const peopleBonus = /quarterback|coach|coordinator|stafford|purdy|injury|questionable|returning/.test(storyText) ? 2.5 : 0
    return marketGap * 1.15 + closeness + spreadEdge + sourceDepth + eventBonus + peopleBonus
  }
  const spotlight = [...games].sort((a,b)=>editorialScore(b)-editorialScore(a))[0]
  const watch = useMemo(() => [...games].filter(g => g.game_id !== spotlight?.game_id).sort((a,b)=>editorialScore(b)-editorialScore(a)).slice(0,3), [games,spotlight?.game_id,evidence,previews])
  const sorted = useMemo(() => {
    const copy=[...games]
    if (sortMode==='strength') return copy.sort((a,b)=>(b.pickP||0)-(a.pickP||0))
    if (sortMode==='edge') return copy.sort((a,b)=>(b.pickEdge??-999)-(a.pickEdge??-999))
    if (sortMode==='close') return copy.sort((a,b)=>Math.abs((a.pickP||.5)-.5)-Math.abs((b.pickP||.5)-.5))
    return copy.sort((a,b)=>(easternKickoff(a)?.getTime()||0)-(easternKickoff(b)?.getTime()||0))
  },[games,sortMode])
  return <main className="pub-main">
    <CompactHero games={games} history={history} status={status} onPreviousWeek={onPreviousWeek} />
    <Spotlight game={spotlight} preview={previews[spotlight?.game_id]} onOpen={setSelected} />
    <GamesToWatch games={watch} previews={previews} locked={locked} onOpen={setSelected} />
    <section className="pub-slate vnext-slate">
      <div className="pub-section-head"><div><span>FULL BOARD</span><h2>Every game, one clean read.</h2></div><div className="pub-sort">{[['kickoff','Kickoff'],['strength','Strongest'],['edge','Biggest edge'],['close','Closest']].map(([key,label])=><button key={key} className={sortMode===key?'active':''} onClick={()=>setSortMode(key)}>{label}</button>)}</div></div>
      <div className="pub-card-grid">{sorted.map(game => <GameCard key={game.game_id} game={game} preview={previews[game.game_id]} evidence={evidence[game.game_id]||[]} locked={locked.has(game.game_id)} onOpen={()=>setSelected(game)} />)}</div>
    </section>
  </main>
}

function ModelConsensus({ game }) {
  const engines = [
    ['Logistic',game.logistic_home_prob],['Extra Trees',game.extra_trees_home_prob],['XGBoost',game.xgboost_home_prob],['CatBoost',game.catboost_home_prob],['Elo',game.elo_home_prob],
  ].map(([label,value]) => ({label,value:pickProbability(game,value)})).filter(row => row.value != null)
  const pure = pickProbability(game,game.pure_home_prob)
  const market = pickProbability(game,game.market_home_prob)
  const final = game.pickP
  const bullish = engines.filter(row=>row.value>.5).length
  const highest = [...engines].sort((a,b)=>b.value-a.value)[0]
  const lowest = [...engines].sort((a,b)=>a.value-b.value)[0]
  const spread = highest && lowest ? (highest.value-lowest.value)*100 : 0
  const summary = engines.length ? `${bullish} of ${engines.length} football engines lean ${game.pick}. ${spread >= 15 ? `${highest.label} is the high case and ${lowest.label} is the low case.` : `The engines are relatively compact, with ${highest.label} highest.`}` : 'Component probabilities are not available yet.'
  return <section className="vnext-consensus">
    <div className="pub-block-head"><span>MODEL CONSENSUS</span><b>{summary}</b></div>
    <div className="vnext-consensus-list">{engines.map(row=><div className="vnext-consensus-row" key={row.label}><div><span>{row.label}</span><b>{pct(row.value,0)}</b></div><div className="vnext-consensus-track"><i className="mid"/><em style={{left:`${probabilityAxisPosition(row.value)}%`}}/></div></div>)}</div>
    <div className="pub-gap-scale vnext-axis-scale"><span>40%</span><span>50</span><span>60</span><span>70</span><span>80%+</span></div>
    <div className="vnext-consensus-output vnext-consensus-formula"><span><small>PURE</small><b>{pct(pure)}</b><em>football only</em></span><i>× 75%</i><span><small>MARKET</small><b>{pct(market)}</b><em>vig-free signal</em></span><i>× 25%</i><span className="final"><small>LEVLINE</small><b>{game.pick} {pct(final)}</b><em>published probability</em></span></div>
    <p className="vnext-consensus-note">Each row uses the same probability scale, so clustered engines stay readable without hiding exact values.</p>
  </section>
}

function QuickNumbers({ game }) {
  const rows = [
    ['LevLine',`${game.pick} ${pct(game.pickP)}`],['Projected score',game.projected_score || '—'],['Model spread',modelLine(game.margin,game.home_team,game.away_team)],['Market spread',modelLine(game.market,game.home_team,game.away_team)],
    ['Spread edge',signed(game.pickEdge)],['Projected total',one(game.expected_total)],['Market total',one(game.total_line)],['Confidence',game.confidence || '—'],
  ]
  return <section className="vnext-quick"><div className="pub-block-head"><span>QUICK NUMBERS</span></div><div className="vnext-quick-grid">{rows.map(([label,value])=><div key={label}><span>{label}</span><b>{value}</b></div>)}</div>
    <details><summary>Advanced numbers</summary><div className="vnext-advanced-grid"><Stat label="PURE" value={pct(pickProbability(game,game.pure_home_prob))}/><Stat label="Market win" value={pct(game.marketPickP)}/><Stat label="Cover probability" value={pct(game.pick===game.home_team?game.cover_home_prob:(num(game.cover_home_prob)==null?null:1-num(game.cover_home_prob)))}/><Stat label="Over" value={pct(game.over_prob)}/><Stat label="Fair home ML" value={num(game.fair_home_moneyline)==null?'—':Math.round(num(game.fair_home_moneyline))}/><Stat label="Model disagreement" value={pct(game.model_disagreement)}/></div></details>
  </section>
}

function EvidenceBlock({ title, items, empty }) {
  return <section className="pub-article-block vnext-evidence-block"><div className="pub-block-head"><span>{title}</span><b>{items.length}</b></div>{items.length ? <div className="pub-evidence-list">{items.map((item,index)=><div className="pub-evidence" key={`${item.title}-${index}`}><div><span>{item.strength || 'Context'}</span><b>{item.title}</b></div><p>{item.summary}</p><small>{item.sample_size ? `Sample ${item.sample_size}` : ''}{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Source ↗</a>}</small></div>)}</div> : <p className="pub-empty">{empty}</p>}</section>
}
function HistoryFeature({ items }) {
  const qb = items.find(item => (item.metadata||{}).family === 'qb_opponent_history')
  if (!qb) return null
  const latest = (qb.metadata||{}).latest_meeting
  return <div className="pub-history-feature"><span>BEEN HERE BEFORE</span><h3>{qb.title}</h3><p>{qb.summary}</p>{latest && <div><b>{latest.human_label || latest.label}</b>{latest.score && <em>{latest.score}</em>}{latest.date && <small>{latest.date}</small>}</div>}</div>
}

function MatchupMeter({ rows=[], evidence=[], game }) {
  if (!rows.length) return null
  const detailFor = row => evidence.find(item => item.title === row.title) || {}
  return <section className="pub-article-block vnext-meter-block"><div className="pub-block-head"><span>MATCHUP EDGES</span><b>Qualitative unless the underlying evidence supplies a real numeric differential</b></div><div className="vnext-meter">{rows.map((row,index)=>{const detail=detailFor(row);const leader=row.leader||'Mixed';return <div className="vnext-meter-row vnext-edge-card" key={`${row.label}-${index}`}><div className="vnext-meter-head"><span>{row.label}</span><b>{['Watch','Mixed','Even'].includes(leader)?leader:`Edge ${leader}`} · {row.strength || 'Context'}</b></div><h4>{row.title || detail.title || 'Matchup signal'}</h4><p>{detail.summary || row.summary || 'This signal is worth monitoring as the matchup develops.'}</p></div>})}</div></section>
}

function ForecastMovement({ game, runs }) {
  const DAY_MS = 86400000
  const DAY_LABELS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  const pacificParts = value => {
    const date = value instanceof Date ? value : new Date(value)
    if (Number.isNaN(date.getTime())) return null
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone:'America/Los_Angeles', year:'numeric', month:'2-digit', day:'2-digit',
      hour:'2-digit', minute:'2-digit', second:'2-digit', hourCycle:'h23',
    }).formatToParts(date)
    const shown = Object.fromEntries(parts.map(part => [part.type, part.value]))
    return { year:+shown.year, month:+shown.month, day:+shown.day, hour:+shown.hour, minute:+shown.minute, second:+shown.second }
  }
  const raw = runs
    .filter(row=>row.game_id===game.game_id && row.prediction_timestamp_utc)
    .sort((a,b)=>new Date(a.prediction_timestamp_utc)-new Date(b.prediction_timestamp_utc))
  const kickoff = easternKickoff(game)
  const reference = kickoff || (raw.length ? new Date(raw[raw.length-1].prediction_timestamp_utc) : new Date())
  const ref = pacificParts(reference)
  const refSerial = ref ? Date.UTC(ref.year,ref.month-1,ref.day) : Date.now()
  const refDow = new Date(refSerial).getUTCDay()
  let mondaySerial = refSerial - (((refDow + 6) % 7) * DAY_MS)
  if (refDow === 1 && raw.length) {
    const first = pacificParts(raw[0].prediction_timestamp_utc)
    const firstSerial = first ? Date.UTC(first.year,first.month-1,first.day) : mondaySerial
    if (firstSerial < mondaySerial) mondaySerial -= 7 * DAY_MS
  }
  const weekX = value => {
    const p = pacificParts(value)
    if (!p) return null
    const serial = Date.UTC(p.year,p.month-1,p.day)
    return (serial-mondaySerial)/DAY_MS + p.hour/24 + p.minute/1440 + p.second/86400
  }
  const prepared = raw.map(row=>({
    x:weekX(row.prediction_timestamp_utc),
    timestamp:row.prediction_timestamp_utc,
    lev:pickProbability(game,row.final_home_prob),
    market:pickProbability(game,row.market_home_prob),
  })).filter(row=>row.x!=null && row.lev!=null)
  const kickoffX = kickoff ? weekX(kickoff) : null
  const latestObserved = prepared.length ? Math.max(...prepared.map(row=>row.x)) : 0
  const axisEnd = kickoffX != null && kickoffX >= 6 ? Math.max(6.15,kickoffX) : Math.max(6.85,latestObserved)
  const prior = [...prepared].filter(row=>row.x<0).pop()
  const trend = prepared.filter(row=>row.x>=0 && row.x<=axisEnd)
  if (prior && (!trend.length || trend[0].x>0)) trend.unshift({...prior,x:0,timestamp:null})
  const ticks = [0,1,2,3,4,5,6].filter(value=>value<=axisEnd+0.001)
  const labelForTick = value => DAY_LABELS[Math.round(value)] || ''
  const tooltipTime = payload => {
    const timestamp = payload?.[0]?.payload?.timestamp
    if (!timestamp) return 'Monday · start of chart'
    const date = new Date(timestamp)
    return new Intl.DateTimeFormat('en-US', {
      weekday:'long', hour:'numeric', minute:'2-digit', timeZone:'America/Los_Angeles', timeZoneName:'short',
    }).format(date)
  }
  return <section className="pub-trend vnext-trend"><div><span>FORECAST MOVEMENT</span><h3>How LevLine and the market moved through the week</h3></div><div>{trend.length>1?<ResponsiveContainer width="100%" height={230}><LineChart data={trend} margin={{top:10,right:10,left:-10,bottom:0}}><CartesianGrid stroke="#183041" strokeDasharray="3 5" vertical={false}/><XAxis type="number" dataKey="x" domain={[0,axisEnd]} ticks={ticks} tickFormatter={labelForTick} tickLine={false} axisLine={false}/><YAxis domain={[0.35,.85]} tickFormatter={v=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><Tooltip labelFormatter={(value,payload)=>tooltipTime(payload)} formatter={(v,name)=>[pct(v),name==='lev'?'LevLine':'Market']}/><Area dataKey="lev" type="stepAfter" fill="#68d8c718" stroke="none"/><Line dataKey="lev" type="stepAfter" stroke="#68d8c7" strokeWidth={3} dot={false}/><Line dataKey="market" type="stepAfter" stroke="#9caebb" strokeWidth={2} strokeDasharray="5 4" dot={false}/></LineChart></ResponsiveContainer>:<p className="pub-empty">Movement appears after the second comparable model run.</p>}</div></section>
}

function MovementAttribution({ movement }) {
  if (!movement) return null
  const driver = movement.largest_driver || 'No material move'
  const move = num(movement.pick_delta_pp)
  const model = num(movement.model_component_pp)
  const market = num(movement.market_component_pp)
  const residual = num(movement.residual_component_pp)
  const pp = value => value == null ? '—' : `${value>=0?'+':''}${value.toFixed(2)} pp`
  return <section className="vnext-movement-note"><div className="pub-block-head"><span>WHAT MOVED THE NUMBER</span><b>{driver}</b></div><div className="vnext-movement-grid"><Stat label="Latest LevLine move" value={pp(move)}/><Stat label="Football-model component" value={pp(model)}/><Stat label="Market component" value={pp(market)}/><Stat label="Residual / data transition" value={pp(residual)}/></div><p>This is arithmetic attribution of the latest forecast change. It does not claim an injury, weather report or news item caused the move unless that information is actually in the numerical model.</p></section>
}

function GameModal({ game, runs, evidence=[], preview, locked, sources, movement, onClose }) {
  const category = item => String(item.category||'').toLowerCase()
  const personnel=evidence.filter(item=>['injury','personnel'].includes(category(item)))
  const history=evidence.filter(item=>['history','coaching','coordinator','structural_change'].includes(category(item)))
  const scenarios=evidence.filter(item=>['scenario','weather','travel'].includes(category(item)))
  const scheme=evidence.filter(item=>['scheme','matchup'].includes(category(item)))
  const paragraphs=preview?.paragraphs?.length ? preview.paragraphs : [`LevLine has ${game.pick} at ${pct(game.pickP)} to win.`]
  const opponent=game.pick===game.home_team?game.away_team:game.home_team
  const issues=publicSourceIssues(sources)
  return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-modal vnext-modal" onClick={e=>e.stopPropagation()}>
    <button className="pub-close" onClick={onClose}>×</button>
    <div className="pub-modal-id"><span><TeamMark team={game.away_team} size="lg" /><b>{teamName(game.away_team)}</b></span><div><small>{kickoffText(game)}</small><strong>@</strong><StateBadge game={game} locked={locked} /></div><span><TeamMark team={game.home_team} size="lg" /><b>{teamName(game.home_team)}</b></span></div>
    <div className="pub-story-kicker">SUNDAY SIGNAL · GAME FILE</div>
    <h1>{preview?.headline || `${game.pick} ${pct(game.pickP)}`}</h1>
    {issues.length>0 && <div className="vnext-modal-warning"><b>Context note</b><span>{issues.map(([key])=>key.replaceAll('_',' ')).join(', ')} feed health is degraded.</span></div>}
    <div className={`pub-verdict vnext-verdict ${locked?'locked':''}`}><div><span>{locked?'OFFICIAL FORECAST':'CURRENT FORECAST'}</span><strong>{game.pick} {pct(game.pickP)}</strong><small>{locked?'Locked. This forecast can no longer change.':'Updates until the official pregame lock.'}</small></div><div><b>{game.projected_score || 'Score projection pending'}</b><small>LevLine {modelLine(game.margin,game.home_team,game.away_team)} · Market {modelLine(game.market,game.home_team,game.away_team)} · Edge {signed(game.pickEdge)}</small></div></div>
    <MarketGap game={game} />

    <section className="pub-article-block pub-prose vnext-read"><div className="pub-block-head"><span>THE READ</span></div>{paragraphs.map((p,i)=><p key={i}>{p}</p>)}</section>
    <MatchupMeter rows={preview?.matchup_meter || []} evidence={evidence} game={game} />

    <section className="pub-article-block vnext-factors"><div className="pub-block-head"><span>THREE THINGS THAT MATTER</span></div><div className="pub-factors">{(preview?.key_factors||[]).slice(0,3).map((factor,index)=><div key={index}><span>0{index+1}</span><b>{factor.title || factor.family}</b><p>{factor.summary}</p><small>{factor.advantage_team?`Edge ${factor.advantage_team} · `:''}{factor.strength || 'Context'}</small></div>)}</div></section>
    <div className="pub-case-grid vnext-case-grid"><div><span>HOW {game.pick} WINS</span><p>{preview?.case_for_pick || `The central estimates favor ${game.pick}.`}</p></div><div><span>HOW {opponent} WINS</span><p>{preview?.case_for_opponent || `${opponent} needs the volatile parts of the game to swing its way.`}</p></div></div>

    <HistoryFeature items={history} />
    <div className="vnext-evidence-grid"><EvidenceBlock title="PERSONNEL" items={personnel} empty="Nothing material on the official availability report yet." /><EvidenceBlock title="HISTORY & STAFF CHANGES" items={history} empty="No verified matchup history worth forcing into the story." /></div>
    <EvidenceBlock title="WEATHER, TRAVEL & SCENARIOS" items={scenarios} empty="No live situational issue is material enough to feature." />

    <div className="vnext-data-grid"><ModelConsensus game={game}/><QuickNumbers game={game}/></div>
    <ForecastMovement game={game} runs={runs}/>
    <MovementAttribution movement={movement}/>

    <section className="pub-article-block pub-wrong vnext-wrong"><div className="pub-block-head"><span>WHY THIS COULD BE WRONG</span></div><p>{preview?.what_could_make_us_wrong || 'Football remains annoyingly good at producing turnovers, busted coverages and weird fourth downs.'}</p></section>
    <details className="pub-raw"><summary>Raw scheme evidence</summary><EvidenceBlock title="SCHEME NOTES" items={scheme} empty="No tactical item cleared the display threshold." /></details>
  </div></div>
}

function PageHead({ kicker,title,copy }) { return <div className="pub-page-head"><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></div> }
function TeamsPage({ profiles, setTeam, powerEditorial }) {
  const rows=[...profiles].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  const editorialByTeam=Object.fromEntries((powerEditorial?.teams||[]).map(row=>[row.team,row]))
  return <main className="pub-inner"><PageHead kicker="32 TEAM PROFILES" title="The league, one team at a time." copy="Current strength, efficiency, the next LevLine forecast, and the short explanation for why each team sits where it does."/><div className="pub-team-grid vnext-team-grid-rich">{rows.map(row=>{const note=editorialByTeam[row.team]||{};return <button key={row.team} onClick={()=>setTeam({...row,editorial:note})}><TeamMark team={row.team}/><span>#{row.rank} {note.movement||''}</span><h3>{teamName(row.team)}</h3><div><small>Elo+</small><b>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</b></div><div><small>Next</small><b>{row.next_opponent?`${row.next_site==='HOME'?'vs':'@'} ${row.next_opponent}`:'TBD'}</b></div><div><small>Win</small><b>{pct(row.next_win_prob)}</b></div>{note.why_here&&<p>{note.why_here}</p>}</button>})}</div></main>
}
function TeamModal({ team,onClose }) {
  const note=team.editorial||{}
  return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-team-modal vnext-team-modal-rich" onClick={e=>e.stopPropagation()}><button className="pub-close" onClick={onClose}>×</button><TeamMark team={team.team} size="lg"/><span>POWER RANK #{team.rank} {note.movement||''}</span><h2>{teamName(team.team)}</h2>{note.why_here&&<p className="vnext-team-thesis">{note.why_here}</p>}<div className="pub-number-grid"><Stat label="Elo+" value={num(team.elo_plus)==null?'—':Math.round(num(team.elo_plus))}/><Stat label="Off EPA" value={num(team.off_epa)==null?'—':num(team.off_epa).toFixed(3)}/><Stat label="Def EPA allowed" value={num(team.def_epa_allowed)==null?'—':num(team.def_epa_allowed).toFixed(3)}/><Stat label="Pass EPA" value={num(team.pass_epa)==null?'—':num(team.pass_epa).toFixed(3)}/><Stat label="Recent" value={pct(team.recent_win_pct,0)}/><Stat label="Next win" value={pct(team.next_win_prob)}/><Stat label="Next projected points" value={one(team.next_projected_points)}/><Stat label="Next game" value={team.next_opponent?`${team.next_site==='HOME'?'vs':'@'} ${team.next_opponent}`:'TBD'} sub={team.next_game_date||''}/></div>{note.what_moves_them&&<div className="vnext-team-pressure"><span>WHAT MOVES THEM</span><p>{note.what_moves_them}</p></div>}</div></div>
}

function RatingsPage({ rows, editorial }) {
  const sorted=[...rows].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  const byTeam=Object.fromEntries((editorial?.teams||[]).map(row=>[row.team,row]))
  return <main className="pub-inner"><PageHead kicker="POWER RATINGS" title="LevLine's current league table." copy="Elo+ sets the published rank. Recent efficiency is shown as supporting or conflicting evidence rather than being quietly blended into a second hidden ranking."/><div className="vnext-power-list">{sorted.map(row=>{const note=byTeam[row.team]||{};const metrics=Object.entries(note.supporting_metric_ranks||{}).sort((a,b)=>a[1]-b[1]).slice(0,3);return <article key={row.team}><div className="vnext-power-rank"><b>#{row.rank}</b><span>{note.movement||'→'} {note.movement_text||'steady'}</span></div><div className="vnext-power-team"><TeamMark team={row.team}/><div><h3>{teamName(row.team)}</h3><span>Elo+ {num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</span></div></div><div className="vnext-power-copy"><p>{note.why_here||'The published rank comes from Elo+; supporting efficiency context is still being assembled.'}</p>{note.what_moves_them&&<small>{note.what_moves_them}</small>}</div><div className="vnext-power-metrics">{metrics.map(([label,rank])=><span key={label}><b>#{rank}</b> {label}</span>)}</div></article>})}</div></main>
}

function HistoryPage({ history, autopsies, calibration, weekFilter, setWeekFilter }) {
  const visible = weekFilter ? history.filter(row=>Number(row.week)===Number(weekFilter)) : history
  const correctFor = row => {
    const item=autopsies[row.game_id]||{}
    const value=item.winner_correct ?? item.correct
    if (value == null || value === '') return null
    return String(value).toLowerCase()==='true'
  }
  const graded=history.filter(row=>correctFor(row)!=null)
  const wins=graded.filter(row=>correctFor(row)===true).length
  return <main className="pub-inner"><PageHead kicker="OFFICIAL HISTORY" title="The receipts stay on the table." copy="Only the first valid pregame lock is graded. No hindsight edit, no quiet probability swap, no pretending the miss was actually a win."/>
    {weekFilter && <button className="vnext-clear-filter" onClick={()=>setWeekFilter(null)}>← All official history</button>}
    <div className="pub-history-summary vnext-history-summary"><Stat label="Official locks" value={history.length} sub="Immutable snapshots"/><Stat label="Record" value={graded.length?`${wins}-${graded.length-wins}`:'—'} sub={graded.length?`${pct(wins/graded.length,0)} winner accuracy`:'Starts after games finish'}/><Stat label="Calibration" value={calibration.length?`${calibration.length} buckets`:'Forward test'} sub="Probability quality, not just picks"/><Stat label="Policy" value="No edits" sub="After official lock"/></div>
    {calibration.length>0 && <section className="vnext-history-cal"><span>CALIBRATION</span><h3>When LevLine says 70%, does reality look like 70%?</h3><div>{calibration.map((row,index)=><div key={index}><b>{row.bucket||row.probability_bucket||`${pct(row.bin_low||0,0)}–${pct(row.bin_high||0,0)}`}</b><span>{row.games||row.n||'—'} games</span><em>{row.actual_win_rate||row.observed_rate||row.observed_home_win||'—'}</em></div>)}</div></section>}
    {visible.length?<div className="pub-table"><table><thead><tr><th>Week</th><th>Matchup</th><th>Pick</th><th>Probability</th><th>Projected</th><th>Result</th></tr></thead><tbody>{visible.map((row,index)=>{const correct=correctFor(row);return <tr key={`${row.game_id}-${index}`}><td>{row.week||'—'}</td><td>{row.away_team&&row.home_team?`${row.away_team} @ ${row.home_team}`:row.game_id}</td><td><b>{row.pick||'—'}</b></td><td>{pct(row.pick_prob||row.final_pick_prob||row.final_home_prob)}</td><td>{row.projected_score||'—'}</td><td>{correct!=null?(correct?'✓ Correct':'✕ Miss'):'Pending'}</td></tr>})}</tbody></table></div>:<div className="pub-empty-state">The ledger starts with the first official lock.</div>}
  </main>
}

function MethodPage({ models }) {
  const nodes=[
    ['FOOTBALL DATA','EPA · success · explosives · turnovers · QB/team strength · rest/travel'],
    ['PURE','Logistic · Extra Trees · XGBoost · CatBoost · Elo/SuJaR → football-only probability'],
    ['MARKET','Vig-free consensus probability, kept separate from PURE'],
    ['LEVLINE','75% PURE + 25% MARKET'],
    ['T−120 LOCK','First valid pregame forecast becomes immutable'],
    ['AUDIT','Brier · calibration · log loss · margin/total error · market comparison'],
  ]
  return <main className="pub-inner vnext-method"><PageHead kicker="METHODOLOGY" title="The thesis behind LevLine." copy="A forecast should be testable, calibrated, explainable, and impossible to rewrite after the fact."/>
    <section className="vnext-method-hero"><img src={`${BASE}brand/sunday-signal-icon.svg`} alt=""/><div><span>THE SHORT VERSION</span><h2>Build the football probability first. Let the market contribute information without taking over. Lock the answer before kickoff. Then grade the probability honestly.</h2></div></section>
    <section className="vnext-pipeline"><div className="pub-block-head"><span>HOW A FORECAST BECOMES OFFICIAL</span></div>{nodes.map(([title,body],index)=><div className="vnext-pipe-node" key={title}><i>{String(index+1).padStart(2,'0')}</i><div><span>{title}</span><b>{body}</b></div>{index<nodes.length-1&&<em>↓</em>}</div>)}</section>
    <div className="pub-method-grid">
      <div><span>TRAIN WITHOUT PEEKING</span><h3>Chronological expanding-window validation</h3><p>Older seasons train the model; later seasons test it. The model does not get to study the answer key before taking the exam.</p></div>
      <div><span>KEEP 2026 SACRED</span><h3>The current season is a forward test</h3><p>2026 results are for measurement, not for choosing the architecture. Any upgrade has to prove itself on earlier held-out data first.</p></div>
      <div><span>SEPARATE NUMBER FROM STORY</span><h3>Context explains; it does not secretly move points</h3><p>Injuries, coaching, scheme, quarterback history, weather and travel appear in the written analysis. They enter the numerical model only after separate out-of-sample validation.</p></div>
      <div><span>RESPECT THE MARKET</span><h3>Useful information, not a veto</h3><p>PURE is the football-only forecast. LevLine blends 75% PURE with 25% market signal. Big disagreements stay visible.</p></div>
      <div><span>LOCK IT</span><h3>No moving the goalposts</h3><p>The first valid forecast inside the T−120 window becomes immutable. That exact probability and pick are what Sunday Signal grades.</p></div>
      <div><span>GRADE THE PROBABILITY</span><h3>Being right is not enough</h3><p>A 51% call and a 90% call should not be judged the same way. Brier score, log loss and calibration punish confidence that was not deserved.</p></div>
    </div>
    {models.length>0 && <section className="vnext-validation"><div className="pub-block-head"><span>VALIDATION</span><b>Former Model Lab, now where it belongs</b></div><div className="pub-table"><table><thead><tr><th>Model</th><th>Games</th><th>Winner%</th><th>Brier</th><th>Log loss</th><th>Margin MAE</th></tr></thead><tbody>{models.map((row,index)=><tr key={`${row.model}-${index}`}><td><b>{row.model==='Final Ensemble'?'LevLine':row.model}</b></td><td>{row.games||'—'}</td><td>{row.winner_pct||row.winner_accuracy||'—'}</td><td>{row.brier||row.brier_score||'—'}</td><td>{row.log_loss||'—'}</td><td>{row.margin_mae||'—'}</td></tr>)}</tbody></table></div></section>}
    <section className="pub-not-do"><span>WHAT LEVLINE DOES NOT DO</span><div><b>No hindsight edits.</b><b>No hand-entered tout picks.</b><b>No unvalidated injury-point guesses.</b><b>No tuning the architecture on 2026 outcomes.</b><b>No pretending a 50.1% game is a mortal lock.</b></div></section>
  </main>
}

export default function App() {
  const [tab,setTab]=useState('week')
  const [games,setGames]=useState([]), [runs,setRuns]=useState([]), [evidence,setEvidence]=useState({}), [previews,setPreviews]=useState({}), [sources,setSources]=useState({}), [status,setStatus]=useState({})
  const [ratings,setRatings]=useState([]), [models,setModels]=useState([]), [history,setHistory]=useState([]), [profiles,setProfiles]=useState([]), [calibration,setCalibration]=useState([]), [autopsies,setAutopsies]=useState({}), [powerEditorial,setPowerEditorial]=useState({teams:[]}), [movement,setMovement]=useState([])
  const [selected,setSelected]=useState(null), [team,setTeam]=useState(null), [historyWeek,setHistoryWeek]=useState(null), [error,setError]=useState('')

  useEffect(()=>{;(async()=>{try{
    const [g,r,e,p,s,st,pr,ml,h,tp,cal,auto,pe,mv]=await Promise.all([
      fetchCSV('this_week.csv'),fetchCSV('run_history.csv'),fetchJSON('contextual_evidence.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('context_source_status.json',{}),fetchJSON('status.json',{}),fetchCSV('power_ratings.csv'),fetchCSV('model_leaderboard.csv'),fetchCSV('prediction_history.csv'),fetchCSV('team_profiles.csv'),fetchCSV('calibration.csv'),fetchJSON('postgame_autopsies.json',{}),fetchJSON('power_editorial.json',{teams:[]}),fetchCSV('movement_attribution.csv'),
    ])
    setGames(g.map(normalizeGame));setRuns(r);setEvidence(e);setPreviews(p);setSources(s);setStatus(st);setRatings(pr);setModels(ml);setHistory(h);setProfiles(tp);setCalibration(cal);setAutopsies(auto);setPowerEditorial(pe);setMovement(mv)
  }catch(err){setError(String(err))}})()},[])

  const locked=useMemo(()=>new Set(history.filter(row=>row.lock_status==='LOCKED').map(row=>row.game_id)),[history])
  const week=Number(games[0]?.week || 0)
  const openHistoryWeek = value => { setHistoryWeek(value); setTab('history'); window.scrollTo({top:0,behavior:'smooth'}) }
  if(error) return <div className="pub-fatal"><b>Sunday Signal could not load.</b><span>{error}</span></div>
  return <div className="pub-app">
    <Header tab={tab} setTab={key=>{setTab(key); if(key!=='history')setHistoryWeek(null)}} status={status} history={history} sources={sources} week={week}/>
    {tab==='week'&&<WeekPage games={games} evidence={evidence} previews={previews} history={history} status={status} setSelected={setSelected} onPreviousWeek={openHistoryWeek}/>} 
    {tab==='teams'&&<TeamsPage profiles={profiles} setTeam={setTeam} powerEditorial={powerEditorial}/>} 
    {tab==='ratings'&&<RatingsPage rows={ratings} editorial={powerEditorial}/>} 
    {tab==='history'&&<HistoryPage history={history} autopsies={autopsies} calibration={calibration} weekFilter={historyWeek} setWeekFilter={setHistoryWeek}/>} 
    {tab==='method'&&<MethodPage models={models}/>} 
    {selected&&<GameModal game={selected} runs={runs} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} locked={locked.has(selected.game_id)} sources={sources} movement={movement.find(row=>row.game_id===selected.game_id)} onClose={()=>setSelected(null)}/>} 
    {team&&<TeamModal team={team} onClose={()=>setTeam(null)}/>} 
    <footer className="pub-footer"><b>SUNDAY SIGNAL</b><span>Built in public. Locked before kickoff. Graded after.</span></footer>
  </div>
}
