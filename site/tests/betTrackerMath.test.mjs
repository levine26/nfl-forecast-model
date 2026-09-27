import test from 'node:test'
import assert from 'node:assert/strict'

import {
  BET_UNIT_DOLLARS,
  americanWinProfit,
  buildBetLedger,
  buildCurrentWeekSlate,
  buildSeasonPerformance,
  combinedEntryProfit,
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

test('current-week slate includes pending public games and uses locked history when available', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_02_DET_BUF', season:'2026', week:'2', lock_status:'LOCKED',
    away_team:'DET', home_team:'BUF', pick:'BUF', final_home_prob:'0.67',
    expected_margin:'6.7', actual_home_score:'41', actual_away_score:'31',
    locked_home_moneyline:'-245',
  }])
  const slate=buildCurrentWeekSlate([
    {
      game_id:'2026_02_DET_BUF', week:2, away_team:'DET', home_team:'BUF',
      official_winner:'BUF', kickoff_utc:'2026-09-18T00:15:00+00:00',
      diagnostics:{independent_margin_home:6.7},
    },
    {
      game_id:'2026_02_NYG_DAL', week:2, away_team:'NYG', home_team:'DAL',
      official_winner:'DAL', kickoff_utc:'2026-09-20T17:00:00+00:00',
      diagnostics:{independent_margin_home:3.4},
    },
  ],ledger)
  assert.equal(slate.week,2)
  assert.equal(slate.entries.length,2)
  assert.equal(slate.entries[0].gameId,'2026_02_DET_BUF')
  assert.equal(slate.entries[0].locked,true)
  assert.equal(slate.entries[0].ml.result,'win')
  assert.equal(slate.entries[1].gameId,'2026_02_NYG_DAL')
  assert.equal(slate.entries[1].locked,false)
  assert.equal(slate.entries[1].ml.result,'pending')
  assert.equal(slate.entries[1].spread.side,'DAL')
  assert.equal(slate.entries[1].spread.line,3.5)
})

test('pending wagers do not enter weekly record, profit, or ROI', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_02_A_B', season:'2026', week:'2', lock_status:'LOCKED',
    away_team:'A', home_team:'B', pick:'B', final_home_prob:'0.60',
    expected_margin:'3.5', locked_home_moneyline:'-125',
  }])
  assert.equal(ledger.length,1)
  assert.equal(ledger[0].ml.result,'pending')
  assert.equal(ledger[0].spread.result,'pending')
  const ml=summarizeBets(ledger,'ml')
  assert.equal(ml.pending,1)
  assert.equal(ml.wins,0)
  assert.equal(ml.losses,0)
  assert.equal(ml.risked,0)
  assert.equal(ml.profit,0)
  assert.equal(ml.roi,null)
  assert.equal(combinedEntryProfit(ledger[0]),null)
})

test('game P/L combines settled moneyline and spread wagers', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_02_DET_BUF', season:'2026', week:'2', lock_status:'LOCKED',
    away_team:'DET', home_team:'BUF', pick:'BUF', final_home_prob:'0.67',
    expected_margin:'6.5', actual_home_score:'41', actual_away_score:'31',
    locked_home_moneyline:'-245', locked_home_spread_price:'-110',
  }])
  const expected=25*100/245 + 25*100/110
  assert.ok(Math.abs(combinedEntryProfit(ledger[0])-expected)<1e-9)
})

test('season performance accumulates Moneyline and spread P/L by week', () => {
  const ledger=buildBetLedger([
    {
      game_id:'2026_01_A_B', season:'2026', week:'1', lock_status:'LOCKED',
      away_team:'A', home_team:'B', pick:'B', final_home_prob:'0.60',
      expected_margin:'3.5', actual_home_score:'24', actual_away_score:'20',
      locked_home_moneyline:'-125', locked_home_spread_price:'-110',
    },
    {
      game_id:'2026_02_C_D', season:'2026', week:'2', lock_status:'LOCKED',
      away_team:'C', home_team:'D', pick:'D', final_home_prob:'0.60',
      expected_margin:'3.5', actual_home_score:'20', actual_away_score:'24',
      locked_home_moneyline:'-125', locked_home_spread_price:'-110',
    },
  ])
  const series=buildSeasonPerformance(ledger)
  assert.equal(series.length,2)
  assert.equal(series[0].week,1)
  assert.ok(series[0].cumulativeMl>0)
  assert.ok(series[0].cumulativeSpread>0)
  assert.ok(series[1].cumulativeMl<series[0].cumulativeMl)
  assert.ok(series[1].cumulativeSpread<series[0].cumulativeSpread)
})

test('locked production receipts use the canonical ATS side at the locked market spread', () => {
  const rows=[
    {game_id:'2026_03_LAC_BUF',away_team:'LAC',home_team:'BUF',pick:'BUF',expected_margin:'9.988118084294427',spread_line:'7.0',side:'BUF',line:-7.0},
    {game_id:'2026_03_CAR_CLE',away_team:'CAR',home_team:'CLE',pick:'CAR',expected_margin:'-1.124340401960138',spread_line:'-2.5',side:'CLE',line:2.5},
    {game_id:'2026_03_NYJ_DET',away_team:'NYJ',home_team:'DET',pick:'DET',expected_margin:'9.436215430944443',spread_line:'6.5',side:'DET',line:-6.5},
    {game_id:'2026_03_HOU_IND',away_team:'HOU',home_team:'IND',pick:'HOU',expected_margin:'-1.19003104415717',spread_line:'-1.5',side:'IND',line:1.5},
    {game_id:'2026_03_NE_JAX',away_team:'NE',home_team:'JAX',pick:'JAX',expected_margin:'2.4895670799105223',spread_line:'3.0',side:'NE',line:3.0},
    {game_id:'2026_03_KC_MIA',away_team:'KC',home_team:'MIA',pick:'KC',expected_margin:'-3.687627745212781',spread_line:'-10.0',side:'MIA',line:10.0},
    {game_id:'2026_03_TEN_NYG',away_team:'TEN',home_team:'NYG',pick:'TEN',expected_margin:'6.881925916672355',spread_line:'2.5',side:'NYG',line:-2.5},
    {game_id:'2026_03_CIN_PIT',away_team:'CIN',home_team:'PIT',pick:'CIN',expected_margin:'-1.4827019057733204',spread_line:'-3.5',side:'PIT',line:3.5},
    {game_id:'2026_03_SEA_WAS',away_team:'SEA',home_team:'WAS',pick:'SEA',expected_margin:'-8.502736613436035',spread_line:'-8.5',side:'SEA',line:-8.5},
  ].map(row=>({...row,season:'2026',week:'3',lock_status:'LOCKED',final_home_prob:'0.50'}))

  const ledger=buildBetLedger(rows)
  const expectedByGame=new Map(rows.map(row=>[row.game_id,{side:row.side,line:row.line}]))
  assert.equal(ledger.length,9)
  for (const entry of ledger) {
    const expected=expectedByGame.get(entry.gameId)
    assert.ok(expected)
    assert.equal(entry.spread.strategy,'ATS_MARKET')
    assert.equal(entry.spread.side,expected.side)
    assert.equal(entry.spread.line,expected.line)
    assert.equal(entry.spread.result,'pending')
  }
})

test('ATS underdog grading applies the locked sportsbook handicap', () => {
  const ledger=buildBetLedger([{
    game_id:'2026_03_A_B',season:'2026',week:'3',lock_status:'LOCKED',
    away_team:'A',home_team:'B',pick:'A',final_home_prob:'0.45',
    expected_margin:'-1.0',spread_line:'-2.5',
    actual_home_score:'24',actual_away_score:'22',
  }])
  assert.equal(ledger[0].spread.strategy,'ATS_MARKET')
  assert.equal(ledger[0].spread.side,'B')
  assert.equal(ledger[0].spread.line,2.5)
  assert.equal(ledger[0].spread.result,'win')
})

test('current public ATS contract drives the pre-lock slate', () => {
  const slate=buildCurrentWeekSlate([{
    game_id:'2026_03_TEN_NYG',week:3,away_team:'TEN',home_team:'NYG',
    official_winner:'TEN',official_home_win_probability:0.4983,
    kickoff_utc:'2026-09-27T17:00:00+00:00',
    ats_status:'VALUE',ats_pick_team:'NYG',ats_pick_market_spread:-2.5,
    ats_model_margin_home:6.8819,ats_market_margin_home:2.5,ats_edge_points:4.3819,
  }],[])
  assert.equal(slate.entries.length,1)
  assert.equal(slate.entries[0].ml.pick,'TEN')
  assert.equal(slate.entries[0].spread.strategy,'ATS_MARKET')
  assert.equal(slate.entries[0].spread.side,'NYG')
  assert.equal(slate.entries[0].spread.line,-2.5)
})
