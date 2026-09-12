import React, { useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './signal.css'
import ImpactMonitor from './ImpactMonitor.jsx'

const BASE = import.meta.env.BASE_URL

const TEAM = {
  ARI:['Arizona Cardinals','ari'], ATL:['Atlanta Falcons','atl'], BAL:['Baltimore Ravens','bal'], BUF:['Buffalo Bills','buf'],
  CAR:['Carolina Panthers','car'], CHI:['Chicago Bears','chi'], CIN:['Cincinnati Bengals','cin'], CLE:['Cleveland Browns','cle'],
  DAL:['Dallas Cowboys','dal'], DEN:['Denver Broncos','den'], DET:['Detroit Lions','det'], GB:['Green Bay Packers','gb'],
  HOU:['Houston Texans','hou'], IND:['Indianapolis Colts','ind'], JAC:['Jacksonville Jaguars','jax'], JAX:['Jacksonville Jaguars','jax'],
  KC:['Kansas City Chiefs','kc'], LAC:['Los Angeles Chargers','lac'], LA:['Los Angeles Rams','lar'], LV:['Las Vegas Raiders','lv'],
  MIA:['Miami Dolphins','mia'], MIN:['Minnesota Vikings','min'], NE:['New England Patriots','ne'], NO:['New Orleans Saints','no'],
  NYG:['New York Giants','nyg'], NYJ:['New York Jets','nyj'], PHI:['Philadelphia Eagles','phi'], PIT:['Pittsburgh Steelers','pit'],
  SEA:['Seattle Seahawks','sea'], SF:['San Francisco 49ers','sf'], TB:['Tampa Bay Buccaneers','tb'], TEN:['Tennessee Titans','ten'],
  WAS:['Washington Commanders','wsh'],
}

const teamName = team => TEAM[team]?.[0] || team || '—'
const teamLogo = team => `https://a.espncdn.com/i/teamlogos/nfl/500/${TEAM[team]?.[1] || String(team || '').toLowerCase()}.png`
const num = value => {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}
const pct = (value, digits=1) => num(value) == null ? '—' : `${(num(value)*100).toFixed(digits)}%`
const pp = value => num(value) == null ? '—' : `${num(value)>=0?'+':''}${num(value).toFixed(1)} pp`
const one = value => num(value) == null ? '—' : num(value).toFixed(1)

function parseCSV(text) {
  const rows=[]
  let row=[], cell='', quoted=false
  for (let i=0;i<text.length;i+=1) {
    const c=text[i]
    if (quoted) {
      if (c==='"' && text[i+1]==='"') { cell+='"'; i+=1 }
      else if (c==='"') quoted=false
      else cell+=c
    } else if (c==='"') quoted=true
    else if (c===',') { row.push(cell); cell='' }
    else if (c==='\n') { row.push(cell); rows.push(row); row=[]; cell='' }
    else if (c!=='\r') cell+=c
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row) }
  const headers=rows.shift() || []
  return rows.filter(r=>r.some(Boolean)).map(r=>Object.fromEntries(headers.map((key,i)=>[key,r[i]??''])))
}

async function fetchCSV(name) {
  try {
    const response=await fetch(`${BASE}data/${name}`,{cache:'no-store'})
    return response.ok ? parseCSV(await response.text()) : []
  } catch { return [] }
}
async function fetchJSON(name,fallback={}) {
  try {
    const response=await fetch(`${BASE}data/${name}`,{cache:'no-store'})
    return response.ok ? await response.json() : fallback
  } catch { return fallback }
}

function formatTime(value,{withDay=false}={}) {
  if (!value) return '—'
  const date=new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US',{
    ...(withDay?{weekday:'short',month:'short',day:'numeric'}:{}),
    hour:'numeric',minute:'2-digit',timeZone:'America/Los_Angeles',timeZoneName:'short',
  }).format(date)
}
function formatKickoff(game) {
  if (!game?.kickoff_utc) return game?.gameday || 'TBD'
  return formatTime(game.kickoff_utc,{withDay:true})
}
function lineText(marginHome,home,away) {
  const margin=num(marginHome)
  if (margin==null) return '—'
  if (Math.abs(margin)<.05) return 'PK'
  return margin>0 ? `${home} -${Math.abs(margin).toFixed(1)}` : `${away} -${Math.abs(margin).toFixed(1)}`
}
function moneyline(value) {
  const n=num(value)
  if (n==null) return '—'
  return n>0 ? `+${Math.round(n)}` : `${Math.round(n)}`
}
function scoreText(game) {
  const home=game.projected_home_score
  const away=game.projected_away_score
  if (home==null || away==null) return '—'
  if (game.official_winner===game.away_team) return `${game.away_team} ${away} – ${game.home_team} ${home}`
  return `${game.home_team} ${home} – ${game.away_team} ${away}`
}
function probabilityForTeam(homeP,team,game) {
  const p=num(homeP)
  if (p==null || !team || team==='PICKEM') return null
  return team===game.home_team ? p : 1-p
}
function signalFavorite(homeP,game) {
  const p=num(homeP)
  if (p==null) return {team:'—',probability:null}
  if (Math.abs(p-.5)<1e-10) return {team:'Pick’em',probability:.5}
  return p>.5 ? {team:game.home_team,probability:p} : {team:game.away_team,probability:1-p}
}
function lifecycleLabel(status) {
  return ({LIVE_FORECAST:'Updating',FINAL_PREGAME:'Final Pregame',IN_PROGRESS:'Live',GRADED:'Final'})[status] || status || 'Forecast'
}
function interpretation(game) {
  const marketP=probabilityForTeam(game.market_home_win_probability,game.official_winner,game)
  const official=num(game.official_winner_probability)
  if (marketP==null) return `LevLine makes ${game.official_winner} the more likely winner at ${pct(official)}.`
  const delta=(official-marketP)*100
  if (Math.abs(delta)<.75) return `LevLine and the market are essentially aligned on ${game.official_winner}.`
  return `LevLine makes ${game.official_winner} ${Math.abs(delta).toFixed(1)} percentage points ${delta>0?'stronger':'weaker'} than the market does.`
}

function parseRoute() {
  const raw=window.location.hash.replace(/^#\/?/,'')
  const parts=raw.split('/').filter(Boolean)
  if (parts[0]==='game' && parts[1]) return {page:'game',gameId:decodeURIComponent(parts.slice(1).join('/'))}
  const page=parts[0] || 'forecasts'
  if (['forecasts','power','history','methodology','teams','more'].includes(page)) return {page}
  return {page:'forecasts'}
}
function navigateHash(path) {
  const next=`#/${path}`
  if (window.location.hash===next) window.scrollTo({top:0,behavior:'smooth'})
  else window.location.hash=next
}

function TeamMark({team,size='md'}) {
  const [failed,setFailed]=useState(false)
  return <span className={`ss-team-mark ${size}`}>
    {!failed && <img src={teamLogo(team)} alt="" onError={()=>setFailed(true)}/>} 
    {failed && <b>{team}</b>}
  </span>
}

function Lifecycle({game}) {
  const key=String(game.lifecycle_status||'').toLowerCase()
  return <span className={`ss-life ${key}`}><i aria-hidden="true"/>{lifecycleLabel(game.lifecycle_status)}</span>
}

function BrandLockup({compact=false}) {
  return <span className={`ss-brand-lockup ${compact?'compact':''}`}>
    <img src={`${BASE}brand/sunday-signal-icon.svg`} alt=""/>
    <span><b>SUNDAY SIGNAL</b><small>powered by <strong>LevLine</strong></small></span>
  </span>
}

function Header({route,week}) {
  const primary=[['forecasts','Forecasts'],['power','Power'],['history','History'],['methodology','Methodology']]
  return <>
    <header className="ss-header">
      <button className="ss-brand-button" onClick={()=>navigateHash('forecasts')} aria-label="Sunday Signal forecasts">
        <BrandLockup/>
      </button>
      <nav className="ss-desktop-nav" aria-label="Primary">
        {primary.map(([key,label])=><button key={key} className={route.page===key?'active':''} onClick={()=>navigateHash(key)}>{label}</button>)}
      </nav>
      <div className="ss-header-tools">
        <span>2026 · WEEK {week||'—'}</span>
        <button onClick={()=>navigateHash('more')} aria-label="More Sunday Signal sections">•••</button>
      </div>
    </header>
    <header className="ss-mobile-header">
      <button className="ss-mobile-menu" onClick={()=>navigateHash('more')} aria-label="More sections">☰</button>
      <button className="ss-brand-button" onClick={()=>navigateHash('forecasts')} aria-label="Sunday Signal forecasts"><BrandLockup compact/></button>
      <span className="ss-mobile-week">W{week||'—'}</span>
    </header>
  </>
}

function MobileNav({route}) {
  const items=[['forecasts','Forecasts','◈'],['power','Power','⌁'],['history','History','◷'],['more','More','•••']]
  const active=route.page==='teams'||route.page==='methodology'?'more':route.page
  return <nav className="ss-mobile-nav" aria-label="Mobile navigation">
    {items.map(([key,label,icon])=><button key={key} className={active===key?'active':''} onClick={()=>navigateHash(key)}><span aria-hidden="true">{icon}</span><small>{label}</small></button>)}
  </nav>
}

function SignalFlow({game,variant=''}) {
  const football=signalFavorite(game.football_only_home_win_probability,game)
  const market=signalFavorite(game.market_home_win_probability,game)
  return <section className={`ss-flow ${variant}`} aria-label="Signal Flow">
    <div className="ss-section-label">THE SIGNAL FLOW</div>
    <div className="ss-flow-row">
      <article>
        <div className="ss-bars neutral" aria-hidden="true"><i/><i/><i/><i/></div>
        <span>Football Signal</span>
        <strong>{football.team} {pct(football.probability)}</strong>
        <small>Team, talent, scheme, matchup data</small>
      </article>
      <b className="ss-flow-op" aria-hidden="true">+</b>
      <article>
        <div className="ss-bars market" aria-hidden="true"><i/><i/><i/><i/></div>
        <span>Market Signal</span>
        <strong>{market.team} {pct(market.probability)}</strong>
        <small>Current vig-free market view</small>
      </article>
      <b className="ss-flow-op" aria-hidden="true">→</b>
      <article className="final">
        <div className="ss-bars final" aria-hidden="true"><i/><i/><i/><i/></div>
        <span>LevLine Final</span>
        <strong>{game.official_winner} {pct(game.official_winner_probability)}</strong>
        <small>Official forecast</small>
      </article>
    </div>
    <p className="ss-flow-note">This presentation preserves the existing signal roles; it is not an exact visual formula for model weighting.</p>
  </section>
}

function ForecastHero({game,compact=false}) {
  return <section className={`ss-forecast-hero ${compact?'compact':''}`}>
    <div className="ss-forecast-title-row">
      <span>LEVLINE FORECAST</span>
      <Lifecycle game={game}/>
    </div>
    <div className="ss-forecast-core">
      <div className="ss-pick">
        <TeamMark team={game.official_winner} size={compact?'md':'lg'}/>
        <div><span>{teamName(game.official_winner)}</span><strong>{pct(game.official_winner_probability,0)}</strong><small>WIN PROBABILITY</small></div>
      </div>
      <div className="ss-metrics">
        <div><span>Probability-Implied Line</span><b>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</b></div>
        <div><span>Market Line</span><b>{lineText(game.market_margin_home,game.home_team,game.away_team)}</b></div>
        <div className="edge"><span>LevLine vs Market</span><b>{pp(game.levline_vs_market_winner_probability_pp)}</b></div>
        <div><span>Approximate Score</span><b>{scoreText(game)}</b></div>
      </div>
    </div>
    {!compact && <div className="ss-freshness">
      <span><b>{game.immutable?'Forecast locked':'Forecast updated'}</b> {formatTime(game.lock_timestamp_utc||game.forecast_timestamp_utc)}</span>
      <span><b>Market updated</b> {formatTime(game.market_timestamp_utc)}</span>
    </div>}
  </section>
}

function TheSignal({preview,compact=false}) {
  const headline=preview?.headline || preview?.key_factors?.[0]?.title
  const paragraphs=Array.isArray(preview?.paragraphs) ? preview.paragraphs.filter(Boolean) : []
  const fallback=preview?.key_factors?.[0]?.summary
  return <section className={`ss-the-signal ${compact?'compact':''}`}>
    <div className="ss-signal-mark" aria-hidden="true"><img src={`${BASE}brand/sunday-signal-icon.svg`} alt=""/></div>
    <div>
      <span>THE SIGNAL</span>
      {headline && <h2>{headline}</h2>}
      {!compact && paragraphs.slice(0,3).map((text,index)=><p key={index}>{text}</p>)}
      {!compact && !paragraphs.length && fallback && <p>{fallback}</p>}
      {!headline && <p className="ss-empty">Game-specific editorial intelligence has not cleared the publication threshold yet.</p>}
    </div>
  </section>
}

function TopSignals({games,onOpen}) {
  if (!games.length) return null
  const valid=games.filter(game=>num(game.official_winner_probability)!=null)
  const strongest=[...valid].sort((a,b)=>num(b.official_winner_probability)-num(a.official_winner_probability))[0]
  const largest=[...valid].filter(g=>num(g.levline_vs_market_winner_probability_pp)!=null).sort((a,b)=>Math.abs(num(b.levline_vs_market_winner_probability_pp))-Math.abs(num(a.levline_vs_market_winner_probability_pp)))[0]
  const closest=[...valid].sort((a,b)=>Math.abs(num(a.official_winner_probability)-.5)-Math.abs(num(b.official_winner_probability)-.5))[0]
  const cards=[
    strongest && {label:'Strongest Forecast',game:strongest,value:`${strongest.official_winner} ${pct(strongest.official_winner_probability,0)}`,sub:'win probability'},
    largest && {label:'Largest vs Market',game:largest,value:`${largest.official_winner} ${pp(largest.levline_vs_market_winner_probability_pp)}`,sub:'probability difference'},
    closest && {label:'Most Competitive',game:closest,value:`${closest.away_team} @ ${closest.home_team}`,sub:`${pct(closest.official_winner_probability,0)} on ${closest.official_winner}`},
  ].filter(Boolean)
  return <section className="ss-top-signals">
    <div className="ss-section-head"><div><span>TOP SIGNALS</span><small>Derived from the current published slate</small></div></div>
    <div className="ss-top-grid">{cards.map(({label,game,value,sub},index)=><button key={label} onClick={()=>onOpen(game)} data-game-open>
      <i>{index+1}</i><span>{label}</span><strong>{value}</strong><small>{sub}</small>
    </button>)}</div>
  </section>
}

function BoardRow({game,preview,onOpen}) {
  const teaser=preview?.headline || preview?.key_factors?.[0]?.title
  return <button className="ss-game-row" onClick={onOpen} data-game-open>
    <div className="ss-row-matchup">
      <span><TeamMark team={game.away_team} size="sm"/><b>{game.away_team}</b></span><em>@</em><span><TeamMark team={game.home_team} size="sm"/><b>{game.home_team}</b></span>
      <small>{formatKickoff(game)}</small>
      {teaser && <p><i>THE SIGNAL</i>{teaser}</p>}
    </div>
    <div className="ss-row-pick"><b>{game.official_winner}</b><span>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</span></div>
    <strong className="ss-row-prob">{pct(game.official_winner_probability,0)}</strong>
    <span>{lineText(game.market_margin_home,game.home_team,game.away_team)}</span>
    <span className="ss-row-edge">{pp(game.levline_vs_market_winner_probability_pp)}</span>
    <span><Lifecycle game={game}/></span>
    <b className="ss-row-arrow" aria-hidden="true">›</b>
  </button>
}

function MobileGameCard({game,preview,onOpen}) {
  return <article className="ss-mobile-card">
    <button className="ss-card-open" onClick={onOpen} data-game-open>
      <div className="ss-card-top"><span>{formatKickoff(game)}</span><Lifecycle game={game}/></div>
      <div className="ss-card-matchup">
        <span><TeamMark team={game.away_team}/><b>{game.away_team}</b></span><em>AT</em><span><TeamMark team={game.home_team}/><b>{game.home_team}</b></span>
      </div>
      <ForecastHero game={game} compact/>
      <TheSignal preview={preview} compact/>
      <div className="ss-view-matchup">View Matchup <span>→</span></div>
    </button>
  </article>
}

function ForecastBoard({games,previews,onOpen,status}) {
  const sorted=[...games].sort((a,b)=>new Date(a.kickoff_utc||0)-new Date(b.kickoff_utc||0))
  const live=sorted.filter(g=>g.lifecycle_status==='IN_PROGRESS').length
  const locked=sorted.filter(g=>g.immutable).length
  const next=sorted.find(g=>Date.parse(g.kickoff_utc||'')>Date.now())
  return <main className="ss-page ss-board">
    <section className="ss-board-hero">
      <div className="ss-hero-copy">
        <span>WEEK {games[0]?.week||'—'} · NFL</span>
        <h1>BETTER INFORMATION.<br/>WINS SUNDAYS.</h1>
        <p>Data. Context. Conviction. Powered by <b>LevLine.</b></p>
      </div>
      <div className="ss-slate-strip">
        <div><b>{games.length}</b><span>Games</span></div>
        <div><b>{locked}</b><span>Final pregame</span></div>
        <div><b>{live}</b><span>Live</span></div>
        <div><b>{next?formatTime(next.kickoff_utc,{withDay:true}):'—'}</b><span>Next kickoff</span></div>
        <div><b>{status?.generated_utc?formatTime(status.generated_utc):'—'}</b><span>Forecast feed</span></div>
      </div>
    </section>

    <TopSignals games={sorted} onOpen={onOpen}/>

    <section className="ss-week">
      <div className="ss-section-head">
        <div><span>NFL WEEK {games[0]?.week||'—'}</span><small>What LevLine thinks this week</small></div>
        <span className="ss-feed-dot"><i/>Published slate</span>
      </div>
      <div className="ss-board-table">
        <div className="ss-board-labels"><span>MATCHUP</span><span>LEVLINE PICK</span><span>WIN PROB.</span><span>MARKET LINE</span><span>VS MARKET</span><span>STATUS</span><span/></div>
        {sorted.map(game=><BoardRow key={game.game_id} game={game} preview={previews[game.game_id]} onOpen={()=>onOpen(game)}/>) }
      </div>
      <div className="ss-mobile-cards">{sorted.map(game=><MobileGameCard key={game.game_id} game={game} preview={previews[game.game_id]} onOpen={()=>onOpen(game)}/>)}</div>
    </section>
  </main>
}

function sourceLink(item) {
  return item?.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer" onClick={event=>event.stopPropagation()}>Source ↗</a> : null
}

function KeyDevelopments({evidence=[],preview}) {
  const priority=['injury','personnel','weather','travel','coaching','structural_change','scheme','matchup']
  const rank=category=>{
    const idx=priority.indexOf(String(category||'').toLowerCase())
    return idx<0 ? priority.length : idx
  }
  const items=[...evidence].sort((a,b)=>rank(a.category)-rank(b.category)).filter(item=>item.title && item.summary).slice(0,5)
  if (!items.length && !preview?.headline) return null
  return <section className="ss-panel ss-developments">
    <div className="ss-section-head"><div><span>KEY DEVELOPMENTS</span><small>Published context with governance preserved</small></div></div>
    <div className="ss-development-list">{items.map((item,index)=><article key={`${item.title}-${index}`}>
      <div className="ss-dev-icon" aria-hidden="true">{String(item.category||'context').toLowerCase()==='injury'?'✚':'◆'}</div>
      <div className="ss-dev-copy">
        <header><span>{String(item.category||'context').replaceAll('_',' ')}</span><small>{item.as_of?formatTime(item.as_of):''}</small></header>
        <b>{item.title}</b><p>{item.summary}</p>
        <footer><span>{item.promoted_to_model?'Validated model input':'Context only'}</span><span>{item.source_name||''}</span>{sourceLink(item)}</footer>
      </div>
    </article>)}</div>
  </section>
}

function movementRows(game,runs) {
  const cutoff=Date.parse(game.lock_timestamp_utc || game.forecast_timestamp_utc || '')
  const rows=runs.filter(row=>row.game_id===game.game_id && row.prediction_timestamp_utc).map(row=>{
    const x=Date.parse(row.prediction_timestamp_utc)
    const official=probabilityForTeam(row.final_home_prob,game.official_winner,game)
    const market=probabilityForTeam(row.market_home_prob,game.official_winner,game)
    return {x,timestamp:row.prediction_timestamp_utc,official,market}
  }).filter(row=>Number.isFinite(row.x) && row.official!=null && (!Number.isFinite(cutoff) || row.x<=cutoff+1000))
  rows.sort((a,b)=>a.x-b.x)
  return rows
}
function contextEvents(game,evidence,rows) {
  if (!rows.length) return []
  const first=rows[0].x
  const last=rows[rows.length-1].x
  const allowed=new Set(['injury','personnel','weather','travel','coaching','structural_change','scenario'])
  const seen=new Set()
  return evidence.map(item=>({
    x:Date.parse(item.as_of||''),
    timestamp:item.as_of,
    title:item.title,
    summary:item.summary,
    category:String(item.category||'context').replaceAll('_',' '),
    promoted:Boolean(item.promoted_to_model),
  })).filter(item=>Number.isFinite(item.x) && item.x>=first && item.x<=last && item.title && allowed.has(String(item.category).replaceAll(' ','_'))).filter(item=>{
    const key=`${item.timestamp}|${item.title}`
    if (seen.has(key)) return false
    seen.add(key); return true
  }).slice(-5)
}
function movementDomain(rows) {
  const values=rows.flatMap(row=>[row.official,row.market]).filter(value=>value!=null)
  if (!values.length) return [.4,.7]
  let low=Math.floor((Math.min(...values)-.03)*20)/20
  let high=Math.ceil((Math.max(...values)+.03)*20)/20
  low=Math.max(.25,low); high=Math.min(.95,high)
  if (high-low<.10) { low=Math.max(.25,low-.05); high=Math.min(.95,high+.05) }
  return [low,high]
}
function ForecastMovement({game,runs,evidence}) {
  const rows=movementRows(game,runs)
  const events=contextEvents(game,evidence,rows)
  if (rows.length<2) return <section className="ss-panel"><div className="ss-section-head"><div><span>FORECAST MOVEMENT</span></div></div><p className="ss-empty">Movement appears after the second comparable forecast run.</p></section>
  const domain=movementDomain(rows)
  const lockX=Date.parse(game.lock_timestamp_utc||'')
  const tooltip=({active,payload,label})=>{
    if (!active || !payload?.length) return null
    return <div className="ss-chart-tooltip"><b>{formatTime(new Date(label).toISOString(),{withDay:true})}</b>{payload.map(item=><span key={item.dataKey}>{item.name}: {pct(item.value,2)}</span>)}</div>
  }
  return <section className="ss-panel ss-movement">
    <div className="ss-section-head"><div><span>FORECAST MOVEMENT</span><small>LevLine vs market through the week</small></div></div>
    <div className="ss-chart-legend"><span className="lev"><i/>LevLine</span><span><i/>Market</span>{Number.isFinite(lockX)&&<span className="lock">Pregame lock</span>}</div>
    <div className="ss-chart"><ResponsiveContainer width="100%" height={280}>
      <LineChart data={rows} margin={{top:22,right:12,left:-4,bottom:8}}>
        <CartesianGrid stroke="rgba(245,241,232,.09)" vertical={false}/>
        <XAxis type="number" dataKey="x" domain={['dataMin','dataMax']} scale="time" tickFormatter={value=>new Intl.DateTimeFormat('en-US',{weekday:'short',hour:'numeric',timeZone:'America/Los_Angeles'}).format(new Date(value))} minTickGap={42} tickLine={false} axisLine={false}/>
        <YAxis domain={domain} tickFormatter={value=>`${Math.round(value*100)}%`} width={42} tickLine={false} axisLine={false}/>
        <Tooltip content={tooltip}/>
        {Number.isFinite(lockX)&&lockX>=rows[0].x&&lockX<=rows[rows.length-1].x&&<ReferenceLine x={lockX} stroke="rgba(201,179,122,.6)" strokeDasharray="4 4" label={{value:'LOCK',position:'top',fontSize:10,fill:'#c9b37a'}}/>}
        {events.map((event,index)=><ReferenceLine key={`${event.x}-${index}`} x={event.x} stroke="rgba(181,35,62,.45)" strokeDasharray="2 5" label={{value:'•',position:'top',fontSize:18,fill:'#b5233e'}}/>)}
        <Line name="LevLine" dataKey="official" type="stepAfter" stroke="#b5233e" strokeWidth={3} dot={false} activeDot={{r:5}} isAnimationActive={false}/>
        <Line name="Market" dataKey="market" type="stepAfter" stroke="#a9a298" strokeWidth={2} strokeDasharray="6 5" dot={false} activeDot={{r:4}} isAnimationActive={false}/>
      </LineChart>
    </ResponsiveContainer></div>
    {events.length>0 && <div className="ss-event-list"><span>CONTEXT ALONGSIDE MOVEMENT</span>{events.map((event,index)=><div key={`${event.title}-${index}`}><time>{formatTime(event.timestamp)}</time><b>{event.title}</b><small>{event.promoted?'Validated model input':'Context surfaced near this forecast update; not claimed as the cause.'}</small></div>)}</div>}
  </section>
}

function ModelConsensus({game,diagnostic}) {
  if (!diagnostic) return <p className="ss-empty">Component diagnostics unavailable.</p>
  const rows=[
    ['Logistic',diagnostic.logistic_home_prob],['Extra Trees',diagnostic.extra_trees_home_prob],['XGBoost',diagnostic.xgboost_home_prob],['CatBoost',diagnostic.catboost_home_prob],['Elo',diagnostic.elo_home_prob],
  ]
  return <div className="ss-model-list">{rows.map(([name,homeP])=>{const signal=signalFavorite(homeP,game);return <div key={name}><span>{name}</span><b>{signal.team} {pct(signal.probability)}</b></div>})}<p>Component diagnostics are supporting views, not competing official forecasts.</p></div>
}
function AdvancedNumbers({game,diagnostic}) {
  const independent=num(game.diagnostics?.independent_margin_home)
  const independentScore=independent==null?null:`${game.home_team} ${one(game.diagnostics?.independent_projected_home_score)} – ${game.away_team} ${one(game.diagnostics?.independent_projected_away_score)}`
  const rows=[
    ['Probability-implied home ML',moneyline(game.probability_derived_fair_home_moneyline)],
    ['Projected total',one(game.public_projected_total)],
    ['Market total',one(game.market_total)],
    ['Market probability',pct(probabilityForTeam(game.market_home_win_probability,game.official_winner,game))],
    ['Independent margin model',independent==null?'—':lineText(independent,game.home_team,game.away_team)],
    ['Independent margin score',independentScore||'—'],
    ['Model disagreement',pct(diagnostic?.model_disagreement)],
  ]
  return <div className="ss-advanced-grid">{rows.map(([label,value])=><div key={label}><span>{label}</span><b>{value}</b></div>)}<p>The independent margin model remains preserved for research and diagnostics. It does not override the probability-implied presentation line or official winner.</p></div>
}

function MatchupPage({game,runs,evidence,preview,diagnostic,gameMonitor}) {
  if (!game) return <main className="ss-page"><section className="ss-panel"><p className="ss-empty">This matchup is not in the current published slate.</p><button className="ss-text-link" onClick={()=>navigateHash('forecasts')}>Back to forecasts →</button></section></main>
  const meta=[game.venue,game.network,game.weather].filter(Boolean)
  return <main className="ss-page ss-matchup-page">
    <button className="ss-back" onClick={()=>navigateHash('forecasts')}>← Back to Week {game.week||'—'}</button>
    <section className="ss-matchup-head">
      <div className="ss-team-side"><TeamMark team={game.away_team} size="xl"/><div><span>{teamName(game.away_team)}</span>{game.away_record&&<small>{game.away_record}</small>}</div></div>
      <div className="ss-at"><b>AT</b><span>{formatKickoff(game)}</span>{meta.length>0&&<small>{meta.join(' · ')}</small>}</div>
      <div className="ss-team-side home"><TeamMark team={game.home_team} size="xl"/><div><span>{teamName(game.home_team)}</span>{game.home_record&&<small>{game.home_record}</small>}</div></div>
    </section>

    <ForecastHero game={game}/>
    <SignalFlow game={game} variant="ss-desktop-flow"/>

    <div className="ss-matchup-grid">
      <div className="ss-matchup-main">
        <TheSignal preview={preview}/>
        <ForecastMovement game={game} runs={runs} evidence={evidence}/>
        <KeyDevelopments evidence={evidence} preview={preview}/>
        <SignalFlow game={game} variant="ss-mobile-flow"/>
        <ImpactMonitor gameMonitor={gameMonitor}/>
      </div>
      <aside className="ss-matchup-side">
        <details className="ss-disclosure" open>
          <summary>Advanced Numbers <span>Show</span></summary>
          <AdvancedNumbers game={game} diagnostic={diagnostic}/>
        </details>
        <details className="ss-disclosure">
          <summary>Model Consensus <span>Components</span></summary>
          <ModelConsensus game={game} diagnostic={diagnostic}/>
        </details>
        <details className="ss-disclosure">
          <summary>Technical Details <span>Provenance</span></summary>
          <div className="ss-tech">
            <p><b>Official probability:</b> {pct(game.official_winner_probability,2)} on {game.official_winner}. This is the only public winner probability.</p>
            <p><b>Probability-implied line:</b> a deterministic probability-to-margin presentation bridge using the forecast's existing margin uncertainty. It is not an expected-margin forecast.</p>
            <p><b>Contract:</b> v{game.contract_version} · source {game.source_snapshot} · signal {game.signals?.football?.kind||'unavailable'}.</p>
            {game.provenance?.artifact_id&&<p><b>Reproducibility:</b> {game.provenance.artifact_id} · model {game.provenance.model_version||'—'}.</p>}
          </div>
        </details>
        <button className="ss-how-link" onClick={()=>navigateHash('methodology')}>How LevLine works →</button>
      </aside>
    </div>
  </main>
}

function PageHead({kicker,title,copy}) {
  return <section className="ss-page-head"><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></section>
}

function PowerPage({ratings,editorial}) {
  const byTeam=Object.fromEntries((editorial?.teams||[]).map(item=>[item.team,item]))
  return <main className="ss-page">
    <PageHead kicker="POWER RATINGS" title="Current team strength." copy="Elo+ sets the published order. Supporting efficiency and editorial context explain the ranking without becoming another hidden forecast."/>
    <section className="ss-power-board">
      <div className="ss-power-labels"><span>RANK</span><span>TEAM</span><span>ELO+</span><span>MOVE</span><span>CONTEXT</span></div>
      {[...ratings].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999)).map(row=>{
        const note=byTeam[row.team]||{}
        return <article key={row.team}>
          <strong>#{row.rank}</strong><div className="ss-power-team"><TeamMark team={row.team}/><b>{teamName(row.team)}</b></div>
          <span>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</span>
          <span className="ss-power-move">{note.movement||row.movement||'→'}</span>
          <p>{note.why_here||'Supporting context is still being assembled.'}</p>
        </article>
      })}
    </section>
  </main>
}

function HistoryPage({history,autopsies}) {
  const correctFor=row=>{
    const item=autopsies[row.game_id]||{}
    const value=item.winner_correct ?? item.correct ?? row.winner_correct
    if (value==null || value==='') return null
    return String(value).toLowerCase()==='true'
  }
  const locked=history.filter(row=>row.lock_status==='LOCKED' && String(row.season||'2026')==='2026')
  const graded=locked.filter(row=>correctFor(row)!=null)
  const wins=graded.filter(row=>correctFor(row)===true).length
  const receipt=row=>{
    const hp=num(row.final_home_prob)
    const pick=row.pick||(hp!=null?(hp>=.5?row.home_team:row.away_team):'—')
    const pickP=hp==null?null:(pick===row.home_team?hp:1-hp)
    return {pick,pickP}
  }
  return <main className="ss-page ss-history">
    <PageHead kicker="OFFICIAL HISTORY · 2026 PICKS OF RECORD" title="Immutable pregame receipts." copy="The first valid pregame lock is the official forecast of record. Later refreshes cannot replace the official pick after kickoff."/>
    <section className="ss-history-stats">
      <div><b>{locked.length}</b><span>Official Picks</span></div>
      <div><b>{graded.length?`${wins}-${graded.length-wins}`:'—'}</b><span>Graded Record</span></div>
      <div><b>{graded.length?pct(wins/graded.length,0):'—'}</b><span>Winner Accuracy</span></div>
      <div><b>{locked.length-graded.length}</b><span>Pending</span></div>
    </section>
    <section className="ss-history-table">
      <div className="ss-history-labels"><span>WEEK</span><span>MATCHUP</span><span>OFFICIAL PICK</span><span>PROBABILITY</span><span>LOCKED</span><span>RESULT</span></div>
      {locked.map((row,index)=>{const correct=correctFor(row);const {pick,pickP}=receipt(row);return <article key={`${row.game_id}-${index}`}>
        <span>{row.week||'—'}</span><span>{row.away_team} @ {row.home_team}</span><b>{pick}</b><strong>{pct(pickP)}</strong><span>{formatTime(row.lock_timestamp_utc)}</span><span className={`ss-result ${correct===true?'correct':correct===false?'miss':'pending'}`}>{correct==null?'Pending':correct?'✓ Correct':'✕ Miss'}</span>
      </article>})}
    </section>
    <section className="ss-history-mobile">{locked.map((row,index)=>{const correct=correctFor(row);const {pick,pickP}=receipt(row);return <article key={`${row.game_id}-m-${index}`}>
      <header><span>WEEK {row.week||'—'}</span><b>{correct==null?'PENDING':'FINAL'}</b></header>
      <h3>{row.away_team} @ {row.home_team}</h3>
      <small>PICK OF RECORD</small><strong>{teamName(pick)}</strong><b>{pct(pickP)}</b>
      <footer><span>Locked {formatTime(row.lock_timestamp_utc)}</span><span className={`ss-result ${correct===true?'correct':correct===false?'miss':'pending'}`}>{correct==null?'Pending':correct?'✓ Correct':'✕ Miss'}</span></footer>
    </article>})}</section>
  </main>
}

function TeamsPage({profiles,editorial}) {
  const byTeam=Object.fromEntries((editorial?.teams||[]).map(item=>[item.team,item]))
  return <main className="ss-page">
    <PageHead kicker="TEAMS" title="The league through LevLine." copy="Published team strength, next-opponent context, and the next forecast using existing profile data."/>
    <section className="ss-team-grid">{[...profiles].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999)).map(row=>{
      const note=byTeam[row.team]||{}
      return <article key={row.team}><header><TeamMark team={row.team}/><span>#{row.rank||'—'} {note.movement||''}</span></header><h3>{teamName(row.team)}</h3><div><span>Elo+</span><b>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</b></div><div><span>Next</span><b>{row.next_opponent?`${row.next_site==='HOME'?'vs':'@'} ${row.next_opponent}`:'TBD'}</b></div><div><span>Next win</span><b>{pct(row.next_win_prob)}</b></div>{note.why_here&&<p>{note.why_here}</p>}</article>
    })}</section>
  </main>
}

function MethodologyPage({models}) {
  return <main className="ss-page ss-method">
    <PageHead kicker="METHODOLOGY" title="How LevLine works." copy="Simple by default. Deep on demand. The system keeps football signal, market intelligence, official probability, presentation translation, and immutable history conceptually separate."/>
    <section className="ss-why-levline">
      <img src={`${BASE}brand/sunday-signal-icon.svg`} alt=""/>
      <div><span>WHY LEVLINE?</span><h2>A disciplined forecasting system with visible signal separation and receipts.</h2><p>LevLine combines a leakage-safe football-only view with current vig-free market information inside a frozen probability architecture. Sunday Signal keeps those inputs visible, keeps context separate from authorized probability features, shows forecast movement, and preserves the first valid pregame lock as the pick of record.</p></div>
    </section>
    <section className="ss-method-flow">
      <article><i>01</i><b>Football Signal</b><p>Pregame team efficiency, opponent-adjusted football state, Elo and component models produce the football-only probability without using the current game's market as a football feature.</p></article>
      <article><i>02</i><b>Market Signal</b><p>Current moneyline prices are converted to a vig-free home-win probability and timestamped independently from the football forecast.</p></article>
      <article><i>03</i><b>Official LevLine Probability</b><p>The frozen 2026 architecture combines the football and market signals. Football/market disagreement remains visible rather than being hidden.</p></article>
      <article><i>04</i><b>Probability-Implied Line</b><p>The official probability is mapped to a presentation margin using the existing margin uncertainty. It is a presentation translation, not a validated expected-margin prediction.</p></article>
      <article><i>05</i><b>Pregame Lock</b><p>The first valid forecast inside the existing lock window becomes immutable. Later refreshes cannot replace the pick of record after kickoff.</p></article>
      <article><i>06</i><b>Grade & Audit</b><p>Winner accuracy is displayed alongside the probability system's existing calibration and scoring diagnostics.</p></article>
    </section>
    <section className="ss-method-principles">
      <article><span>NO LEAKAGE</span><h3>Chronological validation</h3><p>Training and validation move forward through time. Later outcomes never flow backward into an earlier evaluation window.</p></article>
      <article><span>SEPARATE TARGETS</span><h3>Probability, margin and total keep distinct roles</h3><p>The independent margin model remains preserved for research and diagnostics. The consumer probability-implied line does not replace it.</p></article>
      <article><span>TRANSPARENCY</span><h3>Research context stays labeled</h3><p>Explainability-only material is not visually upgraded into an authorized F-ST probability input.</p></article>
      <article><span>IMMUTABLE HISTORY</span><h3>Receipts stay receipts</h3><p>The official pregame forecast is preserved so the published record cannot be rewritten after the result.</p></article>
    </section>
    <details className="ss-method-tech"><summary>Technical details</summary><div><h3>Frozen production probability architecture</h3><p><code>logit(P_home) = -0.06954 + 1.19391 × logit(P_market) − 0.19343 × logit(P_nested_football)</code></p><p>The production artifact is versioned as <code>F-ST-01-FROZEN-2026</code>. The architecture name is provenance metadata, not consumer-facing model branding.</p><h3>Probability-to-margin bridge</h3><p><code>presentation_margin = margin_sigma × Φ⁻¹(P_home)</code></p><p>This bridge enforces directional and probabilistic coherence for the displayed probability-implied line without rewriting the separately trained independent margin model.</p></div></details>
    {models.length>0&&<details className="ss-method-tech"><summary>Historical validation table</summary><div className="ss-table-wrap"><table><thead><tr><th>Model</th><th>Games</th><th>Winner%</th><th>Brier</th><th>Log loss</th><th>Margin MAE</th></tr></thead><tbody>{models.map((row,index)=><tr key={`${row.model}-${index}`}><td>{row.model==='Final Ensemble'?'LevLine':row.model}</td><td>{row.games||'—'}</td><td>{row.winner_pct||row.winner_accuracy||'—'}</td><td>{row.brier||row.brier_score||'—'}</td><td>{row.log_loss||'—'}</td><td>{row.margin_mae||'—'}</td></tr>)}</tbody></table></div></details>}
  </main>
}

function MorePage() {
  return <main className="ss-page"><PageHead kicker="MORE" title="Explore Sunday Signal." copy="Secondary product and trust surfaces."/>
    <section className="ss-more-grid">
      <button onClick={()=>navigateHash('methodology')}><span>01</span><b>Methodology</b><p>How LevLine works, including Why LevLine?</p></button>
      <button onClick={()=>navigateHash('teams')}><span>02</span><b>Teams</b><p>Team profiles using the existing published profile data.</p></button>
      <button onClick={()=>navigateHash('history')}><span>03</span><b>Official History</b><p>2026 picks of record and immutable pregame receipts.</p></button>
    </section>
  </main>
}

function diagnosticMap(current,history) {
  const locked=Object.fromEntries(history.filter(row=>row.lock_status==='LOCKED').map(row=>[row.game_id,row]))
  const live=Object.fromEntries(current.map(row=>[row.game_id,row]))
  return new Proxy({}, {get:(_,gameId)=>locked[gameId]||live[gameId]})
}

export default function App() {
  const [route,setRoute]=useState(()=>parseRoute())
  const [forecastPayload,setForecastPayload]=useState({games:[]})
  const [impactMonitor,setImpactMonitor]=useState({games:[]})
  const [runs,setRuns]=useState([]), [evidence,setEvidence]=useState({}), [previews,setPreviews]=useState({}), [status,setStatus]=useState({})
  const [ratings,setRatings]=useState([]), [models,setModels]=useState([]), [history,setHistory]=useState([]), [profiles,setProfiles]=useState([]), [autopsies,setAutopsies]=useState({}), [editorial,setEditorial]=useState({teams:[]}), [currentRaw,setCurrentRaw]=useState([])
  const [error,setError]=useState('')

  useEffect(()=>{
    const onHash=()=>{setRoute(parseRoute());window.scrollTo({top:0})}
    window.addEventListener('hashchange',onHash)
    return ()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{;(async()=>{try{
    const [publicForecasts,runRows,context,previewRows,statusRows,powerRows,modelRows,historyRows,profileRows,autopsyRows,editorialRows,currentRows,impactRows]=await Promise.all([
      fetchJSON('public_forecasts.json',{games:[]}),fetchCSV('run_history.csv'),fetchJSON('contextual_evidence.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('status.json',{}),fetchCSV('power_ratings.csv'),fetchCSV('model_leaderboard.csv'),fetchCSV('prediction_history.csv'),fetchCSV('team_profiles.csv'),fetchJSON('postgame_autopsies.json',{}),fetchJSON('power_editorial.json',{teams:[]}),fetchCSV('this_week.csv'),fetchJSON('impact_monitor.json',{games:[]}),
    ])
    if (!Array.isArray(publicForecasts.games) || !publicForecasts.games.length) throw new Error('Canonical public forecast contract is unavailable.')
    setForecastPayload(publicForecasts);setImpactMonitor(impactRows);setRuns(runRows);setEvidence(context);setPreviews(previewRows);setStatus(statusRows);setRatings(powerRows);setModels(modelRows);setHistory(historyRows);setProfiles(profileRows);setAutopsies(autopsyRows);setEditorial(editorialRows);setCurrentRaw(currentRows)
  }catch(err){setError(String(err?.message||err))}})()},[])

  const games=forecastPayload.games||[]
  const week=Number(games[0]?.week||0)
  const diagnostics=useMemo(()=>diagnosticMap(currentRaw,history),[currentRaw,history])
  const selected=route.page==='game' ? games.find(game=>game.game_id===route.gameId) : null
  const selectedMonitor=selected ? (impactMonitor?.games||[]).find(row=>row.game_id===selected.game_id) : null
  const openGame=game=>navigateHash(`game/${encodeURIComponent(game.game_id)}`)

  if (error) return <div className="ss-fatal"><BrandLockup/><b>Sunday Signal could not publish this slate.</b><span>{error}</span><small>The public forecast contract fails closed rather than showing contradictory or post-lock values.</small></div>

  return <div className="ss-app">
    <Header route={route} week={week}/>
    {route.page==='forecasts'&&<ForecastBoard games={games} previews={previews} onOpen={openGame} status={status}/>} 
    {route.page==='game'&&<MatchupPage game={selected} runs={runs} evidence={selected?(evidence[selected.game_id]||[]):[]} preview={selected?previews[selected.game_id]:null} diagnostic={selected?diagnostics[selected.game_id]:null} gameMonitor={selectedMonitor}/>} 
    {route.page==='power'&&<PowerPage ratings={ratings} editorial={editorial}/>} 
    {route.page==='history'&&<HistoryPage history={history} autopsies={autopsies}/>} 
    {route.page==='methodology'&&<MethodologyPage models={models}/>} 
    {route.page==='teams'&&<TeamsPage profiles={profiles} editorial={editorial}/>} 
    {route.page==='more'&&<MorePage/>}
    <footer className="ss-footer"><BrandLockup compact/><span>One LevLine forecast per game · locked before kickoff · graded after</span><button onClick={()=>navigateHash('methodology')}>How LevLine Works</button></footer>
    <MobileNav route={route}/>
  </div>
}
