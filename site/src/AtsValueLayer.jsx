import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import './ats-value.css'

const BASE = import.meta.env.BASE_URL

const num = value => {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function pct(value,digits=0) {
  const n=num(value)
  return n==null ? '—' : `${(n*100).toFixed(digits)}%`
}

function lineText(marginHome,home,away) {
  const margin=num(marginHome)
  if (margin==null) return '—'
  if (Math.abs(margin)<0.05) return 'PK'
  return margin>0 ? `${home} -${Math.abs(margin).toFixed(1)}` : `${away} -${Math.abs(margin).toFixed(1)}`
}

function pickedSpread(team,spread) {
  const n=num(spread)
  if (!team || n==null) return '—'
  if (Math.abs(n)<0.05) return `${team} PK`
  return `${team} ${n>0?'+':''}${n.toFixed(1)}`
}

function currentGameId() {
  const parts=window.location.hash.replace(/^#\/?/,'').split('/').filter(Boolean)
  return parts[0]==='game' && parts[1] ? decodeURIComponent(parts.slice(1).join('/')) : null
}

async function loadForecasts() {
  try {
    const response=await fetch(`${BASE}data/public_forecasts.json`,{cache:'no-store'})
    if (!response.ok) return []
    const payload=await response.json()
    return Array.isArray(payload?.games) ? payload.games : []
  } catch {
    return []
  }
}

function AtsValueCard({game}) {
  const status=game?.ats_status || game?.signals?.ats?.status || 'UNAVAILABLE'
  const pick=game?.ats_pick_team ?? game?.signals?.ats?.pick_team ?? null
  const marketSpread=game?.ats_pick_market_spread ?? game?.signals?.ats?.pick_market_spread ?? null
  const modelMargin=game?.ats_model_margin_home ?? game?.signals?.ats?.model_margin_home ?? null
  const marketMargin=game?.ats_market_margin_home ?? game?.signals?.ats?.market_margin_home ?? game?.market_margin_home ?? null
  const edge=game?.ats_edge_points ?? game?.signals?.ats?.edge_points ?? null
  const modelLine=lineText(modelMargin,game.home_team,game.away_team)
  const marketLine=lineText(marketMargin,game.home_team,game.away_team)
  const atsLine=pickedSpread(pick,marketSpread)
  const split=status==='VALUE' && pick && game.official_winner && pick!==game.official_winner

  let explanation='The ATS signal is unavailable until both the independent LevLine margin and a sportsbook spread are present.'
  if (status==='NO_EDGE') {
    explanation=`LevLine's independent margin and the sportsbook spread are aligned at ${marketLine}, so there is no ATS side advantage from the fair-line comparison.`
  } else if (status==='VALUE' && split) {
    explanation=`${game.official_winner} remains LevLine's more likely outright winner. ${atsLine} is the ATS value because LevLine's independent model line is ${modelLine} versus ${marketLine} in the market.`
  } else if (status==='VALUE' && pick) {
    explanation=`${game.official_winner} is LevLine's more likely outright winner, and ${atsLine} is also the ATS value. The independent model line is ${modelLine} versus ${marketLine} in the market.`
  }

  return <section className={`ss-ats-value ${status.toLowerCase()}`} aria-label="LevLine ATS value">
    <div className="ss-ats-value-head">
      <div><span>ATS VALUE</span><small>Winner and spread value are separate forecasts</small></div>
      <b>{status==='VALUE'?'MODEL vs MARKET':status==='NO_EDGE'?'NO EDGE':'UNAVAILABLE'}</b>
    </div>
    <div className="ss-ats-value-grid">
      <article className="winner">
        <span>OUTRIGHT FORECAST</span>
        <strong>{game.official_winner} {pct(game.official_winner_probability)}</strong>
        <small>Frozen F-ST win probability</small>
      </article>
      <article className="ats">
        <span>ATS SIDE</span>
        <strong>{status==='VALUE'?atsLine:status==='NO_EDGE'?'No edge':'—'}</strong>
        <small>{status==='VALUE' && num(edge)!=null ? `${num(edge).toFixed(1)} pts between model and market` : 'Independent margin vs sportsbook line'}</small>
      </article>
      <article>
        <span>LEVLINE MODEL LINE</span>
        <strong>{modelLine}</strong>
        <small>Independent expected-margin forecast</small>
      </article>
      <article>
        <span>MARKET LINE</span>
        <strong>{marketLine}</strong>
        <small>Sportsbook spread</small>
      </article>
    </div>
    <p className={split?'split':''}>{split && <b>Winner / ATS split · </b>}{explanation}</p>
  </section>
}

export default function AtsValueLayer() {
  const [games,setGames]=useState([])
  const [routeVersion,setRouteVersion]=useState(0)
  const [host,setHost]=useState(null)

  useEffect(()=>{
    let active=true
    const refresh=()=>loadForecasts().then(rows=>{if(active)setGames(rows)})
    refresh()
    const onHash=()=>setRouteVersion(value=>value+1)
    window.addEventListener('hashchange',onHash)
    const timer=window.setInterval(refresh,60_000)
    return ()=>{
      active=false
      window.removeEventListener('hashchange',onHash)
      window.clearInterval(timer)
    }
  },[])

  const gameId=useMemo(()=>currentGameId(),[routeVersion])
  const game=useMemo(()=>games.find(row=>String(row.game_id)===String(gameId)),[games,gameId])

  useEffect(()=>{
    let observer
    const attach=()=>{
      const existing=document.getElementById('ss-ats-value-host')
      if (!gameId) {
        existing?.remove()
        setHost(null)
        return
      }
      const anchor=document.querySelector('.ss-forecast-hero:not(.compact)') || document.querySelector('.ss-forecast-hero')
      if (!anchor) return
      let node=existing
      if (!node) {
        node=document.createElement('div')
        node.id='ss-ats-value-host'
        node.className='ss-ats-value-host'
        anchor.insertAdjacentElement('afterend',node)
      }
      setHost(node)
    }
    attach()
    observer=new MutationObserver(attach)
    observer.observe(document.getElementById('root')||document.body,{childList:true,subtree:true})
    return ()=>{
      observer.disconnect()
      document.getElementById('ss-ats-value-host')?.remove()
      setHost(null)
    }
  },[gameId])

  if (!host || !game) return null
  return createPortal(<AtsValueCard game={game}/>,host)
}
