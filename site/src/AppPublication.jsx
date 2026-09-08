import React, { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './publication.css'

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
  return <span className="pub-state current">CURRENT FORECAST</span>
}

function Header({ tab, setTab, status, history, sources }) {
  const tabs = [['week','Forecasts'],['teams','Teams'],['ratings','Power'],['models','Model Lab'],['history','History'],['method','Method']]
  const locked = history.filter(row => row.lock_status === 'LOCKED')
  const graded = locked.filter(row => ['true','false'].includes(String(row.winner_correct).toLowerCase()))
  const wins = graded.filter(row => String(row.winner_correct).toLowerCase() === 'true').length
  return <>
    <header className="pub-header">
      <button className="pub-brand" onClick={() => setTab('week')}>
        <span className="pub-logo">SS</span>
        <span><b>SUNDAY SIGNAL</b><small>powered by LevLine</small></span>
      </button>
      <div className="pub-health"><i /><span><b>{status?.status === 'healthy' ? 'MODEL LIVE' : 'LEVLINE'}</b><small>{graded.length ? `Official 2026 · ${wins}-${graded.length-wins}` : 'Official record begins at first lock'}</small></span></div>
    </header>
    <nav className="pub-nav">{tabs.map(([key,label]) => <button key={key} className={tab===key?'active':''} onClick={() => setTab(key)}>{label}</button>)}</nav>
    <div className="pub-fresh">
      <span>LevLine <b>{age(status?.generated_utc || status?.prediction_timestamp_utc)}</b></span>
      <span>Market <b>{age(status?.market_updated_utc || status?.generated_utc)}</b></span>
      <span>Personnel <b>{age(sources?.injuries?.as_of)}</b></span>
      <span>Context <b>{age(sources?.generated_utc)}</b></span>
    </div>
  </>
}

function CompactHero({ games, history, status }) {
  const next = [...games].filter(g => easternKickoff(g) > new Date()).sort((a,b) => easternKickoff(a)-easternKickoff(b))[0]
  const strongest = [...games].sort((a,b) => (b.pickP||0)-(a.pickP||0))[0]
  const locked = history.filter(row => row.lock_status === 'LOCKED').length
  return <section className="pub-hero">
    <div><span>2026 · WEEK {games[0]?.week || '—'}</span><h1>The numbers, the matchup, and the part that could make us look stupid.</h1><p>LevLine makes the forecast. Sunday Signal explains why it makes sense, where the market disagrees, and what might break it.</p></div>
    <div className="pub-hero-stats">
      <Stat label="Next" value={next ? `${next.away_team} @ ${next.home_team}` : 'Slate complete'} sub={next ? kickoffText(next) : ''} />
      <Stat label="Top signal" value={strongest ? `${strongest.pick} ${pct(strongest.pickP)}` : '—'} sub={strongest?.confidence || 'Current read'} />
      <Stat label="Locked" value={`${locked}/${games.length || 0}`} sub="Never edited after lock" />
      <Stat label="Fresh" value={age(status?.generated_utc)} sub="Latest model run" />
    </div>
  </section>
}

function Stat({ label, value, sub }) {
  return <div className="pub-stat"><span>{label}</span><b>{value}</b><small>{sub}</small></div>
}

function MarketGap({ game, compact = false }) {
  const model = game.pickP == null ? 50 : Math.max(2, Math.min(98, game.pickP*100))
  const market = game.marketPickP == null ? null : Math.max(2, Math.min(98, game.marketPickP*100))
  const gap = game.marketPickP == null || game.pickP == null ? null : (game.pickP-game.marketPickP)*100
  return <div className={`pub-gap ${compact?'compact':''}`}>
    <div className="pub-gap-head"><span>WIN PROBABILITY</span><b>{gap == null ? 'Market unavailable' : `${gap>=0?'+':''}${gap.toFixed(1)} pts vs market`}</b></div>
    <div className="pub-gap-track">
      <i className="mid" />
      {market != null && <i className="market" style={{ left:`${market}%` }}><em>Market</em></i>}
      <i className="model" style={{ left:`${model}%` }}><em>LevLine</em></i>
    </div>
    <div className="pub-gap-scale"><span>40%</span><span>50</span><span>60</span><span>70</span><span>80%+</span></div>
  </div>
}

function GameCard({ game, runs, preview, evidence, locked, onOpen }) {
  const teaser = preview?.headline || preview?.paragraphs?.[0] || `${game.pick} is the current side.`
  return <button className={`pub-game-card ${locked?'is-locked':''}`} onClick={onOpen} style={{ '--away':teamColor(game.away_team), '--home':teamColor(game.home_team) }}>
    <div className="pub-card-top"><span>{kickoffText(game)}</span><StateBadge game={game} locked={locked} /></div>
    <div className="pub-matchup">
      <span><TeamMark team={game.away_team} /><b>{game.away_team}</b></span><em>@</em><span><TeamMark team={game.home_team} /><b>{game.home_team}</b></span>
    </div>
    <div className="pub-pick"><span>LEVLINE</span><strong>{game.pick} <b>{pct(game.pickP)}</b></strong><small>{game.projected_score || 'Central score pending'}</small></div>
    <MarketGap game={game} compact />
    <div className="pub-card-lines"><span><small>Model line</small><b>{modelLine(game.margin,game.home_team,game.away_team)}</b></span><span><small>Market</small><b>{modelLine(game.market,game.home_team,game.away_team)}</b></span><span className="edge"><small>Edge</small><b>{signed(game.pickEdge)}</b></span></div>
    <p>{teaser}</p>
    <div className="pub-card-foot"><span>{preview?.key_factors?.length || evidence?.length || 0} verified matchup signals</span><b>Read the game file →</b></div>
  </button>
}

function Spotlight({ games, previews, onOpen }) {
  const strongest = [...games].sort((a,b)=>(b.pickP||0)-(a.pickP||0))[0]
  if (!strongest) return null
  const preview = previews[strongest.game_id]
  const marketGap = strongest.marketPickP == null ? null : (strongest.pickP-strongest.marketPickP)*100
  return <section className="pub-spotlight" style={{ '--away':teamColor(strongest.away_team), '--home':teamColor(strongest.home_team) }}>
    <div className="pub-spot-copy"><span>SIGNAL OF THE WEEK</span><h2>{preview?.headline || `${strongest.pick} ${pct(strongest.pickP)}`}</h2><p>{preview?.paragraphs?.[0] || 'The strongest current probability on the slate.'}</p><button onClick={() => onOpen(strongest)}>Open the full case →</button></div>
    <div className="pub-spot-board">
      <div><TeamMark team={strongest.away_team} size="lg" /><b>{strongest.away_team}</b><em>@</em><TeamMark team={strongest.home_team} size="lg" /><b>{strongest.home_team}</b></div>
      <strong>{strongest.pick} {pct(strongest.pickP)}</strong>
      <small>{marketGap == null ? 'No market probability attached' : `${marketGap>=0?'+':''}${marketGap.toFixed(1)} percentage points vs market`}</small>
      <MarketGap game={strongest} compact />
    </div>
  </section>
}

function WeekPage({ games, runs, evidence, previews, history, status, setSelected }) {
  const [sortMode,setSortMode] = useState('kickoff')
  const locked = new Set(history.filter(row => row.lock_status==='LOCKED').map(row => row.game_id))
  const sorted = useMemo(() => {
    const copy=[...games]
    if (sortMode==='strength') return copy.sort((a,b)=>(b.pickP||0)-(a.pickP||0))
    if (sortMode==='edge') return copy.sort((a,b)=>(b.pickEdge??-999)-(a.pickEdge??-999))
    if (sortMode==='close') return copy.sort((a,b)=>Math.abs((a.pickP||.5)-.5)-Math.abs((b.pickP||.5)-.5))
    return copy.sort((a,b)=>(easternKickoff(a)?.getTime()||0)-(easternKickoff(b)?.getTime()||0))
  },[games,sortMode])
  return <main className="pub-main">
    <CompactHero games={games} history={history} status={status} />
    <Spotlight games={games} previews={previews} onOpen={setSelected} />
    <section className="pub-slate">
      <div className="pub-section-head"><div><span>WEEK {games[0]?.week || '—'} FORECASTS</span><h2>The whole board, without making you hunt for the pick.</h2></div><div className="pub-sort">{[['kickoff','Kickoff'],['strength','Strongest'],['edge','Biggest edge'],['close','Closest']].map(([key,label])=><button key={key} className={sortMode===key?'active':''} onClick={()=>setSortMode(key)}>{label}</button>)}</div></div>
      <div className="pub-card-grid">{sorted.map(game => <GameCard key={game.game_id} game={game} runs={runs} preview={previews[game.game_id]} evidence={evidence[game.game_id]||[]} locked={locked.has(game.game_id)} onOpen={()=>setSelected(game)} />)}</div>
    </section>
  </main>
}

function ModelStrip({ game }) {
  const rows = [
    ['Logistic',game.logistic_home_prob],['Extra Trees',game.extra_trees_home_prob],['XGBoost',game.xgboost_home_prob],['CatBoost',game.catboost_home_prob],['PURE',game.pure_home_prob],['Market',game.market_home_prob],['LevLine',game.final_home_prob],
  ].map(([label,value]) => ({ label, value:num(value) })).filter(row=>row.value!=null)
  return <div className="pub-model-strip">{rows.map(row => <div key={row.label} className={row.label==='LevLine'?'final':''}><span>{row.label}</span><div><i style={{ width:`${row.value*100}%` }} /></div><b>{pct(row.value,0)}</b></div>)}</div>
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

function MatchupMeter({ rows=[] }) {
  if (!rows.length) return null
  return <section className="pub-article-block"><div className="pub-block-head"><span>MATCHUP METER</span></div><div className="pub-meter">{rows.map((row,index)=><div key={`${row.label}-${index}`}><span>{row.label}</span><i /><b>{row.leader || 'Mixed'}</b><em>{row.strength || 'Context'}</em></div>)}</div></section>
}

function GameModal({ game, runs, evidence=[], preview, locked, sources, onClose }) {
  const category = item => String(item.category||'').toLowerCase()
  const personnel=evidence.filter(item=>['injury','personnel'].includes(category(item)))
  const history=evidence.filter(item=>['history','coaching','coordinator','structural_change'].includes(category(item)))
  const scenarios=evidence.filter(item=>['scenario','weather','travel'].includes(category(item)))
  const scheme=evidence.filter(item=>['scheme','matchup'].includes(category(item)))
  const trend=runs.filter(row=>row.game_id===game.game_id).sort((a,b)=>new Date(a.prediction_timestamp_utc)-new Date(b.prediction_timestamp_utc)).map((row,index)=>({run:index+1,p:num(row.final_home_prob)})).filter(row=>row.p!=null)
  const paragraphs=preview?.paragraphs?.length ? preview.paragraphs : [`LevLine has ${game.pick} at ${pct(game.pickP)} to win.`]
  const opponent=game.pick===game.home_team?game.away_team:game.home_team
  return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-modal" onClick={e=>e.stopPropagation()}>
    <button className="pub-close" onClick={onClose}>×</button>
    <div className="pub-modal-id"><span><TeamMark team={game.away_team} size="lg" /><b>{teamName(game.away_team)}</b></span><div><small>{kickoffText(game)}</small><strong>@</strong><StateBadge game={game} locked={locked} /></div><span><TeamMark team={game.home_team} size="lg" /><b>{teamName(game.home_team)}</b></span></div>
    <div className="pub-story-kicker">SUNDAY SIGNAL · GAME FILE</div>
    <h1>{preview?.headline || `${game.pick} ${pct(game.pickP)}`}</h1>
    <div className={`pub-verdict ${locked?'locked':''}`}><div><span>{locked?'OFFICIAL FORECAST':'CURRENT FORECAST'}</span><strong>{game.pick} {pct(game.pickP)}</strong><small>{locked?'Locked. This forecast can no longer change.':'Updates until the official pregame lock.'}</small></div><div><b>{game.projected_score || 'Score projection pending'}</b><small>LevLine {modelLine(game.margin,game.home_team,game.away_team)} · Market {modelLine(game.market,game.home_team,game.away_team)} · Edge {signed(game.pickEdge)}</small></div></div>
    <MarketGap game={game} />
    <div className="pub-modal-grid"><article>
      <section className="pub-article-block pub-prose"><div className="pub-block-head"><span>THE READ</span></div>{paragraphs.map((p,i)=><p key={i}>{p}</p>)}</section>
      <HistoryFeature items={history} />
      <section className="pub-article-block"><div className="pub-block-head"><span>THREE THINGS THAT MATTER</span></div><div className="pub-factors">{(preview?.key_factors||[]).slice(0,3).map((factor,index)=><div key={index}><span>0{index+1}</span><b>{factor.title || factor.family}</b><p>{factor.summary}</p><small>{factor.advantage_team?`Edge ${factor.advantage_team} · `:''}{factor.strength || 'Context'}</small></div>)}</div></section>
      <div className="pub-case-grid"><div><span>CASE FOR {game.pick}</span><p>{preview?.case_for_pick || `The central estimates favor ${game.pick}.`}</p></div><div><span>CASE FOR {opponent}</span><p>{preview?.case_for_opponent || `${opponent} needs the volatile parts of the game to swing its way.`}</p></div></div>
      <MatchupMeter rows={preview?.matchup_meter || []} />
      <EvidenceBlock title="PERSONNEL" items={personnel} empty="Nothing material on the official availability report yet." />
      <EvidenceBlock title="HISTORY & STAFF CHANGES" items={history} empty="No verified matchup history worth forcing into the story." />
      <EvidenceBlock title="WEATHER, TRAVEL & SCENARIOS" items={scenarios} empty="No live situational issue is material enough to feature." />
      <section className="pub-article-block pub-wrong"><div className="pub-block-head"><span>WHAT COULD MAKE THIS WRONG?</span></div><p>{preview?.what_could_make_us_wrong || 'Football remains annoyingly good at producing turnovers, busted coverages and weird fourth downs.'}</p></section>
      <details className="pub-raw"><summary>Raw scheme evidence</summary><EvidenceBlock title="SCHEME NOTES" items={scheme} empty="No tactical item cleared the display threshold." /></details>
    </article><aside>
      <div className="pub-aside-card"><span>MODEL CONSENSUS</span><h3>Where the engines land</h3><ModelStrip game={game} /></div>
      <div className="pub-aside-card"><span>QUICK NUMBERS</span><div className="pub-number-grid"><Stat label="Fair home" value={pct(game.homeP)} /><Stat label="PURE" value={pct(game.pure_home_prob)} /><Stat label="Market" value={pct(game.market_home_prob)} /><Stat label="Total" value={one(game.expected_total)} /><Stat label="Home cover" value={pct(game.cover_home_prob)} /><Stat label="Over" value={pct(game.over_prob)} /></div></div>
      <div className="pub-source-card"><span>SOURCE HEALTH</span>{Object.entries(sources||{}).filter(([,v])=>v&&typeof v==='object'&&v.status).slice(0,10).map(([key,value])=><div key={key}><b>{key.replaceAll('_',' ')}</b><em className={value.status==='healthy'?'ok':'warn'}>{value.status}</em></div>)}</div>
    </aside></div>
    <section className="pub-trend"><div><span>FORECAST HISTORY</span><h3>How the probability moved</h3></div><div>{trend.length>1?<ResponsiveContainer width="100%" height={220}><AreaChart data={trend}><XAxis dataKey="run" tickLine={false} axisLine={false}/><YAxis domain={[0,1]} tickFormatter={v=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><Tooltip formatter={v=>pct(v)}/><Area dataKey="p" type="monotone" stroke="#68d8c7" fill="#68d8c722" strokeWidth={3}/></AreaChart></ResponsiveContainer>:<p className="pub-empty">Movement appears after the second comparable model run.</p>}</div></section>
  </div></div>
}

function PageHead({ kicker,title,copy }) { return <div className="pub-page-head"><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></div> }

function TeamsPage({ profiles, setTeam }) {
  const rows=[...profiles].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  return <main className="pub-inner"><PageHead kicker="32 TEAM PROFILES" title="The league, one team at a time." copy="Power, efficiency and the next forecast. The useful stuff, minus the press-conference fog."/><div className="pub-team-grid">{rows.map(row=><button key={row.team} onClick={()=>setTeam(row)}><TeamMark team={row.team}/><span>#{row.rank}</span><h3>{teamName(row.team)}</h3><div><small>Elo+</small><b>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</b></div><div><small>Next</small><b>{row.next_opponent?`${row.next_site==='HOME'?'vs':'@'} ${row.next_opponent}`:'TBD'}</b></div><div><small>Win</small><b>{pct(row.next_win_prob)}</b></div></button>)}</div></main>
}

function TeamModal({ team,onClose }) { return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-team-modal" onClick={e=>e.stopPropagation()}><button className="pub-close" onClick={onClose}>×</button><TeamMark team={team.team} size="lg"/><span>POWER RANK #{team.rank}</span><h2>{teamName(team.team)}</h2><div className="pub-number-grid"><Stat label="Elo+" value={num(team.elo_plus)==null?'—':Math.round(num(team.elo_plus))}/><Stat label="Off EPA" value={num(team.off_epa)==null?'—':num(team.off_epa).toFixed(3)}/><Stat label="Def EPA allowed" value={num(team.def_epa_allowed)==null?'—':num(team.def_epa_allowed).toFixed(3)}/><Stat label="Pass EPA" value={num(team.pass_epa)==null?'—':num(team.pass_epa).toFixed(3)}/><Stat label="Recent" value={pct(team.recent_win_pct,0)}/><Stat label="Next win" value={pct(team.next_win_prob)}/></div></div></div> }

function RatingsPage({ rows }) {
  const sorted=[...rows].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  return <main className="pub-inner"><PageHead kicker="POWER RATINGS" title="LevLine's current league table." copy="Elo+ is still the published spine. Anything fancier has to earn its way in out of sample."/><div className="pub-table"><table><thead><tr><th>Rank</th><th>Team</th><th>Elo+</th><th>Off EPA</th><th>Def EPA allowed</th><th>Pass EPA</th><th>Recent</th></tr></thead><tbody>{sorted.map(row=><tr key={row.team}><td>#{row.rank}</td><td><span className="pub-table-team"><TeamMark team={row.team} size="sm"/>{teamName(row.team)}</span></td><td><b>{Math.round(num(row.elo_plus)||0)}</b></td><td>{one(row.off_epa)}</td><td>{one(row.def_epa_allowed)}</td><td>{one(row.pass_epa)}</td><td>{pct(row.recent_win_pct,0)}</td></tr>)}</tbody></table></div></main>
}

function ModelsPage({ rows, calibration }) {
  return <main className="pub-inner"><PageHead kicker="MODEL LAB" title="Confidence has to be earned." copy="Win percentage is the headline. Calibration, Brier score and log loss tell us whether the confidence underneath it is sane."/><div className="pub-lab"><div className="pub-table"><table><thead><tr><th>Model</th><th>Games</th><th>Winner%</th><th>Brier</th><th>Log loss</th><th>Margin MAE</th><th>Total MAE</th></tr></thead><tbody>{rows.map((row,index)=><tr key={`${row.model}-${index}`}><td><b>{row.model==='Final Ensemble'?'LevLine':row.model}</b></td><td>{row.games||'—'}</td><td>{row.winner_pct||row.winner_accuracy||'—'}</td><td>{row.brier||row.brier_score||'—'}</td><td>{row.log_loss||'—'}</td><td>{row.margin_mae||'—'}</td><td>{row.total_mae||'—'}</td></tr>)}</tbody></table></div><div className="pub-cal"><span>CALIBRATION</span><h3>When we say 70%, do we actually mean 70%?</h3>{calibration.length?calibration.map((row,index)=><div key={index}><b>{row.bucket||row.probability_bucket||`Bucket ${index+1}`}</b><span>{row.games||row.n||'—'} games</span><em>{row.actual_win_rate||row.observed_rate||'—'}</em></div>):<p>Calibration bins populate as official 2026 locks are graded.</p>}</div></div></main>
}

function HistoryPage({ history, autopsies }) {
  const graded=history.filter(row=>autopsies[row.game_id]?.correct!=null)
  const wins=graded.filter(row=>String(autopsies[row.game_id]?.correct).toLowerCase()==='true').length
  return <main className="pub-inner"><PageHead kicker="OFFICIAL HISTORY" title="The receipts stay on the table." copy="Only the first valid pregame lock is graded. No hindsight edit, no quiet probability swap, no pretending the miss was actually a win."/><div className="pub-history-summary"><Stat label="Official locks" value={history.length} sub="Immutable snapshots"/><Stat label="Record" value={graded.length?`${wins}-${graded.length-wins}`:'—'} sub={graded.length?`${pct(wins/graded.length,0)} winner accuracy`:'Starts after games finish'}/><Stat label="Policy" value="No edits" sub="After official lock"/></div>{history.length?<div className="pub-table"><table><thead><tr><th>Week</th><th>Matchup</th><th>Pick</th><th>Probability</th><th>Projected</th><th>Result</th></tr></thead><tbody>{history.map((row,index)=><tr key={`${row.game_id}-${index}`}><td>{row.week||'—'}</td><td>{row.away_team&&row.home_team?`${row.away_team} @ ${row.home_team}`:row.game_id}</td><td><b>{row.pick||'—'}</b></td><td>{pct(row.pick_prob||row.final_pick_prob||row.final_home_prob)}</td><td>{row.projected_score||'—'}</td><td>{autopsies[row.game_id]?.correct!=null?(String(autopsies[row.game_id].correct).toLowerCase()==='true'?'✓ Correct':'✕ Miss'):'Pending'}</td></tr>)}</tbody></table></div>:<div className="pub-empty-state">The ledger starts with the first official lock.</div>}</main>
}

function MethodPage() {
  const nodes=[
    ['INPUTS','EPA · success rate · explosives · turnovers · Elo · rest · home field'],
    ['FOUR MODELS','Logistic · Extra Trees · XGBoost · CatBoost'],
    ['PURE','Football-only ensemble probability'],
    ['MARKET','Consensus market-implied probability'],
    ['LEVLINE','75% PURE + 25% MARKET'],
    ['LOCK','First valid forecast inside T−120 becomes official'],
    ['AUDIT','Calibration · Brier · log loss · margin/total error'],
  ]
  return <main className="pub-inner"><PageHead kicker="METHODOLOGY" title="The thesis behind LevLine." copy="The goal is not to sound certain. The goal is to be well calibrated, explain the football underneath the number, and preserve exactly what the model believed before kickoff."/>
    <section className="pub-thesis"><span>THE SHORT VERSION</span><h2>Start with football. Let different models disagree. Use the market as information, not scripture. Lock the answer before the game. Then keep score honestly.</h2><p>That is the entire philosophy. Everything else is implementation detail.</p></section>
    <section className="pub-pipeline"><div className="pub-block-head"><span>HOW A FORECAST BECOMES OFFICIAL</span></div><div className="pub-pipeline-row">{nodes.map(([title,body],index)=><React.Fragment key={title}><div className={`pub-node n${index}`}><span>{title}</span><b>{body}</b></div>{index<nodes.length-1&&<i>→</i>}</React.Fragment>)}</div></section>
    <div className="pub-method-grid">
      <div><span>1 · TRAIN WITHOUT PEEKING</span><h3>Chronological expanding-window validation</h3><p>Older seasons train the model; later seasons test it. The model does not get to study the answer key before taking the exam.</p></div>
      <div><span>2 · KEEP 2026 SACRED</span><h3>The current season is a forward test</h3><p>2026 results are for measurement, not for choosing the architecture. Any upgrade has to prove itself on earlier held-out data first.</p></div>
      <div><span>3 · SEPARATE NUMBER FROM STORY</span><h3>Context explains; it does not secretly move points</h3><p>Injuries, coaching, scheme, quarterback history, weather and travel appear in the written analysis. They enter the numerical model only after separate out-of-sample validation.</p></div>
      <div><span>4 · RESPECT THE MARKET</span><h3>Useful information, not a veto</h3><p>PURE is the football-only forecast. LevLine's published probability blends 75% PURE with 25% market signal. Big disagreements stay visible instead of being averaged into oblivion.</p></div>
      <div><span>5 · LOCK IT</span><h3>No moving the goalposts after kickoff</h3><p>The first valid forecast inside the T−120 window becomes immutable. That exact probability and pick are what Sunday Signal grades.</p></div>
      <div><span>6 · GRADE THE PROBABILITY</span><h3>Being right is not enough</h3><p>A 51% call and a 90% call should not be judged the same way. Brier score, log loss and calibration punish confidence that was not deserved.</p></div>
    </div>
    <section className="pub-not-do"><span>WHAT LEVLINE DOES NOT DO</span><div><b>No hindsight edits.</b><b>No hand-entered tout picks.</b><b>No unvalidated injury-point guesses.</b><b>No tuning the architecture on 2026 outcomes.</b><b>No pretending a 50.1% game is a mortal lock.</b></div></section>
  </main>
}

export default function App() {
  const [tab,setTab]=useState('week')
  const [games,setGames]=useState([]), [runs,setRuns]=useState([]), [evidence,setEvidence]=useState({}), [previews,setPreviews]=useState({}), [sources,setSources]=useState({}), [status,setStatus]=useState({})
  const [ratings,setRatings]=useState([]), [models,setModels]=useState([]), [history,setHistory]=useState([]), [profiles,setProfiles]=useState([]), [calibration,setCalibration]=useState([]), [autopsies,setAutopsies]=useState({})
  const [selected,setSelected]=useState(null), [team,setTeam]=useState(null), [error,setError]=useState('')

  useEffect(()=>{;(async()=>{try{
    const [g,r,e,p,s,st,pr,ml,h,tp,cal,auto]=await Promise.all([
      fetchCSV('this_week.csv'),fetchCSV('run_history.csv'),fetchJSON('contextual_evidence.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('context_source_status.json',{}),fetchJSON('status.json',{}),fetchCSV('power_ratings.csv'),fetchCSV('model_leaderboard.csv'),fetchCSV('prediction_history.csv'),fetchCSV('team_profiles.csv'),fetchCSV('calibration.csv'),fetchJSON('postgame_autopsies.json',{}),
    ])
    setGames(g.map(normalizeGame));setRuns(r);setEvidence(e);setPreviews(p);setSources(s);setStatus(st);setRatings(pr);setModels(ml);setHistory(h);setProfiles(tp);setCalibration(cal);setAutopsies(auto)
  }catch(err){setError(String(err))}})()},[])

  const locked=useMemo(()=>new Set(history.filter(row=>row.lock_status==='LOCKED').map(row=>row.game_id)),[history])
  if(error) return <div className="pub-fatal"><b>Sunday Signal could not load.</b><span>{error}</span></div>
  return <div className="pub-app">
    <Header tab={tab} setTab={setTab} status={status} history={history} sources={sources}/>
    {tab==='week'&&<WeekPage games={games} runs={runs} evidence={evidence} previews={previews} history={history} status={status} setSelected={setSelected}/>} 
    {tab==='teams'&&<TeamsPage profiles={profiles} setTeam={setTeam}/>} 
    {tab==='ratings'&&<RatingsPage rows={ratings}/>} 
    {tab==='models'&&<ModelsPage rows={models} calibration={calibration}/>} 
    {tab==='history'&&<HistoryPage history={history} autopsies={autopsies}/>} 
    {tab==='method'&&<MethodPage/>}
    {selected&&<GameModal game={selected} runs={runs} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} locked={locked.has(selected.game_id)} sources={sources} onClose={()=>setSelected(null)}/>} 
    {team&&<TeamModal team={team} onClose={()=>setTeam(null)}/>} 
    <footer className="pub-footer"><b>SUNDAY SIGNAL</b><span>Built in public. Locked before kickoff. Graded after.</span></footer>
  </div>
}
