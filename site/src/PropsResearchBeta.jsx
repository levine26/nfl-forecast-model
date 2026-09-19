import React, { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  MARKET_FILTERS,
  directionFor,
  formatAmerican,
  formatDifference,
  formatKickoff,
  formatLine,
  formatPercent,
  formatPoints,
  formatTimestamp,
  numberValue,
  primaryMarketPrice,
  propLabel,
  qualityLabel,
  rangeText,
  sortForBrowse,
  unitFor,
} from './propsPresentation.js'
import './props-research-beta.css'

const BASE = import.meta.env.BASE_URL
const MARKET_OPTIONS = [['ALL','All markets'],['PASSING','Passing'],['RUSHING','Rushing'],['RECEIVING','Receiving'],['RECEPTIONS','Receptions'],['TDS','Touchdowns']]
const POSITION_OPTIONS = ['ALL','QB','RB','WR','TE']
const SIGNAL_OPTIONS = [['ALL','All signals'],['MODEL EDGE','Model Edge'],['WATCH','Watch'],['NO SIGNAL','No Signal']]
const SORT_OPTIONS = [['signal','Signal'],['kickoff','Kickoff'],['player','Player'],['fair-line-gap','Gap']]
const HISTORY_PAGE_SIZE = 100

async function fetchJson(name, fallback) {
  try {
    const response = await fetch(BASE + 'data/' + name, { cache: 'no-store' })
    return response.ok ? await response.json() : fallback
  } catch {
    return fallback
  }
}

function routeState() {
  const raw = window.location.hash.replace(/^#\/?/, '')
  const parts = raw.split('/').filter(Boolean)
  if (parts[0] !== 'props') return { active:false, view:'board', gameId:null }
  const requested = parts[1] || 'board'
  const aliases = { top:'board', all:'board', performance:'history' }
  const view = aliases[requested] || requested
  if (view === 'games' && parts.length > 2) {
    return { active:true, view:'games', gameId:decodeURIComponent(parts.slice(2).join('/')) }
  }
  return {
    active:true,
    view:['board','games','history','about'].includes(view) ? view : 'board',
    gameId:null,
  }
}

function navigate(path) {
  window.location.hash = '#/' + path
  window.scrollTo({ top:0, behavior:'smooth' })
}

function ResearchLockup({ compact=false }) {
  return <span className={'lp-lockup' + (compact ? ' compact' : '')}>
    <img src={BASE + 'brand/sunday-signal-icon.svg'} alt=""/>
    <span><strong>LEVLINE PROPS</strong><small>RESEARCH BETA</small></span>
  </span>
}

function SignalPill({ state }) {
  const label = state || 'NO SIGNAL'
  const key = label.toLowerCase().replaceAll(' ', '-')
  return <span className={'lp-signal ' + key}><i aria-hidden="true"/>{label}</span>
}

function Metric({ label, value, accent=false, quiet=false }) {
  return <div className={'lp-metric' + (accent ? ' accent' : '') + (quiet ? ' quiet' : '')}>
    <span>{label}</span><strong>{value}</strong>
  </div>
}

function ResearchStatus({ payload, history }) {
  const graded = (history?.records || []).filter(row=>row?.grade?.grading_result).length
  return <details className="lp-research-status">
    <summary><span>RESEARCH BETA</span><b>·</b><span>{graded ? graded + ' graded forecasts' : 'Prospective validation underway'}</span><i aria-hidden="true">ⓘ</i></summary>
    <div>
      <p>LevLine Props preserves prospective forecasts and immutable receipts. Research Beta does not claim demonstrated profitability, market superiority, or established calibration.</p>
      <p>Completed outcomes can grade published forecasts, but the interface does not rewrite historical forecasts or create new signal states.</p>
      {payload?.generated_utc && <small>Current public artifact: {formatTimestamp(payload.generated_utc)}</small>}
    </div>
  </details>
}

function BoardHeader({ payload, history }) {
  const rows = payload?.forecasts || []
  const games = new Set(rows.map(row=>row.game_id).filter(Boolean)).size
  const edges = rows.filter(row=>row.signal_state==='MODEL EDGE').length
  const watch = rows.filter(row=>row.signal_state==='WATCH').length
  return <section className="lp-board-header">
    <div className="lp-board-copy">
      <div className="lp-eyebrow"><span>LEVLINE PROPS</span><b>RESEARCH BETA</b></div>
      <h1>Player markets through the LevLine lens.</h1>
      <p><strong>Fair Line</strong> = where LevLine believes the sportsbook line should be.</p>
      <ResearchStatus payload={payload} history={history}/>
    </div>
    <div className="lp-summary-strip" aria-label="Current Props slate">
      <Metric label="Games" value={games}/>
      <Metric label="Markets" value={rows.length}/>
      <Metric label="Watch" value={watch}/>
      <Metric label="Model Edge" value={edges} accent={edges>0}/>
      <Metric label="Updated" value={payload?.generated_utc ? formatTimestamp(payload.generated_utc).replace(/^[^,]+,\s*/,'') : '—'} quiet/>
    </div>
  </section>
}

function SelectControl({ label, value, options, onChange }) {
  return <label className="lp-select-control">
    <span>{label}</span>
    <select aria-label={label} value={value} onChange={event=>onChange(event.target.value)}>
      {options.map(option=>{
        const key=Array.isArray(option)?option[0]:option
        const text=Array.isArray(option)?option[1]:(option==='ALL'?'All positions':option)
        return <option value={key} key={key}>{text}</option>
      })}
    </select>
  </label>
}

function Filters({ filters, setFilters, hideSignal=false }) {
  return <section className="lp-filters" aria-label="Prop filters">
    <label className="lp-player-search">
      <span>Search</span>
      <input aria-label="Search players" value={filters.search} placeholder="Search players" onChange={event=>setFilters(current=>({...current,search:event.target.value}))}/>
    </label>
    <SelectControl label="Market" value={filters.market} options={MARKET_OPTIONS} onChange={market=>setFilters(current=>({...current,market}))}/>
    <SelectControl label="Position" value={filters.position} options={POSITION_OPTIONS} onChange={position=>setFilters(current=>({...current,position}))}/>
    {!hideSignal && <SelectControl label="Signal" value={filters.signal} options={SIGNAL_OPTIONS} onChange={signal=>setFilters(current=>({...current,signal}))}/>}
    <SelectControl label="Sort" value={filters.sort} options={SORT_OPTIONS} onChange={sort=>setFilters(current=>({...current,sort}))}/>
  </section>
}

function rowMatches(row, filters) {
  const marketOk = filters.market==='ALL' || (MARKET_FILTERS[filters.market] || []).includes(row.prop_type)
  const positionOk = filters.position==='ALL' || row.position===filters.position
  const signalOk = !filters.signal || filters.signal==='ALL' || row.signal_state===filters.signal
  const search = String(filters.search || '').trim().toLowerCase()
  const searchOk = !search || [row.player,row.team,row.opponent,propLabel(row.prop_type)].some(value=>String(value||'').toLowerCase().includes(search))
  return marketOk && positionOk && signalOk && searchOk
}

function marketOffers(forecast) {
  const market=forecast?.market || {}
  const candidates=[market.books,market.book_offers,market.offers]
  return candidates.find(value=>Array.isArray(value)) || []
}

function primaryProbability(forecast) {
  if (forecast?.market_kind==='BINARY_TD') {
    return { side:'TD', model:forecast?.model?.td_probability, market:forecast?.model?.market_no_vig_probability, edge:forecast?.model?.probability_edge }
  }
  const direction=directionFor(forecast)
  if (direction==='UNDER') {
    const model=numberValue(forecast?.model?.under_probability)
    const market=numberValue(forecast?.market?.no_vig_under_probability)
    return { side:'Under', model, market, edge:model==null||market==null?null:model-market }
  }
  const model=numberValue(forecast?.model?.over_probability)
  const market=numberValue(forecast?.market?.no_vig_over_probability)
  return { side:'Over', model, market, edge:forecast?.model?.probability_edge ?? (model==null||market==null?null:model-market) }
}

function DriverPreview({ drivers=[], limit=3 }) {
  if (!drivers.length) return <p className="lp-muted">No driver explanation supplied by the published artifact.</p>
  return <div className="lp-driver-preview">
    {drivers.slice(0,limit).map((driver,index)=>{
      const dir=String(driver?.direction||'').toUpperCase()
      const glyph=dir==='UP'?'↑':dir==='DOWN'?'↓':dir==='NEUTRAL'?'→':'•'
      return <article key={String(driver?.label||'driver') + '-' + index} className={'lp-driver ' + dir.toLowerCase()}>
        <span aria-hidden="true">{glyph}</span>
        <div><b>{driver?.label || 'Model driver'}</b>{driver?.detail && <p>{driver.detail}</p>}</div>
      </article>
    })}
  </div>
}

function FairLineViz({ forecast }) {
  if (forecast?.market_kind==='BINARY_TD') return null
  const market=numberValue(forecast?.market?.line)
  const fair=numberValue(forecast?.model?.fair_line)
  const low=numberValue(forecast?.model?.prediction_interval?.low)
  const high=numberValue(forecast?.model?.prediction_interval?.high)
  if (market==null || fair==null) return <div className="lp-viz-unavailable">Fair Line comparison unavailable because a required line is missing.</div>
  const values=[market,fair,low,high].filter(value=>value!=null)
  let min=Math.min(...values), max=Math.max(...values)
  const spread=Math.max(max-min,Math.abs(fair-market),1)
  min-=spread*.12
  max+=spread*.12
  const pos=value=>Math.max(1,Math.min(99,((value-min)/(max-min))*100))
  const bandLeft=low==null?null:pos(low), bandRight=high==null?null:pos(high)
  const aria='Model range ' + (low==null||high==null?'unavailable':formatLine(low)+' to '+formatLine(high)) + '. Market line ' + formatLine(market) + '. LevLine Fair Line ' + formatLine(fair) + '.'
  return <div className="lp-fair-viz" role="img" aria-label={aria}>
    <div className="lp-viz-track">
      {bandLeft!=null && bandRight!=null && <i className="lp-viz-band" style={{left:bandLeft+'%',width:Math.max(1,bandRight-bandLeft)+'%'}}/>}
      <i className="lp-viz-line"/>
      <span className="lp-viz-marker market" style={{left:pos(market)+'%'}}><i/><b>MARKET</b><small>{formatLine(market)}</small></span>
      <span className="lp-viz-marker fair" style={{left:pos(fair)+'%'}}><i/><b>LEVLINE</b><small>{formatLine(fair)}</small></span>
    </div>
    <div className="lp-viz-caption"><span>{rangeText(forecast)}</span><span>Fair Line vs market</span></div>
  </div>
}

function LineMovement({ forecast }) {
  const market=forecast?.market || {}
  const open=numberValue(market.open_line ?? market.opening_line)
  const current=numberValue(market.line)
  const fair=numberValue(forecast?.model?.fair_line)
  if (open==null || current==null || fair==null) return null
  return <section className="lp-analysis-section">
    <div className="lp-analysis-title"><span>Line movement</span><small>Prospective market state only</small></div>
    <div className="lp-movement"><div><span>OPEN</span><b>{formatLine(open)}</b></div><i/><div><span>CURRENT</span><b>{formatLine(current)}</b></div><i/><div><span>LEVLINE</span><b>{formatLine(fair)}</b></div></div>
  </section>
}

function MarketTable({ forecast }) {
  const offers=marketOffers(forecast)
  if (!offers.length) return null
  return <section className="lp-analysis-section">
    <div className="lp-analysis-title"><span>Sportsbook market</span><small>Published offers only</small></div>
    <div className="lp-book-table">
      <div className="head"><span>Book</span><span>Line</span><span>Price</span></div>
      {offers.map((offer,index)=><div key={String(offer?.sportsbook||offer?.book||'book')+'-'+index}><b>{offer?.sportsbook||offer?.book||'—'}</b><span>{formatLine(offer?.line)}</span><span>{formatAmerican(offer?.price_american ?? offer?.over_price_american ?? offer?.td_price_american)}</span></div>)}
    </div>
  </section>
}

function AnalysisPanel({ forecast }) {
  const market=forecast?.market || {}, model=forecast?.model || {}, quality=forecast?.data_quality || {}
  return <div className="lp-analysis">
    <section className="lp-analysis-section">
      <div className="lp-analysis-title"><span>Model distribution</span><small>{model.version || 'Model version unavailable'}</small></div>
      <div className="lp-analysis-grid">
        <Metric label="Mean" value={formatLine(model.mean)}/>
        <Metric label="Median" value={formatLine(model.median)}/>
        <Metric label="Fair Line" value={formatLine(model.fair_line)} accent/>
        <Metric label="Over probability" value={formatPercent(model.over_probability)}/>
        <Metric label="Under probability" value={formatPercent(model.under_probability)}/>
        <Metric label="Push probability" value={formatPercent(model.push_probability)}/>
        <Metric label="TD probability" value={formatPercent(model.td_probability)}/>
        <Metric label="Expected TDs" value={formatLine(model.expected_tds)}/>
        <Metric label="Simulations" value={model.simulation_count ? Number(model.simulation_count).toLocaleString() : '—'}/>
      </div>
    </section>
    <section className="lp-analysis-section">
      <div className="lp-analysis-title"><span>Market comparison</span><small>{market.sportsbook || market.source || 'Market source unavailable'}</small></div>
      <div className="lp-analysis-grid">
        <Metric label="Market line" value={formatLine(market.line)}/>
        <Metric label="Line difference" value={formatDifference(model.line_difference,unitFor(forecast).toLowerCase())} accent/>
        <Metric label="Market no-vig" value={formatPercent(model.market_no_vig_probability)}/>
        <Metric label="Probability edge" value={formatPoints(model.probability_edge)} accent/>
        <Metric label="Fair odds" value={formatAmerican(model.fair_odds_american)}/>
        <Metric label="Sportsbook Over" value={formatAmerican(market.over_price_american)}/>
        <Metric label="Sportsbook Under" value={formatAmerican(market.under_price_american)}/>
        <Metric label="Sportsbook TD" value={formatAmerican(market.td_price_american)}/>
        <Metric label="Consensus line" value={formatLine(market.consensus_line)}/>
      </div>
    </section>
    <LineMovement forecast={forecast}/>
    <MarketTable forecast={forecast}/>
    <section className="lp-analysis-section">
      <div className="lp-analysis-title"><span>Quality & provenance</span><small>{qualityLabel(forecast)}</small></div>
      <div className="lp-provenance">
        <div><span>Forecast timestamp</span><b>{formatTimestamp(forecast.forecast_timestamp_utc)}</b></div>
        <div><span>Market captured</span><b>{formatTimestamp(market.captured_utc)}</b></div>
        <div><span>Data horizon</span><b>{formatTimestamp(forecast.data_horizon_utc)}</b></div>
        <div><span>Kickoff</span><b>{formatTimestamp(forecast.kickoff_utc)}</b></div>
        <div><span>Model version</span><b>{model.version || '—'}</b></div>
        <div><span>Forecast ID</span><b>{forecast.forecast_id || '—'}</b></div>
      </div>
      {Array.isArray(quality.notes) && quality.notes.length>0 && <div className="lp-quality-notes">{quality.notes.map((note,index)=><span key={index}>{note}</span>)}</div>}
    </section>
    <section className="lp-analysis-section"><div className="lp-analysis-title"><span>All published model drivers</span></div><DriverPreview drivers={forecast.drivers} limit={99}/></section>
  </div>
}

function NoSignalReason({ forecast }) {
  if (forecast?.signal_state!=='NO SIGNAL') return null
  const reasons=forecast.unavailable_reasons || []
  return <div className="lp-no-signal-copy"><b>No signal published.</b><span>{reasons.length ? reasons.map(reason=>String(reason).replaceAll('_',' ')).join(' · ') : 'The forecast did not satisfy the research-beta publication gate.'}</span></div>
}

function DetailLead({ forecast }) {
  if (forecast?.market_kind==='BINARY_TD') {
    const probability=primaryProbability(forecast)
    return <div className="lp-detail-lead">
      <span>LEVLINE VIEW</span>
      <strong>{propLabel(forecast.prop_type).toUpperCase()}</strong>
      <small>{formatPercent(probability.model)} model probability · market {formatAmerican(primaryMarketPrice(forecast))}</small>
    </div>
  }
  const direction=directionFor(forecast)
  const label=direction==='UNAVAILABLE' ? 'MARKET UNAVAILABLE' : direction==='MARKET ALIGNED' ? direction : direction + ' ' + formatLine(forecast?.market?.line)
  return <div className={'lp-detail-lead ' + direction.toLowerCase().replaceAll(' ','-')}>
    <span>LEVLINE LEAN</span><strong>{label}</strong>
    <small>Signal classification: {forecast.signal_state || 'NO SIGNAL'}</small>
  </div>
}

function TheSignal({ forecast }) {
  return <section className="lp-the-signal">
    <div className="lp-signal-mark" aria-hidden="true"><img src={BASE + 'brand/sunday-signal-icon.svg'} alt=""/></div>
    <div>
      <span>THE SIGNAL</span>
      <h3>Why LevLine landed here.</h3>
      <DriverPreview drivers={forecast.drivers} limit={3}/>
    </div>
  </section>
}

function PropDetail({ forecast }) {
  const probability=primaryProbability(forecast)
  const binary=forecast?.market_kind==='BINARY_TD'
  return <div className="lp-prop-detail">
    <header className="lp-detail-head">
      <div><strong>{forecast.player || 'Unresolved player'}</strong><span>{propLabel(forecast.prop_type)} · {forecast.team || '—'} vs {forecast.opponent || '—'} · {formatKickoff(forecast.kickoff_utc)}</span></div>
      <SignalPill state={forecast.signal_state}/>
    </header>
    <DetailLead forecast={forecast}/>
    <div className="lp-detail-comparison">
      {binary ? <>
        <Metric label="Sportsbook price" value={formatAmerican(primaryMarketPrice(forecast))}/>
        <Metric label="LevLine probability · fair price" value={formatPercent(probability.model) + (numberValue(forecast?.model?.fair_odds_american)!=null ? ' · ' + formatAmerican(forecast.model.fair_odds_american) : '')} accent/>
        <Metric label="Probability disagreement" value={formatPoints(probability.edge)} accent/>
      </> : <>
        <Metric label="Market" value={formatLine(forecast?.market?.line)}/>
        <Metric label="LevLine Fair Line" value={formatLine(forecast?.model?.fair_line)} accent/>
        <Metric label="Difference" value={formatDifference(forecast?.model?.line_difference,unitFor(forecast).toLowerCase())} accent/>
      </>}
    </div>
    <FairLineViz forecast={forecast}/>
    <TheSignal forecast={forecast}/>
    <NoSignalReason forecast={forecast}/>
    <details className="lp-advanced"><summary>Advanced Analysis <span aria-hidden="true">+</span></summary><AnalysisPanel forecast={forecast}/></details>
  </div>
}

function boardValues(forecast) {
  if (forecast?.market_kind==='BINARY_TD') {
    const probability=primaryProbability(forecast)
    return {
      market:formatAmerican(primaryMarketPrice(forecast)),
      levline:formatPercent(probability.model),
      lean:'TD',
      gap:formatPoints(probability.edge),
      marketLabel:'Price',
      levlineLabel:'TD probability',
    }
  }
  return {
    market:formatLine(forecast?.market?.line),
    levline:formatLine(forecast?.model?.fair_line),
    lean:directionFor(forecast),
    gap:formatDifference(forecast?.model?.line_difference,unitFor(forecast)),
    marketLabel:'Market',
    levlineLabel:'LevLine',
  }
}

function PropBoardRow({ forecast }) {
  const values=boardValues(forecast)
  return <details className={'lp-board-row ' + String(forecast.signal_state||'NO SIGNAL').toLowerCase().replaceAll(' ','-')}>
    <summary>
      <div className="lp-row-player"><strong>{forecast.player || 'Unresolved player'}</strong><span>{propLabel(forecast.prop_type)} · {forecast.team || '—'} vs {forecast.opponent || '—'}</span></div>
      <div className="lp-row-value"><span>{values.marketLabel}</span><b>{values.market}</b></div>
      <div className="lp-row-value lp-row-fair"><span>{values.levlineLabel}</span><b>{values.levline}</b></div>
      <div className="lp-row-value lp-row-lean"><span>Lean</span><b>{values.lean}</b></div>
      <div className="lp-row-value lp-row-gap"><span>Gap</span><b>{values.gap}</b></div>
      <SignalPill state={forecast.signal_state}/>
      <i className="lp-row-chevron" aria-hidden="true">›</i>
    </summary>
    <PropDetail forecast={forecast}/>
  </details>
}

function BoardTable({ rows, emptyTitle='No published props match these filters.' }) {
  if (!rows.length) return <EmptyState title={emptyTitle} copy="Try a broader market, position, signal, or player search." compact/>
  return <section className="lp-board-table">
    <div className="lp-board-labels" aria-hidden="true"><span>Player & prop</span><span>Market</span><span>LevLine</span><span>Lean</span><span>Gap</span><span>Signal</span><span/></div>
    <div>{rows.map(row=><PropBoardRow key={row.forecast_id || [row.player,row.prop_type,row.team].join('-')} forecast={row}/>)}</div>
  </section>
}

function LoadingState() {
  return <section className="lp-loading" aria-label="Loading Props forecasts"><span/><span/><span/><div/><div/></section>
}

function EmptyState({ title='Props publication is waiting for a valid forecast artifact.', copy='No signal is being manufactured. This surface populates only from a contract-valid, prospective Props artifact.', compact=false }) {
  return <section className={'lp-empty' + (compact?' compact':'')}><span>RESEARCH BETA</span><h2>{title}</h2><p>{copy}</p></section>
}

function Radar({ rows }) {
  const radar=useMemo(()=>sortForBrowse(rows,'signal').filter(row=>row.signal_state==='MODEL EDGE'||row.signal_state==='WATCH').slice(0,12),[rows])
  const edges=rows.filter(row=>row.signal_state==='MODEL EDGE').length
  return <section className="lp-radar">
    <div className="lp-section-head">
      <div><span>ON LEVLINE'S RADAR</span><h2>Markets worth a closer look.</h2><p>MODEL EDGE appears first when published; WATCH remains clearly distinct and is never upgraded by the interface.</p></div>
      <b>{radar.length}</b>
    </div>
    {!edges && <div className="lp-edge-empty"><span className="lp-edge-empty-mark" aria-hidden="true">◇</span><div><strong>No MODEL EDGE signals right now.</strong><span>LevLine is not upgrading WATCH forecasts simply to populate the board.</span></div></div>}
    {radar.length ? <BoardTable rows={radar}/> : <EmptyState compact title="Nothing is on LevLine's radar right now." copy="The full published market remains available below."/>}
  </section>
}

function FullMarket({ rows }) {
  const [filters,setFilters]=useState({market:'ALL',position:'ALL',signal:'ALL',search:'',sort:'signal'})
  const [limit,setLimit]=useState(120)
  useEffect(()=>setLimit(120),[filters.market,filters.position,filters.signal,filters.search,filters.sort])
  const shown=useMemo(()=>sortForBrowse(rows,filters.sort).filter(row=>rowMatches(row,filters)),[rows,filters])
  const visible=shown.slice(0,limit)
  return <section className="lp-full-market">
    <div className="lp-section-head">
      <div><span>FULL MARKET</span><h2>Every published LevLine prop.</h2><p>Search, filter, and expand only the forecasts you want to inspect.</p></div>
      <b>{shown.length}</b>
    </div>
    <Filters filters={filters} setFilters={setFilters}/>
    <BoardTable rows={visible}/>
    {visible.length<shown.length && <div className="lp-load-more"><button type="button" onClick={()=>setLimit(current=>current+120)}>Load 120 more <span>{visible.length} of {shown.length}</span></button></div>}
  </section>
}

function PropsBoard({ rows, payload, history }) {
  return <>
    <BoardHeader payload={payload} history={history}/>
    {payload ? <><Radar rows={rows}/><FullMarket rows={rows}/></> : <EmptyState/>}
  </>
}

function gameGroups(rows) {
  const map=new Map()
  rows.forEach(row=>{
    const key=row.game_id || ((row.team||'—')+'-'+(row.opponent||'—'))
    if(!map.has(key)) map.set(key,[])
    map.get(key).push(row)
  })
  return [...map.entries()].sort((a,b)=>{
    const ak=Date.parse(a[1][0]?.kickoff_utc||'')
    const bk=Date.parse(b[1][0]?.kickoff_utc||'')
    return (Number.isFinite(ak)?ak:Number.MAX_SAFE_INTEGER)-(Number.isFinite(bk)?bk:Number.MAX_SAFE_INTEGER)
  })
}

function GamesIndex({ rows }) {
  const groups=useMemo(()=>gameGroups(rows),[rows])
  return <section className="lp-games-page">
    <div className="lp-page-head"><span>GAMES</span><h1>Browse the slate, then go deep.</h1><p>Start with the matchup. Open a game only when you want its player markets.</p></div>
    {!groups.length ? <EmptyState title="No game-level Props slate is published yet."/> :
    <section className="lp-games-index">{groups.map(([gameId,gameRows])=>{
      const teams=[...new Set(gameRows.flatMap(row=>[row.team,row.opponent]).filter(Boolean))].slice(0,2)
      const watch=gameRows.filter(row=>row.signal_state==='WATCH').length
      const edges=gameRows.filter(row=>row.signal_state==='MODEL EDGE').length
      return <button type="button" className="lp-game-index-row" key={gameId} onClick={()=>navigate('props/games/'+encodeURIComponent(gameId))}>
        <div><strong>{teams.join(' vs ') || gameId}</strong><span>{formatKickoff(gameRows[0]?.kickoff_utc)}</span></div>
        <span>{gameRows.length}<small>markets</small></span>
        <span>{watch}<small>watch</small></span>
        <span className={edges?'edge':''}>{edges}<small>model edge</small></span>
        <i aria-hidden="true">›</i>
      </button>
    })}</section>}
  </section>
}

function GameDetail({ rows, gameId }) {
  const gameRows=rows.filter(row=>(row.game_id || ((row.team||'—')+'-'+(row.opponent||'—')))===gameId)
  const [filters,setFilters]=useState({market:'ALL',position:'ALL',signal:'ALL',search:'',sort:'signal'})
  const shown=useMemo(()=>sortForBrowse(gameRows,filters.sort).filter(row=>rowMatches(row,filters)),[gameRows,filters])
  const teams=[...new Set(gameRows.flatMap(row=>[row.team,row.opponent]).filter(Boolean))].slice(0,2)
  if(!gameRows.length) return <section className="lp-games-page"><button className="lp-back" onClick={()=>navigate('props/games')}>← All games</button><EmptyState title="This game is not in the current published Props artifact." copy="Return to Games to inspect the active slate."/></section>
  return <section className="lp-games-page">
    <button className="lp-back" onClick={()=>navigate('props/games')}>← All games</button>
    <div className="lp-game-detail-head">
      <div><span>GAME PROPS</span><h1>{teams.join(' vs ') || gameId}</h1><p>{formatKickoff(gameRows[0]?.kickoff_utc)} · {gameRows.length} published markets</p></div>
      <div><Metric label="Watch" value={gameRows.filter(row=>row.signal_state==='WATCH').length}/><Metric label="Model Edge" value={gameRows.filter(row=>row.signal_state==='MODEL EDGE').length} accent/></div>
    </div>
    <Filters filters={filters} setFilters={setFilters}/>
    <BoardTable rows={shown} emptyTitle="No props in this game match the current filters."/>
  </section>
}

function marketReceipt(market={}) {
  const price=market.td_price_american ?? market.over_price_american
  if (market.line!=null) return formatLine(market.line) + (price!=null ? ' · ' + formatAmerican(price) : '')
  return formatAmerican(price)
}

function receiptProbability(original={}) {
  if (original.market_kind==='BINARY_TD' || ['anytime_td','rushing_td','receiving_td'].includes(original.prop_type)) return formatPercent(original?.model?.td_probability)
  return formatPercent(original?.model?.over_probability)
}

function History({ payload }) {
  const records=payload?.records || []
  const graded=records.filter(record=>record?.grade?.grading_result)
  const closed=records.filter(record=>record?.closing_market)
  const [visibleCount,setVisibleCount]=useState(HISTORY_PAGE_SIZE)
  const visibleRecords=useMemo(
    ()=>records.slice(Math.max(0,records.length-visibleCount)).reverse(),
    [records,visibleCount],
  )
  return <section className="lp-performance">
    <div className="lp-page-head"><span>LEVLINE PROPS PERFORMANCE</span><h1>Prospective validation, with receipts.</h1><p>Projection error, calibration, market-relative performance, and betting outcomes remain separate until the evaluation artifacts support them.</p></div>
    <section className="lp-validation-stats">
      <Metric label="Immutable forecasts" value={records.length}/>
      <Metric label="Graded forecasts" value={graded.length} accent={graded.length>0}/>
      <Metric label="Closing snapshots" value={closed.length}/>
      <div className="lp-validation-state"><span>STATUS</span><b>Prospective validation underway</b><small>Sample size is shown before any empirical claim.</small></div>
    </section>
    <section className="lp-performance-concepts">
      {[
        ['Projection Accuracy','How close was the Fair Line to the actual result?'],
        ['Probability Calibration','Did events occur at the frequency LevLine predicted?'],
        ['Market Performance','Did LevLine compare favorably with the later closing market?'],
        ['Betting Performance','What happened to published MODEL EDGE selections at available prices?'],
      ].map(([title,copy])=><article key={title}><span>{title}</span><p>{copy}</p><b>INSUFFICIENT EVALUATION DATA</b><small>Awaiting a validated empirical evaluation artifact.</small></article>)}
    </section>
    <section className="lp-calibration-empty"><div><span>CALIBRATION</span><h2>Calibration visualization is data-gated.</h2><p>No fixture or tiny-sample percentages are presented as real calibration results.</p></div><b>N = {graded.length}</b></section>
    <div className="lp-receipts-head"><div><span>HISTORY RECEIPTS</span><h2>Forecasts of record.</h2></div><p>Original forecast, closing market, and result remain separate append-only facts.</p></div>
    {!records.length ? <EmptyState title="No prospective Props receipts have been published yet." copy="Original forecasts will appear here after the first valid pregame publication. Grading never rewrites the original."/> :
    <>
      <div className="lp-history-window" aria-live="polite">Showing newest {visibleRecords.length.toLocaleString()} of {records.length.toLocaleString()} immutable receipts.</div>
      <section className="lp-receipts">{visibleRecords.map(record=>{
        const original=record.original_forecast || {}, market=original.market || {}, model=original.model || {}, close=record.closing_market || {}, grade=record.grade || {}
        return <details key={record.forecast_id} className="lp-receipt">
          <summary>
            <div><strong>{original.player || 'Unknown player'}</strong><span>{propLabel(original.prop_type)} · {original.team || '—'} vs {original.opponent || '—'}</span></div>
            <div><span>ORIGINAL</span><b>{marketReceipt(market)}</b></div>
            <div><span>LEVLINE FAIR</span><b>{formatLine(model.fair_line)}</b></div>
            <div><span>RESULT</span><b className={'lp-grade ' + String(grade.grading_result||'pending').toLowerCase()}>{grade.grading_result || 'Pending'}</b></div>
            <i aria-hidden="true">+</i>
          </summary>
          <div className="lp-receipt-grid">
            <Metric label="Original sportsbook line / price" value={marketReceipt(market)}/>
            <Metric label="Original model probability" value={receiptProbability(original)}/>
            <Metric label="Closing line / price" value={record.closing_market ? marketReceipt(close) : 'Not captured'}/>
            <Metric label="Actual result" value={formatLine(grade.actual_result)}/>
            <Metric label="Grade" value={grade.grading_result || 'Pending'}/>
            <Metric label="Forecast timestamp" value={formatTimestamp(original.forecast_timestamp_utc)}/>
            <Metric label="Recorded timestamp" value={formatTimestamp(record.recorded_utc)}/>
            <Metric label="Model version" value={model.version || '—'}/>
          </div>
        </details>
      })}</section>
      {visibleRecords.length < records.length && <div className="lp-load-more lp-history-more"><button onClick={()=>setVisibleCount(count=>Math.min(records.length,count+HISTORY_PAGE_SIZE))}>Load older receipts <span>{(records.length-visibleRecords.length).toLocaleString()} remaining</span></button></div>}
    </>}
  </section>
}

function About() {
  return <section className="lp-about">
    <div className="lp-page-head"><span>HOW LEVLINE PROPS WORKS</span><h1>Depth on demand.</h1><p>The board answers what the market says, what LevLine says, and whether the disagreement cleared the model's publication threshold. Technical evidence remains one click deeper.</p></div>
    <section className="lp-about-grid">
      <article><b>01 · Fair Line</b><h2>What should the line be?</h2><p>For line markets, the Fair Line is the model distribution’s approximately 50/50 threshold. Mean and median remain available in Advanced Analysis.</p></article>
      <article><b>02 · Market comparison</b><h2>What is the book offering?</h2><p>Published line, price, and no-vig market probability are shown only when present in the validated public artifact.</p></article>
      <article><b>03 · Signal discipline</b><h2>Direction is not signal state.</h2><p>MODEL EDGE, WATCH, and NO SIGNAL are upstream-governed classifications. The frontend never upgrades a row because the numerical disagreement looks large.</p></article>
      <article><b>04 · Immutable receipts</b><h2>History cannot be rewritten.</h2><p>Original forecasts are stored separately from closing markets and grades so later information cannot replace what LevLine published pregame.</p></article>
    </section>
    <section className="lp-state-guide">
      <div><SignalPill state="MODEL EDGE"/><p>Upstream research criteria support publishing a model edge.</p></div>
      <div><SignalPill state="WATCH"/><p>Worth monitoring, but not promoted to MODEL EDGE.</p></div>
      <div><SignalPill state="NO SIGNAL"/><p>LevLine is withholding an unsupported claim; this is a discipline state, not a failure.</p></div>
    </section>
  </section>
}

function ProductNav({ view }) {
  const items=[['board','Board','props'],['games','Games','props/games'],['history','Performance','props/history'],['about','How It Works','props/about']]
  return <nav className="lp-product-nav" aria-label="LevLine Props views">{items.map(([key,label,path])=><button key={key} className={view===key?'active':''} aria-current={view===key?'page':undefined} onClick={()=>navigate(path)}>{label}</button>)}</nav>
}

function PropsHeader({ view }) {
  return <>
    <header className="lp-header">
      <button className="lp-brand-button" onClick={()=>navigate('props')} aria-label="LevLine Props Research Beta"><ResearchLockup/></button>
      <ProductNav view={view}/>
      <div className="lp-header-actions"><button onClick={()=>navigate('forecasts')}>Sunday Signal ↗</button></div>
    </header>
    <div className="lp-mobile-product-nav"><ProductNav view={view}/></div>
  </>
}

export default function PropsResearchBeta() {
  const [route,setRoute]=useState(routeState)
  const [publicPayload,setPublicPayload]=useState(undefined)
  const [historyPayload,setHistoryPayload]=useState(undefined)
  const [hostTargets,setHostTargets]=useState({desktop:null,mobile:null})

  useEffect(()=>{
    const onHash=()=>setRoute(routeState())
    window.addEventListener('hashchange',onHash)
    return ()=>window.removeEventListener('hashchange',onHash)
  },[])

  useEffect(()=>{
    document.body.classList.toggle('levline-props-route',route.active)
    return ()=>document.body.classList.remove('levline-props-route')
  },[route.active])

  useEffect(()=>{
    if(route.active) {
      setHostTargets({desktop:null,mobile:null})
      return
    }
    const sync=()=>setHostTargets({desktop:document.querySelector('.ss-desktop-nav'),mobile:document.querySelector('.ss-mobile-nav')})
    sync()
    const frame=window.requestAnimationFrame(sync)
    return ()=>window.cancelAnimationFrame(frame)
  },[route.active])

  useEffect(()=>{
    if(!route.active) return
    let cancelled=false
    Promise.all([fetchJson('props_public.json',null),fetchJson('props_history.json',{records:[]})]).then(([published,history])=>{
      if(cancelled) return
      setPublicPayload(published)
      setHistoryPayload(history)
    })
    return ()=>{cancelled=true}
  },[route.active])

  if(!route.active) return <>
    {hostTargets.desktop && createPortal(<button className="lp-host-props-link" onClick={()=>navigate('props')}>Props</button>,hostTargets.desktop)}
    {hostTargets.mobile && createPortal(<button className="lp-host-props-mobile" onClick={()=>navigate('props')} aria-label="LevLine Props"><span aria-hidden="true">◇</span><small>Props</small></button>,hostTargets.mobile)}
  </>

  const rows=publicPayload?.forecasts || []
  const loading=publicPayload===undefined || historyPayload===undefined

  return <div className="lp-app">
    <PropsHeader view={route.view}/>
    <main>
      {loading ? <LoadingState/> : <>
        {route.view==='board' && <PropsBoard rows={rows} payload={publicPayload} history={historyPayload}/>}
        {route.view==='games' && (!publicPayload ? <GamesIndex rows={[]}/> : (route.gameId ? <GameDetail rows={rows} gameId={route.gameId}/> : <GamesIndex rows={rows}/>))}
        {route.view==='history' && <History payload={historyPayload}/>}
        {route.view==='about' && <About/>}
      </>}
    </main>
    <footer className="lp-footer"><ResearchLockup compact/><span>Prospective forecasts · immutable receipts · fail-closed publication</span><button onClick={()=>navigate('props/about')}>How LevLine Props Works</button></footer>
  </div>
}
