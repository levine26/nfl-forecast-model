import React, {useEffect, useMemo, useRef, useState} from 'react'
import {loadBoard,loadGameDossier,loadHistory,loadTeam} from './data.js'
import {navigate,parseRoute,routePath} from './routeState.js'
import {readLastVisit,visitChanges,visitSnapshot,writeLastVisit} from './sinceLastVisit.js'
import './vnext.css'

const BASE=import.meta.env.BASE_URL
const TEAM={
  ARI:'Arizona Cardinals',ATL:'Atlanta Falcons',BAL:'Baltimore Ravens',BUF:'Buffalo Bills',CAR:'Carolina Panthers',CHI:'Chicago Bears',CIN:'Cincinnati Bengals',CLE:'Cleveland Browns',DAL:'Dallas Cowboys',DEN:'Denver Broncos',DET:'Detroit Lions',GB:'Green Bay Packers',HOU:'Houston Texans',IND:'Indianapolis Colts',JAC:'Jacksonville Jaguars',JAX:'Jacksonville Jaguars',KC:'Kansas City Chiefs',LAC:'Los Angeles Chargers',LA:'Los Angeles Rams',LV:'Las Vegas Raiders',MIA:'Miami Dolphins',MIN:'Minnesota Vikings',NE:'New England Patriots',NO:'New Orleans Saints',NYG:'New York Giants',NYJ:'New York Jets',PHI:'Philadelphia Eagles',PIT:'Pittsburgh Steelers',SEA:'Seattle Seahawks',SF:'San Francisco 49ers',TB:'Tampa Bay Buccaneers',TEN:'Tennessee Titans',WAS:'Washington Commanders'
}
const num=value=>{if(value==null||value==='')return null;const n=Number(value);return Number.isFinite(n)?n:null}
const pct=(value,digits=1)=>num(value)==null?'—':`${(num(value)*100).toFixed(digits)}%`
const pp=value=>num(value)==null?'—':`${num(value)>=0?'+':''}${num(value).toFixed(1)} pp`
const teamName=team=>TEAM[team]||team||'—'

function probabilityForTeam(homeP,team,game){const p=num(homeP);if(p==null||!team)return null;return team===game.home_team?p:1-p}
function lineText(marginHome,home,away){const n=num(marginHome);if(n==null)return'—';if(Math.abs(n)<.05)return'PK';return n>0?`${home} -${Math.abs(n).toFixed(1)}`:`${away} -${Math.abs(n).toFixed(1)}`}
function life(game){return({LIVE_FORECAST:'Live',FINAL_PREGAME:'Locked',IN_PROGRESS:'In progress',GRADED:'Graded'})[game?.lifecycle_status]||game?.lifecycle_status||'Forecast'}

function formatTime(value,mode='local',withDay=false){
  if(!value)return'—'
  const date=new Date(value);if(Number.isNaN(date.getTime()))return'—'
  const zone=mode==='pt'?'America/Los_Angeles':mode==='et'?'America/New_York':undefined
  return new Intl.DateTimeFormat('en-US',{...(withDay?{weekday:'short',month:'short',day:'numeric'}:{}),hour:'numeric',minute:'2-digit',timeZoneName:'short',...(zone?{timeZone:zone}:{})}).format(date)
}
function relativeFreshness(value){
  if(!value)return'Unavailable'
  const ms=Date.now()-Date.parse(value);if(!Number.isFinite(ms))return'Unknown'
  const minutes=Math.max(0,Math.round(ms/60000));if(minutes<60)return`${minutes} min ago`
  const hours=Math.round(minutes/60);if(hours<36)return`${hours} hr ago`
  return`${Math.round(hours/24)} d ago`
}

function Link({route,children,className='',onNavigate}){
  const href=routePath(route,BASE)
  return <a href={href} className={className} onClick={event=>{if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;event.preventDefault();navigate(route,{base:BASE});onNavigate?.()}}>{children}</a>
}

function Header({week,timeMode,setTimeMode}){
  return <><header className="vx-header"><Link route={{name:'week',week:week||1}} className="vx-brand"><img src={`${BASE}brand/sunday-signal-icon.svg`} alt=""/><span><b>SUNDAY SIGNAL</b><small>powered by LevLine</small></span></Link><div className="vx-time-control"><label htmlFor="timezone">Kickoff times</label><select id="timezone" value={timeMode} onChange={e=>setTimeMode(e.target.value)}><option value="local">My local time</option><option value="pt">PT</option><option value="et">ET</option></select></div></header><nav className="vx-nav" aria-label="Primary"><Link route={{name:'week',week:week||1}}>Forecasts</Link><Link route={{name:'history'}}>Accountability</Link><Link route={{name:'methodology'}}>Methodology</Link></nav></>
}

function ForecastCore({game}){
  const market=probabilityForTeam(game.market_home_win_probability,game.official_winner,game)
  return <section className="vx-forecast-core" aria-label="Official forecast"><div><span>OFFICIAL LEVLINE FORECAST</span><h2>{game.official_winner} <strong>{pct(game.official_winner_probability)}</strong></h2><p>{market==null?'Market comparison unavailable.':`Market: ${pct(market)} on ${game.official_winner} · LevLine difference ${pp(game.levline_vs_market_winner_probability_pp)}`}</p></div><dl><div><dt>Probability-implied line</dt><dd>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</dd><small>presentation translation, not expected margin</small></div><div><dt>Lifecycle</dt><dd>{life(game)}</dd></div></dl></section>
}

function GameCard({game,preview,timeMode}){
  const signal=preview?.key_factors?.[0]?.title||preview?.headline
  return <article className="vx-card"><div className="vx-card-top"><time>{formatTime(game.kickoff_utc,timeMode,true)}</time><span>{life(game)}</span></div><h2>{game.away_team} <small>@</small> {game.home_team}</h2><div className="vx-pick"><span>LevLine</span><b>{game.official_winner} {pct(game.official_winner_probability)}</b></div><div className="vx-card-grid"><div><span>Market diff</span><b>{pp(game.levline_vs_market_winner_probability_pp)}</b></div><div><span>Probability-implied line</span><b>{lineText(game.coherent_fair_margin_home,game.home_team,game.away_team)}</b></div></div>{signal&&<p className="vx-signal"><b>What changed</b>{signal}</p>}<Link route={{name:'game',gameId:game.game_id}} className="vx-open">Open game dossier <span aria-hidden="true">→</span></Link></article>
}

function WeekBoard({games,previews,timeMode}){
  const sorted=[...games].sort((a,b)=>Date.parse(a.kickoff_utc||0)-Date.parse(b.kickoff_utc||0))
  const week=Number(sorted[0]?.week||1)
  return <main className="vx-page"><section className="vx-hero"><span>WEEK {week} · NFL</span><h1 tabIndex="-1" data-route-heading>Scan the slate in five seconds.</h1><p>Official winner probability first. Market difference, probability-implied line and one meaningful change stay visible without turning the board into a model dashboard.</p></section><section className="vx-board" aria-label={`Week ${week} forecasts`}>{sorted.map(game=><GameCard key={game.game_id} game={game} preview={previews?.[game.game_id]} timeMode={timeMode}/>)}</section></main>
}

function latestMovement(game,runs){
  const rows=[...(runs||[])].filter(row=>row.prediction_timestamp_utc).sort((a,b)=>Date.parse(a.prediction_timestamp_utc)-Date.parse(b.prediction_timestamp_utc))
  if(rows.length<2)return[]
  const before=rows.at(-2),after=rows.at(-1)
  const oldLev=probabilityForTeam(before.final_home_prob,game.official_winner,game),newLev=probabilityForTeam(after.final_home_prob,game.official_winner,game)
  const oldMarket=probabilityForTeam(before.market_home_prob,game.official_winner,game),newMarket=probabilityForTeam(after.market_home_prob,game.official_winner,game)
  const out=[]
  if(oldLev!=null&&newLev!=null)out.push({label:'LevLine probability',delta:(newLev-oldLev)*100,at:after.prediction_timestamp_utc})
  if(oldMarket!=null&&newMarket!=null)out.push({label:'Market probability',delta:(newMarket-oldMarket)*100,at:after.prediction_timestamp_utc})
  return out
}

function Changes({game,dossier,timeMode,lastVisitChanges}){
  const movement=latestMovement(game,dossier.runs)
  const evidence=[...(dossier.evidence||[])].filter(item=>item.title&&item.as_of).sort((a,b)=>Date.parse(b.as_of)-Date.parse(a.as_of)).slice(0,3)
  if(!movement.length&&!evidence.length&&!lastVisitChanges.length)return <p className="vx-empty">No material timestamped change has cleared the display threshold.</p>
  return <div className="vx-change-list">{lastVisitChanges.map((item,i)=><article key={`visit-${i}`}><span>SINCE YOUR LAST VISIT</span><b>{item.label}</b><small>browser-local comparison</small></article>)}{movement.map((item,i)=><article key={`move-${i}`}><span>LATEST MODEL/MARKET UPDATE</span><b>{item.label} {item.delta>=0?'+':''}{item.delta.toFixed(1)} pp</b><small>{formatTime(item.at,timeMode,true)} · movement only, no causal claim</small></article>)}{evidence.map((item,i)=><article key={`e-${i}`}><span>{String(item.category||'context').replaceAll('_',' ').toUpperCase()}</span><b>{item.title}</b><small>{formatTime(item.as_of,timeMode,true)} · contextual evidence, not automatically a model input</small></article>)}</div>
}

function EvidenceGroup({items,category,timeMode}){
  const filtered=(items||[]).filter(item=>category.includes(String(item.category||'').toLowerCase()))
  if(!filtered.length)return <p className="vx-empty">No publication-qualified {category[0]} update is available.</p>
  return <div className="vx-evidence">{filtered.slice(0,5).map((item,i)=><article key={`${item.title}-${i}`}><div><b>{item.title}</b><time>{formatTime(item.as_of,timeMode,true)}</time></div><p>{item.summary}</p><footer>{item.source_name||'Source unavailable'}{item.source_url&&<a href={item.source_url} target="_blank" rel="noreferrer">Source ↗</a>}</footer></article>)}</div>
}

function MovementTable({game,runs,timeMode}){
  const rows=[...(runs||[])].filter(r=>r.prediction_timestamp_utc).sort((a,b)=>Date.parse(a.prediction_timestamp_utc)-Date.parse(b.prediction_timestamp_utc)).slice(-8)
  if(rows.length<2)return <p className="vx-empty">Movement appears after the second comparable forecast run.</p>
  return <div className="vx-table-wrap"><table><thead><tr><th>Time</th><th>LevLine on {game.official_winner}</th><th>Market on {game.official_winner}</th></tr></thead><tbody>{rows.map((row,i)=><tr key={`${row.prediction_timestamp_utc}-${i}`}><td>{formatTime(row.prediction_timestamp_utc,timeMode,true)}</td><td>{pct(probabilityForTeam(row.final_home_prob,game.official_winner,game),2)}</td><td>{pct(probabilityForTeam(row.market_home_prob,game.official_winner,game),2)}</td></tr>)}</tbody></table></div>
}

function Freshness({game,dossier,timeMode}){
  const latestEvidence=[...(dossier.evidence||[])].filter(x=>x.as_of).sort((a,b)=>Date.parse(b.as_of)-Date.parse(a.as_of))[0]
  const rows=[
    ['Forecast',game.lock_timestamp_utc||game.forecast_timestamp_utc,game.immutable?'immutable lock':'live forecast'],
    ['Market',game.market_timestamp_utc,'official market input timestamp'],
    ['Context',latestEvidence?.as_of,latestEvidence?.source_name||'no qualified context source'],
  ]
  return <div className="vx-fresh-grid">{rows.map(([label,value,note])=><div key={label}><span>{label}</span><b>{value?relativeFreshness(value):'Unavailable'}</b><small>{value?formatTime(value,timeMode,true):note}</small></div>)}<div><span>Impact Monitor</span><b>{dossier.impact?'Available':'Unavailable'}</b><small>{dossier.impact?'publication-qualified state loaded':'fails closed; no feed is presented as current'}</small></div></div>
}

function GameDossier({game,dossier,timeMode,loading,error}){
  const [previous,setPrevious]=useState(null)
  useEffect(()=>{if(!game||!dossier)return;const current=visitSnapshot(game,dossier.evidence);setPrevious(readLastVisit(game.game_id));writeLastVisit(game.game_id,current)},[game?.game_id,dossier])
  if(!game)return <main className="vx-page"><h1 tabIndex="-1" data-route-heading>Game not found.</h1></main>
  if(loading)return <main className="vx-page"><h1 tabIndex="-1" data-route-heading>{game.away_team} at {game.home_team}</h1><p className="vx-loading">Loading game dossier…</p></main>
  if(error)return <main className="vx-page"><h1 tabIndex="-1" data-route-heading>{game.away_team} at {game.home_team}</h1><p className="vx-error">{error}</p></main>
  const current=visitSnapshot(game,dossier.evidence)
  const since=visitChanges(previous,current)
  const marketPick=game.market_home_win_probability>=.5?game.home_team:game.away_team
  return <main className="vx-page vx-dossier"><div className="vx-back"><Link route={{name:'week',week:Number(game.week||1)}}>← Week {game.week}</Link></div><header className="vx-game-hero"><div><span>GAME DOSSIER · {life(game).toUpperCase()}</span><h1 tabIndex="-1" data-route-heading>{teamName(game.away_team)} <small>at</small> {teamName(game.home_team)}</h1><p>{formatTime(game.kickoff_utc,timeMode,true)}</p></div><div className="vx-trust"><span>Model {game.provenance?.model_version||'F-ST-01-FROZEN-2026'}</span><span>{game.immutable?'Immutable forecast':'Live forecast'}</span></div></header><ForecastCore game={game}/>
    <section className="vx-section"><header><span>01</span><div><h2>What changed</h2><p>Timestamped movement and context. Correlation is not labeled as cause.</p></div></header><Changes game={game} dossier={dossier} timeMode={timeMode} lastVisitChanges={since}/></section>
    <section className="vx-section"><header><span>02</span><div><h2>Market</h2><p>Kept distinct from LevLine’s official probability.</p></div></header><div className="vx-stat-row"><div><span>Market favorite</span><b>{marketPick} {pct(marketPick===game.home_team?game.market_home_win_probability:1-num(game.market_home_win_probability))}</b></div><div><span>Market line</span><b>{lineText(game.market_margin_home,game.home_team,game.away_team)}</b></div><div><span>LevLine vs market</span><b>{pp(game.levline_vs_market_winner_probability_pp)}</b></div></div></section>
    <section className="vx-section"><header><span>03</span><div><h2>Personnel</h2><p>Context is separated from validated official forecast inputs.</p></div></header><EvidenceGroup items={dossier.evidence} category={['injury','personnel']} timeMode={timeMode}/></section>
    <section className="vx-section"><header><span>04</span><div><h2>Weather</h2><p>Forecast information as published, never realized game weather substituted backward.</p></div></header><EvidenceGroup items={dossier.evidence} category={['weather']} timeMode={timeMode}/></section>
    <section className="vx-section"><header><span>05</span><div><h2>Forecast movement</h2><p>Comparable pregame runs only.</p></div></header><MovementTable game={game} runs={dossier.runs} timeMode={timeMode}/></section>
    <section className="vx-section"><header><span>06</span><div><h2>Impact Monitor</h2><p>Publication-qualified contextual monitoring fails closed.</p></div></header>{dossier.impact?<pre className="vx-impact">{JSON.stringify(dossier.impact,null,2)}</pre>:<p className="vx-empty">Impact Monitor unavailable — source not publication-qualified or no current record.</p>}</section>
    <section className="vx-section"><header><span>07</span><div><h2>Advanced numbers</h2><p>Diagnostics remain separate from the official forecast.</p></div></header><div className="vx-stat-row"><div><span>Projected total</span><b>{num(game.public_projected_total)?.toFixed(1)||'—'}</b></div><div><span>Market total</span><b>{num(game.market_total)?.toFixed(1)||'—'}</b></div><div><span>Independent margin</span><b>{lineText(game.diagnostics?.independent_margin_home,game.home_team,game.away_team)}</b><small>diagnostic only</small></div></div></section>
    <section className="vx-section"><header><span>08</span><div><h2>Sources & freshness</h2><p>Missing sources never silently look current.</p></div></header><Freshness game={game} dossier={dossier} timeMode={timeMode}/></section>
  </main>
}

function Accountability({payload,timeMode,loading,error}){
  if(loading)return <main className="vx-page"><h1 tabIndex="-1" data-route-heading>Accountability</h1><p className="vx-loading">Loading immutable receipts…</p></main>
  if(error)return <main className="vx-page"><h1 tabIndex="-1" data-route-heading>Accountability</h1><p className="vx-error">{error}</p></main>
  const history=payload?.history||[],autopsies=payload?.autopsies||{}
  const locked=history.filter(r=>r.lock_status==='LOCKED')
  const scored=locked.map(row=>{const actual=num(row.actual_home_win??autopsies[row.game_id]?.actual_home_win);const p=num(row.final_home_prob);return actual==null||p==null?null:{row,actual,p}}).filter(Boolean)
  const brier=scored.length?scored.reduce((s,x)=>s+(x.p-x.actual)**2,0)/scored.length:null
  const log=scored.length?scored.reduce((s,x)=>{const p=Math.min(.999999,Math.max(.000001,x.p));return s-(x.actual*Math.log(p)+(1-x.actual)*Math.log(1-p))},0)/scored.length:null
  const accuracy=scored.length?scored.filter(x=>(x.p>=.5)===(x.actual===1)).length/scored.length:null
  return <main className="vx-page"><section className="vx-hero"><span>ACCOUNTABILITY</span><h1 tabIndex="-1" data-route-heading>Probability quality, not just a record.</h1><p>Every scored game points back to the immutable pregame forecast of record.</p></section><div className="vx-account-stats"><div><span>Games scored</span><b>{scored.length}</b></div><div><span>Brier</span><b>{brier==null?'—':brier.toFixed(4)}</b></div><div><span>Log loss</span><b>{log==null?'—':log.toFixed(4)}</b></div><div><span>Winner accuracy</span><b>{pct(accuracy)}</b></div></div><section className="vx-section"><header><span>01</span><div><h2>Locked forecast receipts</h2><p>Original locks remain inspectable and cannot be replaced by later runs.</p></div></header><div className="vx-table-wrap"><table><thead><tr><th>Game</th><th>Probability</th><th>Locked</th><th>Status</th></tr></thead><tbody>{locked.slice().reverse().map((row,i)=><tr key={`${row.game_id}-${i}`}><td><Link route={{name:'game',gameId:row.game_id}}>{row.away_team} @ {row.home_team}</Link></td><td>{pct(row.final_home_prob,2)} home</td><td>{formatTime(row.lock_timestamp_utc,timeMode,true)}</td><td>{autopsies[row.game_id]?'Scored':'Pending'}</td></tr>)}</tbody></table></div></section></main>
}

function TeamPage({team,payload,loading,error}){
  if(loading)return <main className="vx-page"><h1 tabIndex="-1" data-route-heading>{teamName(team)}</h1><p className="vx-loading">Loading team profile…</p></main>
  if(error||!payload?.profile)return <main className="vx-page"><h1 tabIndex="-1" data-route-heading>{teamName(team)}</h1><p className="vx-error">{error||'Team profile unavailable.'}</p></main>
  const p=payload.profile,e=payload.editorial||{}
  return <main className="vx-page"><section className="vx-hero"><span>TEAM PROFILE · {team}</span><h1 tabIndex="-1" data-route-heading>{teamName(team)}</h1><p>{e.why_here||'Published team strength with supporting context kept separate from official game probabilities.'}</p></section><div className="vx-account-stats"><div><span>Rank</span><b>#{p.rank||'—'}</b></div><div><span>Elo+</span><b>{num(p.elo_plus)==null?'—':Math.round(num(p.elo_plus))}</b></div><div><span>Next opponent</span><b>{p.next_opponent||'TBD'}</b></div><div><span>Next win</span><b>{pct(p.next_win_prob)}</b></div></div></main>
}

function Methodology(){return <main className="vx-page"><section className="vx-hero"><span>METHODOLOGY</span><h1 tabIndex="-1" data-route-heading>One official probability. Explicit roles.</h1><p>F-ST-01-FROZEN-2026 remains authoritative. The official lock remains T−120 minutes. Probability-implied line is a presentation translation, not a validated expected-margin forecast.</p></section><div className="vx-method-grid"><article><span>01</span><h2>Football signal</h2><p>Chronology-safe football state contributes to the frozen winner-probability architecture.</p></article><article><span>02</span><h2>Market signal</h2><p>Market probability is an explicit input, timestamped independently from the football signal.</p></article><article><span>03</span><h2>Immutable lock</h2><p>The first valid pregame lock is the forecast of record. Later refreshes cannot overwrite it.</p></article><article><span>04</span><h2>Research firewall</h2><p>Research-only sources and challengers never silently become production inputs.</p></article></div></main>}

export default function AppVNextPrototype(){
  const [route,setRoute]=useState(()=>parseRoute(window.location.pathname,BASE))
  const [timeMode,setTimeMode]=useState('local')
  const [board,setBoard]=useState({games:[],previews:{},status:{}})
  const [boardError,setBoardError]=useState('')
  const [dossier,setDossier]=useState(null),[dossierLoading,setDossierLoading]=useState(false),[dossierError,setDossierError]=useState('')
  const [history,setHistory]=useState(null),[historyLoading,setHistoryLoading]=useState(false),[historyError,setHistoryError]=useState('')
  const [teamPayload,setTeamPayload]=useState(null),[teamLoading,setTeamLoading]=useState(false),[teamError,setTeamError]=useState('')
  const headingRef=useRef(null)

  useEffect(()=>{const onPop=()=>setRoute(parseRoute(window.location.pathname,BASE));window.addEventListener('popstate',onPop);return()=>window.removeEventListener('popstate',onPop)},[])
  useEffect(()=>{loadBoard().then(setBoard).catch(err=>setBoardError(String(err?.message||err)))},[])
  useEffect(()=>{requestAnimationFrame(()=>document.querySelector('[data-route-heading]')?.focus())},[route.name,route.gameId,route.team])
  useEffect(()=>{if(route.name!=='game'||!route.gameId)return;let active=true;setDossierLoading(true);setDossierError('');loadGameDossier(route.gameId).then(value=>{if(active)setDossier(value)}).catch(err=>{if(active)setDossierError(String(err?.message||err))}).finally(()=>{if(active)setDossierLoading(false)});return()=>{active=false}},[route.name,route.gameId])
  useEffect(()=>{if(route.name!=='history'||history)return;let active=true;setHistoryLoading(true);loadHistory().then(value=>{if(active)setHistory(value)}).catch(err=>{if(active)setHistoryError(String(err?.message||err))}).finally(()=>{if(active)setHistoryLoading(false)});return()=>{active=false}},[route.name])
  useEffect(()=>{if(route.name!=='team'||!route.team)return;let active=true;setTeamLoading(true);setTeamError('');loadTeam(route.team).then(value=>{if(active)setTeamPayload(value)}).catch(err=>{if(active)setTeamError(String(err?.message||err))}).finally(()=>{if(active)setTeamLoading(false)});return()=>{active=false}},[route.name,route.team])

  const week=Number(board.games?.[0]?.week||route.week||1)
  const selected=useMemo(()=>board.games.find(g=>g.game_id===route.gameId)||null,[board.games,route.gameId])
  if(boardError)return <div className="vx-fatal"><b>Sunday Signal could not publish this slate.</b><span>{boardError}</span><small>The public contract fails closed.</small></div>
  return <div className="vx-app" ref={headingRef}><a className="vx-skip" href="#main-content">Skip to content</a><Header week={week} timeMode={timeMode} setTimeMode={setTimeMode}/><div id="main-content">{route.name==='week'&&<WeekBoard games={board.games} previews={board.previews} timeMode={timeMode}/>} {route.name==='game'&&<GameDossier game={selected} dossier={dossier} timeMode={timeMode} loading={dossierLoading||!dossier} error={dossierError}/>} {route.name==='history'&&<Accountability payload={history} timeMode={timeMode} loading={historyLoading||!history} error={historyError}/>} {route.name==='team'&&<TeamPage team={route.team} payload={teamPayload} loading={teamLoading||!teamPayload} error={teamError}/>} {route.name==='methodology'&&<Methodology/>} {route.name==='not-found'&&<main className="vx-page"><h1 tabIndex="-1" data-route-heading>Page not found.</h1><Link route={{name:'week',week}}>Return to Week {week}</Link></main>}</div><footer className="vx-footer"><b>SUNDAY SIGNAL</b><span>Official forecast · immutable lock · transparent sources · accountable probabilities</span></footer></div>
}
