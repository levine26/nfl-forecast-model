import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import './matchup-decision-layer.css'

const BASE = import.meta.env.BASE_URL

const num = value => {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}
const pct = (value,digits=0) => num(value)==null ? '—' : `${(num(value)*100).toFixed(digits)}%`
const pp = value => num(value)==null ? '—' : `${num(value)>=0?'+':''}${num(value).toFixed(1)} pp`

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
  return new Intl.DateTimeFormat('en-US',{
    weekday:'short',hour:'numeric',minute:'2-digit',timeZone:'America/Los_Angeles',timeZoneName:'short',
  }).format(date)
}

function routeFromHash() {
  const raw=window.location.hash.replace(/^#\/?/,'')
  const parts=raw.split('/').filter(Boolean)
  if (parts[0]==='game' && parts[1]) return {page:'game',gameId:decodeURIComponent(parts.slice(1).join('/'))}
  return {page:parts[0]||'forecasts'}
}

function probabilityForTeam(homeP,team,game) {
  const p=num(homeP)
  if (p==null || !team) return null
  return team===game.home_team ? p : 1-p
}

function favorite(homeP,game) {
  const p=num(homeP)
  if (p==null) return {team:'—',probability:null}
  if (Math.abs(p-.5)<1e-10) return {team:'Pick’em',probability:.5}
  return p>.5 ? {team:game.home_team,probability:p} : {team:game.away_team,probability:1-p}
}

function PortalSlot({children}) {
  const [host,setHost]=useState(null)
  useEffect(()=>{
    let observer
    const attach=()=>{
      const target=document.querySelector('.ss-matchup-main > .ss-the-signal')
      if (!target) return
      let node=document.getElementById('ss-decision-layer-host')
      if (!node) {
        node=document.createElement('div')
        node.id='ss-decision-layer-host'
        node.className='ss-decision-layer-host'
        target.insertAdjacentElement('beforebegin',node)
      }
      setHost(node)
    }
    attach()
    observer=new MutationObserver(attach)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return ()=>{
      observer.disconnect()
      document.getElementById('ss-decision-layer-host')?.remove()
      setHost(null)
    }
  },[])
  return host ? createPortal(children,host) : null
}

function DecisionPoints({preview,game}) {
  const factors=(preview?.key_factors||[]).filter(item=>item?.title).slice(0,3)
  const football=favorite(game.football_only_home_win_probability,game)
  const market=favorite(game.market_home_win_probability,game)
  const officialP=num(game.official_winner_probability)
  const marketOnPick=probabilityForTeam(game.market_home_win_probability,game.official_winner,game)
  const delta=officialP!=null&&marketOnPick!=null?(officialP-marketOnPick)*100:num(game.levline_vs_market_winner_probability_pp)

  return <section className="mdl-panel mdl-decision-points">
    <header className="mdl-head">
      <div><span>DECISION POINTS</span><h3>The three things most likely to decide this matchup.</h3></div>
      <small>Editorial context only · official forecast unchanged</small>
    </header>
    <div className="mdl-factor-grid">
      {factors.length>0 ? factors.map((factor,index)=><article key={`${factor.title}-${index}`}>
        <i>0{index+1}</i>
        <div><span>{factor.advantage_team||factor.strength||'WATCH'}</span><b>{factor.title}</b>{factor.summary&&<p>{factor.summary}</p>}</div>
      </article>) : <p className="mdl-empty">Decision points will appear when the researched matchup read publishes.</p>}
    </div>
    <div className="mdl-lean-row">
      <article><span>FOOTBALL LEAN</span><b>{football.team} {pct(football.probability)}</b><small>Football-only signal before the current market is combined.</small></article>
      <article><span>MARKET VIEW</span><b>{market.team} {pct(market.probability)}</b><small>Current vig-free market probability.</small></article>
      <article className="final"><span>LEVLINE FINAL</span><b>{game.official_winner} {pct(game.official_winner_probability)}</b><small>{delta==null?'Market delta unavailable':`${pp(delta)} versus the market on the official pick.`}</small></article>
    </div>
  </section>
}

function PersonnelMatchup({evidence}) {
  const allowed=new Set(['injury','personnel','availability','depth_chart','depth chart'])
  const items=(evidence||[]).filter(item=>allowed.has(String(item.category||'').toLowerCase()) && item.title && item.summary).slice(0,6)
  if (!items.length) return null
  return <section className="mdl-panel mdl-personnel">
    <header className="mdl-head"><div><span>PERSONNEL MATCHUP</span><h3>Who is actually available can change how the game is played.</h3></div><small>Source-linked context · not silently promoted into the model</small></header>
    <div className="mdl-personnel-list">{items.map((item,index)=><article key={`${item.title}-${index}`}>
      <div className="mdl-personnel-icon">{String(item.category).toLowerCase()==='injury'?'✚':'◆'}</div>
      <div>
        <header><span>{String(item.category||'personnel').replaceAll('_',' ')}</span><time>{item.as_of?formatTime(item.as_of):'—'}</time></header>
        <b>{item.title}</b><p>{item.summary}</p>
        <footer><span>{item.promoted_to_model?'Validated model input':'Context only'}</span>{item.source_name&&<span>{item.source_name}</span>}{item.source_url&&<a href={item.source_url} target="_blank" rel="noreferrer">Source ↗</a>}</footer>
      </div>
    </article>)}</div>
  </section>
}

function scenarioRows(preview,evidence) {
  const explicit=[...(Array.isArray(preview?.conditional_scenarios)?preview.conditional_scenarios:[]),...(Array.isArray(preview?.scenarios)?preview.scenarios:[])]
  const fromEvidence=(evidence||[]).filter(item=>String(item.category||'').toLowerCase()==='scenario')
  return [...explicit,...fromEvidence].map(item=>({
    title:item.title||item.condition||item.name,
    summary:item.summary||item.impact||item.description,
    asOf:item.as_of||item.timestamp,
    sourceName:item.source_name,
    sourceUrl:item.source_url,
  })).filter(item=>item.title && item.summary).slice(0,4)
}

function ConditionalScenarios({preview,evidence}) {
  const rows=scenarioRows(preview,evidence)
  if (!rows.length) return null
  return <section className="mdl-panel mdl-scenarios">
    <header className="mdl-head"><div><span>IF / THEN</span><h3>Conditional paths worth watching before kickoff.</h3></div><small>Scenario analysis · not a second forecast</small></header>
    <div className="mdl-scenario-grid">{rows.map((row,index)=><article key={`${row.title}-${index}`}>
      <i>IF</i><b>{row.title}</b><p>{row.summary}</p><footer>{row.asOf&&<time>{formatTime(row.asOf)}</time>}{row.sourceName&&<span>{row.sourceName}</span>}{row.sourceUrl&&<a href={row.sourceUrl} target="_blank" rel="noreferrer">Source ↗</a>}</footer>
    </article>)}</div>
  </section>
}

function movementEntries(game,runs) {
  const rows=(runs||[]).filter(row=>row.game_id===game.game_id && row.prediction_timestamp_utc).map(row=>({
    x:Date.parse(row.prediction_timestamp_utc),
    timestamp:row.prediction_timestamp_utc,
    official:probabilityForTeam(row.final_home_prob,game.official_winner,game),
    market:probabilityForTeam(row.market_home_prob,game.official_winner,game),
  })).filter(row=>Number.isFinite(row.x)&&row.official!=null).sort((a,b)=>a.x-b.x)
  const changes=[]
  for (let i=1;i<rows.length;i+=1) {
    const prev=rows[i-1], current=rows[i]
    const lev=(current.official-prev.official)*100
    const market=current.market!=null&&prev.market!=null?(current.market-prev.market)*100:null
    if (Math.abs(lev)<.05 && (market==null||Math.abs(market)<.05)) continue
    changes.push({timestamp:current.timestamp,levline:lev,market})
  }
  return changes.slice(-4).reverse()
}

function WhatChanged({game,runs,evidence}) {
  const moves=movementEntries(game,runs)
  const context=(evidence||[]).filter(item=>item.as_of && item.title && ['injury','personnel','weather','travel','coaching','structural_change','scenario'].includes(String(item.category||'').toLowerCase())).sort((a,b)=>Date.parse(b.as_of)-Date.parse(a.as_of)).slice(0,4)
  if (!moves.length && !context.length) return null
  return <section className="mdl-panel mdl-changes">
    <header className="mdl-head"><div><span>WHAT CHANGED?</span><h3>A timestamped audit trail, without pretending correlation is causation.</h3></div><small>Forecast movement and contextual updates remain separate</small></header>
    <div className="mdl-change-columns">
      <div><span className="mdl-subhead">FORECAST MOVES</span>{moves.length?moves.map((move,index)=><article key={`${move.timestamp}-${index}`}><time>{formatTime(move.timestamp)}</time><b>LevLine {pp(move.levline)}</b><small>{move.market==null?'Market comparison unavailable':`Market ${pp(move.market)} over the same interval.`}</small></article>):<p className="mdl-empty">No distinct probability move has published yet.</p>}</div>
      <div><span className="mdl-subhead">CONTEXT UPDATES</span>{context.length?context.map((item,index)=><article key={`${item.as_of}-${item.title}-${index}`}><time>{formatTime(item.as_of)}</time><b>{item.title}</b><small>{item.promoted_to_model?'Validated model input':'Context surfaced alongside the forecast; not claimed as the cause.'}</small></article>):<p className="mdl-empty">No timestamped contextual update is published.</p>}</div>
    </div>
  </section>
}

export default function MatchupDecisionLayer() {
  const [route,setRoute]=useState(()=>routeFromHash())
  const [data,setData]=useState({games:[],previews:{},evidence:{},runs:[]})

  useEffect(()=>{
    const onHash=()=>setRoute(routeFromHash())
    window.addEventListener('hashchange',onHash)
    return ()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{;(async()=>{
    const [forecastPayload,previews,evidence,runs]=await Promise.all([
      fetchJSON('public_forecasts.json',{games:[]}),
      fetchJSON('game_previews.json',{}),
      fetchJSON('contextual_evidence.json',{}),
      fetchCSV('run_history.csv'),
    ])
    setData({games:Array.isArray(forecastPayload.games)?forecastPayload.games:[],previews,evidence,runs})
  })()},[])

  const game=useMemo(()=>route.page==='game'?data.games.find(row=>row.game_id===route.gameId):null,[route,data.games])
  if (!game) return null
  const preview=data.previews?.[game.game_id]||null
  const evidence=data.evidence?.[game.game_id]||[]

  return <PortalSlot>
    <div className="mdl-stack">
      <DecisionPoints preview={preview} game={game}/>
      <PersonnelMatchup evidence={evidence}/>
      <ConditionalScenarios preview={preview} evidence={evidence}/>
      <WhatChanged game={game} runs={data.runs} evidence={evidence}/>
    </div>
  </PortalSlot>
}
