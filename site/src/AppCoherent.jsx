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
import './coherent.css'

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
function interpretation(game) {
  const marketP=probabilityForTeam(game.market_home_win_probability,game.official_winner,game)
  const official=game.official_winner_probability
  if (marketP==null) return `LevLine makes ${game.official_winner} the more likely winner at ${pct(official)}.`
  const delta=(official-marketP)*100
  if (Math.abs(delta)<.75) return `LevLine and the market are essentially aligned on ${game.official_winner}.`
  return `LevLine makes ${game.official_winner} ${Math.abs(delta).toFixed(1)} percentage points ${delta>0?'stronger':'weaker'} than the market does.`
}

function lifecycleLabel(status) {
  return ({LIVE_FORECAST:'LIVE FORECAST',FINAL_PREGAME:'FINAL PREGAME',IN_PROGRESS:'IN PROGRESS',GRADED:'GRADED'})[status] || status || 'FORECAST'
}

function TeamMark({team,size='md'}) {
  const [failed,setFailed]=useState(false)
  return <span className={`co-team-mark ${size}`}>
    {!failed && <img src={teamLogo(team)} alt="" onError={()=>setFailed(true)}/>} 
    {failed && <b>{team}</b>}
  </span>
}

function Lifecycle({game}) {
  return <span className={`co-life ${String(game.lifecycle_status||'').toLowerCase()}`}>
    {lifecycleLabel(game.lifecycle_status)}
  </span>
}

function Header({tab,setTab,week,status}) {
  const tabs=[['week','Forecasts'],['teams','Teams'],['power','Power'],['history','History'],['method','Methodology']]
  return <>
    <header className="co-header">
      <button className="co-brand" onClick={()=>setTab('week')}>
        <img src={`${BASE}brand/sunday-signal-icon.svg`} alt=""/>
        <span><b>SUNDAY SIGNAL</b><small>powered by LevLine</small></span>
      </button>
      <div className="co-header-state"><small>2026 · WEEK {week||'—'}</small><b>LevLine</b></div>
    </header>
    <nav className="co-nav">{tabs.map(([key,label])=><button key={key} className={tab===key?'active':''} onClick={()=>setTab(key)}>{label}</button>)}</nav>
    <div className="co-fresh"><span>Forecast feed {status?.generated_utc?`updated ${formatTime(status.generated_utc)}`:'loading'}</span><span>Forecast and market timestamps shown separately per game</span></div>
  </>
}

function SignalBreakdown({game}) {
  const football=signalFavorite(game.football_only_home_win_probability,game)
  const market=signalFavorite(game.market_home_win_probability,game)
  return <section className="co-signals" aria-label="LevLine signal breakdown">
    <div><span>FOOTBALL SIGNAL</span><b>{football.team} {pct(football.probability)}</b><small>Independent football view</small></div>
    <i aria-hidden="true">+</i>
    <div className="market"><span>MARKET SIGNAL</span><b>{market.team} {pct(market.probability)}</b><small>Vig-free market view</small></div>
    <i aria-hidden="true">→</i>
    <div className="official"><span>LEVLINE</span><b>{game.official_winner} {pct(game.official_winner_probability)}</b><small>Official forecast</small></div>
  </section>
}

function ForecastSummary({game,large=false}) {
  return <section className={`co-forecast-summary ${large?'large':''}`}>
    <div className="co-forecast-primary">
      <span>LEVLINE FORECAST</span>
      <strong>{game.official_winner} <b>{pct(game.official_winner_probability)}</b></strong>
      <p>{interpretation(game)}</p>
    </div>
    <div className="co-forecast-numbers">
      <div><span>Fair line</span><b>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</b></div>
      <div><span>Approx. score</span><b>{scoreText(game)}</b></div>
      <div><span>Market</span><b>{lineText(game.market_margin_home,game.home_team,game.away_team)}</b><small>{pct(probabilityForTeam(game.market_home_win_probability,game.official_winner,game))} on {game.official_winner}</small></div>
    </div>
  </section>
}

function GameCard({game,preview,onOpen}) {
  const development=preview?.key_factors?.[0]?.title || preview?.headline
  return <button className="co-game-card" onClick={onOpen}>
    <div className="co-card-meta"><span>{formatKickoff(game)}</span><Lifecycle game={game}/></div>
    <div className="co-matchup">
      <span><TeamMark team={game.away_team}/><b>{game.away_team}</b></span>
      <em>@</em>
      <span><TeamMark team={game.home_team}/><b>{game.home_team}</b></span>
    </div>
    <ForecastSummary game={game}/>
    <div className="co-card-market"><span>LEVLINE VS MARKET</span><b>{pp(game.levline_vs_market_winner_probability_pp)}</b><small>difference on {game.official_winner} win probability</small></div>
    {development && <div className="co-card-development"><span>LATEST SIGNAL</span><p>{development}</p></div>}
    <div className="co-open">Open game forecast <span>→</span></div>
  </button>
}

function WeekPage({games,previews,onOpen}) {
  const sorted=[...games].sort((a,b)=>new Date(a.kickoff_utc||0)-new Date(b.kickoff_utc||0))
  const live=sorted.filter(g=>g.lifecycle_status==='LIVE_FORECAST').length
  const locked=sorted.filter(g=>g.immutable).length
  return <main className="co-page">
    <section className="co-page-hero">
      <div><span>WEEK {games[0]?.week||'—'} · NFL</span><h1>One forecast. Clear signals.</h1><p>Who LevLine favors, the fair line implied by that probability, the score environment, and where the market differs.</p></div>
      <div className="co-slate-status"><b>{games.length}</b><span>games</span><b>{live}</b><span>live forecasts</span><b>{locked}</b><span>immutable locks</span></div>
    </section>
    <div className="co-game-grid">{sorted.map(game=><GameCard key={game.game_id} game={game} preview={previews[game.game_id]} onOpen={()=>onOpen(game)}/>)}</div>
  </main>
}

function sourceLink(item) {
  return item?.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer" onClick={event=>event.stopPropagation()}>Source ↗</a> : null
}

function KeyDevelopments({evidence=[],preview}) {
  const priority=['injury','personnel','weather','travel','coaching','structural_change','scheme','matchup']
  const ranked=[...evidence].sort((a,b)=>priority.indexOf(String(a.category||'').toLowerCase())-priority.indexOf(String(b.category||'').toLowerCase()))
  const items=ranked.filter(item=>item.title && item.summary).slice(0,4)
  if (!items.length && !preview?.headline) return null
  return <section className="co-section co-developments">
    <div className="co-section-head"><span>KEY DEVELOPMENTS</span><small>Context, not automatically a model input</small></div>
    {preview?.headline && <div className="co-latest-read"><span>LATEST SIGNAL</span><b>{preview.headline}</b></div>}
    <div className="co-development-list">{items.map((item,index)=><article key={`${item.title}-${index}`}>
      <div><span>{String(item.category||'context').replaceAll('_',' ')}</span><small>{item.as_of?formatTime(item.as_of):''}</small></div>
      <b>{item.title}</b><p>{item.summary}</p><footer><span>{item.source_name||''}</span>{sourceLink(item)}</footer>
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
  if (rows.length<2) return <section className="co-section"><div className="co-section-head"><span>FORECAST MOVEMENT</span></div><p className="co-empty">Movement appears after the second comparable forecast run.</p></section>
  const domain=movementDomain(rows)
  const lockX=Date.parse(game.lock_timestamp_utc||'')
  const tooltip=({active,payload,label})=>{
    if (!active || !payload?.length) return null
    return <div className="co-chart-tooltip"><b>{formatTime(new Date(label).toISOString(),{withDay:true})}</b>{payload.map(item=><span key={item.dataKey}>{item.name}: {pct(item.value,2)}</span>)}</div>
  }
  return <section className="co-section co-movement">
    <div className="co-section-head"><span>FORECAST MOVEMENT</span><small>LevLine vs market through the week</small></div>
    <div className="co-chart-legend"><span className="lev">LevLine</span><span>Market</span>{Number.isFinite(lockX)&&<span className="lock">Pregame lock</span>}</div>
    <div className="co-chart"><ResponsiveContainer width="100%" height={270}>
      <LineChart data={rows} margin={{top:22,right:12,left:-4,bottom:8}}>
        <CartesianGrid stroke="rgba(148,163,184,.14)" vertical={false}/>
        <XAxis type="number" dataKey="x" domain={['dataMin','dataMax']} scale="time" tickFormatter={value=>new Intl.DateTimeFormat('en-US',{weekday:'short',hour:'numeric',timeZone:'America/Los_Angeles'}).format(new Date(value))} minTickGap={42} tickLine={false}/>
        <YAxis domain={domain} tickFormatter={value=>`${Math.round(value*100)}%`} width={42} tickLine={false}/>
        <Tooltip content={tooltip}/>
        {Number.isFinite(lockX)&&lockX>=rows[0].x&&lockX<=rows[rows.length-1].x&&<ReferenceLine x={lockX} className="co-lock-line" strokeDasharray="4 4" label={{value:'LOCK',position:'top',fontSize:10}}/>}
        {events.map((event,index)=><ReferenceLine key={`${event.x}-${index}`} x={event.x} className="co-event-line" strokeDasharray="2 5" label={{value:'•',position:'top',fontSize:18}}/>)}
        <Line name="LevLine" dataKey="official" type="stepAfter" stroke="var(--levline)" strokeWidth={3} dot={false} activeDot={{r:5}} isAnimationActive={false}/>
        <Line name="Market" dataKey="market" type="stepAfter" stroke="var(--muted-strong)" strokeWidth={2} strokeDasharray="6 5" dot={false} activeDot={{r:4}} isAnimationActive={false}/>
      </LineChart>
    </ResponsiveContainer></div>
    {events.length>0 && <div className="co-event-list"><span>CONTEXT ALONGSIDE MOVEMENT</span>{events.map((event,index)=><div key={`${event.title}-${index}`}><time>{formatTime(event.timestamp)}</time><b>{event.title}</b><small>{event.promoted?'Validated model input':'Context surfaced near this forecast update; not claimed as the cause.'}</small></div>)}</div>}
  </section>
}

function WhyLevLine({game,evidence=[],preview}) {
  const factors=[]
  for (const factor of preview?.key_factors||[]) {
    if (!factor?.title || !factor?.summary) continue
    const match=evidence.find(item=>item.title===factor.title)
    factors.push({...factor,source_name:match?.source_name,source_url:match?.source_url})
  }
  for (const item of evidence) {
    if (factors.length>=5) break
    if (!item?.title || !item?.summary || factors.some(f=>f.title===item.title)) continue
    factors.push(item)
  }
  return <section className="co-section co-why">
    <div className="co-section-head"><span>WHY LEVLINE?</span><small>Game-specific evidence and signal context</small></div>
    {factors.length?<div className="co-why-list">{factors.slice(0,5).map((factor,index)=><article key={`${factor.title}-${index}`}>
      <i>{String(index+1).padStart(2,'0')}</i><div><b>{factor.title}</b><p>{factor.summary}</p><footer><span>{factor.source_name||factor.strength||'Context'}</span>{sourceLink(factor)}</footer></div>
    </article>)}</div>:<p className="co-empty">No game-specific explanation has cleared the publication threshold yet.</p>}
  </section>
}

function ModelConsensus({game,diagnostic}) {
  if (!diagnostic) return <p className="co-empty">Component diagnostics unavailable.</p>
  const rows=[
    ['Logistic',diagnostic.logistic_home_prob],['Extra Trees',diagnostic.extra_trees_home_prob],['XGBoost',diagnostic.xgboost_home_prob],['CatBoost',diagnostic.catboost_home_prob],['Elo',diagnostic.elo_home_prob],
  ]
  return <div className="co-model-list">{rows.map(([name,homeP])=>{const signal=signalFavorite(homeP,game);return <div key={name}><span>{name}</span><b>{signal.team} {pct(signal.probability)}</b></div>})}<p>Component diagnostics are supporting views, not competing official forecasts.</p></div>
}

function AdvancedNumbers({game,diagnostic}) {
  const independent=num(game.diagnostics?.independent_margin_home)
  const independentScore=independent==null?null:`${game.home_team} ${one(game.diagnostics?.independent_projected_home_score)} – ${game.away_team} ${one(game.diagnostics?.independent_projected_away_score)}`
  const rows=[
    ['Fair moneyline',moneyline(game.probability_derived_fair_home_moneyline)],
    ['Projected total',one(game.public_projected_total)],
    ['Market total',one(game.market_total)],
    ['Market probability',pct(probabilityForTeam(game.market_home_win_probability,game.official_winner,game))],
    ['Independent margin model',independent==null?'—':lineText(independent,game.home_team,game.away_team)],
    ['Independent margin score',independentScore||'—'],
    ['Model disagreement',pct(diagnostic?.model_disagreement)],
  ]
  return <div className="co-advanced-grid">{rows.map(([label,value])=><div key={label}><span>{label}</span><b>{value}</b></div>)}<p>The independent margin model remains preserved for research and diagnostics. It does not override the coherent public fair line or official winner.</p></div>
}

function GameModal({game,runs,evidence,preview,diagnostic,onClose,onMethod}) {
  return <div className="co-modal-backdrop" onMouseDown={event=>{if(event.target===event.currentTarget)onClose()}}>
    <article className="co-modal" role="dialog" aria-modal="true" aria-label={`${game.away_team} at ${game.home_team} LevLine forecast`}>
      <button className="co-close" onClick={onClose} aria-label="Close">×</button>
      <header className="co-game-head">
        <div className="co-modal-matchup"><span><TeamMark team={game.away_team} size="lg"/><b>{teamName(game.away_team)}</b></span><em>@</em><span><TeamMark team={game.home_team} size="lg"/><b>{teamName(game.home_team)}</b></span></div>
        <div><span>{formatKickoff(game)}</span><Lifecycle game={game}/></div>
      </header>
      <ForecastSummary game={game} large/>
      <div className="co-time-row"><span><b>{game.immutable?'Forecast locked':'Forecast updated'}</b> {formatTime(game.lock_timestamp_utc||game.forecast_timestamp_utc)}</span><span><b>Market updated</b> {formatTime(game.market_timestamp_utc)}</span></div>
      <SignalBreakdown game={game}/>
      <KeyDevelopments evidence={evidence} preview={preview}/>
      <ForecastMovement game={game} runs={runs} evidence={evidence}/>
      <WhyLevLine game={game} evidence={evidence} preview={preview}/>
      {preview?.paragraphs?.length>0 && <section className="co-section co-read"><div className="co-section-head"><span>THE READ</span><small>Editorial context</small></div>{preview.paragraphs.slice(0,4).map((text,index)=><p key={index}>{text}</p>)}</section>}
      <section className="co-disclosure">
        <details><summary>Model Consensus <span>component diagnostics</span></summary><ModelConsensus game={game} diagnostic={diagnostic}/></details>
        <details><summary>Advanced Numbers <span>separate prediction targets</span></summary><AdvancedNumbers game={game} diagnostic={diagnostic}/></details>
        <details><summary>Technical Details <span>provenance and semantics</span></summary><div className="co-tech">
          <p><b>Official probability:</b> {pct(game.official_winner_probability,2)} on {game.official_winner}. This is the only public winner probability.</p>
          <p><b>Public fair line:</b> a deterministic probability-to-margin bridge using the forecast's existing margin uncertainty. The independently trained margin estimate remains diagnostic-only.</p>
          <p><b>Contract:</b> v{game.contract_version} · source {game.source_snapshot} · signal {game.signals?.football?.kind||'unavailable'}.</p>
          {game.provenance?.artifact_id && <p><b>Reproducibility:</b> {game.provenance.artifact_id} · model {game.provenance.model_version||'—'}.</p>}
          <button onClick={onMethod}>How LevLine works →</button>
        </div></details>
      </section>
    </article>
  </div>
}

function PageHead({kicker,title,copy}) {
  return <section className="co-simple-head"><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></section>
}

function TeamsPage({profiles,editorial}) {
  const byTeam=Object.fromEntries((editorial?.teams||[]).map(item=>[item.team,item]))
  return <main className="co-page"><PageHead kicker="32 TEAM PROFILES" title="The league through LevLine." copy="Published team strength and the next forecast, with supporting context kept separate from the official game probability."/><div className="co-team-grid">{[...profiles].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999)).map(row=>{
    const note=byTeam[row.team]||{}
    return <article key={row.team}><TeamMark team={row.team}/><span>#{row.rank||'—'} {note.movement||''}</span><h3>{teamName(row.team)}</h3><div><small>Elo+</small><b>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</b></div><div><small>Next</small><b>{row.next_opponent?`${row.next_site==='HOME'?'vs':'@'} ${row.next_opponent}`:'TBD'}</b></div><div><small>Next win</small><b>{pct(row.next_win_prob)}</b></div>{note.why_here&&<p>{note.why_here}</p>}</article>
  })}</div></main>
}

function PowerPage({ratings,editorial}) {
  const byTeam=Object.fromEntries((editorial?.teams||[]).map(item=>[item.team,item]))
  return <main className="co-page"><PageHead kicker="POWER RATINGS" title="Current team strength." copy="Elo+ sets the published order; efficiency metrics and editorial context explain the rank without becoming a second hidden ranking."/><div className="co-power-list">{[...ratings].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999)).map(row=>{
    const note=byTeam[row.team]||{}
    return <article key={row.team}><b>#{row.rank}</b><TeamMark team={row.team}/><div><h3>{teamName(row.team)}</h3><span>Elo+ {num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</span></div><p>{note.why_here||'Supporting context is still being assembled.'}</p><small>{note.movement_text||''}</small></article>
  })}</div></main>
}

function HistoryPage({history,autopsies}) {
  const correctFor=row=>{
    const item=autopsies[row.game_id]||{}
    const value=item.winner_correct ?? item.correct ?? row.winner_correct
    if (value==null || value==='') return null
    return String(value).toLowerCase()==='true'
  }
  const locked=history.filter(row=>row.lock_status==='LOCKED')
  const graded=locked.filter(row=>correctFor(row)!=null)
  const wins=graded.filter(row=>correctFor(row)===true).length
  return <main className="co-page"><PageHead kicker="OFFICIAL HISTORY" title="Immutable pregame receipts." copy="The first valid pregame lock is the forecast of record. Later refreshes cannot replace it after kickoff."/><div className="co-history-stats"><div><b>{locked.length}</b><span>official locks</span></div><div><b>{graded.length?`${wins}-${graded.length-wins}`:'—'}</b><span>graded record</span></div><div><b>{graded.length?pct(wins/graded.length,0):'—'}</b><span>winner accuracy</span></div></div><div className="co-table-wrap"><table><thead><tr><th>Week</th><th>Matchup</th><th>Pick</th><th>Probability</th><th>Locked</th><th>Result</th></tr></thead><tbody>{locked.map((row,index)=>{const correct=correctFor(row);const hp=num(row.final_home_prob);const pick=row.pick||(hp>=.5?row.home_team:row.away_team);const pickP=hp==null?null:(pick===row.home_team?hp:1-hp);return <tr key={`${row.game_id}-${index}`}><td>{row.week||'—'}</td><td>{row.away_team} @ {row.home_team}</td><td><b>{pick}</b></td><td>{pct(pickP)}</td><td>{formatTime(row.lock_timestamp_utc)}</td><td>{correct==null?'Pending':correct?'✓ Correct':'✕ Miss'}</td></tr>})}</tbody></table></div></main>
}

function MethodPage({models}) {
  return <main className="co-page co-method"><PageHead kicker="METHODOLOGY" title="How LevLine works." copy="A football forecast, a market signal, one official probability, and an immutable pregame record—with each role kept explicit."/>
    <section className="co-method-intro"><span>THE SHORT VERSION</span><h2>LevLine combines a leakage-safe football-only signal with the current vig-free market through a frozen two-input probability model. That official probability determines the published winner and a coherent public fair line.</h2></section>
    <section className="co-method-flow"><article><i>01</i><b>Football-only signal</b><p>Pregame team efficiency, opponent-adjusted football state, Elo and component models produce a nested football probability without using the current game's market as a feature.</p></article><article><i>02</i><b>Market signal</b><p>Current moneyline prices are converted to a vig-free home-win probability and timestamped independently from the football forecast.</p></article><article><i>03</i><b>Official LevLine probability</b><p>The frozen 2026 architecture combines those two inputs. Market information is an input—not the entirety of the analysis—and football/market disagreements remain visible.</p></article><article><i>04</i><b>Coherent public line</b><p>The official probability is mapped to a fair margin using the existing margin uncertainty under a normal-margin bridge. The projected total then yields an approximate whole-number score.</p></article><article><i>05</i><b>Pregame lock</b><p>The first valid forecast inside the T−120 window is immutable. Once kickoff passes, Sunday Signal refuses to substitute a newer live row for that locked forecast.</p></article><article><i>06</i><b>Grade and audit</b><p>Winner accuracy is secondary to probability quality. Calibration, Brier score and log loss measure whether LevLine's confidence was deserved.</p></article></section>
    <section className="co-method-principles"><article><span>NO LEAKAGE</span><h3>Chronological validation</h3><p>Training and validation move forward through time. Later outcomes never flow backward into an earlier evaluation window.</p></article><article><span>2026 FORWARD TEST</span><h3>No architecture selection on completed 2026 outcomes</h3><p>Completed 2026 games may update ordinary rolling pregame football state, but they cannot select, tune or refit the frozen 2026 probability architecture.</p></article><article><span>SEPARATE TARGETS</span><h3>Winner, margin and total are not secretly the same model</h3><p>The independent margin model remains preserved for research and diagnostics. Sunday Signal's consumer fair line is probability-coherent; a true joint score distribution remains a research question.</p></article><article><span>FALLBACK</span><h3>Missing market information is explicit</h3><p>If the current market is unavailable or invalid, the production system records the fallback state rather than pretending fresh market information existed.</p></article></section>
    <details className="co-method-tech"><summary>Technical details</summary><div><h3>Frozen production probability architecture</h3><p><code>logit(P_home) = -0.06954 + 1.19391 × logit(P_market) − 0.19343 × logit(P_nested_football)</code></p><p>The production artifact is versioned as <code>F-ST-01-FROZEN-2026</code>. The architecture name is provenance metadata, not consumer-facing model branding.</p><h3>Probability-to-margin bridge</h3><p><code>fair_margin = margin_sigma × Φ⁻¹(P_home)</code></p><p>This bridge enforces directional and probabilistic coherence for the public fair line without rewriting the separately trained independent margin model. A future joint win/margin/score model would require separate research evidence and explicit promotion authorization.</p></div></details>
    {models.length>0&&<details className="co-method-tech"><summary>Historical validation table</summary><div className="co-table-wrap"><table><thead><tr><th>Model</th><th>Games</th><th>Winner%</th><th>Brier</th><th>Log loss</th><th>Margin MAE</th></tr></thead><tbody>{models.map((row,index)=><tr key={`${row.model}-${index}`}><td>{row.model==='Final Ensemble'?'LevLine':row.model}</td><td>{row.games||'—'}</td><td>{row.winner_pct||row.winner_accuracy||'—'}</td><td>{row.brier||row.brier_score||'—'}</td><td>{row.log_loss||'—'}</td><td>{row.margin_mae||'—'}</td></tr>)}</tbody></table></div></details>}
  </main>
}

function diagnosticMap(current,history) {
  const locked=Object.fromEntries(history.filter(row=>row.lock_status==='LOCKED').map(row=>[row.game_id,row]))
  const live=Object.fromEntries(current.map(row=>[row.game_id,row]))
  return new Proxy({}, {get:(_,gameId)=>locked[gameId]||live[gameId]})
}

export default function App() {
  const [tab,setTab]=useState('week')
  const [forecastPayload,setForecastPayload]=useState({games:[]})
  const [runs,setRuns]=useState([]), [evidence,setEvidence]=useState({}), [previews,setPreviews]=useState({}), [status,setStatus]=useState({})
  const [ratings,setRatings]=useState([]), [models,setModels]=useState([]), [history,setHistory]=useState([]), [profiles,setProfiles]=useState([]), [autopsies,setAutopsies]=useState({}), [editorial,setEditorial]=useState({teams:[]}), [currentRaw,setCurrentRaw]=useState([])
  const [selected,setSelected]=useState(null), [error,setError]=useState('')

  useEffect(()=>{;(async()=>{try{
    const [publicForecasts,runRows,context,previewRows,statusRows,powerRows,modelRows,historyRows,profileRows,autopsyRows,editorialRows,currentRows]=await Promise.all([
      fetchJSON('public_forecasts.json',{games:[]}),fetchCSV('run_history.csv'),fetchJSON('contextual_evidence.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('status.json',{}),fetchCSV('power_ratings.csv'),fetchCSV('model_leaderboard.csv'),fetchCSV('prediction_history.csv'),fetchCSV('team_profiles.csv'),fetchJSON('postgame_autopsies.json',{}),fetchJSON('power_editorial.json',{teams:[]}),fetchCSV('this_week.csv'),
    ])
    if (!Array.isArray(publicForecasts.games) || !publicForecasts.games.length) throw new Error('Canonical public forecast contract is unavailable.')
    setForecastPayload(publicForecasts);setRuns(runRows);setEvidence(context);setPreviews(previewRows);setStatus(statusRows);setRatings(powerRows);setModels(modelRows);setHistory(historyRows);setProfiles(profileRows);setAutopsies(autopsyRows);setEditorial(editorialRows);setCurrentRaw(currentRows)
  }catch(err){setError(String(err?.message||err))}})()},[])

  const games=forecastPayload.games||[]
  const week=Number(games[0]?.week||0)
  const diagnostics=useMemo(()=>diagnosticMap(currentRaw,history),[currentRaw,history])
  const navigate=key=>{setSelected(null);setTab(key);window.scrollTo({top:0,behavior:'smooth'})}

  if (error) return <div className="co-fatal"><b>Sunday Signal could not publish this slate.</b><span>{error}</span><small>The public forecast contract fails closed rather than showing contradictory or post-lock values.</small></div>
  return <div className="co-app">
    <Header tab={tab} setTab={navigate} week={week} status={status}/>
    {tab==='week'&&<WeekPage games={games} previews={previews} onOpen={setSelected}/>} 
    {tab==='teams'&&<TeamsPage profiles={profiles} editorial={editorial}/>} 
    {tab==='power'&&<PowerPage ratings={ratings} editorial={editorial}/>} 
    {tab==='history'&&<HistoryPage history={history} autopsies={autopsies}/>} 
    {tab==='method'&&<MethodPage models={models}/>} 
    {selected&&<GameModal game={selected} runs={runs} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} diagnostic={diagnostics[selected.game_id]} onClose={()=>setSelected(null)} onMethod={()=>navigate('method')}/>} 
    <footer className="co-footer"><b>SUNDAY SIGNAL</b><span>One LevLine forecast per game · locked before kickoff · graded after</span></footer>
  </div>
}
