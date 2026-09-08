import React, { useEffect, useMemo, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import './sunday-signal.css'

const BASE = import.meta.env.BASE_URL

const TEAM = {
  ARI: ['Arizona Cardinals', '#97233F', 'ari'], ATL: ['Atlanta Falcons', '#A71930', 'atl'], BAL: ['Baltimore Ravens', '#241773', 'bal'],
  BUF: ['Buffalo Bills', '#00338D', 'buf'], CAR: ['Carolina Panthers', '#0085CA', 'car'], CHI: ['Chicago Bears', '#0B162A', 'chi'],
  CIN: ['Cincinnati Bengals', '#FB4F14', 'cin'], CLE: ['Cleveland Browns', '#311D00', 'cle'], DAL: ['Dallas Cowboys', '#003594', 'dal'],
  DEN: ['Denver Broncos', '#FB4F14', 'den'], DET: ['Detroit Lions', '#0076B6', 'det'], GB: ['Green Bay Packers', '#203731', 'gb'],
  HOU: ['Houston Texans', '#03202F', 'hou'], IND: ['Indianapolis Colts', '#002C5F', 'ind'], JAC: ['Jacksonville Jaguars', '#006778', 'jax'],
  JAX: ['Jacksonville Jaguars', '#006778', 'jax'], KC: ['Kansas City Chiefs', '#E31837', 'kc'], LAC: ['Los Angeles Chargers', '#0080C6', 'lac'],
  LA: ['Los Angeles Rams', '#003594', 'lar'], LV: ['Las Vegas Raiders', '#A5ACAF', 'lv'], MIA: ['Miami Dolphins', '#008E97', 'mia'],
  MIN: ['Minnesota Vikings', '#4F2683', 'min'], NE: ['New England Patriots', '#002244', 'ne'], NO: ['New Orleans Saints', '#D3BC8D', 'no'],
  NYG: ['New York Giants', '#0B2265', 'nyg'], NYJ: ['New York Jets', '#125740', 'nyj'], PHI: ['Philadelphia Eagles', '#004C54', 'phi'],
  PIT: ['Pittsburgh Steelers', '#FFB612', 'pit'], SEA: ['Seattle Seahawks', '#002244', 'sea'], SF: ['San Francisco 49ers', '#AA0000', 'sf'],
  TB: ['Tampa Bay Buccaneers', '#D50A0A', 'tb'], TEN: ['Tennessee Titans', '#0C2340', 'ten'], WAS: ['Washington Commanders', '#5A1414', 'wsh'],
}

const teamName = team => TEAM[team]?.[0] || team || '—'
const teamColor = team => TEAM[team]?.[1] || '#64748b'
const teamLogo = team => `https://a.espncdn.com/i/teamlogos/nfl/500/${TEAM[team]?.[2] || String(team || '').toLowerCase()}.png`
const num = value => {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}
const pct = (value, digits = 1) => num(value) == null ? '—' : `${(num(value) * 100).toFixed(digits)}%`
const one = value => num(value) == null ? '—' : num(value).toFixed(1)
const signed = value => num(value) == null ? '—' : `${num(value) > 0 ? '+' : ''}${num(value).toFixed(1)}`

function parseCSV(text) {
  const rows = []
  let row = [], cell = '', quoted = false
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i]
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i += 1 }
      else if (c === '"') quoted = false
      else cell += c
    } else if (c === '"') quoted = true
    else if (c === ',') { row.push(cell); cell = '' }
    else if (c === '\n') { row.push(cell); rows.push(row); row = []; cell = '' }
    else if (c !== '\r') cell += c
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row) }
  const headers = rows.shift() || []
  return rows.filter(r => r.some(Boolean)).map(r => Object.fromEntries(headers.map((key, i) => [key, r[i] ?? ''])))
}

async function fetchCSV(path) {
  try {
    const response = await fetch(`${BASE}data/${path}`, { cache: 'no-store' })
    return response.ok ? parseCSV(await response.text()) : []
  } catch { return [] }
}

async function fetchJSON(path, fallback = {}) {
  try {
    const response = await fetch(`${BASE}data/${path}`, { cache: 'no-store' })
    return response.ok ? await response.json() : fallback
  } catch { return fallback }
}

function easternKickoff(game) {
  if (!game?.gameday) return null
  const [year, month, day] = game.gameday.split('-').map(Number)
  const [hour = 0, minute = 0] = (game.gametime || '00:00').split(':').map(Number)
  if (!year || !month || !day) return null
  const nominal = Date.UTC(year, month - 1, day, hour, minute)
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(new Date(nominal))
  const shown = Object.fromEntries(parts.map(part => [part.type, part.value]))
  const easternRendered = Date.UTC(+shown.year, +shown.month - 1, +shown.day, +shown.hour, +shown.minute)
  return new Date(nominal - (easternRendered - nominal))
}

function kickoffText(game) {
  const kickoff = easternKickoff(game)
  if (!kickoff || Number.isNaN(kickoff.getTime())) return game?.gameday || 'TBD'
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZone: 'America/Los_Angeles',
  }).format(kickoff)
}

function modelLine(margin, home, away) {
  const value = num(margin)
  if (value == null) return '—'
  if (Math.abs(value) < 0.05) return 'PK'
  return value > 0 ? `${home} -${Math.abs(value).toFixed(1)}` : `${away} -${Math.abs(value).toFixed(1)}`
}

function normalizeGame(game) {
  const homeProbability = num(game.final_home_prob)
  const pick = game.pick || (homeProbability >= 0.5 ? game.home_team : game.away_team)
  const pickProbability = homeProbability == null ? null : pick === game.home_team ? homeProbability : 1 - homeProbability
  const margin = num(game.expected_margin)
  const market = num(game.spread_line)
  const pickEdge = margin == null || market == null ? null : pick === game.home_team ? margin - market : market - margin
  return { ...game, homeP: homeProbability, pick, pickP: pickProbability, margin, market, pickEdge }
}

function age(timestamp) {
  if (!timestamp) return '—'
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return '—'
  const minutes = Math.max(0, Math.round((Date.now() - date) / 60000))
  if (minutes < 60) return `${minutes}m`
  const hours = Math.round(minutes / 60)
  return hours < 48 ? `${hours}h` : `${Math.round(hours / 24)}d`
}

function american(probability) {
  const p = num(probability)
  if (p == null || p <= 0 || p >= 1) return '—'
  const price = p >= 0.5 ? -100 * p / (1 - p) : 100 * (1 - p) / p
  return `${price > 0 ? '+' : ''}${Math.round(price)}`
}

function TeamBadge({ team, size = 'md' }) {
  const [failed, setFailed] = useState(false)
  return (
    <span className={`team-badge ${size}`} style={{ '--team': teamColor(team) }}>
      {!failed && <img src={teamLogo(team)} alt="" onError={() => setFailed(true)} />}
      <span className={failed ? 'fallback visible' : 'fallback'}>{team}</span>
    </span>
  )
}

function LockBadge({ game, locked }) {
  const kickoff = easternKickoff(game)
  const minutes = kickoff ? (kickoff - new Date()) / 60000 : null
  if (locked) return <span className="state-pill locked">FINAL · LOCKED</span>
  if (minutes != null && minutes <= 120 && minutes > 0) return <span className="state-pill window">LOCK WINDOW</span>
  if (minutes != null && minutes <= 0) return <span className="state-pill started">STARTED</span>
  return <span className="state-pill live">● LIVE</span>
}

function ConfidencePill({ game, row }) {
  const score = num(row?.confidence_index)
  return <span className="signal-pill">{game.confidence || 'Forecast'}{score != null ? ` · ${Math.round(score)}` : ''}</span>
}

function FreshnessStrip({ status, sources }) {
  const rows = [
    ['LevLine', status?.generated_utc || status?.prediction_timestamp_utc, 'healthy'],
    ['Market', status?.market_updated_utc || status?.generated_utc, 'healthy'],
    ['Personnel', sources?.injuries?.as_of, sources?.injuries?.status],
    ['Context', sources?.generated_utc, sources?.evidence?.status],
  ]
  return (
    <div className="fresh-strip">
      {rows.map(([label, timestamp, state]) => (
        <div key={label}><span>{label}</span><b>{age(timestamp)}</b><em className={state === 'healthy' || !state ? 'ok' : 'warn'} /></div>
      ))}
    </div>
  )
}

function Header({ tab, setTab, status, sources, history }) {
  const tabs = [['week', 'Forecasts'], ['teams', 'Teams'], ['ratings', 'Power'], ['models', 'Model Lab'], ['history', 'History'], ['method', 'Method']]
  const locked = history.filter(row => row.lock_status === 'LOCKED')
  const graded = locked.filter(row => ['true', 'false'].includes(String(row.winner_correct).toLowerCase()))
  const accuracy = graded.length ? graded.filter(row => String(row.winner_correct).toLowerCase() === 'true').length / graded.length : null
  return (
    <>
      <header className="ss-topbar">
        <div className="ss-brand" onClick={() => setTab('week')}>
          <div className="ss-mark"><span>S</span><i /><span>S</span></div>
          <div>
            <div className="ss-title">SUNDAY SIGNAL</div>
            <div className="ss-sub">NFL forecasting & matchup intelligence <b>powered by LevLine</b></div>
          </div>
        </div>
        <div className="top-health"><span className="health-dot" /><div><b>{status?.status === 'healthy' ? 'MODEL LIVE' : 'LEVLINE'}</b><small>{accuracy != null ? `Official 2026: ${pct(accuracy, 0)} · ${graded.length} graded` : 'Official record starts at first lock'}</small></div></div>
      </header>
      <nav className="ss-nav">{tabs.map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</nav>
      <FreshnessStrip status={status} sources={sources} />
    </>
  )
}

function ProbabilityBar({ game }) {
  const home = game.homeP ?? 0.5
  const away = 1 - home
  return (
    <div className="prob-wrap">
      <div className="prob-labels"><span>{game.away_team} {pct(away, 0)}</span><span>{pct(home, 0)} {game.home_team}</span></div>
      <div className="probbar"><div style={{ width: `${away * 100}%`, background: teamColor(game.away_team) }} /><div style={{ width: `${home * 100}%`, background: teamColor(game.home_team) }} /></div>
    </div>
  )
}

function Spark({ rows, game }) {
  const data = rows.filter(row => row.game_id === game.game_id)
    .sort((a, b) => new Date(a.prediction_timestamp_utc) - new Date(b.prediction_timestamp_utc))
    .slice(-12)
    .map((row, index) => ({ index, probability: num(row.final_home_prob) }))
    .filter(point => point.probability != null)
  if (data.length < 2) return <div className="spark-empty">Awaiting movement</div>
  return (
    <ResponsiveContainer width="100%" height={42}>
      <AreaChart data={data}><Area dataKey="probability" type="monotone" stroke="currentColor" fill="currentColor" fillOpacity={0.08} strokeWidth={2} /></AreaChart>
    </ResponsiveContainer>
  )
}

function HeroStat({ label, main, sub }) {
  return <div className="hero-stat"><span>{label}</span><b>{main}</b><small>{sub}</small></div>
}

function Hero({ games, history, status }) {
  const next = [...games].filter(game => easternKickoff(game) && easternKickoff(game) > new Date()).sort((a, b) => easternKickoff(a) - easternKickoff(b))[0]
  const locked = history.filter(row => row.lock_status === 'LOCKED').length
  const strongest = [...games].sort((a, b) => (b.pickP || 0) - (a.pickP || 0))[0]
  return (
    <section className="signal-hero">
      <div className="hero-copy">
        <span className="eyebrow">2026 · WEEK {games[0]?.week || '—'}</span>
        <h1>Find the signal.<br /><em>Explain the football.</em></h1>
        <p>Sunday Signal is the publication. LevLine is the engine underneath it: calibrated forecasts, market comparison, matchup intelligence and an immutable record of what the model believed before kickoff.</p>
      </div>
      <div className="hero-board">
        <HeroStat label="Next kickoff" main={next ? `${next.away_team} @ ${next.home_team}` : 'Slate complete'} sub={next ? kickoffText(next) : ''} />
        <HeroStat label="Top signal" main={strongest ? `${strongest.pick} ${pct(strongest.pickP)}` : '—'} sub={strongest?.confidence || 'Current conviction'} />
        <HeroStat label="Official locks" main={`${locked} / ${games.length || 0}`} sub="Graded predictions only" />
        <HeroStat label="Forecast age" main={age(status?.generated_utc || status?.prediction_timestamp_utc)} sub="Latest LevLine output" />
      </div>
    </section>
  )
}

function marketFavorite(game) {
  if (game.market == null || Math.abs(game.market) < 0.05) return null
  return game.market > 0 ? game.home_team : game.away_team
}

function SpotlightTile({ kicker, game, value, note, onOpen }) {
  if (!game) return null
  return (
    <button className="spotlight-tile" onClick={() => onOpen(game)} style={{ '--away': teamColor(game.away_team), '--home': teamColor(game.home_team) }}>
      <span>{kicker}</span>
      <div className="spotlight-matchup"><TeamBadge team={game.away_team} size="sm" /><b>{game.away_team} @ {game.home_team}</b><TeamBadge team={game.home_team} size="sm" /></div>
      <strong>{value}</strong><small>{note}</small>
    </button>
  )
}

function SpotlightRow({ games, onOpen }) {
  const strongest = [...games].sort((a, b) => (b.pickP || 0) - (a.pickP || 0))[0]
  const biggestEdge = [...games].filter(game => game.pickEdge != null).sort((a, b) => b.pickEdge - a.pickEdge)[0]
  const upset = [...games].filter(game => marketFavorite(game) && game.pick !== marketFavorite(game) && (game.pickP || 0) >= 0.5).sort((a, b) => (b.pickP || 0) - (a.pickP || 0))[0]
  const closest = [...games].sort((a, b) => Math.abs((a.pickP || 0.5) - 0.5) - Math.abs((b.pickP || 0.5) - 0.5))[0]
  return (
    <section className="spotlight-row">
      <SpotlightTile kicker="STRONGEST SIGNAL" game={strongest} value={strongest ? `${strongest.pick} ${pct(strongest.pickP)}` : '—'} note="Highest current win probability" onOpen={onOpen} />
      <SpotlightTile kicker="MARKET DISAGREEMENT" game={biggestEdge} value={biggestEdge ? `${biggestEdge.pick} ${signed(biggestEdge.pickEdge)} pts` : '—'} note="Largest LevLine spread gap" onOpen={onOpen} />
      <SpotlightTile kicker={upset ? 'UPSET WATCH' : 'TIGHTEST CALL'} game={upset || closest} value={upset ? `${upset.pick} ${pct(upset.pickP)}` : closest ? `${closest.pick} ${pct(closest.pickP)}` : '—'} note={upset ? `Against market favorite ${marketFavorite(upset)}` : 'Closest game on the slate'} onOpen={onOpen} />
    </section>
  )
}

function Metric({ label, value, hot = false, sub }) {
  return <div className={`metric ${hot ? 'hot' : ''}`}><span>{label}</span><b>{value}</b>{sub && <small>{sub}</small>}</div>
}

function previewTeaser(preview) {
  return preview?.headline || preview?.title || preview?.paragraphs?.[0] || 'Open the forecast for the matchup thesis, key factors and model-versus-market case.'
}

function GameCard({ game, runs, evidence, preview, locked, autopsy, onOpen }) {
  const actual = autopsy && typeof autopsy === 'object' ? autopsy : null
  return (
    <article className={`signal-card ${actual ? 'finished' : ''}`} onClick={onOpen} style={{ '--away': teamColor(game.away_team), '--home': teamColor(game.home_team) }}>
      <div className="card-head"><span>{kickoffText(game)}</span><LockBadge game={game} locked={locked} /></div>
      <div className="matchup-row"><div><TeamBadge team={game.away_team} /><b>{teamName(game.away_team)}</b></div><em>@</em><div><TeamBadge team={game.home_team} /><b>{teamName(game.home_team)}</b></div></div>
      <ProbabilityBar game={game} />
      <div className="forecast-core"><div><span>LEVLINE PICK</span><b>{game.pick} {pct(game.pickP)}</b></div><div><span>PROJECTED SCORE</span><b>{game.projected_score || '—'}</b></div></div>
      <p className="card-teaser">{previewTeaser(preview)}</p>
      <div className="mini-grid"><Metric label="LevLine" value={modelLine(game.margin, game.home_team, game.away_team)} /><Metric label="Market" value={modelLine(game.market, game.home_team, game.away_team)} /><Metric label="Edge" value={signed(game.pickEdge)} hot={(game.pickEdge || 0) > 2} /><Metric label="Signal" value={game.confidence || '—'} /></div>
      <div className="sparkline"><span>Signal change</span><Spark rows={runs} game={game} /></div>
      <div className="card-foot"><span>{preview?.key_factors?.length ? `${preview.key_factors.length} matchup factors` : `${evidence?.length || 0} verified signals`}</span>{actual ? <b>{String(actual.correct).toLowerCase() === 'true' ? '✓ Correct' : '✕ Miss'}</b> : <button>Read forecast →</button>}</div>
    </article>
  )
}

function WeekPage({ games, runs, evidence, previews, history, status, autopsies, setSelected }) {
  const [sortMode, setSortMode] = useState('kickoff')
  const locked = new Set(history.filter(row => row.lock_status === 'LOCKED').map(row => row.game_id))
  const sorted = useMemo(() => {
    const copy = [...games]
    if (sortMode === 'strength') return copy.sort((a, b) => (b.pickP || 0) - (a.pickP || 0))
    if (sortMode === 'edge') return copy.sort((a, b) => (b.pickEdge ?? -999) - (a.pickEdge ?? -999))
    if (sortMode === 'close') return copy.sort((a, b) => Math.abs((a.pickP || 0.5) - 0.5) - Math.abs((b.pickP || 0.5) - 0.5))
    return copy.sort((a, b) => (easternKickoff(a)?.getTime() || 0) - (easternKickoff(b)?.getTime() || 0))
  }, [games, sortMode])
  return (
    <main>
      <Hero games={games} history={history} status={status} />
      <SpotlightRow games={games} onOpen={setSelected} />
      <section className="section slate-section">
        <div className="section-title"><div><span>WEEK {games[0]?.week || '—'} SIGNAL BOARD</span><h2>Every game gets a forecast and a football thesis.</h2></div><p>The card is the quick read. Open any matchup for the written preview, three deciding factors, personnel, history, matchup meter and model audit trail.</p></div>
        <div className="slate-toolbar"><span>Sort slate</span>{[['kickoff', 'Kickoff'], ['strength', 'Strongest'], ['edge', 'Biggest edge'], ['close', 'Closest']].map(([key, label]) => <button key={key} className={sortMode === key ? 'active' : ''} onClick={() => setSortMode(key)}>{label}</button>)}</div>
        <div className="cards">{sorted.map(game => <GameCard key={game.game_id} game={game} runs={runs} evidence={evidence[game.game_id] || []} preview={previews[game.game_id]} locked={locked.has(game.game_id)} autopsy={autopsies[game.game_id]} onOpen={() => setSelected(game)} />)}</div>
      </section>
    </main>
  )
}

function FactorCard({ factor, index }) {
  return <div className="factor-card"><span>{String(index + 1).padStart(2, '0')}</span><div><b>{factor.title || factor.family}</b><p>{factor.summary}</p><small>{factor.advantage_team ? `Edge: ${factor.advantage_team} · ` : ''}{factor.strength || 'Context'}{factor.sample_size ? ` · n=${factor.sample_size}` : ''}</small></div></div>
}

function EvidenceBlock({ title, items, empty }) {
  return (
    <section className="article-block evidence-block">
      <div className="block-head"><span>{title}</span><b>{items.length || 0}</b></div>
      {items.length ? items.map((item, index) => <div className="evidence-card" key={`${item.title}-${index}`}><div><span className={`strength ${(item.strength || 'context').toLowerCase()}`}>{item.strength || 'Context'}</span><b>{item.title}</b></div><p>{item.summary}</p><div className="evidence-foot">{item.sample_size && <span>Sample {item.sample_size}</span>}{item.as_of && <span>Updated {age(item.as_of)} ago</span>}{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Source ↗</a>}</div></div>) : <p className="empty-copy">{empty}</p>}
    </section>
  )
}

function MatchupMeter({ rows = [] }) {
  if (!rows.length) return null
  return <section className="article-block"><div className="block-head"><span>MATCHUP METER</span></div><div className="meter-list">{rows.map((row, index) => <div className="meter-row" key={`${row.label}-${index}`}><span>{row.label}</span><div><i /><b>{row.leader || 'Mixed'}</b></div><em>{row.strength || 'Context'}</em></div>)}</div></section>
}

function SourceHealth({ sources }) {
  const rows = Object.entries(sources || {}).filter(([, value]) => value && typeof value === 'object' && value.status)
  if (!rows.length) return null
  return <div className="source-health"><div className="source-health-title">Context source status</div>{rows.slice(0, 12).map(([key, value]) => <div key={key}><span>{key.replaceAll('_', ' ')}</span><b className={value.status === 'healthy' ? 'ok' : 'warn'}>{value.status}</b></div>)}</div>
}

function GameModal({ game, runs, evidence = [], preview, confidence, sources, locked, autopsy, onClose }) {
  const category = item => String(item.category || '').toLowerCase()
  const personnel = evidence.filter(item => ['injury', 'personnel'].includes(category(item)))
  const scheme = evidence.filter(item => ['scheme', 'matchup'].includes(category(item)))
  const history = evidence.filter(item => ['history', 'coaching', 'coordinator', 'structural_change'].includes(category(item)))
  const scenarios = evidence.filter(item => ['scenario', 'weather', 'travel'].includes(category(item)))
  const trend = runs.filter(row => row.game_id === game.game_id)
    .sort((a, b) => new Date(a.prediction_timestamp_utc) - new Date(b.prediction_timestamp_utc))
    .map((row, index) => ({ run: index + 1, probability: num(row.final_home_prob) }))
    .filter(point => point.probability != null)
  const generic = [
    `LevLine makes ${game.pick} the current pick at ${pct(game.pickP)} with a central margin of ${modelLine(game.margin, game.home_team, game.away_team)}.`,
    game.market == null ? 'No current market spread is attached.' : `The market is around ${modelLine(game.market, game.home_team, game.away_team)}, leaving ${signed(game.pickEdge)} points of difference on LevLine's selected side.`,
  ]
  const paragraphs = preview?.paragraphs?.length ? preview.paragraphs : generic
  const factors = preview?.key_factors || []
  const opponent = game.pick === game.home_team ? game.away_team : game.home_team
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="game-modal" onClick={event => event.stopPropagation()}>
        <button className="close" onClick={onClose} aria-label="Close">×</button>
        <div className="game-identity"><div><TeamBadge team={game.away_team} size="lg" /><h2>{teamName(game.away_team)}</h2></div><div className="vs"><span>{kickoffText(game)}</span><b>@</b><LockBadge game={game} locked={locked} /></div><div><TeamBadge team={game.home_team} size="lg" /><h2>{teamName(game.home_team)}</h2></div></div>
        <div className="story-kicker">SUNDAY SIGNAL GAME FILE</div>
        <h1 className="story-headline">{preview?.headline || `${game.pick} is LevLine's side — now here's the football case.`}</h1>
        <div className="verdict"><span>LEVLINE VERDICT</span><strong>{game.projected_score || `${game.pick} to win`}</strong><div><b>{game.pick} {pct(game.pickP)}</b><ConfidencePill game={game} row={confidence} /></div><small><b>LevLine</b> {modelLine(game.margin, game.home_team, game.away_team)} <i /> Market {modelLine(game.market, game.home_team, game.away_team)} <i /> Edge {signed(game.pickEdge)}</small></div>
        {autopsy && <div className="postgame-banner"><b>POSTGAME REVIEW</b><span>{autopsy.actual_score || autopsy.score || 'Final recorded'}</span><em>{String(autopsy.correct).toLowerCase() === 'true' ? 'Forecast winner correct' : 'Forecast winner missed'}</em></div>}
        <FreshnessStrip status={{ generated_utc: game.prediction_timestamp_utc }} sources={sources} />
        <div className="modal-grid">
          <article>
            <section className="article-block intro"><div className="block-head"><span>THE PREVIEW</span></div>{paragraphs.map((paragraph, index) => <p key={index}>{paragraph}</p>)}</section>
            <section className="article-block"><div className="block-head"><span>3 THINGS THAT DECIDE THIS GAME</span></div><div className="factor-list">{factors.length ? factors.slice(0, 3).map((factor, index) => <FactorCard key={index} factor={factor} index={index} />) : <p className="empty-copy">Three distinct matchup families have not cleared the evidence threshold yet.</p>}</div></section>
            <section className="case-grid"><div><span>THE CASE FOR {game.pick}</span><p>{preview?.case_for_pick || `LevLine's combined probability and margin signals favor ${game.pick}.`}</p></div><div><span>THE CASE FOR {opponent}</span><p>{preview?.case_for_opponent || 'The other side can flip the game through turnovers, explosives and high-leverage downs.'}</p></div></section>
            <MatchupMeter rows={preview?.matchup_meter || []} />
            <EvidenceBlock title="PERSONNEL & AVAILABILITY" items={personnel} empty="No official personnel item has cleared the display threshold yet." />
            <EvidenceBlock title="HISTORY VS. WHAT'S DIFFERENT NOW" items={history} empty="No verified opponent, quarterback or coordinator history has cleared the minimum evidence threshold yet." />
            <EvidenceBlock title="SCENARIO SENSITIVITY" items={scenarios} empty="No material weather, travel, rest or availability scenario is active." />
            <section className="article-block danger"><div className="block-head"><span>WHAT COULD MAKE US WRONG?</span></div><p>{preview?.what_could_make_us_wrong || 'Turnovers, explosives and third-/fourth-down variance remain the clearest upset path.'}</p></section>
            <section className="article-block verdict-copy"><div className="block-head"><span>FINAL READ</span></div><p>{preview?.prediction || `${game.pick} to win.`}</p><small>Only the immutable pregame lock is graded in Sunday Signal history.</small></section>
            <details className="raw-evidence"><summary>Show raw scheme & matchup evidence</summary><EvidenceBlock title="SCHEME & MATCHUP EVIDENCE" items={scheme} empty="No tactical item cleared the evidence filter." /></details>
          </article>
          <aside className="numbers">
            <div className="numbers-title"><span>LEVLINE MODEL CARD</span><h3>Numbers behind the read</h3></div>
            <Metric label="Sujar baseline" value={pct(game.sujar_home_prob)} sub={`${game.home_team} home win`} />
            <Metric label="Logistic" value={pct(game.logistic_home_prob)} />
            <Metric label="Extra Trees" value={pct(game.extra_trees_home_prob)} />
            <Metric label="XGBoost" value={pct(game.xgboost_home_prob)} />
            <Metric label="CatBoost" value={pct(game.catboost_home_prob)} />
            <Metric label="PURE" value={pct(game.pure_home_prob)} />
            <Metric label="Market" value={pct(game.market_home_prob)} />
            <Metric label="LevLine final" value={pct(game.homeP)} hot />
            <Metric label="Fair home ML" value={game.fair_home_moneyline || american(game.homeP)} />
            <Metric label="Expected total" value={one(game.expected_total)} />
            <Metric label="Home cover" value={pct(game.cover_home_prob)} />
            <Metric label="Over" value={pct(game.over_prob)} />
            <Metric label="Model disagreement" value={pct(game.model_disagreement)} />
            <SourceHealth sources={sources} />
          </aside>
        </div>
        <section className="trend"><div><span>FORECAST HISTORY</span><h3>How the signal moved</h3></div><div className="trend-chart">{trend.length > 1 ? <ResponsiveContainer width="100%" height={220}><AreaChart data={trend}><XAxis dataKey="run" tickLine={false} axisLine={false} /><YAxis domain={[0, 1]} tickFormatter={value => `${Math.round(value * 100)}%`} tickLine={false} axisLine={false} /><Tooltip formatter={value => pct(value)} /><Area dataKey="probability" type="monotone" stroke="#64d7c8" fill="#64d7c822" strokeWidth={3} /></AreaChart></ResponsiveContainer> : <div className="empty-chart">Movement appears after the second comparable run.</div>}</div></section>
      </div>
    </div>
  )
}

function PageHead({ kicker, title, copy }) {
  return <div className="page-head"><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></div>
}

function TeamsPage({ profiles, setTeam }) {
  const rows = [...profiles].sort((a, b) => (num(a.rank) || 999) - (num(b.rank) || 999))
  return <main className="inner"><PageHead kicker="32 TEAM PROFILES" title="The league through LevLine." copy="Power rank, efficiency, form and the next forecast — one card per team." /><div className="team-grid">{rows.map(row => <button className="team-card" key={row.team} onClick={() => setTeam(row)}><TeamBadge team={row.team} /><span>#{row.rank}</span><h3>{teamName(row.team)}</h3><div><small>Elo+</small><b>{num(row.elo_plus) == null ? '—' : Math.round(num(row.elo_plus))}</b></div><div><small>Next</small><b>{row.next_opponent ? `${row.next_site === 'HOME' ? 'vs' : '@'} ${row.next_opponent}` : 'TBD'}</b></div><div><small>Win</small><b>{pct(row.next_win_prob)}</b></div></button>)}</div></main>
}

function TeamModal({ team, onClose }) {
  return <div className="modal-backdrop" onClick={onClose}><div className="team-modal" onClick={event => event.stopPropagation()}><button className="close" onClick={onClose}>×</button><TeamBadge team={team.team} size="lg" /><span className="eyebrow">POWER RANK #{team.rank}</span><h2>{teamName(team.team)}</h2><div className="team-stats"><Metric label="Elo+" value={num(team.elo_plus) == null ? '—' : Math.round(num(team.elo_plus))} /><Metric label="Off EPA" value={num(team.off_epa) == null ? '—' : num(team.off_epa).toFixed(3)} /><Metric label="Def EPA allowed" value={num(team.def_epa_allowed) == null ? '—' : num(team.def_epa_allowed).toFixed(3)} /><Metric label="Pass EPA" value={num(team.pass_epa) == null ? '—' : num(team.pass_epa).toFixed(3)} /><Metric label="Recent form" value={pct(team.recent_win_pct, 0)} /><Metric label="Next win prob" value={pct(team.next_win_prob)} /></div></div></div>
}

function RatingsPage({ rows }) {
  const sorted = [...rows].sort((a, b) => (num(a.rank) || 999) - (num(b.rank) || 999))
  return <main className="inner"><PageHead kicker="POWER RATINGS" title="LevLine team strength." copy="Elo+ remains the published ranking spine until a richer composite earns chronological out-of-sample inclusion." /><div className="table-wrap"><table><thead><tr><th>Rank</th><th>Team</th><th>Elo+</th><th>Off EPA</th><th>Def EPA allowed</th><th>Pass EPA</th><th>Recent</th><th>Move</th></tr></thead><tbody>{sorted.map(row => <tr key={row.team}><td>#{row.rank}</td><td><div className="table-team"><TeamBadge team={row.team} size="sm" />{teamName(row.team)}</div></td><td><b>{Math.round(num(row.elo_plus) || 0)}</b></td><td>{one(row.off_epa)}</td><td>{one(row.def_epa_allowed)}</td><td>{one(row.pass_epa)}</td><td>{pct(row.recent_win_pct, 0)}</td><td>{row.movement || row.rank_change || '—'}</td></tr>)}</tbody></table></div></main>
}

function ModelsPage({ rows, calibration }) {
  return <main className="inner"><PageHead kicker="MODEL LAB" title="Does LevLine earn its confidence?" copy="Chronological out-of-sample diagnostics matter more than a flashy raw win percentage." /><div className="lab-grid"><div className="table-wrap"><table><thead><tr><th>Rank</th><th>Model</th><th>Games</th><th>Winner%</th><th>Brier</th><th>Log loss</th><th>Margin MAE</th><th>Total MAE</th></tr></thead><tbody>{rows.map((row, index) => <tr key={`${row.model}-${index}`}><td>{row.rank || index + 1}</td><td><b>{row.model === 'Final Ensemble' ? 'LevLine' : row.model}</b></td><td>{row.games || '—'}</td><td>{row.winner_pct || row.winner_accuracy || '—'}</td><td>{row.brier || row.brier_score || '—'}</td><td>{row.log_loss || '—'}</td><td>{row.margin_mae || '—'}</td><td>{row.total_mae || '—'}</td></tr>)}</tbody></table></div><div className="cal-card"><span>CALIBRATION</span><h3>When LevLine says 70%, does it win about 70%?</h3>{calibration.length ? calibration.map((row, index) => <div key={index}><b>{row.bucket || row.probability_bucket || `Bucket ${index + 1}`}</b><span>{row.games || row.n || '—'} games</span><em>{row.actual_win_rate || row.observed_rate || '—'}</em></div>) : <p>Calibration bins populate as graded predictions accumulate.</p>}</div></div></main>
}

function HistoryPage({ history, autopsies }) {
  const graded = history.filter(row => autopsies[row.game_id]?.correct != null)
  const wins = graded.filter(row => String(autopsies[row.game_id]?.correct).toLowerCase() === 'true').length
  const average = history.length ? history.reduce((sum, row) => sum + (num(row.pick_prob || row.final_pick_prob) || 0), 0) / history.length : null
  return <main className="inner"><PageHead kicker="OFFICIAL HISTORY" title="No hindsight edits." copy="Only immutable pregame locks are graded. Postgame reviews explain misses without rewriting what LevLine believed before kickoff." /><div className="history-summary"><HeroStat label="Official locks" main={history.length} sub="Immutable forecast snapshots" /><HeroStat label="Graded record" main={graded.length ? `${wins}-${graded.length - wins}` : '—'} sub={graded.length ? `${pct(wins / graded.length, 0)} winner accuracy` : 'Begins after results post'} /><HeroStat label="Avg pick confidence" main={average == null ? '—' : pct(average)} sub="Across official locks" /></div>{history.length ? <div className="table-wrap"><table><thead><tr><th>Week</th><th>Matchup</th><th>Pick</th><th>Probability</th><th>Projected</th><th>Status</th><th>Result</th></tr></thead><tbody>{history.map((row, index) => <tr key={`${row.game_id}-${index}`}><td>{row.week || '—'}</td><td>{row.away_team && row.home_team ? `${row.away_team} @ ${row.home_team}` : row.game_id}</td><td><b>{row.pick || '—'}</b></td><td>{pct(row.pick_prob || row.final_pick_prob || row.final_home_prob)}</td><td>{row.projected_score || '—'}</td><td>{row.lock_status || 'LOCKED'}</td><td>{autopsies[row.game_id]?.correct != null ? (String(autopsies[row.game_id].correct).toLowerCase() === 'true' ? '✓ Correct' : '✕ Miss') : 'Pending'}</td></tr>)}</tbody></table></div> : <div className="empty-state">Official history appears after the first forecast enters the lock window.</div>}</main>
}

function Method({ title, body }) {
  return <div className="method-card"><span>{title}</span><p>{body}</p></div>
}

function MethodPage() {
  return <main className="inner"><PageHead kicker="METHODOLOGY" title="Accountable by construction." copy="LevLine predicts. The evidence layer explains. Context only moves the model when it separately proves predictive value." /><div className="method-grid"><Method title="1 · Football signal" body="Elo+, efficiency, recent form, rest, pass/rush splits, success and matchup features feed independent models." /><Method title="2 · Model ensemble" body="Logistic regression, Extra Trees, XGBoost and CatBoost produce chronological out-of-fold predictions before stacking." /><Method title="3 · Market signal" body="PURE remains football-only. MARKET+ blends market information conservatively and is tracked separately." /><Method title="4 · Matchup intelligence" body="Personnel, scheme, quarterback history, coaching changes, weather and travel explain the forecast without silently rewriting it." /><Method title="5 · Final Signal" body="The first valid prediction inside the pregame lock window becomes immutable and is the only forecast used for official grading." /><Method title="6 · Postgame audit" body="Winner accuracy, Brier score, log loss, calibration, margin MAE and total MAE are tracked. Misses become diagnostics, not excuses." /></div></main>
}

export default function App() {
  const [tab, setTab] = useState('week')
  const [games, setGames] = useState([])
  const [runs, setRuns] = useState([])
  const [evidence, setEvidence] = useState({})
  const [previews, setPreviews] = useState({})
  const [sources, setSources] = useState({})
  const [status, setStatus] = useState({})
  const [ratings, setRatings] = useState([])
  const [models, setModels] = useState([])
  const [history, setHistory] = useState([])
  const [profiles, setProfiles] = useState([])
  const [calibration, setCalibration] = useState([])
  const [confidence, setConfidence] = useState([])
  const [autopsies, setAutopsies] = useState({})
  const [selected, setSelected] = useState(null)
  const [team, setTeam] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    ;(async () => {
      try {
        const [g, r, e, p, s, st, pr, ml, h, tp, cal, conf, auto] = await Promise.all([
          fetchCSV('this_week.csv'), fetchCSV('run_history.csv'), fetchJSON('contextual_evidence.json', {}), fetchJSON('game_previews.json', {}),
          fetchJSON('context_source_status.json', {}), fetchJSON('status.json', {}), fetchCSV('power_ratings.csv'), fetchCSV('model_leaderboard.csv'),
          fetchCSV('prediction_history.csv'), fetchCSV('team_profiles.csv'), fetchCSV('calibration.csv'), fetchCSV('confidence_diagnostics.csv'), fetchJSON('postgame_autopsies.json', {}),
        ])
        setGames(g.map(normalizeGame)); setRuns(r); setEvidence(e); setPreviews(p); setSources(s); setStatus(st); setRatings(pr); setModels(ml); setHistory(h); setProfiles(tp); setCalibration(cal); setConfidence(conf); setAutopsies(auto)
      } catch (err) { setError(String(err)) }
    })()
  }, [])

  const confidenceMap = useMemo(() => Object.fromEntries(confidence.map(row => [row.game_id, row])), [confidence])
  const locked = useMemo(() => new Set(history.filter(row => row.lock_status === 'LOCKED').map(row => row.game_id)), [history])

  if (error) return <div className="fatal"><b>Sunday Signal could not load.</b><span>{error}</span></div>

  return (
    <div className="app">
      <Header tab={tab} setTab={setTab} status={status} sources={sources} history={history} />
      {tab === 'week' && <WeekPage games={games} runs={runs} evidence={evidence} previews={previews} history={history} status={status} autopsies={autopsies} setSelected={setSelected} />}
      {tab === 'teams' && <TeamsPage profiles={profiles} setTeam={setTeam} />}
      {tab === 'ratings' && <RatingsPage rows={ratings} />}
      {tab === 'models' && <ModelsPage rows={models} calibration={calibration} />}
      {tab === 'history' && <HistoryPage history={history} autopsies={autopsies} />}
      {tab === 'method' && <MethodPage />}
      {selected && <GameModal game={selected} runs={runs} evidence={evidence[selected.game_id] || []} preview={previews[selected.game_id]} confidence={confidenceMap[selected.game_id]} sources={sources} locked={locked.has(selected.game_id)} autopsy={autopsies[selected.game_id]} onClose={() => setSelected(null)} />}
      {team && <TeamModal team={team} onClose={() => setTeam(null)} />}
      <footer><b>SUNDAY SIGNAL</b><span>Powered by LevLine · probabilities, not prophecies</span></footer>
    </div>
  )
}
