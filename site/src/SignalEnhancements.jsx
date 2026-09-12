import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import './signal-enhancements.css'

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
const pct = (value,digits=0) => num(value)==null ? '—' : `${(num(value)*100).toFixed(digits)}%`
const pp = value => num(value)==null ? '—' : `${num(value)>=0?'+':''}${num(value).toFixed(1)} pp`
const signed = (value,digits=3) => num(value)==null ? '—' : `${num(value)>=0?'+':''}${num(value).toFixed(digits)}`

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
function lineText(marginHome,home,away) {
  const margin=num(marginHome)
  if (margin==null) return '—'
  if (Math.abs(margin)<.05) return 'PK'
  return margin>0 ? `${home} -${Math.abs(margin).toFixed(1)}` : `${away} -${Math.abs(margin).toFixed(1)}`
}
function probabilityForTeam(homeP,team,game) {
  const p=num(homeP)
  if (p==null || !team) return null
  return team===game.home_team ? p : 1-p
}
function signalTier(probability) {
  const p=num(probability)
  if (p==null) return {key:'watch',label:'WATCH'}
  if (p>=.67) return {key:'strong',label:'STRONG SIGNAL'}
  if (p>=.61) return {key:'signal',label:'SIGNAL'}
  if (p>=.56) return {key:'lean',label:'LEAN'}
  return {key:'watch',label:'WATCH'}
}
function routeFromHash() {
  const raw=window.location.hash.replace(/^#\/?/,'')
  const parts=raw.split('/').filter(Boolean)
  if (parts[0]==='game' && parts[1]) return {page:'game',gameId:decodeURIComponent(parts.slice(1).join('/'))}
  return {page:parts[0]||'forecasts'}
}
function openGame(game) {
  if (game?.game_id) window.location.hash=`#/game/${encodeURIComponent(game.game_id)}`
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
        node.className='ss-plus-host'
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

function TeamBadge({team}) {
  return <span className="ss-plus-team"><img src={teamLogo(team)} alt=""/><b>{team}</b></span>
}
function TierPill({probability,compact=false}) {
  const tier=signalTier(probability)
  return <span className={`ss-plus-tier ${tier.key} ${compact?'compact':''}`} title="Presentation tier derived from the published win probability; this is not a separate model output.">{tier.label}</span>
}

function movementFor(game,runs) {
  const rows=runs.filter(row=>row.game_id===game.game_id && row.prediction_timestamp_utc).map(row=>({
    x:Date.parse(row.prediction_timestamp_utc),
    official:probabilityForTeam(row.final_home_prob,game.official_winner,game),
    market:probabilityForTeam(row.market_home_prob,game.official_winner,game),
  })).filter(row=>Number.isFinite(row.x)&&row.official!=null).sort((a,b)=>a.x-b.x)
  if (rows.length<2) return null
  const latest=rows.at(-1)
  const previous=[...rows].reverse().slice(1).find(row=>Math.abs(row.official-latest.official)>.0005 || (row.market!=null&&latest.market!=null&&Math.abs(row.market-latest.market)>.0005)) || rows.at(-2)
  return {
    levline:(latest.official-previous.official)*100,
    market:latest.market!=null&&previous.market!=null?(latest.market-previous.market)*100:null,
  }
}

function SearchMatchups({games}) {
  const [query,setQuery]=useState('')
  const inputRef=useRef(null)
  useEffect(()=>{
    const handler=event=>{
      if (event.key==='/' && !['INPUT','TEXTAREA'].includes(document.activeElement?.tagName)) {
        event.preventDefault(); inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown',handler)
    return ()=>window.removeEventListener('keydown',handler)
  },[])
  const matches=useMemo(()=>{
    const q=query.trim().toLowerCase()
    if (!q) return []
    return games.filter(game=>`${game.away_team} ${teamName(game.away_team)} ${game.home_team} ${teamName(game.home_team)}`.toLowerCase().includes(q)).slice(0,5)
  },[games,query])
  return <section className="ss-plus-discovery" aria-label="Find a matchup">
    <div className="ss-plus-discovery-copy"><span>FIND YOUR GAME</span><b>Jump straight to the matchup that matters.</b><small>Press <kbd>/</kbd> anywhere to search.</small></div>
    <div className="ss-plus-search-wrap">
      <input ref={inputRef} id="ss-matchup-search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Search team or matchup…" aria-label="Search team or matchup"/>
      {matches.length>0&&<div className="ss-plus-search-results">{matches.map(game=><button key={game.game_id} onClick={()=>{setQuery('');openGame(game)}}>
        <span><TeamBadge team={game.away_team}/><i>@</i><TeamBadge team={game.home_team}/></span><b>{game.official_winner} {pct(game.official_winner_probability)}</b>
      </button>)}</div>}
    </div>
  </section>
}

function EnhancedTopSignals({games,runs}) {
  const candidates=games.filter(game=>num(game.official_winner_probability)!=null)
  if (!candidates.length) return null
  const strongest=[...candidates].sort((a,b)=>num(b.official_winner_probability)-num(a.official_winner_probability))[0]
  const positive=[...candidates].filter(game=>num(game.levline_vs_market_winner_probability_pp)>0).sort((a,b)=>num(b.levline_vs_market_winner_probability_pp)-num(a.levline_vs_market_winner_probability_pp))[0]
  const disagreement=[...candidates].filter(game=>game.game_id!==strongest?.game_id&&game.game_id!==positive?.game_id).sort((a,b)=>Math.abs(num(b.levline_vs_market_winner_probability_pp)||0)-Math.abs(num(a.levline_vs_market_winner_probability_pp)||0))[0]
  const cards=[
    strongest&&{label:'Featured Signal',game:strongest,featured:true},
    positive&&{label:'Best LevLine Edge',game:positive},
    disagreement&&{label:'Market Disagreement',game:disagreement},
  ].filter(Boolean)
  return <section className="ss-plus-top-signals">
    <div className="ss-plus-section-head"><div><span>TOP SIGNALS</span><small>The fastest read on the current slate.</small></div><span>Presentation tiers · published forecast only</span></div>
    <div className="ss-plus-top-grid">{cards.map(({label,game,featured},index)=>{
      const move=movementFor(game,runs)
      return <button key={`${label}-${game.game_id}`} className={featured?'featured':''} onClick={()=>openGame(game)} data-game-open>
        <div className="ss-plus-rank">0{index+1}</div>
        <div className="ss-plus-top-title"><span>{label}</span><TierPill probability={game.official_winner_probability}/></div>
        <div className="ss-plus-top-match"><TeamBadge team={game.away_team}/><i>AT</i><TeamBadge team={game.home_team}/></div>
        <div className="ss-plus-top-pick"><img src={teamLogo(game.official_winner)} alt=""/><div><small>LEVLINE PICK</small><b>{game.official_winner} {pct(game.official_winner_probability)}</b></div></div>
        <div className="ss-plus-top-meta"><span>Implied <b>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</b></span><span>vs market <b>{pp(game.levline_vs_market_winner_probability_pp)}</b></span>{move&&<span>last move <b>{pp(move.levline)}</b></span>}</div>
      </button>
    })}</div>
  </section>
}

function ModelMarketScanner({games}) {
  const edges=[...games].filter(game=>num(game.levline_vs_market_winner_probability_pp)>0).sort((a,b)=>num(b.levline_vs_market_winner_probability_pp)-num(a.levline_vs_market_winner_probability_pp)).slice(0,4)
  const disagreements=[...games].filter(game=>num(game.levline_vs_market_winner_probability_pp)!=null).sort((a,b)=>Math.abs(num(b.levline_vs_market_winner_probability_pp))-Math.abs(num(a.levline_vs_market_winner_probability_pp))).slice(0,4)
  if (!edges.length && !disagreements.length) return null
  const list=(title,sub,rows)=><article><header><div><span>{title}</span><small>{sub}</small></div></header>{rows.map(game=><button key={`${title}-${game.game_id}`} onClick={()=>openGame(game)}>
    <span><TeamBadge team={game.official_winner}/><small>{game.away_team} @ {game.home_team}</small></span><strong>{pp(game.levline_vs_market_winner_probability_pp)}</strong><TierPill probability={game.official_winner_probability} compact/>
  </button>)}</article>
  return <section className="ss-plus-market-scanner">
    {list('LEVLINE EDGES','Games where LevLine is more confident in its winner than the market.',edges)}
    {list('MODEL VS MARKET','Largest probability disagreements, regardless of direction.',disagreements)}
  </section>
}

function ShareButton({game,preview}) {
  const [state,setState]=useState('Share')
  const share=async()=>{
    const text=`Sunday Signal — ${game.away_team} @ ${game.home_team}\nLevLine: ${game.official_winner} ${pct(game.official_winner_probability)}\nImplied: ${lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)} · Market: ${lineText(game.market_margin_home,game.home_team,game.away_team)}\n${preview?.headline?`The Signal: ${preview.headline}\n`:''}powered by LevLine`
    try {
      if (navigator.share) await navigator.share({title:`Sunday Signal: ${game.away_team} @ ${game.home_team}`,text,url:window.location.href})
      else if (navigator.clipboard) { await navigator.clipboard.writeText(`${text}\n${window.location.href}`); setState('Copied'); setTimeout(()=>setState('Share'),1800) }
    } catch { /* user cancellation is not an error state */ }
  }
  return <button className="ss-plus-share" onClick={share} aria-label="Share this Sunday Signal matchup">↗ {state}</button>
}

function uncertaintyFor(diagnostic) {
  const value=num(diagnostic?.model_disagreement)
  if (value==null) return null
  const scaled=Math.max(0,Math.min(100,(value/.12)*100))
  const label=value<.035?'Tight':value<.065?'Mixed':'Wide'
  return {value,scaled,label}
}
function GameCommandBar({game,runs,preview,diagnostic}) {
  const move=movementFor(game,runs)
  const edge=num(game.levline_vs_market_winner_probability_pp)
  const uncertainty=uncertaintyFor(diagnostic)
  const marketP=probabilityForTeam(game.market_home_win_probability,game.official_winner,game)
  return <section className="ss-plus-game-command">
    <div className="ss-plus-command-primary"><TierPill probability={game.official_winner_probability}/><div><span>SIGNAL STRENGTH</span><b>{game.official_winner} {pct(game.official_winner_probability)}</b><small>Tier is a presentation shorthand, not a new model output.</small></div></div>
    <div className="ss-plus-what-changed"><span>WHAT CHANGED</span>{move?<><b>LevLine {pp(move.levline)}</b><small>{move.market==null?'Market comparison unavailable':`Market ${pp(move.market)} since the prior distinct forecast.`}</small></>:<><b>No comparable move yet</b><small>A second distinct forecast will populate this.</small></>}</div>
    <div className={`ss-plus-disagreement ${edge!=null&&Math.abs(edge)>=2.5?'active':''}`}><span>{edge!=null&&Math.abs(edge)>=2.5?'MARKET DISAGREEMENT':'MODEL VS MARKET'}</span><b>{edge==null?'—':pp(edge)}</b><small>{edge==null?'Current market comparison unavailable.':edge>=0?`LevLine is more confident in ${game.official_winner} than the market (${pct(marketP)}).`:`The market is more confident in ${game.official_winner} than LevLine (${pct(marketP)}).`}</small></div>
    <div className="ss-plus-uncertainty"><span>COMPONENT SPREAD</span>{uncertainty?<><b>{uncertainty.label} · {pct(uncertainty.value,1)}</b><i><em style={{width:`${uncertainty.scaled}%`}}/></i><small>Supporting model disagreement diagnostic.</small></>:<><b>Unavailable</b><small>Diagnostic not published for this state.</small></>}</div>
    <ShareButton game={game} preview={preview}/>
  </section>
}

function EnhancedSignal({preview}) {
  if (!preview) return null
  const headline=preview.headline || preview.key_factors?.[0]?.title
  const paragraphs=Array.isArray(preview.paragraphs)?preview.paragraphs.filter(Boolean):[]
  const factors=(preview.key_factors||[]).filter(item=>item?.title).slice(0,3)
  const sources=[]
  const seen=new Set()
  for (const item of preview.evidence_used||[]) {
    const key=item.source_name||item.source_url
    if (!key || seen.has(key)) continue
    seen.add(key); sources.push(item)
    if (sources.length>=6) break
  }
  return <section className="ss-plus-signal ss-the-signal">
    <div className="ss-plus-signal-head"><div><span>THE SIGNAL</span><small>{preview.editorial_voice?.media_source_count||sources.length||0} researched sources · {preview.editorial_version||'editorial desk'}</small></div><strong>Same game. A clearer edge.</strong></div>
    {headline?<h2>{headline}</h2>:<p className="ss-empty">Game-specific editorial intelligence has not cleared the publication threshold yet.</p>}
    {paragraphs.slice(0,2).map((text,index)=><p key={index}>{text}</p>)}
    {!paragraphs.length&&preview.key_factors?.[0]?.summary&&<p>{preview.key_factors[0].summary}</p>}
    {factors.length>0&&<div className="ss-plus-what-matters"><span>WHAT MATTERS</span><div>{factors.map((factor,index)=><article key={`${factor.title}-${index}`}>
      <header><b>{factor.advantage_team||'WATCH'}</b><small>{factor.strength||factor.family||'Context'}</small></header><strong>{factor.title}</strong>{factor.summary&&<p>{factor.summary}</p>}
    </article>)}</div></div>}
    {sources.length>0&&<details className="ss-plus-sources"><summary>Research trail <span>{sources.length} source groups</span></summary><div>{sources.map((source,index)=><a key={`${source.source_name}-${index}`} href={source.source_url||undefined} target={source.source_url?'_blank':undefined} rel="noreferrer"><span>{String(source.category||'source').replaceAll('_',' ')}</span><b>{source.source_name}</b><small>{source.strength||''}</small></a>)}</div></details>}
    {preview.guardrail&&<small className="ss-plus-guardrail">{preview.guardrail}</small>}
  </section>
}

function EnhancedPower({ratings}) {
  const sorted=[...ratings].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  if (!sorted.length) return null
  return <section className="ss-plus-power-board">
    <div className="ss-plus-power-intro"><div><span>LEAGUE LENS</span><b>Strength plus the efficiency underneath it.</b></div><small>EPA metrics are descriptive team-profile context; Elo+ remains the published order.</small></div>
    <div className="ss-plus-power-labels"><span>RANK</span><span>TEAM</span><span>ELO+</span><span>OFF EPA</span><span>DEF EPA ALLOWED</span><span>PASS EPA</span><span>RECENT WIN%</span><span>MOVE</span></div>
    {sorted.map(row=><article key={row.team}>
      <strong>#{row.rank}</strong><div className="ss-plus-power-team"><img src={teamLogo(row.team)} alt=""/><b>{teamName(row.team)}</b></div><span>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</span><span>{signed(row.off_epa)}</span><span>{signed(row.def_epa_allowed)}</span><span>{signed(row.pass_epa)}</span><span>{pct(row.recent_win_pct)}</span><span className="move">{row.movement||'→'} {num(row.rank_change)&&num(row.rank_change)!==0?Math.abs(num(row.rank_change)):''}</span>
    </article>)}
  </section>
}

function historyProbability(row) {
  const hp=num(row.final_home_prob)
  if (hp==null) return null
  const pick=row.pick||(hp>=.5?row.home_team:row.away_team)
  return pick===row.home_team?hp:1-hp
}
function truthy(value) {
  if (value==null||value==='') return null
  return String(value).toLowerCase()==='true'
}
function HistoryTiers({history}) {
  const locked=history.filter(row=>row.lock_status==='LOCKED'&&String(row.season||'2026')==='2026')
  const groups=['strong','signal','lean','watch'].map(key=>{
    const rows=locked.filter(row=>signalTier(historyProbability(row)).key===key)
    const graded=rows.filter(row=>truthy(row.winner_correct)!=null)
    const wins=graded.filter(row=>truthy(row.winner_correct)===true).length
    const tier=signalTier(key==='strong'?.7:key==='signal'?.63:key==='lean'?.58:.52)
    return {key,label:tier.label,rows,graded,wins}
  })
  return <section className="ss-plus-history-layer">
    <div className="ss-plus-section-head"><div><span>PERFORMANCE BY SIGNAL TIER</span><small>Presentation tiers applied to immutable pregame probabilities.</small></div></div>
    <div className="ss-plus-tier-stats">{groups.map(group=><article key={group.key} className={group.key}><TierPill probability={group.key==='strong'?.7:group.key==='signal'?.63:group.key==='lean'?.58:.52}/><b>{group.graded.length?`${group.wins}-${group.graded.length-group.wins}`:'—'}</b><span>{group.graded.length?pct(group.wins/group.graded.length):'No graded picks'}</span><small>{group.rows.length} official {group.rows.length===1?'pick':'picks'}</small></article>)}</div>
    <SundaySignalStandard compact/>
  </section>
}

function SundaySignalStandard({compact=false}) {
  return <section className={`ss-plus-standard ${compact?'compact':''}`}>
    <div><span>THE SUNDAY SIGNAL STANDARD</span><b>Publish it. Lock it. Grade it. Never rewrite it.</b></div>
    <ul><li>One official LevLine probability per game</li><li>Research context stays labeled and source-linked</li><li>Pregame locks become immutable receipts</li><li>Results are graded against the published record</li></ul>
  </section>
}

function StatusStrip({games,previews,status}) {
  const researched=games.filter(game=>previews?.[game.game_id]?.headline).length
  const disagreements=games.filter(game=>Math.abs(num(game.levline_vs_market_winner_probability_pp)||0)>=2.5).length
  return <section className="ss-plus-status-strip"><span><i/>{games.length} games published</span><span>{researched}/{games.length} researched reads</span><span>{disagreements} notable market disagreements</span><span>Feed {status?.generated_utc?formatTime(status.generated_utc):'—'}</span><b>Locked picks stay locked.</b></section>
}

function MoreStandard() {
  return <div className="ss-plus-more-standard"><SundaySignalStandard/><button onClick={()=>{window.location.hash='#/teams'}}>Explore team profiles →</button></div>
}

export default function SignalEnhancements() {
  const [route,setRoute]=useState(()=>routeFromHash())
  const [data,setData]=useState({games:[],runs:[],history:[],ratings:[],previews:{},evidence:{},status:{},current:[]})

  useEffect(()=>{
    const onHash=()=>setRoute(routeFromHash())
    window.addEventListener('hashchange',onHash)
    return ()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{
    const classes=['ss-plus-forecasts','ss-plus-game','ss-plus-power','ss-plus-history','ss-plus-methodology','ss-plus-teams','ss-plus-more']
    document.body.classList.add('ss-plus-active')
    document.body.classList.remove(...classes)
    document.body.classList.add(`ss-plus-${route.page}`)
    return ()=>document.body.classList.remove('ss-plus-active',...classes)
  },[route.page])

  useEffect(()=>{;(async()=>{
    const [forecastPayload,runs,history,ratings,previews,evidence,status,current]=await Promise.all([
      fetchJSON('public_forecasts.json',{games:[]}),fetchCSV('run_history.csv'),fetchCSV('prediction_history.csv'),fetchCSV('power_ratings.csv'),fetchJSON('game_previews.json',{}),fetchJSON('contextual_evidence.json',{}),fetchJSON('status.json',{}),fetchCSV('this_week.csv'),
    ])
    setData({games:Array.isArray(forecastPayload.games)?forecastPayload.games:[],runs,history,ratings,previews,evidence,status,current})
  })()},[])

  const selected=route.page==='game'?data.games.find(game=>game.game_id===route.gameId):null
  const diagnostic=selected ? data.current.find(row=>row.game_id===selected.game_id) || data.history.find(row=>row.game_id===selected.game_id&&row.lock_status==='LOCKED') : null

  return <>
    {route.page==='forecasts'&&<>
      <PortalSlot anchor=".ss-board-hero" position="afterend" id="ss-plus-search"><SearchMatchups games={data.games}/></PortalSlot>
      <PortalSlot anchor=".ss-top-signals" position="beforebegin" id="ss-plus-top-signals"><EnhancedTopSignals games={data.games} runs={data.runs}/></PortalSlot>
      <PortalSlot anchor=".ss-week" position="beforebegin" id="ss-plus-market-scanner"><ModelMarketScanner games={data.games}/></PortalSlot>
    </>}
    {route.page==='game'&&selected&&<>
      <PortalSlot anchor=".ss-matchup-page > .ss-forecast-hero" position="afterend" id="ss-plus-game-command"><GameCommandBar game={selected} runs={data.runs} preview={data.previews[selected.game_id]} diagnostic={diagnostic}/></PortalSlot>
      <PortalSlot anchor=".ss-matchup-main > .ss-the-signal" position="beforebegin" id="ss-plus-signal"><EnhancedSignal preview={data.previews[selected.game_id]}/></PortalSlot>
    </>}
    {route.page==='power'&&<PortalSlot anchor=".ss-power-board" position="beforebegin" id="ss-plus-power-board"><EnhancedPower ratings={data.ratings}/></PortalSlot>}
    {route.page==='history'&&<PortalSlot anchor=".ss-history-stats" position="afterend" id="ss-plus-history"><HistoryTiers history={data.history}/></PortalSlot>}
    {route.page==='more'&&<PortalSlot anchor=".ss-more-grid" position="afterend" id="ss-plus-standard"><MoreStandard/></PortalSlot>}
    <PortalSlot anchor=".ss-footer" position="beforebegin" id="ss-plus-status"><StatusStrip games={data.games} previews={data.previews} status={data.status}/></PortalSlot>
  </>
}
