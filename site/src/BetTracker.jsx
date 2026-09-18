import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  BET_UNIT_DOLLARS,
  buildBetLedger,
  buildCurrentWeekSlate,
  combinedEntryProfit,
  summarizeBets,
  summarizeCombined,
} from './betTrackerMath.js'
import './bet-tracker.css'

const BASE = import.meta.env.BASE_URL

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
  if (value == null) return '—'
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

function HistoryCard({label,summary}) {
  const tone=toneForProfit(summary.profit)
  return <article className="ss-bet-history-card">
    <span>{label}</span>
    <strong>{record(summary)}</strong>
    <small>2026 RECORD</small>
    <div className={tone}><span>ROI</span><b>{roi(summary.roi)}</b></div>
    {summary.missingProfit>0&&<em>{summary.missingProfit} winning price{summary.missingProfit===1?'':'s'} unavailable</em>}
  </article>
}

function ResultChip({result}) {
  return <span className={`ss-bet-result ${result||'pending'}`}>{resultLabel(result)}</span>
}

function MoneylineValue({entry}) {
  const bet=entry.ml
  if (!bet) return <span>—</span>
  return <span className="ss-bet-bet-value">
    <b>{bet.pick}</b>
    {bet.odds==null
      ? <small>{entry.locked?'Price unavailable':'Awaiting lock'}</small>
      : <small>{odds(bet.odds)}</small>}
  </span>
}

function SpreadValue({entry}) {
  const bet=entry.spread
  if (!bet) return <span>—</span>
  return <span className="ss-bet-bet-value">
    <b>{lineLabel(bet)}</b>
    {entry.locked
      ? <small>{odds(bet.odds)}{bet.usedFallbackPrice?' fallback':''}</small>
      : <small>Awaiting lock</small>}
  </span>
}

function entryState(entry) {
  const pending=[entry.ml,entry.spread].filter(Boolean).some(bet=>bet.result==='pending')
  if (!entry.locked) return 'AWAITING LOCK'
  return pending ? 'LOCKED · PENDING' : 'FINAL'
}

function profitDisplay(entry) {
  const value=combinedEntryProfit(entry)
  if (value != null) return {label:dollars(value),tone:toneForProfit(value)}
  const pending=[entry.ml,entry.spread].filter(Boolean).some(bet=>bet.result==='pending')
  return {label:pending?'—':'PRICE GAP',tone:'unpriced'}
}

function WeekLedger({entries}) {
  return <>
    <div className="ss-bet-week-ledger">
      <div className="ss-bet-week-ledger-head">
        <span>MATCHUP</span><span>MONEYLINE</span><span>ML RESULT</span><span>LEVLINE SPREAD</span><span>SPREAD RESULT</span><span>GAME P/L</span>
      </div>
      {entries.map(entry=>{
        const gameProfit=profitDisplay(entry)
        return <article key={entry.gameId}>
          <span className="ss-bet-matchup"><b>{entry.awayTeam} @ {entry.homeTeam}</b><small>{entryState(entry)}</small></span>
          <MoneylineValue entry={entry}/>
          <ResultChip result={entry.ml?.result}/>
          <SpreadValue entry={entry}/>
          <ResultChip result={entry.spread?.result}/>
          <strong className={gameProfit.tone}>{gameProfit.label}</strong>
        </article>
      })}
    </div>
    <div className="ss-bet-week-mobile">
      {entries.map(entry=>{
        const gameProfit=profitDisplay(entry)
        return <article key={`${entry.gameId}-mobile`}>
          <header>
            <div><b>{entry.awayTeam} @ {entry.homeTeam}</b><small>{entryState(entry)}</small></div>
            <strong className={gameProfit.tone}>{gameProfit.label}</strong>
          </header>
          <div><span>MONEYLINE</span><MoneylineValue entry={entry}/><ResultChip result={entry.ml?.result}/></div>
          <div><span>LEVLINE SPREAD</span><SpreadValue entry={entry}/><ResultChip result={entry.spread?.result}/></div>
        </article>
      })}
    </div>
  </>
}

function MarketTotal({label,summary}) {
  const tone=toneForProfit(summary.profit)
  return <article className="ss-bet-market-total">
    <span>{label}</span>
    <strong>{record(summary)}</strong>
    <small>RECORD</small>
    <div><span>P/L</span><b className={tone}>{dollars(summary.profit)}</b></div>
    <div><span>ROI</span><b className={tone}>{roi(summary.roi)}</b></div>
    {summary.pending>0&&<em>{summary.pending} pending</em>}
  </article>
}

function WeekTotals({week,entries}) {
  const ml=summarizeBets(entries,'ml')
  const spread=summarizeBets(entries,'spread')
  const combined=summarizeCombined(entries)
  const tone=toneForProfit(combined.profit)
  return <section className="ss-bet-week-totals">
    <header>
      <div><span>WEEK {week} TOTALS</span><h3>Current week performance</h3></div>
      <small>{combined.settled} settled wager{combined.settled===1?'':'s'} · {combined.pending} pending</small>
    </header>
    <div className="ss-bet-market-totals">
      <MarketTotal label="MONEYLINE" summary={ml}/>
      <MarketTotal label="LEVLINE SPREAD" summary={spread}/>
    </div>
    <div className="ss-bet-combined-total">
      <span>WEEK TOTAL</span>
      <strong className={tone}>{dollars(combined.profit)}</strong>
      <div><small>COMBINED ROI</small><b className={tone}>{roi(combined.roi)}</b></div>
    </div>
    {(ml.missingProfit>0||spread.missingProfit>0)&&<p className="ss-bet-disclosure"><b>Verified-price gap:</b> P/L and ROI stay blank whenever a winning locked wager is missing a verifiable sportsbook price.</p>}
    {combined.pending>0&&<p className="ss-bet-disclosure">Pending or not-yet-locked games are excluded from record, P/L and ROI until their immutable pregame receipt is graded.</p>}
  </section>
}

function BetTrackerPanel({history,currentGames}) {
  const ledger=useMemo(()=>buildBetLedger(history),[history])
  const seasonMl=useMemo(()=>summarizeBets(ledger,'ml'),[ledger])
  const seasonSpread=useMemo(()=>summarizeBets(ledger,'spread'),[ledger])
  const slate=useMemo(()=>buildCurrentWeekSlate(currentGames,ledger),[currentGames,ledger])

  if (!ledger.length && !slate.entries.length) return null

  return <section className="ss-bet-tracker" aria-label="LevLine Bet Tracker">
    <header className="ss-bet-tracker-head">
      <div>
        <span>PERFORMANCE HISTORY</span>
        <h2>Every official LevLine bet, tracked.</h2>
        <p>2026 season · 1 unit = $${BET_UNIT_DOLLARS} risked per bet · immutable pregame receipts determine the record.</p>
      </div>
    </header>

    <div className="ss-bet-history-grid">
      <HistoryCard label="MONEYLINE" summary={seasonMl}/>
      <HistoryCard label="LEVLINE SPREAD" summary={seasonSpread}/>
    </div>

    {slate.week!=null&&<section className="ss-bet-this-week">
      <header className="ss-bet-this-week-head">
        <div><span>THIS WEEK</span><h3>Week {slate.week} slate</h3></div>
        <small>{slate.entries.length} game{slate.entries.length===1?'':'s'} · moneyline + modeled spread</small>
      </header>
      <WeekLedger entries={slate.entries}/>
      <WeekTotals week={slate.week} entries={slate.entries}/>
    </section>}
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
