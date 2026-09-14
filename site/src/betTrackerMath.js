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
      const homeScore = firstNumber(row.actual_home_score, row.final_home_score, row.home_score)
      const awayScore = firstNumber(row.actual_away_score, row.final_away_score, row.away_score)
      if (homeScore == null || awayScore == null) return null

      const actualMargin = homeScore - awayScore
      const pick = pickedTeam(row)
      if (!pick) return null
      const actualWinner = actualMargin > 0 ? row.home_team : actualMargin < 0 ? row.away_team : null
      const mlResult = actualWinner == null ? 'push' : pick === actualWinner ? 'win' : 'loss'
      const mlOdds = moneylinePrice(row, pick)
      const mlProfit = settleBet(mlResult, mlOdds, stake)

      const modelMargin = lockedModelMargin(row)
      let spread = null
      if (modelMargin != null) {
        const side = modelMargin > EPS ? row.home_team : modelMargin < -EPS ? row.away_team : pick
        const sideMargin = side === row.home_team ? actualMargin : -actualMargin
        const spreadEdge = sideMargin - Math.abs(modelMargin)
        const spreadResult = resultFromEdge(spreadEdge)
        const price = spreadPrice(row, side)
        spread = {
          side,
          modelMargin,
          line: Math.abs(modelMargin),
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
        actualHomeScore: homeScore,
        actualAwayScore: awayScore,
        lockTimestamp: row.lock_timestamp_utc,
        stake,
        ml: {
          pick,
          odds: mlOdds,
          result: mlResult,
          profit: mlProfit,
          priceSource: row.bet_price_source || row.locked_moneyline_source || '',
        },
        spread,
      }
    })
    .filter(Boolean)
    .sort((a,b) => a.week - b.week || String(a.gameId).localeCompare(String(b.gameId)))
}

export function summarizeBets(entries, kind) {
  const bets = entries
    .map(entry => kind === 'ml' ? entry.ml : entry.spread)
    .filter(Boolean)
  const wins = bets.filter(bet => bet.result === 'win').length
  const losses = bets.filter(bet => bet.result === 'loss').length
  const pushes = bets.filter(bet => bet.result === 'push').length
  const missingProfit = bets.filter(bet => bet.profit == null).length
  const risked = bets.length * BET_UNIT_DOLLARS
  const profit = missingProfit ? null : bets.reduce((sum, bet) => sum + bet.profit, 0)
  return {
    bets: bets.length,
    wins,
    losses,
    pushes,
    missingProfit,
    risked,
    profit,
    roi: profit == null || risked <= 0 ? null : profit / risked,
  }
}

export function summarizeCombined(entries) {
  const ml = summarizeBets(entries, 'ml')
  const spread = summarizeBets(entries, 'spread')
  const risked = ml.risked + spread.risked
  const missingProfit = ml.missingProfit + spread.missingProfit
  const profit = missingProfit ? null : ml.profit + spread.profit
  return {
    bets: ml.bets + spread.bets,
    risked,
    missingProfit,
    profit,
    roi: profit == null || risked <= 0 ? null : profit / risked,
  }
}
