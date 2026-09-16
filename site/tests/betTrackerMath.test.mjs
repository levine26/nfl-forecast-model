import test from 'node:test'
import assert from 'node:assert/strict'

import {
  BET_UNIT_DOLLARS,
  americanWinProfit,
  buildBetLedger,
  roundSpreadToHalfPoint,
  settleBet,
  summarizeBets,
  summarizeCombined,
} from '../src/betTrackerMath.js'
import { canUseCurrentPreviewForReceipt } from '../src/historyEditorialSafety.js'

test('American odds settle a fixed $25 risk correctly', () => {
  assert.equal(BET_UNIT_DOLLARS, 25)
  assert.equal(americanWinProfit(25, 150), 37.5)
  assert.equal(americanWinProfit(25, -125), 20)
  assert.equal(settleBet('loss', -110), -25)
  assert.equal(settleBet('push', -110), 0)
})

test('modeled spread is graded against the LevLine line, not market spread', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_01_A_B', season:'2026', week:'1', lock_status:'LOCKED',
    away_team:'A', home_team:'B', pick:'B', final_home_prob:'0.60',
    locked_model_spread:'3.5', locked_market_spread:'7.5',
    actual_home_score:'24', actual_away_score:'20',
    locked_home_moneyline:'-125',
  }])
  assert.equal(ledger.length,1)
  assert.equal(ledger[0].spread.side,'B')
  assert.equal(ledger[0].spread.line,3.5)
  assert.equal(ledger[0].spread.result,'win')
  assert.equal(ledger[0].spread.odds,-110)
  assert.equal(ledger[0].spread.usedFallbackPrice,true)
})

test('modeled spreads round to the nearest half point before grading', () => {
  assert.equal(roundSpreadToHalfPoint(3.1),3)
  assert.equal(roundSpreadToHalfPoint(3.3),3.5)
  assert.equal(roundSpreadToHalfPoint(-3.8),-4)
  assert.equal(roundSpreadToHalfPoint(3.25),3.5)

  const ledger=buildBetLedger([{
    game_id:'2026_01_A_B', season:'2026', week:'1', lock_status:'LOCKED',
    away_team:'A', home_team:'B', pick:'B', final_home_prob:'0.60',
    locked_model_spread:'3.1', actual_home_score:'24', actual_away_score:'21',
    locked_home_moneyline:'-125',
  }])
  assert.equal(ledger.length,1)
  assert.equal(ledger[0].spread.modelMargin,3.1)
  assert.equal(ledger[0].spread.roundedModelMargin,3)
  assert.equal(ledger[0].spread.line,3)
  assert.equal(ledger[0].spread.result,'push')
})

test('spread push returns stake while remaining in ROI denominator', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_01_A_B', season:'2026', week:'1', lock_status:'LOCKED',
    away_team:'A', home_team:'B', pick:'B', final_home_prob:'0.60',
    locked_model_spread:'3', actual_home_score:'23', actual_away_score:'20',
    locked_home_moneyline:'-125',
  }])
  const summary=summarizeBets(ledger,'spread')
  assert.equal(summary.pushes,1)
  assert.equal(summary.risked,25)
  assert.equal(summary.profit,0)
  assert.equal(summary.roi,0)
})

test('missing winning ML price fails closed instead of inventing profit', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_01_A_B', season:'2026', week:'1', lock_status:'LOCKED',
    away_team:'A', home_team:'B', pick:'B', final_home_prob:'0.60',
    locked_model_spread:'3', actual_home_score:'23', actual_away_score:'20',
  }])
  const ml=summarizeBets(ledger,'ml')
  assert.equal(ml.missingProfit,1)
  assert.equal(ml.risked,25)
  assert.equal(ml.profit,null)
  assert.equal(ml.roi,null)
})

test('combined season ROI uses total dollars risked across both sections', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_01_A_B', season:'2026', week:'1', lock_status:'LOCKED',
    away_team:'A', home_team:'B', pick:'B', final_home_prob:'0.60',
    locked_model_spread:'3.5', actual_home_score:'24', actual_away_score:'20',
    locked_home_moneyline:'-125', locked_home_spread_price:'-110',
  }])
  const combined=summarizeCombined(ledger)
  assert.equal(combined.risked,50)
  assert.ok(Math.abs(combined.profit-(20+25*100/110))<1e-9)
  assert.ok(Math.abs(combined.roi-combined.profit/50)<1e-12)
})

test('historical receipt editorial fails closed after kickoff or grading', () => {
  const gameId='2026_01_DEN_KC'
  const preview={game_id:gameId,headline:'Pregame matchup read'}
  assert.equal(canUseCurrentPreviewForReceipt({
    gameId,
    currentGame:{game_id:gameId,lifecycle_status:'GRADED',kickoff_utc:'2026-09-13T20:00:00Z',lock_timestamp_utc:'2026-09-13T19:55:00Z'},
    preview,
  }),false)
  assert.equal(canUseCurrentPreviewForReceipt({
    gameId,
    currentGame:{game_id:gameId,lifecycle_status:'IN_PROGRESS',kickoff_utc:'2026-09-13T20:00:00Z',lock_timestamp_utc:'2026-09-13T19:55:00Z'},
    preview,
  }),false)
  assert.equal(canUseCurrentPreviewForReceipt({gameId,currentGame:null,preview}),false)
})

test('receipt editorial accepts only the exact current FINAL_PREGAME preview', () => {
  const gameId='2026_02_SEA_ARI'
  const currentGame={game_id:gameId,lifecycle_status:'FINAL_PREGAME',kickoff_utc:'2026-09-20T20:00:00Z',lock_timestamp_utc:'2026-09-20T19:55:00Z'}
  assert.equal(canUseCurrentPreviewForReceipt({gameId,currentGame,preview:{game_id:gameId}}),true)
  assert.equal(canUseCurrentPreviewForReceipt({gameId,currentGame,preview:{game_id:'2026_02_OTHER'}}),false)
  assert.equal(canUseCurrentPreviewForReceipt({
    gameId,
    currentGame:{...currentGame,lock_timestamp_utc:'2026-09-20T20:05:00Z'},
    preview:{game_id:gameId},
  }),false)
})
