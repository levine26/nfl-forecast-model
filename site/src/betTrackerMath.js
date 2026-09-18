export const BET_UNIT_DOLLARS = 25

const EPS = 1e-9

export function numberOrNull(value) {
  if (value === '' || value == null) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function firstNumber(...values) {
  for (const value of values) {
    const parsed = numberOrNull(value)
    if (parsed != null) return parsed
  }
  return null
}

export function roundSpreadToHalfPoint(value) {
  const parsed = numberOrNull(value)
  if (parsed == null) return null
  const magnitude = Math.round((Math.abs(parsed) + EPS) * 2) / 2
  return parsed < 0 ? -magnitude : magnitude
}

function resultFromEdge(edge) {
  if (Math.abs(edge) <= EPS) return 'push'
  return edge > 0 ? 'win' : 'loss'
}

export function americanWinProfit(stake, odds) {
  const price = numberOrNull(odds)
  if (price == null || price === 0) return null
  return price > 0 ? stake * price / 100 : stake * 100 / Math.abs(price)
}

export function settleBet(result, odds, stake=BET_UNIT_DOLLARS) {
  if (result === 'pending') return null
  if (result === 'loss') return -stake
  if (result === 'push') return 0
  if (result !== 'win') return null
  return americanWinProfit(stake, odds)
}

function lockedModelMargin(row) {
  return firstNumber(row.locked_model_spread, row.expected_margin, row.predicted_margin)
}

function pickedTeam(row) {
  if (row.pick && row.pick !== 'PICKEM') return row.pick
  const homeProbability = firstNumber(row.final_home_prob)
  if (homeProbability == null) return null
  return homeProbability >= .5 ? row.home_team : row.away_team
}

function moneylinePrice(row, pick) {
  if (pick === row.home_team) {
    return firstNumber(row.locked_home_moneyline, row.home_moneyline_at_lock, row.bet_home_moneyline)
  }
  if (pick === row.away_team) {
    return firstNumber(row.locked_away_moneyline, row.away_moneyline_at_lock, row.bet_away_moneyline)
  }
  return null
}

function spreadPrice(row, side) {
  const captured = side === row.home_team
    ? firstNumber(row.locked_home_spread_price, row.home_spread_price_at_lock, row.bet_home_spread_price)
    : firstNumber(row.locked_away_spread_price, row.away_spread_price_at_lock, row.bet_away_spread_price)
  return {odds: captured ?? -110, fallback: captured == null}
}

export function buildBetLedger(history, stake=BET_UNIT_DOLLARS) {
  return (history || [])
    .filter(row => row.lock_status === 'LOCKED' && String(row.season || '2026') === '2026')
    .map(row => {
      const pick = pickedTeam(row)
      if (!pick) return null

      const homeScore = firstNumber(row.actual_home_score, row.final_home_score, row.home_score)
      const awayScore = firstNumber(row.actual_away_score, row.final_away_score, row.away_score)
      const graded = homeScore != null && awayScore != null
      const actualMargin = graded ? homeScore - awayScore : null
      const actualWinner = !graded ? null : actualMargin > 0 ? row.home_team : actualMargin < 0 ? row.away_team : null
      const mlResult = !graded ? 'pending' : actualWinner == null ? 'push' : pick === actualWinner ? 'win' : 'loss'
      const mlOdds = moneylinePrice(row, pick)

      const modelMargin = lockedModelMargin(row)
      let spread = null
      if (modelMargin != null) {
        const roundedModelMargin = roundSpreadToHalfPoint(modelMargin)
        const side = modelMargin > EPS ? row.home_team : modelMargin < -EPS ? row.away_team : pick
        const sideMargin = graded ? (side === row.home_team ? actualMargin : -actualMargin) : null
        const line = Math.abs(roundedModelMargin)
        const spreadResult = graded ? resultFromEdge(sideMargin - line) : 'pending'
        const price = spreadPrice(row, side)
        spread = {
          side,
          modelMargin,
          roundedModelMargin,
          line,
          odds: price.odds,
          usedFallbackPrice: price.fallback,
          result: spreadResult,
          profit: settleBet(spreadResult, price.odds, stake),
        }
      }

      return {
        gameId: row.game_id,
        week: Number(row.week),
        awayTeam: row.away_team,
        homeTeam: row.home_team,
        kickoffUtc: row.kickoff_utc || '',
        actualHomeScore: homeScore,
        actualAwayScore: awayScore,
        lockTimestamp: row.lock_timestamp_utc,
        stake,
        locked: true,
        ml: {
          pick,
          odds: mlOdds,
          result: mlResult,
          profit: settleBet(mlResult, mlOdds, stake),
          priceSource: row.bet_price_source || row.locked_moneyline_source || '',
        },
        spread,
      }
    })
    .filter(Boolean)
    .sort((a,b) => a.week - b.week || String(a.kickoffUtc).localeCompare(String(b.kickoffUtc)) || String(a.gameId).localeCompare(String(b.gameId)))
}

function previewEntry(game, stake=BET_UNIT_DOLLARS) {
  const homeProbability = firstNumber(game.official_home_win_probability, game.final_home_prob)
  const pick = game.official_winner && game.official_winner !== 'PICKEM'
    ? game.official_winner
    : homeProbability == null ? null : homeProbability >= .5 ? game.home_team : game.away_team
  if (!pick) return null

  const margin = firstNumber(game.diagnostics?.independent_margin_home, game.independent_margin_home)
  let spread = null
  if (margin != null) {
    const roundedModelMargin = roundSpreadToHalfPoint(margin)
    const side = margin > EPS ? game.home_team : margin < -EPS ? game.away_team : pick
    spread = {
      side,
      modelMargin: margin,
      roundedModelMargin,
      line: Math.abs(roundedModelMargin),
      odds: null,
      usedFallbackPrice: false,
      result: 'pending',
      profit: null,
    }
  }

  return {
    gameId: game.game_id,
    week: Number(game.week),
    awayTeam: game.away_team,
    homeTeam: game.home_team,
    kickoffUtc: game.kickoff_utc || '',
    lockTimestamp: null,
    stake,
    locked: false,
    lifecycleStatus: game.lifecycle_status || 'LIVE_FORECAST',
    ml: {
      pick,
      odds: null,
      result: 'pending',
      profit: null,
      priceSource: '',
    },
    spread,
  }
}

export function buildCurrentWeekSlate(currentGames, ledger, stake=BET_UNIT_DOLLARS) {
  const games = (currentGames || []).filter(game => Number.isFinite(Number(game.week)))
  const ledgerRows = ledger || []
  const currentWeeks = games.map(game => Number(game.week)).filter(Number.isFinite)
  const ledgerWeeks = ledgerRows.map(entry => Number(entry.week)).filter(Number.isFinite)
  const week = currentWeeks.length ? Math.max(...currentWeeks) : ledgerWeeks.length ? Math.max(...ledgerWeeks) : null
  if (week == null) return {week:null, entries:[]}

  const lockedByGame = new Map(ledgerRows.filter(entry => entry.week === week).map(entry => [entry.gameId, entry]))
  const entries = []
  const seen = new Set()

  for (const game of games.filter(game => Number(game.week) === week)) {
    const entry = lockedByGame.get(game.game_id) || previewEntry(game, stake)
    if (!entry) continue
    entries.push(entry)
    seen.add(entry.gameId)
  }

  for (const entry of ledgerRows.filter(entry => entry.week === week)) {
    if (seen.has(entry.gameId)) continue
    entries.push(entry)
  }

  entries.sort((a,b) => String(a.kickoffUtc || '').localeCompare(String(b.kickoffUtc || '')) || String(a.gameId).localeCompare(String(b.gameId)))
  return {week, entries}
}

export function combinedEntryProfit(entry) {
  const bets = [entry?.ml, entry?.spread].filter(Boolean)
  if (!bets.length || bets.some(bet => bet.result === 'pending') || bets.some(bet => bet.profit == null)) return null
  return bets.reduce((sum, bet) => sum + bet.profit, 0)
}

export function summarizeBets(entries, kind) {
  const bets = entries
    .map(entry => kind === 'ml' ? entry.ml : entry.spread)
    .filter(Boolean)
  const settled = bets.filter(bet => bet.result !== 'pending')
  const pending = bets.length - settled.length
  const wins = settled.filter(bet => bet.result === 'win').length
  const losses = settled.filter(bet => bet.result === 'loss').length
  const pushes = settled.filter(bet => bet.result === 'push').length
  const missingProfit = settled.filter(bet => bet.profit == null).length
  const risked = settled.length * BET_UNIT_DOLLARS
  const committed = bets.length * BET_UNIT_DOLLARS
  const profit = missingProfit ? null : settled.reduce((sum, bet) => sum + bet.profit, 0)
  return {
    bets: bets.length,
    settled: settled.length,
    pending,
    wins,
    losses,
    pushes,
    missingProfit,
    risked,
    committed,
    profit,
    roi: profit == null || risked <= 0 ? null : profit / risked,
  }
}

export function summarizeCombined(entries) {
  const ml = summarizeBets(entries, 'ml')
  const spread = summarizeBets(entries, 'spread')
  const risked = ml.risked + spread.risked
  const committed = ml.committed + spread.committed
  const missingProfit = ml.missingProfit + spread.missingProfit
  const settled = ml.settled + spread.settled
  const pending = ml.pending + spread.pending
  const profit = missingProfit ? null : ml.profit + spread.profit
  return {
    bets: ml.bets + spread.bets,
    settled,
    pending,
    risked,
    committed,
    missingProfit,
    profit,
    roi: profit == null || risked <= 0 ? null : profit / risked,
  }
}


export function buildSeasonPerformance(entries) {
  const weeks=[...new Set((entries||[]).map(entry=>Number(entry.week)).filter(Number.isFinite))].sort((a,b)=>a-b)
  let cumulativeMl=0
  let cumulativeSpread=0
  let mlValid=true
  let spreadValid=true
  return weeks.map(week=>{
    const weekEntries=(entries||[]).filter(entry=>Number(entry.week)===week)
    const ml=summarizeBets(weekEntries,'ml')
    const spread=summarizeBets(weekEntries,'spread')
    if (ml.profit==null) mlValid=false
    else if (mlValid) cumulativeMl+=ml.profit
    if (spread.profit==null) spreadValid=false
    else if (spreadValid) cumulativeSpread+=spread.profit
    return {
      week,
      mlProfit: ml.profit,
      spreadProfit: spread.profit,
      cumulativeMl: mlValid ? cumulativeMl : null,
      cumulativeSpread: spreadValid ? cumulativeSpread : null,
    }
  })
}
