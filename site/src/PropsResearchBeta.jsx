import React, { useEffect, useMemo, useState } from 'react'
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
  marketFamily,
  numberValue,
  primaryMarketPrice,
  propLabel,
  qualityLabel,
  rangeText,
  sortForBrowse,
  sortTopSignals,
  unitFor,
} from './propsPresentation.js'
import './props-research-beta.css'

const BASE = import.meta.env.BASE_URL
const MARKET_CHIPS = [['ALL','All'],['PASSING','Passing'],['RUSHING','Rushing'],['RECEIVING','Receiving'],['RECEPTIONS','Receptions'],['TDS','TDs']]
const POSITION_CHIPS = ['ALL','QB','RB','WR','TE']
const SIGNAL_CHIPS = [['ALL','All'],['MODEL EDGE','Model Edge'],['WATCH','Watch'],['NO SIGNAL','No Signal']]

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
  if (!(raw === 'props' || raw.startsWith('props/'))) return { active:false, view:'top' }
  const part = raw.split('/')[1] || 'top'
  const aliases = { board:'top', performance:'history' }
  const view = aliases[part] || part
  return { active:true, view:['top','games','all','history','about'].includes(view) ? view : 'top' }
}

function navigate(path) {
  window.location.hash = '#/' + path
  window.scrollTo({ top:0, behavior:'smooth' })
}

function ResearchLockup({ compact=false }) {
  return <span className={'lp-lockup' + (compact ? ' compact' : '')}>
    <img src={BASE + 'brand/sunday-signal-icon.svg'} alt=""/>
    <span>
      <strong>LEVLINE PROPS</strong>
      <small>RESEARCH BETA</small>
    </span>
  </span>
}

function SignalPill({ state }) {
  const label = state || 'NO SIGNAL'
  const key = label.toLowerCase().replaceAll(' ', '-')
  return <span className={'lp-signal ' + key}><i aria-hidden="true"/>{label}</span>
}

function QualityPill({ forecast }) {
  const state = String(forecast?.data_quality?.state || 'UNKNOWN').toUpperCase()
  return <span className={'lp-quality ' + state.toLowerCase()}>{state} DATA QUALITY</span>
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

function ContextHeader({ payload, history }) {
  const rows = payload?.forecasts || []
  const games = new Set(rows.map(row=>row.game_id).filter(Boolean)).size
  const summary = payload?.summary || {}
  const nextKickoff = [...rows].sort((a,b)=>Date.parse(a.kickoff_utc||'')-Date.parse(b.kickoff_utc||''))[0]?.kickoff_utc
  return <section className="lp-context">
    <div className="lp-context-copy">
      <div className="lp-eyebrow-row"><span>LEVLINE PROPS <b>β</b></span>{payload?.generated_utc && <small>Updated {formatTimestamp(payload.generated_utc)}</small>}</div>
      <h1>Fair lines first. Market comparison second.</h1>
      <p>{games ? games + ' games' : 'Current slate'}{nextKickoff ? ' · Next kickoff ' + formatKickoff(nextKickoff) : ''}</p>
      <ResearchStatus payload={payload} history={history}/>
    </div>
    <div className="lp-summary" aria-label="Current signal counts">
      <Metric label="Model Edge" value={summary.model_edge ?? 0} accent/>
      <Metric label="Watch" value={summary.watch ?? 0}/>
      <Metric label="No Signal" value={summary.no_signal ?? 0} quiet/>
    </div>
  </section>
}

function FilterChips({ label, options, value, onChange }) {
  return <div className="lp-filter-set">
    <span>{label}</span>
    <div className="lp-chip-row">
      {options.map(option=>{
        const key=Array.isArray(option)?option[0]:option
        const text=Array.isArray(option)?option[1]:option
        return <button type="button" key={key} className={value===key?'active':''} aria-pressed={value===key} onClick={()=>onChange(key)}>{text}</button>
      })}
    </div>
  </div>
}

function Filters({ filters, setFilters, showSignal=true, showSort=false }) {
  return <section className="lp-filter-bar" aria-label="Prop filters">
    <FilterChips label="Market" options={MARKET_CHIPS} value={filters.market} onChange={market=>setFilters(current=>({...current,market}))}/>
    <FilterChips label="Position" options={POSITION_CHIPS} value={filters.position} onChange={position=>setFilters(current=>({...current,position}))}/>
    {showSignal && <FilterChips label="Signal" options={SIGNAL_CHIPS} value={filters.signal} onChange={signal=>setFilters(current=>({...current,signal}))}/>}
    <div className="lp-filter-tools">
      <label className="lp-search"><span>Player search</span><input aria-label="Search players" value={filters.search} placeholder="Search player" onChange={event=>setFilters(current=>({...current,search:event.target.value}))}/></label>
      {showSort && <label className="lp-sort"><span>Sort</span><select aria-label="Sort props" value={filters.sort} onChange={event=>setFilters(current=>({...current,sort:event.target.value}))}><option value="signal">Signal state</option><option value="kickoff">Kickoff</option><option value="player">Player</option><option value="fair-line-gap">Fair-line gap</option></select></label>}
    </div>
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

function DriverPreview({ drivers=[] }) {
  if (!drivers.length) return <p className="lp-muted">No driver explanation supplied by the published artifact.</p>
  return <div className="lp-driver-preview">
    {drivers.slice(0,4).map((driver,index)=>{
      const dir=String(driver?.direction||'').toUpperCase()
      const glyph=dir==='UP'?'↑':dir==='DOWN'?'↓':dir==='NEUTRAL'?'→':'•'
      return <div key={String(driver?.label||'driver') + '-' + index} className={'lp-driver ' + dir.toLowerCase()}>
        <span aria-hidden="true">{glyph}</span><b>{driver?.label || 'Model driver'}</b>{driver?.detail && <small>{driver.detail}</small>}
      </div>
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
  const spread=Math.max(max-min, Math.abs(fair-market), 1)
  min-=spread*.12
  max+=spread*.12
  const pos=value=>Math.max(1,Math.min(99,((value-min)/(max-min))*100))
  const marketPos=pos(market), fairPos=pos(fair)
  const bandLeft=low==null?null:pos(low), bandRight=high==null?null:pos(high)
  const aria='Model range ' + (low==null||high==null?'unavailable':formatLine(low)+' to '+formatLine(high)) + '. Market line ' + formatLine(market) + '. LevLine Fair Line ' + formatLine(fair) + '.'
  return <div className="lp-fair-viz" role="img" aria-label={aria}>
    <div className="lp-viz-labels"><span>{low==null?'':formatLine(low)}</span><span>{high==null?'':formatLine(high)}</span></div>
    <div className="lp-viz-track">
      {bandLeft!=null && bandRight!=null && <i className="lp-viz-band" style={{left:bandLeft+'%',width:Math.max(1,bandRight-bandLeft)+'%'}}/>}
      <i className="lp-viz-line"/>
      <span className="lp-viz-marker market" style={{left:marketPos+'%'}}><i/><b>MARKET</b><small>{formatLine(market)}</small></span>
      <span className="lp-viz-marker fair" style={{left:fairPos+'%'}}><i/><b>LEVLINE</b><small>{formatLine(fair)}</small></span>
    </div>
    <div className="lp-viz-caption"><span>{rangeText(forecast)}</span><span>Fair Line vs market</span></div>
  </div>
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
  return { side:'Over', model:forecast?.model?.over_probability, market:forecast?.market?.no_vig_over_probability, edge:forecast?.model?.probability_edge }
}

function marketOffers(forecast) {
  const market=forecast?.market || {}
  const candidates=[market.books,market.book_offers,market.offers]
  return candidates.find(value=>Array.isArray(value)) || []
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
    <section className="lp-analysis-section"><div className="lp-analysis-title"><span>All model drivers</span></div><DriverPreview drivers={forecast.drivers}/></section>
  </div>
}

function NoSignalReason({ forecast }) {
  if (forecast?.signal_state!=='NO SIGNAL') return null
  const reasons=forecast.unavailable_reasons || []
  return <div className="lp-no-signal-copy"><b>No signal published.</b><span>{reasons.length ? reasons.map(reason=>String(reason).replaceAll('_',' ')).join(' · ') : 'The forecast did not satisfy the research-beta publication gate.'}</span></div>
}

function DirectionBlock({ forecast }) {
  if (forecast?.market_kind==='BINARY_TD') {
    return <div className="lp-direction td"><span>{propLabel(forecast.prop_type).toUpperCase()}</span><strong>{formatPercent(forecast?.model?.td_probability)}</strong><small>LevLine probability · market {formatAmerican(primaryMarketPrice(forecast))}</small></div>
  }
  const direction=directionFor(forecast), line=forecast?.market?.line
  return <div className={'lp-direction ' + direction.toLowerCase().replaceAll(' ','-')}>
    <span>MODEL DIRECTION</span>
    <strong>{direction==='MARKET ALIGNED' ? direction : direction + ' ' + formatLine(line)}</strong>
    <small>Signal classification remains {forecast.signal_state || 'NO SIGNAL'}</small>
  </div>
}

function PropCard({ forecast }) {
  const probability=primaryProbability(forecast)
  const unit=unitFor(forecast)
  const lineMarket=forecast.market_kind!=='BINARY_TD'
  return <article className={'lp-card ' + String(forecast.signal_state||'NO SIGNAL').toLowerCase().replaceAll(' ','-')}>
    <header className="lp-card-head">
      <div>
        <div className="lp-player-line"><strong>{forecast.player || 'Unresolved player'}</strong><span>{forecast.position || '—'} · {forecast.team || '—'} vs {forecast.opponent || '—'}</span></div>
        <h2>{propLabel(forecast.prop_type)}</h2>
      </div>
      <SignalPill state={forecast.signal_state}/>
    </header>
    <DirectionBlock forecast={forecast}/>
    {lineMarket && <div className="lp-core-comparison">
      <Metric label="LevLine Fair Line" value={formatLine(forecast?.model?.fair_line)} accent/>
      <Metric label="Market" value={formatLine(forecast?.market?.line)}/>
      <Metric label="Difference" value={formatDifference(forecast?.model?.line_difference,unit.toLowerCase())} accent/>
    </div>}
    <FairLineViz forecast={forecast}/>
    <div className="lp-probability-strip">
      <div><span>LevLine {probability.side}</span><b>{formatPercent(probability.model)}</b></div>
      <div><span>Market {probability.side}</span><b>{formatPercent(probability.market)}</b></div>
      <div><span>Probability gap</span><b>{formatPoints(probability.edge)}</b></div>
    </div>
    <div className="lp-card-support">
      {lineMarket && <div><span>UNCERTAINTY</span><b>{rangeText(forecast)}</b></div>}
      <QualityPill forecast={forecast}/>
    </div>
    <DriverPreview drivers={forecast.drivers}/>
    <NoSignalReason forecast={forecast}/>
    <details className="lp-analysis-details"><summary>View Analysis <span aria-hidden="true">+</span></summary><AnalysisPanel forecast={forecast}/></details>
  </article>
}

function LoadingState() {
  return <section className="lp-loading" aria-label="Loading Props forecasts"><span/><span/><span/><div/><div/></section>
}

function EmptyState({ title='Props publication is waiting for a valid forecast artifact.', copy='No signal is being manufactured. This surface populates only from a contract-valid, prospective Props artifact.' }) {
  return <section className="lp-empty"><span>RESEARCH BETA</span><h2>{title}</h2><p>{copy}</p></section>
}

function TopSignals({ rows }) {
  const [filters,setFilters]=useState({market:'ALL',position:'ALL',signal:'MODEL EDGE',search:'',sort:'signal'})
  const signals=useMemo(()=>sortTopSignals(rows).filter(row=>rowMatches(row,filters)),[rows,filters])
  return <section className="lp-view">
    <div className="lp-view-head"><div><span>TOP SIGNALS</span><h2>Published MODEL EDGE forecasts.</h2><p>Ordered for browsing by probability disagreement, data quality, kickoff, and stable forecast identity. This is not a “best bet” ranking.</p></div><b>{signals.length}</b></div>
    <Filters filters={filters} setFilters={setFilters} showSignal={false}/>
    {!signals.length ? <EmptyState title="No MODEL EDGE forecasts match this view." copy="LevLine is not promoting a WATCH or NO SIGNAL forecast to fill the screen. Adjust the filters or inspect All Props."/> : <section className="lp-card-grid">{signals.map(row=><PropCard key={row.forecast_id} forecast={row}/>)}</section>}
  </section>
}

function CompactProp({ forecast }) {
  const direction=directionFor(forecast)
  const line=forecast?.market?.line
  const fair=forecast?.model?.fair_line
  return <details className="lp-compact-prop">
    <summary>
      <div className="lp-compact-player"><strong>{forecast.player || 'Unresolved player'}</strong><span>{forecast.position || '—'} · {propLabel(forecast.prop_type)}</span></div>
      <div className="lp-compact-lines"><span>{forecast.market_kind==='BINARY_TD' ? formatAmerican(primaryMarketPrice(forecast)) : 'Market ' + formatLine(line) + ' → LevLine ' + formatLine(fair)}</span><b>{direction}</b></div>
      <SignalPill state={forecast.signal_state}/>
      <span className="lp-expand-icon" aria-hidden="true">+</span>
    </summary>
    <div className="lp-compact-analysis"><FairLineViz forecast={forecast}/><DriverPreview drivers={forecast.drivers}/><AnalysisPanel forecast={forecast}/></div>
  </details>
}

function GamesView({ rows }) {
  const [filters,setFilters]=useState({market:'ALL',position:'ALL',signal:'ALL',search:'',sort:'kickoff'})
  const shown=useMemo(()=>sortForBrowse(rows,'kickoff').filter(row=>rowMatches(row,filters)),[rows,filters])
  const groups=useMemo(()=>{
    const map=new Map()
    shown.forEach(row=>{
      const key=row.game_id || ((row.team||'—')+'-'+(row.opponent||'—'))
      if(!map.has(key)) map.set(key,[])
      map.get(key).push(row)
    })
    return [...map.entries()]
  },[shown])
  return <section className="lp-view">
    <div className="lp-view-head"><div><span>GAMES</span><h2>Inspect the player market game by game.</h2><p>Team-grouped props keep each matchup coherent without mixing unrelated forecasts.</p></div><b>{groups.length}</b></div>
    <Filters filters={filters} setFilters={setFilters}/>
    {!groups.length ? <EmptyState title="No games match these filters." copy="No missing rows are backfilled. Adjust filters to inspect the published slate."/> :
    <section className="lp-games">{groups.map(([gameId,gameRows])=>{
      const teams=[...new Set(gameRows.flatMap(row=>[row.team,row.opponent]).filter(Boolean))]
      const teamGroups=[...new Set(gameRows.map(row=>row.team).filter(Boolean))]
      return <article className="lp-game" key={gameId}>
        <header><div><span>{teams.join(' vs ') || gameId}</span><small>{formatKickoff(gameRows[0]?.kickoff_utc)} · {gameRows.length} props</small></div><b>{gameRows.filter(row=>row.signal_state==='MODEL EDGE').length} EDGE</b></header>
        <div className="lp-team-groups">{teamGroups.map(team=><section key={team}><h3>{team}</h3>{gameRows.filter(row=>row.team===team).map(row=><CompactProp key={row.forecast_id} forecast={row}/>)}</section>)}</div>
      </article>
    })}</section>}
  </section>
}

function AllProps({ rows }) {
  const [filters,setFilters]=useState({market:'ALL',position:'ALL',signal:'ALL',search:'',sort:'signal'})
  const shown=useMemo(()=>sortForBrowse(rows,filters.sort).filter(row=>rowMatches(row,filters)),[rows,filters])
  return <section className="lp-view">
    <div className="lp-view-head"><div><span>ALL PROPS</span><h2>Complete published board.</h2><p>Search, filter, sort, and expand any forecast into its full model and market receipt.</p></div><b>{shown.length}</b></div>
    <Filters filters={filters} setFilters={setFilters} showSort/>
    {!shown.length ? <EmptyState title="No published props match these filters." copy="Try a broader market, position, or signal filter."/> :
    <section className="lp-all-list">{shown.map(row=><CompactProp key={row.forecast_id} forecast={row}/>)}</section>}
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
  return <section className="lp-performance">
    <div className="lp-performance-head"><span>LEVLINE PROPS PERFORMANCE</span><h1>Prospective validation, with receipts.</h1><p>Performance concepts remain separate. The interface will not collapse projection error, calibration, market-relative performance, and betting outcomes into a single “accuracy” number.</p></div>
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
    <section className="lp-receipts">{records.map(record=>{
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
    })}</section>}
  </section>
}

function About() {
  return <section className="lp-about">
    <span>HOW LEVLINE PROPS WORKS</span><h1>The Fair Line is the center of the product.</h1><p>LevLine first models the player-stat distribution. The sportsbook market is compared with that distribution afterward. The interface preserves that separation.</p>
    <section className="lp-about-grid">
      <article><b>01 · Fair Line</b><h2>What should the line be?</h2><p>For line markets, the Fair Line is the model distribution’s approximately 50/50 threshold. Mean and median remain available in Full Analysis.</p></article>
      <article><b>02 · Market comparison</b><h2>What is the book offering?</h2><p>Published line, price, and no-vig market probability are shown only when present in the validated public artifact.</p></article>
      <article><b>03 · Signal discipline</b><h2>Direction is not signal state.</h2><p>MODEL EDGE, WATCH, and NO SIGNAL are upstream-governed classifications. The frontend never upgrades a row because the numerical disagreement looks large.</p></article>
      <article><b>04 · Immutable receipts</b><h2>History cannot be rewritten.</h2><p>Original forecasts are stored separately from closing markets and grades so later information cannot replace what LevLine published pregame.</p></article>
    </section>
    <section className="lp-state-guide">
      <div><SignalPill state="MODEL EDGE"/><p>Upstream research criteria support publishing a model edge.</p></div>
      <div><SignalPill state="WATCH"/><p>Worth monitoring, but not promoted to MODEL EDGE.</p></div>
      <div><SignalPill state="NO SIGNAL"/><p>LevLine is withholding an unsupported claim; this is a discipline state, not a red failure.</p></div>
    </section>
  </section>
}

function ProductNav({ view }) {
  const items=[['top','Top Signals','props'],['games','Games','props/games'],['all','All Props','props/all'],['history','Performance','props/history']]
  return <nav className="lp-product-nav" aria-label="LevLine Props views">{items.map(([key,label,path])=><button key={key} className={view===key?'active':''} aria-current={view===key?'page':undefined} onClick={()=>navigate(path)}>{label}</button>)}</nav>
}

function PropsHeader({ view }) {
  return <>
    <header className="lp-header">
      <button className="lp-brand-button" onClick={()=>navigate('props')} aria-label="LevLine Props Research Beta"><ResearchLockup/></button>
      <ProductNav view={view}/>
      <div className="lp-header-actions"><button onClick={()=>navigate('props/about')} className={view==='about'?'active':''}>How It Works</button><button onClick={()=>navigate('forecasts')}>Sunday Signal ↗</button></div>
    </header>
    <div className="lp-mobile-product-nav"><ProductNav view={view}/></div>
  </>
}

export default function PropsResearchBeta() {
  const [route,setRoute]=useState(routeState)
  const [publicPayload,setPublicPayload]=useState(undefined)
  const [historyPayload,setHistoryPayload]=useState(undefined)

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
    if(!route.active) return
    let cancelled=false
    Promise.all([fetchJson('props_public.json',null),fetchJson('props_history.json',{records:[]})]).then(([published,history])=>{
      if(cancelled) return
      setPublicPayload(published)
      setHistoryPayload(history)
    })
    return ()=>{cancelled=true}
  },[route.active])

  if(!route.active) return null

  const rows=publicPayload?.forecasts || []
  const loading=publicPayload===undefined || historyPayload===undefined

  return <div className="lp-app">
    <PropsHeader view={route.view}/>
    <main>
      {loading ? <LoadingState/> : <>
        {route.view!=='about' && route.view!=='history' && <ContextHeader payload={publicPayload} history={historyPayload}/>}
        {!publicPayload && route.view!=='about' && route.view!=='history' ? <EmptyState/> : <>
          {route.view==='top' && <TopSignals rows={rows}/>}
          {route.view==='games' && <GamesView rows={rows}/>}
          {route.view==='all' && <AllProps rows={rows}/>}
        </>}
        {route.view==='history' && <History payload={historyPayload}/>}
        {route.view==='about' && <About/>}
      </>}
    </main>
    <footer className="lp-footer"><ResearchLockup compact/><span>Prospective forecasts · immutable receipts · fail-closed publication</span><button onClick={()=>navigate('props/about')}>How LevLine Props Works</button></footer>
  </div>
}
