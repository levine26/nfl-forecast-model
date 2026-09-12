import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import './forecast-clarity.css'

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

const num = value => {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}
const pct = (value,digits=1) => num(value)==null ? '—' : `${(num(value)*100).toFixed(digits)}%`
const pts = value => num(value)==null ? '—' : `${num(value)>=0?'+':''}${num(value).toFixed(1)} pts`
const teamName = team => TEAM[team]?.[0] || team || '—'
const teamLogo = team => `https://a.espncdn.com/i/teamlogos/nfl/500/${TEAM[team]?.[1] || String(team || '').toLowerCase()}.png`

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
function formatTime(value) {
  if (!value) return '—'
  const date=new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US',{hour:'numeric',minute:'2-digit',timeZone:'America/Los_Angeles',timeZoneName:'short'}).format(date)
}
function lineText(marginHome,home,away) {
  const margin=num(marginHome)
  if (margin==null) return '—'
  if (Math.abs(margin)<.05) return 'PK'
  return margin>0 ? `${home} -${Math.abs(margin).toFixed(1)}` : `${away} -${Math.abs(margin).toFixed(1)}`
}
function scoreText(game) {
  const home=game.projected_home_score
  const away=game.projected_away_score
  if (home==null || away==null) return '—'
  return game.official_winner===game.away_team ? `${game.away_team} ${away} – ${game.home_team} ${home}` : `${game.home_team} ${home} – ${game.away_team} ${away}`
}
function probabilityForTeam(homeP,team,game) {
  const p=num(homeP)
  if (p==null || !team) return null
  return team===game.home_team ? p : 1-p
}
function signalFavorite(homeP,game) {
  const p=num(homeP)
  if (p==null) return {team:'—',probability:null}
  return p>=.5 ? {team:game.home_team,probability:p} : {team:game.away_team,probability:1-p}
}
function signalTier(probability) {
  const p=num(probability)
  if (p==null) return {key:'watch',label:'Watch'}
  if (p>=.67) return {key:'strong',label:'Strong signal'}
  if (p>=.61) return {key:'signal',label:'Signal'}
  if (p>=.56) return {key:'lean',label:'Lean'}
  return {key:'watch',label:'Watch'}
}
function agreementFor(diagnostic) {
  const value=num(diagnostic?.model_disagreement)
  if (value==null) return null
  if (value<.035) return {label:'High agreement',key:'high',value}
  if (value<.065) return {label:'Mixed agreement',key:'mixed',value}
  return {label:'Low agreement',key:'low',value}
}
function routeFromHash() {
  const parts=window.location.hash.replace(/^#\/?/,'').split('/').filter(Boolean)
  return parts[0]==='game' && parts[1] ? {page:'game',gameId:decodeURIComponent(parts.slice(1).join('/'))} : {page:parts[0]||'forecasts'}
}

function PortalSlot({anchor,position='afterend',id,children}) {
  const [host,setHost]=useState(null)
  useEffect(()=>{
    let observer
    const attach=()=>{
      const target=document.querySelector(anchor)
      if (!target) return
      let node=document.getElementById(id)
      if (!node) {
        node=document.createElement('div')
        node.id=id
        node.className='ss-clarity-host'
        target.insertAdjacentElement(position,node)
      }
      setHost(node)
    }
    attach()
    observer=new MutationObserver(attach)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return ()=>{
      observer.disconnect()
      document.getElementById(id)?.remove()
      setHost(null)
    }
  },[anchor,position,id])
  return host ? createPortal(children,host) : null
}

function movementFor(game,runs) {
  const rows=runs.filter(row=>row.game_id===game.game_id && row.prediction_timestamp_utc).map(row=>({
    x:Date.parse(row.prediction_timestamp_utc),
    timestamp:row.prediction_timestamp_utc,
    official:probabilityForTeam(row.final_home_prob,game.official_winner,game),
    market:probabilityForTeam(row.market_home_prob,game.official_winner,game),
  })).filter(row=>Number.isFinite(row.x)&&row.official!=null).sort((a,b)=>a.x-b.x)
  if (rows.length<2) return {rows,previous:null,latest:rows.at(-1)||null}
  const latest=rows.at(-1)
  const previous=[...rows].reverse().slice(1).find(row=>Math.abs(row.official-latest.official)>.0005 || (row.market!=null&&latest.market!=null&&Math.abs(row.market-latest.market)>.0005)) || rows.at(-2)
  return {rows,previous,latest}
}

function ProbabilityBar({game}) {
  const winnerP=num(game.official_winner_probability)
  if (winnerP==null) return null
  const loser=game.official_winner===game.home_team?game.away_team:game.home_team
  const loserP=1-winnerP
  return <div className="ss-clarity-probability">
    <div className="ss-clarity-prob-labels">
      <span><b>{game.official_winner}</b> {pct(winnerP)}</span>
      <span>{pct(loserP)} <b>{loser}</b></span>
    </div>
    <div className="ss-clarity-prob-track" aria-label={`${game.official_winner} ${pct(winnerP)}, ${loser} ${pct(loserP)}`}>
      <i style={{width:`${winnerP*100}%`}}/><em/>
    </div>
  </div>
}

function HistorySparkline({game,runs}) {
  const movement=useMemo(()=>movementFor(game,runs),[game,runs])
  const rows=movement.rows
  if (rows.length<2) return <p className="ss-clarity-empty">A second published forecast will unlock the movement chart.</p>
  const series=rows.slice(-12)
  const vals=series.flatMap(row=>[row.official,row.market]).filter(value=>value!=null)
  const min=Math.max(0,Math.min(...vals)-.04)
  const max=Math.min(1,Math.max(...vals)+.04)
  const range=Math.max(.08,max-min)
  const W=520, H=112, P=10
  const point=(value,index)=>{
    const x=P+(index*(W-P*2)/Math.max(1,series.length-1))
    const y=H-P-((value-min)/range)*(H-P*2)
    return [x,y]
  }
  const official=series.map((row,index)=>point(row.official,index))
  const market=series.map((row,index)=>row.market==null?null:point(row.market,index)).filter(Boolean)
  const path=points=>points.map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return <div className="ss-clarity-history">
    <div className="ss-clarity-chart-head"><span>FORECAST HISTORY</span><div><i className="levline"/>LevLine <i className="market"/>Market</div></div>
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="LevLine and market win probability history">
      <polyline className="market" points={path(market)}/>
      <polyline className="levline" points={path(official)}/>
      {official.map(([x,y],index)=><circle key={`l-${index}`} className="levline" cx={x} cy={y} r="3"><title>{formatTime(series[index].timestamp)} · LevLine {pct(series[index].official)}</title></circle>)}
      {series.map((row,index)=>row.market==null?null:(()=>{const [x,y]=point(row.market,index);return <circle key={`m-${index}`} className="market" cx={x} cy={y} r="2.5"><title>{formatTime(row.timestamp)} · Market {pct(row.market)}</title></circle>})())}
    </svg>
    <small>Hover points for published values. Movement is descriptive; no causal claim is inferred.</small>
  </div>
}

function ShareButton({game}) {
  const [state,setState]=useState('Share')
  const share=async()=>{
    const text=`Sunday Signal — ${game.away_team} @ ${game.home_team}\nLevLine: ${game.official_winner} ${pct(game.official_winner_probability)}\nFair spread: ${lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)} · Market: ${lineText(game.market_margin_home,game.home_team,game.away_team)}`
    try {
      if (navigator.share) await navigator.share({title:`Sunday Signal: ${game.away_team} @ ${game.home_team}`,text,url:window.location.href})
      else if (navigator.clipboard) { await navigator.clipboard.writeText(`${text}\n${window.location.href}`); setState('Copied'); setTimeout(()=>setState('Share'),1600) }
    } catch { /* cancellation */ }
  }
  return <button className="ss-clarity-share" onClick={share}>↗ {state}</button>
}

function ForecastClarityCard({game,runs,diagnostic}) {
  const winnerP=num(game.official_winner_probability)
  const loser=game.official_winner===game.home_team?game.away_team:game.home_team
  const loserP=winnerP==null?null:1-winnerP
  const marketP=probabilityForTeam(game.market_home_win_probability,game.official_winner,game)
  const edge=num(game.levline_vs_market_winner_probability_pp)
  const tier=signalTier(winnerP)
  const agreement=agreementFor(diagnostic)
  const football=signalFavorite(game.football_only_home_win_probability,game)
  const market=signalFavorite(game.market_home_win_probability,game)
  const movement=movementFor(game,runs)
  const previous=movement.previous
  const latest=movement.latest
  const delta=previous&&latest ? (latest.official-previous.official)*100 : null
  const marketDelta=previous&&latest&&previous.market!=null&&latest.market!=null ? (latest.market-previous.market)*100 : null
  const status=game.lifecycle_status==='LIVE_FORECAST'?'LIVE':game.lifecycle_status==='FINAL_PREGAME'?'LOCKED':game.lifecycle_status==='IN_PROGRESS'?'LIVE GAME':game.lifecycle_status==='GRADED'?'FINAL':'FORECAST'
  const stamp=game.lock_timestamp_utc||game.forecast_timestamp_utc

  return <section className="ss-clarity-shell" aria-label="LevLine forecast explained">
    <div className="ss-clarity-head">
      <div><span>LEVLINE FORECAST</span><button className="ss-clarity-info" onClick={()=>document.getElementById('ss-clarity-how')?.setAttribute('open','')}>ⓘ How to read this forecast</button></div>
      <div className={`ss-clarity-status ${String(game.lifecycle_status||'').toLowerCase()}`}><i/>{status}<small>{status==='LIVE'&&stamp?`Updated ${formatTime(stamp)}`:''}</small></div>
    </div>

    <div className="ss-clarity-primary">
      <div className="ss-clarity-pick">
        <img src={teamLogo(game.official_winner)} alt=""/>
        <div><span>{teamName(game.official_winner)} win probability</span><strong>{pct(winnerP)}</strong><small>LevLine estimates {game.official_winner} wins about {winnerP==null?'—':Math.round(winnerP*100)} of 100 comparable games.</small></div>
      </div>
      <ProbabilityBar game={game}/>
      <div className="ss-clarity-metrics">
        <article><span>LEVLINE FAIR SPREAD</span><b>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</b><small>Spread equivalent of the LevLine win forecast</small></article>
        <article><span>SPORTSBOOK SPREAD</span><b>{lineText(game.market_margin_home,game.home_team,game.away_team)}</b><small>Current consensus market line</small></article>
        <article className="edge"><span>WIN-PROBABILITY EDGE</span><b>{game.official_winner} {pts(edge)}</b><small>LevLine {pct(winnerP)} − Market {pct(marketP)}</small></article>
        <article><span>MODEL SCORE ESTIMATE</span><b>{scoreText(game)}</b><small>Approximate score consistent with the forecast</small></article>
      </div>
      <div className="ss-clarity-freshness"><span><b>Forecast</b> {game.immutable?'locked':'updated'} {formatTime(stamp)}</span><span><b>Market updated</b> {formatTime(game.market_timestamp_utc)}</span></div>
    </div>

    <div className="ss-clarity-diagnostics">
      <article><span>FORECAST TIER</span><b className={`tier ${tier.key}`}>{tier.label}</b><small>Presentation shorthand derived from the published win probability, not a second probability.</small></article>
      <article><span>SINCE LAST FORECAST</span>{previous&&latest?<><b>{game.official_winner} {pct(previous.official)} → {pct(latest.official)} {delta>=0?'↑':'↓'}</b><small>LevLine {pts(delta)}{marketDelta==null?'':` · Market ${pts(marketDelta)}`}</small></>:<><b>No comparable move yet</b><small>A second distinct forecast will populate this.</small></>}</article>
      <article className={edge!=null&&Math.abs(edge)>=2.5?'active':''}><span>LEVLINE EDGE VS MARKET</span><b>{game.official_winner} {pts(edge)}</b><small>{marketP==null?'Market comparison unavailable.':`LevLine ${pct(winnerP)} vs market-implied ${pct(marketP)}.`}</small></article>
      <article><span>MODEL AGREEMENT</span>{agreement?<><b>{agreement.label} · {(agreement.value*100).toFixed(1)} pts</b><small>Published component-disagreement diagnostic; lower means tighter agreement.</small></>:<><b>Unavailable</b><small>Diagnostic not published for this state.</small></>}</article>
      <ShareButton game={game}/>
    </div>

    <details id="ss-clarity-how" className="ss-clarity-how">
      <summary>How to read LevLine <span>Definitions for every headline number</span></summary>
      <div>
        <article><b>Win probability</b><p>LevLine's estimated chance that the listed team wins the game.</p></article>
        <article><b>Fair spread</b><p>The point spread corresponding to LevLine's published win probability.</p></article>
        <article><b>Sportsbook spread</b><p>The current consensus market line used for comparison.</p></article>
        <article><b>Win-probability edge</b><p>LevLine probability minus market-implied probability, expressed in percentage points.</p></article>
        <article><b>Model score estimate</b><p>An approximate score consistent with the forecast, not a literal exact-score prediction.</p></article>
        <article><b>Model agreement</b><p>A supporting diagnostic describing how tightly component views line up with one another.</p></article>
      </div>
    </details>

    <details className="ss-clarity-model-details">
      <summary>Model details <span>Forecast history, movement & component signals</span></summary>
      <div className="ss-clarity-detail-grid">
        <HistorySparkline game={game} runs={runs}/>
        <section className="ss-clarity-flow" aria-label="How the forecast comes together">
          <div className="ss-clarity-section-label">HOW THE FORECAST COMES TOGETHER</div>
          <div className="ss-clarity-flow-inputs">
            <article><span>FOOTBALL FACTORS</span><b>Lean: {football.team}</b><strong>{pct(football.probability)}</strong><small>Football-only component model · team, talent, scheme & matchup data</small></article>
            <article><span>MARKET FACTORS</span><b>Lean: {market.team}</b><strong>{pct(market.probability)}</strong><small>Current vig-free market probability</small></article>
          </div>
          <div className="ss-clarity-converge"><span>Inputs feed the calibrated model</span>↓</div>
          <article className="ss-clarity-final"><span>LEVLINE FORECAST</span><img src={teamLogo(game.official_winner)} alt=""/><div><b>{game.official_winner} {pct(winnerP)}</b><small>{loser} {pct(loserP)}</small></div></article>
          <p>These percentages represent distinct model roles. They are not values that are added together.</p>
        </section>
      </div>
    </details>
  </section>
}

export default function ForecastClarity() {
  const [route,setRoute]=useState(()=>routeFromHash())
  const [data,setData]=useState({games:[],runs:[],current:[]})

  useEffect(()=>{
    const onHash=()=>setRoute(routeFromHash())
    window.addEventListener('hashchange',onHash)
    return ()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{;(async()=>{
    const [forecastPayload,runs,current]=await Promise.all([
      fetchJSON('public_forecasts.json',{games:[]}),
      fetchCSV('run_history.csv'),
      fetchCSV('this_week.csv'),
    ])
    setData({games:Array.isArray(forecastPayload.games)?forecastPayload.games:[],runs,current})
  })()},[])

  useEffect(()=>{
    document.body.classList.toggle('ss-clarity-game',route.page==='game')
    return ()=>document.body.classList.remove('ss-clarity-game')
  },[route.page])

  const selected=route.page==='game'?data.games.find(game=>game.game_id===route.gameId):null
  const diagnostic=selected ? data.current.find(row=>row.game_id===selected.game_id) : null
  if (!selected) return null

  return <PortalSlot anchor=".ss-matchup-head" position="afterend" id="ss-forecast-clarity">
    <ForecastClarityCard game={selected} runs={data.runs} diagnostic={diagnostic}/>
  </PortalSlot>
}
