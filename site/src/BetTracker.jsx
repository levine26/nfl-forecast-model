import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  BET_UNIT_DOLLARS,
  buildBetLedger,
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

function onHistoryRoute() {
  const page=window.location.hash.replace(/^#\/?/,'').split('/').filter(Boolean)[0] || 'forecasts'
  return page==='history'
}

function dollars(value) {
  if (value == null) return '—'
  const abs=Math.abs(value).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})
  return `${value>0?'+':value<0?'-':''}$${abs}`
}

function money(value) {
  return `$${Number(value||0).toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0})}`
}

function roi(value) {
  if (value == null) return '—'
  return `${value>=0?'+':''}${(value*100).toFixed(1)}%`
}

function odds(value) {
  if (value == null) return 'Not captured'
  const rounded=Math.round(value)
  return rounded>0 ? `+${rounded}` : `${rounded}`
}

function record(summary) {
  return summary.pushes ? `${summary.wins}-${summary.losses}-${summary.pushes}` : `${summary.wins}-${summary.losses}`
}

function resultLabel(result) {
  return result==='win' ? 'WIN' : result==='loss' ? 'LOSS' : 'PUSH'
}

function lineLabel(bet) {
  if (!bet) return '—'
  if (bet.line < .05) return `${bet.side} PK`
  return `${bet.side} -${bet.line.toFixed(1)}`
}

function SummaryMetric({label,value,tone=''}) {
  return <div className={tone}><span>{label}</span><strong>{value}</strong></div>
}

function WeekSummary({summary}) {
  const tone=summary.profit==null?'':summary.profit>0?'positive':summary.profit<0?'negative':''
  return <div className="ss-bet-week-summary">
    <SummaryMetric label="Record" value={record(summary)}/>
    <SummaryMetric label="Amount wagered" value={money(summary.risked)}/>
    <SummaryMetric label="P/L" value={dollars(summary.profit)} tone={tone}/>
    <SummaryMetric label="ROI" value={roi(summary.roi)} tone={tone}/>
  </div>
}

function SeasonCard({label,summary}) {
  const tone=summary.profit==null?'':summary.profit>0?'positive':summary.profit<0?'negative':''
  return <article className={`ss-bet-season-card ${tone}`}>
    <span>{label}</span>
    <strong>{dollars(summary.profit)}</strong>
    <div><small>ROI</small><b>{roi(summary.roi)}</b></div>
    <div><small>Risked</small><b>{money(summary.risked)}</b></div>
    {summary.missingProfit>0&&<em>{summary.missingProfit} winning price{summary.missingProfit===1?'':'s'} unavailable</em>}
  </article>
}

function MoneylineRows({entries}) {
  return <div className="ss-bet-ledger">
    <div className="ss-bet-ledger-head"><span>Matchup</span><span>LevLine ML</span><span>Odds at lock</span><span>Result</span><span>P/L</span></div>
    {entries.map(entry=><article key={`${entry.gameId}-ml`}>
      <span>{entry.awayTeam} @ {entry.homeTeam}</span>
      <b>{entry.ml.pick}</b>
      <span className={entry.ml.odds==null?'unpriced':''}>{odds(entry.ml.odds)}</span>
      <span className={`result ${entry.ml.result}`}>{resultLabel(entry.ml.result)}</span>
      <strong className={entry.ml.profit==null?'unpriced':entry.ml.profit>0?'positive':entry.ml.profit<0?'negative':''}>{entry.ml.profit==null?'Awaiting price':dollars(entry.ml.profit)}</strong>
    </article>)}
  </div>
}

function SpreadRows({entries}) {
  return <div className="ss-bet-ledger">
    <div className="ss-bet-ledger-head"><span>Matchup</span><span>LevLine spread</span><span>Price</span><span>Result</span><span>P/L</span></div>
    {entries.map(entry=>entry.spread&&<article key={`${entry.gameId}-spread`}>
      <span>{entry.awayTeam} @ {entry.homeTeam}</span>
      <b>{lineLabel(entry.spread)}</b>
      <span>{odds(entry.spread.odds)}{entry.spread.usedFallbackPrice&&<small> fallback</small>}</span>
      <span className={`result ${entry.spread.result}`}>{resultLabel(entry.spread.result)}</span>
      <strong className={entry.spread.profit>0?'positive':entry.spread.profit<0?'negative':''}>{dollars(entry.spread.profit)}</strong>
    </article>)}
  </div>
}

function BetTrackerPanel({history}) {
  const ledger=useMemo(()=>buildBetLedger(history),[history])
  const weeks=useMemo(()=>[...new Set(ledger.map(entry=>entry.week).filter(Number.isFinite))].sort((a,b)=>a-b),[ledger])
  const [week,setWeek]=useState(()=>weeks.at(-1) ?? '')

  useEffect(()=>{
    if (!weeks.length) return
    if (!weeks.includes(Number(week))) setWeek(weeks.at(-1))
  },[weeks,week])

  if (!ledger.length) return null

  const selected=ledger.filter(entry=>entry.week===Number(week))
  const weeklyMl=summarizeBets(selected,'ml')
  const weeklySpread=summarizeBets(selected,'spread')
  const seasonMl=summarizeBets(ledger,'ml')
  const seasonSpread=summarizeBets(ledger,'spread')
  const seasonCombined=summarizeCombined(ledger)
  const missingMl=weeklyMl.missingProfit>0

  return <section className="ss-bet-tracker" aria-label="LevLine Bet Tracker">
    <header className="ss-bet-tracker-head">
      <div><span>BET TRACKER</span><h2>What 1 unit on every LevLine pick would have done.</h2><p>Hypothetical tracking only · 1 unit = ${BET_UNIT_DOLLARS} risked per bet · graded from immutable pregame receipts.</p></div>
      <label><span>Week</span><select value={week} onChange={event=>setWeek(Number(event.target.value))}>{weeks.map(value=><option key={value} value={value}>Week {value}</option>)}</select></label>
    </header>

    <div className="ss-bet-season">
      <SeasonCard label="Season · Moneyline" summary={seasonMl}/>
      <SeasonCard label="Season · LevLine Spread" summary={seasonSpread}/>
      <SeasonCard label="Season · Combined" summary={seasonCombined}/>
    </div>

    <div className="ss-bet-sections">
      <section className="ss-bet-market">
        <div className="ss-bet-market-title"><div><span>MONEYLINE</span><h3>1 unit on every LevLine ML pick</h3></div><small>Sportsbook ML captured at LevLine lock</small></div>
        <WeekSummary summary={weeklyMl}/>
        <MoneylineRows entries={selected}/>
        {missingMl&&<p className="ss-bet-disclosure"><b>Historical pricing gap:</b> a winning ML receipt is missing its verified sportsbook price, so that week’s aggregate ML P/L and ROI remain blank rather than substituting LevLine fair odds or a later market price. Losses still grade at -1 unit.</p>}
      </section>

      <section className="ss-bet-market">
        <div className="ss-bet-market-title"><div><span>LEVLINE SPREAD</span><h3>1 unit on every final modeled spread</h3></div><small>LevLine line, not the market spread</small></div>
        <WeekSummary summary={weeklySpread}/>
        <SpreadRows entries={selected}/>
        <p className="ss-bet-disclosure">Spread wagers are graded against LevLine’s immutable modeled margin. Captured spread-side juice is used when stored; otherwise the approved -110 fallback is applied. Pushes return the stake and remain in the ROI denominator.</p>
      </section>
    </div>
  </section>
}

export default function BetTracker() {
  const [history,setHistory]=useState([])
  const [prices,setPrices]=useState([])
  const [active,setActive]=useState(()=>onHistoryRoute())
  const [host,setHost]=useState(null)

  useEffect(()=>{
    const onHash=()=>setActive(onHistoryRoute())
    window.addEventListener('hashchange',onHash)
    return()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{
    Promise.all([fetchCSV('prediction_history.csv'),fetchCSV('bet_price_history.csv')]).then(([historyRows,priceRows])=>{
      setHistory(historyRows)
      setPrices(priceRows)
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

  return active && host ? createPortal(<BetTrackerPanel history={enrichedHistory}/>,host) : null
}
