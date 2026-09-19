import React, { useEffect, useMemo, useState } from 'react'
import { propLabel } from './propsPresentation.js'
import './props21-challenger.css'

const ENDPOINT = import.meta.env.BASE_URL + 'data/props21/public_challenger.json'
const number = value => typeof value === 'number' && Number.isFinite(value) ? value : null
const decimal = value => number(value) == null ? 'Unavailable' : value.toLocaleString('en-US', { maximumFractionDigits: 2 })
const percent = value => number(value) == null || value < 0 || value > 1 ? 'Unavailable' : (value * 100).toFixed(1) + '%'
const timestamp = value => value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString('en-US', { dateStyle:'medium', timeStyle:'short', timeZoneName:undefined }) : 'Unavailable'
const words = value => typeof value === 'string' && value ? value.replaceAll('_', ' ') : 'Unavailable'
const array = value => Array.isArray(value) ? value : []
function Metric({ label, value }) { return <div className="p21-metric"><dt>{label}</dt><dd>{value}</dd></div> }

function Forecast({ row }) {
  const market = row.market_state || {}
  const role = row.role_state || {}
  const tags = array(row.qa?.reason_tags)
  const td = /td|touchdown/i.test(row.prop_type || '')
  const signal = row.qa?.signal_state || 'NO SIGNAL'
  const books = array(market.books).map(book => typeof book === 'string' ? book : book?.name || book?.book).filter(Boolean)
  return <details className="p21-row">
    <summary>
      <span className="p21-player"><strong>{row.player_name || row.player_id || 'Player unavailable'}</strong><small>{[row.team, row.position, propLabel(row.prop_type)].filter(Boolean).join(' · ')}</small></span>
      <span className="p21-summary-metric"><small>{td ? 'Pure LevLine TD probability' : 'Pure LevLine Fair Line'}</small><strong>{td ? percent(row.probability_td) : decimal(row.model_median)}</strong></span>
      <span className="p21-summary-metric"><small>{td ? 'Market TD probability' : 'Market line'}</small><strong>{td ? percent(row.market_probability_td) : decimal(row.market_line)}</strong></span>
      <span className="p21-signal">{signal}</span><span className="p21-expand" aria-hidden="true">+</span>
    </summary>
    <div className="p21-detail">
      <h3>Model and market</h3>
      <p>The football forecast and sportsbook benchmark are separate. A disagreement is a research observation, not a validated betting edge.</p>
      <dl className="p21-metrics">
        {td ? <>
          <Metric label="Expected touchdowns (xTD)" value={decimal(typeof row.xtd === 'number' ? row.xtd : row.xtd?.expected_touchdowns)}/>
          <Metric label="Pure LevLine TD probability" value={percent(row.probability_td)}/>
          <Metric label="Pure LevLine fair odds" value={number(row.fair_american_odds) == null ? 'Unavailable' : (row.fair_american_odds > 0 ? '+' : '') + decimal(row.fair_american_odds)}/>
          <Metric label="Market TD probability" value={percent(row.market_probability_td)}/>
        </> : <>
          <Metric label="Pure LevLine mean" value={decimal(row.model_mean)}/>
          <Metric label="Pure LevLine Fair Line (median)" value={decimal(row.model_median)}/>
          <Metric label="Pure LevLine P(over market line)" value={percent(row.probability_over)}/>
          <Metric label="Market no-vig P(over)" value={percent(row.market_probability_over)}/>
        </>}
        <Metric label="Market median line" value={decimal(market.market_median)}/>
        <Metric label="Contributing books" value={books.length ? books.join(', ') : 'Unavailable'}/>
        <Metric label="Quote timestamp (your local time)" value={timestamp(market.quote_as_of)}/>
        <Metric label="Market line dispersion" value={decimal(market.dispersion)}/>
        <Metric label="Role state" value={words(typeof role === 'string' ? role : role.state)}/>
        <Metric label="Role uncertainty" value={words(role.uncertainty)}/>
      </dl>
      <h3>Why this state</h3>
      {tags.length ? <ul className="p21-reasons">{tags.map((tag,index) => <li key={tag.code || index}><strong>{tag.label || words(tag.code || tag)}</strong><p>{tag.explanation || 'The published artifact supplies this tag without further explanation.'}</p></li>)}</ul> : <p>No reason tags were supplied by the published artifact.</p>}
      {array(row.qa?.flags).length > 0 && <p className="p21-flags">Data flags: {row.qa.flags.map(flag => words(typeof flag === 'string' ? flag : flag.code)).join(' · ')}</p>}
      <small className="p21-identity">{row.game_id || 'Game unavailable'} · Player ID: {row.player_id || 'Unavailable'}</small>
    </div>
  </details>
}

export default function Props21Challenger() {
  const [payload, setPayload] = useState(undefined)
  const [search, setSearch] = useState('')
  const [limit, setLimit] = useState(100)
  useEffect(() => {
    const controller = new AbortController()
    fetch(ENDPOINT, { cache:'no-store', signal:controller.signal }).then(response => response.ok ? response.json() : null).then(data => {
      if (!controller.signal.aborted) setPayload(data && Array.isArray(data.forecasts) ? data : null)
    }).catch(() => { if (!controller.signal.aborted) setPayload(null) })
    return () => controller.abort()
  }, [])
  const rows = array(payload?.forecasts)
  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    const priority = { RADAR:0, WATCH:1, 'NO SIGNAL':2 }
    return rows.filter(row => [row.player_name,row.player_id,row.team,propLabel(row.prop_type)].some(value => String(value || '').toLowerCase().includes(query))).sort((a,b) => {
      const signal = (priority[a.qa?.signal_state] ?? 3) - (priority[b.qa?.signal_state] ?? 3)
      if (signal) return signal
      return String(a.player_name || '').localeCompare(String(b.player_name || ''))
    })
  }, [rows, search])
  const visible = filtered.slice(0,limit)
  const priced = rows.filter(row => number(row.market_line) != null || number(row.market_probability_td) != null).length
  return <section className="p21-app" aria-labelledby="p21-title">
    <header className="p21-heading">
      <div className="lp-eyebrow"><span>PROPS 2.1 CHALLENGER</span><b>RESEARCH</b></div>
      <h1 id="p21-title">A closer look at player opportunity.</h1>
      <p>A separate research challenger for player roles, scoring opportunities and market context. Accuracy improvement and market superiority have not been established.</p>
      <a href="#/props">View the canonical V1 board →</a>
    </header>
    <dl className="p21-overview">
      <Metric label="Published forecasts" value={payload ? rows.length : 'Unavailable'}/>
      <Metric label="Market coverage" value={payload ? `${priced} of ${rows.length}` : 'Unavailable'}/>
      <Metric label="Updated (your local time)" value={timestamp(payload?.generated_at)}/>
      <Metric label="Model version" value={payload?.model_version || 'Unavailable'}/>
    </dl>
    {payload === undefined ? <p role="status" className="p21-empty">Loading the challenger publication…</p> : !rows.length ? <div className="p21-empty" role="status"><h2>No qualified challenger forecasts published.</h2><p>Current player, market and provenance checks must pass before a forecast appears. V1 remains available on its own board.</p>{payload?.status && <p>Publication state: {words(payload.status)}</p>}</div> : <>
      <label className="p21-search"><span>Search challenger players or markets</span><input type="search" value={search} onChange={event => { setSearch(event.target.value); setLimit(100) }} placeholder="Player, team or market"/></label>
      <p className="p21-count" aria-live="polite">Showing {visible.length} of {filtered.length} matching forecasts · Research states appear first. Open a row for source context and reason tags.</p>
      <div className="p21-board">{visible.map((row,index) => <Forecast key={[row.game_id,row.player_id,row.prop_type,index].join(':')} row={row}/>)}</div>
      {visible.length < filtered.length && <button className="p21-more" onClick={()=>setLimit(value=>value+100)}>Show 100 more</button>}
      {!filtered.length && <p className="p21-empty" role="status">No forecasts match your search.</p>}
    </>}
    <details className="p21-governance"><summary>Research boundary and publication checks</summary><p>This challenger has its own version and evidence stream. Published V1, Market Anchor, Shadow A and Shadow B retain their existing definitions. Signals describe upstream research state; they do not establish profitability.</p><p>Missing inputs appear as unavailable. Tags explain the published model state and do not add score bonuses.</p>{payload?.audit?.publication_note && <p>{payload.audit.publication_note}</p>}</details>
  </section>
}
