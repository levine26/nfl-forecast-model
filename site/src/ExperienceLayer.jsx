import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import './experience-v2.css'

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
function parseRoute() {
  const parts=window.location.hash.replace(/^#\/?/,'').split('/').filter(Boolean)
  if (parts[0]==='game' && parts[1]) return {page:'game',gameId:decodeURIComponent(parts.slice(1).join('/'))}
  if (parts[0]==='receipt' && parts[1]) return {page:'receipt',gameId:decodeURIComponent(parts.slice(1).join('/'))}
  return {page:parts[0]||'forecasts'}
}
function nav(path) { window.location.hash=`#/${path}` }
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
  if (p==null) return {key:'watch',label:'Watch'}
  if (p>=.67) return {key:'strong',label:'Strong signal'}
  if (p>=.61) return {key:'signal',label:'Signal'}
  if (p>=.56) return {key:'lean',label:'Lean'}
  return {key:'watch',label:'Watch'}
}
function truthy(value) {
  if (value==null || value==='') return null
  return String(value).toLowerCase()==='true'
}
function receiptProbability(row) {
  const hp=num(row.final_home_prob)
  if (hp==null) return null
  const pick=row.pick || (hp>=.5?row.home_team:row.away_team)
  return pick===row.home_team ? hp : 1-hp
}
function receiptPick(row) {
  const hp=num(row.final_home_prob)
  return row.pick || (hp==null?'—':hp>=.5?row.home_team:row.away_team)
}
function finalScore(row) {
  const home=num(row.final_home_score ?? row.home_score ?? row.result_home_score ?? row.score_home)
  const away=num(row.final_away_score ?? row.away_score ?? row.result_away_score ?? row.score_away)
  return home==null || away==null ? null : {home,away}
}
function relativeFreshness(value) {
  const ms=Date.now()-Date.parse(value||'')
  if (!Number.isFinite(ms) || ms<0) return value?formatTime(value):'Not timestamped'
  const minutes=Math.floor(ms/60000)
  if (minutes<1) return 'just now'
  if (minutes<60) return `${minutes} min ago`
  const hours=Math.floor(minutes/60)
  if (hours<24) return `${hours}h ago`
  const days=Math.floor(hours/24)
  return `${days}d ago`
}
function countdown(target,now) {
  const ms=Date.parse(target||'')-now
  if (!Number.isFinite(ms) || ms<=0) return null
  const total=Math.ceil(ms/60000)
  const days=Math.floor(total/1440)
  const hours=Math.floor((total%1440)/60)
  const minutes=total%60
  if (days>0) return `${days}d ${hours}h`
  if (hours>0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}
function movementRows(game,runs) {
  const cutoff=Date.parse(game.lock_timestamp_utc || game.forecast_timestamp_utc || '')
  return runs.filter(row=>row.game_id===game.game_id && row.prediction_timestamp_utc).map(row=>({
    x:Date.parse(row.prediction_timestamp_utc),timestamp:row.prediction_timestamp_utc,
    official:probabilityForTeam(row.final_home_prob,game.official_winner,game),
    market:probabilityForTeam(row.market_home_prob,game.official_winner,game),
  })).filter(row=>Number.isFinite(row.x)&&row.official!=null&&(!Number.isFinite(cutoff)||row.x<=cutoff+1000)).sort((a,b)=>a.x-b.x)
}
function latestMovement(game,runs) {
  const rows=movementRows(game,runs)
  if (rows.length<2) return null
  const latest=rows.at(-1)
  const previous=[...rows].reverse().slice(1).find(row=>Math.abs(row.official-latest.official)>.0005 || (row.market!=null&&latest.market!=null&&Math.abs(row.market-latest.market)>.0005)) || rows.at(-2)
  return {previous,latest,delta:(latest.official-previous.official)*100}
}

function Portal({anchor,position='beforebegin',id,children}) {
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
        node.className='ss-exp-host'
        target.insertAdjacentElement(position,node)
      }
      setHost(node)
    }
    attach()
    observer=new MutationObserver(attach)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return ()=>{observer.disconnect();document.getElementById(id)?.remove();setHost(null)}
  },[anchor,position,id])
  return host ? createPortal(children,host) : null
}

function TeamPair({game}) {
  return <div className="ss-exp-team-pair">
    <span><img src={teamLogo(game.away_team)} alt=""/><b>{game.away_team}</b></span><i>@</i><span><img src={teamLogo(game.home_team)} alt=""/><b>{game.home_team}</b></span>
  </div>
}
function MiniProbability({game}) {
  const p=num(game.official_winner_probability)
  if (p==null) return <span>—</span>
  const opponent=game.official_winner===game.home_team?game.away_team:game.home_team
  const opponentP=1-p
  return <div className="ss-exp-mini-prob" aria-label={`${game.official_winner} ${pct(p)}, ${opponent} ${pct(opponentP)}`}>
    <div><span><b>{game.official_winner}</b> {pct(p)}</span><span>{pct(opponentP)} <b>{opponent}</b></span></div>
    <i><em style={{width:`${p*100}%`}}/></i>
  </div>
}
function lifecycle(game,now) {
  const lock=game.lock_timestamp_utc || game.kickoff_utc
  if (game.lifecycle_status==='GRADED') return {key:'final',label:'FINAL',detail:'Pregame forecast preserved'}
  if (game.lifecycle_status==='IN_PROGRESS') return {key:'live',label:'GAME IN PROGRESS',detail:game.lock_timestamp_utc?`Pregame forecast locked ${formatTime(game.lock_timestamp_utc)}`:'Pregame forecast locked'}
  if (game.lifecycle_status==='FINAL_PREGAME' || game.immutable) return {key:'locked',label:'LOCKED',detail:game.lock_timestamp_utc?formatTime(game.lock_timestamp_utc):'Pregame receipt preserved'}
  const left=countdown(lock,now)
  return {key:'forecast',label:'LIVE FORECAST',detail:left?`Locks in ${left}`:(game.forecast_timestamp_utc?`Updated ${formatTime(game.forecast_timestamp_utc)}`:'Published')}
}

function TopSignalsV2({games}) {
  const valid=games.filter(g=>num(g.official_winner_probability)!=null)
  if (!valid.length) return null
  const strongest=[...valid].sort((a,b)=>num(b.official_winner_probability)-num(a.official_winner_probability))[0]
  const largest=[...valid].filter(g=>g.game_id!==strongest?.game_id && num(g.levline_vs_market_winner_probability_pp)!=null).sort((a,b)=>Math.abs(num(b.levline_vs_market_winner_probability_pp))-Math.abs(num(a.levline_vs_market_winner_probability_pp)))[0]
  const closest=[...valid].filter(g=>g.game_id!==strongest?.game_id&&g.game_id!==largest?.game_id).sort((a,b)=>Math.abs(num(a.official_winner_probability)-.5)-Math.abs(num(b.official_winner_probability)-.5))[0]
  const cards=[['Strongest Forecast',strongest],['Largest Edge vs Market',largest],['Closest Game',closest]].filter(([,g])=>g)
  return <section className="ss-exp-top-signals">
    <header><div><span>TOP SIGNALS</span><small>Three different reasons to open a matchup.</small></div></header>
    <div>{cards.map(([label,game],index)=><button key={`${label}-${game.game_id}`} onClick={()=>nav(`game/${encodeURIComponent(game.game_id)}`)}>
      <i>0{index+1}</i><span>{label}</span><TeamPair game={game}/><strong>{game.official_winner} {pct(game.official_winner_probability)}</strong>
      <small>{label==='Largest Edge vs Market'?`${game.official_winner} ${pts(game.levline_vs_market_winner_probability_pp)} vs market`:label==='Closest Game'?'Lowest separation from 50/50 on this slate':`${signalTier(game.official_winner_probability).label} · ${lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}`}</small>
    </button>)}</div>
  </section>
}

function ForecastExplorer({games,runs}) {
  const [sort,setSort]=useState('kickoff')
  const [filter,setFilter]=useState('all')
  const now=Date.now()
  const rows=useMemo(()=>{
    let next=[...games]
    if (filter==='upcoming') next=next.filter(g=>!['IN_PROGRESS','GRADED'].includes(g.lifecycle_status))
    if (filter==='locked') next=next.filter(g=>g.lifecycle_status==='FINAL_PREGAME'||g.immutable)
    if (filter==='live') next=next.filter(g=>g.lifecycle_status==='IN_PROGRESS')
    const move=g=>Math.abs(latestMovement(g,runs)?.delta||0)
    if (sort==='probability') next.sort((a,b)=>num(b.official_winner_probability)-num(a.official_winner_probability))
    else if (sort==='edge') next.sort((a,b)=>Math.abs(num(b.levline_vs_market_winner_probability_pp)||0)-Math.abs(num(a.levline_vs_market_winner_probability_pp)||0))
    else if (sort==='movement') next.sort((a,b)=>move(b)-move(a))
    else next.sort((a,b)=>Date.parse(a.kickoff_utc||0)-Date.parse(b.kickoff_utc||0))
    return next
  },[games,runs,sort,filter])
  return <section className="ss-exp-forecast-explorer">
    <div className="ss-exp-toolbar">
      <div><span>SORT</span>{[['kickoff','Kickoff'],['probability','Win Probability'],['edge','Edge'],['movement','Movement']].map(([key,label])=><button key={key} className={sort===key?'active':''} onClick={()=>setSort(key)}>{label}</button>)}</div>
      <div><span>SHOW</span>{[['all','All'],['upcoming','Upcoming'],['locked','Locked'],['live','Live']].map(([key,label])=><button key={key} className={filter===key?'active':''} onClick={()=>setFilter(key)}>{label}</button>)}</div>
    </div>
    {rows.length===0?<div className="ss-exp-empty"><b>No games match this view.</b><span>Change the filter to return to the published slate.</span></div>:<>
      <div className="ss-exp-board-labels"><span>MATCHUP</span><span>LEVLINE FAIR SPREAD</span><span>WIN PROBABILITY</span><span>SPORTSBOOK SPREAD</span><span>EDGE VS MARKET</span><span>STATUS</span></div>
      <div className="ss-exp-board-rows">{rows.map(game=>{const state=lifecycle(game,now);const move=latestMovement(game,runs);return <button key={game.game_id} onClick={()=>nav(`game/${encodeURIComponent(game.game_id)}`)}>
        <div><TeamPair game={game}/><small>{formatTime(game.kickoff_utc,{withDay:true})}</small></div>
        <strong>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</strong>
        <MiniProbability game={game}/>
        <span>{lineText(game.market_margin_home,game.home_team,game.away_team)}</span>
        <span className="ss-exp-edge"><b>{game.official_winner}</b> {pts(game.levline_vs_market_winner_probability_pp)}{move&&<small>{move.delta>=0?'↑':'↓'} {Math.abs(move.delta).toFixed(1)} since prior forecast</small>}</span>
        <span className={`ss-exp-state ${state.key}`}><b>{state.label}</b><small>{state.detail}</small></span>
      </button>})}</div>
      <div className="ss-exp-mobile-board">{rows.map(game=>{const state=lifecycle(game,now);return <button key={`m-${game.game_id}`} onClick={()=>nav(`game/${encodeURIComponent(game.game_id)}`)}>
        <header><small>{formatTime(game.kickoff_utc,{withDay:true})}</small><span className={`ss-exp-state ${state.key}`}><b>{state.label}</b></span></header>
        <TeamPair game={game}/><MiniProbability game={game}/>
        <div><span><small>Fair spread</small><b>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</b></span><span><small>Sportsbook</small><b>{lineText(game.market_margin_home,game.home_team,game.away_team)}</b></span><span><small>Edge</small><b>{game.official_winner} {pts(game.levline_vs_market_winner_probability_pp)}</b></span></div>
      </button>})}</div>
    </>}
  </section>
}

function LifecycleRibbon({game}) {
  const [now,setNow]=useState(Date.now())
  useEffect(()=>{const id=setInterval(()=>setNow(Date.now()),30000);return()=>clearInterval(id)},[])
  const state=lifecycle(game,now)
  return <div className={`ss-exp-lifecycle ${state.key}`}><span><i/>{state.label}</span><b>{state.detail}</b>{game.market_timestamp_utc&&<small>Market updated {formatTime(game.market_timestamp_utc)}</small>}</div>
}

function researchMeta(preview,evidence) {
  const sources=[]
  const seen=new Set()
  for (const item of preview?.evidence_used||[]) {
    const key=item.source_name||item.source_url
    if (key&&!seen.has(key)) { seen.add(key);sources.push(item) }
  }
  const stamps=[preview?.updated_utc,preview?.generated_utc,...sources.map(x=>x.as_of||x.published_at||x.timestamp),...evidence.map(x=>x.as_of)].filter(Boolean).map(Date.parse).filter(Number.isFinite)
  return {sources,latest:stamps.length?new Date(Math.max(...stamps)).toISOString():null}
}
function SignalV2({preview,evidence=[]}) {
  const {sources,latest}=researchMeta(preview,evidence)
  const paragraphs=Array.isArray(preview?.paragraphs)?preview.paragraphs.filter(Boolean):[]
  const factors=(preview?.key_factors||[]).filter(x=>x?.title).slice(0,3)
  const headline=preview?.headline||factors[0]?.title
  const bottom=paragraphs[0]||factors[0]?.summary
  if (!headline) return <section className="ss-exp-signal ss-exp-empty-signal"><span>THE SIGNAL</span><h2>Matchup analysis is being researched.</h2><p>The LevLine forecast is live. The Signal will appear after the research and source-validation pipeline clears publication.</p></section>
  return <section className="ss-exp-signal">
    <header><div><span>THE SIGNAL</span><small>{latest?`Research updated ${relativeFreshness(latest)}`:'Research timestamp unavailable'} · {sources.length||preview?.editorial_voice?.media_source_count||0} sources checked</small></div><b>Quick matchup read</b></header>
    <h2>{headline}</h2>{bottom&&<p className="ss-exp-bottom-line">{bottom}</p>}
    {factors.length>0&&<div className="ss-exp-what-matters"><span>WHAT MATTERS</span><div>{factors.map((factor,index)=><article key={`${factor.title}-${index}`}><header><b>{factor.advantage_team||'WATCH'}</b><small>{factor.strength||factor.family||'Context'}</small></header><strong>{factor.title}</strong>{factor.summary&&<p>{factor.summary}</p>}</article>)}</div></div>}
    <details><summary>Read full analysis <span>Research trail & supporting context</span></summary><div className="ss-exp-full-analysis">{paragraphs.slice(bottom===paragraphs[0]?1:0).map((text,index)=><p key={index}>{text}</p>)}{sources.length>0&&<div className="ss-exp-sources">{sources.slice(0,8).map((source,index)=><a key={`${source.source_name||source.source_url}-${index}`} href={source.source_url||undefined} target={source.source_url?'_blank':undefined} rel="noreferrer"><small>{String(source.category||'source').replaceAll('_',' ')}</small><b>{source.source_name||'Source'}</b></a>)}</div>}</div></details>
  </section>
}

function MovementContextV2({game,runs,evidence=[]}) {
  const rows=movementRows(game,runs)
  if (rows.length<2) return <section className="ss-exp-movement-context"><header><span>WHAT CHANGED</span><small>Chronology without causal overreach</small></header><div className="ss-exp-empty"><b>Movement needs two comparable forecasts.</b><span>This timeline will populate after another published run.</span></div></section>
  const items=[]
  for (let i=Math.max(1,rows.length-5);i<rows.length;i+=1) {
    const prev=rows[i-1],cur=rows[i]
    if (Math.abs(cur.official-prev.official)>.0005) items.push({x:cur.x,time:cur.timestamp,type:'forecast',title:`LevLine ${game.official_winner} ${pct(prev.official)} → ${pct(cur.official)}`,note:`${pts((cur.official-prev.official)*100)} change in published win probability.`})
    if (cur.market!=null&&prev.market!=null&&Math.abs(cur.market-prev.market)>.0005) items.push({x:cur.x,time:cur.timestamp,type:'market',title:`Market ${game.official_winner} ${pct(prev.market)} → ${pct(cur.market)}`,note:`${pts((cur.market-prev.market)*100)} change in vig-free market probability.`})
  }
  const first=rows[0],last=rows.at(-1)
  evidence.filter(x=>x.title&&Number.isFinite(Date.parse(x.as_of||''))).forEach(x=>items.push({x:Date.parse(x.as_of),time:x.as_of,type:x.promoted_to_model?'validated':'context',title:x.title,note:x.promoted_to_model?'Validated model input published alongside this period.':'Context surfaced in this period; not claimed as the cause of movement.'}))
  items.sort((a,b)=>b.x-a.x)
  const visible=items.filter(x=>x.x>=first.x-3600000&&x.x<=last.x+3600000).slice(0,8)
  return <section className="ss-exp-movement-context">
    <header><div><span>WHAT CHANGED</span><small>Chronology without causal overreach</small></div><b>LevLine {game.official_winner} {pct(first.official)} → {pct(last.official)}</b></header>
    {visible.length?<div className="ss-exp-timeline">{visible.map((item,index)=><article key={`${item.x}-${item.type}-${index}`} className={item.type}><time>{formatTime(item.time)}</time><i/><div><span>{item.type==='validated'?'VALIDATED INPUT':item.type==='context'?'CONTEXT':item.type==='market'?'MARKET':'LEVLINE'}</span><b>{item.title}</b><small>{item.note}</small></div></article>)}</div>:<div className="ss-exp-empty"><b>No distinct movement events yet.</b><span>The published forecast is stable across comparable runs.</span></div>}
    <footer>Context markers are shown as chronology only. They are never presented as the cause of a forecast move unless the underlying data explicitly establishes that relationship.</footer>
  </section>
}

function resultFor(game,row) {
  const score=finalScore(game)||finalScore(row||{})
  if (score) {
    const actual=score.home>score.away?game.home_team:score.away>score.home?game.away_team:'TIE'
    return {score,correct:actual==='TIE'?null:actual===game.official_winner,actual}
  }
  const known=truthy(game.winner_correct ?? row?.winner_correct)
  return {score:null,correct:known,actual:null}
}
function PostgameReceipt({game,historyRow,autopsy}) {
  if (game.lifecycle_status!=='GRADED') return null
  const result=resultFor(game,historyRow)
  const autopsyText=autopsy?.summary||autopsy?.headline||autopsy?.analysis||autopsy?.takeaway
  return <section className="ss-exp-postgame">
    <header><span>POSTGAME RECEIPT</span><b>The pregame forecast stays immutable.</b></header>
    <div><article><small>PREGAME FORECAST</small><strong>{game.official_winner} {pct(game.official_winner_probability)}</strong><span>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</span></article><article><small>FINAL</small><strong>{result.score?`${game.away_team} ${result.score.away} – ${game.home_team} ${result.score.home}`:'Final score not published in this artifact'}</strong><span>{game.lock_timestamp_utc?`Locked ${formatTime(game.lock_timestamp_utc)}`:'Pregame receipt preserved'}</span></article><article className={result.correct===true?'correct':result.correct===false?'miss':'pending'}><small>RESULT</small><strong>{result.correct===true?'✓ CORRECT':result.correct===false?'✕ MISS':'PENDING'}</strong><span>Graded against the published pick of record</span></article></div>
    {autopsyText&&<details><summary>Postgame autopsy <span>What the result taught us</span></summary><p>{autopsyText}</p></details>}
  </section>
}

function Calibration({rows,autopsies}) {
  const graded=rows.map(row=>{const correct=truthy(autopsies[row.game_id]?.winner_correct ?? autopsies[row.game_id]?.correct ?? row.winner_correct);return {...row,_p:receiptProbability(row),_correct:correct}}).filter(row=>row._p!=null&&row._correct!=null)
  const buckets=[[.5,.6,'50–59%'],[.6,.7,'60–69%'],[.7,.8,'70–79%'],[.8,1.01,'80%+']]
  return <section className="ss-exp-calibration"><header><span>PROBABILITY CALIBRATION</span><small>When LevLine said X%, how often did the pick actually win?</small></header><div>{buckets.map(([low,high,label])=>{const group=graded.filter(r=>r._p>=low&&r._p<high);const wins=group.filter(r=>r._correct).length;const actual=group.length?wins/group.length:null;return <article key={label}><span>{label}</span><b>{actual==null?'—':pct(actual,0)}</b><small>{group.length?`${wins}-${group.length-wins} · ${group.length} picks`:'No graded picks'}</small><i><em style={{width:`${actual==null?0:actual*100}%`}}/></i></article>})}</div></section>
}
function HistoryExplorer({history,autopsies}) {
  const locked=history.filter(row=>row.lock_status==='LOCKED'&&String(row.season||'2026')==='2026')
  const weeks=[...new Set(locked.map(r=>r.week).filter(Boolean))].sort((a,b)=>Number(a)-Number(b))
  const [week,setWeek]=useState('all'),[tier,setTier]=useState('all'),[result,setResult]=useState('all')
  const rows=locked.filter(row=>{
    const p=receiptProbability(row),t=signalTier(p).key,c=truthy(autopsies[row.game_id]?.winner_correct ?? autopsies[row.game_id]?.correct ?? row.winner_correct)
    return (week==='all'||String(row.week)===week)&&(tier==='all'||t===tier)&&(result==='all'||(result==='correct'&&c===true)||(result==='miss'&&c===false)||(result==='pending'&&c==null))
  })
  return <section className="ss-exp-history">
    <Calibration rows={locked} autopsies={autopsies}/>
    <div className="ss-exp-history-toolbar"><label>Week<select value={week} onChange={e=>setWeek(e.target.value)}><option value="all">All</option>{weeks.map(w=><option key={w} value={String(w)}>{w}</option>)}</select></label><label>Tier<select value={tier} onChange={e=>setTier(e.target.value)}><option value="all">All</option><option value="strong">Strong signal</option><option value="signal">Signal</option><option value="lean">Lean</option><option value="watch">Watch</option></select></label><label>Result<select value={result} onChange={e=>setResult(e.target.value)}><option value="all">All</option><option value="correct">Correct</option><option value="miss">Miss</option><option value="pending">Pending</option></select></label></div>
    {rows.length===0?<div className="ss-exp-empty"><b>No receipts match these filters.</b><span>Change a filter to inspect the immutable record.</span></div>:<div className="ss-exp-history-list">{rows.map(row=>{const p=receiptProbability(row),pick=receiptPick(row),correct=truthy(autopsies[row.game_id]?.winner_correct ?? autopsies[row.game_id]?.correct ?? row.winner_correct);return <button key={row.game_id} onClick={()=>nav(`receipt/${encodeURIComponent(row.game_id)}`)}><span>WEEK {row.week||'—'}</span><b>{row.away_team} @ {row.home_team}</b><strong>{pick} {pct(p)}</strong><span>{signalTier(p).label}</span><span>{row.lock_timestamp_utc?`Locked ${formatTime(row.lock_timestamp_utc)}`:'Locked pregame'}</span><em className={correct===true?'correct':correct===false?'miss':'pending'}>{correct==null?'Pending':correct?'✓ Correct':'✕ Miss'}</em><i>View receipt →</i></button>})}</div>}
  </section>
}

function ReceiptPage({row,autopsy,preview}) {
  if (!row) return <main className="ss-exp-receipt-page"><button onClick={()=>nav('history')}>← Back to History</button><div className="ss-exp-empty"><b>This receipt is not available in the published history.</b><span>The archive only opens immutable picks that exist in the current public record.</span></div></main>
  const pick=receiptPick(row),p=receiptProbability(row),correct=truthy(autopsy?.winner_correct ?? autopsy?.correct ?? row.winner_correct),score=finalScore(row)
  const text=autopsy?.summary||autopsy?.headline||autopsy?.analysis||autopsy?.takeaway
  return <main className="ss-exp-receipt-page">
    <button onClick={()=>nav('history')}>← Back to Official History</button>
    <section className="ss-exp-receipt-hero"><span>OFFICIAL PREGAME RECEIPT · WEEK {row.week||'—'}</span><h1>{row.away_team} @ {row.home_team}</h1><p>Published, locked before kickoff, and preserved after the result.</p></section>
    <section className="ss-exp-receipt-grid"><article><small>PICK OF RECORD</small><img src={teamLogo(pick)} alt=""/><strong>{teamName(pick)}</strong><b>{pct(p)}</b></article><article><small>LOCKED</small><strong>{formatTime(row.lock_timestamp_utc,{withDay:true})}</strong><span>Later refreshes cannot replace this forecast.</span></article><article className={correct===true?'correct':correct===false?'miss':'pending'}><small>RESULT</small><strong>{correct==null?'Pending':correct?'✓ Correct':'✕ Miss'}</strong><span>{score?`${row.away_team} ${score.away} – ${row.home_team} ${score.home}`:'Final score not stored in this receipt.'}</span></article></section>
    <section className="ss-exp-receipt-analysis"><span>THE SIGNAL</span>{preview?.headline?<><h2>{preview.headline}</h2>{(preview.paragraphs||[]).slice(0,2).map((x,i)=><p key={i}>{x}</p>)}</>:<div className="ss-exp-empty"><b>The immutable forecast receipt is available.</b><span>Archived editorial analysis is not published for this game artifact.</span></div>}</section>
    {text&&<section className="ss-exp-receipt-analysis"><span>POSTGAME AUTOPSY</span><h2>What the result taught us.</h2><p>{text}</p></section>}
  </main>
}

function PresentationTextPass({route}) {
  useEffect(()=>{
    const apply=()=>{
      document.querySelectorAll('.ss-desktop-nav button').forEach(button=>{if(button.textContent==='Power')button.textContent='Power Rankings';if(button.textContent==='Methodology')button.textContent='How LevLine Works'})
      document.querySelectorAll('.ss-method-flow article b').forEach(node=>{if(node.textContent==='Probability-Implied Line')node.textContent='LevLine Fair Spread'})
      document.querySelectorAll('.ss-how-link').forEach(node=>{node.textContent='How LevLine Works →'})
    }
    apply()
    const observer=new MutationObserver(apply)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return()=>observer.disconnect()
  },[route.page])
  return null
}

export default function ExperienceLayer() {
  const [route,setRoute]=useState(()=>parseRoute())
  const [data,setData]=useState({games:[],runs:[],history:[],autopsies:{},previews:{},evidence:{},status:{}})
  useEffect(()=>{const onHash=()=>setRoute(parseRoute());window.addEventListener('hashchange',onHash);return()=>window.removeEventListener('hashchange',onHash)},[])
  useEffect(()=>{;(async()=>{const [forecasts,runs,history,autopsies,previews,evidence,status]=await Promise.all([
    fetchJSON('public_forecasts.json',{games:[]}),fetchCSV('run_history.csv'),fetchCSV('prediction_history.csv'),fetchJSON('postgame_autopsies.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('contextual_evidence.json',{}),fetchJSON('status.json',{}),
  ]);setData({games:Array.isArray(forecasts.games)?forecasts.games:[],runs,history,autopsies,previews,evidence,status})})()},[])
  useEffect(()=>{
    const classes=['ss-exp-forecasts','ss-exp-game','ss-exp-history','ss-exp-receipt']
    document.body.classList.remove(...classes)
    if (classes.includes(`ss-exp-${route.page}`)) document.body.classList.add(`ss-exp-${route.page}`)
    return()=>document.body.classList.remove(...classes)
  },[route.page])
  const game=route.page==='game'?data.games.find(g=>g.game_id===route.gameId):null
  const historyRow=game?data.history.find(r=>r.game_id===game.game_id&&r.lock_status==='LOCKED'):null
  const receiptRow=route.page==='receipt'?data.history.find(r=>r.game_id===route.gameId&&r.lock_status==='LOCKED'):null
  return <>
    <PresentationTextPass route={route}/>
    {route.page==='forecasts'&&<>
      <Portal anchor=".ss-week" position="beforebegin" id="ss-exp-top"><TopSignalsV2 games={data.games}/></Portal>
      <Portal anchor=".ss-board-table" position="beforebegin" id="ss-exp-board"><ForecastExplorer games={data.games} runs={data.runs}/></Portal>
    </>}
    {route.page==='game'&&game&&<>
      <Portal anchor=".ss-clarity-head" position="afterend" id="ss-exp-lifecycle"><LifecycleRibbon game={game}/></Portal>
      <Portal anchor=".ss-plus-signal" position="beforebegin" id="ss-exp-signal"><SignalV2 preview={data.previews[game.game_id]} evidence={data.evidence[game.game_id]||[]}/></Portal>
      <Portal anchor=".ss-movement" position="afterend" id="ss-exp-movement"><MovementContextV2 game={game} runs={data.runs} evidence={data.evidence[game.game_id]||[]}/></Portal>
      {game.lifecycle_status==='GRADED'&&<Portal anchor=".ss-matchup-grid" position="beforebegin" id="ss-exp-postgame"><PostgameReceipt game={game} historyRow={historyRow} autopsy={data.autopsies[game.game_id]}/></Portal>}
    </>}
    {route.page==='history'&&<Portal anchor=".ss-history-stats" position="afterend" id="ss-exp-history"><HistoryExplorer history={data.history} autopsies={data.autopsies}/></Portal>}
    {route.page==='receipt'&&<Portal anchor=".ss-header" position="afterend" id="ss-exp-receipt"><ReceiptPage row={receiptRow} autopsy={data.autopsies[route.gameId]} preview={data.previews[route.gameId]}/></Portal>}
  </>
}
