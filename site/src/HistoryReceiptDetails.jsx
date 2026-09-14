import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import './history-receipt-details.css'

const BASE = import.meta.env.BASE_URL

const num = value => {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
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

async function fetchHistory() {
  try {
    const response=await fetch(`${BASE}data/prediction_history.csv`,{cache:'no-store'})
    return response.ok ? parseCSV(await response.text()) : []
  } catch { return [] }
}

function routeGameId() {
  const parts=window.location.hash.replace(/^#\/?/,'').split('/').filter(Boolean)
  return parts[0]==='receipt' && parts[1] ? decodeURIComponent(parts.slice(1).join('/')) : null
}

function lineText(marginHome,home,away) {
  const margin=num(marginHome)
  if (margin==null) return '—'
  if (Math.abs(margin)<.05) return 'PK'
  return margin>0 ? `${home} -${Math.abs(margin).toFixed(1)}` : `${away} -${Math.abs(margin).toFixed(1)}`
}

function edgeText(value) {
  const edge=num(value)
  if (edge==null) return '—'
  return `${edge>=0?'+':''}${edge.toFixed(1)} pts`
}

function score(row) {
  const home=num(row.actual_home_score ?? row.final_home_score ?? row.home_score ?? row.result_home_score ?? row.score_home)
  const away=num(row.actual_away_score ?? row.final_away_score ?? row.away_score ?? row.result_away_score ?? row.score_away)
  return home==null || away==null ? null : `${row.away_team} ${away} – ${row.home_team} ${home}`
}

function ReceiptDetails({row}) {
  const lockedModel=row.locked_model_spread || row.expected_margin
  const lockedMarket=row.locked_market_spread || row.spread_line
  const lockedEdge=row.locked_edge || row.model_edge
  const closing=row.closing_spread || row.closing_spread_line || row.close_spread || row.close_spread_line
  const final=score(row)
  return <section className="ss-history-receipt-details" aria-label="Locked forecast details">
    <header>
      <span>LOCKED FORECAST DETAILS</span>
      <small>Values below are from the immutable pregame receipt.</small>
    </header>
    <div className="ss-history-receipt-details-grid">
      <article><small>LEVLINE LOCKED SPREAD</small><strong>{lineText(lockedModel,row.home_team,row.away_team)}</strong><span>Model margin at lock</span></article>
      <article><small>MARKET SPREAD AT LOCK</small><strong>{lineText(lockedMarket,row.home_team,row.away_team)}</strong><span>Sportsbook line captured with the receipt</span></article>
      <article><small>EDGE AT LOCK</small><strong>{edgeText(lockedEdge)}</strong><span>LevLine margin minus market line</span></article>
      <article><small>CLOSING SPREAD</small><strong>{closing?lineText(closing,row.home_team,row.away_team):'Not stored'}</strong><span>{closing?'Separate post-lock close':'Never inferred from the lock line'}</span></article>
      <article className="final-score"><small>FINAL SCORE</small><strong>{final || 'Not stored'}</strong><span>{final?'Graded result':'No score is present in this artifact'}</span></article>
    </div>
  </section>
}

export default function HistoryReceiptDetails() {
  const [gameId,setGameId]=useState(()=>routeGameId())
  const [history,setHistory]=useState([])
  const [host,setHost]=useState(null)

  useEffect(()=>{
    const onHash=()=>setGameId(routeGameId())
    window.addEventListener('hashchange',onHash)
    return()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{ fetchHistory().then(setHistory) },[])

  const row=useMemo(()=>gameId ? history.find(item=>item.game_id===gameId && item.lock_status==='LOCKED') : null,[gameId,history])

  useEffect(()=>{
    if (!gameId) { setHost(null); document.getElementById('ss-history-receipt-details-host')?.remove(); return }
    const attach=()=>{
      const grid=document.querySelector('.ss-exp-receipt-grid')
      if (!grid) return
      let node=document.getElementById('ss-history-receipt-details-host')
      if (!node) {
        node=document.createElement('div')
        node.id='ss-history-receipt-details-host'
        grid.insertAdjacentElement('afterend',node)
      }
      setHost(node)
    }
    attach()
    const observer=new MutationObserver(attach)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return()=>{observer.disconnect();document.getElementById('ss-history-receipt-details-host')?.remove();setHost(null)}
  },[gameId])

  useEffect(()=>{
    if (!row) return
    const final=score(row)
    if (!final) return
    const replace=()=>{
      const resultCard=document.querySelector('.ss-exp-receipt-grid > article:nth-child(3) span')
      if (resultCard) resultCard.textContent=final
    }
    replace()
    const observer=new MutationObserver(replace)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return()=>observer.disconnect()
  },[row])

  return host && row ? createPortal(<ReceiptDetails row={row}/>,host) : null
}
