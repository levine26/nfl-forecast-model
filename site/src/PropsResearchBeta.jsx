import React, { useEffect, useMemo, useState } from 'react'
import {
  formatAmerican,
  formatDifference,
  formatLine,
  formatPercent,
  formatPoints,
  primaryMarketPrice,
  propLabel,
  qualityLabel,
  rangeText,
  sortForecasts,
} from './propsPresentation.js'
import './props-research-beta.css'

const BASE = import.meta.env.BASE_URL

async function fetchJson(name, fallback) {
  try {
    const response = await fetch(`${BASE}data/${name}`, { cache: 'no-store' })
    return response.ok ? await response.json() : fallback
  } catch { return fallback }
}

function routeState() {
  const raw = window.location.hash.replace(/^#\/?/, '')
  if (!(raw === 'props' || raw.startsWith('props/'))) return { active: false, tab: 'board' }
  const tab = raw.split('/')[1] || 'board'
  return { active: true, tab: ['board', 'history', 'about'].includes(tab) ? tab : 'board' }
}
function navigate(path) { window.location.hash = `#/${path}`; window.scrollTo({ top: 0, behavior: 'smooth' }) }
function ResearchLockup() { return <div className="lp-lockup"><img src={`${BASE}brand/sunday-signal-icon.svg`} alt=""/><div><strong>LEVLINE PROPS</strong><span>RESEARCH BETA</span></div></div> }
function SignalPill({state}) { const key=String(state||'NO SIGNAL').toLowerCase().replaceAll(' ','-'); return <span className={`lp-signal ${key}`}>{state||'NO SIGNAL'}</span> }
function Metric({label,value,emphasis=false}) { return <div className={`lp-metric ${emphasis?'emphasis':''}`}><span>{label}</span><strong>{value}</strong></div> }
function DriverList({drivers=[]}) {
  if(!drivers.length) return <p className="lp-muted">No driver explanation was supplied by the upstream forecast artifact.</p>
  return <div className="lp-drivers">{drivers.map((driver,index)=>{const direction=driver?.direction==='UP'?'↑':driver?.direction==='DOWN'?'↓':driver?.direction==='NEUTRAL'?'→':'•';return <div key={`${driver?.label||'driver'}-${index}`}><span className={`lp-driver-arrow ${String(driver?.direction||'').toLowerCase()}`}>{direction}</span><b>{driver?.label||'Driver'}</b>{driver?.detail&&<small>{driver.detail}</small>}</div>})}</div>
}
function NoSignalReason({forecast}) {
  if(forecast.signal_state!=='NO SIGNAL') return null
  const reasons=forecast.unavailable_reasons||[]
  return <div className="lp-no-signal-copy"><b>Signal withheld.</b><span>{reasons.length?reasons.map(reason=>reason.replaceAll('_',' ')).join(' · '):'The forecast did not satisfy the research-beta publication gate.'}</span></div>
}
function LineCard({forecast}) {
  const unit=forecast.prop_type==='receptions'?'rec':forecast.prop_type==='passing_tds'?'TD':'yds'
  return <article className={`lp-card ${forecast.signal_state==='NO SIGNAL'?'no-signal':''}`}>
    <div className="lp-card-head"><div><div className="lp-player-row"><strong>{forecast.player||'Unresolved player'}</strong><span>{forecast.position||'—'} · {forecast.team||'—'} vs {forecast.opponent||'—'}</span></div><h2>{propLabel(forecast.prop_type)}</h2></div><SignalPill state={forecast.signal_state}/></div>
    <div className="lp-fair-line"><span>LEVLINE FAIR LINE</span><strong>{formatLine(forecast.model?.fair_line)}</strong><small>Market {formatLine(forecast.market?.line)} · Difference {formatDifference(forecast.model?.line_difference,unit)}</small></div>
    <div className="lp-grid metrics-primary"><Metric label="Market Line" value={formatLine(forecast.market?.line)}/><Metric label="Line Difference" value={formatDifference(forecast.model?.line_difference,unit)} emphasis/><Metric label="LevLine Over" value={formatPercent(forecast.model?.over_probability)}/><Metric label="Market No-Vig" value={formatPercent(forecast.model?.market_no_vig_probability)}/><Metric label="Probability Edge" value={formatPoints(forecast.model?.probability_edge)} emphasis/><Metric label="LevLine Under" value={formatPercent(forecast.model?.under_probability)}/></div>
    <div className="lp-grid metrics-secondary"><Metric label="Model Mean" value={formatLine(forecast.model?.mean)}/><Metric label="Model Median" value={formatLine(forecast.model?.median)}/><Metric label="Push" value={formatPercent(forecast.model?.push_probability)}/><Metric label="LevLine Fair Price" value={formatAmerican(forecast.model?.fair_odds_american)}/><Metric label="Sportsbook Over" value={formatAmerican(forecast.market?.over_price_american)}/><Metric label="Sportsbook Under" value={formatAmerican(forecast.market?.under_price_american)}/></div>
    <div className="lp-card-foot"><div><span>UNCERTAINTY</span><b>{rangeText(forecast)}</b></div><div><span>QUALITY</span><b>{qualityLabel(forecast)}</b></div><div><span>MARKET SOURCE</span><b>{forecast.market?.sportsbook||forecast.market?.source||'—'}</b></div></div>
    <NoSignalReason forecast={forecast}/><details className="lp-driver-details"><summary>Model drivers</summary><DriverList drivers={forecast.drivers}/></details>
  </article>
}
function TdCard({forecast}) {
  return <article className={`lp-card td ${forecast.signal_state==='NO SIGNAL'?'no-signal':''}`}>
    <div className="lp-card-head"><div><div className="lp-player-row"><strong>{forecast.player||'Unresolved player'}</strong><span>{forecast.position||'—'} · {forecast.team||'—'} vs {forecast.opponent||'—'}</span></div><h2>{propLabel(forecast.prop_type)}</h2></div><SignalPill state={forecast.signal_state}/></div>
    <div className="lp-td-probability"><span>LEVLINE TD PROBABILITY</span><strong>{formatPercent(forecast.model?.td_probability,1)}</strong><small>Expected TDs {formatLine(forecast.model?.expected_tds)}</small></div>
    <div className="lp-grid metrics-primary"><Metric label="Market No-Vig" value={formatPercent(forecast.model?.market_no_vig_probability)}/><Metric label="Probability Edge" value={formatPoints(forecast.model?.probability_edge)} emphasis/><Metric label="LevLine Fair Price" value={formatAmerican(forecast.model?.fair_odds_american)} emphasis/><Metric label="Sportsbook Price" value={formatAmerican(primaryMarketPrice(forecast))}/></div>
    <div className="lp-card-foot"><div><span>QUALITY</span><b>{qualityLabel(forecast)}</b></div><div><span>MARKET SOURCE</span><b>{forecast.market?.sportsbook||forecast.market?.source||'—'}</b></div><div><span>MODEL</span><b>{forecast.model?.version||'—'}</b></div></div>
    <NoSignalReason forecast={forecast}/><details className="lp-driver-details"><summary>TD drivers</summary><DriverList drivers={forecast.drivers}/></details>
  </article>
}
function EmptyState(){return <section className="lp-empty"><span>RESEARCH BETA</span><h1>Props publication is waiting for a valid forecast artifact.</h1><p>No signal is being manufactured. The page becomes populated only after the simulation and market lanes produce a contract-valid, pregame Props artifact.</p></section>}
function FilterBar({filters,setFilters,rows}) {
  const positions=['ALL',...new Set(rows.map(row=>row.position).filter(Boolean))], states=['ALL','MODEL EDGE','WATCH','NO SIGNAL']
  return <div className="lp-filters"><label>Position<select value={filters.position} onChange={e=>setFilters(c=>({...c,position:e.target.value}))}>{positions.map(v=><option key={v}>{v}</option>)}</select></label><label>Signal<select value={filters.signal} onChange={e=>setFilters(c=>({...c,signal:e.target.value}))}>{states.map(v=><option key={v}>{v}</option>)}</select></label><label className="lp-search">Player<input value={filters.search} placeholder="Search player" onChange={e=>setFilters(c=>({...c,search:e.target.value}))}/></label></div>
}
function Board({payload}) {
  const rows=useMemo(()=>sortForecasts(payload?.forecasts||[]),[payload]); const [filters,setFilters]=useState({position:'ALL',signal:'ALL',search:''})
  const shown=rows.filter(row=>(filters.position==='ALL'||row.position===filters.position)&&(filters.signal==='ALL'||row.signal_state===filters.signal)&&(!filters.search||String(row.player||'').toLowerCase().includes(filters.search.toLowerCase())))
  if(!rows.length) return <EmptyState/>
  const summary=payload?.summary||{}
  return <><section className="lp-hero"><div><span>OFFENSIVE PROPS ONLY</span><h1>Fair lines first. Market comparison second.</h1><p>LevLine estimates the player-stat distribution, shows what the line should be, then compares that distribution with the sportsbook line and price.</p></div><div className="lp-summary"><Metric label="Model Edge" value={summary.model_edge??0}/><Metric label="Watch" value={summary.watch??0}/><Metric label="No Signal" value={summary.no_signal??0}/></div></section><div className="lp-disclaimer">Research beta only. No demonstrated profitability, market superiority, or calibration claim is made.</div><FilterBar filters={filters} setFilters={setFilters} rows={rows}/><section className="lp-cards">{shown.map(row=>row.market_kind==='BINARY_TD'?<TdCard key={row.forecast_id} forecast={row}/>:<LineCard key={row.forecast_id} forecast={row}/>)}</section></>
}
function marketReceipt(market={}) { const price=market.td_price_american??market.over_price_american; return market.line!=null?`${formatLine(market.line)} · ${formatAmerican(price)}`:formatAmerican(price) }
function History({payload}) {
  const records=payload?.records||[]
  if(!records.length) return <section className="lp-empty compact"><span>IMMUTABLE HISTORY</span><h1>Immutable forecast history</h1><p>No prospective Props records have been published yet. Original forecasts, closing market snapshots, and grades are stored as separate events. Grading never rewrites the original forecast.</p></section>
  return <><section className="lp-history-intro"><span>IMMUTABLE HISTORY</span><h1>Immutable forecast history</h1><p>Original published forecasts never change. Closing markets and results are attached later as separate append-only events.</p></section><section className="lp-history-list">{records.map(record=>{const original=record.original_forecast||{}, market=original.market||{}, model=original.model||{}, close=record.closing_market||{}, grade=record.grade||{};return <article key={record.forecast_id} className="lp-history-row"><div><strong>{original.player||'Unknown player'}</strong><span>{propLabel(original.prop_type)} · {original.team||'—'} vs {original.opponent||'—'}</span><small>{record.recorded_utc||'—'}</small></div><div><span>Published market</span><b>{marketReceipt(market)}</b></div><div><span>LevLine fair</span><b>{formatLine(model.fair_line)}</b></div><div><span>Closing market</span><b>{record.closing_market?marketReceipt(close):'—'}</b></div><div><span>Actual</span><b>{formatLine(grade.actual_result)}</b></div><div><span>Grade</span><b>{grade.grading_result||'Pending'}</b></div></article>})}</section></>
}
function About(){return <section className="lp-about"><span>HOW TO READ LEVLINE PROPS</span><h1>The Fair Line is the center of the product.</h1><p>For yardage and reception markets, LevLine Fair Line is the model distribution’s approximately 50/50 threshold, normally its median. Mean and median remain visible because skewed player-stat distributions can make them differ.</p><div className="lp-about-grid"><article><b>Market comparison</b><p>Probability edge compares LevLine’s probability at the sportsbook line with the market’s no-vig probability when that market probability is available.</p></article><article><b>Signal discipline</b><p>MODEL EDGE is never created merely because two numbers disagree. Identity, timestamps, simulation accounting and critical data quality must pass publication QA.</p></article><article><b>Immutable history</b><p>The published forecast is an original receipt. Closing lines and actual results are later append-only events, so hindsight cannot replace the forecast of record.</p></article><article><b>Research status</b><p>This surface is a research beta. It does not claim proven profitability, market superiority or established calibration.</p></article></div></section>}

export default function PropsResearchBeta(){
  const [route,setRoute]=useState(routeState),[publicPayload,setPublicPayload]=useState(null),[historyPayload,setHistoryPayload]=useState(null)
  useEffect(()=>{const onHash=()=>setRoute(routeState());window.addEventListener('hashchange',onHash);return()=>window.removeEventListener('hashchange',onHash)},[])
  useEffect(()=>{document.body.classList.toggle('levline-props-route',route.active);return()=>document.body.classList.remove('levline-props-route')},[route.active])
  useEffect(()=>{if(!route.active)return;Promise.all([fetchJson('props_public.json',null),fetchJson('props_history.json',{records:[]})]).then(([published,history])=>{setPublicPayload(published);setHistoryPayload(history)})},[route.active])
  if(!route.active) return <button className="lp-entry" onClick={()=>navigate('props')}>Props <b>β</b></button>
  return <div className="lp-app"><header className="lp-header"><button className="lp-brand-button" onClick={()=>navigate('props')}><ResearchLockup/></button><nav aria-label="LevLine Props navigation"><button className={route.tab==='board'?'active':''} onClick={()=>navigate('props')}>Board</button><button className={route.tab==='history'?'active':''} onClick={()=>navigate('props/history')}>History</button><button className={route.tab==='about'?'active':''} onClick={()=>navigate('props/about')}>How it works</button></nav><button className="lp-back" onClick={()=>navigate('forecasts')}>Sunday Signal ↗</button></header><main>{route.tab==='board'&&<Board payload={publicPayload}/>} {route.tab==='history'&&<History payload={historyPayload}/>} {route.tab==='about'&&<About/>}</main><footer className="lp-footer"><ResearchLockup/><span>Prospective research forecasts · append-only history · fail closed on critical QA</span></footer></div>
}
