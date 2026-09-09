import React, { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './publication.css'
import './accountability.css'

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
const three = value => num(value) == null ? '—' : num(value).toFixed(3)

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
  if (minutes < 60) return `${minutes}m`
  const hours = Math.round(minutes / 60)
  return hours < 48 ? `${hours}h` : `${Math.round(hours / 24)}d`
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

function sourceProblems(sources) {
  const ignore = new Set(['weather'])
  return Object.entries(sources || {}).filter(([key,value]) => {
    if (!value || typeof value !== 'object' || !value.status) return false
    return value.status !== 'healthy' && !ignore.has(key)
  })
}

function Header({ tab, setTab, status, history, sources, week }) {
  const tabs = [['week','Forecasts'],['teams','Teams'],['ratings','Power'],['history','History'],['method','Method']]
  const locked = history.filter(row => row.lock_status === 'LOCKED')
  const problems = sourceProblems(sources)
  return <>
    <header className="pub-header">
      <button className="pub-brand" onClick={() => setTab('week')}>
        <span className="pub-logo">SS</span>
        <span><b>SUNDAY SIGNAL</b><small>powered by LevLine</small></span>
      </button>
      <div className="pub-health"><i className={problems.length ? 'warn-dot' : ''}/><span><b>{problems.length ? 'DATA NOTICE' : 'MODEL LIVE'}</b><small>{locked.length ? `${locked.length} official lock${locked.length===1?'':'s'}` : `Week ${week || '—'} · pre-lock`}</small></span></div>
    </header>
    <nav className="pub-nav">
      {tabs.map(([key,label]) => <button key={key} className={tab===key?'active':''} onClick={() => setTab(key)}>{label}</button>)}
      <span className="pub-week-chip">2026 · W{week || '—'}</span>
    </nav>
    {problems.length > 0 && <div className="pub-source-alert"><b>Analysis-source notice</b><span>{problems.map(([key])=>key.replaceAll('_',' ')).join(', ')} currently degraded. LevLine remains published from the validated numerical pipeline.</span></div>}
  </>
}

function Stat({ label, value, sub }) {
  return <div className="pub-stat"><span>{label}</span><b>{value}</b>{sub && <small>{sub}</small>}</div>
}

function CompactHero({ games, history, status }) {
  const next = [...games].filter(g => easternKickoff(g) > new Date()).sort((a,b) => easternKickoff(a)-easternKickoff(b))[0]
  const strongest = [...games].sort((a,b) => (b.pickP||0)-(a.pickP||0))[0]
  const locked = history.filter(row => row.lock_status === 'LOCKED').length
  const week = games[0]?.week || '—'
  return <section className="pub-hero pub-hero-clean">
    <div><span>2026 · WEEK {week}</span><h1>Week {week} NFL Forecasts</h1><p>LevLine probabilities, market edges and matchup analysis for every game.</p></div>
    <div className="pub-hero-stats">
      <Stat label="Next kickoff" value={next ? `${next.away_team} @ ${next.home_team}` : 'Slate complete'} sub={next ? kickoffText(next) : ''} />
      <Stat label="Top signal" value={strongest ? `${strongest.pick} ${pct(strongest.pickP)}` : '—'} sub={strongest?.confidence || 'Current forecast'} />
      <Stat label="Official locks" value={`${locked}/${games.length || 0}`} sub="Immutable after lock" />
      <Stat label="Updated" value={age(status?.generated_utc || status?.prediction_timestamp_utc)} sub="ago" />
    </div>
  </section>
}

function probabilityAxisPosition(probability) {
  const p = num(probability)
  if (p == null) return null
  return Math.max(0, Math.min(100, ((p * 100) - 40) / 40 * 100))
}

function MarketGap({ game, compact = false }) {
  const model = probabilityAxisPosition(game.pickP) ?? 25
  const market = probabilityAxisPosition(game.marketPickP)
  const gap = game.marketPickP == null || game.pickP == null ? null : (game.pickP-game.marketPickP)*100
  return <div className={`pub-gap ${compact?'compact':''}`}>
    <div className="pub-gap-head"><span>LEVLINE vs MARKET</span><b>{gap == null ? 'Market unavailable' : `${gap>=0?'+':''}${gap.toFixed(1)} pts`}</b></div>
    <div className="pub-gap-track"><i className="mid" />{market != null && <i className="market" style={{ left:`${market}%` }}><em>Market</em></i>}<i className="model" style={{ left:`${model}%` }}><em>LevLine</em></i></div>
    <div className="pub-gap-scale"><span>40%</span><span>50</span><span>60</span><span>70</span><span>80%+</span></div>
  </div>
}

function GameCard({ game, preview, evidence, locked, onOpen, compact = false }) {
  const teaser = preview?.headline || preview?.paragraphs?.[0] || `${game.pick} is the current side.`
  return <button className={`pub-game-card ${locked?'is-locked':''} ${compact?'watch-card':''}`} onClick={onOpen} style={{ '--away':teamColor(game.away_team), '--home':teamColor(game.home_team) }}>
    <div className="pub-card-top"><span>{kickoffText(game)}</span><StateBadge game={game} locked={locked} /></div>
    <div className="pub-matchup"><span><TeamMark team={game.away_team} /><b>{game.away_team}</b></span><em>@</em><span><TeamMark team={game.home_team} /><b>{game.home_team}</b></span></div>
    <div className="pub-pick"><span>LEVLINE</span><strong>{game.pick} <b>{pct(game.pickP)}</b></strong><small>{game.projected_score || 'Central score pending'}</small></div>
    <div className="pub-card-lines"><span><small>LevLine</small><b>{modelLine(game.margin,game.home_team,game.away_team)}</b></span><span><small>Market</small><b>{modelLine(game.market,game.home_team,game.away_team)}</b></span><span className="edge"><small>Edge</small><b>{signed(game.pickEdge)}</b></span></div>
    {!compact && <MarketGap game={game} compact />}
    <p>{teaser}</p>
    <div className="pub-card-foot"><span>{preview?.key_factors?.length || evidence?.length || 0} verified signals</span><b>Open game →</b></div>
  </button>
}

function Spotlight({ games, previews, onOpen }) {
  const strongest = [...games].sort((a,b)=>(b.pickP||0)-(a.pickP||0))[0]
  if (!strongest) return null
  const preview = previews[strongest.game_id]
  const marketGap = strongest.marketPickP == null ? null : (strongest.pickP-strongest.marketPickP)*100
  return <section className="pub-spotlight" style={{ '--away':teamColor(strongest.away_team), '--home':teamColor(strongest.home_team) }}>
    <div className="pub-spot-copy"><span>SIGNAL OF THE WEEK</span><h2>{preview?.headline || `${strongest.pick} ${pct(strongest.pickP)}`}</h2><p>{preview?.paragraphs?.[0] || 'The strongest current probability on the slate.'}</p><button onClick={() => onOpen(strongest)}>Open the full case →</button></div>
    <div className="pub-spot-board"><div><TeamMark team={strongest.away_team} size="lg" /><b>{strongest.away_team}</b><em>@</em><TeamMark team={strongest.home_team} size="lg" /><b>{strongest.home_team}</b></div><strong>{strongest.pick} {pct(strongest.pickP)}</strong><small>{marketGap == null ? 'Market probability unavailable' : `${marketGap>=0?'+':''}${marketGap.toFixed(1)} percentage points vs market`}</small><MarketGap game={strongest} compact /></div>
  </section>
}

function GamesToWatch({ games, previews, evidence, history, onOpen }) {
  if (games.length < 2) return null
  const signal = [...games].sort((a,b)=>(b.pickP||0)-(a.pickP||0))[0]?.game_id
  const locked = new Set(history.filter(row=>row.lock_status==='LOCKED').map(row=>row.game_id))
  const watch = [...games].filter(g=>g.game_id!==signal).sort((a,b)=>{
    const aGap = a.marketPickP == null ? 0 : Math.abs((a.pickP||.5)-a.marketPickP)
    const bGap = b.marketPickP == null ? 0 : Math.abs((b.pickP||.5)-b.marketPickP)
    return (bGap + Math.abs(b.pickEdge||0)/20) - (aGap + Math.abs(a.pickEdge||0)/20)
  }).slice(0,3)
  return <section className="pub-watch"><div className="pub-section-head"><div><span>GAMES TO WATCH</span><h2>Where the board gets interesting.</h2></div></div><div className="pub-watch-grid">{watch.map(game=><GameCard key={game.game_id} game={game} preview={previews[game.game_id]} evidence={evidence[game.game_id]||[]} locked={locked.has(game.game_id)} onOpen={()=>onOpen(game)} compact />)}</div></section>
}

function WeekPage({ games, evidence, previews, history, status, setSelected }) {
  const [sortMode,setSortMode] = useState('kickoff')
  const locked = new Set(history.filter(row => row.lock_status==='LOCKED').map(row => row.game_id))
  const sorted = useMemo(() => {
    const copy=[...games]
    if (sortMode==='strength') return copy.sort((a,b)=>(b.pickP||0)-(a.pickP||0))
    if (sortMode==='edge') return copy.sort((a,b)=>(b.pickEdge??-999)-(a.pickEdge??-999))
    if (sortMode==='close') return copy.sort((a,b)=>Math.abs((a.pickP||.5)-.5)-Math.abs((b.pickP||.5)-.5))
    return copy.sort((a,b)=>(easternKickoff(a)?.getTime()||0)-(easternKickoff(b)?.getTime()||0))
  },[games,sortMode])
  return <main className="pub-main"><CompactHero games={games} history={history} status={status}/><Spotlight games={games} previews={previews} onOpen={setSelected}/><GamesToWatch games={games} previews={previews} evidence={evidence} history={history} onOpen={setSelected}/><section className="pub-slate"><div className="pub-section-head"><div><span>FULL WEEK {games[0]?.week || '—'} SLATE</span><h2>Every forecast, in one scan.</h2></div><div className="pub-sort">{[['kickoff','Kickoff'],['strength','Strongest'],['edge','Biggest edge'],['close','Closest']].map(([key,label])=><button key={key} className={sortMode===key?'active':''} onClick={()=>setSortMode(key)}>{label}</button>)}</div></div><div className="pub-card-grid">{sorted.map(game => <GameCard key={game.game_id} game={game} preview={previews[game.game_id]} evidence={evidence[game.game_id]||[]} locked={locked.has(game.game_id)} onOpen={()=>setSelected(game)} />)}</div></section></main>
}

function modelProbabilityRows(game) {
  return [['Logistic',game.logistic_home_prob],['Extra Trees',game.extra_trees_home_prob],['XGBoost',game.xgboost_home_prob],['CatBoost',game.catboost_home_prob],['Elo',game.elo_home_prob]].map(([label,value])=>({label,value:num(value)})).filter(row=>row.value!=null)
}

function ModelConsensus({ game }) {
  const engines = modelProbabilityRows(game)
  const home = game.home_team
  const away = game.away_team
  const values = engines.map(row=>row.value)
  const range = values.length ? (Math.max(...values)-Math.min(...values))*100 : null
  const homeLeans = engines.filter(row=>row.value>=.5).length
  const leanTeam = homeLeans >= Math.ceil(engines.length/2) ? home : away
  const summary = engines.length ? `${homeLeans} of ${engines.length} component models lean ${home}; the model spread is ${range?.toFixed(1)} percentage points.` : 'Component-model probabilities are not available for this run.'
  const pos = p => Math.max(0,Math.min(100,((p-.25)/.5)*100))
  return <div className="consensus-panel"><div className="consensus-axis"><span>25%</span><span>50</span><span>75%</span>{engines.map(row=><i key={row.label} style={{left:`${pos(row.value)}%`}} title={`${row.label}: ${pct(row.value)}`}><em>{row.label}</em></i>)}</div><p>{summary} Majority lean: <b>{leanTeam}</b>.</p><div className="consensus-outcomes"><div><span>PURE</span><b>{pct(game.pure_home_prob)}</b><small>football-only</small></div><div><span>MARKET</span><b>{pct(game.market_home_prob)}</b><small>outside signal</small></div><div className="final"><span>LEVLINE</span><b>{pct(game.final_home_prob)}</b><small>published</small></div></div></div>
}

function EvidenceBlock({ title, items, empty }) {
  return <section className="pub-article-block"><div className="pub-block-head"><span>{title}</span><b>{items.length}</b></div>{items.length ? <div className="pub-evidence-list">{items.map((item,index)=><div className="pub-evidence" key={`${item.title}-${index}`}><div><span>{item.strength || 'Context'}</span><b>{item.title}</b></div><p>{item.summary}</p><small>{item.sample_size ? `Sample ${item.sample_size}` : ''}{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Source ↗</a>}</small></div>)}</div> : <p className="pub-empty">{empty}</p>}</section>
}

function HistoryFeature({ items }) {
  const qb = items.find(item => (item.metadata||{}).family === 'qb_opponent_history')
  if (!qb) return null
  const latest = (qb.metadata||{}).latest_meeting
  return <div className="pub-history-feature"><span>BEEN HERE BEFORE</span><h3>{qb.title}</h3><p>{qb.summary}</p>{latest && <div><b>{latest.human_label || latest.label}</b>{latest.score && <em>{latest.score}</em>}{latest.date && <small>{latest.date}</small>}</div>}</div>
}

function meterPosition(row, away, home) {
  const leader=row.leader
  const strength=String(row.strength||'').toLowerCase()
  const distance=strength==='strong'?34:strength==='moderate'?24:strength==='weak'?14:0
  if (leader===away) return 50-distance
  if (leader===home) return 50+distance
  return 50
}

function MatchupMeter({ rows=[], away, home }) {
  if (!rows.length) return null
  return <section className="pub-article-block"><div className="pub-block-head"><span>MATCHUP METER</span></div><div className="pub-meter-rich">{rows.map((row,index)=><div className="meter-row" key={`${row.label}-${index}`}><div className="meter-copy"><span>{row.label}</span><b>{row.leader || 'Watch'}</b><p>{row.title || 'Live matchup evidence'}</p></div><div className="meter-scale"><small>{away}</small><div><i className="mid"/><b style={{left:`${meterPosition(row,away,home)}%`}}/></div><small>{home}</small></div><em>{row.strength || 'Context'}</em></div>)}</div></section>
}

function QuickNumbers({ game }) {
  return <div className="quick-grid"><Stat label="LevLine" value={`${game.pick} ${pct(game.pickP)}`} /><Stat label="Projected score" value={game.projected_score || '—'} /><Stat label="Model spread" value={modelLine(game.margin,game.home_team,game.away_team)} /><Stat label="Market spread" value={modelLine(game.market,game.home_team,game.away_team)} /><Stat label="Spread edge" value={`${game.pick} ${signed(game.pickEdge)}`} /><Stat label="Projected total" value={one(game.expected_total)} /><Stat label="Market total" value={one(game.total_line)} /><Stat label="Confidence" value={game.confidence || '—'} /></div>
}

function GameModal({ game, runs, evidence=[], preview, locked, onClose }) {
  const category = item => String(item.category||'').toLowerCase()
  const personnel=evidence.filter(item=>['injury','personnel'].includes(category(item)))
  const history=evidence.filter(item=>['history','coaching','coordinator','structural_change'].includes(category(item)))
  const scenarios=evidence.filter(item=>['scenario','weather','travel'].includes(category(item)))
  const scheme=evidence.filter(item=>['scheme','matchup'].includes(category(item)))
  const trend=runs.filter(row=>row.game_id===game.game_id).sort((a,b)=>new Date(a.prediction_timestamp_utc)-new Date(b.prediction_timestamp_utc)).map((row,index)=>({run:index+1,p:num(row.final_home_prob),market:num(row.market_home_prob)})).filter(row=>row.p!=null)
  const paragraphs=preview?.paragraphs?.length ? preview.paragraphs : [`LevLine has ${game.pick} at ${pct(game.pickP)} to win.`]
  const opponent=game.pick===game.home_team?game.away_team:game.home_team
  return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-modal dossier" onClick={e=>e.stopPropagation()}><button className="pub-close" onClick={onClose}>×</button><div className="pub-modal-id"><span><TeamMark team={game.away_team} size="lg" /><b>{teamName(game.away_team)}</b></span><div><small>{kickoffText(game)}</small><strong>@</strong><StateBadge game={game} locked={locked}/></div><span><TeamMark team={game.home_team} size="lg" /><b>{teamName(game.home_team)}</b></span></div><div className="pub-story-kicker">SUNDAY SIGNAL · GAME FILE</div><h1>{preview?.headline || `${game.pick} ${pct(game.pickP)}`}</h1><div className={`pub-verdict ${locked?'locked':''}`}><div><span>{locked?'OFFICIAL FORECAST':'CURRENT FORECAST'}</span><strong>{game.pick} {pct(game.pickP)}</strong><small>{locked?'Locked. This forecast can no longer change.':'Updates until the official pregame lock.'}</small></div><div><b>{game.projected_score || 'Score projection pending'}</b><small>LevLine {modelLine(game.margin,game.home_team,game.away_team)} · Market {modelLine(game.market,game.home_team,game.away_team)} · Edge {signed(game.pickEdge)}</small></div></div><MarketGap game={game}/><div className="pub-modal-grid"><article><section className="pub-article-block pub-prose"><div className="pub-block-head"><span>THE READ</span></div>{paragraphs.map((p,i)=><p key={i}>{p}</p>)}</section><HistoryFeature items={history}/><MatchupMeter rows={preview?.matchup_meter || []} away={game.away_team} home={game.home_team}/><section className="pub-article-block"><div className="pub-block-head"><span>THREE THINGS THAT MATTER</span></div><div className="pub-factors">{(preview?.key_factors||[]).slice(0,3).map((factor,index)=><div key={index}><span>0{index+1}</span><b>{factor.title || factor.family}</b><p>{factor.summary}</p><small>{factor.advantage_team?`Edge ${factor.advantage_team} · `:''}{factor.strength || 'Context'}</small></div>)}</div></section><div className="pub-case-grid"><div><span>CASE FOR {game.pick}</span><p>{preview?.case_for_pick || `The central estimates favor ${game.pick}.`}</p></div><div><span>CASE FOR {opponent}</span><p>{preview?.case_for_opponent || `${opponent} needs the volatile parts of the game to swing its way.`}</p></div></div><EvidenceBlock title="PERSONNEL" items={personnel} empty="Nothing material on the official availability report yet."/><EvidenceBlock title="HISTORY, STAFF & IMPACT" items={history} empty="No verified staff or matchup history is material enough to feature."/><EvidenceBlock title="WEATHER, TRAVEL & SCENARIOS" items={scenarios} empty="No live situational issue is material enough to feature."/><section className="pub-article-block pub-wrong"><div className="pub-block-head"><span>WHAT COULD MAKE THIS WRONG?</span></div><p>{preview?.what_could_make_us_wrong || 'Turnovers, explosives and fourth-down variance remain the cleanest ways for the game to outrun a central forecast.'}</p></section><details className="pub-raw"><summary>Deeper scheme evidence</summary><EvidenceBlock title="SCHEME NOTES" items={scheme} empty="No tactical item cleared the display threshold."/></details></article><aside><div className="pub-aside-card"><span>MODEL CONSENSUS</span><h3>Five engines, then the blend</h3><ModelConsensus game={game}/></div><div className="pub-aside-card"><span>QUICK NUMBERS</span><QuickNumbers game={game}/></div></aside></div><section className="pub-trend"><div><span>FORECAST HISTORY</span><h3>How the probability moved</h3></div><div>{trend.length>1?<ResponsiveContainer width="100%" height={220}><AreaChart data={trend}><XAxis dataKey="run" tickLine={false} axisLine={false}/><YAxis domain={[0,1]} tickFormatter={v=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><Tooltip formatter={v=>pct(v)}/><Area dataKey="p" type="monotone" stroke="#68d8c7" fill="#68d8c722" strokeWidth={3}/></AreaChart></ResponsiveContainer>:<p className="pub-empty">Movement appears after the second comparable model run.</p>}</div></section></div></div>
}

function PageHead({ kicker,title,copy }) { return <div className="pub-page-head"><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></div> }

function TeamsPage({ profiles, setTeam }) {
  const rows=[...profiles].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  return <main className="pub-inner"><PageHead kicker="32 TEAM PROFILES" title="The league, one team at a time." copy="Power, efficiency and the next LevLine forecast."/><div className="pub-team-grid">{rows.map(row=><button key={row.team} onClick={()=>setTeam(row)}><TeamMark team={row.team}/><span>#{row.rank}</span><h3>{teamName(row.team)}</h3><div><small>Elo+</small><b>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</b></div><div><small>Next</small><b>{row.next_opponent?`${row.next_site==='HOME'?'vs':'@'} ${row.next_opponent}`:'TBD'}</b></div><div><small>Win</small><b>{pct(row.next_win_prob)}</b></div></button>)}</div></main>
}

function TeamModal({ team,onClose }) { return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-team-modal" onClick={e=>e.stopPropagation()}><button className="pub-close" onClick={onClose}>×</button><TeamMark team={team.team} size="lg"/><span>POWER RANK #{team.rank}</span><h2>{teamName(team.team)}</h2><div className="pub-number-grid"><Stat label="Elo+" value={num(team.elo_plus)==null?'—':Math.round(num(team.elo_plus))}/><Stat label="Off EPA" value={three(team.off_epa)}/><Stat label="Def EPA allowed" value={three(team.def_epa_allowed)}/><Stat label="Pass EPA" value={three(team.pass_epa)}/><Stat label="Recent" value={pct(team.recent_win_pct,0)}/><Stat label="Next win" value={pct(team.next_win_prob)}/></div></div></div> }

function movementClass(text='') { return text.startsWith('▲') ? 'up' : text.startsWith('▼') ? 'down' : 'flat' }

function RatingsPage({ rows, editorial }) {
  const sorted=[...rows].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  const notes=new Map((editorial?.teams||[]).map(item=>[item.team,item]))
  return <main className="pub-inner"><PageHead kicker="POWER RATINGS" title="The rankings, with an argument attached." copy="Elo+ sets the order. The notes explain what in the efficiency profile supports it—and what could move it next."/><div className="power-list">{sorted.map(row=>{const note=notes.get(row.team)||{};return <article key={row.team} className="power-row"><div className="power-rank"><b>#{row.rank}</b><span className={movementClass(row.movement)}>{row.movement || '→'}</span></div><TeamMark team={row.team}/><div className="power-copy"><h2>{teamName(row.team)}</h2><p>{note.why_here || `Elo+ currently places ${row.team} at No. ${row.rank}.`}</p><small><b>What could move them:</b> {note.what_moves_them || 'New game data will determine the next meaningful move.'}</small></div><div className="power-metrics"><span><small>Elo+</small><b>{Math.round(num(row.elo_plus)||0)}</b></span><span><small>Off EPA</small><b>{three(row.off_epa)}</b></span><span><small>Def EPA</small><b>{three(row.def_epa_allowed)}</b></span><span><small>Pass EPA</small><b>{three(row.pass_epa)}</b></span></div></article>})}</div></main>
}

function CalibrationPanel({ calibration }) {
  return <section className="history-panel"><span>CALIBRATION</span><h2>When LevLine says 70%, does 70% behave like 70%?</h2>{calibration.length?<div className="cal-grid">{calibration.map((row,index)=><div key={index}><b>{row.bucket||row.probability_bucket||`Bucket ${index+1}`}</b><span>{row.games||row.n||'—'} games</span><em>{row.actual_win_rate||row.observed_rate||'—'}</em></div>)}</div>:<p className="pub-empty">Calibration bins populate as official 2026 locks are graded.</p>}</section>
}

function HistoryPage({ history, autopsies, scoreboard, calibration }) {
  const locked=history.filter(row=>row.lock_status==='LOCKED')
  const board=scoreboard||{}
  const brierDelta=num(board.brier_vs_market)
  return <main className="pub-inner"><PageHead kicker="OFFICIAL HISTORY" title="The receipts stay on the table." copy="Only immutable T−120 locks count. The probability, pick and result remain visible after the game."/><section className="history-scoreboard"><Stat label="Record" value={board.graded ? board.record : '0-0'} sub={board.graded ? `${pct(board.winner_accuracy,0)} winner accuracy` : 'Waiting for graded games'}/><Stat label="Brier" value={num(board.brier)==null?'—':num(board.brier).toFixed(3)} sub="Lower is better"/><Stat label="vs market" value={brierDelta==null?'—':`${brierDelta>0?'+':''}${brierDelta.toFixed(3)}`} sub={brierDelta==null?'Common sample':brierDelta>0?'LevLine better':'Market better'}/><Stat label="Margin MAE" value={one(board.margin_mae)} sub="points"/><Stat label="Total MAE" value={one(board.total_mae)} sub="points"/></section><CalibrationPanel calibration={calibration}/>{locked.length?<div className="pub-table history-ledger"><table><thead><tr><th>Week</th><th>Matchup</th><th>Pick</th><th>Probability</th><th>Projected</th><th>Result</th></tr></thead><tbody>{locked.map((row,index)=><tr key={`${row.game_id}-${index}`}><td>{row.week||'—'}</td><td>{row.away_team&&row.home_team?`${row.away_team} @ ${row.home_team}`:row.game_id}</td><td><b>{row.pick||'—'}</b></td><td>{pct(row.pick_prob||row.final_pick_prob||row.final_home_prob)}</td><td>{row.projected_score||'—'}</td><td>{autopsies[row.game_id]?.correct!=null?(String(autopsies[row.game_id].correct).toLowerCase()==='true'?'✓ Correct':'✕ Miss'):'Pending'}</td></tr>)}</tbody></table></div>:<div className="pub-empty-state">The official ledger begins with the first T−120 lock.</div>}<p className="history-note">No ROI is displayed unless Sunday Signal defines and timestamps a betting rule before the games. Prediction performance and betting performance are not the same thing.</p></main>
}

function ValidationTable({ rows }) {
  if (!rows.length) return <p className="pub-empty">Historical validation rows are not available.</p>
  return <div className="pub-table"><table><thead><tr><th>Model</th><th>Games</th><th>Winner%</th><th>Brier</th><th>Log loss</th><th>Margin MAE</th><th>Total MAE</th></tr></thead><tbody>{rows.map((row,index)=><tr key={`${row.model}-${index}`}><td><b>{row.model==='Final Ensemble'?'LevLine':row.model}</b></td><td>{row.games||'—'}</td><td>{row.winner_pct||row.winner_accuracy||'—'}</td><td>{row.brier||row.brier_score||'—'}</td><td>{row.log_loss||'—'}</td><td>{row.margin_mae||'—'}</td><td>{row.total_mae||'—'}</td></tr>)}</tbody></table></div>
}

function MethodPage({ models }) {
  const nodes=[['NFL DATA','EPA · success rate · explosives · turnovers · Elo · QB · rest'],['FEATURES','Rolling form · opponent-adjusted context · home/travel'],['ENSEMBLE','Logistic · Extra Trees · XGBoost · CatBoost · Elo reference'],['PURE','Football-only probability'],['MARKET','Independent consensus signal'],['LEVLINE','75% PURE + 25% MARKET'],['T−120 LOCK','First valid forecast becomes immutable'],['AUDIT','Brier · calibration · error · market comparison']]
  return <main className="pub-inner method-page"><PageHead kicker="METHODOLOGY" title="The thesis behind LevLine." copy="A forecast should be reproducible before kickoff and accountable after it."/><section className="pub-pipeline pipeline-thesis"><div className="pub-block-head"><span>FROM RAW FOOTBALL TO AN OFFICIAL FORECAST</span></div><div className="method-flow">{nodes.map(([title,body],index)=><React.Fragment key={title}><div className="method-node"><span>{String(index+1).padStart(2,'0')}</span><h3>{title}</h3><p>{body}</p></div>{index<nodes.length-1&&<i>→</i>}</React.Fragment>)}</div><p className="method-callout"><b>Important:</b> PURE and Market are separate information streams. The market joins only at the published 75/25 blend; it is not fed into the football models.</p></section><div className="pub-method-grid"><div><span>TRAIN WITHOUT PEEKING</span><h3>Expanding-window validation</h3><p>Older seasons train the architecture; later seasons test it. Chronology prevents the model from learning from games it is supposed to predict.</p></div><div><span>KEEP 2026 SACRED</span><h3>The current season is a forward test</h3><p>2026 outcomes measure the system. They do not get used to choose a better-looking architecture after the fact.</p></div><div><span>SEPARATE NUMBER FROM STORY</span><h3>Context explains unless validated</h3><p>Injuries, staff, scheme, QB history, weather and travel enrich the analysis. They change LevLine only after separate chronological validation.</p></div><div><span>LOCK IT</span><h3>No moving the goalposts</h3><p>The first valid forecast inside T−120 is immutable. Later news can update explanatory context, not rewrite the official pick.</p></div></div><section className="history-panel validation-panel"><span>HISTORICAL VALIDATION</span><h2>The old Model Lab lives here now—for a reason.</h2><p>These are architecture-validation metrics, not a second consumer product.</p><ValidationTable rows={models}/></section><section className="pub-not-do"><span>WHAT LEVLINE DOES NOT DO</span><div><b>No hindsight edits.</b><b>No unvalidated injury-point guesses.</b><b>No tuning the architecture on 2026 outcomes.</b><b>No pretending winner accuracy is the same as calibration.</b></div></section></main>
}

export default function App() {
  const [tab,setTab]=useState('week')
  const [games,setGames]=useState([]), [runs,setRuns]=useState([]), [evidence,setEvidence]=useState({}), [previews,setPreviews]=useState({}), [sources,setSources]=useState({}), [status,setStatus]=useState({})
  const [ratings,setRatings]=useState([]), [models,setModels]=useState([]), [history,setHistory]=useState([]), [profiles,setProfiles]=useState([]), [calibration,setCalibration]=useState([]), [autopsies,setAutopsies]=useState({})
  const [powerEditorial,setPowerEditorial]=useState({teams:[]}), [scoreboard,setScoreboard]=useState({})
  const [selected,setSelected]=useState(null), [team,setTeam]=useState(null), [error,setError]=useState('')

  useEffect(()=>{;(async()=>{try{
    const [g,r,e,p,s,st,pr,ml,h,tp,cal,auto,pe,hs]=await Promise.all([
      fetchCSV('this_week.csv'),fetchCSV('run_history.csv'),fetchJSON('contextual_evidence.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('context_source_status.json',{}),fetchJSON('status.json',{}),fetchCSV('power_ratings.csv'),fetchCSV('model_leaderboard.csv'),fetchCSV('prediction_history.csv'),fetchCSV('team_profiles.csv'),fetchCSV('calibration.csv'),fetchJSON('postgame_autopsies.json',{}),fetchJSON('power_editorial.json',{teams:[]}),fetchJSON('history_scoreboard.json',{}),
    ])
    setGames(g.map(normalizeGame));setRuns(r);setEvidence(e);setPreviews(p);setSources(s);setStatus(st);setRatings(pr);setModels(ml);setHistory(h);setProfiles(tp);setCalibration(cal);setAutopsies(auto);setPowerEditorial(pe);setScoreboard(hs)
  }catch(err){setError(String(err))}})()},[])

  const locked=useMemo(()=>new Set(history.filter(row=>row.lock_status==='LOCKED').map(row=>row.game_id)),[history])
  const week=games[0]?.week
  if(error) return <div className="pub-fatal"><b>Sunday Signal could not load.</b><span>{error}</span></div>
  return <div className="pub-app"><Header tab={tab} setTab={setTab} status={status} history={history} sources={sources} week={week}/>{tab==='week'&&<WeekPage games={games} evidence={evidence} previews={previews} history={history} status={status} setSelected={setSelected}/>} {tab==='teams'&&<TeamsPage profiles={profiles} setTeam={setTeam}/>} {tab==='ratings'&&<RatingsPage rows={ratings} editorial={powerEditorial}/>} {tab==='history'&&<HistoryPage history={history} autopsies={autopsies} scoreboard={scoreboard} calibration={calibration}/>} {tab==='method'&&<MethodPage models={models}/>} {selected&&<GameModal game={selected} runs={runs} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} locked={locked.has(selected.game_id)} onClose={()=>setSelected(null)}/>} {team&&<TeamModal team={team} onClose={()=>setTeam(null)}/>}<footer className="pub-footer"><b>SUNDAY SIGNAL</b><span>Built in public. Locked before kickoff. Graded after.</span></footer></div>
}
