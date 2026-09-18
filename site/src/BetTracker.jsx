import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  BET_UNIT_DOLLARS,
  buildBetLedger,
  buildCurrentWeekSlate,
  buildSeasonPerformance,
  combinedEntryProfit,
  summarizeBets,
  summarizeCombined,
} from './betTrackerMath.js'
import './bet-tracker.css'

const BASE = import.meta.env.BASE_URL

const TEAM_LOGO = {
  ARI:'ari', ATL:'atl', BAL:'bal', BUF:'buf', CAR:'car', CHI:'chi', CIN:'cin', CLE:'cle',
  DAL:'dal', DEN:'den', DET:'det', GB:'gb', HOU:'hou', IND:'ind', JAC:'jax', JAX:'jax',
  KC:'kc', LAC:'lac', LA:'lar', LV:'lv', MIA:'mia', MIN:'min', NE:'ne', NO:'no',
  NYG:'nyg', NYJ:'nyj', PHI:'phi', PIT:'pit', SEA:'sea', SF:'sf', TB:'tb', TEN:'ten', WAS:'wsh',
}

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

function onHistoryRoute() {
  const page=window.location.hash.replace(/^#\/?/,'').split('/').filter(Boolean)[0] || 'forecasts'
  return page==='history'
}

function dollars(value) {
  if (value == null) return '—'
  const abs=Math.abs(value).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})
  return `${value>0?'+':value<0?'-':''}$${abs}`
}

function roi(value) {
  if (value == null) return '—'
  return `${value>=0?'+':''}${(value*100).toFixed(1)}%`
}

function odds(value) {
  if (value == null) return ''
  const rounded=Math.round(value)
  return rounded>0 ? `+${rounded}` : `${rounded}`
}

function record(summary) {
  return summary.pushes ? `${summary.wins}-${summary.losses}-${summary.pushes}` : `${summary.wins}-${summary.losses}`
}

function resultLabel(result) {
  return result==='win' ? 'HIT' : result==='loss' ? 'MISS' : result==='push' ? 'PUSH' : 'PENDING'
}

function lineLabel(bet) {
  if (!bet) return '—'
  if (bet.line < .05) return `${bet.side} PK`
  return `${bet.side} -${bet.line.toFixed(1)}`
}

function toneForProfit(value) {
  return value==null ? '' : value>0 ? 'positive' : value<0 ? 'negative' : ''
}

function TeamMini({team}) {
  const [failed,setFailed]=useState(false)
  const slug=TEAM_LOGO[team] || String(team||'').toLowerCase()
  return <span className="ss-bet-team-mini" aria-hidden="true">
    {!failed && <img src={`https://a.espncdn.com/i/teamlogos/nfl/500/${slug}.png`} alt="" onError={()=>setFailed(true)}/>}
    {failed && <b>{team}</b>}
  </span>
}

function TrackRecordCard({label,summary}) {
  const tone=toneForProfit(summary.profit)
  return <article className="ss-track-card">
    <span>{label}</span>
    <strong>{record(summary)}</strong>
    <small>RECORD</small>
    <div className={tone}>
      <b>{roi(summary.roi)}</b>
      <span>ROI</span>
    </div>
    {summary.missingProfit>0&&<em>ROI unavailable until verified pricing is complete.</em>}
  </article>
}

function ResultChip({result}) {
  return <span className={`ss-bet-result ${result||'pending'}`}>{resultLabel(result)}</span>
}

function MoneylineValue({entry}) {
  const bet=entry.ml
  if (!bet) return <span className="ss-bet-value">—</span>
  const price=odds(bet.odds)
  return <span className="ss-bet-value">
    <b>{bet.pick}{price ? ` ${price}` : ''}</b>
    {!entry.locked&&<small>Awaiting lock</small>}
    {entry.locked&&bet.odds==null&&<small>Price unavailable</small>}
  </span>
}

function SpreadValue({entry}) {
  const bet=entry.spread
  if (!bet) return <span className="ss-bet-value">—</span>
  return <span className="ss-bet-value">
    <b>{lineLabel(bet)}</b>
    {entry.locked ? <small>{odds(bet.odds)}{bet.usedFallbackPrice?' fallback':''}</small> : <small>Awaiting lock</small>}
  </span>
}

function profitDisplay(entry) {
  const value=combinedEntryProfit(entry)
  if (value != null) return {label:dollars(value),tone:toneForProfit(value)}
  const pending=[entry.ml,entry.spread].filter(Boolean).some(bet=>bet.result==='pending')
  return {label:pending?'—':'PRICE GAP',tone:'unpriced'}
}

function GameIdentity({entry}) {
  return <span className="ss-bet-game-id">
    <span><TeamMini team={entry.awayTeam}/><b>{entry.awayTeam}</b></span>
    <em>@</em>
    <span><TeamMini team={entry.homeTeam}/><b>{entry.homeTeam}</b></span>
  </span>
}

function DesktopWeekLedger({entries}) {
  return <div className="ss-week-ledger">
    <div className="ss-week-ledger-labels">
      <span>MATCHUP</span><span>MONEYLINE</span><span>RESULT</span><span>LEVLINE SPREAD</span><span>RESULT</span><span>GAME P/L</span>
    </div>
    {entries.map(entry=>{
      const gameProfit=profitDisplay(entry)
      return <article key={entry.gameId}>
        <GameIdentity entry={entry}/>
        <MoneylineValue entry={entry}/>
        <ResultChip result={entry.ml?.result}/>
        <SpreadValue entry={entry}/>
        <ResultChip result={entry.spread?.result}/>
        <strong className={gameProfit.tone}>{gameProfit.label}</strong>
      </article>
    })}
  </div>
}

function MobileWeekLedger({entries}) {
  return <div className="ss-week-cards">
    {entries.map(entry=>{
      const gameProfit=profitDisplay(entry)
      return <article key={`${entry.gameId}-mobile`}>
        <header>
          <GameIdentity entry={entry}/>
          <strong className={gameProfit.tone}>{gameProfit.label}</strong>
        </header>
        <div>
          <span>ML</span>
          <MoneylineValue entry={entry}/>
          <ResultChip result={entry.ml?.result}/>
        </div>
        <div>
          <span>SPR</span>
          <SpreadValue entry={entry}/>
          <ResultChip result={entry.spread?.result}/>
        </div>
      </article>
    })}
  </div>
}

function SummaryBlock({label,summary}) {
  const tone=toneForProfit(summary.profit)
  return <article>
    <span>{label}</span>
    <strong>{record(summary)}</strong>
    <div><b className={tone}>{dollars(summary.profit)}</b><small>P/L</small></div>
    <div><b className={tone}>{roi(summary.roi)}</b><small>ROI</small></div>
  </article>
}

function WeekSummary({week,entries}) {
  const ml=summarizeBets(entries,'ml')
  const spread=summarizeBets(entries,'spread')
  const combined=summarizeCombined(entries)
  const tone=toneForProfit(combined.profit)
  return <section className="ss-week-summary">
    <header><span>WEEK {week} SUMMARY</span></header>
    <div className="ss-week-summary-grid">
      <SummaryBlock label="MONEYLINE" summary={ml}/>
      <SummaryBlock label="LEVLINE SPREAD" summary={spread}/>
      <article className="ss-week-net">
        <span>WEEK TOTAL</span>
        <strong className={tone}>{dollars(combined.profit)}</strong>
        <div><b className={tone}>{roi(combined.roi)}</b><small>COMBINED ROI</small></div>
      </article>
    </div>
    {(ml.missingProfit>0||spread.missingProfit>0)&&<p className="ss-bet-disclosure"><b>Verified-price gap:</b> P/L and ROI stay blank whenever a winning locked wager lacks a verified sportsbook price.</p>}
    {combined.pending>0&&<p className="ss-bet-disclosure">{combined.pending} pending wager{combined.pending===1?' is':'s are'} excluded from record, P/L and ROI until graded.</p>}
  </section>
}

function svgPoints(series,key,width,height,pad,min,max) {
  const valid=series.filter(row=>row[key]!=null)
  if (!valid.length) return ''
  const span=Math.max(1,series.length-1)
  const range=Math.max(1,max-min)
  return valid.map(row=>{
    const index=series.findIndex(item=>item.week===row.week)
    const x=pad + (width-pad*2)*(index/span)
    const y=height-pad - ((row[key]-min)/range)*(height-pad*2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}

function SeasonPerformance({entries}) {
  const series=useMemo(()=>buildSeasonPerformance(entries),[entries])
  const values=series.flatMap(row=>[row.cumulativeMl,row.cumulativeSpread]).filter(value=>value!=null)
  if (!series.length || !values.length) return null
  const width=720, height=170, pad=20
  let min=Math.min(0,...values), max=Math.max(0,...values)
  if (Math.abs(max-min)<1) { max+=1; min-=1 }
  const zeroY=height-pad - ((0-min)/(max-min))*(height-pad*2)
  const mlPoints=svgPoints(series,'cumulativeMl',width,height,pad,min,max)
  const spreadPoints=svgPoints(series,'cumulativeSpread',width,height,pad,min,max)

  return <section className="ss-season-performance">
    <header>
      <div><span>SEASON PERFORMANCE</span><h3>Cumulative P/L by week</h3></div>
      <div className="ss-season-legend"><span><i className="ml"/>Moneyline</span><span><i className="spread"/>LevLine Spread</span></div>
    </header>
    <div className="ss-season-chart" role="img" aria-label="Cumulative Moneyline and LevLine Spread profit and loss by week">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line className="zero" x1={pad} y1={zeroY} x2={width-pad} y2={zeroY}/>
        {mlPoints&&<polyline className="ml" points={mlPoints}/>}
        {spreadPoints&&<polyline className="spread" points={spreadPoints}/>}
      </svg>
      <div className="ss-season-weeks">{series.map(row=><span key={row.week}>W{row.week}</span>)}</div>
    </div>
  </section>
}

function BetTrackerPanel({history,currentGames}) {
  const ledger=useMemo(()=>buildBetLedger(history),[history])
  const seasonMl=useMemo(()=>summarizeBets(ledger,'ml'),[ledger])
  const seasonSpread=useMemo(()=>summarizeBets(ledger,'spread'),[ledger])
  const slate=useMemo(()=>buildCurrentWeekSlate(currentGames,ledger),[currentGames,ledger])

  if (!ledger.length && !slate.entries.length) return null

  const finalGames=slate.entries.filter(entry=>entry.ml?.result!=='pending' && (!entry.spread || entry.spread.result!=='pending')).length
  const pendingGames=slate.entries.length-finalGames

  return <section className="ss-bet-tracker" aria-label="LevLine Track Record">
    <header className="ss-track-head">
      <div>
        <span>LEVLINE TRACK RECORD</span>
        <h2>Official 2026 betting record.</h2>
        <p>$${BET_UNIT_DOLLARS} flat stake · immutable pregame receipts · hypothetical tracking</p>
      </div>
    </header>

    <div className="ss-track-grid">
      <TrackRecordCard label="MONEYLINE" summary={seasonMl}/>
      <TrackRecordCard label="LEVLINE SPREAD" summary={seasonSpread}/>
    </div>

    {slate.week!=null&&<section className="ss-this-week">
      <header className="ss-this-week-head">
        <div><span>THIS WEEK · W{slate.week}</span><h3>Week {slate.week} slate</h3></div>
        <small>{finalGames} final · {pendingGames} pending</small>
      </header>
      <DesktopWeekLedger entries={slate.entries}/>
      <MobileWeekLedger entries={slate.entries}/>
      <WeekSummary week={slate.week} entries={slate.entries}/>
    </section>}

    <SeasonPerformance entries={ledger}/>
  </section>
}

export default function BetTracker() {
  const [history,setHistory]=useState([])
  const [prices,setPrices]=useState([])
  const [forecastPayload,setForecastPayload]=useState({games:[]})
  const [active,setActive]=useState(()=>onHistoryRoute())
  const [host,setHost]=useState(null)

  useEffect(()=>{
    const onHash=()=>setActive(onHistoryRoute())
    window.addEventListener('hashchange',onHash)
    return()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{
    Promise.all([
      fetchCSV('prediction_history.csv'),
      fetchCSV('bet_price_history.csv'),
      fetchJSON('public_forecasts.json',{games:[]}),
    ]).then(([historyRows,priceRows,publicForecasts])=>{
      setHistory(historyRows)
      setPrices(priceRows)
      setForecastPayload(publicForecasts)
    })
  },[])

  const enrichedHistory=useMemo(()=>{
    if (!prices.length) return history
    const byGame=Object.fromEntries(prices.map(row=>[row.game_id,row]))
    return history.map(row=>({...row,...(byGame[row.game_id]||{})}))
  },[history,prices])

  useEffect(()=>{
    if (!active) {
      document.getElementById('ss-bet-tracker-host')?.remove()
      setHost(null)
      return
    }
    const attach=()=>{
      const anchor=document.querySelector('.ss-history-stats')
      if (!anchor) return
      let node=document.getElementById('ss-bet-tracker-host')
      if (!node) {
        node=document.createElement('div')
        node.id='ss-bet-tracker-host'
        anchor.insertAdjacentElement('afterend',node)
      }
      setHost(node)
    }
    attach()
    const observer=new MutationObserver(attach)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return()=>{
      observer.disconnect()
      document.getElementById('ss-bet-tracker-host')?.remove()
      setHost(null)
    }
  },[active])

  return active && host
    ? createPortal(<BetTrackerPanel history={enrichedHistory} currentGames={forecastPayload.games||[]}/>,host)
    : null
}
